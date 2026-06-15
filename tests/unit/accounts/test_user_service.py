from unittest.mock import Mock, patch

import pytest

from backend.apps.accounts.services.user_service import UserService


pytestmark = pytest.mark.django_db


class _FlexiblePrerequisiteException(Exception):
    def __init__(self, error_type=None, **kwargs):
        self.error_type = error_type
        self.context = kwargs.get('context', {})
        super().__init__(str(error_type))


@pytest.fixture(autouse=True)
def _patch_prereq(monkeypatch):
    monkeypatch.setattr(
        'backend.apps.accounts.services.user_service.PrerequisiteException',
        _FlexiblePrerequisiteException,
    )


def _user(role_name='Administrador general', rbd=123):
    user = Mock()
    user.id = 1
    user.rbd_colegio = rbd
    user.role = Mock(nombre=role_name)
    return user


class TestUserServiceValidations:
    def test_validations_required_fields(self):
        with pytest.raises(ValueError):
            UserService.validations({'email': 'a@a.cl'})

    @patch('backend.apps.accounts.services.user_service.User')
    def test_validations_duplicate_email(self, mock_user):
        email_qs = Mock()
        email_qs.exists.return_value = True
        mock_user.objects.filter.return_value = email_qs

        with pytest.raises(_FlexiblePrerequisiteException):
            UserService.validations({
                'email': 'a@a.cl',
                'nombre': 'A',
                'apellido_paterno': 'B',
                'role_name': 'Profesor',
                'rbd_colegio': 123,
            })

    @patch('backend.apps.accounts.services.user_service.User')
    def test_validations_duplicate_rut(self, mock_user):
        email_qs = Mock(); email_qs.exists.return_value = False
        rut_qs = Mock(); rut_qs.exists.return_value = True
        mock_user.objects.filter.side_effect = [email_qs, rut_qs]

        with pytest.raises(_FlexiblePrerequisiteException):
            UserService.validations({
                'email': 'a@a.cl',
                'nombre': 'A',
                'apellido_paterno': 'B',
                'role_name': 'Profesor',
                'rut': '11-1',
                'rbd_colegio': 123,
            })

    @patch('backend.apps.accounts.services.user_service.User')
    @patch('backend.apps.accounts.services.user_service.UserService._normalize_role', return_value='profesor')
    def test_validate_school_requirement_missing(self, _mock_role, mock_user):
        email_qs = Mock(); email_qs.exists.return_value = False
        mock_user.objects.filter.return_value = email_qs

        with pytest.raises(_FlexiblePrerequisiteException):
            UserService.validations({
                'email': 'a@a.cl',
                'nombre': 'A',
                'apellido_paterno': 'B',
                'role_name': 'Profesor',
            })


class TestUserServiceCrud:
    def test_create_delegates(self):
        actor = _user()
        with patch.object(UserService, 'validations') as mock_val, patch.object(UserService, 'create_user', return_value='u') as mock_create:
            result = UserService.create(actor, {
                'email': 'x@x.cl',
                'nombre': 'X',
                'apellido_paterno': 'Y',
                'role_name': 'Profesor',
                'rbd_colegio': 123,
            })

        assert result == 'u'
        mock_val.assert_called_once()
        mock_create.assert_called_once()

    @patch('backend.apps.accounts.services.user_service.Role')
    @patch('backend.apps.accounts.services.user_service.User')
    @patch('backend.apps.accounts.services.user_service.IntegrityService.validate_usuario_update')
    def test_update_success(self, mock_integrity, mock_user, mock_role):
        actor = _user()
        target = Mock()
        target.email = 'old@a.cl'
        target.nombre = 'Old'
        target.apellido_paterno = 'User'
        target.apellido_materno = None
        target.rut = None
        target.rbd_colegio = 123
        target.is_active = True
        target.role = Mock(nombre='Profesor')
        mock_user.objects.get.return_value = target
        mock_role.objects.get_or_create.return_value = (Mock(), True)

        with patch.object(UserService, '_require_user_management_scope') as mock_scope, patch.object(UserService, 'validations') as mock_val:
            result = UserService.update(actor, 5, {'nombre': 'Nuevo', 'role_name': 'Alumno'})

        assert result is target
        mock_scope.assert_called_once()
        mock_val.assert_called_once()
        mock_integrity.assert_called_once_with(123)
        target.save.assert_called_once()

    @patch('backend.apps.accounts.services.user_service.User')
    @patch('backend.apps.accounts.services.user_service.IntegrityService.validate_usuario_deletion')
    def test_delete_marks_inactive(self, mock_integrity, mock_user):
        target = Mock(rbd_colegio=123, role=Mock(nombre='Profesor'))
        mock_user.objects.get.return_value = target

        with patch.object(UserService, '_require_user_management_scope') as mock_scope:
            UserService.delete(_user(), 9)

        mock_scope.assert_called_once()
        mock_integrity.assert_called_once_with(123)
        target.save.assert_called_once_with(update_fields=['is_active'])

    @patch('backend.apps.accounts.services.user_service.User')
    def test_get_select_related(self, mock_user):
        expected = Mock()
        mock_user.objects.select_related.return_value.get.return_value = expected

        assert UserService.get(7) is expected


class TestUserServiceOperations:
    def test_validate_and_execute_dispatch(self):
        UserService.validate('create_user', {
            'email': 'a@a.cl',
            'nombre': 'A',
            'apellido_paterno': 'B',
            'role_name': 'Profesor',
        })
        UserService.validate('change_role', {'target_user_id': 1, 'new_role_name': 'Alumno'})

        with pytest.raises(ValueError):
            UserService.validate('change_role', {'target_user_id': 1})

        with pytest.raises(ValueError):
            UserService.validate('bad', {})

        with patch.object(UserService, '_execute_create_user', return_value='c') as c_mock, patch.object(
            UserService, '_execute_change_role', return_value='r'
        ) as r_mock:
            assert UserService._execute('create_user', {}) == 'c'
            assert UserService._execute('change_role', {}) == 'r'
        c_mock.assert_called_once()
        r_mock.assert_called_once()

    @patch('backend.apps.accounts.services.user_service.normalizar_rol', return_value='profesor')
    def test_normalize_and_school_requirement(self, _mock_norm):
        assert UserService._normalize_role('Profesor') == 'profesor'

        with patch.object(UserService, '_normalize_role', return_value='profesor'):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._validate_school_requirement('Profesor', None)

    def test_create_user_and_change_role_wrappers(self):
        with patch.object(UserService, 'execute', return_value='ok') as mock_exec:
            assert UserService.create_user(_user(), 'a@a.cl', 'Profesor', 'A', 'B', rbd_colegio=1) == 'ok'
            assert UserService.change_role(_user(), 1, 'Alumno') == 'ok'
        assert mock_exec.call_count == 2


class TestUserServiceExecuteCreate:
    @patch('backend.apps.accounts.services.user_service.Role')
    @patch('backend.apps.accounts.services.user_service.User')
    @patch('backend.apps.accounts.services.user_service.transaction')
    @patch('backend.apps.accounts.services.user_service.IntegrityService.validate_usuario_creation')
    def test_execute_create_user_success(self, _mock_integrity, mock_tx, mock_user, mock_role):
        email_qs = Mock(); email_qs.exists.return_value = False
        rut_qs = Mock(); rut_qs.exists.return_value = False
        mock_user.objects.filter.side_effect = [email_qs, rut_qs]
        created = Mock()
        mock_user.objects.create_user.return_value = created
        mock_role.objects.get_or_create.return_value = (Mock(), True)
        mock_tx.atomic.return_value.__enter__.return_value = None
        mock_tx.atomic.return_value.__exit__.return_value = False

        with patch.object(UserService, '_require_user_management_scope') as mock_scope, patch.object(UserService, '_validate_school_requirement'):
            result = UserService._execute_create_user({
                'actor': _user('Administrador general', rbd=None),
                'email': 'A@A.CL',
                'role_name': 'Profesor',
                'nombre': 'A',
                'apellido_paterno': 'B',
                'rut': '11-1',
                'rbd_colegio': 123,
            })

        assert result is created
        mock_scope.assert_called_once()

    @patch('backend.apps.accounts.services.user_service.User')
    def test_execute_create_user_duplicates(self, mock_user):
        email_qs = Mock(); email_qs.exists.return_value = True
        mock_user.objects.filter.return_value = email_qs

        with patch.object(UserService, '_require_user_management_scope'), patch.object(UserService, '_validate_school_requirement'), patch(
            'backend.apps.accounts.services.user_service.IntegrityService.validate_usuario_creation'
        ):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._execute_create_user({
                    'actor': _user('Administrador general', rbd=None),
                    'email': 'a@a.cl',
                    'role_name': 'Profesor',
                    'nombre': 'A',
                    'apellido_paterno': 'B',
                    'rbd_colegio': 123,
                })


class TestUserServiceExecuteChangeRole:
    @patch('backend.apps.accounts.services.user_service.User')
    @patch('backend.apps.accounts.services.user_service.SensitiveActionService.create_request')
    def test_execute_change_role_requires_dual_control_request(self, mock_create_request, mock_user):
        target = Mock(rbd_colegio=123)
        target.role = Mock(nombre='Alumno')
        mock_user.objects.select_related.return_value.get.return_value = target

        request_obj = Mock(id=77)
        mock_create_request.return_value = request_obj

        with patch.object(UserService, '_require_user_management_scope'), patch.object(
            UserService,
            '_validate_role_profile_consistency',
        ):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._execute_change_role({
                    'actor': _user('Administrador general', rbd=123),
                    'target_user_id': 1,
                    'new_role_name': 'Profesor',
                })

        mock_create_request.assert_called_once()

    @patch('backend.apps.accounts.services.user_service.Role')
    @patch('backend.apps.accounts.services.user_service.User')
    @patch('backend.apps.accounts.services.user_service.IntegrityService.validate_usuario_update')
    @patch('backend.apps.accounts.services.user_service.SensitiveActionService.mark_request_executed')
    @patch('backend.apps.accounts.services.user_service.SensitiveActionService.validate_and_approve_for_execution')
    def test_execute_change_role_success_with_approved_request(
        self,
        mock_approve_request,
        mock_mark_executed,
        mock_integrity,
        mock_user,
        mock_role,
    ):
        target = Mock(rbd_colegio=123)
        target.role = Mock(nombre='Alumno')
        mock_user.objects.select_related.return_value.get.return_value = target
        mock_role.objects.get_or_create.return_value = (Mock(), True)
        mock_approve_request.return_value = Mock(id=77)

        with patch.object(UserService, '_require_user_management_scope'), patch.object(
            UserService,
            '_validate_role_profile_consistency',
        ) as mock_consistency:
            result = UserService._execute_change_role({
                'actor': _user('Administrador general', rbd=123),
                'target_user_id': 1,
                'new_role_name': 'Profesor',
                'approval_request_id': 77,
            })

        assert result is target
        mock_consistency.assert_called_once()
        mock_integrity.assert_called_once_with(123)
        mock_mark_executed.assert_called_once()
        target.save.assert_called_once_with(update_fields=['role'])

    @patch('backend.apps.accounts.services.user_service.User')
    def test_execute_change_role_forbidden_scope(self, mock_user):
        target = Mock(rbd_colegio=123)
        target.role = Mock(nombre='Alumno')
        mock_user.objects.select_related.return_value.get.return_value = target

        with patch.object(UserService, '_require_user_management_scope', side_effect=_FlexiblePrerequisiteException('FORBIDDEN')):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._execute_change_role({
                    'actor': _user('Profesor', rbd=999),
                    'target_user_id': 1,
                    'new_role_name': 'Profesor',
                    'approval_request_id': 10,
                })

    def test_validate_role_profile_consistency(self):
        u1 = Mock(id=1)
        u1.perfil_estudiante = Mock()
        with patch.object(UserService, '_normalize_role', return_value='profesor'):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._validate_role_profile_consistency(u1, 'Profesor')

        u2 = Mock(id=2)
        u2.perfil_profesor = Mock()
        with patch.object(UserService, '_normalize_role', return_value='estudiante'):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._validate_role_profile_consistency(u2, 'Alumno')


class TestUserServiceManagementScope:
    def test_require_scope_allows_global_manager_for_global_role(self):
        with patch.object(UserService, '_has_global_user_management', return_value=True):
            UserService._require_user_management_scope(
                actor=_user('Administrador general', rbd=None),
                action='crear',
                target_role_name='Administrador general',
                target_school_rbd=None,
            )

    def test_require_scope_denies_school_manager_for_global_role(self):
        with patch.object(UserService, '_has_global_user_management', return_value=False):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._require_user_management_scope(
                    actor=_user('Administrador escolar', rbd=123),
                    action='crear',
                    target_role_name='Administrador general',
                    target_school_rbd=None,
                )

    def test_require_scope_denies_school_manager_cross_school_update(self):
        with patch.object(UserService, '_has_global_user_management', return_value=False):
            with pytest.raises(_FlexiblePrerequisiteException):
                UserService._require_user_management_scope(
                    actor=_user('Administrador escolar', rbd=123),
                    action='actualizar',
                    target_role_name='Profesor',
                    target_school_rbd=456,
                    current_role_name='Profesor',
                    current_school_rbd=123,
                )

    def test_require_scope_allows_school_manager_same_school(self):
        with patch.object(UserService, '_has_global_user_management', return_value=False), patch.object(
            UserService,
            '_has_school_user_management',
            return_value=True,
        ):
            UserService._require_user_management_scope(
                actor=_user('Administrador escolar', rbd=123),
                action='actualizar',
                target_role_name='Profesor',
                target_school_rbd=123,
                current_role_name='Profesor',
                current_school_rbd=123,
            )

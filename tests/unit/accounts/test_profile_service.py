"""Tests de ProfileService alineados a contratos actuales."""

from unittest.mock import Mock, patch

from backend.apps.accounts.services.profile_service import ProfileService


class TestProfileServiceRoleValidation:
    def test_validate_role_for_student_operations_success(self):
        user = Mock()
        user.role = Mock(nombre='Alumno')

        is_valid, error = ProfileService.validate_role_for_student_operations(user)

        assert is_valid is True
        assert error is None

    def test_validate_role_for_student_operations_wrong_role(self):
        user = Mock()
        user.role = Mock(nombre='Profesor')

        is_valid, error = ProfileService.validate_role_for_student_operations(user)

        assert is_valid is False
        assert 'acceso denegado' in error.lower()


class TestProfileServiceEmailValidation:
    def test_validate_email_format_valid(self):
        error = ProfileService.validate_email_format('usuario@ejemplo.com')
        assert error is None

    def test_validate_email_format_invalid(self):
        error = ProfileService.validate_email_format('email_invalido')
        assert error is not None
        assert 'no válido' in error['context']['message']

    def test_check_email_availability_available(self):
        user = Mock(id=1, rbd_colegio='12345')
        User = Mock()
        User.objects.filter.return_value.exclude.return_value.exists.return_value = False

        error = ProfileService.check_email_availability('nuevo@ejemplo.com', user, User)

        assert error is None

    def test_check_email_availability_in_use(self):
        user = Mock(id=1, rbd_colegio='12345')
        User = Mock()
        User.objects.filter.return_value.exclude.return_value.exists.return_value = True

        error = ProfileService.check_email_availability('usado@ejemplo.com', user, User)

        assert error is not None
        assert 'ya está en uso' in error['context']['message']


class TestProfileServiceUpdateProfile:
    def test_update_student_profile_success(self):
        user = Mock(username='estudiante1', id=1, rbd_colegio='12345')
        user.role = Mock(nombre='Alumno')
        user.save = Mock()

        User = Mock()
        User.objects.filter.return_value.exclude.return_value.exists.return_value = False

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(ProfileService, '_validate_school_integrity_from_user', return_value=None):
            success, message = ProfileService.update_student_profile(user, 'nuevo@email.com', User=User)

        assert success is True
        assert 'actualizado correctamente' in message
        assert user.email == 'nuevo@email.com'

    def test_update_student_profile_wrong_role(self):
        user = Mock(username='profesor1', id=1, rbd_colegio='12345')
        user.role = Mock(nombre='Profesor')

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(ProfileService, '_validate_school_integrity_from_user', return_value=None):
            success, message = ProfileService.update_student_profile(user, 'email@test.com')

        assert success is False
        assert 'acceso denegado' in message.lower()

    def test_update_staff_profile_email_in_use(self):
        user = Mock(username='admin1', id=1, rbd_colegio='12345')
        user.role = Mock(nombre='Administrador general')

        User = Mock()
        User.objects.filter.return_value.exclude.return_value.exists.return_value = True

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(ProfileService, '_validate_school_integrity_from_user', return_value=None):
            success, message = ProfileService.update_staff_profile(user, 'usado@email.com', User=User)

        assert success is False
        assert 'ya está en uso' in message


class TestProfileServicePasswordChange:
    def test_validate_password_change_success(self):
        user = Mock(username='usuario1')
        user.check_password = Mock(return_value=True)

        is_valid, error = ProfileService.validate_password_change(
            user,
            'password_actual',
            'nueva123456',
            'nueva123456',
            '192.168.1.1',
        )

        assert is_valid is True
        assert error is None

    def test_change_student_password_success(self):
        user = Mock(username='estudiante1', rbd_colegio='12345')
        user.role = Mock(nombre='Alumno')
        user.check_password = Mock(return_value=True)
        user.set_password = Mock()
        user.save = Mock()

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(ProfileService, '_validate_school_integrity_from_user', return_value=None):
            success, message = ProfileService.change_student_password(
                user,
                'actual123',
                'nueva123456',
                'nueva123456',
                '192.168.1.1',
            )

        assert success is True
        assert 'cambiada correctamente' in message

    def test_change_staff_password_validation_error(self):
        user = Mock(username='profesor1', rbd_colegio='12345')
        user.role = Mock(nombre='Profesor')
        user.check_password = Mock(return_value=True)

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(ProfileService, '_validate_school_integrity_from_user', return_value=None):
            success, message = ProfileService.change_staff_password(
                user,
                'actual123',
                'nueva123',
                'diferente123',
                '192.168.1.1',
            )

        assert success is False
        assert 'no coinciden' in message

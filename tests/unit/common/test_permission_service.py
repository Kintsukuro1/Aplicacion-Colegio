"""Unit tests para PermissionService alineados al contrato vigente."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied

from backend.common.services.permission_service import PermissionService


def _user(role_name: str, authenticated: bool = True, active: bool = True):
    return SimpleNamespace(
        is_authenticated=authenticated,
        is_active=active,
        email=f'{role_name}@test.cl',
        id=1,
        role=SimpleNamespace(nombre=role_name) if role_name else None,
    )


class TestPermissionServiceRoles:
    def test_admin_general_has_administrative_permissions(self):
        admin_general = _user('Administrador general')

        assert PermissionService.has_permission(admin_general, 'ADMINISTRATIVO', 'MANAGE_SYSTEM') is True
        assert PermissionService.has_permission(admin_general, 'ADMINISTRATIVO', 'VIEW_REPORTS') is True
        assert PermissionService.has_permission(admin_general, 'ACADEMICO', 'MANAGE_STUDENTS') is True

    def test_estudiante_has_view_only_permissions(self):
        estudiante = _user('Alumno')

        assert PermissionService.has_permission(estudiante, 'ACADEMICO', 'VIEW_OWN_GRADES') is True
        assert PermissionService.has_permission(estudiante, 'ACADEMICO', 'VIEW_OWN_ATTENDANCE') is True
        assert PermissionService.has_permission(estudiante, 'ACADEMICO', 'EDIT_GRADES') is False

    def test_none_user_returns_false(self):
        assert PermissionService.has_permission(None, 'ACADEMICO', 'VIEW_STUDENTS') is False

    def test_inactive_user_returns_false(self):
        user = _user('Profesor', active=False)
        assert PermissionService.has_permission(user, 'ACADEMICO', 'VIEW_STUDENTS') is False


class TestPermissionServiceDecorators:
    def test_decorator_allows_authorized_access(self):
        user = _user('Administrador escolar')

        @PermissionService.require_permission('ACADEMICO', 'VIEW_STUDENTS')
        def test_function(current_user):
            return 'success'

        assert test_function(user) == 'success'

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=False)
    def test_decorator_denies_unauthorized_access(self, _mock_perm):
        user = _user('Alumno')

        @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_SYSTEM')
        def test_function(current_user):
            return 'success'

        with pytest.raises(PermissionDenied):
            test_function(user)

    @patch('backend.common.services.permission_service.logger')
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=False)
    def test_decorator_logs_denied_access(self, _mock_perm, mock_logger):
        user = _user('Alumno')

        @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_SYSTEM')
        def test_function(current_user):
            return 'success'

        with pytest.raises(PermissionDenied):
            test_function(user)

        assert mock_logger.warning.call_count >= 1


def test_has_permission_delegates_context_to_policy_authorize():
    user = _user('Administrador general')

    with patch('backend.common.services.permission_service.PolicyService.has_capability', return_value=True), \
         patch('backend.common.services.permission_service.PolicyService.authorize', return_value=True) as mock_authorize:
        allowed = PermissionService.has_permission(
            user,
            'ACADEMICO',
            'VIEW_GRADES',
            context={'school_id': 123, 'student_id': 99},
        )

    assert allowed is True
    mock_authorize.assert_called_once_with(
        user,
        'GRADE_VIEW',
        context={'school_id': 123, 'student_id': 99},
    )


def test_manage_users_requires_global_scope_capability():
    user = _user('Administrador escolar')

    with patch('backend.common.services.permission_service.PolicyService.has_capability', return_value=False):
        allowed = PermissionService.has_permission(user, 'ADMINISTRATIVO', 'MANAGE_USERS')

    assert allowed is False

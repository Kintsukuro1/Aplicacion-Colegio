from unittest.mock import Mock, patch

import pytest

from backend.apps.accounts.services.role_service import RoleService


class _FakePrerequisiteException(Exception):
    def __init__(self, error_type=None, context=None):
        super().__init__(error_type)
        self.error_type = error_type
        self.context = context or {}


def test_validate_and_execute_guards():
    with pytest.raises(ValueError):
        RoleService.validate('validate_can_delete_role', {})
    with pytest.raises(ValueError):
        RoleService.validate('invalid', {})
    with pytest.raises(ValueError):
        RoleService._execute('invalid', {})


@patch('backend.apps.accounts.services.role_service.IntegrityService.validate_school_integrity_or_raise')
@patch('backend.apps.accounts.services.role_service.User')
def test_validate_integrity_for_role_scope(mock_user, mock_integrity):
    mock_user.objects.filter.return_value.values_list.return_value.distinct.return_value = [11, 12]
    role = Mock()

    RoleService._validate_integrity_for_role_scope(role)

    assert mock_integrity.call_count == 2


@patch('backend.apps.accounts.services.role_service.PrerequisiteException', _FakePrerequisiteException)
@patch('backend.apps.accounts.services.role_service.Role')
def test_validate_can_delete_role_not_found(mock_role):
    mock_role.DoesNotExist = type('DoesNotExist', (Exception,), {})
    mock_role.objects.get.side_effect = mock_role.DoesNotExist

    with pytest.raises(_FakePrerequisiteException) as exc:
        RoleService._execute_validate_can_delete_role({'role_id': 9})

    assert exc.value.context['role_id'] == 9


@patch('backend.apps.accounts.services.role_service.PrerequisiteException', _FakePrerequisiteException)
@patch('backend.apps.accounts.services.role_service.User')
@patch('backend.apps.accounts.services.role_service.Role')
def test_validate_can_delete_role_with_active_users(mock_role, mock_user):
    role = Mock(nombre='Profesor')
    mock_role.objects.get.return_value = role
    mock_user.objects.filter.return_value.count.return_value = 3

    with pytest.raises(_FakePrerequisiteException) as exc:
        RoleService._execute_validate_can_delete_role({'role_id': 1})

    assert exc.value.context['users_count'] == 3


@patch('backend.apps.accounts.services.role_service.logger')
@patch('backend.apps.accounts.services.role_service.User')
@patch('backend.apps.accounts.services.role_service.Role')
def test_validate_can_delete_role_without_active_users(mock_role, mock_user, mock_logger):
    role = Mock(nombre='Auxiliar')
    mock_role.objects.get.return_value = role
    mock_user.objects.filter.return_value.count.return_value = 0

    RoleService._execute_validate_can_delete_role({'role_id': 2})

    mock_logger.info.assert_called_once()


@patch('backend.apps.accounts.services.role_service.User')
@patch('backend.apps.accounts.services.role_service.Role')
def test_get_role_usage_stats_branches(mock_role, mock_user):
    mock_role.DoesNotExist = type('DoesNotExist', (Exception,), {})
    mock_role.objects.get.side_effect = mock_role.DoesNotExist
    not_found = RoleService._execute_get_role_usage_stats({'role_id': 99})
    assert not_found['exists'] is False

    role = Mock(nombre='Alumno')
    mock_role.objects.get.side_effect = None
    mock_role.objects.get.return_value = role
    mock_user.objects.filter.side_effect = [Mock(count=Mock(return_value=7)), Mock(count=Mock(return_value=5))]
    data = RoleService._execute_get_role_usage_stats({'role_id': 4})

    assert data['exists'] is True
    assert data['inactive_users'] == 2


@patch('backend.apps.accounts.services.role_service.logger')
@patch('backend.apps.accounts.services.role_service.IntegrityService.validate_school_integrity_or_raise')
@patch('backend.apps.accounts.services.role_service.User')
@patch('backend.apps.accounts.services.role_service.Role')
def test_assign_default_role_to_users_without_role(mock_role, mock_user, _mock_integrity, mock_logger):
    school_qs = Mock()
    school_qs.values_list.return_value.distinct.return_value = [100]
    users_without_role = Mock()
    users_without_role.count.return_value = 2
    mock_user.objects.filter.side_effect = [school_qs, users_without_role]
    mock_role.objects.get_or_create.return_value = (Mock(), True)

    count = RoleService._execute_assign_default_role_to_users_without_role({})

    assert count == 2
    users_without_role.update.assert_called_once()
    assert mock_logger.info.called
    assert mock_logger.warning.called

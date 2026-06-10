from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from backend.apps.security.services.security_monitoring_service import SecurityMonitoringService


def _user(role='Administrador general', rbd='123'):
    return Mock(role=Mock(nombre=role), rbd_colegio=rbd, username='admin')


def test_validate_execute_dispatch_guards():
    with pytest.raises(ValueError):
        SecurityMonitoringService.validate('', {})
    with pytest.raises(ValueError):
        SecurityMonitoringService.validate('x', [])
    with pytest.raises(ValueError):
        SecurityMonitoringService._execute('unknown', {})


@patch('backend.apps.institucion.models.Colegio')
def test_get_user_school_info_paths(mock_colegio):
    mock_colegio.DoesNotExist = type('DoesNotExist', (Exception,), {})
    colegio = Mock(nombre='Colegio Uno')
    mock_colegio.objects.get.return_value = colegio

    found = SecurityMonitoringService.get_user_school_info(_user(rbd='10'))
    assert found['rbd_colegio'] == '10'
    assert found['nombre_colegio'] == 'Colegio Uno'

    mock_colegio.objects.get.side_effect = mock_colegio.DoesNotExist
    missing = SecurityMonitoringService.get_user_school_info(_user(rbd='10'))
    assert missing['nombre_colegio'] == 'Sistema'


@patch('backend.apps.security.services.security_monitoring_service.settings')
def test_get_axes_settings(mock_settings):
    mock_settings.AXES_FAILURE_LIMIT = 5
    mock_settings.AXES_COOLOFF_TIME = 2

    result = SecurityMonitoringService.get_axes_settings()

    assert result == {'failure_limit': 5, 'cooloff_time': 2}


def test_calculate_statistics():
    failed = Mock(count=Mock(return_value=7))
    blocked = Mock(count=Mock(return_value=3))

    result = SecurityMonitoringService.calculate_statistics(failed, blocked)

    assert result['total_intentos_fallidos'] == 7
    assert result['total_ips_bloqueadas'] == 3


@patch('backend.apps.security.services.security_monitoring_service.get_user_model')
@patch('axes.models.AccessAttempt')
def test_validate_unblock_permission_admin_escolar_paths(mock_access_attempt, mock_get_user_model):
    user_model = Mock()
    mock_get_user_model.return_value = user_model
    user_model.objects.filter.return_value.values_list.return_value = ['u@test.cl']

    admin_escolar = _user(role='Administrador escolar', rbd='200')
    mock_access_attempt.objects.filter.return_value.exists.return_value = False
    ok1, msg1 = SecurityMonitoringService.validate_unblock_permission(admin_escolar, '1.1.1.1')
    assert ok1 is False
    assert 'No tienes permiso' in msg1

    mock_access_attempt.objects.filter.return_value.exists.return_value = True
    ok2, msg2 = SecurityMonitoringService.validate_unblock_permission(admin_escolar, '1.1.1.1')
    assert ok2 is True
    assert msg2 == ''

    no_school = _user(role='Administrador escolar', rbd=None)
    ok3, msg3 = SecurityMonitoringService.validate_unblock_permission(no_school, '1.1.1.1')
    assert ok3 is False
    assert 'escuela asignada' in msg3


@patch('backend.apps.security.services.security_monitoring_service.get_user_model')
@patch('axes.models.AccessAttempt')
def test_unblock_ip_paths(mock_access_attempt, mock_get_user_model):
    user_model = Mock()
    mock_get_user_model.return_value = user_model
    user_model.objects.filter.return_value.values_list.return_value = ['a@test.cl']

    queryset = MagicMock()
    mock_access_attempt.objects.filter.return_value = queryset
    queryset.filter.return_value = queryset
    queryset.delete.side_effect = [(2, {}), (0, {})]

    deleted1, msg1 = SecurityMonitoringService.unblock_ip('2.2.2.2', True, None)
    assert deleted1 == 2
    assert 'desbloqueada exitosamente' in msg1

    deleted2, msg2 = SecurityMonitoringService.unblock_ip('2.2.2.2', False, '123')
    assert deleted2 == 0
    assert 'No se encontraron' in msg2


@patch('backend.apps.security.services.security_monitoring_service.settings')
@patch('backend.apps.security.services.security_monitoring_service.os.path.exists', return_value=True)
@patch('builtins.open')
def test_read_security_log_file(mock_open, _mock_exists, mock_settings):
    mock_settings.BASE_DIR = 'C:/tmp'
    file_handle = Mock()
    file_handle.readlines.return_value = ['l1\n', 'l2\n', 'l3\n']
    mock_open.return_value.__enter__.return_value = file_handle

    result = SecurityMonitoringService.read_security_log_file(limit=2)

    assert result == ['l3\n', 'l2\n']


@patch('backend.apps.security.services.security_monitoring_service.settings')
@patch('backend.apps.security.services.security_monitoring_service.os.path.exists', side_effect=Exception('boom'))
@patch('logging.getLogger')
def test_read_security_log_file_exception(mock_logger, _mock_exists, mock_settings):
    mock_settings.BASE_DIR = 'C:/tmp'

    result = SecurityMonitoringService.read_security_log_file(limit=2)

    assert result == []
    assert mock_logger.return_value.error.called


@patch('axes.models.AccessAttempt')
@patch('backend.apps.security.services.security_monitoring_service.get_user_model')
@patch('backend.apps.security.services.security_monitoring_service.timezone')
def test_get_failed_attempts_and_access_logs_and_blocked_ips(mock_tz, mock_get_user_model, mock_access_attempt):
    mock_tz.now.return_value = datetime(2026, 2, 27, 12, 0, 0)
    user_model = Mock()
    mock_get_user_model.return_value = user_model
    user_model.objects.filter.return_value.values_list.return_value = ['a@test.cl']

    failed_qs = MagicMock()
    mock_access_attempt.objects.filter.return_value = failed_qs
    failed_qs.filter.return_value = failed_qs
    failed_qs.order_by.return_value = failed_qs
    failed_qs.__getitem__.return_value = failed_qs

    result_failed = SecurityMonitoringService.get_failed_attempts(False, '123', 5)
    assert result_failed is failed_qs

    with patch('axes.models.AccessLog') as mock_access_log:
        logs_qs = MagicMock()
        mock_access_log.objects.all.return_value = logs_qs
        logs_qs.filter.return_value = logs_qs
        logs_qs.order_by.return_value = logs_qs
        logs_qs.__getitem__.return_value = logs_qs
        result_logs = SecurityMonitoringService.get_access_logs(False, '123', 10)
        assert result_logs is logs_qs

    with patch('backend.apps.security.services.security_monitoring_service.settings') as mock_settings:
        mock_settings.AXES_FAILURE_LIMIT = 5
        blocked_qs = MagicMock()
        blocked_filtered = MagicMock()
        mock_access_attempt.objects.filter.return_value = blocked_qs
        blocked_qs.filter.return_value = blocked_filtered
        blocked_filtered.values.return_value.distinct.return_value = ['1.1.1.1']
        result_blocked = SecurityMonitoringService.get_blocked_ips(False, '123')
        assert result_blocked == ['1.1.1.1']


@patch('logging.getLogger')
def test_log_unblock_action(mock_logger):
    user = _user(role='Administrador general', rbd='123')

    SecurityMonitoringService.log_unblock_action('1.1.1.1', user, '123', 2)

    assert mock_logger.return_value.info.called

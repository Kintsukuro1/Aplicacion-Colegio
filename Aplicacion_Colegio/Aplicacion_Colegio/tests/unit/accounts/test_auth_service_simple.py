"""Tests simples para AuthService en contrato vigente."""

from unittest.mock import Mock, patch

from backend.apps.accounts.services.auth_service import AuthService


class TestAuthServiceBasic:
    def test_get_client_ip_direct(self):
        request = Mock()
        request.META = {'REMOTE_ADDR': '192.168.1.100'}
        assert AuthService.get_client_ip(request) == '192.168.1.100'

    def test_get_client_ip_with_proxy(self):
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '203.0.113.45, 192.168.1.1',
            'REMOTE_ADDR': '192.168.1.1',
        }
        assert AuthService.get_client_ip(request) == '203.0.113.45'

    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_validate_captcha_disabled(self, mock_settings):
        mock_settings.HCAPTCHA_ENABLED = False
        assert AuthService.validate_captcha('any_token', '127.0.0.1') is None

    @patch('backend.apps.accounts.services.auth_service.security_logger')
    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_validate_captcha_missing(self, mock_settings, mock_logger):
        mock_settings.HCAPTCHA_ENABLED = True

        error = AuthService.validate_captcha('', '127.0.0.1')

        assert error is not None
        assert 'captcha' in error['context']['field']
        mock_logger.warning.assert_called_once()

    @patch('backend.apps.accounts.services.auth_service.security_logger')
    def test_log_login_failure(self, mock_logger):
        AuthService.log_login_failure('test_user', '127.0.0.1', 'Test reason')

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert 'LOGIN FALLIDO' in call_args
        assert 'test_user' in call_args

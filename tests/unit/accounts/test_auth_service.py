"""Tests unitarios para AuthService alineados al contrato actual."""

from unittest.mock import Mock, patch

from django.test import RequestFactory

from backend.apps.accounts.services.auth_service import AuthService


class TestAuthService:
    def test_get_client_ip_direct(self):
        request = RequestFactory().get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        assert AuthService.get_client_ip(request) == '192.168.1.100'

    def test_get_client_ip_with_proxy(self):
        request = RequestFactory().get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.45, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        assert AuthService.get_client_ip(request) == '203.0.113.45'

    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_validate_captcha_disabled(self, mock_settings):
        mock_settings.HCAPTCHA_ENABLED = False
        error = AuthService.validate_captcha('any_token', '127.0.0.1')
        assert error is None

    @patch('backend.apps.accounts.services.auth_service.settings')
    @patch('backend.apps.accounts.services.auth_service.security_logger')
    def test_validate_captcha_missing_response(self, mock_logger, mock_settings):
        mock_settings.HCAPTCHA_ENABLED = True
        error = AuthService.validate_captcha('', '127.0.0.1')

        assert error is not None
        assert 'captcha' in error['context']['message'].lower()
        mock_logger.warning.assert_called_once()

    @patch('backend.apps.accounts.services.auth_service.verify_hcaptcha')
    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_validate_captcha_invalid_token(self, mock_settings, mock_verify):
        mock_settings.HCAPTCHA_ENABLED = True
        mock_verify.return_value = False

        error = AuthService.validate_captcha('invalid_token', '127.0.0.1')

        assert error is not None
        assert 'fallida' in error['context']['message'].lower()

    @patch('backend.apps.accounts.services.auth_service.verify_hcaptcha')
    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_validate_captcha_valid_token(self, mock_settings, mock_verify):
        mock_settings.HCAPTCHA_ENABLED = True
        mock_verify.return_value = True

        error = AuthService.validate_captcha('valid_token', '127.0.0.1')

        assert error is None

    @patch('backend.apps.accounts.services.auth_service.authenticate')
    def test_authenticate_user_success(self, mock_authenticate):
        mock_user = Mock()
        mock_authenticate.return_value = mock_user
        request = RequestFactory().post('/login/')

        user = AuthService.authenticate_user(request, 'admin_test', 'password123')

        assert user == mock_user
        mock_authenticate.assert_called_once_with(request, username='admin_test', password='password123')

    @patch('backend.apps.accounts.services.auth_service.auth_login')
    def test_login_user_no_remember(self, mock_auth_login):
        mock_user = Mock()
        request = RequestFactory().post('/login/')
        request.session = Mock()
        request.session.set_expiry = Mock()

        AuthService.login_user(request, mock_user, remember_me=False)

        mock_auth_login.assert_called_once_with(request, mock_user)
        request.session.set_expiry.assert_called_once_with(0)

    @patch('backend.apps.accounts.services.auth_service.auth_login')
    def test_login_user_with_remember(self, mock_auth_login):
        mock_user = Mock()
        request = RequestFactory().post('/login/')
        request.session = Mock()
        request.session.set_expiry = Mock()

        AuthService.login_user(request, mock_user, remember_me=True)

        mock_auth_login.assert_called_once_with(request, mock_user)
        request.session.set_expiry.assert_called_once_with(1209600)

    @patch('backend.apps.accounts.services.auth_service.auth_logout')
    @patch('backend.apps.accounts.services.auth_service.security_logger')
    def test_logout_user_authenticated(self, mock_logger, mock_auth_logout):
        request = RequestFactory().post('/logout/')
        request.user = Mock(is_authenticated=True, email='admin@test.cl')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        username, was_authenticated = AuthService.logout_user(request)

        assert was_authenticated is True
        assert username == 'admin@test.cl'
        mock_auth_logout.assert_called_once_with(request)
        mock_logger.info.assert_called_once()

    @patch('backend.apps.accounts.services.auth_service.AuthService.login_user')
    @patch('backend.apps.accounts.services.auth_service.authenticate')
    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_perform_login_success(self, mock_settings, mock_authenticate, _mock_login_user):
        mock_settings.HCAPTCHA_ENABLED = False

        mock_user = Mock()
        mock_user.get_full_name.return_value = 'Profe Test'
        mock_user.role = Mock(nombre='Profesor')
        mock_user.email = 'profe@test.cl'
        mock_authenticate.return_value = mock_user

        request = RequestFactory().post('/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        result = AuthService.perform_login(
            request,
            'profe@test.cl',
            'password123',
            '',
            False,
            login_type='staff',
        )

        assert result['success'] is True
        assert result['user'] == mock_user
        assert result['error'] is None

    @patch('backend.apps.accounts.services.auth_service.authenticate')
    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_perform_login_wrong_credentials(self, mock_settings, mock_authenticate):
        mock_settings.HCAPTCHA_ENABLED = False
        mock_authenticate.return_value = None

        request = RequestFactory().post('/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        result = AuthService.perform_login(request, 'wrong', 'wrong', '', False)

        assert result['success'] is False
        assert result['user'] is None
        assert result['error'] is not None
        assert 'incorrectos' in result['error']['context']['message']

    @patch('backend.apps.accounts.services.auth_service.verify_hcaptcha')
    @patch('backend.apps.accounts.services.auth_service.settings')
    def test_perform_login_invalid_captcha(self, mock_settings, mock_verify):
        mock_settings.HCAPTCHA_ENABLED = True
        mock_verify.return_value = False

        request = RequestFactory().post('/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        result = AuthService.perform_login(request, 'admin', 'pass', 'bad_captcha', False)

        assert result['success'] is False
        assert result['error'] is not None
        assert 'captcha' in result['error']['context']['field'].lower()

"""
Tests unitarios para captcha
"""
import pytest
from unittest.mock import Mock, patch
from backend.common.utils.captcha import verify_hcaptcha


class TestVerifyHCaptcha:
    """Tests para la función verify_hcaptcha"""
    
    @patch('backend.common.utils.captcha.settings')
    def test_hcaptcha_deshabilitado(self, mock_settings):
        """Test: Si hCaptcha está deshabilitado, siempre retorna True"""
        mock_settings.HCAPTCHA_ENABLED = False
        
        result = verify_hcaptcha('cualquier_token', '127.0.0.1')
        
        assert result is True
    
    @patch('backend.common.utils.captcha.requests.post')
    @patch('backend.common.utils.captcha.settings')
    def test_hcaptcha_exitoso(self, mock_settings, mock_post):
        """Test: Verificación exitosa de hCaptcha"""
        mock_settings.HCAPTCHA_ENABLED = True
        mock_settings.HCAPTCHA_SECRET = 'secret_key'
        
        # Mock de respuesta exitosa
        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_post.return_value = mock_response
        
        result = verify_hcaptcha('valid_token', '192.168.1.1')
        
        assert result is True
        mock_post.assert_called_once_with(
            'https://hcaptcha.com/siteverify',
            data={
                'secret': 'secret_key',
                'response': 'valid_token',
                'remoteip': '192.168.1.1'
            },
            timeout=5
        )
    
    @patch('backend.common.utils.captcha.requests.post')
    @patch('backend.common.utils.captcha.settings')
    def test_hcaptcha_fallido(self, mock_settings, mock_post):
        """Test: Verificación fallida de hCaptcha"""
        mock_settings.HCAPTCHA_ENABLED = True
        mock_settings.HCAPTCHA_SECRET = 'secret_key'
        
        # Mock de respuesta fallida
        mock_response = Mock()
        mock_response.json.return_value = {'success': False}
        mock_post.return_value = mock_response
        
        result = verify_hcaptcha('invalid_token', '192.168.1.1')
        
        assert result is False
    
    @patch('backend.common.utils.captcha.requests.post')
    @patch('backend.common.utils.captcha.settings')
    def test_hcaptcha_respuesta_sin_success(self, mock_settings, mock_post):
        """Test: Respuesta sin campo 'success' retorna False"""
        mock_settings.HCAPTCHA_ENABLED = True
        mock_settings.HCAPTCHA_SECRET = 'secret_key'
        
        # Mock de respuesta sin 'success'
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        result = verify_hcaptcha('token', '192.168.1.1')
        
        assert result is False
    
    @patch('backend.common.utils.captcha.requests.post')
    @patch('backend.common.utils.captcha.settings')
    @patch('backend.common.utils.captcha.security_logger')
    def test_hcaptcha_error_conexion(self, mock_logger, mock_settings, mock_post):
        """Test: Error de conexión retorna False por seguridad"""
        mock_settings.HCAPTCHA_ENABLED = True
        mock_settings.HCAPTCHA_SECRET = 'secret_key'
        
        # Simular error de conexión
        mock_post.side_effect = Exception('Connection error')
        
        result = verify_hcaptcha('token', '192.168.1.1')
        
        assert result is False
        mock_logger.error.assert_called_once()
    
    @patch('backend.common.utils.captcha.requests.post')
    @patch('backend.common.utils.captcha.settings')
    @patch('backend.common.utils.captcha.security_logger')
    def test_hcaptcha_timeout(self, mock_logger, mock_settings, mock_post):
        """Test: Timeout en la petición retorna False"""
        mock_settings.HCAPTCHA_ENABLED = True
        mock_settings.HCAPTCHA_SECRET = 'secret_key'
        
        # Simular timeout
        import requests
        mock_post.side_effect = requests.Timeout('Request timeout')
        
        result = verify_hcaptcha('token', '192.168.1.1')
        
        assert result is False
        mock_logger.error.assert_called_once()

"""
Utilidades para verificación de hCaptcha
"""
import requests
import logging
from django.conf import settings

security_logger = logging.getLogger('security')


def verify_hcaptcha(token, ip_address):
    """
    Verifica el token de hCaptcha con la API de hCaptcha
    
    Args:
        token (str): Token de hCaptcha recibido del frontend
        ip_address (str): Dirección IP del cliente
        
    Returns:
        bool: True si la verificación es exitosa, False en caso contrario
        
    Notes:
        - Si HCAPTCHA_ENABLED es False en settings, siempre retorna True
        - En caso de error de conexión, retorna False por seguridad
    """
    if not settings.HCAPTCHA_ENABLED:
        return True  # Si está deshabilitado, siempre retorna True
    
    try:
        response = requests.post(
            'https://hcaptcha.com/siteverify',
            data={
                'secret': settings.HCAPTCHA_SECRET,
                'response': token,
                'remoteip': ip_address
            },
            timeout=5
        )
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        security_logger.error(f"Error verificando hCaptcha: {str(e)}")
        return False  # En caso de error, rechazar por seguridad

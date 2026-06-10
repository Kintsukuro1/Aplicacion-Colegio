"""
Servicio de autenticación - Toda la lógica de login/logout
"""
import logging
from typing import Optional, Dict, Any
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.conf import settings
from backend.common.services.policy_service import PolicyService
from backend.common.utils.captcha import verify_hcaptcha
from backend.common.utils.error_response import ErrorResponseBuilder

security_logger = logging.getLogger('security')


class AuthService:
    """
    Servicio para manejar autenticación de usuarios
    Centraliza toda la lógica de login, logout y validaciones de seguridad
    """

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        AuthService.validate(operation, params)
        return AuthService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(AuthService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')
    
    @staticmethod
    def get_client_ip(request):
        """
        Obtiene la IP real del cliente considerando proxies
        
        Args:
            request: HttpRequest de Django
            
        Returns:
            str: Dirección IP del cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def validate_captcha(captcha_response, client_ip) -> Optional[Dict[str, Any]]:
        """
        Valida el captcha si está habilitado
        
        Args:
            captcha_response (str): Respuesta del captcha del cliente
            client_ip (str): IP del cliente
            
        Returns:
            Optional[Dict]: None si válido, Dict con error si inválido
        """
        if not settings.HCAPTCHA_ENABLED:
            return None
        
        if not captcha_response:
            security_logger.warning(
                f"[SEGURIDAD] Intento de login sin captcha - IP: {client_ip}"
            )
            return ErrorResponseBuilder.build('VALIDATION_ERROR', context={
                'field': 'captcha',
                'message': 'Por favor, completa el captcha de seguridad.',
                'client_ip': client_ip
            })
        
        if not verify_hcaptcha(captcha_response, client_ip):
            security_logger.warning(
                f"[SEGURIDAD] Captcha inválido - IP: {client_ip}"
            )
            return ErrorResponseBuilder.build('VALIDATION_ERROR', context={
                'field': 'captcha',
                'message': 'Verificación de captcha fallida. Por favor, intenta nuevamente.',
                'client_ip': client_ip
            })
        
        return None
    
    @staticmethod
    def authenticate_user(request, username, password):
        """
        Autentica un usuario con sus credenciales
        
        Args:
            request: HttpRequest de Django
            username (str): Nombre de usuario o RUT
            password (str): Contraseña
            
        Returns:
            User or None: Usuario autenticado o None si falló
        """
        return authenticate(request, username=username, password=password)
    
    @staticmethod
    def login_user(request, user, remember_me=False):
        """
        Realiza el login del usuario y configura la sesión
        
        Args:
            request: HttpRequest de Django
            user: Usuario a loguear
            remember_me (bool): Si True, la sesión dura 2 semanas. Si False, expira al cerrar navegador
            
        Returns:
            None
        """
        auth_login(request, user)
        
        # Configurar duración de sesión
        if not remember_me:
            # Sesión expira al cerrar el navegador
            request.session.set_expiry(0)
        else:
            # Sesión dura 2 semanas
            request.session.set_expiry(1209600)  # 14 días en segundos
    
    @staticmethod
    def log_login_success(username, user, client_ip, remember_me):
        """
        Registra un login exitoso en los logs de seguridad
        
        Args:
            username (str): Username usado para login
            user: Usuario que se logueó
            client_ip (str): IP del cliente
            remember_me (bool): Si se activó recordar sesión
        """
        security_logger.info(
            f"[LOGIN EXITOSO] Usuario: {username} ({user.get_full_name()}), "
            f"Rol: {user.role.nombre if hasattr(user, 'role') and user.role else 'N/A'}, "
            f"IP: {client_ip}, Recordar sesión: {remember_me}"
        )
    
    @staticmethod
    def log_login_failure(username, client_ip, reason="Credenciales incorrectas"):
        """
        Registra un intento de login fallido
        
        Args:
            username (str): Username que intentó login
            client_ip (str): IP del cliente
            reason (str): Razón del fallo
        """
        security_logger.warning(
            f"[LOGIN FALLIDO] Usuario: {username}, IP: {client_ip}, Motivo: {reason}"
        )
    
    @staticmethod
    def logout_user(request):
        """
        Cierra la sesión del usuario y registra el evento
        
        Args:
            request: HttpRequest de Django
            
        Returns:
            tuple: (username: str, was_authenticated: bool)
        """
        was_authenticated = request.user.is_authenticated
        username = None
        
        if was_authenticated:
            username = request.user.email if hasattr(request.user, 'email') else str(request.user)
            client_ip = AuthService.get_client_ip(request)
            
            # Log del logout
            security_logger.info(
                f"[LOGOUT] Usuario: {username}, IP: {client_ip}"
            )
            
            # Realizar logout
            auth_logout(request)
        
        return username, was_authenticated
    
    @staticmethod
    def _user_login_scopes(user) -> tuple[bool, bool]:
        """Deriva alcance staff / estudiante-apoderado por capabilities."""
        has_staff_scope = (
            PolicyService.has_capability(user, 'SYSTEM_ADMIN')
            or PolicyService.has_capability(user, 'SYSTEM_CONFIGURE')
            or PolicyService.has_capability(user, 'DASHBOARD_VIEW_SCHOOL')
            or PolicyService.has_capability(user, 'TEACHER_VIEW')
            or PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE')
            or PolicyService.has_capability(user, 'USER_VIEW')
        )
        has_student_scope = (
            PolicyService.has_capability(user, 'DASHBOARD_VIEW_SELF')
            and not has_staff_scope
        )
        return has_staff_scope, has_student_scope

    @staticmethod
    def resolve_login_scope(user) -> Optional[str]:
        """
        Determina el portal correcto tras login unificado.

        Returns:
            'staff', 'student' o None si el usuario no tiene alcance válido.
        """
        has_staff_scope, has_student_scope = AuthService._user_login_scopes(user)
        if has_staff_scope:
            return 'staff'
        if has_student_scope:
            return 'student'
        return None

    @staticmethod
    def validate_role_for_login_type(user, login_type) -> Optional[Dict[str, Any]]:
        """
        Valida que el rol del usuario sea compatible con el tipo de login que está usando
        
        Args:
            user: Usuario autenticado
            login_type (str): 'staff', 'student' o 'unified'
            
        Returns:
            Optional[Dict]: None si válido, Dict con error si inválido
        """
        if not hasattr(user, 'role') or user.role is None:
            return ErrorResponseBuilder.build('INVALID_STATE', context={
                'entity': 'User',
                'field': 'role',
                'message': 'Usuario sin rol asignado. Contacta al administrador.',
                'user_id': user.id
            })
        
        user_role = user.role.nombre
        has_staff_scope, has_student_scope = AuthService._user_login_scopes(user)

        if login_type == 'unified':
            if has_staff_scope or has_student_scope:
                return None
            security_logger.warning(
                f"[SEGURIDAD] Usuario sin alcance de portal - Usuario: {user.email}, Rol: {user_role}"
            )
            return ErrorResponseBuilder.build('PERMISSION_DENIED', context={
                'user_role': user_role,
                'required_scope': 'unified',
                'login_type': login_type,
                'message': 'Tu cuenta no tiene permisos para acceder al portal. Contacta al administrador.',
            })

        if login_type == 'staff':
            if not has_staff_scope:
                security_logger.warning(
                    f"[SEGURIDAD] Intento de acceso de {user_role} al portal de staff - Usuario: {user.email}"
                )
                return ErrorResponseBuilder.build('PERMISSION_DENIED', context={
                    'user_role': user_role,
                    'required_scope': 'staff',
                    'login_type': login_type,
                    'message': 'Acceso denegado. Este portal es solo para personal académico.'
                })
        elif login_type == 'student':
            if not has_student_scope:
                security_logger.warning(
                    f"[SEGURIDAD] Intento de acceso de {user_role} al portal de estudiantes - Usuario: {user.email}"
                )
                return ErrorResponseBuilder.build('PERMISSION_DENIED', context={
                    'user_role': user_role,
                    'required_scope': 'student',
                    'login_type': login_type,
                    'message': 'Acceso denegado. Este portal es solo para estudiantes y apoderados.'
                })
        
        return None
    
    @staticmethod
    def perform_login(request, username, password, captcha_response, remember_me=False, login_type='student'):
        """
        Método principal que orquesta todo el proceso de login
        
        Args:
            request: HttpRequest de Django
            username (str): Username o RUT
            password (str): Contraseña
            captcha_response (str): Respuesta del captcha
            remember_me (bool): Recordar sesión
            login_type (str): 'staff', 'student' o 'unified' (detecta portal automáticamente)
            
        Returns:
            dict: {
                'success': bool,
                'user': User or None,
                'error': Dict or None  # ErrorResponseBuilder dict si hay error
            }
        """
        client_ip = AuthService.get_client_ip(request)
        
        # 1. Validar captcha
        captcha_error = AuthService.validate_captcha(captcha_response, client_ip)
        if captcha_error:
            return {
                'success': False,
                'user': None,
                'error': captcha_error
            }
        
        # 2. Autenticar usuario
        user = AuthService.authenticate_user(request, username, password)
        
        if user is not None:
            # 3. Validar que el rol sea compatible con el tipo de login
            role_error = AuthService.validate_role_for_login_type(user, login_type)
            if role_error:
                role_name = user.role.nombre if getattr(user, 'role', None) else 'Sin rol'
                AuthService.log_login_failure(username, client_ip, reason=f"Rol incompatible ({role_name}) para login tipo {login_type}")
                return {
                    'success': False,
                    'user': None,
                    'error': role_error
                }
            
            # 4. Login exitoso
            AuthService.login_user(request, user, remember_me)
            AuthService.log_login_success(username, user, client_ip, remember_me)
            
            return {
                'success': True,
                'user': user,
                'error': None
            }
        else:
            # 5. Login fallido
            AuthService.log_login_failure(username, client_ip)
            
            error = ErrorResponseBuilder.build('AUTHENTICATION_FAILED', context={
                'message': 'Usuario o contraseña incorrectos.',
                'username': username,
                'client_ip': client_ip
            })
            
            return {
                'success': False,
                'user': None,
                'error': error
            }

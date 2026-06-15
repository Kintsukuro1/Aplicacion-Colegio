"""
Servicio para monitoreo y gestión de seguridad del sistema.

FASE 15: Extracción de lógica de monitoreo de seguridad.
Gestión de intentos fallidos, IPs bloqueadas y logs de acceso.
"""

import os
from datetime import timedelta
from typing import List, Dict, Tuple, Optional
from django.conf import settings
from django.utils import timezone
from django.db.models import QuerySet
from django.contrib.auth import get_user_model

from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService


class SecurityMonitoringService:
    """
    Servicio para monitoreo y gestión de seguridad.
    
    Responsabilidades:
    - Validar permisos de acceso al monitoreo
    - Obtener intentos fallidos de autenticación
    - Obtener logs de acceso
    - Identificar IPs bloqueadas
    - Leer logs de archivos
    - Calcular estadísticas de seguridad
    - Desbloquear IPs
    
    Patrón: Service Layer con métodos estáticos
    """

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        SecurityMonitoringService.validate(operation, params)
        return SecurityMonitoringService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(SecurityMonitoringService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')
    
    # ========================================================================
    # SECCIÓN 1: VALIDACIÓN DE PERMISOS
    # ========================================================================
    
    @staticmethod
    def validate_monitoring_access(user) -> Tuple[bool, bool]:
        """
        Valida si el usuario puede acceder al monitoreo de seguridad.
        
        Permisos:
        - Administrador general: acceso total
        - Administrador escolar: acceso filtrado por su escuela
        - Otros roles: sin acceso
        
        Args:
            user: Usuario solicitante
        
        Returns:
            Tuple[bool, bool]: (tiene_acceso, es_admin_general)
        """
        if not user:
            return (False, False)

        can_view_monitoring = PolicyService.has_capability(user, 'AUDIT_VIEW')
        if not can_view_monitoring:
            return (False, False)

        is_admin_general = PolicyService.has_capability(user, 'SYSTEM_ADMIN')
        return (True, is_admin_general)
    
    @staticmethod
    def get_user_school_info(user) -> Dict[str, Optional[str]]:
        """
        Obtiene información de la escuela del usuario.
        
        Args:
            user: Usuario
        
        Returns:
            Dict con rbd_colegio y nombre_colegio
        """
        from backend.apps.institucion.models import Colegio
        
        escuela_rbd = user.rbd_colegio
        escuela_nombre = 'Sistema'
        
        if escuela_rbd:
            try:
                colegio = Colegio.objects.get(rbd=escuela_rbd)
                escuela_nombre = colegio.nombre
            except Colegio.DoesNotExist:
                pass
        
        return {
            'rbd_colegio': escuela_rbd,
            'nombre_colegio': escuela_nombre
        }
    
    # ========================================================================
    # SECCIÓN 2: OBTENCIÓN DE DATOS DE SEGURIDAD
    # ========================================================================
    
    @staticmethod
    def get_failed_attempts(
        es_admin_general: bool,
        escuela_rbd: Optional[str],
        limit: int = 50
    ) -> QuerySet:
        """
        Obtiene intentos fallidos de autenticación de las últimas 24 horas.
        
        Args:
            es_admin_general: Si es administrador general
            escuela_rbd: RBD de la escuela (para filtrado)
            limit: Número máximo de registros
        
        Returns:
            QuerySet de AccessAttempt
        """
        from axes.models import AccessAttempt
        User = get_user_model()
        
        # Últimas 24 horas
        hace_24h = timezone.now() - timedelta(hours=24)
        
        intentos = AccessAttempt.objects.filter(
            attempt_time__gte=hace_24h
        )
        
        # Filtrar por escuela si es admin escolar
        if not es_admin_general and escuela_rbd:
            usuarios_escuela = User.objects.filter(
                rbd_colegio=escuela_rbd
            ).values_list('email', flat=True)
            intentos = intentos.filter(username__in=usuarios_escuela)
        
        return intentos.order_by('-attempt_time')[:limit]
    
    @staticmethod
    def get_access_logs(
        es_admin_general: bool,
        escuela_rbd: Optional[str],
        limit: int = 100
    ) -> QuerySet:
        """
        Obtiene logs de acceso al sistema.
        
        Args:
            es_admin_general: Si es administrador general
            escuela_rbd: RBD de la escuela (para filtrado)
            limit: Número máximo de registros
        
        Returns:
            QuerySet de AccessLog
        """
        from axes.models import AccessLog
        User = get_user_model()
        
        logs = AccessLog.objects.all()
        
        # Filtrar por escuela si es admin escolar
        if not es_admin_general and escuela_rbd:
            usuarios_escuela = User.objects.filter(
                rbd_colegio=escuela_rbd
            ).values_list('email', flat=True)
            logs = logs.filter(username__in=usuarios_escuela)
        
        return logs.order_by('-attempt_time')[:limit]
    
    @staticmethod
    def get_blocked_ips(
        es_admin_general: bool,
        escuela_rbd: Optional[str]
    ) -> QuerySet:
        """
        Obtiene IPs actualmente bloqueadas.
        
        Una IP se considera bloqueada cuando tiene intentos fallidos >= AXES_FAILURE_LIMIT.
        
        Args:
            es_admin_general: Si es administrador general
            escuela_rbd: RBD de la escuela (para filtrado)
        
        Returns:
            QuerySet de IPs bloqueadas (distinct)
        """
        from axes.models import AccessAttempt
        User = get_user_model()
        
        ips_bloqueadas = AccessAttempt.objects.filter(
            failures_since_start__gte=settings.AXES_FAILURE_LIMIT
        )
        
        # Filtrar por escuela si es admin escolar
        if not es_admin_general and escuela_rbd:
            usuarios_escuela = User.objects.filter(
                rbd_colegio=escuela_rbd
            ).values_list('email', flat=True)
            ips_bloqueadas = ips_bloqueadas.filter(username__in=usuarios_escuela)
        
        return ips_bloqueadas.values('ip_address').distinct()
    
    @staticmethod
    def read_security_log_file(limit: int = 50) -> List[str]:
        """
        Lee las últimas líneas del archivo de log de seguridad.
        
        Args:
            limit: Número de líneas a leer
        
        Returns:
            Lista de líneas del log (en orden inverso)
        """
        logs_archivo = []
        
        try:
            log_path = os.path.join(settings.BASE_DIR, 'logs', 'security.log')
            
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    logs_archivo = lines[-limit:]
                    logs_archivo.reverse()
        except Exception as e:
            # Log el error pero retornar lista vacía
            import logging
            logger = logging.getLogger('security')
            logger.error(f"Error leyendo log de seguridad: {str(e)}")
        
        return logs_archivo
    
    # ========================================================================
    # SECCIÓN 3: CÁLCULO DE ESTADÍSTICAS
    # ========================================================================
    
    @staticmethod
    def calculate_statistics(
        intentos_fallidos: QuerySet,
        ips_bloqueadas: QuerySet
    ) -> Dict[str, int]:
        """
        Calcula estadísticas de seguridad.
        
        Args:
            intentos_fallidos: QuerySet de intentos fallidos
            ips_bloqueadas: QuerySet de IPs bloqueadas
        
        Returns:
            Dict con total_intentos_fallidos y total_ips_bloqueadas
        """
        return {
            'total_intentos_fallidos': intentos_fallidos.count(),
            'total_ips_bloqueadas': ips_bloqueadas.count()
        }
    
    @staticmethod
    def get_axes_settings() -> Dict[str, any]:
        """
        Obtiene configuración de django-axes desde settings.
        
        Returns:
            Dict con AXES_FAILURE_LIMIT y AXES_COOLOFF_TIME
        """
        return {
            'failure_limit': settings.AXES_FAILURE_LIMIT,
            'cooloff_time': settings.AXES_COOLOFF_TIME
        }
    
    # ========================================================================
    # SECCIÓN 4: DESBLOQUEO DE IPs
    # ========================================================================
    
    @staticmethod
    def validate_unblock_permission(
        user,
        ip_address: str
    ) -> Tuple[bool, str]:
        """
        Valida si el usuario puede desbloquear una IP específica.
        
        Args:
            user: Usuario solicitante
            ip_address: IP a desbloquear
        
        Returns:
            Tuple[bool, str]: (puede_desbloquear, mensaje_error)
        """
        if not user:
            return (False, "No tienes permiso para esta acción")

        has_audit_access = PolicyService.has_capability(user, 'AUDIT_VIEW')
        if not has_audit_access:
            return (False, "No tienes permiso para esta acción")

        is_admin_general = PolicyService.has_capability(user, 'SYSTEM_ADMIN')
        if is_admin_general:
            return (True, "")
        
        # Admin escolar: verificar que la IP pertenezca a usuarios de su escuela
        from axes.models import AccessAttempt
        User = get_user_model()
        
        escuela_rbd = user.rbd_colegio
        
        if not escuela_rbd:
            return (False, "No tienes una escuela asignada")
        
        # Verificar que existan intentos de usuarios de la escuela con esa IP
        usuarios_escuela = User.objects.filter(
            rbd_colegio=escuela_rbd
        ).values_list('email', flat=True)
        
        intentos_escuela = AccessAttempt.objects.filter(
            ip_address=ip_address,
            username__in=usuarios_escuela
        )
        
        if not intentos_escuela.exists():
            return (
                False,
                "No tienes permiso para desbloquear esta IP. "
                "Solo puedes desbloquear IPs de usuarios de tu escuela."
            )
        
        return (True, "")
    
    @staticmethod
    def unblock_ip(
        ip_address: str,
        es_admin_general: bool,
        escuela_rbd: Optional[str]
    ) -> Tuple[int, str]:
        """
        Desbloquea una IP eliminando sus intentos fallidos.
        
        Args:
            ip_address: IP a desbloquear
            es_admin_general: Si es administrador general
            escuela_rbd: RBD de la escuela (para filtrado)
        
        Returns:
            Tuple[int, str]: (registros_eliminados, mensaje)
        """
        from axes.models import AccessAttempt
        User = get_user_model()
        
        intentos_a_eliminar = AccessAttempt.objects.filter(ip_address=ip_address)
        
        # Si es admin escolar, filtrar por usuarios de su escuela
        if not es_admin_general and escuela_rbd:
            usuarios_escuela = User.objects.filter(
                rbd_colegio=escuela_rbd
            ).values_list('email', flat=True)
            intentos_a_eliminar = intentos_a_eliminar.filter(
                username__in=usuarios_escuela
            )
        
        deleted_count = intentos_a_eliminar.delete()[0]
        
        if deleted_count > 0:
            mensaje = f"✓ IP {ip_address} desbloqueada exitosamente ({deleted_count} registros eliminados)"
        else:
            mensaje = f"No se encontraron registros bloqueados para la IP {ip_address}"
        
        return (deleted_count, mensaje)
    
    @staticmethod
    def log_unblock_action(
        ip_address: str,
        user,
        escuela_rbd: Optional[str],
        deleted_count: int
    ):
        """
        Registra la acción de desbloqueo en el log de seguridad.
        
        Args:
            ip_address: IP desbloqueada
            user: Usuario que realizó la acción
            escuela_rbd: RBD de la escuela
            deleted_count: Número de registros eliminados
        """
        import logging
        logger = logging.getLogger('security')
        
        logger.info(
            f"IP desbloqueada manualmente - IP: {ip_address}, "
            f"Por: {user.username}, "
            f"Escuela: {escuela_rbd or 'Sistema'}, "
            f"Registros eliminados: {deleted_count}"
        )

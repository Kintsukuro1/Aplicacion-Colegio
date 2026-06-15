"""
Vistas orchestradoras para monitoreo y gestión de seguridad.

FASE 15: Vistas refactorizadas usando arquitectura limpia.
Responsabilidad: Coordinación HTTP, sin lógica de negocio.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django_ratelimit.decorators import ratelimit
from datetime import datetime

from backend.apps.security.services import SecurityMonitoringService


@login_required()
@never_cache
def monitoreo_seguridad(request):
    """
    Vista orchestradora para monitoreo de seguridad del sistema.
    
    Muestra:
    - Intentos fallidos de autenticación (últimas 24h)
    - Logs de acceso al sistema
    - IPs bloqueadas actualmente
    - Logs del archivo de seguridad
    - Estadísticas de seguridad
    
    Flujo en 11 pasos:
    -------------------
    PASO 1: Validar permisos de acceso
    PASO 2: Obtener información de la escuela del usuario
    PASO 3: Obtener intentos fallidos de autenticación
    PASO 4: Obtener logs de acceso
    PASO 5: Obtener IPs bloqueadas
    PASO 6: Calcular estadísticas
    PASO 7: Leer logs del archivo
    PASO 8: Obtener configuración de axes
    PASO 9: Determinar sidebar según rol
    PASO 10: Preparar contexto completo
    PASO 11: Renderizar template
    
    Permisos:
    ---------
    - Administrador general: ve todos los datos del sistema
    - Administrador escolar: ve solo datos de su escuela
    - Otros roles: sin acceso (redirect a dashboard)
    
    Args:
        request: HttpRequest
    
    Returns:
        HttpResponse: Template con datos de monitoreo o redirect
    
    Template:
        admin_escolar/monitoreo_seguridad.html
    """
    
    # ========================================================================
    # PASO 1: Validar permisos de acceso
    # ========================================================================
    tiene_acceso, es_admin_general = SecurityMonitoringService.validate_monitoring_access(
        request.user
    )
    
    if not tiene_acceso:
        messages.error(request, "No tienes permiso para acceder a esta página")
        return redirect('dashboard')
    
    # ========================================================================
    # PASO 2: Obtener información de la escuela del usuario
    # ========================================================================
    escuela_info = SecurityMonitoringService.get_user_school_info(request.user)
    escuela_rbd = escuela_info['rbd_colegio']
    escuela_nombre = escuela_info['nombre_colegio']
    
    # ========================================================================
    # PASO 3: Obtener intentos fallidos de autenticación
    # ========================================================================
    intentos_fallidos = SecurityMonitoringService.get_failed_attempts(
        es_admin_general=es_admin_general,
        escuela_rbd=escuela_rbd,
        limit=50
    )
    
    # ========================================================================
    # PASO 4: Obtener logs de acceso
    # ========================================================================
    logs_acceso = SecurityMonitoringService.get_access_logs(
        es_admin_general=es_admin_general,
        escuela_rbd=escuela_rbd,
        limit=100
    )
    
    # ========================================================================
    # PASO 5: Obtener IPs bloqueadas
    # ========================================================================
    ips_bloqueadas = SecurityMonitoringService.get_blocked_ips(
        es_admin_general=es_admin_general,
        escuela_rbd=escuela_rbd
    )
    
    # ========================================================================
    # PASO 6: Calcular estadísticas
    # ========================================================================
    estadisticas = SecurityMonitoringService.calculate_statistics(
        intentos_fallidos=intentos_fallidos,
        ips_bloqueadas=ips_bloqueadas
    )
    
    # ========================================================================
    # PASO 7: Leer logs del archivo
    # ========================================================================
    logs_archivo = SecurityMonitoringService.read_security_log_file(limit=50)
    
    # ========================================================================
    # PASO 8: Obtener configuración de axes
    # ========================================================================
    axes_config = SecurityMonitoringService.get_axes_settings()
    
    # ========================================================================
    # PASO 9: Determinar sidebar según rol
    # ========================================================================
    rol = 'admin' if es_admin_general else 'admin_escolar'
    
    sidebar_map = {
        'admin': 'sidebars/sidebar_admin.html',
        'admin_escolar': 'sidebars/sidebar_admin_escuela.html',
    }
    
    # ========================================================================
    # PASO 10: Preparar contexto completo
    # ========================================================================
    context = {
        # Datos de seguridad
        'intentos_fallidos': intentos_fallidos,
        'logs_acceso': logs_acceso,
        'ips_bloqueadas': ips_bloqueadas,
        'total_intentos_fallidos': estadisticas['total_intentos_fallidos'],
        'total_ips_bloqueadas': estadisticas['total_ips_bloqueadas'],
        'logs_archivo': logs_archivo,
        
        # Configuración de axes
        'axes_failure_limit': axes_config['failure_limit'],
        'axes_cooloff_time': axes_config['cooloff_time'],
        
        # Información del usuario y escuela
        'es_admin_general': es_admin_general,
        'rol': rol,
        'nombre_usuario': request.user.get_full_name(),
        'id_usuario': request.user.id,
        'escuela_rbd': escuela_rbd,
        'escuela_nombre': escuela_nombre,
        'sidebar_template': sidebar_map.get(rol, 'sidebars/sidebar_admin.html'),
        'year': datetime.now().year,
        'pagina_actual': 'monitoreo_seguridad',
    }
    
    # ========================================================================
    # PASO 11: Renderizar template
    # ========================================================================
    return render(request, 'admin_escolar/monitoreo_seguridad.html', context)


@login_required()
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def desbloquear_ip(request):
    """
    Vista orchestradora para desbloquear IPs bloqueadas por django-axes.
    
    Permite a administradores desbloquear IPs que han sido bloqueadas
    por múltiples intentos fallidos de autenticación.
    
    Flujo en 8 pasos:
    ------------------
    PASO 1: Validar método POST
    PASO 2: Validar permisos básicos
    PASO 3: Obtener IP del formulario
    PASO 4: Validar permisos específicos para la IP
    PASO 5: Desbloquear IP usando servicio
    PASO 6: Registrar acción en log de seguridad
    PASO 7: Mostrar mensaje de resultado
    PASO 8: Redirigir a monitoreo
    
    Permisos:
    ---------
    - Administrador general: puede desbloquear cualquier IP
    - Administrador escolar: solo IPs de usuarios de su escuela
    - Otros roles: sin acceso
    
    Rate Limit:
    -----------
    10 intentos por minuto por usuario
    
    Args:
        request: HttpRequest (debe ser POST)
    
    Returns:
        HttpResponse: Redirect a monitoreo_seguridad
    
    Example:
        POST /seguridad/desbloquear-ip/
        Form data: ip_address=192.168.1.100
    """
    
    # ========================================================================
    # PASO 1: Validar método POST
    # ========================================================================
    if request.method != 'POST':
        return redirect('monitoreo_seguridad')
    
    # ========================================================================
    # PASO 2: Validar permisos básicos
    # ========================================================================
    tiene_acceso, es_admin_general = SecurityMonitoringService.validate_monitoring_access(
        request.user
    )
    
    if not tiene_acceso:
        messages.error(request, "No tienes permiso para esta acción")
        return redirect('dashboard')
    
    # ========================================================================
    # PASO 3: Obtener IP del formulario
    # ========================================================================
    ip_address = request.POST.get('ip_address')
    
    if not ip_address:
        messages.error(request, "IP no especificada")
        return redirect('monitoreo_seguridad')
    
    # ========================================================================
    # PASO 4: Validar permisos específicos para la IP
    # ========================================================================
    puede_desbloquear, mensaje_error = SecurityMonitoringService.validate_unblock_permission(
        user=request.user,
        ip_address=ip_address
    )
    
    if not puede_desbloquear:
        messages.error(request, mensaje_error)
        return redirect('monitoreo_seguridad')
    
    # ========================================================================
    # PASO 5: Desbloquear IP usando servicio
    # ========================================================================
    escuela_info = SecurityMonitoringService.get_user_school_info(request.user)
    escuela_rbd = escuela_info['rbd_colegio']
    
    deleted_count, mensaje_resultado = SecurityMonitoringService.unblock_ip(
        ip_address=ip_address,
        es_admin_general=es_admin_general,
        escuela_rbd=escuela_rbd
    )
    
    # ========================================================================
    # PASO 6: Registrar acción en log de seguridad
    # ========================================================================
    if deleted_count > 0:
        SecurityMonitoringService.log_unblock_action(
            ip_address=ip_address,
            user=request.user,
            escuela_rbd=escuela_rbd,
            deleted_count=deleted_count
        )
    
    # ========================================================================
    # PASO 7: Mostrar mensaje de resultado
    # ========================================================================
    if deleted_count > 0:
        messages.success(request, mensaje_resultado)
    else:
        messages.warning(request, mensaje_resultado)
    
    # ========================================================================
    # PASO 8: Redirigir a monitoreo
    # ========================================================================
    return redirect('monitoreo_seguridad')


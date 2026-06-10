"""
Views de seguridad — Semana 7-8.

Endpoints para administradores:
1. Dashboard de seguridad (estadísticas, intentos, IPs bloqueadas)
2. Gestión de sesiones activas (ver y revocar)
3. Auditoría de acceso a datos sensibles (historial)
4. Desbloqueo de IPs
"""
import logging

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.security.models import ActiveSession, PasswordHistory
from backend.apps.security.services.security_hardening_service import (
    audit_sensitive_access,
    check_password_reuse,
    record_password_change,
)
from backend.apps.security.services.security_monitoring_service import SecurityMonitoringService
from backend.common.services.policy_service import PolicyService

logger = logging.getLogger('security')


def _is_admin(user):
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN') or \
        PolicyService.has_capability(user, 'AUDIT_VIEW')


def _get_ip(request):
    return request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
        or request.META.get('REMOTE_ADDR', '')


# ═══════════════════════════════════════════════
# 1. DASHBOARD DE SEGURIDAD
# ═══════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def security_dashboard(request):
    """
    GET /api/seguridad/dashboard/
    Panel de seguridad para administradores.
    Muestra: intentos fallidos 24h, IPs bloqueadas, sesiones activas, auditoría reciente.
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores pueden acceder al panel de seguridad.')

    has_access, is_global = SecurityMonitoringService.validate_monitoring_access(user)
    if not has_access:
        raise PermissionDenied('Sin permisos de monitoreo.')

    school_info = SecurityMonitoringService.get_user_school_info(user)
    school_rbd = school_info['rbd_colegio']

    # Intentos fallidos últimas 24h
    failed = SecurityMonitoringService.get_failed_attempts(is_global, school_rbd, limit=20)
    blocked = SecurityMonitoringService.get_blocked_ips(is_global, school_rbd)
    stats = SecurityMonitoringService.calculate_statistics(failed, blocked)

    # Sesiones activas
    if is_global:
        sessions_count = ActiveSession.objects.filter(is_active=True).count()
    else:
        from backend.apps.accounts.models import User
        school_users = User.objects.filter(rbd_colegio=school_rbd).values_list('id', flat=True)
        sessions_count = ActiveSession.objects.filter(
            user_id__in=school_users, is_active=True
        ).count()

    # Auditoría de datos sensibles (últimas 24h)
    from backend.apps.auditoria.models import AuditoriaEvento
    audit_qs = AuditoriaEvento.objects.filter(
        accion='ACCESO_DATOS_SENSIBLES',
        fecha_hora__gte=timezone.now() - timezone.timedelta(hours=24),
    )
    if not is_global:
        audit_qs = audit_qs.filter(colegio_rbd=str(school_rbd))
    sensitive_access_count = audit_qs.count()

    # Axes config
    axes_config = SecurityMonitoringService.get_axes_settings()

    return Response({
        'colegio': school_info['nombre_colegio'],
        'es_admin_global': is_global,
        'intentos_fallidos_24h': stats['total_intentos_fallidos'],
        'ips_bloqueadas': stats['total_ips_bloqueadas'],
        'sesiones_activas': sessions_count,
        'accesos_datos_sensibles_24h': sensitive_access_count,
        'configuracion': {
            'max_intentos': axes_config['failure_limit'],
            'cooloff_horas': axes_config['cooloff_time'],
            'historial_passwords': 5,
        },
        'intentos_recientes': [
            {
                'username': a.username,
                'ip': a.ip_address,
                'timestamp': a.attempt_time.isoformat(),
                'failures': a.failures_since_start,
            }
            for a in failed[:10]
        ],
        'ips_bloqueadas_lista': [
            ip['ip_address'] for ip in blocked
        ],
    })


# ═══════════════════════════════════════════════
# 2. GESTIÓN DE SESIONES ACTIVAS
# ═══════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_sessions(request):
    """
    GET /api/seguridad/mis-sesiones/
    Lista las sesiones activas del usuario actual.
    """
    sessions = ActiveSession.objects.filter(
        user=request.user, is_active=True
    ).order_by('-last_activity')

    current_ip = _get_ip(request)

    return Response({
        'sesiones': [
            {
                'id': s.id,
                'ip': s.ip_address,
                'dispositivo': s.get_device_type_display(),
                'user_agent': s.user_agent[:100],
                'ultima_actividad': s.last_activity.isoformat(),
                'creada': s.created_at.isoformat(),
                'es_sesion_actual': s.ip_address == current_ip,
            }
            for s in sessions
        ],
        'total': sessions.count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_sessions_list(request):
    """
    GET /api/seguridad/sesiones-activas/
    Lista sesiones activas para admins (global o por colegio).
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores pueden ver sesiones activas.')

    has_access, is_global = SecurityMonitoringService.validate_monitoring_access(user)
    if not has_access:
        raise PermissionDenied('Sin permisos de monitoreo.')

    qs = ActiveSession.objects.filter(is_active=True).select_related('user__role').order_by('-last_activity')

    if not is_global:
        school_rbd = getattr(user, 'rbd_colegio', None)
        qs = qs.filter(user__rbd_colegio=school_rbd)

    return Response({
        'total': qs.count(),
        'sesiones': [
            {
                'id': s.id,
                'user_id': s.user_id,
                'user_email': s.user.email,
                'user_nombre': s.user.get_full_name() or s.user.email,
                'user_rol': getattr(getattr(s.user, 'role', None), 'nombre', ''),
                'colegio_rbd': s.user.rbd_colegio,
                'ip': s.ip_address,
                'dispositivo': s.get_device_type_display(),
                'user_agent': s.user_agent[:140],
                'ultima_actividad': s.last_activity.isoformat(),
                'creada': s.created_at.isoformat(),
            }
            for s in qs[:200]
        ],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_session(request, session_id):
    """
    POST /api/seguridad/sesiones/<id>/revocar/
    Revoca (cierra remotamente) una sesión activa.
    """
    success = ActiveSession.revoke_session(request.user, session_id)
    if success:
        return Response({'detail': 'Sesión revocada exitosamente.'})
    raise ValidationError({'session_id': 'Sesión no encontrada o ya inactiva.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_all_other_sessions(request):
    """
    POST /api/seguridad/sesiones/revocar-otras/
    Revoca todas las sesiones excepto la actual.
    """
    current_ip = _get_ip(request)
    other_sessions = ActiveSession.objects.filter(
        user=request.user, is_active=True
    ).exclude(ip_address=current_ip)

    count = other_sessions.count()
    for session in other_sessions:
        ActiveSession.revoke_session(request.user, session.id)

    return Response({
        'detail': f'{count} sesiones revocadas.',
        'revocadas': count,
    })


# ═══════════════════════════════════════════════
# 3. AUDITORÍA DE DATOS SENSIBLES
# ═══════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sensitive_data_audit_log(request):
    """
    GET /api/seguridad/auditoria-datos-sensibles/
    Lista los accesos a datos sensibles (solo admins).

    Query params: ?dias=7&modelo=PerfilEstudiante
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores acceden a esta auditoría.')

    has_access, is_global = SecurityMonitoringService.validate_monitoring_access(user)
    school_rbd = getattr(user, 'rbd_colegio', None)

    from backend.apps.auditoria.models import AuditoriaEvento

    dias = int(request.query_params.get('dias', 7))
    fecha_desde = timezone.now() - timezone.timedelta(days=dias)

    qs = AuditoriaEvento.objects.filter(
        accion='ACCESO_DATOS_SENSIBLES',
        fecha_hora__gte=fecha_desde,
    ).order_by('-fecha_hora')

    if not is_global:
        qs = qs.filter(colegio_rbd=str(school_rbd))

    modelo = request.query_params.get('modelo')
    if modelo:
        qs = qs.filter(metadata__modelo=modelo)

    results = []
    for evento in qs[:100]:
        datos = evento.metadata or {}
        results.append({
            'id': evento.id,
            'timestamp': evento.fecha_hora.isoformat(),
            'usuario': evento.usuario.email if evento.usuario else evento.usuario_email or 'N/A',
            'rol': evento.usuario_rol or '',
            'modelo': datos.get('modelo', ''),
            'object_id': datos.get('object_id', ''),
            'campos': datos.get('campos_accedidos', []),
            'ip': evento.ip_address,
        })

    return Response({
        'periodo_dias': dias,
        'total': len(results),
        'eventos': results,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def password_history_list(request):
    """
    GET /api/seguridad/password-history/
    Lista historial de cambios de contraseña para admins.
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores acceden al historial de contraseñas.')

    has_access, is_global = SecurityMonitoringService.validate_monitoring_access(user)
    if not has_access:
        raise PermissionDenied('Sin permisos de monitoreo.')

    qs = PasswordHistory.objects.select_related('user__role').order_by('-created_at')
    if not is_global:
        school_rbd = getattr(user, 'rbd_colegio', None)
        qs = qs.filter(user__rbd_colegio=school_rbd)

    return Response({
        'total': qs.count(),
        'entries': [
            {
                'id': entry.id,
                'user_id': entry.user_id,
                'user_email': entry.user.email,
                'user_nombre': entry.user.get_full_name() or entry.user.email,
                'user_rol': getattr(getattr(entry.user, 'role', None), 'nombre', ''),
                'colegio_rbd': entry.user.rbd_colegio,
                'created_at': entry.created_at.isoformat(),
            }
            for entry in qs[:300]
        ],
    })


# ═══════════════════════════════════════════════
# 4. DESBLOQUEO DE IPs
# ═══════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unblock_ip(request):
    """
    POST /api/seguridad/desbloquear-ip/
    Body: {"ip": "192.168.1.1"}
    """
    user = request.user
    ip = request.data.get('ip', '').strip()
    if not ip:
        raise ValidationError({'ip': 'Dirección IP requerida.'})

    can_unblock, error_msg = SecurityMonitoringService.validate_unblock_permission(user, ip)
    if not can_unblock:
        raise PermissionDenied(error_msg)

    has_access, is_global = SecurityMonitoringService.validate_monitoring_access(user)
    school_rbd = getattr(user, 'rbd_colegio', None)

    deleted, msg = SecurityMonitoringService.unblock_ip(ip, is_global, school_rbd)
    SecurityMonitoringService.log_unblock_action(ip, user, school_rbd, deleted)

    return Response({
        'detail': msg,
        'registros_eliminados': deleted,
    })


# ═══════════════════════════════════════════════
# 5. CAMBIO DE PASSWORD CON HISTORIAL
# ═══════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_secure(request):
    """
    POST /api/seguridad/cambiar-password/
    Cambio de contraseña con verificación de historial.

    Body: {"current_password": "...", "new_password": "..."}
    """
    user = request.user
    current = request.data.get('current_password', '')
    new_pw = request.data.get('new_password', '')

    if not current or not new_pw:
        raise ValidationError({'detail': 'current_password y new_password son requeridos.'})

    if not user.check_password(current):
        logger.warning(f'Intento de cambio de password fallido — user={user.email}')
        raise ValidationError({'current_password': 'Contraseña actual incorrecta.'})

    if current == new_pw:
        raise ValidationError({'new_password': 'La nueva contraseña debe ser diferente a la actual.'})

    # Verificar historial
    if check_password_reuse(user, new_pw):
        raise ValidationError({
            'new_password': f'No puedes reutilizar una de tus últimas {5} contraseñas.'
        })

    # Validar complejidad con los validators de Django
    from django.contrib.auth.password_validation import validate_password
    try:
        validate_password(new_pw, user)
    except Exception as e:
        raise ValidationError({'new_password': list(e.messages)})

    # Registrar password actual en historial antes de cambiar
    record_password_change(user, current)

    # Cambiar password
    user.set_password(new_pw)
    user.save(update_fields=['password'])

    # Registrar nuevo password en historial
    record_password_change(user, new_pw)

    # Auditar
    ip = _get_ip(request)
    logger.info(f'Password cambiado — user={user.email} ip={ip}')
    audit_sensitive_access(
        model_name='User',
        object_id=user.id,
        user=user,
        fields_accessed=['password_change'],
        ip=ip,
    )

    return Response({'detail': 'Contraseña actualizada exitosamente.'})

"""
Utilidades para Suscripciones
==============================

Funciones helper para gestión de suscripciones y límites.
Migrado desde sistema_antiguo/subscriptions/utils.py
"""

from backend.apps.subscriptions.models import Plan, Subscription, UsageLog
from backend.apps.accounts.models import User
from backend.apps.cursos.models import Curso


def get_active_student_count(colegio_rbd):
    """
    Cuenta estudiantes activos para un colegio.
    
    Un estudiante se considera activo si:
    - El usuario está activo (is_active=True)
    - Tiene perfil de estudiante
    - El estado académico es 'Activo'
    """
    return User.objects.filter(
        rbd_colegio=colegio_rbd,
        perfil_estudiante__isnull=False,
        is_active=True,
        perfil_estudiante__estado_academico='Activo'
    ).count()


def get_active_teacher_count(colegio_rbd):
    """Cuenta profesores activos para un colegio"""
    return User.objects.filter(
        rbd_colegio=colegio_rbd,
        perfil_profesor__isnull=False,
        is_active=True
    ).count()


def get_active_course_count(colegio_rbd):
    """Cuenta cursos activos para un colegio"""
    return Curso.objects.filter(
        colegio__rbd=colegio_rbd,
        activo=True
    ).count()


def update_all_usage_counts(subscription):
    """
    Actualiza todos los contadores de uso para una suscripción.
    
    Se debe llamar periódicamente (ej: diariamente) para mantener
    los contadores actualizados.
    """
    usage = UsageLog.get_current_period(subscription)
    
    # Actualizar contadores
    usage.update_student_count(get_active_student_count(subscription.colegio.rbd))
    usage.teacher_count = get_active_teacher_count(subscription.colegio.rbd)
    usage.course_count = get_active_course_count(subscription.colegio.rbd)
    usage.save()
    
    return usage


def can_add_student(colegio_rbd):
    """
    Verifica si un colegio puede agregar más estudiantes.
    
    Returns:
        tuple: (can_add: bool, current_count: int, limit: int or None)
    """
    try:
        subscription = Subscription.objects.select_related('plan').get(
            colegio__rbd=colegio_rbd
        )
        
        # TESTER siempre puede agregar
        if subscription.plan.is_unlimited:
            return (True, 0, None)
        
        # Verificar si está activa
        if not subscription.is_active():
            return (False, 0, 0)
        
        # Obtener conteo actual
        current_count = get_active_student_count(colegio_rbd)
        limit = subscription.plan.max_estudiantes
        
        # 999999 se considera ilimitado
        if limit >= 999999:
            return (True, current_count, None)
        
        can_add = current_count < limit
        return (can_add, current_count, limit)
        
    except Subscription.DoesNotExist:
        # Sin suscripción, no permitir
        return (False, 0, 0)


def can_send_message(colegio_rbd):
    """
    Verifica si un colegio puede enviar más mensajes este mes.
    
    Returns:
        tuple: (can_send: bool, sent_count: int, limit: int or None)
    """
    try:
        subscription = Subscription.objects.select_related('plan').get(
            colegio__rbd=colegio_rbd
        )
        
        # TESTER siempre puede enviar
        if subscription.plan.is_unlimited:
            return (True, 0, None)
        
        if not subscription.is_active():
            return (False, 0, 0)
        
        # Obtener uso del mes actual
        usage = UsageLog.get_current_period(subscription)
        has_reached, current, limit = usage.check_limit('messages_sent')
        
        can_send = not has_reached
        return (can_send, current, limit)
        
    except Subscription.DoesNotExist:
        return (False, 0, 0)


def can_create_evaluation(colegio_rbd):
    """
    Verifica si un colegio puede crear más evaluaciones este mes.
    
    Returns:
        tuple: (can_create: bool, created_count: int, limit: int or None)
    """
    try:
        subscription = Subscription.objects.select_related('plan').get(
            colegio__rbd=colegio_rbd
        )
        
        # TESTER siempre puede crear
        if subscription.plan.is_unlimited:
            return (True, 0, None)
        
        if not subscription.is_active():
            return (False, 0, 0)
        
        usage = UsageLog.get_current_period(subscription)
        has_reached, current, limit = usage.check_limit('evaluations_created')
        
        can_create = not has_reached
        return (can_create, current, limit)
        
    except Subscription.DoesNotExist:
        return (False, 0, 0)


def get_subscription_status_message(subscription):
    """
    Genera un mensaje descriptivo del estado de la suscripción.
    
    Útil para mostrar en dashboards o alertas.
    """
    if not subscription:
        return {
            'type': 'danger',
            'message': 'No tienes una suscripción activa. Contacta a soporte.'
        }
    
    # TESTER (ilimitado)
    if subscription.plan.is_unlimited:
        return {
            'type': 'success',
            'message': f'Plan {subscription.plan.nombre}: Acceso ilimitado para demos y desarrollo.'
        }
    
    # Verificar si está activa
    if not subscription.is_active():
        return {
            'type': 'danger',
            'message': 'Tu suscripción ha expirado. Renueva tu plan para continuar usando la plataforma.'
        }
    
    # Verificar días restantes
    dias = subscription.dias_restantes()
    
    if dias is None:
        return {
            'type': 'success',
            'message': f'Plan {subscription.plan.nombre}: Suscripción activa.'
        }
    
    if dias == 0:
        return {
            'type': 'danger',
            'message': 'Tu suscripción expira hoy. Renueva ahora para evitar interrupciones.'
        }
    
    if dias <= 7:
        return {
            'type': 'warning',
            'message': f'Tu suscripción expira en {dias} días. Renueva pronto para evitar interrupciones.'
        }
    
    if dias <= 15:
        return {
            'type': 'info',
            'message': f'Tu suscripción expira en {dias} días.'
        }
    
    return {
        'type': 'success',
        'message': f'Plan {subscription.plan.nombre}: Suscripción activa ({dias} días restantes).'
    }


def get_usage_warnings(subscription):
    """
    Genera advertencias si algún límite está cerca del máximo.
    
    Returns:
        list: Lista de diccionarios con advertencias
    """
    if not subscription or subscription.plan.is_unlimited:
        return []
    
    warnings = []
    usage = UsageLog.get_current_period(subscription)
    
    # Verificar cada límite
    limits_to_check = [
        ('student_count', 'estudiantes activos', 'estudiantes'),
        ('messages_sent', 'mensajes enviados este mes', 'mensajes'),
        ('evaluations_created', 'evaluaciones creadas este mes', 'evaluaciones'),
    ]
    
    for field, description, short_name in limits_to_check:
        porcentaje = usage.get_usage_percentage(field)
        
        if porcentaje >= 100:
            has_reached, current, limit = usage.check_limit(field)
            warnings.append({
                'type': 'danger',
                'message': f'Has alcanzado el límite de {description} ({limit}). Actualiza tu plan para continuar.',
                'field': field,
                'percentage': 100
            })
        elif porcentaje >= 90:
            has_reached, current, limit = usage.check_limit(field)
            warnings.append({
                'type': 'warning',
                'message': f'Estás cerca del límite de {description} ({current}/{limit} - {porcentaje}%).',
                'field': field,
                'percentage': porcentaje
            })
    
    return warnings

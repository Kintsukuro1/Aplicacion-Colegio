"""
Helpers centralizados para views del API.

Elimina la duplicación de funciones helper que se repetían en 6+ archivos
de views (resources_views, gestion_escolar_views, finanzas_reuniones_views,
seguridad_views, importacion_exportacion_views, comunicacion_analitica_views).
"""
from rest_framework.exceptions import PermissionDenied

from backend.common.services.policy_service import PolicyService


def is_global_admin(user):
    """Verifica si el usuario tiene capability SYSTEM_ADMIN (admin global)."""
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN')


def has_cap(user, capability):
    """Verifica si el usuario tiene una capability específica en su colegio."""
    return PolicyService.has_capability(
        user,
        capability,
        school_id=getattr(user, 'rbd_colegio', None),
    )


def school_id(user):
    """Devuelve el rbd_colegio del usuario."""
    return getattr(user, 'rbd_colegio', None)


def is_admin(user):
    """Verifica si el usuario es admin global o tiene SYSTEM_CONFIGURE."""
    return is_global_admin(user) or has_cap(user, 'SYSTEM_CONFIGURE')


def is_security_admin(user):
    """Verifica si el usuario es admin global o tiene AUDIT_VIEW."""
    return is_global_admin(user) or has_cap(user, 'AUDIT_VIEW')


def can_manage_school(user):
    """Verifica si el usuario puede gestionar la escuela."""
    return is_global_admin(user) or has_cap(user, 'SYSTEM_CONFIGURE')


def ensure_same_school(user, target_school_id):
    """Lanza PermissionDenied si el usuario opera en otro colegio (salvo admin global)."""
    if is_global_admin(user):
        return
    if school_id(user) != target_school_id:
        raise PermissionDenied('No puede operar recursos de otro colegio.')


def forbid_without_cap(user, capability):
    """Lanza PermissionDenied si el usuario no tiene la capability (salvo admin global)."""
    if not is_global_admin(user) and not has_cap(user, capability):
        raise PermissionDenied('No tiene permisos para este recurso.')


def get_role_name(user):
    """Devuelve el nombre del rol del usuario en minúsculas, stripped."""
    return getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()


def is_teacher(user):
    """Verifica si el usuario tiene rol Profesor."""
    return get_role_name(user) == 'profesor'


def is_student(user):
    """Verifica si el usuario tiene rol Estudiante/Alumno."""
    return get_role_name(user) in {'estudiante', 'alumno'}


def ensure_teacher_owns_class(user, clase):
    """Lanza PermissionDenied si un profesor opera sobre una clase que no le pertenece."""
    if is_global_admin(user):
        return
    if is_teacher(user) and clase.profesor_id != user.id:
        raise PermissionDenied('No puede operar una clase asignada a otro profesor.')


def get_client_ip(request):
    """Extrae la IP del cliente del request."""
    return request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
        or request.META.get('REMOTE_ADDR', '')


def apply_search_filter(queryset, search_term, fields):
    """
    Aplica filtro de búsqueda por icontains sobre múltiples campos.

    Ejemplo:
        apply_search_filter(qs, 'juan', ['nombre', 'email', 'rut'])
    """
    from django.db.models import Q

    if not search_term or not search_term.strip():
        return queryset

    search = search_term.strip()
    query = Q()
    for field in fields:
        query |= Q(**{f'{field}__icontains': search})
    return queryset.filter(query)

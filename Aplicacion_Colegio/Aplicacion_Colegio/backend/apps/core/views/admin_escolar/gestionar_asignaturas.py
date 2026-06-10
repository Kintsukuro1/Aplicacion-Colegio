from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from backend.apps.core.services.asignaturas_view_service import AsignaturasViewService
from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService


@login_required
def gestionar_asignaturas(request):
    """Vista para gestionar asignaturas con CRUD y asignación a cursos/profesores."""
    can_access = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN') or PolicyService.has_capability(
        request.user, 'SYSTEM_CONFIGURE'
    )
    if not can_access:
        can_access = PermissionService.has_permission(
            request.user,
            'ADMINISTRATIVO',
            'MANAGE_SYSTEM',
        )
    if not can_access:
        return render(request, 'compartido/acceso_denegado.html', {
            'mensaje': 'No tiene permisos para gestionar asignaturas.'
        })

    return AsignaturasViewService.handle(request)
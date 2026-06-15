"""POST handler for admin escolar subject management (dashboard forms)."""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from backend.apps.core.services.asignaturas_view_service import AsignaturasViewService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.apps.core.views.admin_escolar._access import can_manage_school_data


def _redirect_asignaturas(**params):
    query = {'pagina': 'gestionar_asignaturas'}
    for key, value in params.items():
        if value not in (None, ''):
            query[key] = value
    return redirect(f'/dashboard/?{urlencode(query)}')


@login_required(login_url='login')
def gestionar_asignaturas(request):
    """Processes POST actions from admin_escolar/gestionar_asignaturas.html."""
    if request.method != 'POST':
        return _redirect_asignaturas()

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, 'Sesión inválida')
        return redirect('accounts:login')

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if not can_manage_school_data(rol, request.user):
        messages.error(request, 'Acceso denegado')
        return redirect('dashboard')

    if not escuela_rbd:
        messages.error(request, 'No hay escuela asignada')
        return redirect('dashboard')

    try:
        colegio = SchoolQueryService.get_required_by_rbd(escuela_rbd)
    except Exception:
        messages.error(request, 'No se encontró la escuela')
        return redirect('dashboard')

    early = AsignaturasViewService.process_post(request, colegio)
    if early is not None:
        return early

    curso_horario = request.POST.get('curso_horario') or request.GET.get('curso_horario')
    busqueda = request.POST.get('busqueda') or request.GET.get('busqueda')
    return _redirect_asignaturas(curso_horario=curso_horario, busqueda=busqueda)

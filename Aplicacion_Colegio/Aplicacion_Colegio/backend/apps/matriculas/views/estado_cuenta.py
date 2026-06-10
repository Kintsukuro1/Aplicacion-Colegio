# matriculas/views/estado_cuenta.py
"""Vista para el estado de cuenta de matrículas."""

from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.core.exceptions import ObjectDoesNotExist

from backend.apps.matriculas.services import MatriculaService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.dashboard_helpers import build_dashboard_context
from backend.apps.core.services.dashboard_service import DashboardService


def _has_profile(user, profile_attr: str) -> bool:
    try:
        return getattr(user, profile_attr, None) is not None
    except (ObjectDoesNotExist, AttributeError):
        return False


@login_required()
def mi_estado_cuenta(request):
    school_id = getattr(request.user, 'rbd_colegio', None)
    has_finance_view = PolicyService.has_capability(request.user, 'FINANCE_VIEW', school_id=school_id)
    is_estudiante = _has_profile(request.user, 'perfil_estudiante')
    is_apoderado = _has_profile(request.user, 'perfil_apoderado')

    if not has_finance_view or not (is_estudiante or is_apoderado):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('dashboard')

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None and not is_apoderado:
        if not request.user.rbd_colegio:
            return redirect('seleccionar_escuela')
        messages.error(request, 'Sesión inválida - sin escuela asignada')
        return redirect('accounts:login')

    estudiante_obj = request.user
    estudiantes = None

    if is_apoderado:
        apoderado, estudiantes = MatriculaService.get_apoderado_estudiantes(request.user)
        if not apoderado or not estudiantes:
            messages.warning(request, 'No tienes estudiantes asociados para ver estado de cuenta.')
            return redirect('dashboard')

        estudiante_id = request.GET.get('estudiante_id')
        if estudiante_id:
            try:
                estudiante_obj = next(e for e in estudiantes if str(e.id) == str(estudiante_id))
            except StopIteration:
                messages.error(request, 'No tienes permiso para ver el estado de cuenta de ese estudiante.')
                return redirect('dashboard')
        else:
            estudiante_obj = estudiantes[0]

    # Usar el service para obtener los datos del estado de cuenta
    result = MatriculaService.get_estado_cuenta_data(request.user, estudiante_obj)
    if 'error' in result:
        messages.error(request, result['error'])
        return redirect('dashboard')

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='mi_estado_cuenta',
        content_template='matriculas/estado_cuenta.html',
    )
    if redirect_response:
        return redirect_response

    context.update(
        {
            'matricula': result['matricula'],
            'cuotas': result['cuotas'],
            'estudiante_seleccionado': estudiante_obj if is_apoderado else None,
            'estudiantes': estudiantes if is_apoderado else None,
            'totales': result['totales'],
        }
    )
    return render(request, 'dashboard.html', context)

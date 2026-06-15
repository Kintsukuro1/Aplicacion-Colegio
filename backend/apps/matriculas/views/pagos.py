# matriculas/views/pagos.py
"""Vista para los pagos de matrículas."""

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
def mis_pagos(request):
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        if not request.user.rbd_colegio:
            return redirect('seleccionar_escuela')
        messages.error(request, 'Sesión inválida - sin escuela asignada')
        return redirect('accounts:login')

    school_id = getattr(request.user, 'rbd_colegio', None)
    has_finance_view = PolicyService.has_capability(request.user, 'FINANCE_VIEW', school_id=school_id)
    is_estudiante = _has_profile(request.user, 'perfil_estudiante')
    is_apoderado = _has_profile(request.user, 'perfil_apoderado')

    if not has_finance_view or not (is_estudiante or is_apoderado):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('dashboard')

    estudiante_obj = request.user
    estudiantes = None

    if is_apoderado:
        apoderado, estudiantes = MatriculaService.get_apoderado_estudiantes(request.user)
        if not apoderado or not estudiantes:
            messages.warning(request, 'No tienes estudiantes asociados para ver pagos.')
            return redirect('dashboard')

        estudiante_id = request.GET.get('estudiante_id')
        if estudiante_id:
            try:
                estudiante_obj = next(e for e in estudiantes if str(e.id) == str(estudiante_id))
            except StopIteration:
                messages.error(request, 'No tienes permiso para ver los pagos de ese estudiante.')
                return redirect('dashboard')
        else:
            estudiante_obj = estudiantes[0]

    # Usar el service para obtener los datos de pagos
    result = MatriculaService.get_pagos_data(request.user, estudiante_obj)
    if 'error' in result:
        messages.error(request, result['error'])
        return redirect('dashboard')

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='mis_pagos',
        content_template='matriculas/mis_pagos.html',
    )
    if redirect_response:
        return redirect_response

    context.update(
        {
            'pagos': result['pagos'],
            'total_pagado': result['total_pagado'],
            'estudiante_seleccionado': estudiante_obj if is_apoderado else None,
            'estudiantes': estudiantes if is_apoderado else None,
        }
    )
    return render(request, 'dashboard.html', context)

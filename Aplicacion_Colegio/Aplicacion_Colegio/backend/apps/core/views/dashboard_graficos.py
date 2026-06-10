"""Dashboard de estadísticas (gráficos) + APIs JSON.

Migrado desde `sistema_antiguo/core/views_dashboard_graficos.py`.

El dashboard se renderiza dentro de `frontend/templates/dashboard.html` usando
`content_template='compartido/dashboard_graficos.html'`.
"""

from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from backend.common.utils.dashboard_helpers import build_dashboard_context
from backend.apps.core.services.dashboard_graficos_service import DashboardGraficosService
from backend.apps.core.services.dashboard_service import DashboardService


@login_required()
def dashboard_graficos(request):
    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='dashboard_graficos',
        content_template='compartido/dashboard_graficos.html',
    )
    if redirect_response:
        return redirect_response
    return render(request, 'dashboard.html', context)


@login_required()
def api_datos_asistencia(request):
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        return JsonResponse({'labels': [], 'data': []})

    user_context_data = user_context['data']
    rol = user_context_data.get('rol')
    escuela_rbd = user_context_data['escuela_rbd']

    return JsonResponse(DashboardGraficosService.get_datos_asistencia(request.user, rol, escuela_rbd))


@login_required()
def api_datos_calificaciones(request):
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        return JsonResponse({'labels': [], 'data': []})

    user_context_data = user_context['data']
    rol = user_context_data.get('rol')
    escuela_rbd = user_context_data['escuela_rbd']

    return JsonResponse(DashboardGraficosService.get_datos_calificaciones(request.user, rol, escuela_rbd))


@login_required()
def api_datos_rendimiento(request):
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        return JsonResponse({'labels': [], 'data': []})

    user_context_data = user_context['data']
    rol = user_context_data.get('rol')
    escuela_rbd = user_context_data['escuela_rbd']

    return JsonResponse(DashboardGraficosService.get_datos_rendimiento(request.user, rol, escuela_rbd))


@login_required()
def api_datos_estadisticas(request):
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        return JsonResponse({'error': 'Sesión inválida'})

    user_context_data = user_context['data']
    rol = user_context_data.get('rol')
    escuela_rbd = user_context_data['escuela_rbd']

    return JsonResponse(DashboardGraficosService.get_datos_estadisticas(request.user, rol, escuela_rbd))


@login_required()
def api_notificaciones(request):
    """API para obtener notificaciones del usuario"""
    from backend.apps.core.services.dashboard_context_service import DashboardContextService
    
    notificaciones_context = DashboardContextService.get_notificaciones_context(request.user)
    
    return JsonResponse({
        'count': notificaciones_context['notificaciones_count'],
        'notificaciones': notificaciones_context['notificaciones_recientes']
    })


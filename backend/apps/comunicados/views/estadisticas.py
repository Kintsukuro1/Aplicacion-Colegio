# comunicados/views/estadisticas.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..services import ComunicadosService


@login_required
def estadisticas_dashboard(request, comunicado_id):
    """
    Dashboard detallado de estadísticas del comunicado
    con gráficos y métricas avanzadas
    """
    data = ComunicadosService.get_detailed_statistics(request.user, comunicado_id)
    if 'error' in data:
        messages.error(request, data['error'])
        return redirect('comunicados:lista')

    return render(request, 'comunicados/estadisticas_dashboard.html', data)
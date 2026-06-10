"""Core view: actualizar escuela (Admin escolar)

Handles the POST from admin_escolar/mi_escuela.html.
Kept minimal for the migration: updates editable Colegio fields for the current user's school.
"""

from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.colegio_service import ColegioService


@login_required(login_url="login")
def actualizar_escuela(request):
    if request.method != "POST":
        return redirect("dashboard")

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, "Sesión inválida")
        return redirect("accounts:login")

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if rol not in ["admin", "admin_escolar"]:
        messages.error(request, "No tienes permiso para actualizar la escuela")
        return redirect("dashboard")

    if not escuela_rbd:
        messages.error(request, "No hay escuela asignada")
        return redirect("dashboard")

    nombre = (request.POST.get("nombre") or "").strip()
    if not nombre:
        messages.error(request, "El nombre del establecimiento es obligatorio")
        return redirect("dashboard")

    payload = {
        'nombre': nombre,
        'direccion': (request.POST.get("direccion") or "").strip() or None,
        'telefono': (request.POST.get("telefono") or "").strip() or None,
        'correo': (request.POST.get("correo") or "").strip() or None,
        'web': (request.POST.get("web") or "").strip() or None,
    }

    capacidad_raw = (request.POST.get("capacidad_maxima") or "").strip()
    if capacidad_raw:
        try:
            payload['capacidad_maxima'] = int(capacidad_raw)
        except ValueError:
            messages.error(request, "Capacidad máxima inválida")
            return redirect("dashboard")
    else:
        payload['capacidad_maxima'] = None

    fecha_raw = (request.POST.get("fecha_fundacion") or "").strip()
    if fecha_raw:
        try:
            payload['fecha_fundacion'] = date.fromisoformat(fecha_raw)
        except ValueError:
            messages.error(request, "Fecha de fundación inválida")
            return redirect("dashboard")
    else:
        payload['fecha_fundacion'] = None

    try:
        ColegioService.update_basic_info(
            user=request.user,
            rbd=escuela_rbd,
            data=payload,
        )
    except Exception:
        messages.error(request, "No se pudo guardar los cambios")
        return redirect("dashboard")

    messages.success(request, "Información de la escuela actualizada")
    return redirect("dashboard")

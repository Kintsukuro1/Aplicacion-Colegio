"""Core view: gestionar asistencia (Profesor/Admin)

Endpoint POST utilizado por el template profesor/asistencia.html dentro del dashboard.
Se mantiene como URL global (sin namespace) durante la migración.
"""

from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from backend.apps.academico.services.attendance_service import AttendanceService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.common.services.policy_service import PolicyService


@login_required(login_url="login")
def gestionar_asistencia_profesor(request):
    """Vista pasarela para gestión de asistencia."""
    # En el dashboard la página es un GET, este endpoint se usa solo para POST.
    if request.method != "POST":
        return redirect(f"{reverse('dashboard')}?pagina=asistencia")

    can_manage_classes = PolicyService.has_capability(request.user, "CLASS_VIEW") and (
        PolicyService.has_capability(request.user, "CLASS_EDIT")
        or PolicyService.has_capability(request.user, "CLASS_TAKE_ATTENDANCE")
    )
    can_admin = PolicyService.has_capability(request.user, "SYSTEM_ADMIN") or PolicyService.has_capability(
        request.user, "SYSTEM_CONFIGURE"
    )
    if not (can_manage_classes or can_admin):
        messages.error(request, "No tienes permisos para gestionar asistencia")
        return redirect(f"{reverse('dashboard')}?pagina=asistencia")

    if not request.user.rbd_colegio:
        messages.error(request, "No hay escuela asignada")
        return redirect(f"{reverse('dashboard')}?pagina=asistencia")

    colegio = SchoolQueryService.get_by_rbd(request.user.rbd_colegio)
    if not colegio:
        messages.error(request, "No se encontró la escuela")
        return redirect(f"{reverse('dashboard')}?pagina=asistencia")

    accion = (request.POST.get("accion") or "").strip()

    try:
        if accion in {"registrar_asistencia", "actualizar_observacion"}:
            # Delegar procesamiento de asistencia al servicio
            result = AttendanceService.process_attendance_action(request.user, colegio, request.POST)
            if result['success']:
                messages.success(request, result['message'])
            else:
                messages.error(request, result['message'])
        else:
            messages.error(request, "Acción no reconocida")

    except Exception:
        logger = __import__('logging').getLogger(__name__)
        logger.exception("Error al procesar la solicitud de asistencia de profesor")
        messages.error(request, "No se pudo procesar la solicitud. Intenta nuevamente.")

    # Mantiene la navegación dentro del dashboard.
    return redirect(f"{reverse('dashboard')}?pagina=asistencia")
"""Core view: gestionar evaluaciones y calificaciones (Profesor/Admin)

Endpoint POST utilizado por el template profesor/notas.html dentro del dashboard.
Se expone como URL global (sin namespace) para compatibilidad durante la migración.

Acciones soportadas (POST):
- crear_evaluacion
- editar_evaluacion
- eliminar_evaluacion (soft delete: Evaluacion.activa=False)
- registrar_calificaciones
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from backend.apps.academico.services.grades_service import GradesService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.common.services.policy_service import PolicyService


def _redirect_notas():
	return redirect(f"{reverse('dashboard')}?pagina=notas")


@login_required(login_url="login")
def gestionar_evaluaciones_calificaciones(request):
	# En el dashboard, la página de notas es GET; este endpoint se usa solo para POST.
	if request.method != "POST":
		return _redirect_notas()

	can_manage_classes = PolicyService.has_capability(request.user, "CLASS_VIEW") and (
		PolicyService.has_capability(request.user, "CLASS_EDIT")
		or PolicyService.has_capability(request.user, "CLASS_TAKE_ATTENDANCE")
	)
	can_admin = PolicyService.has_capability(request.user, "SYSTEM_ADMIN") or PolicyService.has_capability(
		request.user, "SYSTEM_CONFIGURE"
	)
	if not (can_manage_classes or can_admin):
		messages.error(request, "No tienes permisos para gestionar evaluaciones")
		return _redirect_notas()

	if not request.user.rbd_colegio:
		messages.error(request, "No hay escuela asignada")
		return _redirect_notas()

	colegio = SchoolQueryService.get_by_rbd(request.user.rbd_colegio)
	if not colegio:
		messages.error(request, "No se encontró la escuela")
		return _redirect_notas()

	accion = (request.POST.get("accion") or "").strip()

	try:
		if accion in {"crear_evaluacion", "editar_evaluacion", "eliminar_evaluacion"}:
			# Delegar gestión de evaluaciones al servicio
			result = GradesService.process_evaluation_action(request.user, colegio, request.POST, request.FILES)
			if result['success']:
				messages.success(request, result['message'])
				if 'redirect_url' in result:
					return redirect(result['redirect_url'])
				return _redirect_notas()
			else:
				messages.error(request, result['message'])
				return _redirect_notas()

		if accion == "registrar_calificaciones":
			# Delegar registro de calificaciones al servicio
			result = GradesService.process_grades_registration(request.user, colegio, request.POST)
			if result['success']:
				messages.success(request, result['message'])
				if 'redirect_url' in result:
					return redirect(result['redirect_url'])
				return _redirect_notas()
			else:
				messages.error(request, result['message'])
				return _redirect_notas()

		messages.error(request, "Acción no reconocida")
		return _redirect_notas()

	except Exception:
		logger = __import__('logging').getLogger(__name__)
		logger.exception("Error al procesar la solicitud de evaluaciones/calificaciones")
		messages.error(request, "No se pudo procesar la solicitud. Intenta nuevamente.")
		return _redirect_notas()

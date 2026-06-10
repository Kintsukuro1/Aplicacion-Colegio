"""Core view: gestionar ciclos académicos (Admin escolar)

Endpoint POST utilizado por el template admin_escolar/gestionar_ciclos.html.
Se implementa en core (URL global) para evitar problemas de namespace durante la migración.

Acciones soportadas (POST):
- crear
- editar
- eliminar (soft delete)
- activar
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect

from backend.apps.core.services.ciclo_academico_service import CicloAcademicoService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.apps.institucion.models import CicloAcademico
from backend.common.services.onboarding_service import OnboardingService
from backend.common.exceptions import PrerequisiteException

logger = logging.getLogger(__name__)


@login_required(login_url="login")
def gestionar_ciclos(request):
    if request.method != "POST":
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, "Sesión inválida")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if rol not in ["admin", "admin_escolar"]:
        messages.error(request, "Acceso denegado")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    if not escuela_rbd:
        messages.error(request, "No hay escuela asignada")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    try:
        colegio = SchoolQueryService.get_required_by_rbd(escuela_rbd)
    except Exception:
        messages.error(request, "No se encontró la escuela")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    action = request.POST.get('action')

    if action == 'crear':
        return _crear_ciclo(request, colegio)
    elif action == 'editar':
        return _editar_ciclo(request, colegio)
    elif action == 'eliminar':
        return _eliminar_ciclo(request, colegio)
    elif action == 'activar':
        return _activar_ciclo(request, colegio)
    else:
        messages.error(request, "Acción no válida")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')


def _crear_ciclo(request, colegio):
    nombre = request.POST.get('nombre')
    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')
    descripcion = request.POST.get('descripcion', '')

    if not nombre or not fecha_inicio or not fecha_fin:
        messages.error(request, "Todos los campos son obligatorios")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    try:
        with transaction.atomic():
            CicloAcademicoService.create(
                user=request.user,
                school_rbd=colegio.rbd,
                nombre=nombre,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                descripcion=descripcion,
            )
        messages.success(request, f"Ciclo académico '{nombre}' creado exitosamente")
    except (PrerequisiteException, ValueError) as e:
        messages.error(request, str(e))
    except Exception:
        logger.exception("Error al crear ciclo académico")
        messages.error(request, "Ocurrió un error al crear el ciclo. Contacte al administrador.")

    return redirect(f'/dashboard/?pagina=gestionar_ciclos')


def _editar_ciclo(request, colegio):
    ciclo_id = request.POST.get('ciclo_id')
    nombre = request.POST.get('nombre')
    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')
    descripcion = request.POST.get('descripcion', '')

    if not ciclo_id or not nombre or not fecha_inicio or not fecha_fin:
        messages.error(request, "Todos los campos son obligatorios")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    try:
        with transaction.atomic():
            CicloAcademicoService.update(
                user=request.user,
                school_rbd=colegio.rbd,
                ciclo_id=int(ciclo_id),
                nombre=nombre,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                descripcion=descripcion,
            )
        messages.success(request, f"Ciclo académico '{nombre}' actualizado exitosamente")
    except Exception:
        logger.exception("Error al actualizar ciclo académico")
        messages.error(request, "Ocurrió un error al actualizar el ciclo. Contacte al administrador.")

    return redirect(f'/dashboard/?pagina=gestionar_ciclos')


def _eliminar_ciclo(request, colegio):
    ciclo_id = request.POST.get('ciclo_id')

    if not ciclo_id:
        messages.error(request, "ID de ciclo requerido")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    try:
        with transaction.atomic():
            CicloAcademicoService.delete(
                user=request.user,
                school_rbd=colegio.rbd,
                ciclo_id=int(ciclo_id),
            )
        messages.success(request, "Ciclo académico eliminado exitosamente")
    except Exception:
        logger.exception("Error al eliminar ciclo académico")
        messages.error(request, "Ocurrió un error al eliminar el ciclo. Contacte al administrador.")

    return redirect(f'/dashboard/?pagina=gestionar_ciclos')


def _activar_ciclo(request, colegio):
    ciclo_id = request.POST.get('ciclo_id')

    if not ciclo_id:
        messages.error(request, "ID de ciclo requerido")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    try:
        ciclo = ORMAccessService.get(CicloAcademico, id=ciclo_id, colegio=colegio)
    except Exception:
        messages.error(request, "No se encontró el ciclo solicitado")
        return redirect(f'/dashboard/?pagina=gestionar_ciclos')

    try:
        with transaction.atomic():
            CicloAcademicoService.activate(
                user=request.user,
                school_rbd=colegio.rbd,
                ciclo_id=ciclo.id,
            )
        messages.success(request, f"Ciclo académico '{ciclo.nombre}' activado exitosamente")
    except Exception:
        logger.exception("Error al activar ciclo académico")
        messages.error(request, "Ocurrió un error al activar el ciclo. Contacte al administrador.")

    return redirect(f'/dashboard/?pagina=gestionar_ciclos')
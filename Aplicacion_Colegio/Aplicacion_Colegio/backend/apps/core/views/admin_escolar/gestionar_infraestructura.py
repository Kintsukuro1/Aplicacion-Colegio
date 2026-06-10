"""Core view: gestionar infraestructura (Admin escolar)

Provides POST handlers used by admin_escolar/infraestructura.html:
- crear
- editar
- eliminar

Kept minimal for the migration; relies on backend.apps.institucion.models.Infraestructura.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.infraestructura_service import InfraestructuraService


def _redirect_infraestructura():
    return redirect(f"{reverse('dashboard')}?pagina=infraestructura")


def _to_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return int(raw)


def _to_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return Decimal(raw)


@login_required(login_url="login")
def gestionar_infraestructura(request):
    if request.method != "POST":
        return _redirect_infraestructura()

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, "Sesión inválida")
        return redirect("accounts:login")

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if rol not in ["admin", "admin_escolar"]:
        messages.error(request, "No tienes permiso para gestionar infraestructura")
        return _redirect_infraestructura()

    if not escuela_rbd:
        messages.error(request, "No hay escuela asignada")
        return _redirect_infraestructura()

    accion = (request.POST.get("accion") or "").strip().lower()

    try:
        if accion == "eliminar":
            infra_id = _to_int(request.POST.get("id"))
            if not infra_id:
                messages.error(request, "ID inválido")
                return _redirect_infraestructura()

            deleted = InfraestructuraService.delete(
                school_rbd=escuela_rbd,
                infra_id=infra_id,
            )
            if deleted:
                messages.success(request, "Espacio eliminado")
            else:
                messages.error(request, "No se encontró el espacio")
            return _redirect_infraestructura()

        if accion in {"crear", "editar"}:
            nombre = (request.POST.get("nombre") or "").strip()
            tipo = (request.POST.get("tipo") or "").strip()
            estado = (request.POST.get("estado") or "").strip()
            observaciones = (request.POST.get("observaciones") or "").strip() or None

            if not nombre or not tipo or not estado:
                messages.error(request, "Faltan campos obligatorios")
                return _redirect_infraestructura()

            try:
                piso = _to_int(request.POST.get("piso"))
                capacidad = _to_int(request.POST.get("capacidad"))
            except ValueError:
                messages.error(request, "Piso o capacidad inválidos")
                return _redirect_infraestructura()

            if piso is None or capacidad is None:
                messages.error(request, "Piso y capacidad son obligatorios")
                return _redirect_infraestructura()

            try:
                ancho = _to_decimal(request.POST.get("ancho"))
                largo = _to_decimal(request.POST.get("largo"))
                alto = _to_decimal(request.POST.get("alto"))
            except (InvalidOperation, ValueError):
                messages.error(request, "Dimensiones inválidas")
                return _redirect_infraestructura()

            if accion == "crear":
                InfraestructuraService.create(
                    school_rbd=escuela_rbd,
                    data={
                        'nombre': nombre,
                        'tipo': tipo,
                        'piso': piso,
                        'capacidad_estudiantes': capacidad,
                        'ancho_metros': ancho,
                        'largo_metros': largo,
                        'alto_metros': alto,
                        'estado': estado,
                        'observaciones': observaciones,
                        'activo': True,
                    }
                )
                messages.success(request, "Espacio creado")
                return _redirect_infraestructura()

            infra_id = _to_int(request.POST.get("id"))
            if not infra_id:
                messages.error(request, "ID inválido")
                return _redirect_infraestructura()

            infraestructura = InfraestructuraService.update(
                school_rbd=escuela_rbd,
                infra_id=infra_id,
                data={
                    'nombre': nombre,
                    'tipo': tipo,
                    'piso': piso,
                    'capacidad_estudiantes': capacidad,
                    'ancho_metros': ancho,
                    'largo_metros': largo,
                    'alto_metros': alto,
                    'estado': estado,
                    'observaciones': observaciones,
                }
            )
            if not infraestructura:
                messages.error(request, "No se encontró el espacio")
                return _redirect_infraestructura()

            messages.success(request, "Cambios guardados")
            return _redirect_infraestructura()

        messages.error(request, "Acción inválida")
        return _redirect_infraestructura()

    except Exception:
        messages.error(request, "Ocurrió un error al procesar la solicitud")
        return _redirect_infraestructura()

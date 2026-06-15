"""API para gestión de cuotas (asesor financiero)."""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.apps.matriculas.models import Cuota, Matricula
from backend.common.services import PermissionService
from backend.common.utils.auth_helpers import normalizar_rol
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'VIEW_FEES')
@require_http_methods(["GET"])
def estadisticas_cuotas(request):
    """Estadísticas de cuotas del colegio.

    Endpoint consumido por [frontend/templates/asesor_financiero/cuotas.html](frontend/templates/asesor_financiero/cuotas.html).
    """

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    try:
        # Detectar ciclo academico activo/más reciente
        ciclo_activo_id = (
            ORMAccessService.filter(Matricula, colegio_id=rbd, estado="ACTIVA")
            .values_list("ciclo_academico_id", flat=True)
            .order_by("-ciclo_academico__fecha_inicio", "-ciclo_academico_id")
            .first()
        )

        if not ciclo_activo_id:
            return JsonResponse(
                {
                    "success": True,
                    "total_cuotas": 0,
                    "cuotas_pagadas": 0,
                    "cuotas_pendientes": 0,
                    "cuotas_vencidas": 0,
                    "monto_total_pendiente": 0,
                    "porcentaje_pagadas": 0,
                    "porcentaje_pendientes": 0,
                    "porcentaje_vencidas": 0,
                }
            )

        # Cuotas del colegio (año activo)
        cuotas = ORMAccessService.filter(
            Cuota,
            matricula__colegio_id=rbd,
            matricula__estado="ACTIVA",
            matricula__ciclo_academico_id=ciclo_activo_id,
        )

        total_cuotas = cuotas.count()
        hoy = timezone.now().date()

        # Cuotas pagadas
        cuotas_pagadas = cuotas.filter(estado="PAGADA").count()

        # Cuotas pendientes (PENDIENTE y no vencidas)
        cuotas_pendientes = cuotas.filter(
            estado__in=["PENDIENTE", "PAGADA_PARCIAL"], fecha_vencimiento__gte=hoy
        ).count()

        # Cuotas vencidas (PENDIENTE/PAGADA_PARCIAL y vencidas, o VENCIDA)
        cuotas_vencidas = (
            cuotas.filter(estado="VENCIDA").count()
            + cuotas.filter(estado__in=["PENDIENTE", "PAGADA_PARCIAL"], fecha_vencimiento__lt=hoy).count()
        )

        # Monto total pendiente (saldo de cuotas no pagadas)
        cuotas_no_pagadas = cuotas.exclude(estado="PAGADA")
        monto_total_pendiente = Decimal("0")
        for cuota in cuotas_no_pagadas:
            saldo = cuota.monto_final - cuota.monto_pagado
            if saldo > 0:
                monto_total_pendiente += saldo

        # Calcular porcentajes
        if total_cuotas > 0:
            porcentaje_pagadas = round((cuotas_pagadas / total_cuotas) * 100, 1)
            porcentaje_pendientes = round((cuotas_pendientes / total_cuotas) * 100, 1)
            porcentaje_vencidas = round((cuotas_vencidas / total_cuotas) * 100, 1)
        else:
            porcentaje_pagadas = 0
            porcentaje_pendientes = 0
            porcentaje_vencidas = 0

        return JsonResponse(
            {
                "success": True,
                "total_cuotas": total_cuotas,
                "cuotas_pagadas": cuotas_pagadas,
                "cuotas_pendientes": cuotas_pendientes,
                "cuotas_vencidas": cuotas_vencidas,
                "monto_total_pendiente": float(monto_total_pendiente),
                "porcentaje_pagadas": porcentaje_pagadas,
                "porcentaje_pendientes": porcentaje_pendientes,
                "porcentaje_vencidas": porcentaje_vencidas,
            }
        )

    except Exception:
        logger.exception("Error al obtener estadísticas de cuotas")
        return JsonResponse({"success": False, "error": "Error interno del servidor"}, status=500)


@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'VIEW_FEES')
@require_http_methods(["GET"])
def listar_cuotas_proximas(request):
    """Lista cuotas próximas a vencer (próximos 30 días).

    Endpoint consumido por [frontend/templates/asesor_financiero/cuotas.html](frontend/templates/asesor_financiero/cuotas.html).
    """


    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    try:
        # Detectar ciclo academico activo/más reciente
        ciclo_activo_id = (
            ORMAccessService.filter(Matricula, colegio_id=rbd, estado="ACTIVA")
            .values_list("ciclo_academico_id", flat=True)
            .order_by("-ciclo_academico__fecha_inicio", "-ciclo_academico_id")
            .first()
        )

        if not ciclo_activo_id:
            return JsonResponse({"success": True, "cuotas": [], "total": 0})

        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=30)

        # Cuotas pendientes con vencimiento en próximos 30 días (incluyendo vencidas)
        cuotas = (
            ORMAccessService.filter(
                Cuota,
                matricula__colegio_id=rbd,
                matricula__estado="ACTIVA",
                matricula__ciclo_academico_id=ciclo_activo_id,
                estado__in=["PENDIENTE", "PAGADA_PARCIAL", "VENCIDA"],
                fecha_vencimiento__lte=fecha_limite,
            )
            .select_related("matricula__estudiante", "matricula__curso")
            .order_by("fecha_vencimiento")
        )

        # Preparar lista de cuotas
        cuotas_list = []
        meses = {
            1: "Enero",
            2: "Febrero",
            3: "Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Septiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre",
        }

        for cuota in cuotas:
            dias_para_vencer = (cuota.fecha_vencimiento - hoy).days

            # Determinar urgencia
            if dias_para_vencer < 0:
                urgencia = "vencida"
                urgencia_label = "Vencida"
            elif dias_para_vencer <= 7:
                urgencia = "urgente"
                urgencia_label = "Urgente"
            elif dias_para_vencer <= 30:
                urgencia = "proxima"
                urgencia_label = "Próxima"
            else:
                urgencia = "normal"
                urgencia_label = "Normal"

            estudiante = cuota.matricula.estudiante
            curso = cuota.matricula.curso

            cuotas_list.append(
                {
                    "id": cuota.id,
                    "numero_cuota": cuota.numero_cuota,
                    "monto_final": float(cuota.monto_final),
                    "fecha_vencimiento": cuota.fecha_vencimiento.strftime("%Y-%m-%d"),
                    "fecha_vencimiento_formatted": cuota.fecha_vencimiento.strftime("%d/%m/%Y"),
                    "mes": meses.get(cuota.mes, str(cuota.mes)),
                    "anio": cuota.anio,
                    "estudiante": {
                        "nombre": estudiante.get_full_name() if estudiante else "Sin nombre",
                        "rut": getattr(estudiante, "rut", None) or "Sin RUT",
                    },
                    "curso": {"nombre": curso.nombre if curso else "Sin curso"},
                    "urgencia": urgencia,
                    "urgencia_label": urgencia_label,
                    "dias_para_vencer": abs(dias_para_vencer),
                }
            )

        return JsonResponse({"success": True, "cuotas": cuotas_list, "total": len(cuotas_list)})

    except Exception:
        logger.exception("Error al listar cuotas próximas")
        return JsonResponse({"success": False, "error": "Error interno del servidor"}, status=500)

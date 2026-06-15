"""API para gestión de pagos (asesor financiero)."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.matriculas.models import Pago
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required


@jwt_or_session_auth_required
@require_http_methods(["GET"])
def listar_pagos(request):
    """Lista pagos con filtros.

    Endpoint consumido por [frontend/templates/asesor_financiero/pagos.html](frontend/templates/asesor_financiero/pagos.html).
    """

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    if not PolicyService.has_capability(request.user, 'FINANCE_VIEW', school_id=rbd):
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    # Parámetros de filtro
    busqueda = request.GET.get("busqueda", "").strip()
    metodo = request.GET.get("metodo", "")
    estado = request.GET.get("estado", "")
    fecha_desde = request.GET.get("fecha_desde", "")
    fecha_hasta = request.GET.get("fecha_hasta", "")

    # Query base: pagos del colegio
    pagos = (
        ORMAccessService.filter(Pago, cuota__matricula__colegio_id=rbd)
        .select_related("estudiante", "cuota__matricula", "procesado_por")
        .order_by("-fecha_pago")
    )

    # Filtrar por búsqueda (estudiante o comprobante)
    if busqueda:
        pagos = pagos.filter(
            Q(estudiante__nombre__icontains=busqueda)
            | Q(estudiante__apellido_paterno__icontains=busqueda)
            | Q(estudiante__apellido_materno__icontains=busqueda)
            | Q(estudiante__rut__icontains=busqueda)
            | Q(numero_comprobante__icontains=busqueda)
        )

    # Filtrar por método
    if metodo:
        pagos = pagos.filter(metodo_pago=metodo)

    # Filtrar por estado
    if estado:
        pagos = pagos.filter(estado=estado)

    # Filtrar por rango de fechas
    if fecha_desde:
        try:
            fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            pagos = pagos.filter(fecha_pago__gte=fecha_desde_dt)
        except ValueError:
            pass

    if fecha_hasta:
        try:
            fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
            # Incluir todo el día hasta
            fecha_hasta_dt = fecha_hasta_dt + timedelta(days=1)
            pagos = pagos.filter(fecha_pago__lt=fecha_hasta_dt)
        except ValueError:
            pass

    # Limitar resultados
    pagos = pagos[:100]

    # Estadísticas totales
    pagos_total = ORMAccessService.filter(
        Pago,
        cuota__matricula__colegio_id=rbd,
        estado__in=["APROBADO", "PENDIENTE"],
    )

    total_recaudado_hoy = (
        pagos_total.filter(estado="APROBADO").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    )

    pagos_procesados_hoy = pagos_total.count()
    
    # Nota: el campo 'conciliado' no existe en el modelo actual, usar 0 por defecto
    pendientes_conciliacion = 0

    # Preparar datos
    resultados = []
    for pago in pagos:
        estudiante = pago.estudiante
        cuota = pago.cuota

        # Obtener número de cuota
        cuota_numero = getattr(cuota, "numero_cuota", 1) if cuota else 1
        cuota_mes = ""
        if cuota and hasattr(cuota, "mes"):
            meses = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
            }
            cuota_mes = meses.get(cuota.mes, "")

        resultados.append(
            {
                "id": pago.id,
                "estudiante": {
                    "nombre": estudiante.get_full_name() if estudiante else "Sin nombre",
                    "rut": getattr(estudiante, "rut", None) or "Sin RUT",
                },
                "cuota": {
                    "numero": cuota_numero,
                    "mes": cuota_mes,
                },
                "monto_pagado": str(pago.monto or 0),
                "metodo": dict(Pago.METODO_CHOICES).get(pago.metodo_pago, pago.metodo_pago),
                "metodo_code": pago.metodo_pago,
                "estado": dict(Pago.ESTADO_CHOICES).get(pago.estado, pago.estado),
                "estado_code": pago.estado,
                "numero_comprobante": pago.numero_comprobante or "",
                "fecha_pago": timezone.localtime(pago.fecha_pago).strftime("%Y-%m-%d %H:%M"),
                "conciliado": False,  # Campo no disponible en modelo
                "observaciones": pago.observaciones or "",
            }
        )

    return JsonResponse(
        {
            "resultados": resultados,
            "estadisticas": {
                "total_recaudado_hoy": str(total_recaudado_hoy),
                "pagos_procesados_hoy": pagos_procesados_hoy,
                "pendientes_conciliacion": pendientes_conciliacion,
            },
            "metodos": [{"code": code, "label": label} for code, label in Pago.METODO_CHOICES],
            "estados": [{"code": code, "label": label} for code, label in Pago.ESTADO_CHOICES],
        }
    )

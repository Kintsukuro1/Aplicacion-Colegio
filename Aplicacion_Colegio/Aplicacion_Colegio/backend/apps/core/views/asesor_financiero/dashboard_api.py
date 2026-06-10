from __future__ import annotations

import logging
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.apps.institucion.models import CicloAcademico
from backend.apps.matriculas.models import Beca, Cuota, Matricula, Pago
from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


@jwt_or_session_auth_required
@require_http_methods(["GET"])
def dashboard_kpis(request):
    """KPIs del dashboard financiero para asesor financiero.

    Endpoint consumido por [frontend/templates/asesor_financiero/dashboard.html](frontend/templates/asesor_financiero/dashboard.html).
    """

    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Autenticación requerida"}, status=401)

    has_finance_access = PolicyService.has_capability(request.user, 'FINANCE_VIEW')
    if not has_finance_access:
        # Fallback legado: permisos heredados del módulo financiero
        has_finance_access = PermissionService.has_permission(
            request.user,
            'FINANCIERO',
            'VIEW_FINANCIAL_DASHBOARD',
        )
    if not has_finance_access:
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    try:
        hoy_dt = timezone.localtime(timezone.now())
        hoy = hoy_dt.date()
        mes_actual = hoy_dt.month
        anio_actual = hoy_dt.year

        # Detectar año escolar activo (el más reciente con matrículas)
        ciclo_activo = (
            ORMAccessService.filter(CicloAcademico, colegio_id=rbd, estado="ACTIVO")
            .order_by("-fecha_inicio", "-id")
            .first()
        )

        cuotas = ORMAccessService.filter(Cuota, matricula__colegio_id=rbd)

        cuotas_pagadas = cuotas.filter(estado="PAGADA").count()

        cuotas_vencidas_qs = cuotas.filter(
            Q(estado="VENCIDA")
            | (
                Q(estado__in=["PENDIENTE", "PAGADA_PARCIAL"]) & Q(fecha_vencimiento__lt=hoy)
            )
        )
        cuotas_vencidas = cuotas_vencidas_qs.count()

        cuotas_pendientes = (
            cuotas.filter(estado__in=["PENDIENTE", "PAGADA_PARCIAL"]).exclude(id__in=cuotas_vencidas_qs)
        ).count()

        cuotas_total = cuotas.count()

        pagos_mes = (
            ORMAccessService.filter(
                Pago,
                cuota__matricula__colegio_id=rbd,
                fecha_pago__year=anio_actual,
                fecha_pago__month=mes_actual,
                estado="APROBADO",
            ).aggregate(total=Coalesce(Sum("monto"), Value(Decimal("0"))))
        )["total"]

        stats = cuotas.aggregate(
            facturado=Coalesce(Sum("monto_final"), Value(Decimal("0"))),
            pagado=Coalesce(Sum("monto_pagado"), Value(Decimal("0"))),
        )
        total_facturado = stats["facturado"]
        total_pagado = stats["pagado"]

        tasa_cobro = 0.0
        if total_facturado and total_facturado > 0:
            tasa_cobro = float((total_pagado / total_facturado) * 100)

        deuda_vencida = (
            cuotas_vencidas_qs.annotate(
                saldo=Coalesce(
                    F("monto_final") - F("monto_pagado"),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ).aggregate(total=Coalesce(Sum("saldo"), Value(Decimal("0"))))
        )["total"]

        mora_promedio = 0.0
        if cuotas_vencidas > 0:
            fechas = list(cuotas_vencidas_qs.values_list("fecha_vencimiento", flat=True))
            if fechas:
                dias_mora_total = sum((hoy - f).days for f in fechas)
                mora_promedio = dias_mora_total / len(fechas)

        matriculas_deudoras = (
            ORMAccessService.filter(Matricula, colegio_id=rbd, estado="ACTIVA")
            .select_related("estudiante")
            .annotate(
                total_facturado=Coalesce(
                    Sum("cuotas__monto_final"), Value(Decimal("0")), output_field=DecimalField(max_digits=12, decimal_places=2)
                ),
                total_pagado=Coalesce(
                    Sum("cuotas__monto_pagado"), Value(Decimal("0")), output_field=DecimalField(max_digits=12, decimal_places=2)
                ),
            )
            .annotate(
                saldo=Coalesce(
                    F("total_facturado") - F("total_pagado"),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
            .filter(saldo__gt=0)
            .order_by("-saldo")[:5]
        )

        deudores = [
            {
                "estudiante": m.estudiante.get_full_name() if m.estudiante else "(Sin estudiante)",
                "saldo": int(m.saldo or 0),
            }
            for m in matriculas_deudoras
        ]

        pagos_recientes = (
            ORMAccessService.filter(
                Pago,
                cuota__matricula__colegio_id=rbd,
                fecha_pago__date=hoy,
                estado="APROBADO",
            )
            .select_related("cuota__matricula__estudiante")
            .order_by("-fecha_pago")[:10]
        )

        pagos_list = []
        for pago in pagos_recientes:
            estudiante = pago.cuota.matricula.estudiante if pago.cuota_id else pago.estudiante
            pagos_list.append(
                {
                    "estudiante": estudiante.get_full_name() if estudiante else "(Sin estudiante)",
                    "monto": int(pago.monto or 0),
                    "metodo": pago.metodo_pago,
                    "hora": timezone.localtime(pago.fecha_pago).strftime("%H:%M"),
                }
            )

        # Becas: conteos por estado + monto estimado mensual (valor_mensual * %)
        # Filtrar por año escolar activo si está disponible
        becas_filter = {"matricula__colegio_id": rbd}
        if ciclo_activo:
            becas_filter["matricula__ciclo_academico"] = ciclo_activo
        
        becas_aprobadas_qs = ORMAccessService.filter(Beca, **becas_filter, estado="APROBADA")
        becas_pendientes_qs = ORMAccessService.filter(Beca, **becas_filter, estado="PENDIENTE")

        becas_activas = becas_aprobadas_qs.count()
        becas_pendientes = becas_pendientes_qs.count()

        monto_becas = 0
        for beca in becas_aprobadas_qs.select_related("matricula"):
            base = getattr(beca.matricula, "valor_mensual", 0) or 0
            try:
                monto_becas += int((Decimal(base) * (beca.porcentaje_descuento / Decimal("100"))).quantize(Decimal("1")))
            except Exception:
                continue

        metodos_pago = (
            ORMAccessService.filter(Pago, cuota__matricula__colegio_id=rbd, estado="APROBADO")
            .values("metodo_pago")
            .annotate(total=Coalesce(Sum("monto"), Value(Decimal("0"))), cantidad=Count("id"))
            .order_by("-total")
        )

        metodos_list = [
            {
                "metodo": m["metodo_pago"],
                "total": int(m["total"] or 0),
                "cantidad": m["cantidad"],
            }
            for m in metodos_pago
        ]

        return JsonResponse(
            {
                "success": True,
                "ingresos_mes": int(pagos_mes or 0),
                "tasa_cobro": tasa_cobro,
                "mora_promedio": mora_promedio,
                "deuda_vencida": int(deuda_vencida or 0),
                "cuotas_pagadas": cuotas_pagadas,
                "cuotas_pendientes": cuotas_pendientes,
                "cuotas_vencidas": cuotas_vencidas,
                "cuotas_total": cuotas_total,
                "deudores": deudores,
                "pagos_recientes": pagos_list,
                "becas_activas": becas_activas,
                "becas_pendientes": becas_pendientes,
                "monto_becas": monto_becas,
                "metodos_pago": metodos_list,
            }
        )

    except Exception:
        logger.exception("Error al construir dashboard de cobranzas")
        return JsonResponse({"success": False, "error": "Error interno del servidor"}, status=500)


@PermissionService.require_permission('FINANCIERO', 'VIEW_FINANCIAL_DASHBOARD')
@jwt_or_session_auth_required
@require_http_methods(["GET"])
def dashboard_estadisticas(request):
    """Estadísticas básicas del dashboard de inicio para asesor financiero.

    Endpoint consumido por [frontend/templates/asesor_financiero/inicio.html](frontend/templates/asesor_financiero/inicio.html).
    """

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    try:
        hoy_dt = timezone.localtime(timezone.now())
        mes_actual = hoy_dt.month
        anio_actual = hoy_dt.year

        # Total facturado del mes actual (suma de cuotas del mes)
        cuotas_mes = ORMAccessService.filter(
            Cuota,
            matricula__colegio_id=rbd,
            anio=anio_actual,
            mes=mes_actual
        ).aggregate(
            total=Coalesce(Sum('monto_final'), Value(Decimal('0')))
        )['total']

        # Pagos recibidos del mes actual
        pagos_mes = ORMAccessService.filter(
            Pago,
            cuota__matricula__colegio_id=rbd,
            fecha_pago__year=anio_actual,
            fecha_pago__month=mes_actual,
            estado='APROBADO'
        ).aggregate(
            total=Coalesce(Sum('monto'), Value(Decimal('0')))
        )['total']

        # Saldo pendiente (total facturado - total pagado de todas las cuotas)
        stats = ORMAccessService.filter(
            Cuota,
            matricula__colegio_id=rbd
        ).aggregate(
            facturado=Coalesce(Sum('monto_final'), Value(Decimal('0'))),
            pagado=Coalesce(Sum('monto_pagado'), Value(Decimal('0')))
        )
        saldo_pendiente = stats['facturado'] - stats['pagado']

        # Cuotas vencidas
        cuotas_vencidas = ORMAccessService.filter(
            Cuota,
            matricula__colegio_id=rbd,
            estado__in=['PENDIENTE', 'PAGADA_PARCIAL'],
            fecha_vencimiento__lt=hoy_dt.date()
        ).count()

        return JsonResponse({
            'success': True,
            'total_facturado': float(cuotas_mes),
            'pagos_recibidos': float(pagos_mes),
            'saldo_pendiente': float(saldo_pendiente),
            'cuotas_vencidas': cuotas_vencidas,
        })

    except Exception:
        logger.exception("Error al obtener estadísticas del dashboard financiero")
        return JsonResponse({"success": False, "error": "Error interno del servidor"}, status=500)

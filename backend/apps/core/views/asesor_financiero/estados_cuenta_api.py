"""API para gestión de estados de cuenta (asesor financiero)."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.common.utils.auth_helpers import normalizar_rol
from backend.apps.matriculas.models import Matricula
from backend.apps.cursos.models import Curso
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.common.services import PermissionService
from backend.common.utils.view_auth import jwt_or_session_auth_required


@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'VIEW_ACCOUNT_STATEMENTS')
@require_http_methods(["GET"])
def listar_estados_cuenta(request):
    """Lista matrículas con estado financiero y filtros.

    Endpoint consumido por [frontend/templates/asesor_financiero/estados_cuenta.html](frontend/templates/asesor_financiero/estados_cuenta.html).
    """

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    # Parámetros de filtro
    estudiante_query = request.GET.get("estudiante", "").strip()
    curso_id = request.GET.get("curso", "")
    estado_filtro = request.GET.get("estado", "")
    orden = request.GET.get("orden", "nombre")
    anio_param = request.GET.get("anio", "")

    # Determinar año escolar activo dinámicamente
    if anio_param:
        try:
            anio_actual = int(anio_param)
        except ValueError:
            anio_actual = None
    else:
        # Buscar el año más reciente con matrículas activas
        anio_actual = (
            ORMAccessService.filter(Matricula, colegio_id=rbd, estado="ACTIVA")
            .values_list("anio_escolar", flat=True)
            .order_by("-anio_escolar")
            .first()
        )
    
    if not anio_actual:
        return JsonResponse(
            {
                "resultados": [],
                "cursos": [],
                "filtros": {},
                "estadisticas": {
                    "total_al_dia": 0,
                    "total_atrasado": 0,
                    "total_moroso": 0,
                    "saldo_total_pendiente": "0",
                },
            }
        )

    # Query base: matrículas activas
    matriculas = (
        ORMAccessService.filter(
            Matricula,
            anio_escolar=anio_actual,
            estado="ACTIVA",
            colegio_id=rbd,
        )
        .select_related("estudiante", "curso")
        .prefetch_related("cuotas")
    )

    # Filtrar por estudiante (nombre/RUT)
    if estudiante_query:
        matriculas = matriculas.filter(
            Q(estudiante__nombre__icontains=estudiante_query)
            | Q(estudiante__apellido_paterno__icontains=estudiante_query)
            | Q(estudiante__apellido_materno__icontains=estudiante_query)
            | Q(estudiante__rut__icontains=estudiante_query)
        )

    # Filtrar por curso
    if curso_id:
        try:
            matriculas = matriculas.filter(curso_id=int(curso_id))
        except ValueError:
            pass

    # Calcular estado financiero de cada matrícula
    resultados = []
    total_al_dia = 0
    total_atrasado = 0
    total_moroso = 0
    saldo_total_pendiente = Decimal("0")

    hoy = timezone.now().date()

    for matricula in matriculas:
        total_facturado = matricula.cuotas.aggregate(total=Sum("monto_final"))["total"] or Decimal("0")
        total_pagado = matricula.cuotas.aggregate(total=Sum("monto_pagado"))["total"] or Decimal("0")
        saldo = total_facturado - total_pagado

        # Cuotas vencidas
        cuotas_vencidas = matricula.cuotas.filter(fecha_vencimiento__lt=hoy).exclude(estado="PAGADA")

        dias_mora = 0
        if cuotas_vencidas.exists():
            cuota_mas_antigua = cuotas_vencidas.order_by("fecha_vencimiento").first()
            dias_mora = (hoy - cuota_mas_antigua.fecha_vencimiento).days

        # Clasificar estado
        if saldo <= 0:
            estado_pago = "al_dia"
            estado_label = "✅ Al día"
            estado_class = "success"
            total_al_dia += 1
        elif dias_mora >= 30:
            estado_pago = "moroso"
            estado_label = f"🚨 Moroso ({dias_mora} días)"
            estado_class = "danger"
            total_moroso += 1
            saldo_total_pendiente += saldo
        elif dias_mora > 0:
            estado_pago = "atrasado"
            estado_label = f"⚠️ Atrasado ({dias_mora} días)"
            estado_class = "warning"
            total_atrasado += 1
            saldo_total_pendiente += saldo
        else:
            estado_pago = "al_dia"
            estado_label = "✅ Al día"
            estado_class = "success"
            total_al_dia += 1

        # Filtrar por estado
        if estado_filtro and estado_filtro != estado_pago:
            continue

        # Nombre estudiante
        nombre_completo = matricula.estudiante.get_full_name() if matricula.estudiante else "Sin nombre"
        partes = nombre_completo.split(" ", 1)
        first_name = partes[0] if partes else ""
        last_name = partes[1] if len(partes) > 1 else ""

        resultados.append(
            {
                "matricula": {"id": matricula.id},
                "estudiante": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "rut": getattr(matricula.estudiante, "rut", None) or "Sin RUT",
                },
                "curso": {"nombre": matricula.curso.nombre if matricula.curso else "Sin curso"},
                "total_facturado": str(total_facturado),
                "total_pagado": str(total_pagado),
                "saldo": str(saldo),
                "dias_mora": dias_mora,
                "estado_pago": estado_pago,
                "estado_label": estado_label,
                "estado_class": estado_class,
            }
        )

    # Ordenar
    if orden == "deuda":
        resultados.sort(key=lambda x: float(x["saldo"]), reverse=True)
    elif orden == "dias_mora":
        resultados.sort(key=lambda x: x["dias_mora"], reverse=True)
    else:
        resultados.sort(key=lambda x: f"{x['estudiante']['first_name']} {x['estudiante']['last_name']}")

    # Cursos disponibles
    cursos = list(
        ORMAccessService.filter(Curso, colegio_id=rbd, anio_escolar=anio_actual, activo=True)
        .order_by("nombre")
        .values("id_curso", "nombre")
    )

    return JsonResponse(
        {
            "resultados": resultados,
            "cursos": cursos,
            "anio_escolar": anio_actual,
            "filtros": {
                "estudiante": estudiante_query,
                "curso": curso_id,
                "estado": estado_filtro,
                "orden": orden,
                "anio": str(anio_actual),
            },
            "estadisticas": {
                "total_al_dia": total_al_dia,
                "total_atrasado": total_atrasado,
                "total_moroso": total_moroso,
                "saldo_total_pendiente": str(saldo_total_pendiente),
            },
        }
    )

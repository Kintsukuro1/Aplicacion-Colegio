"""API endpoints para gestión de finanzas — Admin Escolar.

Endpoints:
- registrar_pago_manual: POST — Registra un pago manual contra una cuota.
- listar_cuotas_estudiante: GET — Lista las cuotas de una matrícula.
- listar_cuotas_ciclo: GET — Lista cuotas del ciclo activo (panel admin).
- condonar_cuota: POST — Condona una cuota cambiando su estado.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.apps.institucion.models import CicloAcademico
from backend.apps.matriculas.models import Cuota, Pago
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)

MESES_CUOTA = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _effective_cuota_estado(cuota, hoy):
    if cuota.estado in ("PAGADA", "CONDONADA"):
        return cuota.estado
    if cuota.fecha_vencimiento < hoy and cuota.estado in ("PENDIENTE", "PAGADA_PARCIAL"):
        return "VENCIDA"
    return cuota.estado


def _serialize_cuota_admin(cuota, hoy):
    estudiante = cuota.matricula.estudiante
    estado_code = _effective_cuota_estado(cuota, hoy)
    return {
        "id": cuota.id,
        "numero_cuota": cuota.numero_cuota,
        "mes": MESES_CUOTA.get(cuota.mes, str(cuota.mes)),
        "anio": cuota.anio,
        "monto_original": int(cuota.monto_original),
        "monto_descuento": int(cuota.monto_descuento),
        "monto_final": int(cuota.monto_final),
        "monto_pagado": int(cuota.monto_pagado),
        "saldo_pendiente": int(cuota.saldo_pendiente()),
        "estado": cuota.get_estado_display(),
        "estado_code": estado_code,
        "fecha_vencimiento": cuota.fecha_vencimiento.strftime("%Y-%m-%d"),
        "estudiante_nombre": estudiante.get_full_name() if estudiante else "Sin nombre",
        "estudiante_rut": getattr(estudiante, "rut", None) or "",
        "curso_nombre": str(cuota.matricula.curso) if cuota.matricula.curso else "Sin curso",
    }


@require_http_methods(["POST"])
@jwt_or_session_auth_required
def registrar_pago_manual(request):
    """Register a manual payment against a specific fee (cuota).

    Validates tenant boundaries, prevents overpayment, and updates cuota
    state machine (PENDIENTE -> PAGADA_PARCIAL -> PAGADA).
    """

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    if not PolicyService.has_capability(request.user, "FINANCE_MANAGE_PAYMENTS", school_id=rbd):
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Datos JSON inválidos"}, status=400)

    cuota_id = data.get("cuota_id")
    monto_raw = data.get("monto")
    metodo_pago = data.get("metodo_pago", "EFECTIVO")
    numero_comprobante = data.get("numero_comprobante", "")
    observaciones = data.get("observaciones", "")

    if not cuota_id or not monto_raw:
        return JsonResponse({"success": False, "error": "cuota_id y monto son requeridos"}, status=400)

    try:
        monto = Decimal(str(monto_raw))
        if monto <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return JsonResponse({"success": False, "error": "El monto debe ser un número positivo"}, status=400)

    # Validate payment method
    metodos_validos = {code for code, _ in Pago.METODO_CHOICES}
    if metodo_pago not in metodos_validos:
        return JsonResponse({"success": False, "error": f"Método de pago inválido: {metodo_pago}"}, status=400)

    try:
        # Fetch cuota with tenant boundary check
        cuota = ORMAccessService.filter(
            Cuota,
            id=cuota_id,
            matricula__colegio_id=rbd,
        ).select_related("matricula__estudiante").get()
    except Cuota.DoesNotExist:
        return JsonResponse({"success": False, "error": "Cuota no encontrada o no pertenece a este colegio"}, status=404)

    # Validate cuota is payable
    if cuota.estado in ("PAGADA", "CONDONADA"):
        return JsonResponse({"success": False, "error": f"La cuota ya está {cuota.get_estado_display()}"}, status=400)

    # Prevent overpayment
    saldo = cuota.saldo_pendiente()
    if monto > saldo:
        return JsonResponse({
            "success": False,
            "error": f"El monto (${int(monto)}) excede el saldo pendiente (${int(saldo)})",
        }, status=400)

    try:
        # Create payment record
        pago = Pago.objects.create(
            cuota=cuota,
            estudiante=cuota.matricula.estudiante,
            monto=monto,
            metodo_pago=metodo_pago,
            numero_comprobante=numero_comprobante or None,
            estado="APROBADO",
            fecha_pago=timezone.now(),
            procesado_por=request.user,
            fecha_procesamiento=timezone.now(),
            observaciones=observaciones or None,
        )

        # Update cuota balance
        cuota.monto_pagado = cuota.monto_pagado + monto
        if cuota.monto_pagado >= cuota.monto_final:
            cuota.estado = "PAGADA"
            cuota.fecha_pago_completo = timezone.now()
        elif cuota.monto_pagado > 0:
            cuota.estado = "PAGADA_PARCIAL"
        cuota.save()

        return JsonResponse({
            "success": True,
            "message": "Pago registrado exitosamente",
            "pago": {
                "id": pago.id,
                "monto": int(pago.monto),
                "metodo": pago.get_metodo_pago_display(),
                "fecha": timezone.localtime(pago.fecha_pago).strftime("%d/%m/%Y %H:%M"),
            },
            "cuota": {
                "id": cuota.id,
                "monto_pagado": int(cuota.monto_pagado),
                "saldo_pendiente": int(cuota.saldo_pendiente()),
                "estado": cuota.get_estado_display(),
            },
        })

    except Exception:
        logger.exception("Error al registrar pago manual")
        return JsonResponse({"success": False, "error": "Error interno del servidor"}, status=500)


@require_http_methods(["GET"])
@jwt_or_session_auth_required
def listar_cuotas_estudiante(request):
    """List fees for a specific enrollment (matrícula)."""

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    if not PolicyService.has_capability(request.user, "FINANCE_VIEW", school_id=rbd):
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    matricula_id = request.GET.get("matricula_id")
    if not matricula_id:
        return JsonResponse({"success": False, "error": "matricula_id es requerido"}, status=400)

    cuotas = (
        ORMAccessService.filter(
            Cuota,
            matricula_id=matricula_id,
            matricula__colegio_id=rbd,
        )
        .order_by("anio", "mes", "numero_cuota")
    )

    hoy = timezone.localtime(timezone.now()).date()
    cuotas_list = []
    for cuota in cuotas:
        item = _serialize_cuota_admin(cuota, hoy)
        item["fecha_vencimiento"] = cuota.fecha_vencimiento.strftime("%d/%m/%Y")
        cuotas_list.append(item)

    return JsonResponse({
        "success": True,
        "cuotas": cuotas_list,
        "total": len(cuotas_list),
    })


@require_http_methods(["GET"])
@jwt_or_session_auth_required
def listar_cuotas_ciclo(request):
    """Lista cuotas del ciclo académico activo para el panel admin escolar."""

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    if not PolicyService.has_capability(request.user, "FINANCE_VIEW", school_id=rbd):
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    ciclo_activo = CicloAcademico.objects.filter(
        colegio_id=rbd, estado="ACTIVO"
    ).order_by("-fecha_inicio", "-id").first()

    if not ciclo_activo:
        return JsonResponse({"success": True, "cuotas": [], "total": 0})

    hoy = timezone.localtime(timezone.now()).date()
    filtro_estado = (request.GET.get("estado") or "").strip().upper()
    filtro_busqueda = (request.GET.get("busqueda") or "").strip().lower()

    cuotas = (
        ORMAccessService.filter(
            Cuota,
            matricula__colegio_id=rbd,
            matricula__estado="ACTIVA",
            matricula__ciclo_academico=ciclo_activo,
        )
        .select_related("matricula__estudiante", "matricula__curso")
        .order_by("-anio", "-mes", "matricula__estudiante__apellido_paterno")
    )

    cuotas_list = []
    for cuota in cuotas:
        item = _serialize_cuota_admin(cuota, hoy)
        if filtro_estado and item["estado_code"] != filtro_estado:
            continue
        if filtro_busqueda:
            nombre = item["estudiante_nombre"].lower()
            rut = (item["estudiante_rut"] or "").lower()
            if filtro_busqueda not in nombre and filtro_busqueda not in rut:
                continue
        cuotas_list.append(item)

    return JsonResponse({
        "success": True,
        "cuotas": cuotas_list,
        "total": len(cuotas_list),
        "ciclo": ciclo_activo.nombre,
    })


@require_http_methods(["POST"])
@jwt_or_session_auth_required
def condonar_cuota(request):
    """Forgive a fee by transitioning its state to CONDONADA."""

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    if not PolicyService.has_capability(request.user, "FINANCE_MANAGE_PAYMENTS", school_id=rbd):
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Datos JSON inválidos"}, status=400)

    cuota_id = data.get("cuota_id")
    motivo = data.get("motivo", "").strip()

    if not cuota_id:
        return JsonResponse({"success": False, "error": "cuota_id es requerido"}, status=400)

    if not motivo:
        return JsonResponse({"success": False, "error": "Se requiere un motivo para la condonación"}, status=400)

    try:
        cuota = ORMAccessService.filter(
            Cuota,
            id=cuota_id,
            matricula__colegio_id=rbd,
        ).get()
    except Cuota.DoesNotExist:
        return JsonResponse({"success": False, "error": "Cuota no encontrada o no pertenece a este colegio"}, status=404)

    if cuota.estado in ("PAGADA", "CONDONADA"):
        return JsonResponse({"success": False, "error": f"La cuota ya está {cuota.get_estado_display()}"}, status=400)

    cuota.estado = "CONDONADA"
    cuota.observaciones = f"[CONDONADA por {request.user.get_full_name()}] {motivo}"
    cuota.save()

    return JsonResponse({
        "success": True,
        "message": "Cuota condonada exitosamente",
        "cuota": {
            "id": cuota.id,
            "estado": cuota.get_estado_display(),
        },
    })

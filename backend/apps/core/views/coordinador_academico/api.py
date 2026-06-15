import json
import logging
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.coordinador_academico_api_service import CoordinadorAcademicoApiService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


def _get_rbd(request):
    return getattr(request.user, 'rbd_colegio', None)


@jwt_or_session_auth_required
@require_http_methods(['GET'])
def listar_planificaciones(request):
    """Lista planificaciones pendientes de aprobación para acciones rápidas."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    can_view = (
        PolicyService.has_capability(request.user, 'PLANNING_VIEW', school_id=rbd)
        or PolicyService.has_capability(request.user, 'PLANNING_APPROVE', school_id=rbd)
    )
    if not can_view:
        return JsonResponse({'success': False, 'error': 'Sin permisos para ver planificaciones'}, status=403)

    try:
        data = CoordinadorAcademicoApiService.list_planificaciones_pendientes(rbd)
        return JsonResponse({'success': True, 'planificaciones': data})
    except Exception:
        logger.exception('Error listando planificaciones')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def actualizar_estado_planificacion(request, planificacion_id):
    """Actualiza el estado de una planificación (Aprobada/Rechazada)."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    # Permiso para revisar/aprobar planificaciones (capability canónica)
    if not PolicyService.has_capability(request.user, 'PLANNING_APPROVE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para revisar planificaciones'}, status=403)

    try:
        body = json.loads(request.body)
        nuevo_estado = body.get('estado', '').upper()
        observaciones = body.get('observaciones', '').strip()

        estados_validos = {'APROBADA', 'RECHAZADA'}
        if nuevo_estado not in estados_validos:
            return JsonResponse({'success': False, 'error': 'Estado inválido'}, status=400)

        planificacion = CoordinadorAcademicoApiService.get_planificacion_or_none(planificacion_id, rbd)
        if planificacion is None:
            return JsonResponse({'success': False, 'error': 'Planificación no encontrada'}, status=404)

        CoordinadorAcademicoApiService.actualizar_estado_planificacion(
            planificacion,
            nuevo_estado=nuevo_estado,
            observaciones=observaciones,
            aprobado_por=request.user,
            fecha_aprobacion=timezone.now(),
        )

        return JsonResponse({
            'success': True,
            'message': f'Planificación {nuevo_estado} correctamente',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error actualizando estado de planificación')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)

"""
API endpoints para Inspector de Convivencia.
- Crear/listar anotaciones de convivencia
- Aprobar/rechazar justificativos de inasistencia
"""
import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.auditoria.models import AuditoriaEvento
from backend.apps.core.services.inspector_convivencia_api_service import InspectorConvivenciaApiService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


def _get_rbd(request):
    return resolve_request_rbd(request)


@jwt_or_session_auth_required
@require_http_methods(['GET'])
def listar_estudiantes(request):
    """Retorna lista de estudiantes del colegio para selectores."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'STUDENT_VIEW', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = InspectorConvivenciaApiService.list_estudiantes(rbd)
        return JsonResponse({'success': True, 'estudiantes': data})
    except Exception:
        logger.exception('Error listando estudiantes')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['GET'])
def listar_justificativos(request):
    """Retorna justificativos pendientes para revisión rápida."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'JUSTIFICATION_APPROVE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para revisar justificativos'}, status=403)

    try:
        data = InspectorConvivenciaApiService.list_justificativos_pendientes(rbd)
        return JsonResponse({'success': True, 'justificativos': data})
    except Exception:
        logger.exception('Error listando justificativos')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def crear_anotacion(request):
    """Crea una nueva anotación de convivencia."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'DISCIPLINE_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para crear anotaciones'}, status=403)

    try:
        body = json.loads(request.body)
        estudiante_id = body.get('estudiante_id')
        tipo = body.get('tipo', 'NEUTRA')
        categoria = body.get('categoria', 'OTRO')
        descripcion = (body.get('descripcion') or '').strip()
        gravedad = int(body.get('gravedad', 1))

        if not estudiante_id:
            return JsonResponse({'success': False, 'error': 'Debe seleccionar un estudiante'}, status=400)
        if not descripcion:
            return JsonResponse({'success': False, 'error': 'La descripción es obligatoria'}, status=400)

        try:
            estudiante = InspectorConvivenciaApiService.get_estudiante_or_none(int(estudiante_id), rbd)
        except (ValueError, TypeError):
            estudiante = None
        if not estudiante:
            return JsonResponse({'success': False, 'error': 'Estudiante no encontrado'}, status=404)

        anotacion = InspectorConvivenciaApiService.crear_anotacion(
            estudiante=estudiante,
            rbd=rbd,
            tipo=tipo,
            categoria=categoria,
            descripcion=descripcion,
            gravedad=gravedad,
            registrado_por=request.user,
        )

        AuditoriaEvento.registrar_evento(
            usuario=request.user,
            accion=AuditoriaEvento.CREAR,
            tabla_afectada='anotacion_convivencia',
            descripcion=f"Creación de anotación de convivencia {tipo.lower()} para el estudiante",
            categoria=AuditoriaEvento.CATEGORIA_ESTUDIANTES,
            content_object=anotacion,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            nivel=AuditoriaEvento.NIVEL_INFO,
            metadata={
                'anotacion_id': anotacion.id_anotacion,
                'estudiante_id': estudiante.id,
                'tipo': tipo,
                'categoria': categoria,
                'gravedad': gravedad,
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Anotación registrada correctamente',
            'id': anotacion.id_anotacion,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error creando anotación')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def actualizar_justificativo(request, justificativo_id):
    """Aprueba o rechaza un justificativo de inasistencia."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'JUSTIFICATION_APPROVE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para aprobar justificativos'}, status=403)

    try:
        body = json.loads(request.body)
        nuevo_estado = body.get('estado', '').upper()

        if nuevo_estado not in ('APROBADO', 'RECHAZADO'):
            return JsonResponse({'success': False, 'error': 'Estado inválido'}, status=400)

        try:
            justificativo = InspectorConvivenciaApiService.get_justificativo_or_none(justificativo_id, rbd)
        except Exception:
            justificativo = None
        if not justificativo:
            return JsonResponse({'success': False, 'error': 'Justificativo no encontrado'}, status=404)

        if justificativo.estado != 'PENDIENTE':
            return JsonResponse(
                {'success': False, 'error': 'Solo se pueden revisar justificativos pendientes'},
                status=400,
            )

        InspectorConvivenciaApiService.actualizar_justificativo(
            justificativo,
            nuevo_estado=nuevo_estado,
            revisado_por=request.user,
            observaciones=body.get('observaciones', ''),
        )

        AuditoriaEvento.registrar_evento(
            usuario=request.user,
            accion=AuditoriaEvento.MODIFICAR,
            tabla_afectada='justificativo_inasistencia',
            descripcion=f"Resolución de justificativo de inasistencia: {nuevo_estado.lower()}",
            categoria=AuditoriaEvento.CATEGORIA_ASISTENCIA,
            content_object=justificativo,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            nivel=AuditoriaEvento.NIVEL_INFO,
            metadata={
                'justificativo_id': justificativo.id_justificativo,
                'estado': nuevo_estado,
                'observaciones': body.get('observaciones', ''),
            }
        )

        return JsonResponse({
            'success': True,
            'message': f'Justificativo {nuevo_estado.lower()} correctamente',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error actualizando justificativo')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def registrar_atraso(request):
    """Registra un atraso ('T' - Tardanza) para un estudiante en una clase específica."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'DISCIPLINE_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para registro de atrasos'}, status=403)

    try:
        body = json.loads(request.body)
        estudiante_id = body.get('estudiante_id')
        clase_id = body.get('clase_id')
        fecha = body.get('fecha')
        observaciones = body.get('observaciones', '').strip()

        if not estudiante_id or not clase_id or not fecha:
            return JsonResponse({'success': False, 'error': 'Debe seleccionar estudiante, clase y fecha'}, status=400)

        estudiante = InspectorConvivenciaApiService.get_estudiante_or_none(int(estudiante_id), rbd)
        clase = InspectorConvivenciaApiService.get_clase_or_none(clase_id, rbd)
        if not estudiante or not clase:
            return JsonResponse({'success': False, 'error': 'Estudiante o clase no encontrado'}, status=404)

        asistencia = InspectorConvivenciaApiService.registrar_atraso(
            rbd=rbd,
            clase=clase,
            estudiante=estudiante,
            fecha=fecha,
            observaciones=observaciones,
        )

        AuditoriaEvento.registrar_evento(
            usuario=request.user,
            accion=AuditoriaEvento.CREAR,
            tabla_afectada='asistencia',
            descripcion="Registro de atraso de estudiante en clase",
            categoria=AuditoriaEvento.CATEGORIA_ASISTENCIA,
            content_object=asistencia,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            nivel=AuditoriaEvento.NIVEL_INFO,
            metadata={
                'asistencia_id': asistencia.id_asistencia,
                'estudiante_id': estudiante.id,
                'clase_id': clase.id,
                'fecha': fecha if isinstance(fecha, str) else fecha.isoformat(),
                'estado': 'T',
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Atraso registrado correctamente',
            'id': asistencia.id_asistencia,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error registrando atraso')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)

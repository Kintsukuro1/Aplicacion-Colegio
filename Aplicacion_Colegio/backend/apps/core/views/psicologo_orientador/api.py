"""
API endpoints para Psicólogo Orientador.
- Crear entrevistas de orientación
- Crear / actualizar derivaciones externas
"""
import json
import logging
from datetime import date

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.psicologo_orientador_api_service import PsicologoOrientadorApiService
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
        data = PsicologoOrientadorApiService.list_estudiantes(rbd)
        return JsonResponse({'success': True, 'estudiantes': data})
    except Exception:
        logger.exception('Error listando estudiantes')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def crear_entrevista(request):
    """Crea una nueva entrevista de orientación."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'COUNSELING_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para registrar entrevistas'}, status=403)

    try:
        body = json.loads(request.body)
        estudiante_id = body.get('estudiante_id')
        fecha = body.get('fecha')
        motivo = body.get('motivo', 'ACADEMICO')
        observaciones = (body.get('observaciones') or '').strip()
        acuerdos = (body.get('acuerdos') or '').strip()
        seguimiento = bool(body.get('seguimiento_requerido', False))
        fecha_siguiente = body.get('fecha_siguiente_sesion') or None

        if not estudiante_id:
            return JsonResponse({'success': False, 'error': 'Debe seleccionar un estudiante'}, status=400)
        if not fecha:
            return JsonResponse({'success': False, 'error': 'La fecha es obligatoria'}, status=400)
        if not observaciones:
            return JsonResponse({'success': False, 'error': 'Las observaciones son obligatorias'}, status=400)

        try:
            estudiante = PsicologoOrientadorApiService.get_estudiante_or_none(int(estudiante_id), rbd)
        except (ValueError, TypeError):
            estudiante = None
        if not estudiante:
            return JsonResponse({'success': False, 'error': 'Estudiante no encontrado'}, status=404)

        entrevista = PsicologoOrientadorApiService.crear_entrevista(
            estudiante=estudiante,
            rbd=rbd,
            psicologo=request.user,
            fecha=fecha,
            motivo=motivo,
            observaciones=observaciones,
            acuerdos=acuerdos,
            seguimiento=seguimiento,
            fecha_siguiente=fecha_siguiente,
        )

        return JsonResponse({
            'success': True,
            'message': 'Entrevista registrada correctamente',
            'id': entrevista.id_entrevista,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error creando entrevista')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def crear_derivacion(request):
    """Crea una nueva derivación externa."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'REFERRAL_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para crear derivaciones'}, status=403)

    try:
        body = json.loads(request.body)
        estudiante_id = body.get('estudiante_id')
        profesional = (body.get('profesional_destino') or '').strip()
        especialidad = (body.get('especialidad') or '').strip()
        motivo = (body.get('motivo') or '').strip()
        fecha_derivacion = body.get('fecha_derivacion') or str(date.today())

        if not estudiante_id:
            return JsonResponse({'success': False, 'error': 'Debe seleccionar un estudiante'}, status=400)
        if not profesional:
            return JsonResponse({'success': False, 'error': 'El profesional de destino es obligatorio'}, status=400)
        if not especialidad:
            return JsonResponse({'success': False, 'error': 'La especialidad es obligatoria'}, status=400)
        if not motivo:
            return JsonResponse({'success': False, 'error': 'El motivo es obligatorio'}, status=400)

        try:
            estudiante = PsicologoOrientadorApiService.get_estudiante_or_none(int(estudiante_id), rbd)
        except (ValueError, TypeError):
            estudiante = None
        if not estudiante:
            return JsonResponse({'success': False, 'error': 'Estudiante no encontrado'}, status=404)

        derivacion = PsicologoOrientadorApiService.crear_derivacion(
            estudiante=estudiante,
            rbd=rbd,
            derivado_por=request.user,
            profesional=profesional,
            especialidad=especialidad,
            motivo=motivo,
            fecha_derivacion=fecha_derivacion,
        )

        return JsonResponse({
            'success': True,
            'message': 'Derivación registrada correctamente',
            'id': derivacion.id_derivacion,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error creando derivación')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def actualizar_derivacion(request, derivacion_id):
    """Actualiza el estado de una derivación."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'REFERRAL_EDIT', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para editar derivaciones'}, status=403)

    try:
        body = json.loads(request.body)
        nuevo_estado = body.get('estado', '').upper()
        estados_validos = {'PENDIENTE', 'EN_PROCESO', 'COMPLETADA', 'CANCELADA'}

        if nuevo_estado not in estados_validos:
            return JsonResponse({'success': False, 'error': 'Estado inválido'}, status=400)

        derivacion = PsicologoOrientadorApiService.get_derivacion_or_none(derivacion_id, rbd)
        if not derivacion:
            return JsonResponse({'success': False, 'error': 'Derivación no encontrada'}, status=404)

        PsicologoOrientadorApiService.actualizar_derivacion(
            derivacion,
            nuevo_estado=nuevo_estado,
            informe=body.get('informe_retorno', ''),
            fecha_retorno=body.get('fecha_retorno'),
        )

        return JsonResponse({
            'success': True,
            'message': 'Derivación actualizada correctamente',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error actualizando derivación')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def toggle_pie_status(request, estudiante_id):
    """Activar/Desactivar estado PIE del estudiante."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'COUNSELING_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        estudiante = PsicologoOrientadorApiService.get_estudiante_or_none(
            int(estudiante_id), rbd, require_student_role=True
        )
        if not estudiante:
            return JsonResponse({'success': False, 'error': 'Estudiante no encontrado'}, status=404)

        body = json.loads(request.body)
        requiere_pie = bool(body.get('requiere_pie', False))

        perfil = PsicologoOrientadorApiService.toggle_pie_status(estudiante, requiere_pie=requiere_pie)

        return JsonResponse({
            'success': True,
            'message': 'Estado PIE actualizado correctamente',
            'requiere_pie': perfil.requiere_pie,
        })

    except Exception:
        logger.exception('Error actualizando PIE')
        return JsonResponse({'success': False, 'error': 'Error interno'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['GET', 'POST'])
def listar_crear_citaciones(request):
    """GET para listar y POST para agendar citaciones de apoderados."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if request.method == 'GET':
        if not PolicyService.has_capability(request.user, 'COUNSELING_VIEW', school_id=rbd):
            return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)
        try:
            from backend.apps.core.models import CitacionApoderado
            citaciones = CitacionApoderado.objects.filter(colegio_id=rbd).select_related('estudiante', 'solicitado_por').order_by('-fecha_citacion')
            data = []
            for c in citaciones:
                data.append({
                    'id': c.id_citacion,
                    'estudiante_id': c.estudiante_id,
                    'estudiante_nombre': c.estudiante.get_full_name(),
                    'solicitado_por': c.solicitado_por.get_full_name(),
                    'fecha_citacion': c.fecha_citacion.isoformat(),
                    'motivo': c.motivo,
                    'estado': c.estado,
                    'estado_display': c.get_estado_display(),
                    'observaciones': c.observaciones,
                    'acuerdos': c.acuerdos,
                })
            return JsonResponse({'success': True, 'citaciones': data})
        except Exception:
            logger.exception('Error listando citaciones')
            return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)

    elif request.method == 'POST':
        if not PolicyService.has_capability(request.user, 'COUNSELING_CREATE', school_id=rbd):
            return JsonResponse({'success': False, 'error': 'Sin permisos para agendar citaciones'}, status=403)
        try:
            body = json.loads(request.body)
            estudiante_id = body.get('estudiante_id')
            fecha_citacion = body.get('fecha_citacion')
            motivo = (body.get('motivo') or '').strip()

            if not estudiante_id or not fecha_citacion or not motivo:
                return JsonResponse({'success': False, 'error': 'Faltan campos obligatorios'}, status=400)

            estudiante = PsicologoOrientadorApiService.get_estudiante_or_none(int(estudiante_id), rbd)
            if not estudiante:
                return JsonResponse({'success': False, 'error': 'Estudiante no encontrado'}, status=404)

            citacion = PsicologoOrientadorApiService.crear_citacion(
                estudiante=estudiante,
                rbd=rbd,
                solicitado_por=request.user,
                fecha_citacion=fecha_citacion,
                motivo=motivo
            )

            return JsonResponse({
                'success': True,
                'message': 'Citación agendada correctamente',
                'id': citacion.id_citacion,
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
        except Exception:
            logger.exception('Error creando citación')
            return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def actualizar_citacion(request, citacion_id):
    """POST para registrar asistencia, notas de entrevista privada y acuerdos."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'COUNSELING_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        body = json.loads(request.body)
        nuevo_estado = body.get('estado', '').upper()
        observaciones = body.get('observaciones', '')
        acuerdos = body.get('acuerdos', '')

        estados_validos = {'PENDIENTE', 'ASISTIO', 'INASISTENTE', 'CANCELADA'}
        if nuevo_estado not in estados_validos:
            return JsonResponse({'success': False, 'error': 'Estado inválido'}, status=400)

        citacion = PsicologoOrientadorApiService.get_citacion_or_none(citacion_id, rbd)
        if not citacion:
            return JsonResponse({'success': False, 'error': 'Citación no encontrada'}, status=404)

        PsicologoOrientadorApiService.actualizar_citacion(
            citacion,
            nuevo_estado=nuevo_estado,
            observaciones=observaciones,
            acuerdos=acuerdos
        )

        return JsonResponse({
            'success': True,
            'message': 'Citación actualizada correctamente',
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error actualizando citación')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['GET', 'POST'])
def listar_crear_casos_convivencia(request):
    """GET para listar y POST para abrir casos de bullying/agresiones."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if request.method == 'GET':
        if not PolicyService.has_capability(request.user, 'COUNSELING_VIEW', school_id=rbd):
            return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)
        try:
            from backend.apps.core.models import CasoBullyingConvivencia
            casos = CasoBullyingConvivencia.objects.filter(colegio_id=rbd).select_related('estudiante_implicado', 'registrado_por').order_by('-fecha_registro')
            data = []
            for c in casos:
                data.append({
                    'id': c.id_caso,
                    'estudiante_id': c.estudiante_implicado_id,
                    'estudiante_nombre': c.estudiante_implicado.get_full_name(),
                    'registrado_por': c.registrado_por.get_full_name(),
                    'tipo_falta': c.tipo_falta,
                    'tipo_falta_display': c.get_tipo_falta_display(),
                    'estado': c.estado,
                    'estado_display': c.get_estado_display(),
                    'descripcion_hechos': c.descripcion_hechos,
                    'medidas_tomadas': c.medidas_tomadas,
                    'apoderado_notificado': c.apoderado_notificado,
                    'fecha_registro': c.fecha_registro.isoformat(),
                })
            return JsonResponse({'success': True, 'casos': data})
        except Exception:
            logger.exception('Error listando casos')
            return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)

    elif request.method == 'POST':
        if not PolicyService.has_capability(request.user, 'COUNSELING_CREATE', school_id=rbd):
            return JsonResponse({'success': False, 'error': 'Sin permisos para registrar casos de violencia/bullying'}, status=403)
        try:
            body = json.loads(request.body)
            estudiante_id = body.get('estudiante_id')
            tipo_falta = body.get('tipo_falta')
            descripcion_hechos = (body.get('descripcion_hechos') or '').strip()
            apoderado_notificado = bool(body.get('apoderado_notificado', False))

            if not estudiante_id or not tipo_falta or not descripcion_hechos:
                return JsonResponse({'success': False, 'error': 'Faltan campos obligatorios'}, status=400)

            estudiante = PsicologoOrientadorApiService.get_estudiante_or_none(int(estudiante_id), rbd)
            if not estudiante:
                return JsonResponse({'success': False, 'error': 'Estudiante no encontrado'}, status=404)

            caso = PsicologoOrientadorApiService.crear_caso_bullying(
                estudiante_implicado=estudiante,
                rbd=rbd,
                registrado_por=request.user,
                tipo_falta=tipo_falta,
                descripcion_hechos=descripcion_hechos,
                apoderado_notificado=apoderado_notificado
            )

            return JsonResponse({
                'success': True,
                'message': 'Caso registrado correctamente',
                'id': caso.id_caso,
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
        except Exception:
            logger.exception('Error creando caso')
            return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def actualizar_caso_convivencia(request, caso_id):
    """POST para transicionar estado e ingresar medidas de apoyo/disciplinarias (Ley Aula Segura)."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'COUNSELING_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        body = json.loads(request.body)
        nuevo_estado = body.get('estado', '').upper()
        medidas_tomadas = body.get('medidas_tomadas', '')
        apoderado_notificado = bool(body.get('apoderado_notificado', False))

        estados_validos = {'ABIERTO', 'EN_INVESTIGACION', 'MEDIDAS_APLICADAS', 'CERRADO'}
        if nuevo_estado not in estados_validos:
            return JsonResponse({'success': False, 'error': 'Estado inválido'}, status=400)

        caso = PsicologoOrientadorApiService.get_caso_bullying_or_none(caso_id, rbd)
        if not caso:
            return JsonResponse({'success': False, 'error': 'Caso no encontrado'}, status=404)

        PsicologoOrientadorApiService.actualizar_caso_bullying(
            caso,
            nuevo_estado=nuevo_estado,
            medidas_tomadas=medidas_tomadas,
            apoderado_notificado=apoderado_notificado
        )

        return JsonResponse({
            'success': True,
            'message': 'Caso de Convivencia actualizado correctamente',
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error actualizando caso')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


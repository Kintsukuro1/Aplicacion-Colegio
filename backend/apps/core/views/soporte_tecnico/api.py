"""
API endpoints para Soporte Técnico Escolar.
- Crear tickets de soporte
- Actualizar estado / resolver tickets
"""
import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.auditoria.services.sensitive_action_service import SensitiveActionService
from backend.apps.core.services.soporte_tecnico_api_service import SoporteTecnicoApiService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


def _get_rbd(request):
    return getattr(request.user, 'rbd_colegio', None)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def crear_ticket(request):
    """Crea un nuevo ticket de soporte."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'SUPPORT_CREATE_TICKET', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para crear tickets'}, status=403)

    try:
        body = json.loads(request.body)
        titulo = (body.get('titulo') or '').strip()
        descripcion = (body.get('descripcion') or '').strip()
        categoria = body.get('categoria', 'OTRO')
        prioridad = body.get('prioridad', 'MEDIA')

        if not titulo:
            return JsonResponse({'success': False, 'error': 'El título es obligatorio'}, status=400)
        if not descripcion:
            return JsonResponse({'success': False, 'error': 'La descripción es obligatoria'}, status=400)

        categorias_validas = {'ACCESO', 'PLATAFORMA', 'CONTRASEÑA', 'OTRO'}
        prioridades_validas = {'BAJA', 'MEDIA', 'ALTA', 'URGENTE'}

        if categoria not in categorias_validas:
            categoria = 'OTRO'
        if prioridad not in prioridades_validas:
            prioridad = 'MEDIA'

        ticket = SoporteTecnicoApiService.crear_ticket(
            rbd=rbd,
            user=request.user,
            titulo=titulo,
            descripcion=descripcion,
            categoria=categoria,
            prioridad=prioridad,
        )

        return JsonResponse({
            'success': True,
            'message': 'Ticket creado correctamente',
            'id': ticket.id_ticket,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error creando ticket')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def reset_password(request, user_id):
    """Restablecer la contrasena de un usuario con doble control."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    can_reset_password = (
        PolicyService.has_capability(request.user, 'SUPPORT_RESET_PASSWORD', school_id=rbd)
        or PolicyService.has_capability(request.user, 'SUPPORT_RESOLVE_TICKET', school_id=rbd)
    )
    if not can_reset_password:
        return JsonResponse({'success': False, 'error': 'Sin permisos para gestionar usuarios'}, status=403)

    try:
        body = json.loads(request.body)
        approval_request_id = body.get('approval_request_id')
        new_password = (body.get('new_password') or '').strip()

        target_user = SoporteTecnicoApiService.get_target_user_or_none(user_id, rbd)
        if not target_user:
            return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=404)

        if approval_request_id is None:
            request_obj = SensitiveActionService.create_request(
                action_type=SensitiveActionService.ACTION_PASSWORD_RESET,
                requested_by=request.user,
                school_rbd=rbd,
                target_user=target_user,
                payload={'target_user_id': target_user.id},
                justification='Reset de contrasena solicitado por soporte tecnico.',
            )
            return JsonResponse(
                {
                    'success': True,
                    'requires_approval': True,
                    'request_id': request_obj.id,
                    'message': 'Solicitud registrada. Un segundo usuario debe aprobar y ejecutar el reset.',
                },
                status=202,
            )

        if not new_password:
            return JsonResponse({'success': False, 'error': 'La nueva contrasena es obligatoria'}, status=400)
        if len(new_password) < 12:
            return JsonResponse({'success': False, 'error': 'La nueva contrasena debe tener al menos 12 caracteres'}, status=400)

        request_obj = SensitiveActionService.validate_and_approve_for_execution(
            request_id=int(approval_request_id),
            actor=request.user,
            action_type=SensitiveActionService.ACTION_PASSWORD_RESET,
            school_rbd=rbd,
            target_user_id=target_user.id,
            expected_payload={'target_user_id': target_user.id},
        )

        try:
            target_user.set_password(new_password)
            target_user.save()
        except Exception as exc:
            SensitiveActionService.mark_request_failed(
                request_obj,
                actor=request.user,
                error_message=str(exc),
            )
            raise

        SensitiveActionService.mark_request_executed(
            request_obj,
            actor=request.user,
            execution_result={'target_user_id': target_user.id},
        )

        return JsonResponse({
            'success': True,
            'message': 'Contrasena restablecida correctamente',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON invalido'}, status=400)
    except Exception:
        logger.exception('Error restableciendo contrasena')
        return JsonResponse({'success': False, 'error': 'Error interno'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def actualizar_ticket(request, ticket_id):
    """Actualiza el estado o resolucion de un ticket."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'SUPPORT_RESOLVE_TICKET', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para gestionar tickets'}, status=403)

    try:
        body = json.loads(request.body)
        nuevo_estado = body.get('estado', '').upper()
        estados_validos = {'ABIERTO', 'EN_PROGRESO', 'RESUELTO', 'CERRADO'}

        if nuevo_estado not in estados_validos:
            return JsonResponse({'success': False, 'error': 'Estado inválido'}, status=400)

        try:
            ticket = SoporteTecnicoApiService.get_ticket_or_none(ticket_id, rbd)
        except Exception:
            ticket = None
        if not ticket:
            return JsonResponse({'success': False, 'error': 'Ticket no encontrado'}, status=404)

        resolucion = body.get('resolucion', '')
        fecha_resolucion = timezone.now() if nuevo_estado in ('RESUELTO', 'CERRADO') else None
        SoporteTecnicoApiService.actualizar_ticket(
            ticket,
            nuevo_estado=nuevo_estado,
            resolucion=resolucion,
            resuelto_por=request.user if nuevo_estado in ('RESUELTO', 'CERRADO') else None,
            fecha_resolucion=fecha_resolucion,
        )

        return JsonResponse({
            'success': True,
            'message': f'Ticket actualizado a "{ticket.get_estado_display()}"',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error actualizando ticket')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)

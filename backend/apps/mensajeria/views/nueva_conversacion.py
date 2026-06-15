"""Vista para crear nuevas conversaciones y enviar primer mensaje."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from backend.apps.mensajeria.services import MensajeriaService


@login_required()
@require_http_methods(["POST"])
def crear_nueva_conversacion(request):
    """
    Crear una nueva conversación y enviar primer mensaje.
    
    Espera POST con:
    - clase_id: ID de la clase
    - destinatario_id: ID del destinatario
    - contenido: Contenido del mensaje
    
    Retorna JSON con:
    - success: bool
    - conversacion_id: int (si success=True)
    - message: str (si success=False)
    """
    try:
        # Obtener datos del formulario o JSON
        data = request.POST or json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'Formato de datos inválido'},
            status=400
        )
    
    # Validar que tenemos los datos necesarios
    clase_id = data.get('clase_id')
    destinatario_id = data.get('destinatario_id')
    contenido = (data.get('contenido') or '').strip()
    
    if not clase_id:
        return JsonResponse(
            {'success': False, 'message': 'Debes seleccionar una clase'},
            status=400
        )
    
    if not destinatario_id:
        return JsonResponse(
            {'success': False, 'message': 'Debes seleccionar un destinatario'},
            status=400
        )
    
    if not contenido:
        return JsonResponse(
            {'success': False, 'message': 'El mensaje no puede estar vacío'},
            status=400
        )
    
    try:
        clase_id_int = int(clase_id)
        destinatario_id_int = int(destinatario_id)
    except (ValueError, TypeError):
        return JsonResponse(
            {'success': False, 'message': 'IDs inválidos'},
            status=400
        )
    
    try:
        # Obtener la clase
        clase = MensajeriaService.get_class_for_messages(clase_id_int)
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': 'Clase no encontrada'},
            status=404
        )
    
    # Validar que el usuario tiene acceso a la clase
    if not MensajeriaService.user_has_access_to_class(request.user, clase):
        return JsonResponse(
            {'success': False, 'message': 'No tienes acceso a esa clase'},
            status=403
        )
    
    try:
        # Obtener el destinatario
        destinatario = MensajeriaService.get_user_for_messages(destinatario_id_int)
    except Exception:
        return JsonResponse(
            {'success': False, 'message': 'Destinatario no encontrado'},
            status=404
        )
    
    # Validar que el destinatario es válido para esta clase
    is_valid, error_msg = MensajeriaService.validate_destinatario_for_class(clase, destinatario)
    if not is_valid:
        return JsonResponse(
            {'success': False, 'message': error_msg},
            status=400
        )
    
    # Crear o obtener la conversación
    try:
        conversacion = MensajeriaService.get_or_create_conversacion(
            clase, 
            request.user, 
            destinatario
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error al crear conversación: {str(e)}'},
            status=500
        )
    
    # Enviar el primer mensaje
    try:
        receptor = conversacion.get_otro_participante(request.user)
        mensaje = MensajeriaService.send_message(
            conversacion,
            request.user,
            receptor,
            contenido,
            archivo=None
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error al enviar mensaje: {str(e)}'},
            status=500
        )
    
    return JsonResponse({
        'success': True,
        'conversacion_id': conversacion.id_conversacion,
        'message': 'Mensaje enviado correctamente'
    }, status=201)

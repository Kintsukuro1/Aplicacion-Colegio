# mensajeria/views/conversacion.py
"""Vista de conversación."""

from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from backend.apps.mensajeria.services import MensajeriaService
from backend.apps.mensajeria.views.bandeja import (
    _apply_mensajeria_shell,
    _finalize_profesor_mensajeria_context,
    _get_clases_for_user,
    _mensajeria_content_template,
    enrich_apoderado_mensajeria_context,
)
from backend.common.utils.dashboard_helpers import build_dashboard_context


@login_required()
def ver_conversacion(request, id_conversacion: int):
    conversacion = MensajeriaService.get_conversacion_for_user(request.user, id_conversacion)
    if not conversacion:
        messages.error(request, 'No tienes acceso a esa conversación')
        return redirect('mensajeria:bandeja_mensajes')

    # Marcar como leídos usando el service
    MensajeriaService.mark_conversation_as_read(request.user, conversacion)
    MensajeriaService.mark_mensaje_notifications_read(
        request.user,
        conversacion.id_conversacion,
    )

    if request.method == 'POST':
        contenido = (request.POST.get('contenido') or '').strip()
        archivo = request.FILES.get('archivo')

        # Validar datos del mensaje usando el service
        is_valid, error_msg = MensajeriaService.validate_message_data(contenido, archivo)
        if not is_valid:
            messages.warning(request, error_msg)
            return redirect('mensajeria:ver_conversacion', id_conversacion=id_conversacion)

        # Enviar mensaje usando el service
        otro = conversacion.get_otro_participante(request.user)
        MensajeriaService.send_message(conversacion, request.user, otro, contenido, archivo)

        return redirect('mensajeria:ver_conversacion', id_conversacion=id_conversacion)

    # Obtener mensajes usando el service
    mensajes = MensajeriaService.get_conversation_messages(conversacion)

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='mensajes',
        content_template=_mensajeria_content_template(request.user),
    )
    if redirect_response:
        return redirect_response

    # Fix: misma corrección de rol/sidebar que en bandeja_mensajes.
    _apply_mensajeria_shell(context, request.user)

    otro = conversacion.get_otro_participante(request.user)
    mensajeria_rol = context['rol']
    uses_mm_bandeja = mensajeria_rol in {'estudiante', 'apoderado', 'profesor'}
    clases = list(_get_clases_for_user(request.user))

    if mensajeria_rol == 'profesor':
        context.update(
            MensajeriaService.get_profesor_bandeja_context(
                request.user,
                request.GET,
                conversacion_activa_id=conversacion.id_conversacion,
                clases=clases,
                notificaciones_count=context.get('notificaciones_count'),
            ),
        )
        _finalize_profesor_mensajeria_context(context, request.user)
    elif uses_mm_bandeja:
        context.update(
            MensajeriaService.get_alumno_bandeja_context(
                request.user,
                request.GET,
                conversacion_activa_id=conversacion.id_conversacion,
                clases=clases,
                notificaciones_count=context.get('notificaciones_count'),
            ),
        )

    context.update({
        'conversacion_actual': {
            'id': conversacion.id_conversacion,
            'destinatario': otro,
            'clase': conversacion.clase,
        },
        'mensajes': mensajes,
        'clases': clases,
    })
    enrich_apoderado_mensajeria_context(request.user, context)
    return render(request, 'dashboard.html', context)

"""Vista de bandeja de mensajes."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from backend.apps.cursos.models import Clase, ClaseEstudiante
from backend.apps.mensajeria.services import MensajeriaService
from backend.common.utils.dashboard_helpers import build_dashboard_context


def _mensajeria_content_template(user) -> str:
    if hasattr(user, 'perfil_apoderado'):
        return 'apoderado/mensajeria.html'
    return 'estudiante/mensajeria.html'


def _pupilo_nombre_por_clase(user, clase_id) -> str:
    ce = (
        ClaseEstudiante.objects.filter(
            clase_id=clase_id,
            activo=True,
            estudiante__apoderados__user=user,
        )
        .select_related('estudiante')
        .first()
    )
    if ce and ce.estudiante:
        return ce.estudiante.get_full_name()
    return ''


def _clases_con_pupilo(user, clases) -> list[dict]:
    return [
        {
            'clase': clase,
            'pupilo_nombre': _pupilo_nombre_por_clase(user, clase.id),
        }
        for clase in clases
    ]


def enrich_apoderado_mensajeria_context(user, context: dict) -> None:
    if not hasattr(user, 'perfil_apoderado'):
        return
    clases = context.get('clases') or []
    context['clases_contacto'] = _clases_con_pupilo(user, clases)
    for key in ('conversaciones', 'conversaciones_todas'):
        items = context.get(key)
        if not items:
            continue
        for item in items:
            item['pupilo_nombre'] = _pupilo_nombre_por_clase(
                user,
                item['conversacion'].clase_id,
            )
    conv_actual = context.get('conversacion_actual')
    if conv_actual and conv_actual.get('clase'):
        context['pupilo_nombre_actual'] = _pupilo_nombre_por_clase(
            user,
            conv_actual['clase'].id,
        )


def _get_clases_for_user(user):
    """Obtener clases accesibles por el usuario."""
    if hasattr(user, 'perfil_estudiante'):
        return (
            Clase.objects.filter(
                estudiantes__estudiante=user,
                estudiantes__activo=True,
                activo=True,
            )
            .select_related('curso', 'asignatura', 'profesor')
            .distinct()
            .order_by('asignatura__nombre', 'curso__nombre')
        )

    if hasattr(user, 'perfil_profesor'):
        return (
            Clase.objects.filter(profesor=user, activo=True)
            .select_related('curso', 'asignatura', 'profesor')
            .order_by('asignatura__nombre', 'curso__nombre')
        )

    if hasattr(user, 'perfil_apoderado'):
        return (
            Clase.objects.filter(
                estudiantes__estudiante__apoderados__user=user,
                estudiantes__activo=True,
                activo=True,
            )
            .select_related('curso', 'asignatura', 'profesor')
            .distinct()
            .order_by('asignatura__nombre', 'curso__nombre')
        )

    return Clase.objects.none()


@login_required()
def bandeja_mensajes(request):
    """Bandeja principal.

    Soporta atajo por query params:
    - `clase_id` y `destinatario_id` -> crea/abre conversación y redirige.
    """

    # Atajo desde detalle de clase: abrir conversación directo.
    clase_id = request.GET.get('clase_id')
    destinatario_id = request.GET.get('destinatario_id')
    if clase_id and destinatario_id:
        try:
            clase_id_int = int(clase_id)
            destinatario_id_int = int(destinatario_id)
        except ValueError:
            return HttpResponseBadRequest('Parámetros inválidos')

        try:
            clase = MensajeriaService.get_class_for_messages(clase_id_int)
        except Exception:
            return HttpResponseBadRequest('Clase inválida')
        if not MensajeriaService.user_has_access_to_class(request.user, clase):
            messages.error(request, 'No tienes acceso a esa clase')
            return redirect('dashboard')

        try:
            destinatario = MensajeriaService.get_user_for_messages(destinatario_id_int)
        except Exception:
            return HttpResponseBadRequest('Destinatario inválido')

        # Validar destinatario usando el service
        is_valid, error_msg = MensajeriaService.validate_destinatario_for_class(clase, destinatario)
        if not is_valid:
            messages.error(request, error_msg)
            return redirect('dashboard')

        conv = MensajeriaService.get_or_create_conversacion(clase, request.user, destinatario)
        return redirect('mensajeria:ver_conversacion', id_conversacion=conv.id_conversacion)

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='mensajes',
        content_template=_mensajeria_content_template(request.user),
    )
    if redirect_response:
        return redirect_response

    clases = list(_get_clases_for_user(request.user))
    uses_mm_bandeja = (
        hasattr(request.user, 'perfil_estudiante')
        or hasattr(request.user, 'perfil_apoderado')
    )

    if uses_mm_bandeja:
        context.update(
            MensajeriaService.get_alumno_bandeja_context(request.user, request.GET),
        )
        context.update({
            'conversacion_actual': None,
            'mensajes': [],
            'clases': clases,
        })
        enrich_apoderado_mensajeria_context(request.user, context)
    else:
        context.update({
            'conversaciones': MensajeriaService.get_conversaciones_data(request.user),
            'conversacion_actual': None,
            'mensajes': [],
            'clases': clases,
        })
    return render(request, 'dashboard.html', context)

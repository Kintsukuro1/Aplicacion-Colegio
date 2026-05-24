"""Vista de bandeja de mensajes."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from backend.apps.cursos.models import Clase
from backend.apps.mensajeria.services import MensajeriaService
from backend.common.utils.dashboard_helpers import build_dashboard_context


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
        content_template='estudiante/mensajeria.html',
    )
    if redirect_response:
        return redirect_response

    # Obtener clases del usuario
    clases = _get_clases_for_user(request.user)
    
    # Obtener lista de clases ordenada por nombre
    from backend.apps.cursos.models import Clase
    if isinstance(clases, Clase.objects.none().__class__):
        clases_list = list(clases)
    else:
        clases_list = list(Clase.objects.filter(id__in=clases).order_by('nombre'))

    clases = list(_get_clases_for_user(request.user))
    is_estudiante = hasattr(request.user, 'perfil_estudiante')

    if is_estudiante:
        context.update(
            MensajeriaService.get_alumno_bandeja_context(request.user, request.GET),
        )
        context.update({
            'conversacion_actual': None,
            'mensajes': [],
            'clases': clases,
        })
    else:
        context.update({
            'conversaciones': MensajeriaService.get_conversaciones_data(request.user),
            'conversacion_actual': None,
            'mensajes': [],
            'clases': clases,
        })
    return render(request, 'dashboard.html', context)

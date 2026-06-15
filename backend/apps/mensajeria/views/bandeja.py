"""Vista de bandeja de mensajes."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from backend.apps.core.services.dashboard_auth_service import DashboardAuthService
from backend.apps.cursos.models import Clase, ClaseEstudiante
from backend.apps.mensajeria.services import MensajeriaService
from backend.common.utils.auth_helpers import es_apoderado, es_estudiante, es_profesor
from backend.common.utils.dashboard_helpers import build_dashboard_context


def _resolve_mensajeria_rol(user) -> str:
    """Rol efectivo para mensajería (prioriza apoderado sobre otros perfiles)."""
    # Fix: antes se usaba solo hasattr(perfil_*); apoderado/profesor podían caer en UI de estudiante.
    if es_apoderado(user):
        return 'apoderado'
    if es_profesor(user):
        return 'profesor'
    if es_estudiante(user):
        return 'estudiante'
    return DashboardAuthService._resolve_dashboard_role(user) or 'estudiante'


def _mensajeria_content_template(user) -> str:
    rol = _resolve_mensajeria_rol(user)
    if rol == 'apoderado':
        return 'apoderado/mensajeria.html'
    if rol == 'profesor':
        return 'profesor/mensajeria.html'
    return 'estudiante/mensajeria.html'


def _apply_mensajeria_shell(context: dict, user) -> None:
    """Alinea rol y sidebar con el perfil real (evita UI de estudiante en apoderado/profesor)."""
    # Fix: build_dashboard_context a veces dejaba rol distinto al perfil activo en mensajería.
    mensajeria_rol = _resolve_mensajeria_rol(user)
    context['rol'] = mensajeria_rol
    context['sidebar_template'] = DashboardAuthService.get_sidebar_template(mensajeria_rol)


def _finalize_profesor_mensajeria_context(context: dict, user) -> None:
    """Usa hero lavanda propio de mensajería (_mensajeria_hero), no el genérico del wrap."""
    context['prof_hero_manual'] = True


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
    # Fix: usar rol resuelto, no solo perfil_apoderado, para datos de pupilos en la bandeja.
    if _resolve_mensajeria_rol(user) != 'apoderado':
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
    # Fix: el orden importa; antes estudiante ganaba y un apoderado veía clases de alumno.
    rol = _resolve_mensajeria_rol(user)

    if rol == 'apoderado':
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

    if rol == 'profesor':
        return (
            Clase.objects.filter(profesor=user, activo=True)
            .select_related('curso', 'asignatura', 'profesor')
            .order_by('asignatura__nombre', 'curso__nombre')
        )

    if rol == 'estudiante':
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

    # Fix: corrige sidebar y plantilla embebida según apoderado / profesor / estudiante.
    _apply_mensajeria_shell(context, request.user)

    clases = list(_get_clases_for_user(request.user))
    mensajeria_rol = context['rol']
    # Fix: bandeja MM compartida por los tres roles del portal SSR (no solo por hasattr de perfil).
    uses_mm_bandeja = mensajeria_rol in {'estudiante', 'apoderado', 'profesor'}

    if mensajeria_rol == 'profesor':
        context.update(
            MensajeriaService.get_profesor_bandeja_context(
                request.user,
                request.GET,
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
                clases=clases,
                notificaciones_count=context.get('notificaciones_count'),
            ),
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

# mensajeria/views/clase.py
"""Vista de mensajes por clase."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from backend.apps.mensajeria.services import MensajeriaService
from backend.common.services.policy_service import PolicyService


def _has_profile(user, profile_attr: str) -> bool:
    try:
        return getattr(user, profile_attr, None) is not None
    except (ObjectDoesNotExist, AttributeError):
        return False


def _resolve_context_role(user) -> str:
    school_id = getattr(user, 'rbd_colegio', None)
    if _has_profile(user, 'perfil_estudiante'):
        return 'estudiante'
    if _has_profile(user, 'perfil_apoderado'):
        return 'apoderado'
    if PolicyService.has_capability(user, 'TEACHER_VIEW', school_id=school_id):
        return 'profesor'
    if PolicyService.has_capability(user, 'SYSTEM_CONFIGURE', school_id=school_id):
        return 'admin_escolar'
    return 'usuario'


@login_required()
def mensajes_clase(request, id_clase: int):
    """Vista liviana para embebidos (iframe) en detalle de clase.

    Por ahora entrega un link a la bandeja con el `clase_id` preseleccionado.
    """

    try:
        clase = MensajeriaService.get_class_for_messages(id_clase)
    except Exception:
        raise Http404('Clase no encontrada')
    if not MensajeriaService.user_has_access_to_class(request.user, clase):
        return render(request, 'mensajeria/mensajes_clase.html', {'sin_acceso': True, 'clase': clase})

    rol = _resolve_context_role(request.user)

    return render(
        request,
        'mensajeria/mensajes_clase.html',
        {
            'sin_acceso': False,
            'rol': rol,
            'clase': clase,
            'bandeja_url': f"{reverse('mensajeria:bandeja_mensajes')}?clase_id={clase.id}",
        },
    )

"""Helpers para resolver contexto de colegio en vistas de core."""

from __future__ import annotations

from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.institucion.models import Colegio
from backend.common.services.policy_service import PolicyService


def _parse_rbd(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_request_rbd(request):
    """Resuelve el RBD efectivo para la request actual.

    Prioridad:
    1) `request.user.rbd_colegio`
    2) Query param `colegio_id`/`school_id` (solo SYSTEM_ADMIN)
    3) Sesion `admin_rbd_activo` (solo SYSTEM_ADMIN)
    4) Primer colegio disponible (solo SYSTEM_ADMIN)
    """

    user = getattr(request, "user", None)
    if user is None:
        return None

    user_rbd = getattr(user, "rbd_colegio", None)
    if user_rbd:
        return user_rbd

    if not PolicyService.has_capability(user, "SYSTEM_ADMIN"):
        return None

    query_rbd = _parse_rbd(request.GET.get("colegio_id") or request.GET.get("school_id"))
    if query_rbd and ORMAccessService.filter(Colegio, rbd=query_rbd).exists():
        return query_rbd

    session = getattr(request, "session", None)
    session_rbd = _parse_rbd(session.get("admin_rbd_activo") if session else None)
    if session_rbd and ORMAccessService.filter(Colegio, rbd=session_rbd).exists():
        return session_rbd

    return (
        ORMAccessService.filter(Colegio)
        .order_by("rbd")
        .values_list("rbd", flat=True)
        .first()
    )

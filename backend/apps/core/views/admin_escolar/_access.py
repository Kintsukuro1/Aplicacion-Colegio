"""Helpers de acceso compartidos para vistas admin escolar / admin general."""

from __future__ import annotations

from backend.common.services.policy_service import PolicyService

SCHOOL_ADMIN_ROLES = frozenset({'admin', 'admin_escolar', 'admin_general'})


def can_manage_school_data(rol: str | None, user) -> bool:
    if rol in SCHOOL_ADMIN_ROLES:
        return True
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN') is True

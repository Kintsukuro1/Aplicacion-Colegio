"""Seed idempotente de capabilities por rol."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from django.db import transaction

from backend.apps.accounts.models import Capability, Role, RoleCapability
from backend.common.capabilities import CAPABILITIES, DEFAULT_CAPABILITIES_BY_ROLE
from backend.common.utils.auth_helpers import normalizar_rol


def _capability_description(code: str) -> str:
    return code.replace('_', ' ').title()


def seed_role_capabilities(*, roles: Optional[Iterable[Role]] = None) -> Dict[str, int]:
    """
    Crea las capabilities canonicas y asigna a cada rol sus permisos base.

    La operacion es aditiva: no cambia denegaciones explicitas ni permisos ya
    configurados manualmente.
    """
    summary = {
        'capabilities_created': 0,
        'role_capabilities_created': 0,
        'role_capabilities_existing': 0,
        'role_capabilities_denied': 0,
        'roles_without_defaults': 0,
    }

    all_codes = set(CAPABILITIES)
    for role_capabilities in DEFAULT_CAPABILITIES_BY_ROLE.values():
        all_codes.update(role_capabilities)

    with transaction.atomic():
        capability_by_code = {}
        for code in sorted(all_codes):
            capability, created = Capability.objects.get_or_create(
                code=code,
                defaults={
                    'description': _capability_description(code),
                    'is_active': True,
                },
            )
            capability_by_code[code] = capability
            if created:
                summary['capabilities_created'] += 1

        role_iterable = roles if roles is not None else Role.objects.all()
        for role in role_iterable:
            normalized_role = normalizar_rol(role.nombre)
            expected_capabilities = DEFAULT_CAPABILITIES_BY_ROLE.get(normalized_role)
            if not expected_capabilities:
                summary['roles_without_defaults'] += 1
                continue

            for capability_code in sorted(expected_capabilities):
                capability = capability_by_code[capability_code]
                role_capability, created = RoleCapability.objects.get_or_create(
                    role=role,
                    capability=capability,
                    defaults={'is_granted': True},
                )
                if created:
                    summary['role_capabilities_created'] += 1
                elif role_capability.is_granted:
                    summary['role_capabilities_existing'] += 1
                else:
                    summary['role_capabilities_denied'] += 1

    return summary

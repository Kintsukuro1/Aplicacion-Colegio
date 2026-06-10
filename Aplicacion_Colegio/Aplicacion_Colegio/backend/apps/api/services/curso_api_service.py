from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from backend.common.services.policy_service import PolicyService


def _is_global_admin(user) -> bool:
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN')


def _ensure_same_school(user, school_id) -> None:
    if _is_global_admin(user):
        return
    if getattr(user, 'rbd_colegio', None) != school_id:
        raise PermissionDenied('No puede operar recursos de otro colegio.')


class CursoApiService:
    """Logica de dominio de cursos para capa API."""

    @staticmethod
    @transaction.atomic
    def create_course(*, serializer, actor, requested_school_id=None):
        ciclo = serializer.validated_data.get('ciclo_academico')
        if ciclo is not None:
            _ensure_same_school(actor, ciclo.colegio_id)

        school_id = getattr(actor, 'rbd_colegio', None)
        if _is_global_admin(actor):
            school_id = requested_school_id or school_id

        serializer.save(colegio_id=school_id)

    @staticmethod
    @transaction.atomic
    def update_course(*, serializer, actor):
        ciclo = serializer.validated_data.get('ciclo_academico', serializer.instance.ciclo_academico)
        if ciclo is not None:
            _ensure_same_school(actor, ciclo.colegio_id)
        serializer.save()

from __future__ import annotations

from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.institucion.models import Infraestructura


class InfraestructuraService:
    @classmethod
    def create(cls, *, school_rbd: int, data: dict):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='INFRAESTRUCTURA_CREATE',
        )
        return Infraestructura.objects.create(
            rbd_colegio=school_rbd,
            **data,
        )

    @classmethod
    def update(cls, *, school_rbd: int, infra_id: int, data: dict):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='INFRAESTRUCTURA_UPDATE',
        )

        infraestructura = Infraestructura.objects.filter(id=infra_id, rbd_colegio=school_rbd).first()
        if not infraestructura:
            return None

        for key, value in data.items():
            setattr(infraestructura, key, value)
        infraestructura.save()
        return infraestructura

    @classmethod
    def delete(cls, *, school_rbd: int, infra_id: int) -> bool:
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='INFRAESTRUCTURA_DELETE',
        )
        deleted, _ = Infraestructura.objects.filter(id=infra_id, rbd_colegio=school_rbd).delete()
        return deleted > 0

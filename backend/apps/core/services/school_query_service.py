from __future__ import annotations

from backend.apps.institucion.models import Colegio


class SchoolQueryService:
    @staticmethod
    def get_by_rbd(rbd: int):
        return Colegio.objects.filter(rbd=rbd).first()

    @staticmethod
    def get_required_by_rbd(rbd: int):
        return Colegio.objects.get(rbd=rbd)

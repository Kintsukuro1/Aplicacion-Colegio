from __future__ import annotations

from django.db import transaction


class AsignaturaApiService:
    """Logica de dominio para operaciones API de asignaturas."""

    @staticmethod
    @transaction.atomic
    def create_for_school(*, serializer, school_id: int) -> None:
        serializer.save(colegio_id=school_id)

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError


class MatriculaApiService:
    """Logica de dominio de matriculas para capa API."""

    @staticmethod
    @transaction.atomic
    def create_for_school(*, serializer, school_id: int) -> None:
        serializer.save(colegio_id=school_id)

    @staticmethod
    @transaction.atomic
    def bulk_close_active(*, queryset, ids):
        if not isinstance(ids, list) or not ids:
            raise ValidationError({'ids': 'Debe enviar una lista no vacia de IDs.'})
        return queryset.filter(id__in=ids, estado='ACTIVA').update(estado='FINALIZADA')

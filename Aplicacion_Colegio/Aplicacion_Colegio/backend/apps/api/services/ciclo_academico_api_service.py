from __future__ import annotations

from django.db import transaction

from backend.apps.institucion.models import CicloAcademico


class CicloAcademicoApiService:
    """Logica de dominio para operaciones API sobre ciclos academicos."""

    @staticmethod
    @transaction.atomic
    def create_for_school(*, serializer, actor, school_id: int) -> None:
        serializer.save(
            colegio_id=school_id,
            creado_por=actor,
            modificado_por=actor,
        )

    @staticmethod
    @transaction.atomic
    def update_with_audit(*, serializer, actor) -> None:
        serializer.save(modificado_por=actor)

    @staticmethod
    @transaction.atomic
    def activate_cycle(*, ciclo, actor) -> bool:
        """Activa un ciclo y finaliza cualquier otro activo del mismo colegio.

        Returns:
            bool: True si hubo cambio de estado, False si ya estaba activo.
        """
        if ciclo.estado == 'ACTIVO':
            return False

        CicloAcademico.objects.filter(colegio_id=ciclo.colegio_id, estado='ACTIVO').exclude(pk=ciclo.pk).update(
            estado='FINALIZADO',
            modificado_por=actor,
        )
        ciclo.estado = 'ACTIVO'
        ciclo.modificado_por = actor
        ciclo.save(update_fields=['estado', 'modificado_por'])
        return True

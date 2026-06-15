from __future__ import annotations

from typing import Any, Dict, Optional

from backend.apps.core.services.integrity_service import IntegrityService

from .matriculas_service import MatriculasService


class MatriculaService:
    """
    Servicio de dominio (singular) para operaciones de matrícula.

    Mantiene un contrato explícito para el agregado `Matricula` y delega
    internamente en `MatriculasService` para preservar compatibilidad.
    """

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        return MatriculasService.execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        MatriculasService.validate(operation, params)

    @staticmethod
    def validations(operation: str, params: Dict[str, Any]) -> None:
        MatriculasService.validate(operation, params)

    @staticmethod
    def create(
        actor,
        estudiante_id: int,
        colegio_rbd: int,
        curso_id: Optional[int] = None,
        ciclo_academico_id: Optional[int] = None,
        valor_matricula: int = 0,
        valor_mensual: int = 0,
        observaciones: Optional[str] = None,
    ):
        IntegrityService.validate_matricula_creation(colegio_rbd)
        return MatriculasService.create(
            actor=actor,
            estudiante_id=estudiante_id,
            colegio_rbd=colegio_rbd,
            curso_id=curso_id,
            ciclo_academico_id=ciclo_academico_id,
            valor_matricula=valor_matricula,
            valor_mensual=valor_mensual,
            observaciones=observaciones,
        )

    @staticmethod
    def update(
        actor,
        matricula_id: int,
        new_status: Optional[str] = None,
        observaciones: Optional[str] = None,
    ):
        from backend.apps.matriculas.models import Matricula

        matricula = Matricula.objects.get(id=matricula_id)
        IntegrityService.validate_matricula_update(matricula.colegio_id)
        if new_status:
            return MatriculasService.change_status(
                actor=actor,
                matricula_id=matricula_id,
                new_status=new_status,
            )

        if observaciones is not None:
            matricula.observaciones = observaciones
            matricula.save(update_fields=['observaciones'])
        return matricula

    @staticmethod
    def change_status(actor, matricula_id: int, new_status: str):
        return MatriculasService.change_status(
            actor=actor,
            matricula_id=matricula_id,
            new_status=new_status,
        )

    @staticmethod
    def delete(actor, matricula_id: int) -> None:
        from backend.apps.matriculas.models import Matricula

        matricula = Matricula.objects.get(id=matricula_id)
        IntegrityService.validate_matricula_deletion(matricula.colegio_id)
        MatriculasService.delete(actor=actor, matricula_id=matricula_id)

    @staticmethod
    def get(matricula_id: int):
        from backend.apps.matriculas.models import Matricula

        return Matricula.objects.select_related('colegio', 'estudiante', 'curso', 'ciclo_academico').get(id=matricula_id)

    @staticmethod
    def get_active_matricula_for_user(user, escuela_rbd: int):
        return MatriculasService.get_active_matricula_for_user(user, escuela_rbd)

    @staticmethod
    def get_apoderado_estudiantes(user):
        return MatriculasService.get_apoderado_estudiantes(user)

    @staticmethod
    def apoderado_puede_ver_estudiante(apoderado, estudiante) -> bool:
        return MatriculasService.apoderado_puede_ver_estudiante(apoderado, estudiante)

    @staticmethod
    def get_estado_cuenta_data(user, estudiante_seleccionado=None):
        return MatriculasService.get_estado_cuenta_data(user, estudiante_seleccionado)

    @staticmethod
    def get_pagos_data(user, estudiante_seleccionado=None):
        return MatriculasService.get_pagos_data(user, estudiante_seleccionado)

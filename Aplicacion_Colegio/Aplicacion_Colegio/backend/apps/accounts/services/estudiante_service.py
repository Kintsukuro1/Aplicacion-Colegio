from __future__ import annotations

from typing import Any, Dict

from .student_service import StudentService


class EstudianteService:
    @staticmethod
    def create(user, data: Dict[str, Any], escuela_rbd: str):
        return StudentService.create(user=user, data=data, escuela_rbd=escuela_rbd)

    @staticmethod
    def update(user, estudiante_id: int, data: Dict[str, Any], escuela_rbd: str):
        return StudentService.update(
            user=user,
            estudiante_id=estudiante_id,
            data=data,
            escuela_rbd=escuela_rbd,
        )

    @staticmethod
    def delete(user, estudiante_id: int, escuela_rbd: str):
        return StudentService.delete(
            user=user,
            estudiante_id=estudiante_id,
            escuela_rbd=escuela_rbd,
        )

    @staticmethod
    def get(estudiante_id: int, escuela_rbd: str):
        return StudentService.get(estudiante_id=estudiante_id, escuela_rbd=escuela_rbd)

    @staticmethod
    def validations(data: Dict[str, Any], *, estudiante_id: int | None = None):
        return StudentService.validations(data=data, estudiante_id=estudiante_id)

from __future__ import annotations

from typing import Any, Dict

from .grades_service import GradesService


class CalificacionesService:
    @staticmethod
    def create(data: Dict[str, Any]):
        return GradesService.create(data=data)

    @staticmethod
    def update(calificacion_id: int, data: Dict[str, Any]):
        return GradesService.update(calificacion_id=calificacion_id, data=data)

    @staticmethod
    def delete(calificacion_id: int):
        return GradesService.delete(calificacion_id=calificacion_id)

    @staticmethod
    def get(calificacion_id: int):
        return GradesService.get(calificacion_id=calificacion_id)

    @staticmethod
    def validations(data: Dict[str, Any]):
        return GradesService.validations(data=data)

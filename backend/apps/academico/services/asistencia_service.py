from __future__ import annotations

from typing import Any, Dict

from .attendance_service import AttendanceService


class AsistenciaService:
    @staticmethod
    def create(data: Dict[str, Any]):
        return AttendanceService.create(data=data)

    @staticmethod
    def update(asistencia_id: int, data: Dict[str, Any]):
        return AttendanceService.update(asistencia_id=asistencia_id, data=data)

    @staticmethod
    def delete(asistencia_id: int):
        return AttendanceService.delete(asistencia_id=asistencia_id)

    @staticmethod
    def get(asistencia_id: int):
        return AttendanceService.get(asistencia_id=asistencia_id)

    @staticmethod
    def validations(data: Dict[str, Any]):
        return AttendanceService.validations(data=data)

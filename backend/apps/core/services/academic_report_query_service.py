from __future__ import annotations

from backend.apps.accounts.models import User
from backend.apps.institucion.models import Colegio


class AcademicReportQueryService:
    @staticmethod
    def get_student_with_profile(estudiante_id: int):
        return User.objects.select_related('role').select_related('perfil_estudiante').get(id=estudiante_id)

    @staticmethod
    def get_school_by_rbd(rbd: int):
        return Colegio.objects.get(rbd=rbd)

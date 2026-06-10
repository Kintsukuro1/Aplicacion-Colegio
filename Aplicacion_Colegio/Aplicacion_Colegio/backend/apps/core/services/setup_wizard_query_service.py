from __future__ import annotations

from backend.apps.cursos.models import Curso
from backend.apps.institucion.models import CicloAcademico, NivelEducativo


class SetupWizardQueryService:
    @staticmethod
    def get_active_cycle(*, colegio, estado_activo: str):
        return CicloAcademico.objects.filter(
            colegio=colegio,
            estado=estado_activo,
        ).first()

    @staticmethod
    def list_levels():
        return NivelEducativo.objects.all()

    @staticmethod
    def list_courses_for_cycle(*, colegio, ciclo):
        return Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=ciclo,
        ).select_related('nivel')

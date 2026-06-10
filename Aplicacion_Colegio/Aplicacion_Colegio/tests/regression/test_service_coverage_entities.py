"""Regresión: cobertura mínima de services por entidad crítica."""

from backend.apps.accounts.services.student_service import StudentService
from backend.apps.core.services.clase_service import ClaseService
from backend.apps.core.services.ciclo_academico_service import CicloAcademicoService
from backend.apps.core.services.curso_service import CursoService
from backend.apps.cursos.services.profesor_service import ProfesorService
from backend.apps.matriculas.services.matricula_service import MatriculaService


def test_services_exist_for_critical_entities():
    assert CursoService is not None
    assert ClaseService is not None
    assert MatriculaService is not None
    assert StudentService is not None
    assert ProfesorService is not None
    assert CicloAcademicoService is not None

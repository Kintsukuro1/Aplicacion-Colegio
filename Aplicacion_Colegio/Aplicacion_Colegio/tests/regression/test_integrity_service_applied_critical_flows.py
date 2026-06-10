"""Regresión: enforcement de IntegrityService en flujos críticos."""

import inspect

from backend.apps.accounts.services.student_service import StudentService
from backend.apps.core.services.clase_service import ClaseService
from backend.apps.core.services.ciclo_academico_service import CicloAcademicoService
from backend.apps.core.services.curso_service import CursoService
from backend.apps.cursos.services.profesor_service import ProfesorService
from backend.apps.matriculas.services.matricula_service import MatriculaService


def _src(fn):
    return inspect.getsource(fn)


def test_curso_service_has_integrity_on_critical_operations():
    assert 'IntegrityService.validate_curso_creation' in _src(CursoService.create)
    assert 'IntegrityService.validate_curso_update' in _src(CursoService.update)
    assert 'IntegrityService.validate_curso_deletion' in _src(CursoService.delete)


def test_clase_service_has_integrity_on_critical_operations():
    assert 'IntegrityService.validate_clase_creation' in _src(ClaseService.create)
    assert 'IntegrityService.validate_clase_update' in _src(ClaseService.update)
    assert 'IntegrityService.validate_clase_deletion' in _src(ClaseService.delete)


def test_matricula_service_has_integrity_on_critical_operations():
    assert 'IntegrityService.validate_matricula_creation' in _src(MatriculaService.create)
    assert 'IntegrityService.validate_matricula_update' in _src(MatriculaService.update)
    assert 'IntegrityService.validate_matricula_deletion' in _src(MatriculaService.delete)


def test_student_service_has_integrity_for_critical_actions():
    action_map_src = _src(StudentService._validate_school_integrity)
    assert 'CREATE_STUDENT' in action_map_src
    assert 'UPDATE_STUDENT' in action_map_src
    assert 'DEACTIVATE_STUDENT' in action_map_src
    assert 'IntegrityService.validate_estudiante_creation' in action_map_src
    assert 'IntegrityService.validate_estudiante_update' in action_map_src
    assert 'IntegrityService.validate_estudiante_deletion' in action_map_src


def test_profesor_service_has_integrity_on_critical_operations():
    assert 'IntegrityService.validate_profesor_creation' in _src(ProfesorService.create)
    assert 'IntegrityService.validate_profesor_update' in _src(ProfesorService.update)
    assert 'IntegrityService.validate_profesor_deletion' in _src(ProfesorService._validate_school_integrity_for_profesor)


def test_ciclo_service_has_integrity_on_critical_operations():
    assert 'IntegrityService.validate_ciclo_creation' in _src(CicloAcademicoService.create)
    assert 'IntegrityService.validate_ciclo_update' in _src(CicloAcademicoService.update)
    assert 'IntegrityService.validate_ciclo_deletion' in _src(CicloAcademicoService.delete)

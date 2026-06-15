from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.setup_service import SetupService
from backend.apps.institucion.models import Colegio


def test_validate_and_execute_guard_clauses():
    with pytest.raises(ValueError):
        SetupService.validate('', {})
    with pytest.raises(ValueError):
        SetupService.validate('x', [])
    with pytest.raises(ValueError):
        SetupService._execute('no_existe', {})


def test_is_valid_ciclo_rules():
    today = date.today()
    bad_order = SimpleNamespace(fecha_inicio=today, fecha_fin=today - timedelta(days=1), estado='ACTIVO')
    expired_active = SimpleNamespace(fecha_inicio=today - timedelta(days=30), fecha_fin=today - timedelta(days=1), estado='ACTIVO')
    valid_plan = SimpleNamespace(fecha_inicio=today - timedelta(days=1), fecha_fin=today + timedelta(days=30), estado='PLANIFICACION')

    assert SetupService._is_valid_ciclo(bad_order) is False
    assert SetupService._is_valid_ciclo(expired_active) is False
    assert SetupService._is_valid_ciclo(valid_plan) is True


@patch('backend.apps.core.services.setup_service.Colegio.objects.get', side_effect=Colegio.DoesNotExist)
def test_get_setup_status_school_not_found(_mock_get):
    result = SetupService.get_setup_status(123)

    assert result['setup_complete'] is False
    assert result['missing_steps'] == ['COLEGIO_NOT_FOUND']
    assert result['error'] is True


@patch('backend.apps.core.services.setup_service.Clase')
@patch('backend.apps.core.services.setup_service.Matricula')
@patch('backend.apps.core.services.setup_service.Curso')
@patch('backend.apps.core.services.setup_service.CicloAcademico')
@patch('backend.apps.core.services.setup_service.get_user_model')
@patch('backend.apps.core.services.setup_service.Colegio')
def test_get_setup_status_complete(
    mock_colegio,
    mock_get_user_model,
    mock_ciclo,
    mock_curso,
    mock_matricula,
    mock_clase,
):
    colegio = SimpleNamespace(rbd=777)
    valid_ciclo = SimpleNamespace(id=11, fecha_inicio=date.today(), fecha_fin=date.today() + timedelta(days=30), estado='ACTIVO')
    mock_colegio.objects.get.return_value = colegio
    mock_ciclo.objects.filter.return_value = [valid_ciclo]
    mock_curso.objects.filter.return_value.exists.return_value = True
    mock_matricula.objects.filter.return_value.exists.return_value = True
    mock_clase.objects.filter.return_value.exists.return_value = True
    user_model = Mock()
    user_model.objects.filter.return_value.exists.return_value = True
    mock_get_user_model.return_value = user_model

    result = SetupService.get_setup_status(777)

    assert result['setup_complete'] is True
    assert result['missing_steps'] == []
    assert result['completed_steps'] == 5
    assert result['next_step'] is None


@patch('backend.apps.core.services.setup_service.Clase')
@patch('backend.apps.core.services.setup_service.Matricula')
@patch('backend.apps.core.services.setup_service.Curso')
@patch('backend.apps.core.services.setup_service.CicloAcademico')
@patch('backend.apps.core.services.setup_service.get_user_model')
@patch('backend.apps.core.services.setup_service.Colegio')
def test_get_setup_status_missing_priority_is_respected(
    mock_colegio,
    mock_get_user_model,
    mock_ciclo,
    mock_curso,
    mock_matricula,
    mock_clase,
):
    colegio = SimpleNamespace(rbd=555)
    expired = SimpleNamespace(
        id=9,
        fecha_inicio=date.today() - timedelta(days=60),
        fecha_fin=date.today() - timedelta(days=1),
        estado='ACTIVO',
    )
    mock_colegio.objects.get.return_value = colegio
    mock_ciclo.objects.filter.return_value = [expired]
    mock_curso.objects.filter.return_value.exists.return_value = False
    mock_matricula.objects.filter.return_value.exists.return_value = False
    mock_clase.objects.filter.return_value.exists.return_value = False
    user_model = Mock()
    user_model.objects.filter.return_value.exists.return_value = False
    mock_get_user_model.return_value = user_model

    result = SetupService.get_setup_status(555)

    assert result['setup_complete'] is False
    assert 'MISSING_CICLO_ACTIVO' in result['missing_steps']
    assert result['next_required_step'] == 1


def test_get_setup_step_details_known_and_unknown():
    known = SetupService.get_setup_step_details('MISSING_PROFESOR')
    unknown = SetupService.get_setup_step_details('UNKNOWN_STEP')

    assert known['priority'] == 3
    assert unknown['priority'] == 999

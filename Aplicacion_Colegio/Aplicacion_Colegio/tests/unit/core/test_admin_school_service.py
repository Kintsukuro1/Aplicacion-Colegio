from datetime import date
from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.admin_school_service import AdminSchoolService
from backend.common.constants import (
    CICLO_ESTADO_ACTIVO,
    CICLO_ESTADO_CERRADO,
    CICLO_ESTADO_PLANIFICACION,
)
from backend.common.exceptions import PrerequisiteException


@patch('backend.apps.core.services.admin_school_service.IntegrityService.get_school_integrity_report')
def test_validate_integrity_with_allowed_errors_ignores_expected(mock_report):
    mock_report.return_value = {'errors': ['No active academic cycle: setup pending']}

    AdminSchoolService._validate_integrity_with_allowed_errors(
        school_rbd=123,
        action='ACTION',
        allowed_errors=('No active academic cycle',),
    )


@patch('backend.apps.core.services.admin_school_service.IntegrityService.get_school_integrity_report')
def test_validate_integrity_with_allowed_errors_raises_for_disallowed(mock_report):
    mock_report.return_value = {'errors': ['Broken foreign key reference']}

    with pytest.raises(PrerequisiteException):
        AdminSchoolService._validate_integrity_with_allowed_errors(
            school_rbd=123,
            action='ACTION',
            allowed_errors=('No active academic cycle',),
        )


@patch('backend.apps.core.services.admin_school_service.AdminSchoolService._validate_integrity_with_allowed_errors')
@patch('backend.apps.core.services.admin_school_service.Colegio')
@patch('backend.apps.core.services.admin_school_service.NivelEducativo')
@patch('backend.apps.core.services.admin_school_service.CicloAcademico')
def test_create_course_requires_active_cycle(mock_ciclo, mock_nivel, mock_colegio, _mock_integrity):
    mock_colegio.objects.get.return_value = Mock()
    mock_nivel.objects.get.return_value = Mock()
    mock_ciclo.objects.filter.return_value.first.return_value = None

    with pytest.raises(PrerequisiteException):
        AdminSchoolService.create_course(user=Mock(), school_rbd=10, nombre='1A', nivel_id=4)


@patch('backend.apps.core.services.admin_school_service.AdminSchoolService._validate_integrity_with_allowed_errors')
@patch('backend.apps.core.services.admin_school_service.Colegio')
@patch('backend.apps.core.services.admin_school_service.NivelEducativo')
@patch('backend.apps.core.services.admin_school_service.CicloAcademico')
@patch('backend.apps.core.services.admin_school_service.Curso')
def test_create_course_success(mock_curso, mock_ciclo, mock_nivel, mock_colegio, _mock_integrity):
    colegio = Mock()
    nivel = Mock()
    ciclo = Mock()
    created = Mock()
    mock_colegio.objects.get.return_value = colegio
    mock_nivel.objects.get.return_value = nivel
    mock_ciclo.objects.filter.return_value.first.return_value = ciclo
    mock_curso.objects.filter.return_value.exists.return_value = False
    mock_curso.objects.create.return_value = created

    result = AdminSchoolService.create_course(user=Mock(), school_rbd=10, nombre='1A', nivel_id=4)

    assert result is created
    mock_curso.objects.create.assert_called_once_with(
        colegio=colegio,
        nombre='1A',
        nivel=nivel,
        ciclo_academico=ciclo,
        activo=True,
    )


@patch('backend.apps.core.services.admin_school_service.AdminSchoolService._validate_integrity_with_allowed_errors')
@patch('backend.apps.core.services.admin_school_service.Colegio')
@patch('backend.apps.core.services.admin_school_service.CicloAcademico')
def test_create_academic_cycle_activate_true_sets_active(mock_ciclo, mock_colegio, _mock_integrity):
    colegio = Mock()
    user = Mock()
    created = Mock()
    mock_colegio.objects.get.return_value = colegio
    mock_ciclo.objects.filter.return_value.exists.return_value = False
    mock_ciclo.objects.create.return_value = created

    result = AdminSchoolService.create_academic_cycle(
        user=user,
        school_rbd=999,
        nombre='2026',
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 31),
        activate=True,
    )

    assert result is created
    assert mock_ciclo.objects.create.call_args.kwargs['estado'] == CICLO_ESTADO_ACTIVO


@patch('backend.apps.core.services.admin_school_service.transaction.atomic')
@patch('backend.apps.core.services.admin_school_service.AdminSchoolService._validate_integrity_with_allowed_errors')
@patch('backend.apps.core.services.admin_school_service.Colegio')
@patch('backend.apps.core.services.admin_school_service.CicloAcademico')
def test_activate_academic_cycle_updates_previous(mock_ciclo_model, mock_colegio, _mock_integrity, mock_atomic):
    colegio = Mock()
    user = Mock()
    ciclo = Mock(id=8)
    mock_colegio.objects.get.return_value = colegio
    mock_ciclo_model.objects.get.return_value = ciclo

    result = AdminSchoolService.activate_academic_cycle(user=user, school_rbd=1, ciclo_id=8)

    assert result is ciclo
    assert ciclo.estado == CICLO_ESTADO_ACTIVO
    mock_ciclo_model.objects.filter.assert_called_once_with(colegio=colegio, estado=CICLO_ESTADO_ACTIVO)
    mock_atomic.assert_called_once()


@patch('backend.apps.core.services.admin_school_service.AdminSchoolService._validate_integrity_with_allowed_errors')
@patch('backend.apps.core.services.admin_school_service.Colegio')
@patch('backend.apps.core.services.admin_school_service.CicloAcademico')
@patch('backend.apps.core.services.admin_school_service.Clase')
def test_close_academic_cycle_branches(mock_clase, mock_ciclo_model, mock_colegio, _mock_integrity):
    colegio = Mock()
    user = Mock()
    ciclo = Mock()
    mock_colegio.objects.get.return_value = colegio
    mock_ciclo_model.objects.get.return_value = ciclo

    mock_clase.objects.filter.return_value.exists.return_value = True
    with pytest.raises(ValueError):
        AdminSchoolService.close_academic_cycle(user=user, school_rbd=1, ciclo_id=3)

    mock_clase.objects.filter.return_value.exists.return_value = False
    result = AdminSchoolService.close_academic_cycle(user=user, school_rbd=1, ciclo_id=3)
    assert result is ciclo
    assert ciclo.estado == CICLO_ESTADO_CERRADO
    ciclo.save.assert_called_once_with(update_fields=['estado', 'modificado_por', 'fecha_modificacion'])


@patch('backend.apps.core.services.admin_school_service.AdminSchoolService._validate_integrity_with_allowed_errors')
@patch('backend.apps.core.services.admin_school_service.Colegio')
@patch('backend.apps.core.services.admin_school_service.CicloAcademico')
def test_create_academic_cycle_duplicate_name(mock_ciclo, mock_colegio, _mock_integrity):
    mock_colegio.objects.get.return_value = Mock()
    mock_ciclo.objects.filter.return_value.exists.return_value = True

    with pytest.raises(ValueError):
        AdminSchoolService.create_academic_cycle(
            user=Mock(),
            school_rbd=1,
            nombre='2026',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            descripcion='',
            activate=False,
        )

    assert CICLO_ESTADO_PLANIFICACION == 'PLANIFICACION'

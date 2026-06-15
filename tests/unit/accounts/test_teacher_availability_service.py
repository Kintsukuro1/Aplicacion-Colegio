from unittest.mock import Mock, patch

import pytest

from backend.apps.accounts.services.teacher_availability_service import TeacherAvailabilityService


pytestmark = pytest.mark.django_db


def _professor(role_name='Profesor'):
    professor = Mock()
    professor.role = Mock()
    professor.role.nombre = role_name
    return professor


def test_save_weekly_availability_rejects_non_teacher():
    with patch('backend.apps.accounts.services.teacher_availability_service.PolicyService.has_capability', return_value=False):
        with pytest.raises(ValueError):
            TeacherAvailabilityService.save_weekly_availability(
                professor=_professor('Alumno'),
                school_rbd=1,
                post_data={},
            )


@patch('backend.apps.accounts.services.teacher_availability_service.PolicyService.has_capability')
@patch('backend.apps.accounts.services.teacher_availability_service.IntegrityService.validate_school_integrity_or_raise')
@patch('backend.apps.accounts.services.teacher_availability_service.SchoolQueryService.get_required_by_rbd')
@patch('backend.apps.accounts.services.teacher_availability_service.DisponibilidadProfesor')
@patch('backend.apps.accounts.services.teacher_availability_service.BloqueHorario')
def test_save_weekly_availability_all_created(
    mock_bloque,
    mock_disp,
    mock_school,
    _mock_integrity,
    mock_has_capability,
):
    professor = _professor()
    colegio = Mock()
    mock_school.return_value = colegio

    b1 = Mock(bloque_numero=1, hora_inicio='08:00', hora_fin='08:45')
    b2 = Mock(bloque_numero=2, hora_inicio='09:00', hora_fin='09:45')
    mock_bloque.objects.filter.return_value.order_by.return_value = [b1, b2]

    def _capabilities(_user, capability, school_id=None):
        if capability == 'CLASS_VIEW':
            return True
        if capability in {'CLASS_EDIT', 'CLASS_TAKE_ATTENDANCE'}:
            return True
        return False

    mock_has_capability.side_effect = _capabilities

    mock_disp.objects.get_or_create.return_value = (Mock(), True)

    post_data = {'disponible_1_1': 'on', 'disponible_2_2': 'on'}

    result = TeacherAvailabilityService.save_weekly_availability(
        professor=professor,
        school_rbd=123,
        post_data=post_data,
    )

    assert result['updated'] == 10
    assert result['slots'] == 10
    assert mock_disp.objects.get_or_create.call_count == 10


@patch('backend.apps.accounts.services.teacher_availability_service.PolicyService.has_capability')
@patch('backend.apps.accounts.services.teacher_availability_service.IntegrityService.validate_school_integrity_or_raise')
@patch('backend.apps.accounts.services.teacher_availability_service.SchoolQueryService.get_required_by_rbd')
@patch('backend.apps.accounts.services.teacher_availability_service.DisponibilidadProfesor')
@patch('backend.apps.accounts.services.teacher_availability_service.BloqueHorario')
def test_save_weekly_availability_existing_changed_and_unchanged(
    mock_bloque,
    mock_disp,
    mock_school,
    _mock_integrity,
    mock_has_capability,
):
    professor = _professor()
    colegio = Mock()
    mock_school.return_value = colegio

    b1 = Mock(bloque_numero=1, hora_inicio='08:00', hora_fin='08:45')
    b1_dup = Mock(bloque_numero=1, hora_inicio='08:00', hora_fin='08:45')
    mock_bloque.objects.filter.return_value.order_by.return_value = [b1, b1_dup]

    def _capabilities(_user, capability, school_id=None):
        if capability == 'CLASS_VIEW':
            return True
        if capability in {'CLASS_EDIT', 'CLASS_TAKE_ATTENDANCE'}:
            return True
        return False

    mock_has_capability.side_effect = _capabilities

    unchanged = Mock(disponible=False, hora_inicio='08:00', hora_fin='08:45')
    changed = Mock(disponible=False, hora_inicio='07:00', hora_fin='07:45')

    def side_effect(**kwargs):
        if kwargs['dia_semana'] == 1:
            return unchanged, False
        return changed, False

    mock_disp.objects.get_or_create.side_effect = side_effect

    result = TeacherAvailabilityService.save_weekly_availability(
        professor=professor,
        school_rbd=123,
        post_data={'disponible_2_1': 'on'},
    )

    assert result['slots'] == 5
    assert result['updated'] == 2
    assert changed.save.call_count == 2
    unchanged.save.assert_not_called()

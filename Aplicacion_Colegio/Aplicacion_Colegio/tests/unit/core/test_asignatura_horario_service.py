from unittest.mock import Mock, patch

from backend.apps.core.services.asignatura_horario_service import AsignaturaHorarioService


@patch('backend.apps.core.services.asignatura_horario_service.Asignatura')
@patch('backend.apps.core.services.asignatura_horario_service.IntegrityService.validate_school_integrity_or_raise')
def test_create_asignatura_calls_integrity_and_create(mock_integrity, mock_asignatura):
    created = Mock()
    mock_asignatura.objects.create.return_value = created

    result = AsignaturaHorarioService.create_asignatura(
        school_rbd=123,
        nombre='Matemática',
        codigo='MAT01',
        horas_semanales=6,
    )

    assert result is created
    mock_integrity.assert_called_once_with(school_id=123, action='ASIGNATURA_CREATE')


@patch('backend.apps.core.services.asignatura_horario_service.BloqueHorario')
@patch('backend.apps.core.services.asignatura_horario_service.IntegrityService.validate_school_integrity_or_raise')
def test_upsert_bloque_created_true(mock_integrity, mock_bloque):
    bloque = Mock()
    mock_bloque.objects.get_or_create.return_value = (bloque, True)

    result, created = AsignaturaHorarioService.upsert_bloque(
        school_rbd=123,
        colegio=Mock(),
        clase=Mock(),
        dia_semana=1,
        bloque_numero=2,
        hora_inicio='08:00',
        hora_fin='08:45',
    )

    assert result is bloque
    assert created is True
    bloque.save.assert_not_called()
    mock_integrity.assert_called_once_with(school_id=123, action='BLOQUE_HORARIO_UPSERT')


@patch('backend.apps.core.services.asignatura_horario_service.BloqueHorario')
@patch('backend.apps.core.services.asignatura_horario_service.IntegrityService.validate_school_integrity_or_raise')
def test_upsert_bloque_created_false_updates_block(mock_integrity, mock_bloque):
    bloque = Mock()
    mock_bloque.objects.get_or_create.return_value = (bloque, False)

    result, created = AsignaturaHorarioService.upsert_bloque(
        school_rbd=123,
        colegio=Mock(),
        clase=Mock(),
        dia_semana=1,
        bloque_numero=2,
        hora_inicio='09:00',
        hora_fin='09:45',
    )

    assert result is bloque
    assert created is False
    assert bloque.hora_inicio == '09:00'
    assert bloque.hora_fin == '09:45'
    assert bloque.activo is True
    bloque.save.assert_called_once()
    mock_integrity.assert_called_once_with(school_id=123, action='BLOQUE_HORARIO_UPSERT')


@patch('backend.apps.core.services.asignatura_horario_service.BloqueHorario')
@patch('backend.apps.core.services.asignatura_horario_service.IntegrityService.validate_school_integrity_or_raise')
def test_create_bloque(mock_integrity, mock_bloque):
    created = Mock()
    mock_bloque.objects.create.return_value = created

    result = AsignaturaHorarioService.create_bloque(
        school_rbd=888,
        colegio=Mock(),
        clase=Mock(),
        dia_semana=3,
        bloque_numero=4,
        hora_inicio='11:00',
        hora_fin='11:45',
    )

    assert result is created
    mock_integrity.assert_called_once_with(school_id=888, action='BLOQUE_HORARIO_CREATE')

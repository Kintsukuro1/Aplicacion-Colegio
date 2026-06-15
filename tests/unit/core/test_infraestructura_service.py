from unittest.mock import Mock, patch

from backend.apps.core.services.infraestructura_service import InfraestructuraService


@patch('backend.apps.core.services.infraestructura_service.Infraestructura')
@patch('backend.apps.core.services.infraestructura_service.IntegrityService.validate_school_integrity_or_raise')
def test_create(mock_integrity, mock_infra):
    created = Mock()
    mock_infra.objects.create.return_value = created

    result = InfraestructuraService.create(school_rbd=11, data={'nombre': 'Sala 1'})

    assert result is created
    mock_integrity.assert_called_once_with(school_id=11, action='INFRAESTRUCTURA_CREATE')


@patch('backend.apps.core.services.infraestructura_service.Infraestructura')
@patch('backend.apps.core.services.infraestructura_service.IntegrityService.validate_school_integrity_or_raise')
def test_update_found_and_not_found(mock_integrity, mock_infra):
    instance = Mock()
    mock_infra.objects.filter.return_value.first.side_effect = [instance, None]

    ok = InfraestructuraService.update(school_rbd=11, infra_id=1, data={'nombre': 'Nuevo'})
    missing = InfraestructuraService.update(school_rbd=11, infra_id=2, data={'nombre': 'X'})

    assert ok is instance
    assert instance.nombre == 'Nuevo'
    instance.save.assert_called_once()
    assert missing is None
    assert mock_integrity.call_count == 2


@patch('backend.apps.core.services.infraestructura_service.Infraestructura')
@patch('backend.apps.core.services.infraestructura_service.IntegrityService.validate_school_integrity_or_raise')
def test_delete(mock_integrity, mock_infra):
    mock_infra.objects.filter.return_value.delete.side_effect = [(1, {}), (0, {})]

    assert InfraestructuraService.delete(school_rbd=11, infra_id=1) is True
    assert InfraestructuraService.delete(school_rbd=11, infra_id=2) is False
    assert mock_integrity.call_count == 2

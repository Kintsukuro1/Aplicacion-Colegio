from unittest.mock import Mock, patch

from backend.apps.core.services.setup_wizard_query_service import SetupWizardQueryService


@patch('backend.apps.core.services.setup_wizard_query_service.CicloAcademico')
def test_get_active_cycle(mock_ciclo):
    expected = Mock()
    mock_ciclo.objects.filter.return_value.first.return_value = expected

    result = SetupWizardQueryService.get_active_cycle(colegio=Mock(), estado_activo='ACTIVO')

    assert result is expected


@patch('backend.apps.core.services.setup_wizard_query_service.NivelEducativo')
def test_list_levels(mock_nivel):
    expected = Mock()
    mock_nivel.objects.all.return_value = expected

    result = SetupWizardQueryService.list_levels()

    assert result is expected


@patch('backend.apps.core.services.setup_wizard_query_service.Curso')
def test_list_courses_for_cycle(mock_curso):
    expected = Mock()
    mock_curso.objects.filter.return_value.select_related.return_value = expected

    result = SetupWizardQueryService.list_courses_for_cycle(colegio=Mock(), ciclo=Mock())

    assert result is expected

from unittest.mock import Mock, patch

from backend.apps.core.services.academic_report_query_service import AcademicReportQueryService


@patch('backend.apps.core.services.academic_report_query_service.User')
def test_get_student_with_profile(mock_user):
    expected = Mock()
    chain = mock_user.objects.select_related.return_value.select_related.return_value
    chain.get.return_value = expected

    result = AcademicReportQueryService.get_student_with_profile(15)

    assert result is expected
    chain.get.assert_called_once_with(id=15)


@patch('backend.apps.core.services.academic_report_query_service.Colegio')
def test_get_school_by_rbd(mock_colegio):
    expected = Mock()
    mock_colegio.objects.get.return_value = expected

    result = AcademicReportQueryService.get_school_by_rbd(123)

    assert result is expected
    mock_colegio.objects.get.assert_called_once_with(rbd=123)

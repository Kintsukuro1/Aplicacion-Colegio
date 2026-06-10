"""
Tests for IntegrityService — domain integrity validation.

Covers:
- execute/validate/_execute pattern
- validate_school_integrity_or_raise (raises PrerequisiteException on errors)
- validate_school_integrity (returns error list)
- get_school_integrity_report (detailed check per school)
- get_system_integrity_report (multi-school aggregation)
- _count_invalid_enrollments edge cases
- _count_broken_relationships edge cases
"""

from unittest.mock import Mock, patch, MagicMock

import pytest

from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException


# ---------------------------------------------------------------------------
# execute / validate / _execute pattern
# ---------------------------------------------------------------------------

class TestIntegrityServicePattern:
    def test_validate_rejects_empty_operation(self):
        with pytest.raises(ValueError, match="operation"):
            IntegrityService.validate("", {})

    def test_validate_rejects_non_string_operation(self):
        with pytest.raises(ValueError, match="operation"):
            IntegrityService.validate(123, {})

    def test_validate_rejects_non_dict_params(self):
        with pytest.raises(ValueError, match="params"):
            IntegrityService.validate("check", "bad_params")

    def test_validate_accepts_valid_inputs(self):
        IntegrityService.validate("check_school", {"school_id": 1})

    def test_execute_rejects_unsupported_operation(self):
        with pytest.raises(ValueError, match="no soportada"):
            IntegrityService.execute("unknown_op", {})

    def test_execute_calls_validate_then_execute(self):
        with patch.object(
            IntegrityService, "validate", return_value=None
        ) as validate_mock, patch.object(
            IntegrityService, "_execute", return_value={"ok": True}
        ) as execute_mock:
            result = IntegrityService.execute("op", {"a": 1})

        assert result == {"ok": True}
        validate_mock.assert_called_once_with("op", {"a": 1})
        execute_mock.assert_called_once_with("op", {"a": 1})

    def test_execute_defaults_params_to_empty_dict(self):
        with patch.object(
            IntegrityService, "validate", return_value=None
        ), patch.object(
            IntegrityService, "_execute", return_value={}
        ) as execute_mock:
            IntegrityService.execute("op")

        execute_mock.assert_called_once_with("op", {})


# ---------------------------------------------------------------------------
# validate_school_integrity_or_raise
# ---------------------------------------------------------------------------

class TestValidateSchoolIntegrityOrRaise:
    def test_no_errors_returns_none(self):
        with patch.object(
            IntegrityService, "validate_school_integrity", return_value=[]
        ):
            result = IntegrityService.validate_school_integrity_or_raise(12345)
        assert result is None

    def test_raises_prerequisite_exception_with_errors(self):
        with patch.object(
            IntegrityService,
            "validate_school_integrity",
            return_value=["No active academic cycle"],
        ):
            with pytest.raises(PrerequisiteException) as exc_info:
                IntegrityService.validate_school_integrity_or_raise(
                    12345, action="CREATE_CURSO"
                )

        assert exc_info.value.error_type == "DATA_INCONSISTENCY"

    def test_exception_context_includes_school_id_and_action(self):
        with patch.object(
            IntegrityService,
            "validate_school_integrity",
            return_value=["Error 1"],
        ):
            with pytest.raises(PrerequisiteException) as exc_info:
                IntegrityService.validate_school_integrity_or_raise(
                    99999, action="DELETE_CURSO"
                )

        ctx = exc_info.value.context
        assert ctx["school_id"] == 99999
        assert ctx["action"] == "DELETE_CURSO"
        assert "Error 1" in ctx["integrity_errors"]


class TestOperationSpecificValidators:
    def test_validate_curso_creation_uses_expected_action(self):
        with patch.object(
            IntegrityService,
            'validate_school_integrity',
            return_value=['No active academic cycle', 'No courses exist'],
        ) as validate_mock, patch.object(IntegrityService, '_raise_integrity_exception') as raise_mock:
            IntegrityService.validate_curso_creation(12345)

        validate_mock.assert_called_once_with(12345)
        raise_mock.assert_not_called()

    def test_validate_estudiante_update_uses_expected_action(self):
        with patch.object(IntegrityService, 'validate_school_integrity_or_raise') as validate_mock:
            IntegrityService.validate_estudiante_update('12345')

        validate_mock.assert_called_once_with(school_id=12345, action='ESTUDIANTE_UPDATE')

    def test_validate_asistencia_deletion_accepts_colegio_instance(self):
        colegio = Mock(rbd='98765')
        with patch.object(IntegrityService, 'validate_school_integrity_or_raise') as validate_mock:
            IntegrityService.validate_asistencia_deletion(colegio)

        validate_mock.assert_called_once_with(school_id=98765, action='ASISTENCIA_DELETE')


class TestRepairGuidance:
    def test_build_repair_guidance_with_dry_run_preview(self):
        with patch('backend.apps.core.services.data_repair_service.DataRepairService') as repair_cls:
            repair_cls.return_value.repair_all.return_value = {
                'total_corrections': 4,
                'categories': {
                    'matriculas': {'count': 2},
                    'cursos': {'count': 1},
                    'clases': {'count': 1},
                },
            }

            guidance = IntegrityService._build_repair_guidance(12345)

        assert guidance['repair_service'] == 'DataRepairService'
        assert guidance['repair_dry_run_available'] is True
        assert guidance['repair_operation'] == 'repair_all'
        assert guidance['repair_params'] == {'rbd_colegio': '12345', 'dry_run': True}
        assert guidance['estimated_corrections'] == 4
        assert guidance['estimated_corrections_by_category']['matriculas'] == 2
        repair_cls.return_value.repair_all.assert_called_once_with(rbd_colegio='12345', dry_run=True)

    def test_build_repair_guidance_is_resilient_on_error(self):
        with patch('backend.apps.core.services.data_repair_service.DataRepairService', side_effect=RuntimeError('preview unavailable')):
            guidance = IntegrityService._build_repair_guidance(12345)

        assert guidance['repair_service'] == 'DataRepairService'
        assert guidance['repair_dry_run_available'] is True
        assert guidance['repair_preview_error'] == 'preview unavailable'

    def test_raise_integrity_exception_includes_repair_guidance(self):
        with patch.object(IntegrityService, '_build_repair_guidance', return_value={'repair_hint': 'run_dry_run'}):
            with pytest.raises(PrerequisiteException) as exc_info:
                IntegrityService._raise_integrity_exception(12345, 'TEST_ACTION', ['Error 1'])

        assert exc_info.value.context['repair_hint'] == 'run_dry_run'


# ---------------------------------------------------------------------------
# get_school_integrity_report
# ---------------------------------------------------------------------------

class TestGetSchoolIntegrityReport:
    @patch("backend.apps.core.services.integrity_service.CicloAcademico.objects")
    @patch("backend.apps.core.services.integrity_service.Curso.objects")
    @patch("backend.apps.core.services.integrity_service.Clase.objects")
    @patch.object(IntegrityService, "_count_invalid_enrollments", return_value=0)
    @patch.object(IntegrityService, "_count_broken_relationships", return_value=0)
    def test_clean_school_reports_valid(
        self, mock_broken, mock_invalid, mock_clase, mock_curso, mock_ciclo
    ):
        # Active cycle exists
        mock_ciclo.filter.return_value.exists.return_value = True
        # Courses exist
        curso_qs = MagicMock()
        curso_qs.exists.return_value = True
        curso_qs.filter.return_value.count.return_value = 0
        mock_curso.filter.return_value = curso_qs
        # No classes without teacher
        mock_clase.filter.return_value.count.return_value = 0

        report = IntegrityService.get_school_integrity_report(12345)

        assert report["is_valid"] is True
        assert report["errors"] == []
        assert report["school_id"] == 12345

    @patch("backend.apps.core.services.integrity_service.CicloAcademico.objects")
    @patch("backend.apps.core.services.integrity_service.Curso.objects")
    @patch("backend.apps.core.services.integrity_service.Clase.objects")
    @patch.object(IntegrityService, "_count_invalid_enrollments", return_value=0)
    @patch.object(IntegrityService, "_count_broken_relationships", return_value=0)
    def test_missing_active_cycle_reported(
        self, mock_broken, mock_invalid, mock_clase, mock_curso, mock_ciclo
    ):
        mock_ciclo.filter.return_value.exists.return_value = False
        curso_qs = MagicMock()
        curso_qs.exists.return_value = True
        curso_qs.filter.return_value.count.return_value = 0
        mock_curso.filter.return_value = curso_qs
        mock_clase.filter.return_value.count.return_value = 0

        report = IntegrityService.get_school_integrity_report(12345)

        assert report["is_valid"] is False
        assert any("active academic cycle" in e.lower() for e in report["errors"])

    @patch("backend.apps.core.services.integrity_service.CicloAcademico.objects")
    @patch("backend.apps.core.services.integrity_service.Curso.objects")
    @patch("backend.apps.core.services.integrity_service.Clase.objects")
    @patch.object(IntegrityService, "_count_invalid_enrollments", return_value=0)
    @patch.object(IntegrityService, "_count_broken_relationships", return_value=0)
    def test_no_courses_reported(
        self, mock_broken, mock_invalid, mock_clase, mock_curso, mock_ciclo
    ):
        mock_ciclo.filter.return_value.exists.return_value = True
        curso_qs = MagicMock()
        curso_qs.exists.return_value = False
        curso_qs.filter.return_value.count.return_value = 0
        mock_curso.filter.return_value = curso_qs
        mock_clase.filter.return_value.count.return_value = 0

        report = IntegrityService.get_school_integrity_report(12345)

        assert any("no courses" in e.lower() for e in report["errors"])

    @patch("backend.apps.core.services.integrity_service.CicloAcademico.objects")
    @patch("backend.apps.core.services.integrity_service.Curso.objects")
    @patch("backend.apps.core.services.integrity_service.Clase.objects")
    @patch.object(IntegrityService, "_count_invalid_enrollments", return_value=0)
    @patch.object(IntegrityService, "_count_broken_relationships", return_value=0)
    def test_courses_without_cycle_reported(
        self, mock_broken, mock_invalid, mock_clase, mock_curso, mock_ciclo
    ):
        mock_ciclo.filter.return_value.exists.return_value = True
        curso_qs = MagicMock()
        curso_qs.exists.return_value = True
        curso_qs.filter.return_value.count.return_value = 3
        mock_curso.filter.return_value = curso_qs
        mock_clase.filter.return_value.count.return_value = 0

        report = IntegrityService.get_school_integrity_report(12345)

        assert report["details"]["courses_without_cycle"] == 3
        assert any("without academic cycle" in e.lower() for e in report["errors"])

    @patch("backend.apps.core.services.integrity_service.CicloAcademico.objects")
    @patch("backend.apps.core.services.integrity_service.Curso.objects")
    @patch("backend.apps.core.services.integrity_service.Clase.objects")
    @patch.object(IntegrityService, "_count_invalid_enrollments", return_value=5)
    @patch.object(IntegrityService, "_count_broken_relationships", return_value=2)
    def test_invalid_enrollments_and_broken_rels_reported(
        self, mock_broken, mock_invalid, mock_clase, mock_curso, mock_ciclo
    ):
        mock_ciclo.filter.return_value.exists.return_value = True
        curso_qs = MagicMock()
        curso_qs.exists.return_value = True
        curso_qs.filter.return_value.count.return_value = 0
        mock_curso.filter.return_value = curso_qs
        mock_clase.filter.return_value.count.return_value = 0

        report = IntegrityService.get_school_integrity_report(12345)

        assert report["details"]["invalid_enrollments"] == 5
        assert report["details"]["broken_relationships"] == 2
        assert any("invalid enrollments" in e.lower() for e in report["errors"])
        assert any("broken relationships" in e.lower() for e in report["errors"])

    @patch("backend.apps.core.services.integrity_service.CicloAcademico.objects")
    @patch("backend.apps.core.services.integrity_service.Curso.objects")
    @patch("backend.apps.core.services.integrity_service.Clase.objects")
    @patch.object(IntegrityService, "_count_invalid_enrollments", return_value=0)
    @patch.object(IntegrityService, "_count_broken_relationships", return_value=0)
    def test_classes_without_teacher_reported(
        self, mock_broken, mock_invalid, mock_clase, mock_curso, mock_ciclo
    ):
        mock_ciclo.filter.return_value.exists.return_value = True
        curso_qs = MagicMock()
        curso_qs.exists.return_value = True
        curso_qs.filter.return_value.count.return_value = 0
        mock_curso.filter.return_value = curso_qs
        mock_clase.filter.return_value.count.return_value = 4

        report = IntegrityService.get_school_integrity_report(12345)

        assert report["details"]["classes_without_teacher"] == 4
        assert any("without assigned teacher" in e.lower() for e in report["errors"])


# ---------------------------------------------------------------------------
# get_system_integrity_report
# ---------------------------------------------------------------------------

class TestGetSystemIntegrityReport:
    def test_aggregates_multiple_school_reports(self):
        with patch(
            "backend.apps.core.services.integrity_service.Curso.objects"
        ) as mock_curso, patch(
            "backend.apps.core.services.integrity_service.Clase.objects"
        ) as mock_clase, patch(
            "backend.apps.core.services.integrity_service.Matricula.objects"
        ) as mock_mat, patch(
            "backend.apps.core.services.integrity_service.CicloAcademico.objects"
        ) as mock_ciclo, patch.object(
            IntegrityService,
            "get_school_integrity_report",
            side_effect=[
                {"school_id": 1, "is_valid": True, "errors": [], "details": {}},
                {"school_id": 2, "is_valid": False, "errors": ["err"], "details": {}},
            ],
        ):
            mock_curso.values_list.return_value = [1]
            mock_clase.values_list.return_value = [2]
            mock_mat.values_list.return_value = []
            mock_ciclo.values_list.return_value = []

            report = IntegrityService.get_system_integrity_report()

        assert report["total_schools_analyzed"] == 2
        assert report["invalid_schools"] == 1
        assert report["valid_schools"] == 1


# ---------------------------------------------------------------------------
# _count_invalid_enrollments
# ---------------------------------------------------------------------------

class TestCountInvalidEnrollments:
    def test_active_enrollment_without_curso_is_invalid(self):
        enrollment = Mock()
        enrollment.estado = "ACTIVA"
        enrollment.curso = None
        enrollment.ciclo_academico = Mock()

        qs = MagicMock()
        qs.__iter__ = Mock(return_value=iter([enrollment]))

        with patch(
            "backend.apps.core.services.integrity_service.Matricula.objects"
        ) as mock_mat:
            mock_mat.filter.return_value.select_related.return_value = qs
            count = IntegrityService._count_invalid_enrollments(12345)

        assert count == 1

    def test_active_enrollment_in_inactive_course_is_invalid(self):
        enrollment = Mock()
        enrollment.estado = "ACTIVA"
        enrollment.curso = Mock(activo=False, colegio_id=12345, ciclo_academico_id=1)
        enrollment.ciclo_academico = Mock(colegio_id=12345)
        enrollment.ciclo_academico_id = 1

        qs = MagicMock()
        qs.__iter__ = Mock(return_value=iter([enrollment]))

        with patch(
            "backend.apps.core.services.integrity_service.Matricula.objects"
        ) as mock_mat:
            mock_mat.filter.return_value.select_related.return_value = qs
            count = IntegrityService._count_invalid_enrollments(12345)

        assert count == 1

    def test_enrollment_in_different_school_curso_is_invalid(self):
        enrollment = Mock()
        enrollment.estado = "ACTIVA"
        enrollment.curso = Mock(activo=True, colegio_id=99999, ciclo_academico_id=1)
        enrollment.ciclo_academico = Mock(colegio_id=12345)
        enrollment.ciclo_academico_id = 1

        qs = MagicMock()
        qs.__iter__ = Mock(return_value=iter([enrollment]))

        with patch(
            "backend.apps.core.services.integrity_service.Matricula.objects"
        ) as mock_mat:
            mock_mat.filter.return_value.select_related.return_value = qs
            count = IntegrityService._count_invalid_enrollments(12345)

        assert count == 1

    def test_valid_enrollment_returns_zero(self):
        enrollment = Mock()
        enrollment.estado = "ACTIVA"
        enrollment.curso = Mock(activo=True, colegio_id=12345, ciclo_academico_id=1)
        enrollment.ciclo_academico = Mock(colegio_id=12345)
        enrollment.ciclo_academico_id = 1

        qs = MagicMock()
        qs.__iter__ = Mock(return_value=iter([enrollment]))

        with patch(
            "backend.apps.core.services.integrity_service.Matricula.objects"
        ) as mock_mat:
            mock_mat.filter.return_value.select_related.return_value = qs
            count = IntegrityService._count_invalid_enrollments(12345)

        assert count == 0


# ---------------------------------------------------------------------------
# _count_broken_relationships
# ---------------------------------------------------------------------------

class TestCountBrokenRelationships:
    def test_class_with_wrong_school_curso_is_broken(self):
        clase = Mock()
        clase.curso = Mock(colegio_id=99999)
        clase.asignatura = Mock(colegio_id=12345)
        clase.profesor = Mock(rbd_colegio=12345)

        qs = MagicMock()
        qs.__iter__ = Mock(return_value=iter([clase]))

        with patch(
            "backend.apps.core.services.integrity_service.Clase.objects"
        ) as mock_clase, patch(
            "backend.apps.core.services.integrity_service.User.objects"
        ) as mock_user:
            mock_clase.filter.return_value.select_related.return_value = qs
            mock_user.filter.return_value.values_list.return_value = [1]
            mock_clase.filter.return_value.exclude.return_value.count.return_value = 0
            count = IntegrityService._count_broken_relationships(12345)

        assert count >= 1

    def test_all_relationships_valid_returns_zero(self):
        clase = Mock()
        clase.curso = Mock(colegio_id=12345)
        clase.asignatura = Mock(colegio_id=12345)
        clase.profesor = Mock(rbd_colegio=12345)

        qs = MagicMock()
        qs.__iter__ = Mock(return_value=iter([clase]))

        with patch(
            "backend.apps.core.services.integrity_service.Clase.objects"
        ) as mock_clase, patch(
            "backend.apps.core.services.integrity_service.User.objects"
        ) as mock_user:
            mock_clase.filter.return_value.select_related.return_value = qs
            mock_user.filter.return_value.values_list.return_value = [1]
            mock_clase.filter.return_value.exclude.return_value.count.return_value = 0
            count = IntegrityService._count_broken_relationships(12345)

        assert count == 0

from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest
from django.db.models.deletion import ProtectedError

from backend.apps.core.services.academic_service import AcademicService
from backend.common.exceptions import PrerequisiteException
from backend.apps.cursos.models import Curso, Clase


@pytest.fixture
def user_mock():
    user = Mock()
    user.rbd_colegio = 12345
    user.is_authenticated = True
    user.is_active = True
    return user


class TestAcademicServiceValidation:
    def test_validate_requires_user(self):
        with pytest.raises(ValueError):
            AcademicService.validate("gestionar_curso", {})

    def test_validate_requires_user_school(self):
        user = Mock()
        user.rbd_colegio = None
        with pytest.raises(ValueError):
            AcademicService.validate("gestionar_curso", {"user": user, "action": "create"})

    def test_validate_rejects_invalid_course_action(self, user_mock):
        with patch(
            "backend.apps.core.services.academic_service.IntegrityService.validate_school_integrity_or_raise",
            return_value=None,
        ):
            with pytest.raises(ValueError):
                AcademicService.validate("gestionar_curso", {"user": user_mock, "action": "invalid"})

    def test_validate_requires_clase_id_for_attendance(self, user_mock):
        with patch(
            "backend.apps.core.services.academic_service.IntegrityService.validate_school_integrity_or_raise",
            return_value=None,
        ):
            with pytest.raises(ValueError):
                AcademicService.validate(
                    "registrar_asistencia",
                    {"user": user_mock, "asistencias_data": []},
                )

    def test_validate_requires_attendance_payload(self, user_mock):
        with patch(
            "backend.apps.core.services.academic_service.IntegrityService.validate_school_integrity_or_raise",
            return_value=None,
        ):
            with pytest.raises(ValueError):
                AcademicService.validate(
                    "registrar_asistencia",
                    {"user": user_mock, "clase_id": 10},
                )

    def test_execute_dispatches_validate_and_execute(self, user_mock):
        with patch.object(AcademicService, "validate", return_value=None) as validate_mock, patch.object(
            AcademicService, "_execute", return_value={"success": True}
        ) as execute_mock:
            result = AcademicService.execute("gestionar_curso", {"user": user_mock})

        assert result["success"] is True
        validate_mock.assert_called_once()
        execute_mock.assert_called_once()

    def test_execute_rejects_unsupported_operation(self):
        with pytest.raises(ValueError):
            AcademicService._execute("not_supported", {})

    def test_execute_gestionar_curso_rejects_invalid_action(self, user_mock):
        with pytest.raises(ValueError):
            AcademicService._execute_gestionar_curso(
                {
                    "user": user_mock,
                    "curso_id": 1,
                    "data": {},
                    "action": "invalid",
                }
            )


class TestAcademicServiceCourses:
    def test_create_course_raises_when_prerequisite_fails(self, user_mock):
        with patch(
            "backend.apps.core.services.academic_service.OnboardingService.validate_prerequisite",
            return_value={
                "valid": False,
                "error": {"error_type": "MISSING_CICLO_ACTIVO", "context": {}},
            },
        ):
            with pytest.raises(PrerequisiteException):
                AcademicService._crear_curso(user_mock, {"nivel": "1"})

    def test_create_course_requires_mandatory_fields(self, user_mock):
        ciclo_qs = Mock()
        ciclo_qs.first.return_value = Mock()
        with patch(
            "backend.apps.core.services.academic_service.OnboardingService.validate_prerequisite",
            return_value={"valid": True},
        ), patch(
            "backend.apps.core.services.academic_service.CicloAcademico.objects.filter",
            return_value=ciclo_qs,
        ):
            result = AcademicService._crear_curso(
                user_mock,
                {"nivel": "1", "anio_escolar": 2026},
            )

        assert result["success"] is False
        assert "Campo requerido" in result["error"]

    def test_create_course_rejects_duplicate(self, user_mock):
        ciclo_qs = Mock()
        ciclo_qs.first.return_value = Mock()
        duplicate_qs = Mock()
        duplicate_qs.exists.return_value = True

        with patch(
            "backend.apps.core.services.academic_service.OnboardingService.validate_prerequisite",
            return_value={"valid": True},
        ), patch(
            "backend.apps.core.services.academic_service.CicloAcademico.objects.filter",
            return_value=ciclo_qs,
        ), patch(
            "backend.apps.core.services.academic_service.Curso.objects.filter",
            return_value=duplicate_qs,
        ):
            result = AcademicService._crear_curso(
                user_mock,
                {"nivel": "1", "letra": "A", "anio_escolar": 2026},
            )

        assert result["success"] is False
        assert "Ya existe un curso" in result["error"]

    def test_create_course_success(self, user_mock):
        ciclo_qs = Mock()
        ciclo_qs.first.return_value = Mock()

        not_duplicate_qs = Mock()
        not_duplicate_qs.exists.return_value = False

        course = Mock()
        create_mock = Mock(return_value=course)

        with patch(
            "backend.apps.core.services.academic_service.OnboardingService.validate_prerequisite",
            return_value={"valid": True},
        ), patch(
            "backend.apps.core.services.academic_service.CicloAcademico.objects.filter",
            return_value=ciclo_qs,
        ), patch(
            "backend.apps.core.services.academic_service.Curso.objects.filter",
            return_value=not_duplicate_qs,
        ), patch(
            "backend.apps.core.services.academic_service.Curso.objects.create",
            create_mock,
        ):
            result = AcademicService._crear_curso(
                user_mock,
                {"nivel": "1", "letra": "A", "anio_escolar": 2026},
            )

        assert result["success"] is True
        assert result["curso"] is course
        create_mock.assert_called_once()

    def test_update_course_success(self, user_mock):
        course = Mock()
        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.get",
            return_value=course,
        ):
            result = AcademicService._actualizar_curso(
                user_mock,
                curso_id=22,
                data={"descripcion": "Nuevo texto", "capacidad_maxima": 40},
            )

        assert result["success"] is True
        course.save.assert_called_once()

    def test_update_course_not_found(self, user_mock):
        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.get",
            side_effect=Curso.DoesNotExist,
        ):
            result = AcademicService._actualizar_curso(
                user_mock,
                curso_id=999,
                data={"descripcion": "X"},
            )

        assert result["success"] is False
        assert "no encontrado" in result["error"].lower()

    def test_delete_course_blocked_by_enrollments(self, user_mock):
        course = Mock()
        matricula_qs = Mock()
        matricula_qs.count.return_value = 2

        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.get",
            return_value=course,
        ), patch(
            "backend.apps.core.services.academic_service.Matricula.objects.filter",
            return_value=matricula_qs,
        ):
            result = AcademicService._eliminar_curso(user_mock, curso_id=10)

        assert result["success"] is False
        assert "matr" in result["error"].lower()

    def test_delete_course_blocked_by_classes(self, user_mock):
        course = Mock()
        matricula_qs = Mock()
        matricula_qs.count.return_value = 0
        clase_qs = Mock()
        clase_qs.count.return_value = 1

        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.get",
            return_value=course,
        ), patch(
            "backend.apps.core.services.academic_service.Matricula.objects.filter",
            return_value=matricula_qs,
        ), patch(
            "backend.apps.core.services.academic_service.Clase.objects.filter",
            return_value=clase_qs,
        ):
            result = AcademicService._eliminar_curso(user_mock, curso_id=10)

        assert result["success"] is False
        assert "clase" in result["error"].lower()

    def test_delete_course_handles_protected_error(self, user_mock):
        course = Mock()
        course.delete.side_effect = ProtectedError("protected", [Mock()])

        matricula_qs = Mock()
        matricula_qs.count.return_value = 0
        clase_qs = Mock()
        clase_qs.count.return_value = 0

        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.get",
            return_value=course,
        ), patch(
            "backend.apps.core.services.academic_service.Matricula.objects.filter",
            return_value=matricula_qs,
        ), patch(
            "backend.apps.core.services.academic_service.Clase.objects.filter",
            return_value=clase_qs,
        ):
            result = AcademicService._eliminar_curso(user_mock, curso_id=10)

        assert result["success"] is False
        assert "protegidas" in result["error"].lower()

    def test_delete_course_success(self, user_mock):
        course = Mock()
        matricula_qs = Mock()
        matricula_qs.count.return_value = 0
        clase_qs = Mock()
        clase_qs.count.return_value = 0

        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.get",
            return_value=course,
        ), patch(
            "backend.apps.core.services.academic_service.Matricula.objects.filter",
            return_value=matricula_qs,
        ), patch(
            "backend.apps.core.services.academic_service.Clase.objects.filter",
            return_value=clase_qs,
        ):
            result = AcademicService._eliminar_curso(user_mock, curso_id=10)

        assert result["success"] is True
        course.delete.assert_called_once()


class TestAcademicServiceAttendance:
    def test_register_attendance_rejects_non_today_class(self, user_mock):
        clase = Mock()
        clase.fecha = date(2026, 1, 1)

        with patch(
            "backend.apps.core.services.academic_service.Clase.objects.select_related"
        ) as select_related_mock, patch(
            "backend.apps.core.services.academic_service.timezone.now",
            return_value=datetime(2026, 1, 2, 9, 0, 0),
        ):
            select_related_mock.return_value.get.return_value = clase
            result = AcademicService._execute_registrar_asistencia(
                {
                    "user": user_mock,
                    "clase_id": 7,
                    "asistencias_data": [{"estudiante_id": 1, "estado": "PRESENTE"}],
                }
            )

        assert result["success"] is False
        assert "actual" in result["error"]

    def test_register_attendance_handles_missing_class(self, user_mock):
        with patch(
            "backend.apps.core.services.academic_service.Clase.objects.select_related"
        ) as select_related_mock:
            select_related_mock.return_value.get.side_effect = Clase.DoesNotExist
            result = AcademicService._execute_registrar_asistencia(
                {
                    "user": user_mock,
                    "clase_id": 404,
                    "asistencias_data": [],
                }
            )

        assert result["success"] is False
        assert "no encontrada" in result["error"].lower()

    def test_register_attendance_success_and_skips_unenrolled(self, user_mock):
        clase = Mock()
        clase.fecha = date(2026, 1, 2)
        clase.curso = Mock()

        matricula_ok = Mock()
        matricula_ok.first.return_value = Mock()
        matricula_missing = Mock()
        matricula_missing.first.return_value = None

        with patch(
            "backend.apps.core.services.academic_service.Clase.objects.select_related"
        ) as select_related_mock, patch(
            "backend.apps.core.services.academic_service.Matricula.objects.filter",
            side_effect=[matricula_ok, matricula_missing],
        ), patch(
            "backend.apps.core.services.academic_service.Asistencia.objects.update_or_create",
            return_value=(Mock(), True),
        ) as update_or_create_mock, patch(
            "backend.apps.core.services.academic_service.timezone.now",
            return_value=datetime(2026, 1, 2, 9, 0, 0),
        ):
            select_related_mock.return_value.get.return_value = clase
            result = AcademicService._execute_registrar_asistencia(
                {
                    "user": user_mock,
                    "clase_id": 7,
                    "asistencias_data": [
                        {"estudiante_id": 1, "estado": "presente"},
                        {"estudiante_id": 2, "estado": "ausente"},
                    ],
                }
            )

        assert result["success"] is True
        assert result["asistencias_registradas"] == 1
        update_or_create_mock.assert_called_once()


class TestAcademicServiceReports:
    def test_obtener_asistencia_curso_without_access(self, user_mock):
        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(AcademicService, "_validar_acceso_curso", return_value=None):
            result = AcademicService.obtener_asistencia_curso(user_mock, curso_id=10)

        assert result["success"] is False
        assert "sin acceso" in result["error"].lower()

    def test_generar_reporte_rejects_invalid_type(self, user_mock):
        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ):
            result = AcademicService.generar_reporte_academico(
                user_mock,
                tipo_reporte="inexistente",
                filtros={},
            )

        assert result["success"] is False
        assert "tipo de reporte" in result["error"].lower()

    def test_reporte_curso_requires_curso_id(self, user_mock):
        result = AcademicService._reporte_curso(user_mock, filtros={})
        assert result["success"] is False
        assert "curso_id requerido" in result["error"].lower()

    def test_reporte_curso_returns_error_without_access(self, user_mock):
        with patch.object(AcademicService, "_validar_acceso_curso", return_value=None):
            result = AcademicService._reporte_curso(user_mock, filtros={"curso_id": 99})

        assert result["success"] is False
        assert "sin acceso" in result["error"].lower()

    def test_reporte_asignatura_requires_asignatura_id(self, user_mock):
        result = AcademicService._reporte_asignatura(user_mock, filtros={})
        assert result["success"] is False
        assert "asignatura_id requerido" in result["error"].lower()

    def test_reporte_asignatura_returns_error_when_course_not_accessible(self, user_mock):
        with patch(
            "backend.apps.core.services.academic_service.Asignatura.objects.get",
            return_value=Mock(),
        ), patch.object(AcademicService, "_validar_acceso_curso", return_value=None):
            result = AcademicService._reporte_asignatura(
                user_mock,
                filtros={"asignatura_id": 1, "curso_id": 2},
            )

        assert result["success"] is False
        assert "sin acceso" in result["error"].lower()

    def test_reporte_asignatura_success(self, user_mock):
        asignatura = Mock()
        with patch(
            "backend.apps.core.services.academic_service.Asignatura.objects.get",
            return_value=asignatura,
        ), patch.object(
            AcademicService,
            "_calcular_estadisticas_asignatura",
            return_value={"promedio": 5.8},
        ):
            result = AcademicService._reporte_asignatura(
                user_mock,
                filtros={"asignatura_id": 1},
            )

        assert result["success"] is True
        assert result["tipo"] == "asignatura"
        assert "estadisticas" in result

    def test_validar_acceso_curso_returns_none_if_course_missing(self, user_mock):
        select_related_qs = Mock()
        select_related_qs.get.side_effect = Curso.DoesNotExist
        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.select_related",
            return_value=select_related_qs,
        ):
            result = AcademicService._validar_acceso_curso(user_mock, curso_id=999)

        assert result is None

    def test_validar_acceso_curso_allows_admin(self, user_mock):
        curso = Mock()
        select_related_qs = Mock()
        select_related_qs.get.return_value = curso

        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.select_related",
            return_value=select_related_qs,
        ), patch(
            "backend.apps.core.services.academic_service.PermissionService.has_permission",
            return_value=True,
        ):
            result = AcademicService._validar_acceso_curso(user_mock, curso_id=5)

        assert result is curso

    def test_validar_acceso_curso_allows_teacher_with_class(self, user_mock):
        user_mock.role = Mock()
        user_mock.role.nombre = "Profesor"

        curso = Mock()
        select_related_qs = Mock()
        select_related_qs.get.return_value = curso
        clase_qs = Mock()
        clase_qs.exists.return_value = True

        with patch(
            "backend.apps.core.services.academic_service.Curso.objects.select_related",
            return_value=select_related_qs,
        ), patch(
            "backend.apps.core.services.academic_service.PermissionService.has_permission",
            return_value=False,
        ), patch(
            "backend.apps.core.services.academic_service.Clase.objects.filter",
            return_value=clase_qs,
        ):
            result = AcademicService._validar_acceso_curso(user_mock, curso_id=5)

        assert result is curso

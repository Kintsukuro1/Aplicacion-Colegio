from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from backend.apps.academico.services.grades_service import GradesService
from backend.common.exceptions import PrerequisiteException


@pytest.fixture
def auth_user_mock():
    user = Mock()
    user.is_authenticated = True
    user.is_active = True
    user.role = Mock()
    user.role.nombre = "Profesor"
    return user


def _build_valid_class_bundle():
    colegio = Mock()
    colegio.rbd = 12345

    ciclo = Mock()
    ciclo.estado = "ACTIVO"
    ciclo.nombre = "2026"

    curso = Mock()
    curso.activo = True
    curso.id_curso = 10
    curso.ciclo_academico = ciclo

    profesor = Mock()
    profesor.is_active = True

    clase = Mock()
    clase.id = 88
    clase.id_clase = 88
    clase.colegio_id = 12345
    clase.curso = curso
    clase.profesor = profesor
    clase.profesor_id = 22
    clase.activo = True

    return colegio, ciclo, curso, clase


class TestGradesServiceExecution:
    def test_validate_requires_operation(self):
        with pytest.raises(ValueError):
            GradesService.validate("", {})

    def test_validate_requires_dict_params(self):
        with pytest.raises(ValueError):
            GradesService.validate("create", [])

    def test_execute_dispatches_custom_handler(self, monkeypatch):
        monkeypatch.setattr(
            GradesService,
            "_execute_ping",
            staticmethod(lambda params: {"pong": params["value"]}),
            raising=False,
        )

        result = GradesService.execute("ping", {"value": 7})

        assert result == {"pong": 7}

    def test_execute_rejects_unsupported_operation(self):
        with pytest.raises(ValueError):
            GradesService.execute("operation_does_not_exist", {})


class TestGradesServiceClassValidations:
    def test_validate_clase_relationships_rejects_cross_school_class(self):
        colegio, _, _, clase = _build_valid_class_bundle()
        clase.colegio_id = 99999

        with pytest.raises(PrerequisiteException):
            GradesService._validate_clase_relationships(clase, colegio)

    def test_validate_clase_relationships_requires_teacher(self):
        colegio, _, _, clase = _build_valid_class_bundle()
        clase.profesor_id = None

        with pytest.raises(PrerequisiteException):
            GradesService._validate_clase_relationships(clase, colegio)

    def test_validate_clase_relationships_rejects_inactive_teacher(self):
        colegio, _, _, clase = _build_valid_class_bundle()
        clase.profesor.is_active = False

        with pytest.raises(PrerequisiteException):
            GradesService._validate_clase_relationships(clase, colegio)

    def test_validate_clase_active_state_rejects_inactive_class(self):
        _, _, _, clase = _build_valid_class_bundle()
        clase.activo = False

        with pytest.raises(PrerequisiteException):
            GradesService._validate_clase_active_state(clase)

    def test_validate_clase_active_state_rejects_inactive_course(self):
        _, _, _, clase = _build_valid_class_bundle()
        clase.curso.activo = False

        with pytest.raises(PrerequisiteException):
            GradesService._validate_clase_active_state(clase)

    def test_validate_clase_active_state_rejects_closed_cycle(self):
        _, _, _, clase = _build_valid_class_bundle()
        clase.curso.ciclo_academico.estado = "CERRADO"

        with pytest.raises(PrerequisiteException):
            GradesService._validate_clase_active_state(clase)


class TestGradesServiceOperations:
    def test_create_evaluation_success(self, auth_user_mock):
        colegio, _, _, clase = _build_valid_class_bundle()
        evaluacion_mock = Mock()

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch(
            "backend.apps.academico.services.grades_service.OnboardingService.validate_prerequisite",
            return_value={"valid": True},
        ), patch(
            "backend.apps.academico.models.Evaluacion.objects.create",
            return_value=evaluacion_mock,
        ) as create_mock:
            result = GradesService.create_evaluation(
                auth_user_mock,
                colegio,
                clase,
                "Prueba 1",
                date(2026, 5, 10),
                Decimal("40.00"),
            )

        assert result is evaluacion_mock
        create_mock.assert_called_once()

    def test_create_evaluation_fails_when_teacher_not_assigned(self, auth_user_mock):
        colegio, _, _, clase = _build_valid_class_bundle()
        clase.profesor_id = None

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch(
            "backend.apps.academico.services.grades_service.OnboardingService.validate_prerequisite",
            return_value={"valid": True},
        ):
            with pytest.raises(PrerequisiteException):
                GradesService.create_evaluation(
                    auth_user_mock,
                    colegio,
                    clase,
                    "Prueba sin profesor",
                    date(2026, 6, 1),
                    Decimal("30.00"),
                )

    def test_register_grades_rejects_inactive_evaluation(self, auth_user_mock):
        colegio, ciclo, _, clase = _build_valid_class_bundle()
        evaluacion = Mock()
        evaluacion.id_evaluacion = 9
        evaluacion.colegio = colegio
        evaluacion.clase = clase
        evaluacion.clase.curso.ciclo_academico = ciclo
        evaluacion.activa = False

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch.object(
            GradesService, "_validate_clase_active_state", return_value=None
        ):
            with pytest.raises(PrerequisiteException):
                GradesService.register_grades_for_evaluation(
                    auth_user_mock,
                    evaluacion,
                    {1: Decimal("6.0")},
                    colegio=colegio,
                )

    def test_register_grades_skips_students_outside_cycle(self, auth_user_mock):
        colegio, ciclo, _, clase = _build_valid_class_bundle()
        other_cycle = Mock()
        other_cycle.nombre = "2025"

        evaluacion = Mock()
        evaluacion.id_evaluacion = 10
        evaluacion.colegio = colegio
        evaluacion.clase = clase
        evaluacion.activa = True

        student_ok = Mock()
        student_ok.perfil_estudiante = Mock()
        student_ok.perfil_estudiante.ciclo_actual = ciclo

        student_wrong_cycle = Mock()
        student_wrong_cycle.perfil_estudiante = Mock()
        student_wrong_cycle.perfil_estudiante.ciclo_actual = other_cycle

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch.object(
            GradesService, "_validate_clase_active_state", return_value=None
        ), patch.object(
            GradesService,
            "_get_escala",
            return_value={
                "nota_minima": Decimal("1.0"),
                "nota_maxima": Decimal("7.0"),
                "nota_aprobacion": Decimal("4.0"),
                "redondeo_decimales": 1,
            },
        ), patch(
            "backend.apps.accounts.models.User.objects.get",
            side_effect=[student_ok, student_wrong_cycle],
        ), patch(
            "backend.apps.academico.models.Calificacion.objects.update_or_create",
            return_value=(Mock(), True),
        ) as upsert_mock:
            count = GradesService.register_grades_for_evaluation(
                auth_user_mock,
                evaluacion,
                {
                    1: Decimal("6.0"),
                    2: Decimal("5.5"),
                    3: Decimal("9.0"),  # Out of range, ignored
                    4: None,  # Empty value, ignored
                },
                colegio=colegio,
            )

        assert count == 1
        upsert_mock.assert_called_once()

    def test_register_grades_rejects_inactive_class(self, auth_user_mock):
        colegio, _, _, clase = _build_valid_class_bundle()
        clase.activo = False

        evaluacion = Mock()
        evaluacion.id_evaluacion = 9
        evaluacion.colegio = colegio
        evaluacion.clase = clase
        evaluacion.activa = True

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ):
            with pytest.raises(PrerequisiteException):
                GradesService.register_grades_for_evaluation(
                    auth_user_mock,
                    evaluacion,
                    {1: Decimal("6.0")},
                    colegio=colegio,
                )

    def test_update_evaluation_returns_false_when_not_found(self, auth_user_mock):
        colegio, _, _, _ = _build_valid_class_bundle()
        from backend.apps.academico.models import Evaluacion

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch(
            "backend.apps.academico.models.Evaluacion.objects.get",
            side_effect=Evaluacion.DoesNotExist,
        ):
            result = GradesService.update_evaluation(
                auth_user_mock,
                colegio,
                evaluacion_id=999,
                nombre="No existe",
                fecha_evaluacion=date(2026, 6, 1),
                ponderacion=Decimal("20.00"),
            )

        assert result is False

    def test_update_evaluation_success(self, auth_user_mock):
        colegio, _, _, _ = _build_valid_class_bundle()
        evaluacion = Mock()

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch(
            "backend.apps.academico.models.Evaluacion.objects.get",
            return_value=evaluacion,
        ):
            result = GradesService.update_evaluation(
                auth_user_mock,
                colegio,
                evaluacion_id=5,
                nombre="Control 1",
                fecha_evaluacion=date(2026, 5, 11),
                ponderacion=Decimal("30.00"),
            )

        assert result is True
        assert evaluacion.nombre == "Control 1"
        evaluacion.save.assert_called_once()

    def test_delete_evaluation_success(self, auth_user_mock):
        colegio, _, _, _ = _build_valid_class_bundle()
        evaluacion = Mock()

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch(
            "backend.apps.academico.models.Evaluacion.objects.get",
            return_value=evaluacion,
        ):
            result = GradesService.delete_evaluation(auth_user_mock, colegio, evaluacion_id=10)

        assert result is True
        assert evaluacion.activa is False
        evaluacion.save.assert_called_once()

    def test_delete_evaluation_returns_false_when_not_found(self, auth_user_mock):
        colegio, _, _, _ = _build_valid_class_bundle()
        from backend.apps.academico.models import Evaluacion

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            GradesService, "_validate_school_integrity", return_value=None
        ), patch(
            "backend.apps.academico.models.Evaluacion.objects.get",
            side_effect=Evaluacion.DoesNotExist,
        ):
            result = GradesService.delete_evaluation(auth_user_mock, colegio, evaluacion_id=404)

        assert result is False


class TestGradesServiceQueries:
    def test_calculate_student_final_grade_without_data(self):
        queryset = Mock()
        queryset.select_related.return_value = []
        with patch(
            "backend.apps.academico.models.Calificacion.objects.filter",
            return_value=queryset,
        ):
            result = GradesService.calculate_student_final_grade(Mock(), Mock())

        assert result["nota_final"] is None
        assert result["sin_datos"] is True

    def test_calculate_student_final_grade_weighted(self):
        calif1 = Mock()
        calif1.nota = Decimal("6.0")
        calif1.evaluacion = Mock(nombre="Prueba 1", ponderacion=Decimal("60.0"))

        calif2 = Mock()
        calif2.nota = Decimal("4.0")
        calif2.evaluacion = Mock(nombre="Prueba 2", ponderacion=Decimal("40.0"))

        queryset = Mock()
        queryset.select_related.return_value = [calif1, calif2]
        with patch(
            "backend.apps.academico.models.Calificacion.objects.filter",
            return_value=queryset,
        ), patch.object(
            GradesService,
            "_get_escala",
            return_value={
                "nota_minima": Decimal("1.0"),
                "nota_maxima": Decimal("7.0"),
                "nota_aprobacion": Decimal("4.0"),
                "redondeo_decimales": 1,
            },
        ):
            result = GradesService.calculate_student_final_grade(Mock(), Mock())

        assert result["nota_final"] == 5.2
        assert result["estado"] == "Aprobado"
        assert result["sin_datos"] is False

    def test_calculate_class_grades_stats(self):
        evaluaciones_qs = Mock()
        evaluaciones_qs.count.return_value = 2

        calificaciones_qs = Mock()
        calificaciones_qs.count.return_value = 5
        calificaciones_qs.aggregate.return_value = {"nota__avg": 5.45}

        with patch(
            "backend.apps.academico.models.Evaluacion.objects.filter",
            return_value=evaluaciones_qs,
        ), patch(
            "backend.apps.academico.models.Calificacion.objects.filter",
            return_value=calificaciones_qs,
        ):
            result = GradesService.calculate_class_grades_stats(Mock())

        assert result["total_evaluaciones"] == 2
        assert result["total_calificaciones"] == 5
        assert result["promedio_general"] == 5.45
        assert result["sin_datos"] is False

    def test_get_evaluation_by_id_returns_none(self):
        from backend.apps.academico.models import Evaluacion

        with patch(
            "backend.apps.academico.models.Evaluacion.objects.get",
            side_effect=Evaluacion.DoesNotExist,
        ):
            result = GradesService.get_evaluation_by_id(Mock(), 999)

        assert result is None

    def test_get_student_grades_summary_without_profile(self):
        from backend.apps.accounts.models import PerfilEstudiante

        user = Mock()
        user.id = 123

        with patch(
            "backend.apps.accounts.models.PerfilEstudiante.objects.get",
            side_effect=PerfilEstudiante.DoesNotExist,
        ):
            result = GradesService.get_student_grades_summary(user)

        assert result["sin_datos"] is True
        assert result["error"] == "Student profile not found"

    def test_get_student_classes_summary_without_course(self):
        user = Mock()
        user.perfil_estudiante = Mock()
        user.perfil_estudiante.curso_actual = None

        result = GradesService.get_student_classes_summary(user)

        assert "error" in result
        assert "curso asignado" in result["error"].lower()

    def test_get_teacher_classes_for_gradebook_delegates_to_teacher_classes(self):
        expected = [Mock(), Mock()]
        with patch.object(
            GradesService,
            "get_teacher_classes_for_grades",
            return_value=expected,
        ) as delegated:
            result = GradesService.get_teacher_classes_for_gradebook(Mock(), Mock())

        assert result == expected
        delegated.assert_called_once()

    def test_get_teacher_classes_for_grades(self):
        query = Mock()
        query.select_related.return_value = ["c1"]

        with patch(
            "backend.apps.cursos.models.Clase.objects.filter",
            return_value=query,
        ):
            result = GradesService.get_teacher_classes_for_grades(Mock(), Mock())

        assert result == ["c1"]

    def test_get_evaluations_for_class_list(self):
        query = Mock()
        query.order_by.return_value = ["ev1", "ev2"]

        with patch(
            "backend.apps.academico.models.Evaluacion.objects.filter",
            return_value=query,
        ):
            result = GradesService.get_evaluations_for_class(Mock())

        assert result == ["ev1", "ev2"]

    def test_get_students_with_grades_final_helper(self):
        colegio = Mock()
        colegio.rbd = 12345

        ciclo = Mock()
        clase = Mock()
        clase.curso.ciclo_academico = ciclo
        evaluacion = Mock()
        evaluacion.clase = clase

        student = Mock()
        student.id = 1

        calif = Mock()
        calif.estudiante = student
        calif.nota = Decimal("6.0")
        calif.fecha_creacion = date(2026, 5, 10)

        student_qs = Mock()
        student_qs.select_related.return_value.order_by.return_value = [student]
        evaluacion.calificaciones.all.return_value = [calif]

        with patch(
            "backend.apps.accounts.models.User.objects.filter",
            return_value=student_qs,
        ):
            result = GradesService.get_students_with_grades(colegio, evaluacion)

        assert len(result) == 1
        assert result[0]["calificacion"] == Decimal("6.0")

    def test_get_student_grades_summary_no_course_assigned(self):
        user = Mock()
        perfil = Mock()
        perfil.curso_actual = None

        with patch(
            "backend.apps.accounts.models.PerfilEstudiante.objects.get",
            return_value=perfil,
        ):
            result = GradesService.get_student_grades_summary(user)

        assert result["error"] == "No course assigned"

    def test_get_student_grades_summary_success(self):
        user = Mock()
        user.id = 2

        course = Mock()
        course.nombre = "1A"

        clase = Mock()
        clase.asignatura.nombre = "Matematica"
        clase.profesor.get_full_name.return_value = "Profesor Uno"

        course.clases.filter.return_value.select_related.return_value = [clase]

        perfil = Mock()
        perfil.curso_actual = course

        calif = Mock()
        calif.evaluacion.nombre = "Prueba 1"
        calif.evaluacion.ponderacion = Decimal("100")
        calif.evaluacion.fecha_evaluacion = date(2026, 5, 10)
        calif.nota = Decimal("5.8")

        calif_qs = Mock()
        calif_qs.select_related.return_value.order_by.return_value = [calif]

        with patch(
            "backend.apps.accounts.models.PerfilEstudiante.objects.get",
            return_value=perfil,
        ), patch.object(
            GradesService,
            "calculate_student_final_grade",
            return_value={"nota_final": 5.8, "estado": "Aprobado"},
        ), patch(
            "backend.apps.academico.models.Calificacion.objects.filter",
            return_value=calif_qs,
        ):
            result = GradesService.get_student_grades_summary(user)

        assert result["total_notas"] == 1
        assert result["curso_actual"] == "1A"
        assert result["sin_datos"] is False

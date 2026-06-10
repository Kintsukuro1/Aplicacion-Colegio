from datetime import date
from unittest.mock import Mock, patch

import pytest

from backend.apps.academico.services.attendance_service import AttendanceService
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
    ciclo.nombre = "2026"
    ciclo.estado = "ACTIVO"
    ciclo.fecha_inicio = date(2026, 3, 1)
    ciclo.fecha_fin = date(2026, 12, 20)

    curso = Mock()
    curso.id_curso = 11
    curso.activo = True
    curso.ciclo_academico = ciclo

    clase = Mock()
    clase.id = 90
    clase.id_clase = 90
    clase.activo = True
    clase.curso = curso

    return colegio, ciclo, curso, clase


class TestAttendanceServiceExecution:
    def test_validate_requires_operation(self):
        with pytest.raises(ValueError):
            AttendanceService.validate("", {})

    def test_validate_requires_dict_params(self):
        with pytest.raises(ValueError):
            AttendanceService.validate("register", [])

    def test_execute_rejects_unsupported_operation(self):
        with pytest.raises(ValueError):
            AttendanceService.execute("operation_does_not_exist", {})

    def test_execute_dispatches_custom_handler(self, monkeypatch):
        monkeypatch.setattr(
            AttendanceService,
            "_execute_ping",
            staticmethod(lambda params: {"ok": params["value"]}),
            raising=False,
        )

        result = AttendanceService.execute("ping", {"value": 11})

        assert result == {"ok": 11}


class TestAttendanceServiceClassValidations:
    def test_validate_clase_for_attendance_rejects_inactive_class(self):
        _, _, _, clase = _build_valid_class_bundle()
        clase.activo = False

        with pytest.raises(PrerequisiteException):
            AttendanceService._validate_clase_for_attendance(clase)

    def test_validate_clase_for_attendance_rejects_inactive_course(self):
        _, _, _, clase = _build_valid_class_bundle()
        clase.curso.activo = False

        with pytest.raises(PrerequisiteException):
            AttendanceService._validate_clase_for_attendance(clase)

    def test_validate_clase_for_attendance_rejects_closed_cycle(self):
        _, _, _, clase = _build_valid_class_bundle()
        clase.curso.ciclo_academico.estado = "CERRADO"

        with pytest.raises(PrerequisiteException):
            AttendanceService._validate_clase_for_attendance(clase)


class TestAttendanceServiceOperations:
    def test_register_attendance_rejects_date_outside_cycle(self, auth_user_mock):
        colegio, _, _, clase = _build_valid_class_bundle()

        with patch.object(AttendanceService, "_validate_school_integrity", return_value=None):
            with pytest.raises(PrerequisiteException):
                AttendanceService.register_attendance_for_class(
                    auth_user_mock,
                    colegio,
                    clase,
                    fecha=date(2026, 1, 15),
                    estudiantes_estados={1: "P"},
                )

    def test_register_attendance_rejects_inactive_class(self, auth_user_mock):
        colegio, _, _, clase = _build_valid_class_bundle()
        clase.activo = False

        with patch.object(AttendanceService, "_validate_school_integrity", return_value=None):
            with pytest.raises(PrerequisiteException):
                AttendanceService.register_attendance_for_class(
                    auth_user_mock,
                    colegio,
                    clase,
                    fecha=date(2026, 5, 10),
                    estudiantes_estados={1: AttendanceService.PRESENTE},
                )

    def test_register_attendance_counts_only_valid_students(self, auth_user_mock):
        colegio, ciclo, _, clase = _build_valid_class_bundle()
        another_cycle = Mock()
        another_cycle.nombre = "2025"

        student_ok = Mock()
        student_ok.perfil_estudiante = Mock()
        student_ok.perfil_estudiante.ciclo_actual = ciclo

        student_other_cycle = Mock()
        student_other_cycle.perfil_estudiante = Mock()
        student_other_cycle.perfil_estudiante.ciclo_actual = another_cycle

        with patch.object(AttendanceService, "_validate_school_integrity", return_value=None), patch(
            "backend.apps.accounts.models.User.objects.get",
            side_effect=[student_ok, student_other_cycle],
        ), patch(
            "backend.apps.academico.models.Asistencia.objects.update_or_create",
            return_value=(Mock(), True),
        ) as upsert_mock:
            count = AttendanceService.register_attendance_for_class(
                auth_user_mock,
                colegio,
                clase,
                fecha=date(2026, 5, 10),
                estudiantes_estados={
                    1: AttendanceService.PRESENTE,
                    2: AttendanceService.AUSENTE,
                    3: "X",  # Invalid state
                },
            )

        assert count == 1
        upsert_mock.assert_called_once()

    def test_update_attendance_observation_returns_false_when_not_found(self, auth_user_mock):
        colegio, _, _, _ = _build_valid_class_bundle()
        from backend.apps.academico.models import Asistencia

        with patch.object(AttendanceService, "_validate_school_integrity", return_value=None), patch(
            "backend.apps.academico.models.Asistencia.objects.get",
            side_effect=Asistencia.DoesNotExist,
        ):
            result = AttendanceService.update_attendance_observation(
                auth_user_mock,
                colegio,
                asistencia_id=999,
                observaciones="Sin registro",
            )

        assert result is False

    def test_update_attendance_observation_success(self, auth_user_mock):
        colegio, _, _, _ = _build_valid_class_bundle()
        asistencia = Mock()

        with patch.object(AttendanceService, "_validate_school_integrity", return_value=None), patch(
            "backend.apps.academico.models.Asistencia.objects.get",
            return_value=asistencia,
        ):
            result = AttendanceService.update_attendance_observation(
                auth_user_mock,
                colegio,
                asistencia_id=1,
                observaciones="Llego tarde por transporte",
            )

        assert result is True
        assert asistencia.observaciones == "Llego tarde por transporte"
        asistencia.save.assert_called_once()

    def test_get_students_for_class_returns_compact_payload(self, auth_user_mock):
        colegio, _, _, clase = _build_valid_class_bundle()
        student = Mock(
            id=7,
            nombre="Ana",
            apellido_paterno="Diaz",
            apellido_materno="Lopez",
            rut="11.111.111-1",
        )

        student_qs = Mock()
        student_qs.select_related.return_value.order_by.return_value = [student]

        with patch.object(AttendanceService, "_validate_school_integrity", return_value=None), patch.object(
            AttendanceService, "_validate_clase_for_attendance", return_value=None
        ), patch(
            "backend.apps.accounts.models.User.objects.filter",
            return_value=student_qs,
        ):
            result = AttendanceService.get_students_for_class(auth_user_mock, colegio, clase)

        assert result == [
            {
                "id": 7,
                "nombre": "Ana",
                "apellido_paterno": "Diaz",
                "apellido_materno": "Lopez",
                "rut": "11.111.111-1",
            }
        ]

    def test_get_students_with_attendance_merges_existing_records(self, auth_user_mock):
        colegio, ciclo, _, clase = _build_valid_class_bundle()
        clase.curso.ciclo_academico = ciclo

        student = Mock(id=1)
        attendance = Mock()
        attendance.estudiante = student
        attendance.estado = AttendanceService.AUSENTE

        student_qs = Mock()
        student_qs.select_related.return_value.order_by.return_value = [student]

        attendance_qs = Mock()
        attendance_qs.select_related.return_value = [attendance]

        with patch(
            "backend.apps.accounts.models.User.objects.filter",
            return_value=student_qs,
        ), patch(
            "backend.apps.academico.models.Asistencia.objects.filter",
            return_value=attendance_qs,
        ):
            result = AttendanceService.get_students_with_attendance(
                auth_user_mock, colegio, clase, date(2026, 5, 10)
            )

        assert len(result) == 1
        assert result[0]["estado"] == AttendanceService.AUSENTE

    def test_calculate_class_attendance_stats(self, auth_user_mock):
        _, _, _, clase = _build_valid_class_bundle()

        asis_qs = Mock()
        asis_qs.count.return_value = 10

        state_counts = {
            "P": 7,
            "A": 2,
            "T": 1,
            "J": 0,
        }

        def _filter_state(*args, **kwargs):
            state = kwargs.get("estado")
            state_qs = Mock()
            state_qs.count.return_value = state_counts[state]
            return state_qs

        asis_qs.filter.side_effect = _filter_state

        with patch(
            "backend.apps.academico.models.Asistencia.objects.filter",
            return_value=asis_qs,
        ):
            result = AttendanceService.calculate_class_attendance_stats(auth_user_mock, clase, days=30)

        assert result["total_registros"] == 10
        assert result["presentes"] == 7
        assert result["porcentaje_asistencia"] == 70.0

    def test_get_student_attendance_stats(self, auth_user_mock):
        _, _, _, clase = _build_valid_class_bundle()

        asis_qs = Mock()
        asis_qs.count.return_value = 8

        state_counts = {
            "P": 5,
            "A": 2,
            "T": 1,
            "J": 0,
        }

        def _filter_state(*args, **kwargs):
            state = kwargs.get("estado")
            state_qs = Mock()
            state_qs.count.return_value = state_counts[state]
            return state_qs

        asis_qs.filter.side_effect = _filter_state

        with patch(
            "backend.apps.academico.models.Asistencia.objects.filter",
            return_value=asis_qs,
        ):
            result = AttendanceService.get_student_attendance_stats(
                auth_user_mock, Mock(), clase, periodo_dias=20
            )

        assert result["total_clases"] == 8
        assert result["ausentes"] == 2
        assert result["porcentaje_asistencia"] == 62.5

    def test_get_class_for_user_returns_none_when_not_found(self):
        from backend.apps.cursos.models import Clase

        user = Mock()
        user.colegio = Mock()

        with patch(
            "backend.apps.cursos.models.Clase.objects.get",
            side_effect=Clase.DoesNotExist,
        ):
            result = AttendanceService.get_class_for_user(user, clase_id=999)

        assert result is None

    def test_prepare_attendance_data_from_post(self):
        perfil1 = Mock()
        perfil1.user.id = 10
        perfil2 = Mock()
        perfil2.user.id = 11

        data = AttendanceService.prepare_attendance_data_from_post(
            user=Mock(),
            post_data={
                "estado_10": "P",
                "obs_10": "ok",
                "obs_11": "ignored without state",
            },
            perfiles=[perfil1, perfil2],
        )

        assert data == {10: {"estado": "P", "observaciones": "ok"}}

    def test_get_student_profile_and_course(self):
        perfil = Mock()
        perfil.curso_actual = "1A"
        user = Mock()
        user.perfil_estudiante = perfil

        result = AttendanceService.get_student_profile_and_course(user)
        assert result == (perfil, "1A")

    def test_get_student_profile_and_course_when_missing(self):
        class BrokenUser:
            @property
            def perfil_estudiante(self):
                raise Exception("no profile")

        user = BrokenUser()

        perfil, curso = AttendanceService.get_student_profile_and_course(user)
        assert perfil is None
        assert curso is None

    def test_date_and_month_helpers(self):
        parsed = AttendanceService.parse_date_from_string("2026-05-10")
        assert parsed == date(2026, 5, 10)
        assert AttendanceService.get_month_name(5) == "Mayo"
        assert AttendanceService.get_month_name(99) == ""
        assert len(AttendanceService.get_months_list()) == 12
        assert len(AttendanceService.get_years_list()) == 5

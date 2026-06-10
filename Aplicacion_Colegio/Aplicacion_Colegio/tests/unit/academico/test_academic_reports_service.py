from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.http import HttpResponse

from backend.apps.academico.services.academic_reports_service import AcademicReportsService


pytestmark = pytest.mark.django_db


class _FlexiblePrerequisiteException(Exception):
    def __init__(self, error_type=None, **kwargs):
        self.error_type = error_type
        self.context = kwargs.get('context', {})
        super().__init__(str(error_type))


@pytest.fixture(autouse=True)
def _patch_prereq(monkeypatch):
    monkeypatch.setattr(
        'backend.apps.academico.services.academic_reports_service.PrerequisiteException',
        _FlexiblePrerequisiteException,
    )


@pytest.fixture(autouse=True)
def _patch_permissions(monkeypatch):
    monkeypatch.setattr(
        'backend.common.services.permission_service.PermissionService.has_permission',
        lambda *args, **kwargs: True,
    )


def _user():
    user = SimpleNamespace()
    user.id = 1
    user.role = SimpleNamespace(nombre='Administrador general')
    user.rbd_colegio = 123
    user.is_authenticated = True
    user.email = 'admin@test.cl'
    return user


class TestBasics:
    def test_validate_and_execute_dispatch(self):
        user = _user()

        with pytest.raises(ValueError):
            AcademicReportsService.validate('generate_student_academic_report', {'user': user})

        AcademicReportsService.validate('generate_student_academic_report', {'user': user, 'estudiante': Mock()})
        AcademicReportsService.validate(
            'generate_class_attendance_report',
            {'user': user, 'clase': Mock(), 'fecha_inicio': date.today(), 'fecha_fin': date.today()},
        )
        AcademicReportsService.validate('generate_class_performance_report', {'user': user, 'clase': Mock()})

        with pytest.raises(ValueError):
            AcademicReportsService.validate('x', {'user': user})

        with patch.object(AcademicReportsService, 'validate') as mock_validate, patch.object(
            AcademicReportsService,
            '_execute',
            return_value='ok',
        ) as mock_execute:
            result = AcademicReportsService.execute('generate_student_academic_report', {'user': user, 'estudiante': Mock()})

        assert result == 'ok'
        mock_validate.assert_called_once()
        mock_execute.assert_called_once()

        with pytest.raises(ValueError):
            AcademicReportsService._execute('bad', {})

    def test_execute_dispatch_methods(self):
        with patch.object(AcademicReportsService, '_execute_generate_student_academic_report', return_value='s') as s, patch.object(
            AcademicReportsService,
            '_execute_generate_class_attendance_report',
            return_value='a',
        ) as a, patch.object(AcademicReportsService, '_execute_generate_class_performance_report', return_value='p') as p:
            assert AcademicReportsService._execute('generate_student_academic_report', {}) == 's'
            assert AcademicReportsService._execute('generate_class_attendance_report', {}) == 'a'
            assert AcademicReportsService._execute('generate_class_performance_report', {}) == 'p'

        assert s.called and a.called and p.called


class TestStudentReport:
    @patch.object(AcademicReportsService, '_validate_school_integrity')
    def test_student_report_validations(self, _mock_integrity):
        estudiante = Mock(rbd_colegio=123, is_active=False, id=1, email='e@test.cl')
        with pytest.raises(_FlexiblePrerequisiteException):
            AcademicReportsService._execute_generate_student_academic_report({'estudiante': estudiante})

        estudiante.is_active = True
        type(estudiante).perfil_estudiante = property(lambda _self: (_ for _ in ()).throw(Exception('no perfil')))
        with pytest.raises(_FlexiblePrerequisiteException):
            AcademicReportsService._execute_generate_student_academic_report({'estudiante': estudiante})

    @patch.object(AcademicReportsService, '_validate_school_integrity')
    def test_student_report_missing_course(self, _mock_integrity):
        perfil = Mock(curso_actual=None)
        estudiante = Mock(
            rbd_colegio=123,
            is_active=True,
            id=1,
            email='e@test.cl',
            perfil_estudiante=perfil,
            nombre='A',
            apellido_paterno='B',
        )

        with pytest.raises(_FlexiblePrerequisiteException):
            AcademicReportsService._execute_generate_student_academic_report({'estudiante': estudiante})

    @patch.object(AcademicReportsService, '_validate_school_integrity')
    @patch('backend.apps.academico.models.Asistencia')
    @patch('backend.apps.academico.models.Calificacion')
    def test_student_report_success(self, mock_calificacion, mock_asistencia, _mock_integrity):
        curso = Mock(nombre='1A')
        clase = Mock()
        clase.asignatura.nombre = 'Matemática'
        curso.clases.filter.return_value.select_related.return_value = [clase]
        perfil = Mock(curso_actual=curso)

        estudiante = Mock(
            rbd_colegio=123,
            is_active=True,
            id=1,
            email='e@test.cl',
            perfil_estudiante=perfil,
            nombre='Ana',
            apellido_paterno='Pérez',
            apellido_materno='López',
            rut='11-1',
        )

        c1 = Mock(); c1.evaluacion.ponderacion = 50; c1.nota = 6.0
        c2 = Mock(); c2.evaluacion.ponderacion = 50; c2.nota = 4.0
        mock_calificacion.objects.filter.return_value.select_related.return_value = [c1, c2]

        asist_qs = Mock()
        asist_qs.count.return_value = 10
        asist_qs.filter.return_value.count.return_value = 8
        mock_asistencia.objects.filter.return_value = asist_qs

        result = AcademicReportsService._execute_generate_student_academic_report({'estudiante': estudiante, 'periodo': 'anual'})

        assert result['curso'] == '1A'
        assert result['promedio_general'] == 5.0
        assert result['asistencia']['porcentaje'] == 80.0


class TestClassAttendanceReport:
    @patch.object(AcademicReportsService, '_validate_school_integrity')
    def test_class_attendance_report_inactive_class(self, _mock_integrity):
        clase = Mock(activo=False)
        clase.id_clase = 1
        clase.asignatura.nombre = 'Historia'
        clase.colegio.rbd = 123

        with pytest.raises(_FlexiblePrerequisiteException):
            AcademicReportsService._execute_generate_class_attendance_report(
                {'clase': clase, 'fecha_inicio': date.today(), 'fecha_fin': date.today()}
            )

    @patch.object(AcademicReportsService, '_validate_school_integrity')
    @patch('backend.apps.accounts.models.User')
    def test_class_attendance_report_success(self, mock_user, _mock_integrity):
        clase = Mock(activo=True)
        clase.colegio.rbd = 123

        est = Mock()
        est.total_clases = 5
        est.presentes = 4
        est.ausentes = 1
        est.tardanzas = 0
        est.justificadas = 0
        students = [est]

        mock_user.objects.filter.return_value.select_related.return_value.annotate.return_value.distinct.return_value.order_by.return_value = students

        result = AcademicReportsService._execute_generate_class_attendance_report(
            {'clase': clase, 'fecha_inicio': date.today(), 'fecha_fin': date.today()}
        )

        assert result['estadisticas_generales']['total_registros'] == 5
        assert result['estadisticas_generales']['porcentaje_asistencia'] == 80.0
        assert len(result['asistencia_por_estudiante']) == 1


class TestClassPerformanceReport:
    @patch('backend.apps.accounts.models.User')
    @patch('backend.apps.academico.models.Calificacion')
    def test_class_performance_report(self, mock_calificacion, mock_user):
        clase = Mock()
        est = Mock()
        est.apellido_paterno = 'A'
        est.nombre = 'B'
        students = [est]
        mock_user.objects.filter.return_value.select_related.return_value.distinct.return_value.order_by.return_value = students

        c1 = Mock(); c1.evaluacion.ponderacion = 100; c1.nota = 6.0
        c1.evaluacion.nombre = 'Prueba 1'; c1.evaluacion.fecha_evaluacion = date.today()

        califs_qs = MagicMock()
        califs_qs.select_related.return_value = califs_qs
        califs_qs.count.return_value = 1
        califs_qs.__iter__.return_value = iter([c1])

        report_eval_qs = [Mock(nota=6.0)]

        def filter_side_effect(**kwargs):
            if 'evaluacion' in kwargs:
                return report_eval_qs
            return califs_qs

        mock_calificacion.objects.filter.side_effect = filter_side_effect

        result = AcademicReportsService._execute_generate_class_performance_report({'clase': clase})

        assert result['total_estudiantes'] == 1
        assert result['promedio_curso'] == 6.0
        assert result['aprobados'] == 1
        assert result['porcentaje_aprobacion'] == 100.0


class TestHelpersAndExports:
    @patch('backend.apps.cursos.models.Clase')
    @patch('backend.apps.academico.models.Asistencia')
    @patch('backend.apps.academico.models.Calificacion')
    def test_generate_academic_summary(self, mock_calif, mock_asist, mock_clase):
        user = _user()
        colegio = Mock()
        curso = Mock(nombre='2A')
        curso.perfil_estudiante_set.count.return_value = 30

        clase = Mock()
        clase.asignatura.nombre = 'Lenguaje'
        clase.profesor.get_full_name.return_value = 'Prof Lenguaje'
        mock_clase.objects.filter.return_value.select_related.return_value = [clase]

        calif_qs = Mock()
        calif_qs.aggregate.return_value = {'nota__avg': 5.2}
        calif_qs.count.return_value = 10
        mock_calif.objects.filter.return_value = calif_qs

        asist_qs = Mock()
        asist_qs.count.return_value = 20
        asist_qs.filter.return_value.count.return_value = 18
        mock_asist.objects.filter.return_value = asist_qs

        result = AcademicReportsService.generate_academic_summary(user, colegio, curso)

        assert result['curso'] == '2A'
        assert result['asignaturas'][0]['promedio_asignatura'] == 5.2
        assert result['asignaturas'][0]['porcentaje_asistencia'] == 90.0

    def test_parse_report_filters(self):
        f1, f2 = AcademicReportsService.parse_report_filters('2026-01-01', '2026-01-31')
        assert f1.year == 2026 and f2.year == 2026

        f3, f4 = AcademicReportsService.parse_report_filters('bad', 'bad')
        assert f3 <= f4

    @patch('backend.apps.cursos.models.Clase')
    def test_get_available_classes_variants(self, mock_clase):
        user = _user()
        colegio = Mock()
        mock_clase.objects.filter.return_value.select_related.return_value.order_by.return_value = ['c1']

        r1 = AcademicReportsService.get_available_classes(user, colegio)
        r2 = AcademicReportsService.get_available_classes_for_reports(user, colegio)

        assert r1 == ['c1']
        assert r2 == ['c1']

    @patch('backend.apps.cursos.models.Clase')
    @patch('backend.common.utils.auth_helpers.normalizar_rol')
    def test_get_classes_for_reports_by_role(self, mock_norm, mock_clase):
        user = _user()
        colegio = Mock()
        mock_clase.objects.filter.return_value.select_related.return_value.order_by.return_value = ['c1']

        mock_norm.return_value = 'admin_general'
        assert AcademicReportsService.get_classes_for_reports(user, colegio) == ['c1']

        mock_norm.return_value = 'profesor'
        assert AcademicReportsService.get_classes_for_reports(user, colegio) == ['c1']

    @patch('backend.apps.cursos.models.Clase')
    def test_get_selected_class_and_class_report_data(self, mock_clase):
        user = _user()
        colegio = Mock()
        clase = Mock()
        mock_clase.objects.filter.return_value.select_related.return_value.first.return_value = clase
        mock_clase.objects.get.return_value = clase
        mock_clase.DoesNotExist = Exception

        assert AcademicReportsService.get_selected_class_for_report(user, colegio, '') is None
        assert AcademicReportsService.get_selected_class_for_report(user, colegio, 'x') is None
        assert AcademicReportsService.get_selected_class_for_report(user, colegio, '1') is clase

        r = AcademicReportsService.get_class_report_data(user, colegio, '1', date.today(), date.today())
        assert r['clase'] is clase

        mock_clase.objects.get.side_effect = Exception('not found')
        assert AcademicReportsService.get_class_report_data(user, colegio, '1', date.today(), date.today()) is None

    def test_generate_report_data_dispatch(self):
        user = _user()
        clase = Mock()

        assert AcademicReportsService.generate_report_data(user, None, 'asistencia', date.today(), date.today()) == {}

        with patch.object(AcademicReportsService, 'generate_class_attendance_report', return_value={'a': 1}) as att, patch.object(
            AcademicReportsService,
            'generate_class_performance_report',
            return_value={'p': 1},
        ) as perf:
            assert AcademicReportsService.generate_report_data(user, clase, 'asistencia', date.today(), date.today()) == {'a': 1}
            assert AcademicReportsService.generate_report_data(user, clase, 'academico', date.today(), date.today()) == {'p': 1}
            assert AcademicReportsService.generate_report_data(user, clase, 'otro', date.today(), date.today()) == {}
        assert att.called and perf.called

    @patch('django.http.HttpResponse')
    @patch('backend.apps.cursos.models.Clase')
    def test_validate_and_get_class_for_export(self, mock_clase, mock_http):
        user = _user()
        colegio = Mock()

        mock_http.side_effect = lambda msg, status=200: {'msg': msg, 'status': status}

        assert AcademicReportsService.validate_and_get_class_for_export(user, colegio, '')['status'] == 400
        assert AcademicReportsService.validate_and_get_class_for_export(user, colegio, 'x')['status'] == 400

        mock_clase.objects.filter.return_value.select_related.return_value.first.return_value = None
        assert AcademicReportsService.validate_and_get_class_for_export(user, colegio, '1')['status'] == 404

        clase = Mock()
        mock_clase.objects.filter.return_value.select_related.return_value.first.return_value = clase
        assert AcademicReportsService.validate_and_get_class_for_export(user, colegio, '1') is clase

    def test_prepare_export_data(self):
        user = _user()
        colegio = Mock()
        clase = Mock()

        with patch.object(
            AcademicReportsService,
            'validate_and_get_class_for_export',
            return_value=HttpResponse('bad', status=400),
        ):
            bad = AcademicReportsService.prepare_export_data(user, colegio, 'asistencia', '1', '2026-01-01', '2026-01-31')
            assert bad.status_code == 400

        with patch.object(AcademicReportsService, 'validate_and_get_class_for_export', return_value=clase), patch.object(
            AcademicReportsService,
            'parse_report_filters',
            return_value=(date.today(), date.today()),
        ), patch.object(AcademicReportsService, 'generate_report_data', return_value={}):
            empty = AcademicReportsService.prepare_export_data(user, colegio, 'asistencia', '1', '2026-01-01', '2026-01-31')
            assert empty.status_code == 400

        with patch.object(AcademicReportsService, 'validate_and_get_class_for_export', return_value=clase), patch.object(
            AcademicReportsService,
            'parse_report_filters',
            return_value=(date.today(), date.today()),
        ), patch.object(AcademicReportsService, 'generate_report_data', return_value={'k': 1}):
            ok = AcademicReportsService.prepare_export_data(user, colegio, 'asistencia', '1', '2026-01-01', '2026-01-31')
            assert ok[0] is clase
            assert ok[3] == {'k': 1}

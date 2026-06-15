from datetime import date
from unittest import TestCase
from unittest.mock import Mock, patch

from django.core.exceptions import PermissionDenied

from backend.apps.core.services.dashboard_graficos_service import (
    DashboardGraficosService,
    MonthRange,
)


class TestDashboardGraficosService(TestCase):
    def test_validate_requires_supported_operation_and_params(self):
        with self.assertRaises(ValueError):
            DashboardGraficosService.validate('unknown', {})

        with self.assertRaises(ValueError):
            DashboardGraficosService.validate('get_datos_asistencia', {'rol': 'estudiante', 'escuela_rbd': 1})

    def test_execute_dispatches_supported_operation(self):
        with patch.object(DashboardGraficosService, 'validate') as mock_validate, patch.object(
            DashboardGraficosService,
            '_execute',
            return_value={'ok': True},
        ) as mock_execute:
            result = DashboardGraficosService.execute('get_datos_asistencia', {'user': Mock(), 'rol': 'estudiante', 'escuela_rbd': 1})

        assert result == {'ok': True}
        mock_validate.assert_called_once()
        mock_execute.assert_called_once()

    def test_add_months_and_last_month_ranges(self):
        assert DashboardGraficosService._add_months(date(2025, 12, 1), 2) == date(2026, 2, 1)

        with patch('backend.apps.core.services.dashboard_graficos_service.timezone.localdate', return_value=date(2025, 3, 15)):
            ranges = DashboardGraficosService._last_n_month_ranges(3)

        assert [r.label for r in ranges] == ['Ene', 'Feb', 'Mar']
        assert ranges[0].start == date(2025, 1, 1)
        assert ranges[-1].end_exclusive == date(2025, 4, 1)

    def test_get_student_course_and_get_clases_estudiante_without_course(self):
        user = Mock()

        with patch('backend.apps.core.services.dashboard_graficos_service.PerfilEstudiante') as mock_perfil:
            mock_perfil.objects.filter.return_value.first.return_value = None
            assert DashboardGraficosService._get_student_course(user) is None

        with patch.object(DashboardGraficosService, '_get_student_course', return_value=None), patch(
            'backend.apps.core.services.dashboard_graficos_service.Clase'
        ) as mock_clase:
            sentinel = Mock(name='none_qs')
            mock_clase.objects.none.return_value = sentinel
            result = DashboardGraficosService._get_clases_estudiante(user, 10)

        assert result is sentinel

    def test_execute_get_datos_asistencia_for_student(self):
        user = Mock()
        month = MonthRange(start=date(2025, 1, 1), end_exclusive=date(2025, 2, 1), label='Ene')

        qs_student = Mock()
        qs_student.count.return_value = 10
        qs_student.exclude.return_value.count.return_value = 8

        with patch.object(DashboardGraficosService, '_validate_school_integrity'), patch.object(
            DashboardGraficosService, '_last_n_month_ranges', return_value=[month]
        ), patch('backend.apps.core.services.dashboard_graficos_service.Asistencia') as mock_asistencia:
            mock_asistencia.objects.filter.return_value.filter.return_value = qs_student
            result = DashboardGraficosService._execute_get_datos_asistencia(
                {'user': user, 'rol': 'estudiante', 'escuela_rbd': 123}
            )

        assert result['labels'] == ['Ene']
        assert result['data'] == [80.0]

    def test_execute_get_datos_asistencia_for_profesor_and_unsupported_role(self):
        user = Mock()
        month = MonthRange(start=date(2025, 1, 1), end_exclusive=date(2025, 2, 1), label='Ene')

        qs_profesor = Mock()
        qs_profesor.count.return_value = 5
        qs_profesor.exclude.return_value.count.return_value = 3

        with patch.object(DashboardGraficosService, '_validate_school_integrity'), patch.object(
            DashboardGraficosService, '_last_n_month_ranges', return_value=[month]
        ), patch('backend.apps.core.services.dashboard_graficos_service.Asistencia') as mock_asistencia, patch(
            'backend.apps.core.services.dashboard_graficos_service.Clase'
        ) as mock_clase:
            mock_clase.objects.filter.return_value.values_list.return_value = [1, 2]
            mock_asistencia.objects.filter.return_value.filter.return_value = qs_profesor
            result_prof = DashboardGraficosService._execute_get_datos_asistencia(
                {'user': user, 'rol': 'profesor', 'escuela_rbd': 123}
            )

            none_qs = Mock()
            none_qs.count.return_value = 0
            none_qs.exclude.return_value.count.return_value = 0
            mock_asistencia.objects.none.return_value = none_qs
            result_unknown = DashboardGraficosService._execute_get_datos_asistencia(
                {'user': user, 'rol': 'otro', 'escuela_rbd': 123}
            )

        assert result_prof['data'] == [60.0]
        assert result_unknown['data'] == [0.0]

    def test_execute_get_datos_calificaciones_success_and_fallbacks(self):
        user = Mock()
        rows = [
            {'evaluacion__clase__asignatura__nombre': 'Lenguaje y Comunicacion', 'promedio': 5.44},
            {'evaluacion__clase__asignatura__nombre': None, 'promedio': None},
        ]

        with patch.object(DashboardGraficosService, '_validate_school_integrity'), patch(
            'backend.apps.core.services.dashboard_graficos_service.Calificacion'
        ) as mock_calificacion:
            base = mock_calificacion.objects.filter.return_value
            base.values.return_value.annotate.return_value.order_by.return_value = rows
            result = DashboardGraficosService._execute_get_datos_calificaciones(
                {'user': user, 'rol': 'admin', 'escuela_rbd': 1}
            )

            base.values.return_value.annotate.return_value.order_by.return_value = []
            empty_result = DashboardGraficosService._execute_get_datos_calificaciones(
                {'user': user, 'rol': 'admin', 'escuela_rbd': 1}
            )

            mock_calificacion.objects.filter.side_effect = Exception('boom')
            error_result = DashboardGraficosService._execute_get_datos_calificaciones(
                {'user': user, 'rol': 'admin', 'escuela_rbd': 1}
            )

        assert result['labels'] == ['Lenguaje y Comu', 'Sin asignatura']
        assert result['data'] == [5.4, 0.0]
        assert empty_result['labels'] == ['Sin datos']
        assert error_result['data'] == [0.0]

    def test_execute_get_datos_rendimiento_counts_ranges(self):
        user = Mock()
        c0, c1, c2, c3 = Mock(), Mock(), Mock(), Mock()
        c0.count.return_value = 2
        c1.count.return_value = 4
        c2.count.return_value = 6
        c3.count.return_value = 8

        with patch.object(DashboardGraficosService, '_validate_school_integrity'), patch(
            'backend.apps.core.services.dashboard_graficos_service.Calificacion'
        ) as mock_calificacion:
            base = mock_calificacion.objects.filter.return_value
            base.filter.side_effect = [base, c0, c1, c2, c3]
            result = DashboardGraficosService._execute_get_datos_rendimiento(
                {'user': user, 'rol': 'estudiante', 'escuela_rbd': 1}
            )

        assert result['title'] == 'Distribución de Notas'
        assert result['data'] == [2, 4, 6, 8]

    def test_get_datos_estadisticas_permission_denied_for_non_student(self):
        user = Mock()

        with patch.object(DashboardGraficosService, '_validate_school_integrity'), patch(
            'backend.apps.core.services.dashboard_graficos_service.PolicyService.has_capability', return_value=False
        ):
            with self.assertRaises(PermissionDenied):
                DashboardGraficosService._execute_get_datos_estadisticas({'user': user, 'rol': 'profesor', 'escuela_rbd': 1})

    def test_get_datos_estadisticas_student_success(self):
        user = Mock()
        user.id = 7

        def _student_caps(_u, capability, school_id=None):
            return capability in {'CLASS_VIEW', 'GRADE_VIEW'}

        with patch.object(DashboardGraficosService, '_validate_school_integrity'), patch(
            'backend.apps.core.services.dashboard_graficos_service.PolicyService.has_capability', side_effect=_student_caps
        ), patch('backend.apps.core.services.dashboard_graficos_service.Calificacion') as mock_calificacion, patch(
            'backend.apps.core.services.dashboard_graficos_service.Asistencia'
        ) as mock_asistencia, patch.object(
            DashboardGraficosService,
            '_get_clases_estudiante',
        ) as mock_get_clases, patch(
            'backend.apps.core.services.dashboard_graficos_service.Tarea'
        ) as mock_tarea, patch('backend.apps.core.services.dashboard_graficos_service.EntregaTarea') as mock_entrega, patch(
            'backend.apps.core.services.dashboard_graficos_service.Evaluacion'
        ) as mock_evaluacion, patch('backend.apps.core.services.dashboard_graficos_service.timezone') as mock_timezone:
            mock_calificacion.objects.filter.return_value.aggregate.return_value = {'p': 5.6}

            asist_qs = Mock()
            asist_qs.count.return_value = 10
            asist_qs.exclude.return_value.count.return_value = 9
            mock_asistencia.objects.filter.return_value = asist_qs

            clases = Mock()
            clases.values_list.return_value = [11, 12]
            mock_get_clases.return_value = clases

            tareas_qs = Mock()
            tareas_qs.values_list.return_value = [100, 200]
            mock_tarea.objects.filter.return_value = tareas_qs

            mock_entrega.objects.filter.return_value.values_list.return_value = [100]
            mock_evaluacion.objects.filter.return_value.count.return_value = 3

            mock_timezone.now.return_value = Mock()
            mock_timezone.localdate.return_value = date(2025, 1, 10)

            result = DashboardGraficosService._execute_get_datos_estadisticas(
                {'user': user, 'rol': 'estudiante', 'escuela_rbd': 1}
            )

        assert result['promedio_general'] == 5.6
        assert result['asistencia_porcentaje'] == 90.0
        assert result['tareas_pendientes'] == 1
        assert result['evaluaciones_proximas'] == 3

    def test_get_datos_estadisticas_profesor_admin_and_error_paths(self):
        user = Mock()

        with patch.object(DashboardGraficosService, '_validate_school_integrity'), patch(
            'backend.apps.core.services.dashboard_graficos_service.PolicyService.has_capability', return_value=True
        ), patch(
            'backend.apps.core.services.dashboard_graficos_service.Clase'
        ) as mock_clase, patch('backend.apps.core.services.dashboard_graficos_service.User') as mock_user, patch(
            'backend.apps.core.services.dashboard_graficos_service.Calificacion'
        ) as mock_calificacion, patch('backend.apps.core.services.dashboard_graficos_service.Asistencia') as mock_asistencia, patch(
            'backend.apps.core.services.dashboard_graficos_service.Curso'
        ) as mock_curso:
            mock_clase.objects.filter.return_value.values_list.return_value = [1, 2]
            mock_user.objects.filter.return_value.distinct.return_value.count.return_value = 20
            mock_calificacion.objects.filter.return_value.aggregate.return_value = {'p': 6.1}

            asist_qs = Mock()
            asist_qs.count.return_value = 5
            asist_qs.exclude.return_value.count.return_value = 4
            mock_asistencia.objects.filter.return_value = asist_qs

            prof_result = DashboardGraficosService._execute_get_datos_estadisticas(
                {'user': user, 'rol': 'profesor', 'escuela_rbd': 1}
            )

            mock_user.objects.filter.return_value.count.side_effect = [30, 6]
            mock_curso.objects.filter.return_value.count.return_value = 4
            mock_calificacion.objects.filter.return_value.aggregate.return_value = {'p': 5.0}
            admin_result = DashboardGraficosService._execute_get_datos_estadisticas(
                {'user': user, 'rol': 'admin', 'escuela_rbd': 1}
            )

            unsupported_result = DashboardGraficosService._execute_get_datos_estadisticas(
                {'user': user, 'rol': 'visitante', 'escuela_rbd': 1}
            )

            mock_clase.objects.filter.side_effect = Exception('boom')
            error_result = DashboardGraficosService._execute_get_datos_estadisticas(
                {'user': user, 'rol': 'profesor', 'escuela_rbd': 1}
            )

        assert prof_result['total_clases'] == 2
        assert prof_result['promedio_clases'] == 6.1
        assert admin_result['total_estudiantes'] == 30
        assert admin_result['total_profesores'] == 6
        assert unsupported_result == {'error': 'Rol no soportado'}
        assert error_result == {'error': 'No se pudieron cargar las estadísticas'}
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import PermissionDenied

from backend.apps.core.services.dashboard_context_service import DashboardContextService


pytestmark = pytest.mark.django_db


class TestDashboardContextServiceValidation:
    def test_validate_unsupported_operation_raises(self):
        with pytest.raises(ValueError, match='Operación no soportada'):
            DashboardContextService.validate('invalid_op', {})

    @pytest.mark.parametrize(
        'operation,params,error_msg',
        [
            ('get_estudiante_context', {'pagina_solicitada': 'inicio', 'escuela_rbd': 1}, 'user'),
            ('get_estudiante_context', {'user': Mock(), 'escuela_rbd': 1}, 'pagina_solicitada'),
            ('get_estudiante_context', {'user': Mock(), 'pagina_solicitada': 'inicio'}, 'escuela_rbd'),
            ('get_asistencia_context', {'colegio': Mock()}, 'user'),
            ('get_asistencia_context', {'user': Mock()}, 'colegio'),
            ('get_profesor_context', {'pagina_solicitada': 'perfil', 'escuela_rbd': 1}, 'user'),
            ('get_notificaciones_context', {}, 'user'),
        ],
    )
    def test_validate_required_params(self, operation, params, error_msg):
        with pytest.raises(ValueError, match=error_msg):
            DashboardContextService.validate(operation, params)

    def test_execute_routes_to_internal_execute(self):
        with patch.object(DashboardContextService, 'validate') as mock_validate, patch.object(
            DashboardContextService, '_execute', return_value={'ok': True}
        ) as mock_execute:
            result = DashboardContextService.execute('get_notificaciones_context', {'user': Mock()})

        assert result == {'ok': True}
        mock_validate.assert_called_once()
        mock_execute.assert_called_once()

    def test_execute_internal_unsupported_raises(self):
        with pytest.raises(ValueError, match='Operación no soportada'):
            DashboardContextService._execute('invalid_op', {})

    def test_validate_school_integrity_when_rbd_present(self):
        with patch(
            'backend.apps.core.services.dashboard_context_service.IntegrityService.validate_school_integrity_or_raise'
        ) as mock_integrity:
            DashboardContextService._validate_school_integrity(12345, 'ACTION')

        mock_integrity.assert_called_once_with(school_id=12345, action='ACTION')

    def test_validate_school_integrity_when_rbd_missing(self):
        with patch(
            'backend.apps.core.services.dashboard_context_service.IntegrityService.validate_school_integrity_or_raise'
        ) as mock_integrity:
            DashboardContextService._validate_school_integrity(None, 'ACTION')

        mock_integrity.assert_not_called()


class TestDashboardContextServiceEstudiante:
    def test_get_estudiante_context_wrapper(self):
        with patch.object(DashboardContextService, 'execute', return_value={'x': 1}) as mock_execute:
            result = DashboardContextService.get_estudiante_context(Mock(), 'inicio', 111)

        assert result == {'x': 1}
        mock_execute.assert_called_once()

    def test_execute_get_estudiante_context_requires_permission_for_non_student(self):
        user = Mock()
        user.role = Mock(nombre='Profesor')

        with patch('backend.apps.core.services.dashboard_context_service.PolicyService.has_capability', return_value=False), patch.object(
            DashboardContextService, '_validate_school_integrity'
        ):
            with pytest.raises(PermissionDenied):
                DashboardContextService._execute_get_estudiante_context(
                    {
                        'user': user,
                        'pagina_solicitada': 'inicio',
                        'escuela_rbd': 123,
                        'request_get_params': {},
                    }
                )

    @pytest.mark.parametrize(
        'pagina,helper_name,expected',
        [
            ('inicio', '_get_estudiante_inicio_context', {'a': 1}),
            ('perfil', '_get_estudiante_perfil_context', {'b': 2}),
            ('asistencia', '_get_estudiante_asistencia_context', {'c': 3}),
            ('mis_clases', '_get_estudiante_clases_context', {'d': 4}),
            ('mis_notas', '_get_estudiante_notas_context', {'e': 5}),
            ('mis_tareas', '_get_estudiante_tareas_context', {'f': 6}),
            ('mis_evaluaciones', '_get_estudiante_evaluaciones_context', {'g': 7}),
        ],
    )
    def test_execute_get_estudiante_context_routes_by_page(self, pagina, helper_name, expected):
        user = Mock()
        user.role = Mock(nombre='Alumno')

        patch_target = f'backend.apps.core.services.dashboard_context_service.DashboardContextService.{helper_name}'
        def _has_capability(_u, capability, school_id=None):
            return capability in {'CLASS_VIEW', 'GRADE_VIEW'}

        with patch('backend.apps.core.services.dashboard_context_service.PolicyService.has_capability', side_effect=_has_capability), patch.object(
            DashboardContextService, '_validate_school_integrity'
        ), patch(patch_target, return_value=expected) as mock_helper:
            result = DashboardContextService._execute_get_estudiante_context(
                {
                    'user': user,
                    'pagina_solicitada': pagina,
                    'escuela_rbd': 123,
                    'request_get_params': {'mes': '2026-01'},
                }
            )

        assert result == expected
        if pagina in ('inicio', 'perfil'):
            mock_helper.assert_called_once_with(user, 123)
        elif pagina == 'asistencia':
            mock_helper.assert_called_once_with(user, {'mes': '2026-01'})
        else:
            mock_helper.assert_called_once_with(user)

    def test_execute_get_estudiante_context_unknown_page_returns_empty(self):
        user = Mock()
        user.role = Mock(nombre='Alumno')

        def _has_capability(_u, capability, school_id=None):
            return capability in {'CLASS_VIEW', 'GRADE_VIEW'}

        with patch('backend.apps.core.services.dashboard_context_service.PolicyService.has_capability', side_effect=_has_capability), patch.object(
            DashboardContextService, '_validate_school_integrity'
        ):
            result = DashboardContextService._execute_get_estudiante_context(
                {
                    'user': user,
                    'pagina_solicitada': 'no_existe',
                    'escuela_rbd': 123,
                    'request_get_params': {},
                }
            )

        assert result == {}


class TestDashboardContextServiceProfesorYNotificaciones:
    def test_get_profesor_clases_context_returns_fallback_on_error(self):
        user = Mock(email='profe@test.cl')
        with patch(
            'backend.apps.academico.services.academic_view_service.AcademicViewService.get_teacher_classes',
            side_effect=Exception('boom'),
        ):
            result = DashboardContextService._get_profesor_clases_context(user)

        assert result['total_clases'] == 0
        assert result['mis_clases'] == []

    @pytest.mark.parametrize(
        'pagina,helper_name,helper_result',
        [
            ('perfil', '_get_profesor_perfil_context', {'perfil': True}),
            ('mis_clases', '_get_profesor_clases_context', {'mis_clases': []}),
            ('notas', '_get_profesor_notas_context', {'notas': []}),
            ('libro_clases', '_get_profesor_libro_clases_context', {'libro': []}),
            ('reportes', '_get_profesor_reportes_context', {'reportes': []}),
            ('disponibilidad', '_get_profesor_disponibilidad_context', {'disponibilidad': []}),
        ],
    )
    def test_execute_get_profesor_context_routes_by_page(self, pagina, helper_name, helper_result):
        user = Mock()
        colegio = Mock(rbd=123)

        patch_target = f'backend.apps.core.services.dashboard_context_service.DashboardContextService.{helper_name}'
        with patch.object(DashboardContextService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=colegio
        ), patch(patch_target, return_value=helper_result) as mock_helper:
            result = DashboardContextService._execute_get_profesor_context(
                {
                    'request_get_params': {'tipo': 'asistencia'},
                    'user': user,
                    'pagina_solicitada': pagina,
                    'escuela_rbd': 123,
                }
            )

        assert result == helper_result
        if pagina == 'perfil':
            mock_helper.assert_called_once_with(user, 123)
        elif pagina == 'mis_clases':
            mock_helper.assert_called_once_with(user)
        elif pagina in ('notas', 'libro_clases', 'reportes'):
            mock_helper.assert_called_once_with({'tipo': 'asistencia'}, user, colegio)
        else:
            mock_helper.assert_called_once_with(user, colegio)

    def test_execute_get_notificaciones_context_formats_items(self):
        user = Mock()
        notif_1 = SimpleNamespace(
            titulo='Aviso 1',
            mensaje='M1',
            fecha_creacion='2026-01-01',
            tipo='calificacion',
            enlace='/a',
            leido=False,
        )
        notif_2 = SimpleNamespace(
            titulo='Aviso 2',
            mensaje='M2',
            fecha_creacion='2026-01-02',
            tipo='desconocido',
            enlace=None,
            leido=True,
        )

        unread_qs = Mock()
        unread_qs.count.return_value = 2
        recent_qs = Mock()
        recent_qs.order_by.return_value = [notif_1, notif_2]

        with patch('backend.apps.notificaciones.models.Notificacion.objects.filter', side_effect=[unread_qs, recent_qs]):
            result = DashboardContextService._execute_get_notificaciones_context({'user': user})

        assert result['notificaciones_count'] == 2
        assert len(result['notificaciones_recientes']) == 2
        assert result['notificaciones_recientes'][0]['icono'] == 'star'
        assert result['notificaciones_recientes'][1]['icono'] == 'bell'
        assert result['notificaciones_recientes'][1]['url'] == '#'


class TestDashboardContextServiceFallbacks:
    def test_get_estudiante_inicio_context_with_data(self):
        user = Mock()
        user.email = 'alumno@test.cl'
        curso = Mock()
        perfil = Mock(curso_actual=curso)

        bloque_values = Mock()
        bloque_values.distinct.return_value.count.return_value = 2
        bloques_qs = Mock()
        bloques_qs.values.return_value = bloque_values

        tareas_qs = Mock()
        tareas_qs.exclude.return_value.count.return_value = 1

        califs_promedio_qs = Mock()
        califs_promedio_qs.aggregate.return_value = {'promedio': 5.6}

        califs_progreso_qs = Mock()
        califs_progreso_qs.values.return_value.annotate.return_value = [
            {'evaluacion__clase_id': 10, 'total': 1}
        ]

        asist_qs = Mock()
        asist_qs.aggregate.return_value = {'total': 2, 'presentes': 1}

        asignatura = Mock(nombre='Matemática', codigo='MAT101')
        profesor = Mock()
        profesor.get_full_name.return_value = 'Profe Uno'
        clase = SimpleNamespace(id=10, asignatura=asignatura, profesor=profesor, total_evaluaciones=2)
        clases_qs = Mock()
        clases_qs.select_related.return_value = clases_qs
        clases_qs.annotate.return_value = clases_qs
        clases_qs.order_by.return_value = [clase]

        with patch('backend.apps.accounts.models.PerfilEstudiante.objects.get', return_value=perfil), patch(
            'backend.apps.cursos.models.BloqueHorario.objects.filter', return_value=bloques_qs
        ), patch('backend.apps.academico.models.Tarea.objects.filter', return_value=tareas_qs), patch(
            'backend.apps.academico.models.EntregaTarea.objects.filter'
        ) as mock_entrega_filter, patch(
            'backend.apps.academico.models.Calificacion.objects.filter',
            side_effect=[califs_promedio_qs, califs_progreso_qs],
        ), patch('backend.apps.academico.models.Asistencia.objects.filter', return_value=asist_qs), patch(
            'backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs
        ):
            mock_entrega_filter.return_value.values_list.return_value = [99]
            result = DashboardContextService._get_estudiante_inicio_context(user, 123)

        assert result['clases_hoy'] == 2
        assert result['tareas_pendientes'] == 1
        assert result['promedio_general'] == 5.6
        assert result['porcentaje_asistencia'] == 50.0
        assert result['sin_datos'] is False
        assert len(result['clases_activas']) == 1

    def test_get_estudiante_asistencia_context_without_records(self):
        user = Mock(email='alumno@test.cl')

        asistencias_query = Mock()
        asistencias_query.count.return_value = 0
        asistencias_query.aggregate.return_value = {
            'total': 0,
            'presentes': 0,
            'ausentes': 0,
            'tardanzas': 0,
        }
        asistencias_query.filter.return_value.order_by.return_value = []
        asistencias_query.select_related.return_value = asistencias_query

        clases_qs = Mock()
        clases_qs.select_related.return_value = clases_qs
        clases_qs.order_by.return_value = clases_qs

        with patch('backend.apps.academico.models.Asistencia.objects.filter', return_value=asistencias_query), patch(
            'backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs
        ):
            result = DashboardContextService._get_estudiante_asistencia_context(user, {'mes': 'bad-format'})

        assert result['presentes'] == 0
        assert result['ausentes'] == 0
        assert result['tardanzas'] == 0
        assert result['porcentaje_asistencia'] == 0
        assert result['sin_datos_asistencia'] is True

    def test_get_estudiante_inicio_context_without_profile(self):
        from backend.apps.accounts.models import PerfilEstudiante

        user = Mock()
        with patch(
            'backend.apps.accounts.models.PerfilEstudiante.objects.get',
            side_effect=PerfilEstudiante.DoesNotExist,
        ):
            result = DashboardContextService._get_estudiante_inicio_context(user, 123)

        assert result['sin_datos'] is True
        assert result['clases_hoy'] == 0

    def test_get_estudiante_perfil_context_without_profile(self):
        from backend.apps.accounts.models import PerfilEstudiante

        with patch(
            'backend.apps.accounts.models.PerfilEstudiante.objects.select_related',
        ) as mock_select:
            mock_select.return_value.get.side_effect = PerfilEstudiante.DoesNotExist
            result = DashboardContextService._get_estudiante_perfil_context(Mock(), 123)

        assert result == {}

    def test_get_estudiante_clases_context_without_profile(self):
        from backend.apps.accounts.models import PerfilEstudiante

        user = Mock(email='alumno@test.cl')
        with patch(
            'backend.apps.accounts.models.PerfilEstudiante.objects.get',
            side_effect=PerfilEstudiante.DoesNotExist,
        ):
            result = DashboardContextService._get_estudiante_clases_context(user)

        assert result['mis_clases'] == []
        assert result['total_clases'] == 0

    def test_get_estudiante_notas_context_without_profile(self):
        from backend.apps.accounts.models import PerfilEstudiante

        with patch(
            'backend.apps.accounts.models.PerfilEstudiante.objects.get',
            side_effect=PerfilEstudiante.DoesNotExist,
        ):
            result = DashboardContextService._get_estudiante_notas_context(Mock())

        assert result['promedio_general'] == 0.0
        assert result['curso_actual'] is None

    def test_get_profesor_perfil_context_handles_internal_exception(self):
        user = Mock(id=7)
        clases_qs = Mock()
        clases_qs.values.return_value.distinct.return_value.count.return_value = 3
        eval_count = Mock()
        eval_count.count.return_value = 8
        calif_qs = Mock()
        calif_qs.values.return_value.distinct.return_value.count.return_value = 20
        planif_qs = Mock()
        planif_qs.count.return_value = 5

        with patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs), patch(
            'backend.apps.academico.models.Evaluacion.objects.filter', return_value=eval_count
        ), patch(
            'backend.apps.academico.models.Calificacion.objects.filter', return_value=calif_qs
        ), patch('backend.apps.academico.models.Planificacion.objects.filter', return_value=planif_qs):
            result = DashboardContextService._get_profesor_perfil_context(user, 123)

        assert result['estadisticas']['total_asignaturas'] == 3
        assert result['estadisticas']['total_evaluaciones'] == 8
        assert result['estadisticas']['total_estudiantes'] == 20
        assert result['estadisticas']['total_planificaciones'] == 5

    def test_get_estudiante_clases_context_with_data(self):
        user = Mock(email='alumno@test.cl')
        perfil = Mock(curso_actual='2A')

        bloque_1 = Mock(bloque_numero=1)
        bloque_1.get_dia_semana_display.return_value = 'Lunes'
        bloque_1.hora_inicio.strftime.return_value = '08:00'
        bloque_1.hora_fin.strftime.return_value = '08:45'
        bloque_2 = Mock(bloque_numero=2)
        bloque_2.get_dia_semana_display.return_value = 'Lunes'
        bloque_2.hora_inicio.strftime.return_value = '08:45'
        bloque_2.hora_fin.strftime.return_value = '09:30'

        bloques_qs = Mock()
        bloques_qs.order_by.return_value = bloques_qs
        bloques_qs.count.return_value = 2
        bloques_qs.__iter__ = Mock(return_value=iter([bloque_1, bloque_2]))

        asignatura = Mock(nombre='Lenguaje', codigo='LEN101', color='blue', horas_semanales=4)
        profesor = Mock(email='profe@test.cl')
        profesor.get_full_name.return_value = 'Profe Uno'
        clase = Mock(id=30, asignatura=asignatura, profesor=profesor, total_evaluaciones=5)
        clase.bloques_horario_activos = [bloque_1, bloque_2]

        clases_qs = Mock()
        clases_qs.select_related.return_value = clases_qs
        clases_qs.prefetch_related.return_value = clases_qs
        clases_qs.annotate.return_value = clases_qs
        clases_qs.order_by.return_value = clases_qs
        clases_qs.__iter__ = Mock(return_value=iter([clase]))

        with patch('backend.apps.accounts.models.PerfilEstudiante.objects.get', return_value=perfil), patch(
            'backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs
        ), patch('backend.apps.academico.models.Calificacion.objects.filter') as mock_calif:
            mock_calif.return_value.values.return_value.annotate.return_value = [
                {'evaluacion__clase_id': 30, 'total': 1}
            ]
            result = DashboardContextService._get_estudiante_clases_context(user)

        assert result['curso_actual'] == '2A'
        assert result['total_clases'] == 1
        assert result['mis_clases'][0]['progreso'] == 20
        assert result['mis_clases'][0]['color_progreso'] == 'progress-low'

    def test_get_estudiante_notas_context_with_data(self):
        user = Mock()
        perfil = Mock(curso_actual='3A')
        profesor = Mock()
        profesor.get_full_name.return_value = 'Profe Dos'
        asignatura = Mock(nombre='Historia')

        clase = Mock(asignatura=asignatura, profesor=profesor)
        eval_1 = Mock(nombre='Prueba 1', fecha_evaluacion='2026-01-10', ponderacion=40, clase=clase)
        eval_2 = Mock(nombre='Prueba 2', fecha_evaluacion='2026-01-20', ponderacion=60, clase=clase)
        calif_1 = Mock(evaluacion=eval_1, nota=5.0)
        calif_2 = Mock(evaluacion=eval_2, nota=6.0)

        califs_qs = Mock()
        califs_qs.select_related.return_value = califs_qs
        califs_qs.order_by.return_value = [calif_1, calif_2]

        with patch('backend.apps.accounts.models.PerfilEstudiante.objects.get', return_value=perfil), patch(
            'backend.apps.academico.models.Calificacion.objects.filter', return_value=califs_qs
        ):
            result = DashboardContextService._get_estudiante_notas_context(user)

        assert result['total_notas'] == 2
        assert result['promedio_general'] == 5.5
        assert result['notas_por_asignatura'][0]['estado'] == 'Aprobado'

    def test_get_profesor_notas_context_without_selected_class(self):
        clases_qs = Mock()
        clases_qs.exists.return_value = False
        clases_qs.select_related.return_value = clases_qs

        with patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs), patch(
            'backend.apps.academico.models.Evaluacion.objects.filter'
        ) as mock_evals_filter, patch('backend.apps.academico.models.Calificacion.objects.filter') as mock_calif_filter:
            mock_evals_filter.return_value.count.return_value = 0
            mock_calif_filter.return_value.count.return_value = 0
            result = DashboardContextService._get_profesor_notas_context({}, Mock(), Mock())

        assert result['filtro_clase_id'] == ''
        assert result['total_evaluaciones'] == 0
        assert result['promedio_general'] == 0

    def test_get_profesor_notas_context_with_selected_class(self):
        user = Mock()
        colegio = Mock()
        clase = Mock(id=88)

        clases_qs = Mock()
        clases_qs.select_related.return_value = clases_qs
        clases_qs.exists.return_value = True
        clases_qs.first.return_value = clase

        eval_1 = Mock(nombre='E1')
        eval_2 = Mock(nombre='E2')
        evals_qs = Mock()
        evals_qs.order_by.return_value = [eval_1, eval_2]

        estudiante = Mock()
        estudiante_rel = Mock(estudiante=estudiante)
        estudiantes_qs = Mock()
        estudiantes_qs.select_related.return_value = [estudiante_rel]

        total_califs_qs = Mock()
        total_califs_qs.count.return_value = 4
        total_avg_qs = Mock()
        total_avg_qs.aggregate.return_value = {'avg_nota': 5.0}

        eval1_califs_qs = Mock()
        eval1_califs_qs.count.return_value = 2
        eval1_califs_qs.aggregate.return_value = {'avg_nota': 5.5}
        eval2_califs_qs = Mock()
        eval2_califs_qs.count.return_value = 1
        eval2_califs_qs.aggregate.return_value = {'avg_nota': 4.0}

        calif_first_1 = Mock()
        calif_first_1.first.return_value = Mock(nota=6.0)
        calif_first_2 = Mock()
        calif_first_2.first.return_value = Mock(nota=4.0)

        with patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs), patch(
            'backend.apps.cursos.models.Clase.objects.get', return_value=clase
        ), patch('backend.apps.academico.models.Evaluacion.objects.filter', side_effect=[Mock(count=Mock(return_value=3)), evals_qs]), patch(
            'backend.apps.academico.models.Calificacion.objects.filter',
            side_effect=[total_califs_qs, total_avg_qs, eval1_califs_qs, eval2_califs_qs, calif_first_1, calif_first_2],
        ), patch('backend.apps.cursos.models.ClaseEstudiante.objects.filter', return_value=estudiantes_qs):
            result = DashboardContextService._get_profesor_notas_context({'clase_id': '88'}, user, colegio)

        assert result['clase_seleccionada'] is clase
        assert result['promedio_general'] == 5.0
        assert len(result['evaluaciones']) == 2
        assert len(result['estudiantes_con_notas']) == 1

    def test_get_profesor_libro_clases_context_invalid_filter(self):
        clases = Mock()
        with patch(
            'backend.apps.academico.services.grades_service.GradesService.get_teacher_classes_for_gradebook',
            return_value=clases,
        ):
            result = DashboardContextService._get_profesor_libro_clases_context({'clase_id': 'abc'}, Mock(), Mock())

        assert result['evaluaciones'] == []
        assert result['total_evaluaciones'] == 0

    def test_get_profesor_libro_clases_context_with_valid_filter(self):
        clase = Mock()
        clases = Mock()
        clases.filter.return_value.first.return_value = clase

        gradebook = {
            'evaluaciones': ['e1'],
            'matriz_calificaciones': ['m1'],
            'promedios_evaluaciones': [5.5],
            'total_evaluaciones': 1,
            'total_estudiantes': 3,
            'promedio_general': 5.5,
        }

        with patch(
            'backend.apps.academico.services.grades_service.GradesService.get_teacher_classes_for_gradebook',
            return_value=clases,
        ), patch(
            'backend.apps.academico.services.grades_service.GradesService.build_gradebook_matrix',
            return_value=gradebook,
        ):
            result = DashboardContextService._get_profesor_libro_clases_context({'clase_id': '10'}, Mock(), Mock())

        assert result['evaluaciones'] == ['e1']
        assert result['total_estudiantes'] == 3

    def test_get_profesor_reportes_context_without_filter(self):
        clases = Mock()
        with patch(
            'backend.apps.academico.services.academic_reports_service.AcademicReportsService.get_classes_for_reports',
            return_value=clases,
        ):
            result = DashboardContextService._get_profesor_reportes_context({}, Mock(), Mock())

        assert result['tipo_reporte'] == 'asistencia'
        assert result['reporte_data'] is None

    def test_get_profesor_reportes_context_academico(self):
        clase = Mock()
        clases = Mock()
        clases.filter.return_value.first.return_value = clase

        with patch(
            'backend.apps.academico.services.academic_reports_service.AcademicReportsService.get_classes_for_reports',
            return_value=clases,
        ), patch(
            'backend.apps.academico.services.academic_reports_service.AcademicReportsService.parse_report_filters',
            return_value=('fi', 'ff'),
        ), patch(
            'backend.apps.academico.services.academic_reports_service.AcademicReportsService.generate_class_performance_report',
            return_value={'ok': True},
        ):
            result = DashboardContextService._get_profesor_reportes_context(
                {'clase_id': '1', 'tipo': 'academico'},
                Mock(),
                Mock(),
            )

        assert result['reporte_data'] == {'ok': True}

    def test_get_profesor_disponibilidad_context_without_blocks(self):
        bloques_qs = Mock()
        bloques_qs.order_by.return_value = []
        bloques_con_clases_qs = Mock()
        bloques_con_clases_qs.count.return_value = 0
        clases_qs = Mock()
        clases_qs.select_related.return_value = []
        disp_qs = Mock()
        disp_qs.count.return_value = 0

        with patch('backend.apps.cursos.models.BloqueHorario.objects.filter', side_effect=[bloques_qs, bloques_con_clases_qs]), patch(
            'backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs
        ), patch('backend.apps.accounts.models.DisponibilidadProfesor.objects.filter', return_value=disp_qs):
            result = DashboardContextService._get_profesor_disponibilidad_context(Mock(), Mock())

        assert result['bloques_horarios'] == []
        assert result['estadisticas']['total_bloques'] == 0
        assert result['estadisticas']['porcentaje_disponibilidad'] == 0

    def test_get_profesor_disponibilidad_context_with_blocks(self):
        user = Mock()
        colegio = Mock()

        bloque = Mock(bloque_numero=1)
        bloque.hora_inicio.strftime.return_value = '08:00'
        bloque.hora_fin.strftime.return_value = '08:45'
        bloques_qs = Mock()
        bloques_qs.order_by.return_value = [bloque, bloque]

        clases_qs = Mock()
        clases_qs.select_related.return_value = [Mock()]
        bloques_clases_qs = Mock()
        bloques_clases_qs.count.return_value = 1

        exists_true = Mock()
        exists_true.exists.return_value = True
        exists_false = Mock()
        exists_false.exists.return_value = False
        count_qs = Mock()
        count_qs.count.return_value = 3

        with patch(
            'backend.apps.cursos.models.BloqueHorario.objects.filter',
            side_effect=[bloques_qs, bloques_clases_qs],
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases_qs), patch(
            'backend.apps.accounts.models.DisponibilidadProfesor.objects.filter',
            side_effect=[exists_true, exists_false, exists_true, exists_false, exists_true, count_qs],
        ):
            result = DashboardContextService._get_profesor_disponibilidad_context(user, colegio)

        assert len(result['bloques_horarios']) == 1
        assert result['estadisticas']['total_bloques'] == 5
        assert result['estadisticas']['bloques_disponibles'] == 3

    def test_execute_get_asistencia_context_with_selected_class(self):
        clase = Mock(id=10)
        clases = Mock()
        clases.count.return_value = 1
        clases.exists.return_value = True
        clases.first.return_value = clase
        clases.select_related.return_value = clases

        with patch.object(DashboardContextService, '_validate_school_integrity'), patch(
            'backend.apps.cursos.models.Clase.objects.filter', return_value=clases
        ), patch('backend.apps.cursos.models.Clase.objects.get', return_value=clase), patch(
            'backend.apps.academico.services.attendance_service.AttendanceService.get_students_with_attendance',
            return_value=['ok'],
        ) as mock_students, patch(
            'backend.apps.academico.services.attendance_service.AttendanceService.calculate_class_attendance_stats',
            return_value={'p': 90},
        ) as mock_stats:
            result = DashboardContextService._execute_get_asistencia_context(
                {
                    'request_get_params': {},
                    'colegio': Mock(rbd=123),
                    'user': Mock(),
                }
            )

        assert result['total_clases'] == 1
        assert result['estudiantes_con_asistencia'] == ['ok']
        assert result['stats_clase'] == {'p': 90}
        mock_students.assert_called_once()
        mock_stats.assert_called_once()

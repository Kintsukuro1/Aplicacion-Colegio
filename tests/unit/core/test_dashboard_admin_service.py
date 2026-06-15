from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.dashboard_admin_service import DashboardAdminService


pytestmark = pytest.mark.django_db


class TestDashboardAdminServiceCore:
    def test_validate_rejects_empty_operation(self):
        with pytest.raises(ValueError, match='operation'):
            DashboardAdminService.validate('', {})

    def test_validate_rejects_non_dict_params(self):
        with pytest.raises(ValueError, match='params debe ser dict'):
            DashboardAdminService.validate('x', [])

    def test_execute_uses_default_empty_params(self):
        with patch.object(DashboardAdminService, 'validate') as mock_validate, patch.object(
            DashboardAdminService, '_execute', return_value={'ok': True}
        ) as mock_execute:
            result = DashboardAdminService.execute('custom_op')

        assert result == {'ok': True}
        mock_validate.assert_called_once_with('custom_op', {})
        mock_execute.assert_called_once_with('custom_op', {})

    def test_execute_internal_unknown_operation_raises(self):
        with pytest.raises(ValueError, match='Operación no soportada'):
            DashboardAdminService._execute('no_handler', {})

    def test_execute_internal_calls_dynamic_handler(self):
        with patch.object(
            DashboardAdminService,
            '_execute_demo',
            return_value={'demo': True},
            create=True,
        ) as mock_handler:
            result = DashboardAdminService._execute('demo', {'a': 1})

        assert result == {'demo': True}
        mock_handler.assert_called_once_with({'a': 1})

    def test_validate_school_integrity_delegates(self):
        with patch(
            'backend.apps.core.services.dashboard_admin_service.IntegrityService.validate_school_integrity_or_raise'
        ) as mock_integrity:
            DashboardAdminService._validate_school_integrity(321, 'ACTION')

        mock_integrity.assert_called_once_with(school_id=321, action='ACTION')


class TestDashboardAdminServiceSetupHelpers:
    def test_validate_colegio_setup_returns_not_configured_error(self):
        from backend.apps.institucion.models import Colegio

        with patch(
            'backend.apps.institucion.models.Colegio.objects.get',
            side_effect=Colegio.DoesNotExist,
        ), patch(
            'backend.apps.core.services.dashboard_admin_service.ErrorResponseBuilder.build',
            return_value={'error': 'SCHOOL_NOT_CONFIGURED'},
        ) as mock_error:
            ok, result = DashboardAdminService._validate_colegio_setup(999)

        assert ok is False
        assert result == {'error': 'SCHOOL_NOT_CONFIGURED'}
        mock_error.assert_called_once()

    def test_validate_colegio_setup_returns_missing_ciclo_error(self):
        colegio = Mock(nombre='Colegio Uno')
        ciclo_qs = Mock()
        ciclo_qs.first.return_value = None

        with patch('backend.apps.institucion.models.Colegio.objects.get', return_value=colegio), patch(
            'backend.apps.institucion.models.CicloAcademico.objects.filter', return_value=ciclo_qs
        ), patch(
            'backend.apps.core.services.dashboard_admin_service.ErrorResponseBuilder.build',
            return_value={'error': 'MISSING_CICLO_ACTIVO'},
        ) as mock_error:
            ok, result = DashboardAdminService._validate_colegio_setup(123)

        assert ok is False
        assert result == {'error': 'MISSING_CICLO_ACTIVO'}
        mock_error.assert_called_once()

    def test_validate_colegio_setup_success(self):
        colegio = Mock(nombre='Colegio Uno')
        ciclo = Mock(estado='ACTIVO')
        ciclo_qs = Mock()
        ciclo_qs.first.return_value = ciclo

        with patch('backend.apps.institucion.models.Colegio.objects.get', return_value=colegio), patch(
            'backend.apps.institucion.models.CicloAcademico.objects.filter', return_value=ciclo_qs
        ):
            ok, result = DashboardAdminService._validate_colegio_setup(123)

        assert ok is True
        assert result['colegio'] is colegio
        assert result['ciclo_activo'] is ciclo

    @pytest.mark.parametrize('count_value,expected', [(0, (False, 0)), (4, (True, 4))])
    def test_validate_cursos_exist(self, count_value, expected):
        count_qs = Mock()
        count_qs.count.return_value = count_value

        with patch('backend.apps.cursos.models.Curso.objects.filter', return_value=count_qs):
            result = DashboardAdminService._validate_cursos_exist(Mock(), Mock())

        assert result == expected

    def test_get_infraestructura_context_groups_by_type(self):
        item_a = SimpleNamespace(tipo='Sala', nombre='A')
        item_b = SimpleNamespace(tipo='Laboratorio', nombre='B')
        item_c = SimpleNamespace(tipo='Sala', nombre='C')

        infra_qs = Mock()
        infra_qs.order_by.return_value = [item_a, item_b, item_c]

        stats_qs = Mock()
        stats_qs.aggregate.return_value = {'total_espacios': 3, 'total_salas': 2}

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Infraestructura.objects.filter',
            side_effect=[infra_qs, stats_qs],
        ):
            result = DashboardAdminService._get_infraestructura_context(123)

        assert len(result['infraestructura']) == 3
        assert set(result['infraestructura_agrupada'].keys()) == {'Sala', 'Laboratorio'}
        assert result['estadisticas']['total_espacios'] == 3


class TestDashboardAdminServiceAdminEscolar:
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_admin_escolar_context_mi_escuela_success(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()
        colegio_qs = Mock()
        colegio_qs.prefetch_related.return_value.get.return_value = colegio

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.select_related', return_value=colegio_qs
        ):
            result = DashboardAdminService.get_admin_escolar_context(user, 'mi_escuela', 123)

        assert result['colegio'] is colegio

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_admin_escolar_context_infraestructura_delegates(self, _mock_permission):
        user = Mock(is_authenticated=True)
        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService, '_get_infraestructura_context', return_value={'infra': True}
        ) as mock_infra:
            result = DashboardAdminService.get_admin_escolar_context(user, 'infraestructura', 456)

        assert result == {'infra': True}
        mock_infra.assert_called_once_with(456)

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_admin_escolar_context_unknown_page_returns_empty(self, _mock_permission):
        user = Mock(is_authenticated=True)
        with patch.object(DashboardAdminService, '_validate_school_integrity'):
            result = DashboardAdminService.get_admin_escolar_context(user, 'otra_pagina', 123)

        assert result == {}


class TestDashboardAdminServiceLargeFlows:
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_gestionar_estudiantes_returns_error_when_setup_invalid(self, _mock_permission):
        user = Mock(is_authenticated=True)
        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(False, {'error': 'MISSING_CICLO_ACTIVO'}),
        ):
            result = DashboardAdminService.get_gestionar_estudiantes_context(user, {}, 123)

        assert result == {'error': 'MISSING_CICLO_ACTIVO'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_gestionar_cursos_returns_error_when_setup_invalid(self, _mock_permission):
        user = Mock(is_authenticated=True)
        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(False, {'error': 'SCHOOL_NOT_CONFIGURED'}),
        ):
            result = DashboardAdminService.get_gestionar_cursos_context(user, {}, 123)

        assert result == {'error': 'SCHOOL_NOT_CONFIGURED'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_gestionar_asignaturas_returns_error_when_setup_invalid(self, _mock_permission):
        user = Mock(is_authenticated=True)
        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(False, {'error': 'MISSING_CICLO_ACTIVO'}),
        ):
            result = DashboardAdminService.get_gestionar_asignaturas_context(user, {}, 123)

        assert result == {'error': 'MISSING_CICLO_ACTIVO'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_admin_notas_context_without_selected_class(self, _mock_permission):
        user = Mock(is_authenticated=True)
        clases = Mock()
        clases.exists.return_value = False
        clases.select_related.return_value = clases
        clases.order_by.return_value = clases

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=Mock()
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases):
            result = DashboardAdminService.get_admin_notas_context(user, {}, 123)

        assert result['filtro_clase_id'] == ''
        assert result['total_evaluaciones'] == 0
        assert result['promedio_general'] == 0

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_admin_libro_clases_context_without_filter(self, _mock_permission):
        user = Mock(is_authenticated=True)
        clases = Mock()
        clases.select_related.return_value = clases
        clases.order_by.return_value = clases

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=Mock()
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases):
            result = DashboardAdminService.get_admin_libro_clases_context(user, {}, 123)

        assert result['filtro_clase_id'] == ''
        assert result['total_evaluaciones'] == 0

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_gestionar_profesores_context_returns_error_when_setup_invalid(self, _mock_permission):
        user = Mock(is_authenticated=True)
        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(False, {'error': 'MISSING_CICLO_ACTIVO'}),
        ):
            result = DashboardAdminService.get_gestionar_profesores_context(user, {}, 123)

        assert result == {'error': 'MISSING_CICLO_ACTIVO'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_admin_reportes_context_without_filter(self, _mock_permission):
        user = Mock(is_authenticated=True)
        clases = Mock()
        clases.select_related.return_value = clases
        clases.order_by.return_value = clases

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=Mock()
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases):
            result = DashboardAdminService.get_admin_reportes_context(user, {}, 123)

        assert result['tipo_reporte'] == 'asistencia'
        assert result['reporte_data'] is None

    def test_get_gestionar_ciclos_context_builds_ciclos_data(self):
        user = Mock()
        colegio = Mock()
        ciclo_1 = SimpleNamespace(
            id=1,
            nombre='2026',
            fecha_inicio=None,
            fecha_fin=None,
            descripcion='Ciclo 2026',
            estado='ACTIVO',
        )

        ciclos = Mock()
        ciclos.order_by.return_value = ciclos
        ciclos.__iter__ = Mock(return_value=iter([ciclo_1]))
        ciclos.count.return_value = 1
        ciclos.filter.side_effect = [Mock(count=Mock(return_value=1)), Mock(count=Mock(return_value=0))]

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=colegio
        ), patch('backend.apps.institucion.models.CicloAcademico.objects.filter', return_value=ciclos):
            result = DashboardAdminService.get_gestionar_ciclos_context(user, {}, 123)

        assert result['total_ciclos'] == 1
        assert result['ciclos_data'][0]['nombre'] == '2026'

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_gestionar_estudiantes_full_flow(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()
        ciclo = Mock()

        estudiantes_query = Mock()
        estudiantes_query.filter.return_value = estudiantes_query
        estudiantes_query.count.return_value = 5

        user_qs = Mock()
        user_qs.select_related.return_value = user_qs
        user_qs.prefetch_related.return_value = user_qs
        user_qs.order_by.return_value = estudiantes_query

        paginator_instance = Mock()
        paginator_instance.page.return_value = ['u1', 'u2']
        paginator_instance.num_pages = 1

        cursos_qs = Mock()
        cursos_qs.select_related.return_value = cursos_qs
        cursos_qs.order_by.return_value = ['curso-a']

        perfil_activos = Mock()
        perfil_activos.count.return_value = 3
        perfil_sin = Mock()
        perfil_sin.count.return_value = 1
        perfil_con = Mock()
        perfil_con.values.return_value.distinct.return_value.count.return_value = 2

        matricula_qs = Mock()
        matricula_qs.select_related.return_value = matricula_qs

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(True, {'colegio': colegio, 'ciclo_activo': ciclo}),
        ), patch('backend.apps.core.services.dashboard_admin_service.Prefetch', return_value=Mock()), patch(
            'django.core.paginator.Paginator',
            return_value=paginator_instance,
        ), patch('backend.apps.accounts.models.User.objects.filter', return_value=user_qs), patch(
            'backend.apps.matriculas.models.Matricula.objects.filter', return_value=matricula_qs
        ), patch(
            'backend.apps.cursos.models.Curso.objects.filter', return_value=cursos_qs
        ), patch(
            'backend.apps.accounts.models.PerfilEstudiante.objects.filter',
            side_effect=[perfil_activos, perfil_sin, perfil_con],
        ):
            result = DashboardAdminService.get_gestionar_estudiantes_context(
                user,
                {'busqueda': 'ana', 'curso': '3', 'estado': 'Activo', 'page': 1},
                123,
            )

        assert result['total_estudiantes'] == 5
        assert result['estudiantes_activos'] == 3
        assert result['estudiantes_sin_curso'] == 1
        assert result['total_cursos_con_estudiantes'] == 2

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_gestionar_cursos_full_flow(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()
        ciclo = Mock()

        curso_item = Mock()
        cursos_query = Mock()
        cursos_query.select_related.return_value = cursos_query
        cursos_query.annotate.return_value = cursos_query
        cursos_query.order_by.return_value = cursos_query
        cursos_query.filter.return_value = cursos_query
        cursos_query.__iter__ = Mock(return_value=iter([curso_item]))

        curso_invalid_qs = Mock()
        curso_invalid_qs.exclude.return_value.count.return_value = 1
        total_cursos_qs = Mock()
        total_cursos_qs.count.return_value = 4
        cursos_sin_qs = Mock()
        cursos_sin_qs.exclude.return_value.distinct.return_value.count.return_value = 1
        matricula_curso_qs = Mock()
        matricula_curso_qs.count.return_value = 22

        perfil_asignados_qs = Mock()
        perfil_asignados_qs.count.return_value = 20
        clases_activas_qs = Mock()
        clases_activas_qs.count.return_value = 9

        niveles_qs = Mock()
        niveles_qs.order_by.return_value = ['nivel-a']
        estudiantes_sin_curso_qs = Mock()
        estudiantes_sin_curso_qs.select_related.return_value.order_by.return_value = ['est-a']
        asignaturas_qs = Mock()
        asignaturas_qs.order_by.return_value = ['asg-a']
        profesores_qs = Mock()
        profesores_qs.order_by.return_value = ['profe-a']

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(True, {'colegio': colegio, 'ciclo_activo': ciclo}),
        ), patch(
            'backend.apps.cursos.models.Curso.objects.filter',
            side_effect=[cursos_query, curso_invalid_qs, total_cursos_qs, cursos_sin_qs],
        ), patch('backend.apps.matriculas.models.Matricula.objects.filter', return_value=matricula_curso_qs), patch(
            'backend.apps.accounts.models.PerfilEstudiante.objects.filter', return_value=perfil_asignados_qs
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases_activas_qs), patch(
            'backend.apps.institucion.models.NivelEducativo.objects.all', return_value=niveles_qs
        ), patch(
            'backend.apps.accounts.models.User.objects.filter',
            side_effect=[estudiantes_sin_curso_qs, profesores_qs],
        ), patch('backend.apps.cursos.models.Asignatura.objects.filter', return_value=asignaturas_qs):
            result = DashboardAdminService.get_gestionar_cursos_context(user, {'nivel': '1'}, 123)

        assert result['total_cursos'] == 4
        assert result['total_estudiantes_asignados'] == 20
        assert result['total_clases_activas'] == 9
        assert result['cursos_sin_estudiantes'] == 1
        assert result['cursos_with_invalid_ciclo'] == 1

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_gestionar_asignaturas_full_flow(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()
        ciclo = Mock()

        asignatura = Mock(id_asignatura=11)
        asignaturas_query = Mock()
        asignaturas_query.annotate.return_value = asignaturas_query
        asignaturas_query.order_by.return_value = [asignatura]

        total_asig_qs = Mock()
        total_asig_qs.count.return_value = 5
        horas_qs = Mock()
        horas_qs.aggregate.return_value = {'total': 30}
        sin_asig_qs = Mock()
        sin_asig_qs.exclude.return_value.distinct.return_value.count.return_value = 2

        total_clases_qs = Mock()
        total_clases_qs.count.return_value = 8

        curso_sel = Mock()
        curso_sel.nombre = '2A'
        cursos_qs = Mock()
        cursos_qs.select_related.return_value = cursos_qs
        cursos_qs.order_by.return_value = cursos_qs
        cursos_qs.first.return_value = curso_sel

        clase_item = Mock(id=77)
        clase_item.asignatura = Mock(id_asignatura=11)
        clase_item.curso = Mock(nombre='2A')
        clase_item.profesor.get_full_name.return_value = 'Profe Asig'
        clases_activas_qs = Mock()
        clases_activas_qs.select_related.return_value = clases_activas_qs
        clases_activas_qs.order_by.return_value = [clase_item]

        profesores_qs = Mock()
        profesores_qs.order_by.return_value = ['p1']

        horario_qs = Mock()
        horario_qs.select_related.return_value = []

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(True, {'colegio': colegio, 'ciclo_activo': ciclo}),
        ), patch(
            'backend.apps.cursos.models.Asignatura.objects.filter',
            side_effect=[asignaturas_query, total_asig_qs, horas_qs, sin_asig_qs],
        ), patch('backend.apps.cursos.models.Clase.objects.filter', side_effect=[total_clases_qs, clases_activas_qs]), patch(
            'backend.apps.cursos.models.Curso.objects.filter', return_value=cursos_qs
        ), patch('backend.apps.accounts.models.User.objects.filter', return_value=profesores_qs), patch(
            'backend.apps.cursos.models.BloqueHorario.objects.filter', return_value=horario_qs
        ):
            result = DashboardAdminService.get_gestionar_asignaturas_context(user, {}, 123)

        assert result['total_asignaturas'] == 5
        assert result['total_clases_activas'] == 8
        assert result['total_horas_semanales'] == 30
        assert result['asignaturas_sin_asignar'] == 2

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_admin_notas_full_flow_with_promedio(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()
        clase = Mock(id=50)

        clases = Mock()
        clases.select_related.return_value = clases
        clases.order_by.return_value = clases
        clases.exists.return_value = True
        clases.first.return_value = clase

        eval_1 = Mock(id=1)
        eval_2 = Mock(id=2)
        evals_qs = Mock()
        evals_qs.order_by.return_value = [eval_1, eval_2]

        estudiante = Mock(id=10)
        estudiante_rel = Mock(user=estudiante)
        estudiantes_rel = Mock()
        estudiantes_rel.__iter__ = Mock(return_value=iter([estudiante_rel]))
        estudiantes_rel.select_related.return_value.distinct.return_value = [estudiante_rel]

        calif_1 = Mock(nota=5.0, evaluacion_id=1, estudiante_id=10)
        calif_2 = Mock(nota=6.0, evaluacion_id=2, estudiante_id=10)
        calificaciones_qs = Mock()
        calificaciones_qs.select_related.return_value = [calif_1, calif_2]

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=colegio
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases), patch(
            'backend.apps.cursos.models.Clase.objects.get', return_value=clase
        ), patch('backend.apps.academico.models.Evaluacion.objects.filter', return_value=evals_qs), patch(
            'backend.apps.accounts.models.PerfilEstudiante.objects.filter', return_value=estudiantes_rel
        ), patch('backend.apps.academico.models.Calificacion.objects.filter', return_value=calificaciones_qs):
            result = DashboardAdminService.get_admin_notas_context(user, {}, 123)

        assert result['total_evaluaciones'] == 2
        assert result['total_calificaciones'] == 2
        assert result['promedio_general'] == 5.5

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_admin_libro_clases_full_flow(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()
        clase = Mock(id=10)

        clases = Mock()
        clases.select_related.return_value = clases
        clases.order_by.return_value = clases
        clases.filter.return_value.first.return_value = clase

        gradebook = {
            'evaluaciones': ['e'],
            'matriz_calificaciones': ['m'],
            'promedios_evaluaciones': [6.0],
            'total_evaluaciones': 1,
            'total_estudiantes': 2,
            'promedio_general': 6.0,
        }

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=colegio
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases), patch(
            'backend.apps.academico.services.grades_service.GradesService.build_gradebook_matrix',
            return_value=gradebook,
        ):
            result = DashboardAdminService.get_admin_libro_clases_context(user, {'clase_id': '10'}, 123)

        assert result['total_evaluaciones'] == 1
        assert result['total_estudiantes'] == 2
        assert result['promedio_general'] == 6.0

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_gestionar_profesores_full_flow(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()

        profesores_query = Mock()
        profesores_query.filter.return_value = profesores_query
        profesores_query.count.return_value = 7

        user_qs = Mock()
        user_qs.select_related.return_value = user_qs
        user_qs.prefetch_related.return_value = user_qs
        user_qs.annotate.return_value = user_qs
        user_qs.order_by.return_value = profesores_query

        paginator = Mock()
        paginator.page.return_value = ['p1']
        paginator.num_pages = 1

        perfil_prof_qs = Mock()
        perfil_prof_qs.count.return_value = 4
        clase_qs = Mock()
        clase_qs.count.return_value = 10
        horas_qs = Mock()
        horas_qs.aggregate.return_value = {'total': 25}
        asignaturas_qs = Mock()
        asignaturas_qs.order_by.return_value = ['asg1']

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch.object(
            DashboardAdminService,
            '_validate_colegio_setup',
            return_value=(True, {'colegio': colegio}),
        ), patch('backend.apps.accounts.models.User.objects.filter', return_value=user_qs), patch(
            'django.core.paginator.Paginator', return_value=paginator
        ), patch('backend.apps.accounts.models.PerfilProfesor.objects.filter', return_value=perfil_prof_qs), patch(
            'backend.apps.cursos.models.Clase.objects.filter', return_value=clase_qs
        ), patch(
            'backend.apps.cursos.models.Asignatura.objects.filter',
            side_effect=[horas_qs, asignaturas_qs],
        ):
            result = DashboardAdminService.get_gestionar_profesores_context(
                user,
                {'buscar': 'pro', 'estado': 'Activo', 'asignatura': '1'},
                123,
            )

        assert result['total_profesores'] == 7
        assert result['profesores_activos'] == 4
        assert result['total_clases'] == 10
        assert result['total_horas'] == 25

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_admin_reportes_full_flow(self, _mock_permission):
        user = Mock(is_authenticated=True)
        colegio = Mock()
        clase = Mock(id=10)
        clases = Mock()
        clases.select_related.return_value = clases
        clases.order_by.return_value = clases
        clases.filter.return_value.first.return_value = clase

        with patch.object(DashboardAdminService, '_validate_school_integrity'), patch(
            'backend.apps.institucion.models.Colegio.objects.get', return_value=colegio
        ), patch('backend.apps.cursos.models.Clase.objects.filter', return_value=clases), patch(
            'backend.apps.academico.services.academic_reports_service.AcademicReportsService.parse_report_filters',
            return_value=('fi', 'ff'),
        ), patch(
            'backend.apps.academico.services.academic_reports_service.AcademicReportsService.generate_report_data',
            return_value={'report': 1},
        ):
            result = DashboardAdminService.get_admin_reportes_context(
                user,
                {'clase_id': '10', 'tipo': 'asistencia'},
                123,
            )

        assert result['clase_seleccionada'] is clase
        assert result['reporte_data'] == {'report': 1}

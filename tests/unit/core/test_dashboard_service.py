"""Tests unitarios para DashboardService alineados a contratos vigentes."""

from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.dashboard_service import DashboardService


pytestmark = pytest.mark.django_db


class TestDashboardServiceUserContext:
    @patch('backend.apps.core.services.dashboard_auth_service.IntegrityService.validate_school_integrity_or_raise', return_value=None)
    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol')
    def test_get_user_context_with_valid_school_assigned(self, mock_normalizar, _mock_integrity):
        mock_normalizar.return_value = 'admin_escolar'

        mock_user = Mock()
        mock_user.role = Mock(nombre='Administrador Escolar')
        mock_user.get_full_name.return_value = 'Juan Pérez'
        mock_user.id = 123
        mock_user.rbd_colegio = 12345
        mock_user.colegio = Mock(nombre='Colegio Test')

        result = DashboardService.get_user_context(mock_user, {})

        assert result is not None
        assert result['data']['rol'] == 'admin_escolar'
        assert result['data']['escuela_rbd'] == 12345

    @patch('backend.apps.core.services.dashboard_auth_service.IntegrityService.validate_school_integrity_or_raise', return_value=None)
    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol')
    def test_get_user_context_admin_with_session_rbd(self, mock_normalizar, _mock_integrity):
        mock_normalizar.return_value = 'admin'

        mock_user = Mock()
        mock_user.role = Mock(nombre='Administrador General')
        mock_user.get_full_name.return_value = 'Admin User'
        mock_user.id = 1
        mock_user.rbd_colegio = None
        mock_user.colegio = None

        result = DashboardService.get_user_context(
            mock_user,
            {'admin_rbd_activo': 99999, 'admin_colegio_nombre': 'Colegio desde Sesión'},
        )

        assert result is not None
        assert result['data']['escuela_rbd'] == 99999


class TestDashboardServiceDelegation:
    @patch('backend.apps.core.services.dashboard_context_service.DashboardContextService._get_estudiante_inicio_context', return_value={'ok': True})
    @patch('backend.apps.core.services.dashboard_service.IntegrityService.validate_school_integrity_or_raise', return_value=None)
    def test_get_estudiante_context_inicio(self, _mock_integrity, mock_inicio):
        user = Mock(id=100)

        result = DashboardService.get_estudiante_context(user, 'inicio', 12345)

        assert result == {'ok': True}
        mock_inicio.assert_called_once_with(user, 12345)

    @patch('backend.apps.core.services.dashboard_context_service.DashboardContextService._get_estudiante_perfil_context', return_value={'estadisticas': {'total_calificaciones': 0}})
    @patch('backend.apps.core.services.dashboard_service.IntegrityService.validate_school_integrity_or_raise', return_value=None)
    def test_get_estudiante_context_perfil(self, _mock_integrity, mock_perfil):
        user = Mock(id=100)

        result = DashboardService.get_estudiante_context(user, 'perfil', 12345)

        assert 'estadisticas' in result
        mock_perfil.assert_called_once_with(user, 12345)

    @patch('backend.apps.core.services.dashboard_apoderado_service.DashboardApoderadoService.get_apoderado_context', return_value={'total_pupilos': 2})
    def test_get_apoderado_context(self, mock_apoderado):
        user = Mock(id=200)

        result = DashboardService.get_apoderado_context(user, 'inicio')

        assert result['total_pupilos'] == 2
        mock_apoderado.assert_called_once_with(user, 'inicio', None)


class TestDashboardServiceBasics:
    def test_get_sidebar_unknown_role(self):
        assert DashboardService.get_sidebar_template('desconocido') == 'sidebars/sidebar_default.html'

    @patch('backend.common.utils.permissions.get_paginas_por_rol', return_value={'inicio': 'compartido/inicio_modulos.html'})
    def test_validate_page_access_invalid(self, _mock_paginas):
        is_valid, template = DashboardService.validate_page_access('estudiante', 'admin_only')
        assert is_valid is False
        assert template == 'compartido/acceso_denegado.html'

    @patch('backend.apps.core.services.dashboard_auth_service.DashboardAuthService.validate_page_access', return_value=(True, 'x.html'))
    def test_validate_page_access_delegates_with_user_and_school(self, mock_validate):
        user = Mock()
        result = DashboardService.validate_page_access('profesor', 'inicio', user=user, school_id=123)

        assert result == (True, 'x.html')
        mock_validate.assert_called_once_with('profesor', 'inicio', user=user, school_id=123)

    def test_validate_requires_operation_string(self):
        with pytest.raises(ValueError, match='operation'):
            DashboardService.validate('', {})

    def test_validate_requires_dict_params(self):
        with pytest.raises(ValueError, match='params debe ser dict'):
            DashboardService.validate('algo', [])

    def test_execute_calls_validate_and_dispatch(self):
        with patch.object(DashboardService, 'validate') as mock_validate, patch.object(
            DashboardService,
            '_execute',
            return_value={'ok': True},
        ) as mock_execute:
            result = DashboardService.execute('op', {'x': 1})

        assert result == {'ok': True}
        mock_validate.assert_called_once_with('op', {'x': 1})
        mock_execute.assert_called_once_with('op', {'x': 1})

    def test_execute_defaults_params_to_dict(self):
        with patch.object(DashboardService, 'validate') as mock_validate, patch.object(
            DashboardService,
            '_execute',
            return_value='ok',
        ):
            result = DashboardService.execute('op')

        assert result == 'ok'
        mock_validate.assert_called_once_with('op', {})

    def test_internal_execute_unsupported_operation(self):
        with pytest.raises(ValueError, match='Operación no soportada'):
            DashboardService._execute('op_nope', {})

    def test_internal_execute_supported_operation(self):
        with patch.object(DashboardService, '_execute_demo', return_value=123, create=True):
            result = DashboardService._execute('demo', {'k': 1})
        assert result == 123

    def test_validate_school_integrity_skips_when_missing(self):
        with patch('backend.apps.core.services.dashboard_service.IntegrityService.validate_school_integrity_or_raise') as mock_integrity:
            DashboardService._validate_school_integrity(None, 'ACCION')
        mock_integrity.assert_not_called()

    def test_validate_school_integrity_calls_when_present(self):
        with patch('backend.apps.core.services.dashboard_service.IntegrityService.validate_school_integrity_or_raise') as mock_integrity:
            DashboardService._validate_school_integrity(123, 'ACCION')
        mock_integrity.assert_called_once_with(school_id=123, action='ACCION')


class TestDashboardServiceDelegatedMethods:
    def test_get_asistencia_context_delegates(self):
        request = Mock(GET={'fecha': '2026-01-01'}, user=Mock())
        colegio = Mock(rbd=123)
        with patch.object(DashboardService, '_validate_school_integrity') as mock_integrity, patch(
            'backend.apps.core.services.dashboard_context_service.DashboardContextService.get_asistencia_context',
            return_value={'ok': 1},
        ) as mock_ctx:
            result = DashboardService.get_asistencia_context(request, colegio)
        assert result == {'ok': 1}
        mock_integrity.assert_called_once_with(123, 'DASHBOARD_GET_ASISTENCIA_CONTEXT')
        mock_ctx.assert_called_once_with(request.GET, colegio, request.user)

    def test_get_profesor_context_delegates(self):
        request = Mock(GET={'pagina': 'x'})
        user = Mock()
        with patch.object(DashboardService, '_validate_school_integrity') as mock_integrity, patch(
            'backend.apps.core.services.dashboard_context_service.DashboardContextService.get_profesor_context',
            return_value={'ok': True},
        ) as mock_ctx:
            result = DashboardService.get_profesor_context(request, user, 'inicio', 555)
        assert result == {'ok': True}
        mock_integrity.assert_called_once_with(555, 'DASHBOARD_GET_PROFESOR_CONTEXT')
        mock_ctx.assert_called_once_with(request.GET, user, 'inicio', 555)

    @pytest.mark.parametrize(
        'method_name,service_target,action,fail_on_integrity',
        [
            ('get_gestionar_estudiantes_context', 'get_gestionar_estudiantes_context', 'DASHBOARD_GET_GESTIONAR_ESTUDIANTES_CONTEXT', False),
            ('get_gestionar_cursos_context', 'get_gestionar_cursos_context', 'DASHBOARD_GET_GESTIONAR_CURSOS_CONTEXT', False),
            ('get_gestionar_profesores_context', 'get_gestionar_profesores_context', 'DASHBOARD_GET_GESTIONAR_PROFESORES_CONTEXT', False),
            ('get_gestionar_asignaturas_context', 'get_gestionar_asignaturas_context', 'DASHBOARD_GET_GESTIONAR_ASIGNATURAS_CONTEXT', False),
            ('get_admin_notas_context', 'get_admin_notas_context', 'DASHBOARD_GET_ADMIN_NOTAS_CONTEXT', True),
            ('get_admin_libro_clases_context', 'get_admin_libro_clases_context', 'DASHBOARD_GET_ADMIN_LIBRO_CLASES_CONTEXT', True),
            ('get_admin_reportes_context', 'get_admin_reportes_context', 'DASHBOARD_GET_ADMIN_REPORTES_CONTEXT', True),
        ],
    )
    def test_admin_request_delegates(self, method_name, service_target, action, fail_on_integrity):
        user = Mock()
        request = Mock(GET={'q': '1'})
        with patch.object(DashboardService, '_validate_school_integrity') as mock_integrity, patch(
            f'backend.apps.core.services.dashboard_admin_service.DashboardAdminService.{service_target}',
            return_value={'ok': method_name},
        ) as mock_admin:
            result = getattr(DashboardService, method_name)(user, request, 999)

        assert result == {'ok': method_name}
        if not fail_on_integrity:
            mock_integrity.assert_called_once_with(999, action, fail_on_integrity=False)
            mock_admin.assert_called_once_with(user, request.GET, 999, fail_on_integrity=False)
        else:
            mock_integrity.assert_called_once_with(999, action)
            mock_admin.assert_called_once_with(user, request.GET, 999)

    def test_get_gestionar_ciclos_context_delegates(self):
        user = Mock()
        request_get_params = {'p': '1'}
        with patch.object(DashboardService, '_validate_school_integrity') as mock_integrity, patch(
            'backend.apps.core.services.dashboard_admin_service.DashboardAdminService.get_gestionar_ciclos_context',
            return_value={'ok': 'ciclos'},
        ) as mock_admin:
            result = DashboardService.get_gestionar_ciclos_context(user, request_get_params, 999)
        assert result == {'ok': 'ciclos'}
        mock_integrity.assert_called_once_with(999, 'DASHBOARD_GET_GESTIONAR_CICLOS_CONTEXT', fail_on_integrity=False)
        mock_admin.assert_called_once_with(user, request_get_params, 999)


class TestDashboardServiceAdminGeneralContext:
    def test_admin_general_context_escuelas(self):
        escuelas_qs = Mock()
        escuelas_qs.order_by.return_value = ['c1']
        with patch('backend.apps.institucion.models.Colegio.objects.all', return_value=escuelas_qs):
            result = DashboardService.get_admin_general_context(Mock(), 'escuelas')
        assert result['escuelas'] == ['c1']

    def test_admin_general_context_usuarios(self):
        usuarios_qs = Mock()
        usuarios_qs.select_related.return_value.order_by.return_value = ['u1']
        with patch('backend.apps.accounts.models.User.objects.all', return_value=usuarios_qs):
            result = DashboardService.get_admin_general_context(Mock(), 'usuarios')
        assert result['usuarios'] == ['u1']

    def test_admin_general_context_planes(self):
        with patch('backend.apps.subscriptions.models.Plan.objects.all', return_value=['p1']), patch(
            'backend.apps.subscriptions.models.Subscription.objects.all'
        ) as mock_subs_all:
            mock_subs_all.return_value.select_related.return_value = ['s1']
            result = DashboardService.get_admin_general_context(Mock(), 'planes')
        assert result['planes'] == ['p1']
        assert result['suscripciones'] == ['s1']

    def test_admin_general_context_estadisticas_globales(self):
        usuarios_values = Mock()
        usuarios_values.annotate.return_value = [{'role__nombre': 'Alumno', 'count': 5}]
        with patch('backend.apps.institucion.models.Colegio.objects.count', return_value=3), patch(
            'backend.apps.accounts.models.User.objects.count',
            return_value=20,
        ), patch('backend.apps.accounts.models.User.objects.values', return_value=usuarios_values):
            result = DashboardService.get_admin_general_context(Mock(), 'estadisticas_globales')
        assert result['total_escuelas'] == 3
        assert result['total_usuarios'] == 20
        assert result['usuarios_por_rol'][0]['count'] == 5

    def test_admin_general_context_reportes_financieros(self):
        subs_qs = Mock()
        subs_qs.aggregate.return_value = {'total': 1200}
        with patch('backend.apps.subscriptions.models.Subscription.objects.filter', return_value=subs_qs):
            result = DashboardService.get_admin_general_context(Mock(), 'reportes_financieros')
        assert result['ingresos_totales'] == 1200

    def test_admin_general_context_configuracion_with_auditoria(self):
        mock_settings = Mock(DEBUG=True, ALLOWED_HOSTS=['*'], DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}})
        with patch('backend.apps.institucion.models.Colegio.objects.count', return_value=2), patch(
            'backend.apps.accounts.models.User.objects.count', return_value=10
        ), patch('backend.apps.accounts.models.Role.objects.count', return_value=4), patch(
            'backend.apps.subscriptions.models.Plan.objects.count', return_value=3
        ), patch('django.conf.settings', mock_settings), patch(
            'backend.apps.auditoria.models.ConfiguracionAuditoria.get_config', return_value='cfg'
        ):
            result = DashboardService.get_admin_general_context(Mock(), 'configuracion')
        assert result['total_colegios'] == 2
        assert result['config_auditoria'] == 'cfg'

    def test_admin_general_context_configuracion_without_auditoria(self):
        mock_settings = Mock(DEBUG=False, ALLOWED_HOSTS=['localhost'], DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}})
        with patch('backend.apps.institucion.models.Colegio.objects.count', return_value=1), patch(
            'backend.apps.accounts.models.User.objects.count', return_value=1
        ), patch('backend.apps.accounts.models.Role.objects.count', return_value=1), patch(
            'backend.apps.subscriptions.models.Plan.objects.count', return_value=1
        ), patch('django.conf.settings', mock_settings), patch(
            'backend.apps.auditoria.models.ConfiguracionAuditoria.get_config', side_effect=Exception('x')
        ):
            result = DashboardService.get_admin_general_context(Mock(), 'configuracion')
        assert result['config_auditoria'] is None

    def test_admin_general_context_auditoria(self):
        logs_qs = Mock()
        logs_qs.order_by.return_value = ['l1']
        with patch('backend.apps.auditoria.models.AuditoriaEvento.objects.all', return_value=logs_qs):
            result = DashboardService.get_admin_general_context(Mock(), 'auditoria')
        assert result['logs_auditoria'] == ['l1']

    def test_admin_general_context_monitoreo_seguridad_noop(self):
        result = DashboardService.get_admin_general_context(Mock(), 'monitoreo_seguridad')
        assert result == {}

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.dashboard_orchestrator_service import DashboardOrchestratorService


pytestmark = pytest.mark.django_db


class TestDashboardOrchestratorService:
    def test_handle_dashboard_admin_general_escuelas_redirects_to_special_view(self):
        request = SimpleNamespace(user=SimpleNamespace(rbd_colegio=1), session={}, GET={'pagina': 'escuelas'}, method='GET')
        user_context = {'data': {'rol': 'admin_general', 'escuela_rbd': None}}
        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.views.admin_general.escuelas.gestionar_escuelas', return_value='special'
        ) as mock_view:
            result = DashboardOrchestratorService.handle_dashboard(request)
        assert result == 'special'
        mock_view.assert_called_once_with(request)

    def test_handle_dashboard_post_asistencia_profesor_delegates_view(self):
        user = SimpleNamespace(rbd_colegio=123)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'asistencia'}, method='POST')
        user_context = {'data': {'rol': 'profesor', 'escuela_rbd': 123}}
        colegio = Mock(rbd=123)
        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.SchoolQueryService.get_required_by_rbd',
            return_value=colegio,
        ) as mock_school, patch(
            'backend.apps.core.views.profesor.asistencia.gestionar_asistencia',
            return_value='asistencia-post',
        ) as mock_asistencia:
            result = DashboardOrchestratorService.handle_dashboard(request)
        assert result == 'asistencia-post'
        mock_school.assert_called_once_with(123)
        mock_asistencia.assert_called_once_with(request, colegio)

    def test_handle_dashboard_redirects_when_no_school(self):
        request = SimpleNamespace(user=SimpleNamespace(rbd_colegio=None), session={}, GET={}, method='GET')
        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=None), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.redirect', return_value='redir'
        ) as mock_redirect:
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'redir'
        mock_redirect.assert_called_once_with('seleccionar_escuela')

    def test_handle_dashboard_redirects_login_when_session_invalid(self):
        request = SimpleNamespace(user=SimpleNamespace(rbd_colegio=123), session={}, GET={}, method='GET')
        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=None), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.messages.error'
        ) as mock_msg, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.redirect',
            return_value='redir-login',
        ) as mock_redirect:
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'redir-login'
        mock_msg.assert_called_once()
        mock_redirect.assert_called_once_with('accounts:login')

    def test_handle_dashboard_post_disponibilidad_success(self):
        user = SimpleNamespace(rbd_colegio=123)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'disponibilidad'}, method='POST', POST={'a': '1'})
        user_context = {'data': {'rol': 'profesor', 'escuela_rbd': 123}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.TeacherAvailabilityService.save_weekly_availability'
        ) as mock_save, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.messages.success'
        ) as mock_success, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.redirect', return_value='redir-disp'
        ) as mock_redirect:
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'redir-disp'
        mock_save.assert_called_once()
        mock_success.assert_called_once()
        mock_redirect.assert_called_once_with('/dashboard/?pagina=disponibilidad')

    def test_handle_dashboard_post_disponibilidad_with_error_message(self):
        user = SimpleNamespace(rbd_colegio=123)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'disponibilidad'}, method='POST', POST={'a': '1'})
        user_context = {'data': {'rol': 'profesor', 'escuela_rbd': 123}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.TeacherAvailabilityService.save_weekly_availability',
            side_effect=ValueError('bad data'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.messages.error'
        ) as mock_error, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.redirect', return_value='redir-disp'
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'redir-disp'
        mock_error.assert_called_once()

    def test_handle_dashboard_invalid_page_falls_back_to_inicio(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'prohibida'}, method='GET')
        user_context = {'data': {'rol': 'profesor', 'escuela_rbd': 123, 'nombre_usuario': 'X'}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(False, 'compartido/acceso_denegado.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.messages.error'
        ) as mock_error, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_profesor.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_profesor_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-invalid',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-invalid'
        mock_error.assert_called_once()

    def test_handle_dashboard_profesor_get_renders(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'inicio'}, method='GET')
        user_context = {'data': {'rol': 'profesor', 'escuela_rbd': 123, 'nombre_usuario': 'X'}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_navigation_access',
            return_value={'paginas_habilitadas': ['inicio'], 'menu_access': {'comunicados': True}},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_profesor.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={'notificaciones_count': 1},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_profesor_context',
            return_value={'mis_clases': []},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='rendered',
        ) as mock_render:
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'rendered'
        mock_render.assert_called_once()
        render_context = mock_render.call_args[0][2]
        assert 'paginas_habilitadas' in render_context
        assert 'menu_access' in render_context

    def test_handle_dashboard_profesor_asistencia_get_merges_context(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'asistencia'}, method='GET')
        user_context = {'data': {'rol': 'profesor', 'escuela_rbd': 123, 'nombre_usuario': 'X'}}
        colegio = Mock(rbd=123)

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_profesor.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_profesor_context',
            return_value={'k': 1},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.SchoolQueryService.get_required_by_rbd',
            return_value=colegio,
        ), patch(
            'backend.apps.core.views.profesor.asistencia.gestionar_asistencia',
            return_value={'asistencia': True},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-prof-asis',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-prof-asis'

    def test_handle_dashboard_estudiante_branch(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'inicio'}, method='GET')
        user_context = {'data': {'rol': 'estudiante', 'escuela_rbd': 123, 'nombre_usuario': 'E'}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_estudiante.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_estudiante_context',
            return_value={'clases_hoy': 2},
        ) as mock_role, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-est',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-est'
        mock_role.assert_called_once()

    def test_handle_dashboard_apoderado_branch(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'inicio', 'estudiante_id': '99'}, method='GET')
        user_context = {'data': {'rol': 'apoderado', 'escuela_rbd': 123, 'nombre_usuario': 'A'}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_apoderado.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_apoderado_context',
            return_value={'total_pupilos': 1},
        ) as mock_role, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-apo',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-apo'
        mock_role.assert_called_once_with(user, 'inicio', '99')

    def test_handle_dashboard_asesor_branch(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'inicio'}, method='GET')
        user_context = {'data': {'rol': 'asesor_financiero', 'escuela_rbd': 123, 'nombre_usuario': 'F'}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_asesor_financiero.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_asesor_financiero_context',
            return_value={'kpis': {}},
        ) as mock_role, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-asesor',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-asesor'
        mock_role.assert_called_once_with(user, 'inicio', 123)

    def test_handle_dashboard_admin_setup_and_default_context(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'otra'}, method='GET')
        user_context = {'data': {'rol': 'admin_escolar', 'escuela_rbd': 123, 'nombre_usuario': 'Admin'}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_admin_escuela.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_status',
            return_value={'setup_complete': False},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_progress_percentage',
            return_value=40,
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingNotificationService.notify_if_needed'
        ) as mock_notify, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_admin_escolar_context',
            return_value={'colegio': 'x'},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='rendered-admin',
        ) as mock_render:
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'rendered-admin'
        mock_notify.assert_called_once()
        mock_render.assert_called_once()

    def test_handle_dashboard_admin_specific_pages(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        pages_and_targets = [
            ('gestionar_estudiantes', 'get_gestionar_estudiantes_context'),
            ('gestionar_cursos', 'get_gestionar_cursos_context'),
            ('gestionar_asignaturas', 'get_gestionar_asignaturas_context'),
            ('gestionar_profesores', 'get_gestionar_profesores_context'),
            ('notas', 'get_admin_notas_context'),
            ('libro_clases', 'get_admin_libro_clases_context'),
            ('reportes', 'get_admin_reportes_context'),
        ]

        for page, target in pages_and_targets:
            request = SimpleNamespace(user=user, session={}, GET={'pagina': page}, method='GET')
            user_context = {'data': {'rol': 'admin_escolar', 'escuela_rbd': 123, 'nombre_usuario': 'Admin'}}
            with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
                'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
                return_value=(True, 'compartido/inicio_modulos.html'),
            ), patch(
                'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
                return_value='sidebars/sidebar_admin_escuela.html',
            ), patch(
                'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
                return_value={},
            ), patch(
                'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_status',
                return_value={'setup_complete': True},
            ), patch(
                'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_progress_percentage',
                return_value=100,
            ), patch(
                f'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.{target}',
                return_value={page: True},
            ) as mock_target, patch(
                'backend.apps.core.services.dashboard_orchestrator_service.render',
                return_value=f'render-{page}',
            ):
                result = DashboardOrchestratorService.handle_dashboard(request)

            assert result == f'render-{page}'
            mock_target.assert_called_once()

    def test_handle_dashboard_admin_gestionar_ciclos_branch(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'gestionar_ciclos'}, method='GET')
        user_context = {'data': {'rol': 'admin_escolar', 'escuela_rbd': 123, 'nombre_usuario': 'Admin'}}
        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_admin_escuela.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_status',
            return_value={'setup_complete': True},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_progress_percentage',
            return_value=100,
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_gestionar_ciclos_context',
            return_value={'ciclos': []},
        ) as mock_target, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-ciclos',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-ciclos'
        mock_target.assert_called_once_with(user, request.GET, 123)

    def test_handle_dashboard_admin_asistencia_branch(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'asistencia'}, method='GET')
        user_context = {'data': {'rol': 'admin_escolar', 'escuela_rbd': 123, 'nombre_usuario': 'Admin'}}
        colegio = Mock(rbd=123)
        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_admin_escuela.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_status',
            return_value={'setup_complete': True},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_progress_percentage',
            return_value=100,
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.SchoolQueryService.get_required_by_rbd',
            return_value=colegio,
        ), patch(
            'backend.apps.core.views.profesor.asistencia.gestionar_asistencia',
            return_value={'asistencia': True},
        ) as mock_asis, patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-admin-asistencia',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-admin-asistencia'
        mock_asis.assert_called_once_with(request, colegio, admin_mode=True)

    def test_handle_dashboard_admin_prerequisite_exception_ignored_when_setup_incomplete(self):
        user = SimpleNamespace(rbd_colegio=123, is_authenticated=True)
        request = SimpleNamespace(user=user, session={}, GET={'pagina': 'gestionar_estudiantes'}, method='GET')
        user_context = {'data': {'rol': 'admin_escolar', 'escuela_rbd': 123, 'nombre_usuario': 'Admin'}}

        with patch('backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_user_context', return_value=user_context), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.validate_page_access',
            return_value=(True, 'compartido/inicio_modulos.html'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_sidebar_template',
            return_value='sidebars/sidebar_admin_escuela.html',
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardContextService.get_notificaciones_context',
            return_value={},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_status',
            return_value={'setup_complete': False},
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingService.get_setup_progress_percentage',
            return_value=40,
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.OnboardingNotificationService.notify_if_needed',
            return_value=None,
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.PrerequisiteException',
            Exception,
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.DashboardService.get_gestionar_estudiantes_context',
            side_effect=Exception('dep'),
        ), patch(
            'backend.apps.core.services.dashboard_orchestrator_service.render',
            return_value='render-prereq-ignore',
        ):
            result = DashboardOrchestratorService.handle_dashboard(request)

        assert result == 'render-prereq-ignore'

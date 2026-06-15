"""DashboardAuthService unit tests aligned to current contracts."""

from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.dashboard_auth_service import DashboardAuthService
from backend.common.utils.permissions import get_paginas_por_rol


pytestmark = pytest.mark.django_db


ROLE_DISPLAY_NAMES = {
    'admin': 'Administrador',
    'admin_general': 'Administrador general',
    'admin_escolar': 'Administrador escolar',
    'profesor': 'Profesor',
    'estudiante': 'Estudiante',
    'apoderado': 'Apoderado',
    'asesor_financiero': 'Asesor financiero',
    'coordinador_academico': 'Coordinador academico',
    'inspector_convivencia': 'Inspector convivencia',
    'psicologo_orientador': 'Psicologo orientador',
    'soporte_tecnico_escolar': 'Soporte tecnico escolar',
    'bibliotecario_digital': 'Bibliotecario digital',
}


def _user_for_role(role):
    user = Mock(is_authenticated=True, is_active=True)
    user.role = Mock(nombre=ROLE_DISPLAY_NAMES.get(role, role))
    user.rbd_colegio = 12345
    return user


class TestDashboardAuthService:
    @patch('backend.apps.core.services.dashboard_auth_service.IntegrityService.validate_school_integrity_or_raise', return_value=None)
    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol', return_value='estudiante')
    def test_get_user_context_valid_student(self, _mock_normalizar, _mock_integrity):
        user = Mock()
        user.id = 1
        user.role = Mock(nombre='Alumno')
        user.get_full_name.return_value = 'Juan Pérez'
        user.rbd_colegio = 12345
        user.colegio = Mock(nombre='Escuela Test')
        user.email = 'juan@test.cl'

        result = DashboardAuthService.get_user_context(user, {})

        assert result is not None
        assert result['success'] is True
        assert result['data']['rol'] == 'estudiante'
        assert result['data']['id_usuario'] == 1
        assert result['data']['escuela_rbd'] == 12345

    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol', return_value='estudiante')
    def test_get_user_context_no_school_assigned(self, _mock_normalizar):
        user = Mock()
        user.role = Mock(nombre='Alumno')
        user.rbd_colegio = None

        result = DashboardAuthService.get_user_context(user, {})

        assert result is None

    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol', return_value='admin')
    def test_get_user_context_admin_without_session_rbd(self, _mock_normalizar):
        user = Mock()
        user.role = Mock(nombre='Administrador general')
        user.rbd_colegio = None
        user.colegio = None

        result = DashboardAuthService.get_user_context(user, {})

        assert result is None

    @patch('backend.apps.core.services.dashboard_auth_service.PolicyService.has_capability', return_value=True)
    def test_validate_page_access_capability_first_allows_new_role_inicio(self, mock_has_capability):
        user = Mock(is_authenticated=True, is_active=True)

        is_valid, template = DashboardAuthService.validate_page_access(
            'coordinador',
            'inicio',
            user=user,
            school_id=12345,
        )

        assert is_valid is True
        assert template == 'compartido/inicio_modulos.html'
        mock_has_capability.assert_called()

    @patch('backend.apps.core.services.dashboard_auth_service.PolicyService.has_capability', return_value=False)
    def test_validate_page_access_capability_first_denies_without_capability(self, mock_has_capability):
        user = Mock(is_authenticated=True, is_active=True)

        is_valid, template = DashboardAuthService.validate_page_access(
            'profesor',
            'reportes',
            user=user,
            school_id=12345,
        )

        assert is_valid is False
        assert template == 'compartido/acceso_denegado.html'
        mock_has_capability.assert_called()

    @patch('backend.apps.core.services.dashboard_auth_service.PolicyService.has_capability')
    def test_get_navigation_access_filters_pages_by_capability(self, mock_has_capability):
        def _has_capability(_user, capability, school_id=None):
            return capability in {'DASHBOARD_VIEW_SELF', 'CLASS_VIEW'}

        mock_has_capability.side_effect = _has_capability
        user = Mock(is_authenticated=True, is_active=True)

        result = DashboardAuthService.get_navigation_access('estudiante', user=user, school_id=12345)

        assert 'inicio' in result['paginas_habilitadas']
        assert 'mis_clases' in result['paginas_habilitadas']
        assert 'mis_notas' not in result['paginas_habilitadas']

    @patch('backend.apps.core.services.dashboard_auth_service.PolicyService.has_capability', return_value=True)
    def test_get_navigation_access_fallback_no_user_uses_role_pages(self, _mock_has_capability):
        result = DashboardAuthService.get_navigation_access('profesor', user=None, school_id=12345)

        assert 'inicio' in result['paginas_habilitadas']
        assert 'mis_clases' in result['paginas_habilitadas']

    @patch('backend.apps.core.services.dashboard_auth_service.PolicyService.has_capability')
    def test_validate_page_access_uses_role_specific_capabilities_for_justificativos(self, mock_has_capability):
        def _has_capability(_user, capability, school_id=None):
            return capability == 'STUDENT_VIEW'

        mock_has_capability.side_effect = _has_capability
        user = Mock(is_authenticated=True, is_active=True)

        is_valid, template = DashboardAuthService.validate_page_access(
            'apoderado',
            'justificativos',
            user=user,
            school_id=12345,
        )

        assert is_valid is True
        assert template == 'apoderado/justificativos.html'
        assert all(
            call_args.args[1] != 'JUSTIFICATION_APPROVE'
            for call_args in mock_has_capability.call_args_list
        )

    @patch('backend.apps.core.services.dashboard_auth_service.PolicyService.has_capability')
    def test_navigation_uses_inspector_capabilities_for_justificativos(self, mock_has_capability):
        def _has_capability(_user, capability, school_id=None):
            return capability in {'DASHBOARD_VIEW_SCHOOL', 'JUSTIFICATION_VIEW'}

        mock_has_capability.side_effect = _has_capability
        user = Mock(is_authenticated=True, is_active=True)

        result = DashboardAuthService.get_navigation_access('inspector_convivencia', user=user, school_id=12345)

        assert 'inicio' in result['paginas_habilitadas']
        assert 'justificativos' in result['paginas_habilitadas']

    def test_all_django_pages_declared_for_a_role_are_accessible_with_default_capabilities(self):
        roles = [
            'admin',
            'admin_general',
            'admin_escolar',
            'profesor',
            'estudiante',
            'apoderado',
            'asesor_financiero',
            'coordinador_academico',
            'inspector_convivencia',
            'psicologo_orientador',
            'soporte_tecnico_escolar',
            'bibliotecario_digital',
        ]

        for role in roles:
            user = _user_for_role(role)
            for page, expected_template in get_paginas_por_rol(role).items():
                is_valid, template = DashboardAuthService.validate_page_access(
                    role,
                    page,
                    user=user,
                    school_id=12345,
                )

                assert is_valid is True, f'{role} should access {page}'
                assert template == expected_template

    def test_django_page_access_denies_pages_from_other_roles_even_when_capability_matches(self):
        denied_cases = [
            ('profesor', 'mis_notas'),
            ('estudiante', 'notas'),
            ('apoderado', 'anotaciones'),
            ('inspector_convivencia', 'mis_pupilos'),
        ]

        for role, page in denied_cases:
            is_valid, template = DashboardAuthService.validate_page_access(
                role,
                page,
                user=_user_for_role(role),
                school_id=12345,
            )

            assert is_valid is False, f'{role} should not access {page}'
            assert template == 'compartido/acceso_denegado.html'

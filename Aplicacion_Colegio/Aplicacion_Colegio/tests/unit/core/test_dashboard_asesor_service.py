from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.dashboard_asesor_service import DashboardAsesorService


pytestmark = pytest.mark.django_db


class TestDashboardAsesorService:
    def test_validate_rejects_missing_params(self):
        with pytest.raises(ValueError, match='user'):
            DashboardAsesorService.validate('get_asesor_financiero_context', {'pagina_solicitada': 'perfil', 'escuela_rbd': 1})

        with pytest.raises(ValueError, match='pagina_solicitada'):
            DashboardAsesorService.validate('get_asesor_financiero_context', {'user': Mock(), 'escuela_rbd': 1})

        with pytest.raises(ValueError, match='escuela_rbd'):
            DashboardAsesorService.validate('get_asesor_financiero_context', {'user': Mock(), 'pagina_solicitada': 'perfil'})

    def test_validate_rejects_unsupported_operation(self):
        with pytest.raises(ValueError, match='Operación no soportada'):
            DashboardAsesorService.validate('op_x', {})

    def test_execute_routes_operation(self):
        with patch.object(DashboardAsesorService, 'validate'), patch.object(
            DashboardAsesorService, '_execute', return_value={'ok': True}
        ) as mock_execute:
            result = DashboardAsesorService.execute('get_asesor_financiero_context', {'user': Mock(), 'pagina_solicitada': 'perfil', 'escuela_rbd': 1})

        assert result == {'ok': True}
        mock_execute.assert_called_once()

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_asesor_financiero_context_wrapper(self, _mock_permission):
        with patch.object(DashboardAsesorService, 'execute', return_value={'x': 1}) as mock_exec:
            result = DashboardAsesorService.get_asesor_financiero_context(Mock(is_authenticated=True), 'perfil', 10)

        assert result == {'x': 1}
        mock_exec.assert_called_once()

    def test_execute_get_asesor_financiero_context_non_profile_pages(self):
        pages = ['dashboard_financiero', 'estados_cuenta', 'pagos', 'cuotas', 'becas', 'boletas']
        for page in pages:
            with patch('backend.apps.core.services.dashboard_asesor_service.IntegrityService.validate_school_integrity_or_raise') as mock_integrity:
                result = DashboardAsesorService._execute_get_asesor_financiero_context(
                    {'pagina_solicitada': page, 'escuela_rbd': 555}
                )

            assert result == {}
            mock_integrity.assert_called_once_with(school_id=555, action='DASHBOARD_ASESOR_CONTEXT')

    def test_execute_get_asesor_financiero_context_profile_success(self):
        cuotas_qs = Mock()
        cuotas_qs.count.return_value = 12
        pagos_qs = Mock()
        pagos_qs.count.return_value = 8

        with patch('backend.apps.core.services.dashboard_asesor_service.IntegrityService.validate_school_integrity_or_raise'), patch(
            'backend.apps.matriculas.models.Cuota.objects.filter', return_value=cuotas_qs
        ), patch('backend.apps.matriculas.models.Pago.objects.filter', return_value=pagos_qs):
            result = DashboardAsesorService._execute_get_asesor_financiero_context(
                {'pagina_solicitada': 'perfil', 'escuela_rbd': 101}
            )

        assert result['estadisticas']['total_cuotas_gestionadas'] == 12
        assert result['estadisticas']['total_pagos_procesados'] == 8

    def test_execute_get_asesor_financiero_context_profile_fallback(self):
        with patch('backend.apps.core.services.dashboard_asesor_service.IntegrityService.validate_school_integrity_or_raise'), patch(
            'backend.apps.matriculas.models.Cuota.objects.filter', side_effect=Exception('db')
        ):
            result = DashboardAsesorService._execute_get_asesor_financiero_context(
                {'pagina_solicitada': 'perfil', 'escuela_rbd': 101}
            )

        assert result['estadisticas']['total_cuotas_gestionadas'] == 0
        assert result['estadisticas']['total_pagos_procesados'] == 0

"""
Dashboard Asesor Service - Context loaders específicos para rol asesor_financiero.

Extraído de dashboard_service.py para separar responsabilidades.
"""

from backend.common.services import PermissionService
from backend.apps.core.services.integrity_service import IntegrityService

class DashboardAsesorService:
    """Service for asesor_financiero-specific context loading."""

    @staticmethod
    def execute(operation: str, params: dict):
        DashboardAsesorService.validate(operation, params)
        return DashboardAsesorService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: dict) -> None:
        if operation == 'get_asesor_financiero_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('pagina_solicitada') is None:
                raise ValueError('Parámetro requerido: pagina_solicitada')
            if params.get('escuela_rbd') is None:
                raise ValueError('Parámetro requerido: escuela_rbd')
            return
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: dict):
        if operation == 'get_asesor_financiero_context':
            return DashboardAsesorService._execute_get_asesor_financiero_context(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    @PermissionService.require_permission('FINANCIERO', 'VIEW_FINANCIAL_REPORTS')
    def get_asesor_financiero_context(user, pagina_solicitada, escuela_rbd):
        return DashboardAsesorService.execute('get_asesor_financiero_context', {
            'user': user,
            'pagina_solicitada': pagina_solicitada,
            'escuela_rbd': escuela_rbd,
        })

    @staticmethod
    def _execute_get_asesor_financiero_context(params: dict):
        """Get context specific for asesor_financiero role"""
        pagina_solicitada = params['pagina_solicitada']
        escuela_rbd = params['escuela_rbd']

        IntegrityService.validate_school_integrity_or_raise(
            school_id=escuela_rbd,
            action='DASHBOARD_ASESOR_CONTEXT',
        )

        context = {}
        
        # Dashboard financiero page - context loaded by JS via KPI API
        if pagina_solicitada == 'dashboard_financiero':
            # No server-side context needed; all data fetched client-side
            pass
        
        # Estados de cuenta - context loaded by JS via API
        elif pagina_solicitada == 'estados_cuenta':
            # No server-side context needed; all data fetched client-side
            pass
        
        # Pagos - context loaded by JS via API
        elif pagina_solicitada == 'pagos':
            # No server-side context needed; all data fetched client-side
            pass
        
        # Cuotas - context loaded by JS via API
        elif pagina_solicitada == 'cuotas':
            # No server-side context needed; all data fetched client-side
            pass
        
        # Becas - context loaded by JS via API
        elif pagina_solicitada == 'becas':
            # No server-side context needed; all data fetched client-side
            pass
        
        # Boletas - context loaded by JS via API
        elif pagina_solicitada == 'boletas':
            # No server-side context needed; all data fetched client-side
            pass
        
        # Profile page estadísticas
        elif pagina_solicitada == 'perfil':
            estadisticas = {
                'total_cuotas_gestionadas': 0,
                'total_pagos_procesados': 0,
            }
            
            try:
                from backend.apps.matriculas.models import Cuota, Pago
                
                estadisticas['total_cuotas_gestionadas'] = Cuota.objects.filter(
                    matricula__colegio_id=escuela_rbd
                ).count()
                
                estadisticas['total_pagos_procesados'] = Pago.objects.filter(
                    cuota__matricula__colegio_id=escuela_rbd,
                    estado='APROBADO'
                ).count()
            except Exception:
                pass
            
            context['estadisticas'] = estadisticas
        
        return context
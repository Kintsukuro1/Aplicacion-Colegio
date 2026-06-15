# Core views module

from datetime import datetime

from backend.apps.core.services.dashboard_service import DashboardService

def load_dashboard_context(request):
    """
    Carga el contexto básico del dashboard para el usuario.
    
    Returns:
        dict: Contexto básico del usuario
    """
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        return {}

    user_context_data = user_context.get('data') or {}
    rol = user_context_data.get('rol')

    navigation_access = DashboardService.get_navigation_access(
        rol,
        user=request.user,
        school_id=user_context_data.get('escuela_rbd'),
    )

    return {
        **user_context_data,
        'sidebar_template': DashboardService.get_sidebar_template(rol),
        'year': datetime.now().year,
        **navigation_access,
    }
"""Dashboard view delgada: delega completamente en service orquestador."""

from django.contrib.auth.decorators import login_required
from backend.apps.core.services.dashboard_orchestrator_service import DashboardOrchestratorService



@login_required()
def dashboard(request):
    return DashboardOrchestratorService.handle_dashboard(request)


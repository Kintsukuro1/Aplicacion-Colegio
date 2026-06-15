"""
Vista de checklist de configuración inicial.

Muestra el progreso de configuración del colegio con los 4 pasos obligatorios:
1. Ciclo Académico activo
2. Cursos creados
3. Profesores asignados
4. Estudiantes matriculados
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from backend.apps.core.services.dashboard_service import DashboardService
from backend.common.services.onboarding_service import OnboardingService


@login_required(login_url="login")
def setup_checklist(request):
    """
    Vista de checklist de configuración inicial.
    
    Muestra el estado de completitud de los 4 pasos obligatorios
    y proporciona enlaces para completar cada paso.
    """
    # Validar contexto de usuario
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, "Sesión inválida")
        return redirect("accounts:login")

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    # Solo administradores pueden ver el checklist
    if rol not in ["admin", "admin_escolar", "admin_general"]:
        messages.error(request, "Acceso denegado")
        return redirect("dashboard")

    if not escuela_rbd:
        messages.error(request, "No hay escuela asignada")
        return redirect("dashboard")

    # Obtener estado de configuración
    setup_status = OnboardingService.get_setup_status(escuela_rbd)
    progress_percentage = OnboardingService.get_setup_progress_percentage(escuela_rbd)
    is_legacy = OnboardingService.is_legacy_school(escuela_rbd)

    # Construir datos para el template
    steps = [
        {
            'number': 1,
            'title': 'Ciclo Académico Activo',
            'description': 'Define el período escolar actual (año académico)',
            'completed': setup_status['has_active_ciclo'],
            'action_url': '/dashboard/?pagina=gestionar_ciclos',
            'action_text': 'Crear Ciclo Académico' if not setup_status['has_active_ciclo'] else 'Ver Ciclos',
        },
        {
            'number': 2,
            'title': 'Cursos Creados',
            'description': 'Crea los cursos del colegio (niveles y secciones)',
            'completed': setup_status['has_courses'],
            'action_url': '/dashboard?pagina=gestionar_cursos',
            'action_text': 'Crear Cursos' if not setup_status['has_courses'] else 'Ver Cursos',
            'disabled': not setup_status['has_active_ciclo'],
        },
        {
            'number': 3,
            'title': 'Profesores Asignados',
            'description': 'Asigna profesores a las asignaturas de cada curso',
            'completed': setup_status['has_teachers'],
            'action_url': '/dashboard?pagina=gestionar_profesores',
            'action_text': 'Asignar Profesores' if not setup_status['has_teachers'] else 'Ver Profesores',
            'disabled': not setup_status['has_courses'],
        },
        {
            'number': 4,
            'title': 'Estudiantes Matriculados',
            'description': 'Matricula estudiantes en los cursos del ciclo actual',
            'completed': setup_status['has_students'],
            'action_url': '/dashboard?pagina=gestionar_estudiantes',
            'action_text': 'Matricular Estudiantes' if not setup_status['has_students'] else 'Ver Estudiantes',
            'disabled': not setup_status['has_courses'],
        },
    ]

    context = {
        'setup_status': setup_status,
        'progress_percentage': progress_percentage,
        'is_legacy': is_legacy,
        'steps': steps,
        'next_step': setup_status['next_required_step'],
        'user_context': user_context,
    }

    return render(request, 'admin_escolar/setup_checklist.html', context)

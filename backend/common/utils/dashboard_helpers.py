"""
Dashboard helpers for views.
Contains HTTP-dependent logic for dashboard context building.
"""

from datetime import datetime
from django.contrib import messages
from django.shortcuts import redirect

from backend.apps.core.services.dashboard_auth_service import DashboardAuthService
from backend.common.services.policy_service import PolicyService


def build_dashboard_context(request, pagina_actual: str, content_template: str):
    """
    Build complete dashboard context for views.
    Handles redirects and messages for invalid sessions.
    """
    user_context = DashboardAuthService.get_user_context(request.user, request.session)
    if user_context is None:
        is_apoderado_scope = hasattr(request.user, 'perfil_apoderado')
        if not is_apoderado_scope and not hasattr(request.user, 'perfil_profesor'):
            # Fix: profesor con STUDENT_VIEW no debe entrar al flujo de apoderado.
            has_guardian_scope = (
                PolicyService.has_capability(request.user, 'DASHBOARD_VIEW_SELF')
                and PolicyService.has_capability(request.user, 'STUDENT_VIEW')
                and not PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE')
                and not PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
                and not PolicyService.has_capability(request.user, 'CLASS_VIEW')
            )
            is_apoderado_scope = has_guardian_scope

        rol = 'apoderado' if is_apoderado_scope else None

        if not is_apoderado_scope:
            if not request.user.rbd_colegio:
                return None, redirect('seleccionar_escuela')
            messages.error(request, 'Sesión inválida - sin escuela asignada')
            return None, redirect('accounts:login')
    else:
        user_context_data = user_context['data']
        rol = user_context_data['rol']

    is_apoderado_scope = hasattr(request.user, 'perfil_apoderado')
    if not is_apoderado_scope and not hasattr(request.user, 'perfil_profesor'):
        # Fix: misma exclusión de profesor que arriba al resolver scope apoderado.
        is_apoderado_scope = (
            PolicyService.has_capability(request.user, 'DASHBOARD_VIEW_SELF')
            and PolicyService.has_capability(request.user, 'STUDENT_VIEW')
            and not PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE')
            and not PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
            and not PolicyService.has_capability(request.user, 'CLASS_VIEW')
        )

    if user_context is not None:
        navigation_access = DashboardAuthService.get_navigation_access(
            rol,
            user=request.user,
            school_id=user_context_data.get('escuela_rbd'),
        )
        context = {
            **user_context_data,
            'pagina_actual': pagina_actual,
            'sidebar_template': DashboardAuthService.get_sidebar_template(rol),
            'content_template': content_template,
            'year': datetime.now().year,
            **navigation_access,
        }
    else:
        # For apoderado when user_context is None
        navigation_access = DashboardAuthService.get_navigation_access(rol, user=request.user, school_id=None)
        context = {
            'rol': rol,
            'pagina_actual': pagina_actual,
            'sidebar_template': DashboardAuthService.get_sidebar_template(rol),
            'content_template': content_template,
            'year': datetime.now().year,
            **navigation_access,
        }

    # Special handling for apoderado
    if is_apoderado_scope:
        from backend.apps.accounts.models import PerfilEstudiante
        estudiantes = PerfilEstudiante.objects.filter(
            user__apoderados__user=request.user
        ).select_related('user', 'ciclo_actual').order_by('user__apellido_paterno', 'user__nombre')

        if not estudiantes.exists():
            messages.warning(request, 'No tienes estudiantes asociados.')
            return None, redirect('dashboard')

        context.update({
            'estudiantes': estudiantes,
            'estudiante_seleccionado': None,  # Will be set by specific views if needed
        })
        # Fix: forzar portal apoderado; evita sidebar de estudiante al ir a Mensajes u otras vistas.
        context['rol'] = 'apoderado'
        context['sidebar_template'] = DashboardAuthService.get_sidebar_template('apoderado')

    return context, None
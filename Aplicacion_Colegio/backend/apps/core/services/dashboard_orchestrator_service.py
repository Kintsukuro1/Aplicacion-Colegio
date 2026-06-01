"""
Servicio orquestador de dashboard.
Centraliza la lógica de la view dashboard para mantener la view delgada.
"""

from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages

from backend.apps.accounts.services import TeacherAvailabilityService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.dashboard_context_service import DashboardContextService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException
from backend.common.services.onboarding_service import OnboardingService
from backend.common.services.onboarding_notification_service import OnboardingNotificationService
from backend.common.services.policy_service import PolicyService


class DashboardOrchestratorService:
    """Orquesta flujo completo del dashboard manteniendo la view mínima."""

    @staticmethod
    def handle_dashboard(request):
        # Clear per-request caches to avoid cross-request data leaks
        IntegrityService.clear_cache()

        user_context = DashboardService.get_user_context(request.user, request.session)

        if user_context is None:
            if not request.user.rbd_colegio:
                return redirect('seleccionar_escuela')
            messages.error(request, "Sesión inválida - sin escuela asignada")
            return redirect('accounts:login')

        user_context_data = user_context['data']
        rol = user_context_data['rol']
        escuela_rbd = user_context_data['escuela_rbd']
        is_system_admin_scope = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN') is True
        is_school_admin_scope = PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE', school_id=escuela_rbd) is True

        pagina_solicitada = request.GET.get('pagina', 'inicio')

        if (is_system_admin_scope or rol == 'admin_general') and pagina_solicitada == 'escuelas':
            from backend.apps.core.views.admin_general.escuelas import gestionar_escuelas
            return gestionar_escuelas(request)

        if request.method == 'POST' and pagina_solicitada == 'asistencia':
            from backend.apps.core.views.profesor.asistencia import gestionar_asistencia
            colegio = SchoolQueryService.get_required_by_rbd(escuela_rbd)
            return gestionar_asistencia(request, colegio)

        if request.method == 'POST' and pagina_solicitada == 'disponibilidad':
            try:
                TeacherAvailabilityService.save_weekly_availability(
                    professor=request.user,
                    school_rbd=escuela_rbd,
                    post_data=request.POST,
                )
                messages.success(request, 'Disponibilidad horaria guardada correctamente.')
            except ValueError as exc:
                messages.error(request, str(exc))
            return redirect('/dashboard/?pagina=disponibilidad')

        access_valid, template_pagina = DashboardService.validate_page_access(
            rol,
            pagina_solicitada,
            user=request.user,
            school_id=escuela_rbd,
        )

        if not access_valid:
            messages.error(request, f"No tienes permiso para ver la página '{pagina_solicitada}'")
            pagina_solicitada = 'inicio'
            template_pagina = 'compartido/inicio_modulos.html'

        context = {
            **user_context_data,
            'pagina_actual': pagina_solicitada,
            'sidebar_template': DashboardService.get_sidebar_template(rol),
            'content_template': template_pagina,
            'year': datetime.now().year,
        }

        navigation_access = DashboardService.get_navigation_access(
            rol,
            user=request.user,
            school_id=escuela_rbd,
        )
        context.update(navigation_access)

        if request.user.is_authenticated:
            notificaciones_context = DashboardContextService.get_notificaciones_context(request.user)
            context.update(notificaciones_context)

        if pagina_solicitada == 'notificaciones' and request.user.is_authenticated:
            context.update(DashboardContextService.get_notificaciones_full_context(request.user, request.GET))

        if rol == 'estudiante':
            role_context = DashboardService.get_estudiante_context(
                request.user, pagina_solicitada, escuela_rbd, request.GET
            )
            context.update(role_context)

        elif rol == 'profesor':
            role_context = DashboardService.get_profesor_context(
                request, request.user, pagina_solicitada, escuela_rbd
            )

            if pagina_solicitada == 'asistencia':
                from backend.apps.core.views.profesor.asistencia import gestionar_asistencia
                colegio = SchoolQueryService.get_required_by_rbd(escuela_rbd)
                asistencia_context = gestionar_asistencia(request, colegio)
                role_context.update(asistencia_context)

            context.update(role_context)

        elif rol == 'apoderado':
            role_context = DashboardService.get_apoderado_context(
                request.user, pagina_solicitada, request.GET.get('estudiante_id')
            )
            context.update(role_context)

        elif rol == 'admin_general':
            role_context = DashboardService.get_admin_general_context(
                request.user, pagina_solicitada, request.GET
            )
            context.update(role_context)

        elif is_school_admin_scope or rol in ['admin', 'admin_escolar']:
            setup_status = OnboardingService.get_setup_status(escuela_rbd)
            context['setup_status'] = setup_status
            context['setup_incomplete'] = not setup_status['setup_complete']
            
            steps_completed = sum([
                setup_status['has_active_ciclo'],
                setup_status['has_courses'],
                setup_status['has_teachers'],
                setup_status['has_students'],
            ])
            context['setup_progress'] = int((steps_completed / 4) * 100)

            if not setup_status['setup_complete']:
                OnboardingNotificationService.notify_if_needed(request.user, escuela_rbd)

            try:
                if pagina_solicitada == 'gestionar_estudiantes':
                    estudiantes_context = DashboardService.get_gestionar_estudiantes_context(
                        request.user, request, escuela_rbd
                    )
                    context.update(estudiantes_context)
                elif pagina_solicitada == 'gestionar_cursos':
                    cursos_context = DashboardService.get_gestionar_cursos_context(
                        request.user, request, escuela_rbd
                    )
                    context.update(cursos_context)
                elif pagina_solicitada == 'gestionar_asignaturas':
                    asignaturas_context = DashboardService.get_gestionar_asignaturas_context(
                        request.user, request, escuela_rbd
                    )
                    context.update(asignaturas_context)
                elif pagina_solicitada == 'gestionar_profesores':
                    profesores_context = DashboardService.get_gestionar_profesores_context(
                        request.user, request, escuela_rbd
                    )
                    context.update(profesores_context)
                elif pagina_solicitada == 'gestionar_ciclos':
                    ciclos_context = DashboardService.get_gestionar_ciclos_context(
                        request.user, request.GET, escuela_rbd
                    )
                    context.update(ciclos_context)
                elif pagina_solicitada == 'asistencia':
                    from backend.apps.core.views.profesor.asistencia import gestionar_asistencia
                    colegio = SchoolQueryService.get_required_by_rbd(escuela_rbd)
                    asistencia_context = gestionar_asistencia(request, colegio, admin_mode=True)
                    context.update(asistencia_context)
                elif pagina_solicitada == 'notas':
                    notas_context = DashboardService.get_admin_notas_context(request.user, request, escuela_rbd)
                    context.update(notas_context)
                elif pagina_solicitada == 'libro_clases':
                    libro_context = DashboardService.get_admin_libro_clases_context(request.user, request, escuela_rbd)
                    context.update(libro_context)
                elif pagina_solicitada == 'reportes':
                    reportes_context = DashboardService.get_admin_reportes_context(request.user, request, escuela_rbd)
                    context.update(reportes_context)
                elif pagina_solicitada == 'reporte_cursos':
                    reporte_cursos_context = DashboardService.get_reporte_cursos_context(request.user, request, escuela_rbd)
                    context.update(reporte_cursos_context)
                elif pagina_solicitada == 'gestionar_finanzas':
                    finanzas_context = DashboardService.get_gestionar_finanzas_context(
                        request.user, escuela_rbd
                    )
                    context.update(finanzas_context)
                else:
                    role_context = DashboardService.get_admin_escolar_context(
                        request.user, pagina_solicitada, escuela_rbd
                    )
                    context.update(role_context)
            except PrerequisiteException:
                # Durante onboarding incompleto, el dashboard debe seguir cargando
                # para mostrar banner/checklist y permitir completar setup.
                if setup_status['setup_complete']:
                    raise

        elif rol == 'asesor_financiero':
            role_context = DashboardService.get_asesor_financiero_context(
                request.user, pagina_solicitada, escuela_rbd
            )
            context.update(role_context)

        elif rol == 'coordinador_academico':
            from backend.apps.core.services.dashboard_nuevos_roles_service import DashboardCoordinadorService
            role_context = DashboardCoordinadorService.get_context(
                request.user, pagina_solicitada, escuela_rbd
            )
            context.update(role_context)

        elif rol == 'inspector_convivencia':
            from backend.apps.core.services.dashboard_nuevos_roles_service import DashboardInspectorService
            role_context = DashboardInspectorService.get_context(
                request.user, pagina_solicitada, escuela_rbd
            )
            context.update(role_context)

        elif rol == 'psicologo_orientador':
            from backend.apps.core.services.dashboard_nuevos_roles_service import DashboardPsicologoService
            role_context = DashboardPsicologoService.get_context(
                request.user, pagina_solicitada, escuela_rbd, request.GET
            )
            context.update(role_context)

        elif rol == 'soporte_tecnico_escolar':
            from backend.apps.core.services.dashboard_nuevos_roles_service import DashboardSoporteService
            role_context = DashboardSoporteService.get_context(
                request.user, pagina_solicitada, escuela_rbd
            )
            context.update(role_context)

        elif rol == 'bibliotecario_digital':
            from backend.apps.core.services.dashboard_nuevos_roles_service import DashboardBibliotecarioService
            role_context = DashboardBibliotecarioService.get_context(
                request.user, pagina_solicitada, escuela_rbd
            )
            context.update(role_context)

        return render(request, 'dashboard.html', context)

"""
FASE 5: Dashboard Service
Extracted from sistema_antiguo/core/views.py (dashboard function, lines 192-850)

Business logic for main dashboard view, including:
- Role-based routing
- Context loading per role and page
- Multi-tenant school support
- Permission validation
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum, Max
from collections import defaultdict

from .dashboard_auth_service import DashboardAuthService
from .dashboard_context_service import DashboardContextService
from .dashboard_apoderado_service import DashboardApoderadoService
from .dashboard_asesor_service import DashboardAsesorService
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger(__name__)
from .dashboard_admin_service import DashboardAdminService
from backend.common.exceptions import PrerequisiteException


class DashboardService:
    """Service for dashboard business logic - Main orchestrator"""

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        DashboardService.validate(operation, params)
        return DashboardService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(DashboardService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')

    # =====================================
    # DELEGATION TO SPECIALIZED SERVICES
    # =====================================

    @staticmethod
    def _validate_school_integrity(escuela_rbd, action, *, fail_on_integrity: bool = True):
        if escuela_rbd:
            try:
                IntegrityService.validate_school_integrity_or_raise(
                    school_id=escuela_rbd,
                    action=action,
                )
            except PrerequisiteException as exc:
                if fail_on_integrity:
                    raise
                # Log and continue to let downstream defensive checks enforce tenant boundaries
                logger.warning("Continuing despite integrity inconsistencies for %s: %s", action, exc)

    @staticmethod
    def get_user_context(user, session):
        """Delegate to auth service"""
        return DashboardAuthService.get_user_context(user, session)

    @staticmethod
    def get_sidebar_template(rol):
        """Delegate to auth service"""
        return DashboardAuthService.get_sidebar_template(rol)

    @staticmethod
    def validate_page_access(rol, pagina_solicitada, user=None, school_id=None):
        """Delegate to auth service"""
        return DashboardAuthService.validate_page_access(
            rol,
            pagina_solicitada,
            user=user,
            school_id=school_id,
        )

    @staticmethod
    def get_navigation_access(rol, user=None, school_id=None):
        """Delegate to auth service"""
        return DashboardAuthService.get_navigation_access(
            rol,
            user=user,
            school_id=school_id,
        )

    @staticmethod
    def get_estudiante_context(user, pagina_solicitada, escuela_rbd, request_get_params=None):
        """Delegate to context service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_ESTUDIANTE_CONTEXT')
        return DashboardContextService.get_estudiante_context(user, pagina_solicitada, escuela_rbd, request_get_params)

    @staticmethod
    def get_asistencia_context(request, colegio):
        """Delegate to context service"""
        DashboardService._validate_school_integrity(colegio.rbd, 'DASHBOARD_GET_ASISTENCIA_CONTEXT')
        return DashboardContextService.get_asistencia_context(request.GET, colegio, request.user)

    @staticmethod
    def get_profesor_context(request, user, pagina_solicitada, escuela_rbd):
        """Delegate to context service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_PROFESOR_CONTEXT')
        return DashboardContextService.get_profesor_context(request.GET, user, pagina_solicitada, escuela_rbd)

    @staticmethod
    def get_apoderado_context(user, pagina_solicitada, estudiante_id_param=None):
        """Delegate to apoderado service"""
        return DashboardApoderadoService.get_apoderado_context(user, pagina_solicitada, estudiante_id_param)

    @staticmethod
    def get_asesor_financiero_context(user, pagina_solicitada, escuela_rbd):
        """Delegate to asesor service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_ASESOR_FINANCIERO_CONTEXT')
        return DashboardAsesorService.get_asesor_financiero_context(user, pagina_solicitada, escuela_rbd)

    @staticmethod
    def get_admin_escolar_context(user, pagina_solicitada, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_ADMIN_ESCOLAR_CONTEXT')
        return DashboardAdminService.get_admin_escolar_context(user, pagina_solicitada, escuela_rbd)

    @staticmethod
    def get_gestionar_finanzas_context(user, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_GESTIONAR_FINANZAS_CONTEXT')
        return DashboardAdminService.get_gestionar_finanzas_context(user, escuela_rbd)

    @staticmethod
    def get_gestionar_estudiantes_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_GESTIONAR_ESTUDIANTES_CONTEXT', fail_on_integrity=False)
        return DashboardAdminService.get_gestionar_estudiantes_context(
            user,
            request.GET,
            escuela_rbd,
            fail_on_integrity=False,
        )

    @staticmethod
    def get_gestionar_cursos_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_GESTIONAR_CURSOS_CONTEXT', fail_on_integrity=False)
        return DashboardAdminService.get_gestionar_cursos_context(
            user,
            request.GET,
            escuela_rbd,
            fail_on_integrity=False,
        )

    @staticmethod
    def get_gestionar_profesores_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_GESTIONAR_PROFESORES_CONTEXT', fail_on_integrity=False)
        return DashboardAdminService.get_gestionar_profesores_context(
            user,
            request.GET,
            escuela_rbd,
            fail_on_integrity=False,
        )

    @staticmethod
    def get_gestionar_asignaturas_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_GESTIONAR_ASIGNATURAS_CONTEXT', fail_on_integrity=False)
        return DashboardAdminService.get_gestionar_asignaturas_context(
            user,
            request.GET,
            escuela_rbd,
            fail_on_integrity=False,
        )

    @staticmethod
    def get_gestionar_ciclos_context(user, request_get_params, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_GESTIONAR_CICLOS_CONTEXT', fail_on_integrity=False)
        return DashboardAdminService.get_gestionar_ciclos_context(user, request_get_params, escuela_rbd)

    @staticmethod
    def get_admin_notas_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_ADMIN_NOTAS_CONTEXT')
        return DashboardAdminService.get_admin_notas_context(user, request.GET, escuela_rbd)

    @staticmethod
    def get_admin_libro_clases_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_ADMIN_LIBRO_CLASES_CONTEXT')
        return DashboardAdminService.get_admin_libro_clases_context(user, request.GET, escuela_rbd)

    @staticmethod
    def get_admin_reportes_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_ADMIN_REPORTES_CONTEXT')
        return DashboardAdminService.get_admin_reportes_context(user, request.GET, escuela_rbd)

    @staticmethod
    def get_reporte_cursos_context(user, request, escuela_rbd):
        """Delegate to admin service"""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_REPORTE_CURSOS_CONTEXT')
        return DashboardAdminService.get_reporte_cursos_context(user, request.GET, escuela_rbd)
    
    # =====================================
    # ROLE-SPECIFIC CONTEXT LOADERS
    # =====================================
    
    @staticmethod
    def get_estudiante_context(user, pagina_solicitada, escuela_rbd, request_get_params=None):
        """Get context specific for estudiante role."""
        DashboardService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GET_ESTUDIANTE_CONTEXT_ROLE')
        # Delegate to the canonical context loader to avoid drift between duplicated
        # mappings (mi_horario, mis_tareas, mis_anotaciones, etc.).
        return DashboardContextService.get_estudiante_context(
            user,
            pagina_solicitada,
            escuela_rbd,
            request_get_params,
        )

    # Alias de compatibilidad para tests/regresión que llaman métodos privados legacy.
    @staticmethod
    def _get_estudiante_inicio_context(user, escuela_rbd):
        return DashboardContextService._get_estudiante_inicio_context(user, escuela_rbd)

    @staticmethod
    def _get_estudiante_perfil_context(user, escuela_rbd):
        return DashboardContextService._get_estudiante_perfil_context(user, escuela_rbd)

    @staticmethod
    def _get_estudiante_asistencia_context(user, request_get_params=None):
        return DashboardContextService._get_estudiante_asistencia_context(user, request_get_params)

    @staticmethod
    def _get_estudiante_clases_context(user):
        return DashboardContextService._get_estudiante_clases_context(user)

    @staticmethod
    def _get_estudiante_notas_context(user):
        return DashboardContextService._get_estudiante_notas_context(user)

    @staticmethod
    def get_admin_general_context(user, pagina_solicitada, request_get_params=None):
        """
        Get context specific for admin_general role (system-wide admin)
        """
        context = {}

        if pagina_solicitada == 'escuelas':
            # Gestionar escuelas - listar todas las escuelas del sistema
            from backend.apps.institucion.models import Colegio
            escuelas = Colegio.objects.all().order_by('nombre')
            context['escuelas'] = escuelas

        elif pagina_solicitada == 'usuarios':
            # Usuarios del sistema - gestión de usuarios global
            from backend.apps.accounts.models import User
            usuarios = User.objects.all().select_related('role').order_by('email')
            context['usuarios'] = usuarios

        elif pagina_solicitada == 'planes':
            # Planes y suscripciones - gestión de suscripciones
            from backend.apps.subscriptions.models import Plan, Subscription
            planes = Plan.objects.all()
            suscripciones = Subscription.objects.all().select_related('colegio', 'plan')
            context['planes'] = planes
            context['suscripciones'] = suscripciones

        elif pagina_solicitada == 'estadisticas_globales':
            # Estadísticas globales del sistema
            from backend.apps.institucion.models import Colegio
            from backend.apps.accounts.models import User
            from django.db.models import Count

            total_escuelas = Colegio.objects.count()
            total_usuarios = User.objects.count()
            usuarios_por_rol = User.objects.values('role__nombre').annotate(count=Count('id'))

            context['total_escuelas'] = total_escuelas
            context['total_usuarios'] = total_usuarios
            context['usuarios_por_rol'] = usuarios_por_rol

        elif pagina_solicitada == 'reportes_financieros':
            # Reportes financieros globales
            from backend.apps.subscriptions.models import Subscription
            from django.db.models import Sum

            ingresos_totales = Subscription.objects.filter(status='active').aggregate(
                total=Sum('plan__precio_mensual')
            )['total'] or 0

            context['ingresos_totales'] = ingresos_totales

        elif pagina_solicitada == 'configuracion':
            # Configuración del sistema
            from backend.apps.institucion.models import Colegio
            from backend.apps.accounts.models import User, Role
            from backend.apps.subscriptions.models import Plan
            from django.conf import settings
            
            # Información del sistema
            context['total_colegios'] = Colegio.objects.count()
            context['total_usuarios'] = User.objects.count()
            context['total_roles'] = Role.objects.count()
            context['total_planes'] = Plan.objects.count()
            
            # Configuración de Django
            context['debug_mode'] = settings.DEBUG
            context['allowed_hosts'] = ', '.join(settings.ALLOWED_HOSTS)
            context['database_engine'] = settings.DATABASES['default']['ENGINE'].split('.')[-1]
            
            # Configuración de auditoría global (si existe)
            try:
                from backend.apps.auditoria.models import ConfiguracionAuditoria
                config_auditoria = ConfiguracionAuditoria.get_config(None)  # Config global
                context['config_auditoria'] = config_auditoria
            except:
                context['config_auditoria'] = None

        elif pagina_solicitada == 'auditoria':
            # Logs de auditoría
            from backend.apps.auditoria.models import AuditoriaEvento
            logs = AuditoriaEvento.objects.all().order_by('-fecha_hora')[:100]  # Últimos 100 logs
            context['logs_auditoria'] = logs

        elif pagina_solicitada == 'monitoreo_seguridad':
            # Monitoreo de seguridad
            # Por ahora, contexto vacío - se puede expandir con métricas de seguridad
            pass

        return context

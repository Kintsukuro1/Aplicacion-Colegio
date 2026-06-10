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
        from backend.apps.institucion.models import Colegio
        context = {}

        if pagina_solicitada == 'inicio':
            from backend.apps.accounts.models import User
            from backend.apps.subscriptions.models import Subscription, Plan
            from backend.apps.academico.models import MaterialClase, Asistencia, EntregaTarea
            from django.db.models import Sum, Count, Q
            from django.utils import timezone
            from datetime import date, timedelta

            # Real DB counts for main KPIs
            colegios_activos = Colegio.objects.count()
            total_usuarios = User.objects.count()
            total_profesores = User.objects.filter(role__nombre__iexact='profesor').count()
            total_estudiantes = User.objects.filter(role__nombre__iexact='estudiante').count()

            # Platform Status
            status_api = 'Online'
            status_db = 'Online'
            status_email = 'Online'
            status_backups = 'Correctos'

            # Active Trial Subscriptions
            colegios_prueba = Subscription.objects.filter(status='active', plan__is_trial=True).count()

            # Subscriptions expiring soon (next 30 days)
            hoy = timezone.now().date()
            limite_vencimiento = hoy + timedelta(days=30)
            
            expiring_subs = Subscription.objects.filter(
                status='active',
                fecha_fin__isnull=False,
                fecha_fin__gte=hoy,
                fecha_fin__lte=limite_vencimiento
            )
            licencias_vencer = expiring_subs.count()

            # Percentages for progress bars
            pct_colegios_prueba = round((colegios_prueba / colegios_activos) * 100, 1) if colegios_activos > 0 else 0
            pct_licencias_vencer = round((licencias_vencer / colegios_activos) * 100, 1) if colegios_activos > 0 else 0

            # 1. Almacenamiento Global
            total_bytes_db = MaterialClase.objects.filter(activo=True).aggregate(total=Sum('tamanio_bytes'))['total'] or 0
            limit_bytes = 500 * 1024 * 1024 * 1024 # 500 GB
            pct_almacenamiento = round((total_bytes_db / limit_bytes) * 100, 1)
            
            def format_bytes(b):
                if b == 0:
                    return "0.0 B"
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if b < 1024.0:
                        return f"{b:.1f} {unit}"
                    b /= 1024.0
                return f"{b:.1f} PB"
            total_storage_formatted = format_bytes(total_bytes_db)

            # 2. Actividad Diaria
            asistencias_hoy = Asistencia.objects.filter(fecha=hoy).count()
            entregas_hoy = EntregaTarea.objects.filter(fecha_entrega__date=hoy).count()
            actividad_diaria = asistencias_hoy + entregas_hoy

            # 3. Alertas de Baja Asistencia (Real data)
            baja_asist_colegios = (
                Asistencia.objects.values('colegio__nombre', 'colegio_id')
                .annotate(
                    total=Count('id_asistencia'),
                    presentes=Count('id_asistencia', filter=Q(estado='P'))
                )
            )
            colegios_baja_asistencia = []
            for item in baja_asist_colegios:
                if item['total'] > 0:
                    avg_asist = (item['presentes'] / item['total']) * 100
                    if avg_asist < 85.0:
                        colegios_baja_asistencia.append({
                            'nombre': item['colegio__nombre'] or f"Colegio RBD {item['colegio_id']}",
                            'asistencia': round(avg_asist, 1)
                        })

            # 4. Usuarios Bloqueados / Inactivos
            usuarios_bloqueados_count = User.objects.filter(is_active=False).count()

            # 5. Plan Distribution (Donut Chart)
            PLAN_METADATA = {
                'enterprise': {'nombre': 'Enterprise', 'color': 'hsl(224, 76%, 48%)'},
                'premium': {'nombre': 'Premium', 'color': 'hsl(262, 83%, 58%)'},
                'standard': {'nombre': 'Estándar', 'color': 'hsl(142, 72%, 29%)'},
                'basic': {'nombre': 'Básico', 'color': 'hsl(200, 70%, 40%)'},
                'trial': {'nombre': 'Prueba (Trial)', 'color': 'hsl(38, 92%, 50%)'},
                'tester': {'nombre': 'Tester', 'color': 'hsl(180, 60%, 45%)'},
            }
            
            active_subs_by_plan = Subscription.objects.filter(status='active').values('plan__codigo').annotate(total=Count('id'))
            counts_dict = {item['plan__codigo']: item['total'] for item in active_subs_by_plan}
            
            distribucion_planes = []
            total_active_subs = sum(counts_dict.values())
            
            for code, meta in PLAN_METADATA.items():
                qty = counts_dict.get(code, 0)
                if qty > 0:
                    distribucion_planes.append({
                        'plan': meta['nombre'],
                        'cantidad': qty,
                        'color': meta['color'],
                        'codigo': code
                    })
            
            # SVG math for donut chart
            accumulated_len = 0
            for pl in distribucion_planes:
                pct = pl['cantidad'] / total_active_subs if total_active_subs > 0 else 0
                stroke_len = pct * 251.2
                pl['dash_array'] = f"{stroke_len:.1f} 251.2"
                pl['dash_offset'] = f"-{accumulated_len:.1f}"
                accumulated_len += stroke_len

            # 6. Dynamic Platform Alerts
            alertas_plataforma = []
            for sub in expiring_subs.select_related('colegio'):
                dias = (sub.fecha_fin - hoy).days
                alertas_plataforma.append({
                    'tipo': 'warning',
                    'mensaje': f"Licencia de {sub.colegio.nombre} vence en {dias} días."
                })
            
            non_active_subs = Subscription.objects.exclude(status='active').select_related('colegio')
            for sub in non_active_subs:
                estado_lbl = sub.get_status_display().lower()
                alertas_plataforma.append({
                    'tipo': 'warning',
                    'mensaje': f"La suscripción de {sub.colegio.nombre} está {estado_lbl}."
                })
                
            alertas_plataforma.append({
                'tipo': 'info',
                'mensaje': 'Próximo backup automático programado hoy a las 23:59.'
            })

            # 7. Listado de Colegios Tenants (Dynamic list)
            user_counts = User.objects.values('rbd_colegio').annotate(count=Count('id'))
            user_counts_dict = {item['rbd_colegio']: item['count'] for item in user_counts if item['rbd_colegio'] is not None}
            
            plan_display_map = {
                'enterprise': 'Enterprise',
                'premium': 'Premium',
                'standard': 'Standard',
                'basic': 'Básico',
                'trial': 'Trial',
                'tester': 'Tester',
            }
            status_map = {
                'active': 'Activa',
                'expired': 'Expirada',
                'cancelled': 'Cancelada',
                'suspended': 'Suspendida',
            }
            meses = {
                1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
            }

            colegios_lista = []
            colegios_qs = Colegio.objects.all().select_related('subscription__plan').order_by('nombre')
            for col in colegios_qs:
                has_sub = hasattr(col, 'subscription') and col.subscription is not None
                
                # Determine Plan Name
                plan_name = 'Sin Plan'
                if has_sub:
                    plan_name = plan_display_map.get(col.subscription.plan.codigo, col.subscription.plan.nombre)
                
                # Determine State Label
                estado_lbl = 'Inactiva'
                if has_sub:
                    sub = col.subscription
                    if sub.status == 'active':
                        if sub.fecha_fin and sub.fecha_fin <= limite_vencimiento:
                            estado_lbl = 'Próxima a vencer'
                        elif sub.plan.is_trial:
                            estado_lbl = 'Prueba'
                        else:
                            estado_lbl = 'Activa'
                    else:
                        estado_lbl = status_map.get(sub.status, 'Inactiva')
                
                # Format renewal/expiration date
                vence_str = 'Nunca'
                if has_sub and col.subscription.fecha_fin:
                    f_fin = col.subscription.fecha_fin
                    vence_str = f"{f_fin.day} {meses[f_fin.month]} {f_fin.year}"
                elif has_sub and col.subscription.plan.is_unlimited:
                    vence_str = 'Nunca'
                elif has_sub and not col.subscription.fecha_fin:
                    vence_str = '-'

                colegios_lista.append({
                    'nombre': col.nombre,
                    'rbd': col.rbd,
                    'plan': plan_name,
                    'usuarios': user_counts_dict.get(col.rbd, 0),
                    'estado': estado_lbl,
                    'vence': vence_str,
                })

            context.update({
                'colegios_activos': colegios_activos,
                'total_usuarios': total_usuarios,
                'total_profesores': total_profesores,
                'total_estudiantes': total_estudiantes,
                'status_api': status_api,
                'status_db': status_db,
                'status_email': status_email,
                'status_backups': status_backups,
                'colegios_prueba': colegios_prueba,
                'licencias_vencer': licencias_vencer,
                'pct_colegios_prueba': pct_colegios_prueba,
                'pct_licencias_vencer': pct_licencias_vencer,
                'uso_almacenamiento_formatted': total_storage_formatted,
                'pct_almacenamiento': pct_almacenamiento,
                'actividad_diaria': actividad_diaria,
                'colegios_baja_asistencia': colegios_baja_asistencia,
                'usuarios_bloqueados_count': usuarios_bloqueados_count,
                'distribucion_planes': distribucion_planes,
                'total_active_subs': total_active_subs,
                'colegios_lista': colegios_lista,
                'alertas_plataforma': alertas_plataforma
            })

        elif pagina_solicitada == 'escuelas':
            # Gestionar escuelas - listar todas las escuelas del sistema
            from backend.apps.institucion.models import Colegio
            escuelas = Colegio.objects.all().order_by('nombre')
            context['escuelas'] = escuelas

        elif pagina_solicitada == 'usuarios':
            # Usuarios del sistema - gestión de usuarios global
            from backend.apps.accounts.models import User, Role
            usuarios = User.objects.all().select_related('role').order_by('email')
            roles = Role.objects.all().order_by('nombre')
            colegios = Colegio.objects.all().order_by('nombre')
            context['usuarios'] = usuarios
            context['roles'] = roles
            context['colegios'] = colegios

        elif pagina_solicitada == 'planes':
            # Planes y suscripciones - gestión de suscripciones
            from backend.apps.subscriptions.models import Plan, Subscription
            planes = Plan.objects.all()
            suscripciones = Subscription.objects.all().select_related('colegio', 'plan')
            colegios_sin_suscripcion = Colegio.objects.exclude(
                subscription__isnull=False
            ).order_by('nombre')
            context['planes'] = planes
            context['suscripciones'] = suscripciones
            context['colegios_sin_suscripcion'] = colegios_sin_suscripcion

        elif pagina_solicitada == 'estadisticas_globales':
            # Estadísticas globales del sistema con filtros
            from backend.apps.institucion.models import Colegio
            from backend.apps.accounts.models import User
            from django.db.models import Count

            colegio_rbd = request_get_params.get('colegio_rbd', '').strip() if request_get_params else ''
            fecha_inicio = request_get_params.get('fecha_inicio', '').strip() if request_get_params else ''
            fecha_fin = request_get_params.get('fecha_fin', '').strip() if request_get_params else ''

            colegios_qs = Colegio.objects.all()
            users_qs = User.objects.all()

            if colegio_rbd:
                colegios_qs = colegios_qs.filter(rbd=colegio_rbd)
                users_qs = users_qs.filter(rbd_colegio=colegio_rbd)

            if fecha_inicio:
                try:
                    inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                    users_qs = users_qs.filter(fecha_creacion__gte=inicio)
                except ValueError:
                    pass

            if fecha_fin:
                try:
                    fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
                    users_qs = users_qs.filter(fecha_creacion__lte=fin)
                except ValueError:
                    pass

            total_escuelas = colegios_qs.count()
            total_usuarios = users_qs.count()
            total_profesores = users_qs.filter(role__nombre__iexact='profesor').count()
            total_estudiantes = users_qs.filter(role__nombre__iexact='estudiante').count()
            total_apoderados = users_qs.filter(role__nombre__iexact='apoderado').count()
            usuarios_por_rol = users_qs.values('role__nombre').annotate(count=Count('id')).order_by('-count')
            usuarios_por_colegio = (
                users_qs.filter(rbd_colegio__isnull=False)
                .values('rbd_colegio')
                .annotate(count=Count('id'))
                .order_by('-count')[:20]
            )

            # Map RBD to colegio nombre
            all_colegios = Colegio.objects.all().order_by('nombre')
            rbds = [item['rbd_colegio'] for item in usuarios_por_colegio]
            colegios_map = {c.rbd: c.nombre for c in Colegio.objects.filter(rbd__in=rbds)}
            for item in usuarios_por_colegio:
                item['colegio_nombre'] = colegios_map.get(item['rbd_colegio'], f'RBD {item["rbd_colegio"]}')

            context['total_escuelas'] = total_escuelas
            context['total_usuarios'] = total_usuarios
            context['total_profesores'] = total_profesores
            context['total_estudiantes'] = total_estudiantes
            context['total_apoderados'] = total_apoderados
            context['usuarios_por_rol'] = usuarios_por_rol
            context['usuarios_por_colegio'] = list(usuarios_por_colegio)
            context['colegios_choices'] = all_colegios
            context['filtros'] = {
                'colegio_rbd': colegio_rbd,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            }

        elif pagina_solicitada == 'reportes_financieros':
            # Reportes financieros globales con filtros
            from backend.apps.subscriptions.models import Subscription, Plan
            from django.db.models import Sum, Count
            from django.utils import timezone
            from datetime import timedelta

            plan_id = request_get_params.get('plan_id', '').strip() if request_get_params else ''
            status = request_get_params.get('status', '').strip() if request_get_params else ''
            fecha_inicio = request_get_params.get('fecha_inicio', '').strip() if request_get_params else ''
            fecha_fin = request_get_params.get('fecha_fin', '').strip() if request_get_params else ''

            subs_qs = Subscription.objects.all()

            if plan_id:
                subs_qs = subs_qs.filter(plan_id=plan_id)
            if status:
                subs_qs = subs_qs.filter(status=status)
            if fecha_inicio:
                try:
                    inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    subs_qs = subs_qs.filter(fecha_inicio__gte=inicio)
                except ValueError:
                    pass
            if fecha_fin:
                try:
                    fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    subs_qs = subs_qs.filter(fecha_inicio__lte=fin)
                except ValueError:
                    pass

            ingresos_totales = subs_qs.filter(status='active').aggregate(
                total=Sum('plan__precio_mensual')
            )['total'] or 0

            # Desglose por plan
            ingresos_por_plan = (
                subs_qs.filter(status='active')
                .values('plan__nombre', 'plan__codigo')
                .annotate(
                    cantidad=Count('id'),
                    total_ingresos=Sum('plan__precio_mensual'),
                )
                .order_by('-total_ingresos')
            )

            # Suscripciones por estado
            suscripciones_por_estado = (
                subs_qs.values('status')
                .annotate(count=Count('id'))
            )

            # Próximas a vencer (dentro de 30 días)
            hoy = timezone.now().date()
            proximas_vencer = subs_qs.filter(
                status='active',
                fecha_fin__isnull=False,
                fecha_fin__lte=hoy + timedelta(days=30),
                fecha_fin__gte=hoy,
            ).select_related('colegio', 'plan').order_by('fecha_fin')[:10]

            total_suscripciones = subs_qs.count()
            suscripciones_activas = subs_qs.filter(status='active').count()

            all_planes = Plan.objects.all().order_by('nombre')

            context['ingresos_totales'] = ingresos_totales
            context['ingresos_por_plan'] = list(ingresos_por_plan)
            context['suscripciones_por_estado'] = list(suscripciones_por_estado)
            context['proximas_vencer'] = proximas_vencer
            context['total_suscripciones'] = total_suscripciones
            context['suscripciones_activas'] = suscripciones_activas
            context['planes_choices'] = all_planes
            context['status_choices'] = Subscription.STATUS_CHOICES
            context['filtros'] = {
                'plan_id': plan_id,
                'status': status,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            }

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
            # Logs de auditoría con filtros y paginación
            from backend.apps.auditoria.models import AuditoriaEvento
            from django.core.paginator import Paginator

            busqueda = request_get_params.get('busqueda', '').strip() if request_get_params else ''
            accion = request_get_params.get('accion', '').strip() if request_get_params else ''
            nivel = request_get_params.get('nivel', '').strip() if request_get_params else ''
            categoria = request_get_params.get('categoria', '').strip() if request_get_params else ''
            fecha_inicio = request_get_params.get('fecha_inicio', '').strip() if request_get_params else ''
            fecha_fin = request_get_params.get('fecha_fin', '').strip() if request_get_params else ''

            logs_qs = AuditoriaEvento.objects.all().order_by('-fecha_hora')

            if busqueda:
                logs_qs = logs_qs.filter(
                    Q(usuario_nombre__icontains=busqueda) |
                    Q(usuario_email__icontains=busqueda) |
                    Q(ip_address__icontains=busqueda) |
                    Q(descripcion__icontains=busqueda) |
                    Q(tabla_afectada__icontains=busqueda)
                )
            if accion:
                logs_qs = logs_qs.filter(accion=accion)
            if nivel:
                logs_qs = logs_qs.filter(nivel=nivel)
            if categoria:
                logs_qs = logs_qs.filter(categoria=categoria)
            if fecha_inicio:
                try:
                    logs_qs = logs_qs.filter(fecha_hora__date__gte=datetime.strptime(fecha_inicio, '%Y-%m-%d').date())
                except ValueError:
                    pass
            if fecha_fin:
                try:
                    logs_qs = logs_qs.filter(fecha_hora__date__lte=datetime.strptime(fecha_fin, '%Y-%m-%d').date())
                except ValueError:
                    pass

            # Paginación
            paginator = Paginator(logs_qs, 20)  # 20 logs por página
            page_number = request_get_params.get('page', 1) if request_get_params else 1
            logs_page = paginator.get_page(page_number)

            context['logs_auditoria'] = logs_page
            context['filtros'] = {
                'busqueda': busqueda,
                'accion': accion,
                'nivel': nivel,
                'categoria': categoria,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            }
            context['acciones_choices'] = AuditoriaEvento.TIPOS_ACCION
            context['categorias_choices'] = AuditoriaEvento.CATEGORIAS
            context['niveles_choices'] = AuditoriaEvento.NIVELES

        elif pagina_solicitada == 'monitoreo_seguridad':
            # Monitoreo de seguridad - datos reales de django-axes
            from django.conf import settings as django_settings

            axes_failure_limit = getattr(django_settings, 'AXES_FAILURE_LIMIT', 5)
            axes_cooloff_time = getattr(django_settings, 'AXES_COOLOFF_TIME', 1)
            context['axes_failure_limit'] = axes_failure_limit
            context['axes_cooloff_time'] = axes_cooloff_time

            try:
                from axes.models import AccessAttempt, AccessLog
                from django.utils import timezone
                from datetime import timedelta

                hace_24h = timezone.now() - timedelta(hours=24)

                intentos_fallidos = (
                    AccessAttempt.objects
                    .filter(attempt_time__gte=hace_24h)
                    .order_by('-attempt_time')[:50]
                )
                context['intentos_fallidos'] = intentos_fallidos
                context['total_intentos_fallidos'] = intentos_fallidos.count() if intentos_fallidos else 0

                # IPs bloqueadas
                from axes.utils import reset
                ips_con_muchos_intentos = (
                    AccessAttempt.objects
                    .filter(attempt_time__gte=hace_24h)
                    .values('ip_address')
                    .annotate(total=Count('id'))
                    .filter(total__gte=axes_failure_limit)
                )
                context['ips_bloqueadas'] = ips_con_muchos_intentos
                context['total_ips_bloqueadas'] = ips_con_muchos_intentos.count()

                # Logs de acceso recientes
                try:
                    logs_acceso = AccessLog.objects.order_by('-attempt_time')[:50]
                    context['logs_acceso'] = logs_acceso
                except Exception:
                    context['logs_acceso'] = []

            except ImportError:
                context['intentos_fallidos'] = []
                context['total_intentos_fallidos'] = 0
                context['ips_bloqueadas'] = []
                context['total_ips_bloqueadas'] = 0
                context['logs_acceso'] = []
            except Exception:
                logger.exception("Error cargando datos de seguridad")
                context['intentos_fallidos'] = []
                context['total_intentos_fallidos'] = 0
                context['ips_bloqueadas'] = []
                context['total_ips_bloqueadas'] = 0
                context['logs_acceso'] = []

        return context


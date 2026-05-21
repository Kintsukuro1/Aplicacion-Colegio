"""
Dashboard Admin Service - Context loaders específicos para roles administrativos.

Extraído de dashboard_service.py para separar responsabilidades.
"""

import logging
from datetime import datetime
from django.db.models import Q, Count, Sum, Max, Prefetch
from collections import defaultdict

from backend.common.services import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException

logger = logging.getLogger(__name__)


class DashboardAdminService:
    """Service for admin-specific context loading."""

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        DashboardAdminService.validate(operation, params)
        return DashboardAdminService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(DashboardAdminService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(escuela_rbd, action, *, fail_on_integrity: bool = True):
        try:
            IntegrityService.validate_school_integrity_or_raise(
                school_id=escuela_rbd,
                action=action,
            )
        except PrerequisiteException as exc:
            if fail_on_integrity:
                raise
            # Allow workflow to continue so tenant filters can still run
            logger.warning("Continuing despite integrity inconsistencies for %s: %s", action, exc)

    @staticmethod
    def _validate_colegio_setup(escuela_rbd):
        """
        Validate that the school has required setup completed.
        Returns tuple (is_valid, error_dict or None)
        """
        from backend.apps.institucion.models import Colegio, CicloAcademico
        
        # Check colegio exists
        try:
            colegio = Colegio.objects.get(rbd=escuela_rbd)
        except Colegio.DoesNotExist:
            return False, ErrorResponseBuilder.build(
                'SCHOOL_NOT_CONFIGURED',
                context={'rbd': escuela_rbd}
            )
        
        # Check active ciclo exists
        ciclo_activo = CicloAcademico.objects.filter(
            colegio=colegio,
            estado='ACTIVO'
        ).first()
        
        if not ciclo_activo:
            return False, ErrorResponseBuilder.build(
                'MISSING_CICLO_ACTIVO',
                context={'colegio': colegio.nombre, 'rbd': escuela_rbd}
            )
        
        return True, {'colegio': colegio, 'ciclo_activo': ciclo_activo}

    @staticmethod
    def _validate_cursos_exist(colegio, ciclo_activo):
        """
        Validate that active courses exist for the active ciclo.
        Returns tuple (exist, count)
        """
        from backend.apps.cursos.models import Curso
        
        cursos_count = Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=ciclo_activo,
            activo=True
        ).count()
        
        return cursos_count > 0, cursos_count


    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'VIEW_REPORTS')
    def get_admin_escolar_context(user, pagina_solicitada, escuela_rbd):
        """Get context specific for admin_escolar role"""
        DashboardAdminService._validate_school_integrity(escuela_rbd, 'DASHBOARD_ADMIN_ESCOLAR_CONTEXT')
        context = {}
        
        # Mi Escuela page
        if pagina_solicitada == 'mi_escuela':
            from backend.apps.institucion.models import Colegio
            
            try:
                colegio = Colegio.objects.select_related(
                    'comuna__region', 
                    'tipo_establecimiento', 
                    'dependencia'
                ).prefetch_related('infraestructura__tipo_infra').get(rbd=escuela_rbd)
                context['colegio'] = colegio
            except Colegio.DoesNotExist:
                context['colegio'] = None
        
        # Infraestructura page
        elif pagina_solicitada == 'infraestructura':
            context_infra = DashboardAdminService._get_infraestructura_context(escuela_rbd)
            context.update(context_infra)
        
        # Gestionar estudiantes page
        elif pagina_solicitada == 'gestionar_estudiantes':
            # Note: This requires request parameters, will be handled in view
            pass

        # Gestionar finanzas page
        elif pagina_solicitada == 'gestionar_finanzas':
            finanzas_context = DashboardAdminService.get_gestionar_finanzas_context(user, escuela_rbd)
            context.update(finanzas_context)
        
        return context

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'VIEW_REPORTS')
    def get_gestionar_finanzas_context(user, escuela_rbd):
        """
        Get context for gestionar_finanzas page (Admin Escolar).
        Loads key financial KPIs and reference data for the finance panel.
        """
        from decimal import Decimal
        from django.db.models import F, Sum, Value, DecimalField
        from django.db.models.functions import Coalesce
        from django.utils import timezone

        from backend.apps.institucion.models import Colegio, CicloAcademico
        from backend.apps.matriculas.models import Beca, Cuota, Matricula, Pago

        DashboardAdminService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GESTIONAR_FINANZAS_CONTEXT')

        hoy = timezone.localtime(timezone.now()).date()

        # Detect active academic cycle
        ciclo_activo = CicloAcademico.objects.filter(
            colegio_id=escuela_rbd, estado='ACTIVO'
        ).order_by('-fecha_inicio', '-id').first()

        # Base querysets scoped to school
        cuotas_qs = Cuota.objects.filter(matricula__colegio_id=escuela_rbd)
        if ciclo_activo:
            cuotas_qs = cuotas_qs.filter(matricula__ciclo_academico=ciclo_activo)

        # KPI: Total Facturado / Recaudado
        stats = cuotas_qs.aggregate(
            total_facturado=Coalesce(Sum('monto_final'), Value(Decimal('0')), output_field=DecimalField(max_digits=12, decimal_places=0)),
            total_recaudado=Coalesce(Sum('monto_pagado'), Value(Decimal('0')), output_field=DecimalField(max_digits=12, decimal_places=0)),
        )
        total_facturado = stats['total_facturado']
        total_recaudado = stats['total_recaudado']

        # KPI: Collection rate
        tasa_cobro = 0.0
        if total_facturado and total_facturado > 0:
            tasa_cobro = round(float((total_recaudado / total_facturado) * 100), 1)

        # KPI: Overdue debt
        from django.db.models import Q
        cuotas_vencidas_qs = cuotas_qs.filter(
            Q(estado='VENCIDA') | (
                Q(estado__in=['PENDIENTE', 'PAGADA_PARCIAL']) & Q(fecha_vencimiento__lt=hoy)
            )
        )
        cuotas_vencidas_count = cuotas_vencidas_qs.count()

        deuda_vencida = cuotas_vencidas_qs.annotate(
            saldo=Coalesce(
                F('monto_final') - F('monto_pagado'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=12, decimal_places=0),
            )
        ).aggregate(total=Coalesce(Sum('saldo'), Value(Decimal('0'))))['total']

        # KPI: Scholarships
        becas_filter = {'matricula__colegio_id': escuela_rbd}
        if ciclo_activo:
            becas_filter['matricula__ciclo_academico'] = ciclo_activo

        becas_activas = Beca.objects.filter(**becas_filter, estado__in=['APROBADA', 'VIGENTE']).count()
        becas_pendientes = Beca.objects.filter(**becas_filter, estado__in=['SOLICITADA', 'EN_REVISION']).count()

        # Top 5 debtors
        matriculas_deudoras_qs = Matricula.objects.filter(
            colegio_id=escuela_rbd, estado='ACTIVA'
        ).select_related('estudiante', 'curso')
        if ciclo_activo:
            matriculas_deudoras_qs = matriculas_deudoras_qs.filter(ciclo_academico=ciclo_activo)

        matriculas_deudoras = (
            matriculas_deudoras_qs
            .annotate(
                total_facturado_m=Coalesce(
                    Sum('cuotas__monto_final'), Value(Decimal('0')),
                    output_field=DecimalField(max_digits=12, decimal_places=0)
                ),
                total_pagado_m=Coalesce(
                    Sum('cuotas__monto_pagado'), Value(Decimal('0')),
                    output_field=DecimalField(max_digits=12, decimal_places=0)
                ),
            )
            .annotate(
                saldo_m=Coalesce(
                    F('total_facturado_m') - F('total_pagado_m'),
                    Value(Decimal('0')),
                    output_field=DecimalField(max_digits=12, decimal_places=0),
                )
            )
            .filter(saldo_m__gt=0)
            .order_by('-saldo_m')[:5]
        )

        deudores = []
        for m in matriculas_deudoras:
            deudores.append({
                'estudiante': m.estudiante.get_full_name() if m.estudiante else '(Sin estudiante)',
                'curso': str(m.curso) if m.curso else 'Sin curso',
                'saldo': int(m.saldo_m or 0),
            })

        # Reference data for modals
        metodos_pago = [{'code': code, 'label': label} for code, label in Pago.METODO_CHOICES]
        tipos_beca = [{'code': code, 'label': label} for code, label in Beca.TIPO_CHOICES]

        return {
            'total_facturado': int(total_facturado),
            'total_recaudado': int(total_recaudado),
            'deuda_vencida': int(deuda_vencida),
            'tasa_cobro': tasa_cobro,
            'cuotas_vencidas_count': cuotas_vencidas_count,
            'becas_activas': becas_activas,
            'becas_pendientes': becas_pendientes,
            'deudores': deudores,
            'metodos_pago': metodos_pago,
            'tipos_beca': tipos_beca,
            'ciclo_activo': ciclo_activo,
        }

    @staticmethod
    def _get_infraestructura_context(escuela_rbd):
        """Helper: Get infraestructura context"""
        DashboardAdminService._validate_school_integrity(escuela_rbd, 'DASHBOARD_INFRAESTRUCTURA_CONTEXT')
        from backend.apps.institucion.models import Infraestructura
        
        # Get active infraestructura
        infraestructura = Infraestructura.objects.filter(
            rbd_colegio=escuela_rbd,
            activo=True
        ).order_by('tipo', 'piso', 'nombre')
        
        # Calculate stats
        stats = Infraestructura.objects.filter(
            rbd_colegio=escuela_rbd,
            activo=True
        ).aggregate(
            total_espacios=Count('id'),
            total_salas=Count('id', filter=Q(tipo='Sala de Clases')),
            capacidad_total=Sum('capacidad_estudiantes'),
            area_total=Sum('area_m2'),
            total_pisos=Max('piso'),
            espacios_operativos=Count('id', filter=Q(estado='Operativo')),
            espacios_mantenimiento=Count('id', filter=Q(estado='En Mantenimiento')),
            espacios_fuera_servicio=Count('id', filter=Q(estado='Fuera de Servicio'))
        )
        
        # Group by type
        infraestructura_agrupada = defaultdict(list)
        for item in infraestructura:
            infraestructura_agrupada[item.tipo].append(item)
        
        return {
            'infraestructura': infraestructura,
            'infraestructura_agrupada': dict(infraestructura_agrupada),
            'estadisticas': stats,
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def get_gestionar_estudiantes_context(user, request_get_params, escuela_rbd, *, fail_on_integrity: bool = True):
        """
        Get context for gestionar_estudiantes page
        Requires request_get_params dict for filters and pagination
        """
        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

        from backend.apps.accounts.models import PerfilEstudiante, User
        from backend.apps.cursos.models import Curso
        from backend.apps.matriculas.models import Matricula

        DashboardAdminService._validate_school_integrity(
            escuela_rbd,
            'DASHBOARD_GESTIONAR_ESTUDIANTES_CONTEXT',
            fail_on_integrity=fail_on_integrity,
        )
        
        # Validate colegio setup first
        is_valid, result = DashboardAdminService._validate_colegio_setup(escuela_rbd)
        if not is_valid:
            return result  # Return error dict
        
        colegio = result['colegio']
        ciclo_activo = result['ciclo_activo']
        
        # Get filters
        filtro_curso = request_get_params.get('curso', '')
        filtro_estado = request_get_params.get('estado', '')
        filtro_busqueda = request_get_params.get('busqueda', '').strip()
        
        # Optimized query (ported from sistema_antiguo.core.optimizations.get_estudiantes_optimized)
        estudiantes_query = (
            User.objects.filter(
                rbd_colegio=escuela_rbd,
                perfil_estudiante__isnull=False,
                is_active=True,
            )
            .select_related('role', 'perfil_estudiante')
            .prefetch_related(
                Prefetch(
                    'matriculas',
                    queryset=Matricula.objects.filter(estado='ACTIVA').select_related('colegio'),
                )
            )
            .order_by('apellido_paterno', 'apellido_materno', 'nombre')
        )
        
        # Apply filters
        if filtro_busqueda:
            estudiantes_query = estudiantes_query.filter(
                Q(nombre__icontains=filtro_busqueda) |
                Q(apellido_paterno__icontains=filtro_busqueda) |
                Q(apellido_materno__icontains=filtro_busqueda) |
                Q(rut__icontains=filtro_busqueda) |
                Q(email__icontains=filtro_busqueda)
            )
        
        if filtro_curso:
            try:
                ciclo_id = int(filtro_curso)
                estudiantes_query = estudiantes_query.filter(perfil_estudiante__ciclo_actual=ciclo_id)
            except (ValueError, TypeError):
                pass
        
        if filtro_estado:
            estudiantes_query = estudiantes_query.filter(perfil_estudiante__estado_academico=filtro_estado)
        
        # Apply pagination (ported from sistema_antiguo.core.utils.pagination.paginate_queryset)
        per_page = 50
        page = request_get_params.get('page', 1)
        paginator = Paginator(estudiantes_query, per_page)

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Get available cursos (current year and future)
        anio_actual = datetime.now().year
        cursos = Curso.objects.filter(
            colegio_id=escuela_rbd,
            activo=True,
            ciclo_academico__fecha_inicio__year__gte=anio_actual - 1
        ).select_related('nivel', 'ciclo_academico').order_by('-ciclo_academico__fecha_inicio', 'nivel__nombre', 'nombre')
        
        # Calculate statistics
        total_estudiantes = estudiantes_query.count()
        estudiantes_activos = PerfilEstudiante.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_estudiante__isnull=False,
            user__is_active=True,
            estado_academico='Activo'
        ).count()
        estudiantes_sin_curso = PerfilEstudiante.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_estudiante__isnull=False,
            user__is_active=True,
            ciclo_actual__isnull=True
        ).count()
        cursos_con_estudiantes = PerfilEstudiante.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_estudiante__isnull=False,
            user__is_active=True,
            ciclo_actual__isnull=False
        ).values('ciclo_actual').distinct().count()
        
        return {
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'estudiantes': page_obj,  # Maintain compatibility
            'cursos': cursos,
            'total_estudiantes': total_estudiantes,
            'estudiantes_activos': estudiantes_activos,
            'estudiantes_sin_curso': estudiantes_sin_curso,
            'total_cursos_con_estudiantes': cursos_con_estudiantes,
            'filtro_curso': filtro_curso,
            'filtro_estado': filtro_estado,
            'filtro_busqueda': filtro_busqueda,
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_COURSES')
    def get_gestionar_cursos_context(user, request_get_params, escuela_rbd, *, fail_on_integrity: bool = True):
        """
        Get context for gestionar_cursos page
        Requires request_get_params dict for filters
        """
        DashboardAdminService._validate_school_integrity(
            escuela_rbd,
            'DASHBOARD_GESTIONAR_CURSOS_CONTEXT',
            fail_on_integrity=fail_on_integrity,
        )

        from django.db.models import Count, Q
        
        from backend.apps.accounts.models import PerfilEstudiante, User
        from backend.apps.cursos.models import Asignatura, Clase, Curso
        from backend.apps.institucion.models import NivelEducativo
        
        # Validate colegio setup first
        is_valid, result = DashboardAdminService._validate_colegio_setup(escuela_rbd)
        if not is_valid:
            return result  # Return error dict
        
        colegio = result['colegio']
        ciclo_activo = result['ciclo_activo']
        
        # Get filters
        filtro_nivel = request_get_params.get('nivel', '').strip()
        
        # Get cursos with annotations
        cursos_query = Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=ciclo_activo,  # Only courses in active ciclo
            activo=True
        ).select_related('nivel', 'ciclo_academico').annotate(
            total_clases=Count('clases', filter=Q(clases__activo=True), distinct=True),
            total_estudiantes=Count(
                'matriculas__estudiante',
                filter=Q(
                    matriculas__estado='ACTIVA',
                    matriculas__estudiante__is_active=True,
                    matriculas__ciclo_academico=ciclo_activo,
                ),
                distinct=True,
            ),
        ).order_by('nivel__nombre', 'nombre')
        
        # Apply filters
        if filtro_nivel:
            cursos_query = cursos_query.filter(nivel_id=filtro_nivel)
        
        cursos = list(cursos_query)
        
        # Defensive check: Warn if courses with mismatched ciclo states exist
        cursos_with_invalid_ciclo = Curso.objects.filter(
            colegio=colegio,
            activo=True
        ).exclude(
            ciclo_academico__estado='ACTIVO'
        ).count()
        
        # Calculate statistics (only for active ciclo)
        total_cursos = Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=ciclo_activo,
            activo=True
        ).count()
        
        total_estudiantes_asignados = PerfilEstudiante.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_estudiante__isnull=False,
            user__is_active=True,
            ciclo_actual__isnull=False
        ).count()
        
        total_clases_activas = Clase.objects.filter(
            curso__colegio=colegio,
            curso__ciclo_academico=ciclo_activo,  # Only for active ciclo
            curso__activo=True,
            activo=True
        ).count()
        
        cursos_sin_estudiantes = Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=ciclo_activo,  # Only for active ciclo
            activo=True
        ).exclude(
            matriculas__estado='ACTIVA',
            matriculas__estudiante__is_active=True,
            matriculas__ciclo_academico=ciclo_activo
        ).distinct().count()
        
        # Get niveles
        niveles = NivelEducativo.objects.all().order_by('nombre')
        
        # Get estudiantes sin curso
        estudiantes_sin_curso = User.objects.filter(
            rbd_colegio=escuela_rbd,
            perfil_estudiante__isnull=False,
            is_active=True,
            perfil_estudiante__ciclo_actual__isnull=True
        ).select_related('perfil_estudiante').order_by('apellido_paterno', 'apellido_materno', 'nombre')
        
        # Get asignaturas
        asignaturas = Asignatura.objects.filter(activa=True).order_by('nombre')
        
        # Get profesores
        profesores = User.objects.filter(
            rbd_colegio=escuela_rbd,
            perfil_profesor__isnull=False,
            is_active=True
        ).order_by('apellido_paterno', 'apellido_materno', 'nombre')
        
        return {
            'cursos': cursos,
            'total_cursos': total_cursos,
            'total_estudiantes_asignados': total_estudiantes_asignados,
            'total_clases_activas': total_clases_activas,
            'cursos_sin_estudiantes': cursos_sin_estudiantes,
            'niveles': niveles,
            'filtro_nivel': filtro_nivel,
            'estudiantes_sin_curso': estudiantes_sin_curso,
            'asignaturas': asignaturas,
            'profesores': profesores,
            'ciclo_activo': ciclo_activo,  # Include for context
            'colegio': colegio,  # Include for context
            'cursos_with_invalid_ciclo': cursos_with_invalid_ciclo,  # Warn admin
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_COURSES')
    def get_gestionar_asignaturas_context(user, request_get_params, escuela_rbd, *, fail_on_integrity: bool = False):
        """
        Get context for gestionar_asignaturas page
        Requires request_get_params dict for filters
        """
        DashboardAdminService._validate_school_integrity(
            escuela_rbd,
            'DASHBOARD_GESTIONAR_ASIGNATURAS_CONTEXT',
            fail_on_integrity=fail_on_integrity,
        )

        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
        from django.db.models import Count, Q, Sum
        from collections import defaultdict
        import json
        
        from backend.apps.accounts.models import User
        from backend.apps.cursos.models import Asignatura, BloqueHorario, Clase, Curso
        from backend.apps.institucion.models import Colegio
        
        # Validate colegio setup first
        is_valid, result = DashboardAdminService._validate_colegio_setup(escuela_rbd)
        if not is_valid:
            return result  # Return error dict
        
        colegio = result['colegio']
        ciclo_activo = result['ciclo_activo']
        
        # Get filters
        filtro_busqueda = request_get_params.get('busqueda', '').strip()
        curso_horario_id = request_get_params.get('curso_horario', '').strip()
        
        # Get asignaturas with annotations (only for active courses in active ciclo)
        asignaturas_query = Asignatura.objects.filter(
            colegio=colegio,
            activa=True
        ).annotate(
            total_cursos=Count(
                'clases__curso', 
                filter=Q(clases__curso__ciclo_academico=ciclo_activo, clases__curso__activo=True),
                distinct=True
            ),
            total_clases=Count(
                'clases', 
                filter=Q(clases__curso__ciclo_academico=ciclo_activo, clases__activo=True),
                distinct=True
            )
        ).order_by('nombre')
        
        # Apply search filter
        if filtro_busqueda:
            asignaturas_query = asignaturas_query.filter(
                Q(nombre__icontains=filtro_busqueda) | Q(codigo__icontains=filtro_busqueda)
            )
        
        # Paginate asignaturas listing
        per_page = 30
        page = request_get_params.get('page', 1)
        paginator = Paginator(asignaturas_query, per_page)
        try:
            asignaturas_page = paginator.page(page)
        except PageNotAnInteger:
            asignaturas_page = paginator.page(1)
        except EmptyPage:
            asignaturas_page = paginator.page(paginator.num_pages)

        asignaturas = asignaturas_page
        
        # Calculate statistics (only for active ciclo)
        total_asignaturas = Asignatura.objects.filter(
            colegio=colegio,
            activa=True
        ).count()
        
        total_clases_activas = Clase.objects.filter(
            colegio=colegio,
            curso__ciclo_academico=ciclo_activo,  # Active ciclo only
            asignatura__activa=True,
            activo=True
        ).count()
        
        total_horas_semanales = Asignatura.objects.filter(
            colegio=colegio,
            activa=True
        ).aggregate(total=Sum('horas_semanales'))['total'] or 0
        
        asignaturas_sin_asignar = Asignatura.objects.filter(
            colegio=colegio,
            activa=True
        ).exclude(
            clases__curso__ciclo_academico=ciclo_activo,  # Active ciclo only
            clases__activo=True
        ).distinct().count()
        
        # Get cursos for horario selector (only active ciclo)
        cursos = Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=ciclo_activo,
            activo=True
        ).select_related('nivel', 'ciclo_academico').order_by('nivel__nombre', 'nombre')
        
        # Get curso seleccionado for horario
        curso_seleccionado = None
        if curso_horario_id:
            try:
                curso_seleccionado = Curso.objects.get(
                    id_curso=curso_horario_id,
                    colegio=colegio,
                    activo=True
                )
            except Curso.DoesNotExist:
                curso_seleccionado = cursos.first() if cursos else None
        else:
            curso_seleccionado = cursos.first() if cursos else None
        
        # Get clases activas for assignment (only active ciclo)
        clases_activas = Clase.objects.filter(
            colegio=colegio,
            curso__ciclo_academico=ciclo_activo,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by(
            'asignatura__nombre', 'curso__nombre'
        )
        
        # Get profesores
        profesores = User.objects.filter(
            rbd_colegio=escuela_rbd,
            perfil_profesor__isnull=False,
            is_active=True
        ).order_by('apellido_paterno', 'apellido_materno', 'nombre')
        
        # Get bloques horarios (fixed time slots)
        from datetime import time
        bloques_horarios = [
            {'numero': 1, 'hora_inicio': time(8, 0), 'hora_fin': time(8, 45)},
            {'numero': 2, 'hora_inicio': time(8, 45), 'hora_fin': time(9, 30)},
            {'numero': 3, 'hora_inicio': time(9, 40), 'hora_fin': time(10, 25)},
            {'numero': 4, 'hora_inicio': time(10, 25), 'hora_fin': time(11, 10)},
            {'numero': 5, 'hora_inicio': time(11, 20), 'hora_fin': time(12, 5)},
            {'numero': 6, 'hora_inicio': time(12, 5), 'hora_fin': time(12, 50)},
            {'numero': 7, 'hora_inicio': time(13, 30), 'hora_fin': time(14, 15)},
            {'numero': 8, 'hora_inicio': time(14, 15), 'hora_fin': time(15, 0)},
        ]
        
        # Add horario data to bloques
        if curso_seleccionado:
            horarios_curso = BloqueHorario.objects.filter(
                colegio=colegio,
                clase__curso=curso_seleccionado,
                activo=True,
            ).select_related('clase__asignatura', 'clase__profesor')

            horarios_por_slot = defaultdict(list)
            for horario in horarios_curso:
                horarios_por_slot[(horario.bloque_numero, horario.dia_semana)].append(horario)

            for bloque in bloques_horarios:
                bloque['dias'] = []
                for dia_num in range(1, 6):  # Lunes a Viernes
                    horarios = horarios_por_slot.get((bloque['numero'], dia_num), [])

                    if horarios:
                        clases_en_bloque = []
                        for horario in horarios:
                            clases_en_bloque.append({
                                'bloque_id': horario.id_bloque,
                                'clase': horario.clase
                            })
                        bloque['dias'].append({
                            'dia_numero': dia_num,
                            'clases': clases_en_bloque
                        })
                    else:
                        bloque['dias'].append({
                            'dia_numero': dia_num,
                            'clases': []
                        })
        
        # Prepare clases_por_asignatura_json for JavaScript
        clases_por_asignatura = defaultdict(list)
        for clase in clases_activas:
            clases_por_asignatura[clase.asignatura.id_asignatura].append({
                'clase_id': clase.id,
                'curso_nombre': clase.curso.nombre,
                'profesor_nombre': clase.profesor.get_full_name()
            })
        clases_por_asignatura_json = json.dumps(dict(clases_por_asignatura))
        
        return {
            'asignaturas': asignaturas,
            'page_obj': asignaturas_page,
            'is_paginated': paginator.num_pages > 1,
            'total_asignaturas': total_asignaturas,
            'total_clases_activas': total_clases_activas,
            'total_horas_semanales': total_horas_semanales,
            'asignaturas_sin_asignar': asignaturas_sin_asignar,
            'filtro_busqueda': filtro_busqueda,
            'cursos': cursos,
            'curso_seleccionado': curso_seleccionado,
            'clases_activas': clases_activas,
            'profesores': profesores,
            'bloques_horarios': bloques_horarios,
            'clases_por_asignatura_json': clases_por_asignatura_json,
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def get_admin_notas_context(user, request_get_params, escuela_rbd):
        """
        Get context for notas page in admin mode (all classes)
        """
        DashboardAdminService._validate_school_integrity(escuela_rbd, 'DASHBOARD_ADMIN_NOTAS_CONTEXT')

        from django.db.models import Q
        from backend.apps.institucion.models import Colegio
        from backend.apps.cursos.models import Clase
        from backend.apps.academico.models import Evaluacion, Calificacion
        
        colegio = Colegio.objects.get(rbd=escuela_rbd)
        
        # Get all active classes for the school
        clases = Clase.objects.filter(
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by(
            'asignatura__nombre', 'curso__nombre'
        )
        
        filtro_clase_id = request_get_params.get('clase_id', '')
        if not filtro_clase_id and clases.exists():
            filtro_clase_id = str(clases.first().id)
        
        evaluaciones = []
        estudiantes_con_notas = []
        clase_seleccionada = None
        
        if filtro_clase_id:
            try:
                clase_seleccionada = Clase.objects.get(id=filtro_clase_id, colegio=colegio)
            
                # Obtener evaluaciones de la clase
                evaluaciones = Evaluacion.objects.filter(
                    clase=clase_seleccionada, 
                    activa=True
                ).order_by('fecha_evaluacion')
                
                # Obtener estudiantes de la clase
                from backend.apps.accounts.models import PerfilEstudiante
                from backend.apps.matriculas.models import Matricula
                estudiantes_rel = PerfilEstudiante.objects.filter(
                    user__matriculas__curso=clase_seleccionada.curso,
                    user__matriculas__estado='ACTIVA',
                    user__is_active=True
                ).select_related('user').distinct()
                
                estudiantes = [rel.user for rel in estudiantes_rel]
                calificaciones_map = {}

                if evaluaciones and estudiantes:
                    calificaciones = Calificacion.objects.filter(
                        evaluacion__in=evaluaciones,
                        estudiante__in=estudiantes,
                    ).select_related('evaluacion', 'estudiante')
                    calificaciones_map = {
                        (calif.evaluacion_id, calif.estudiante_id): calif
                        for calif in calificaciones
                    }

                # Para cada estudiante, obtener calificaciones (sin N+1)
                for estudiante_rel in estudiantes_rel:
                    estudiante = estudiante_rel.user
                    calificaciones_estudiante = []
                    
                    for evaluacion in evaluaciones:
                        calif = calificaciones_map.get((evaluacion.id, estudiante.id))
                        calificaciones_estudiante.append({
                            'evaluacion': evaluacion,
                            'nota': calif.nota if calif else None
                        })
                    
                    estudiantes_con_notas.append({
                        'estudiante': estudiante,
                        'calificaciones': calificaciones_estudiante
                    })
            except Exception as e:
                pass
        
        # Calcular estadísticas para el template
        total_evaluaciones = len(evaluaciones)
        total_calificaciones = 0
        promedio_general = 0
        
        if estudiantes_con_notas and evaluaciones:
            todas_las_notas = []
            for estudiante in estudiantes_con_notas:
                for calif in estudiante['calificaciones']:
                    if calif['nota'] is not None:
                        todas_las_notas.append(float(calif['nota']))
                        total_calificaciones += 1
            
            if todas_las_notas:
                promedio_general = round(sum(todas_las_notas) / len(todas_las_notas), 1)
        
        return {
            'clases': clases,
            'filtro_clase_id': filtro_clase_id,
            'evaluaciones': evaluaciones,
            'estudiantes_con_notas': estudiantes_con_notas,
            'clase_seleccionada': clase_seleccionada,
            'total_evaluaciones': total_evaluaciones,
            'total_calificaciones': total_calificaciones,
            'promedio_general': promedio_general
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_GRADES')
    def get_admin_libro_clases_context(user, request_get_params, escuela_rbd):
        """
        Get context for libro_clases page in admin mode (all classes)
        """
        DashboardAdminService._validate_school_integrity(escuela_rbd, 'DASHBOARD_ADMIN_LIBRO_CLASES_CONTEXT')

        from backend.apps.institucion.models import Colegio
        from backend.apps.cursos.models import Clase
        from backend.apps.academico.services.grades_service import GradesService
        
        colegio = Colegio.objects.get(rbd=escuela_rbd)
        
        # Get all active classes for the school
        clases = Clase.objects.filter(
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by(
            'asignatura__nombre', 'curso__nombre'
        )
        
        filtro_clase_id = request_get_params.get('clase_id', '')
        clase_seleccionada = None
        matriz_calificaciones = []
        evaluaciones = []
        promedios_evaluaciones = []
        total_evaluaciones = 0
        total_estudiantes = 0
        promedio_general = 0
        
        if filtro_clase_id:
            try:
                clase_id = int(filtro_clase_id)
                clase_seleccionada = clases.filter(id=clase_id).first()
                
                if clase_seleccionada:
                    gradebook_data = GradesService.build_gradebook_matrix(
                        colegio, clase_seleccionada
                    )
                    
                    evaluaciones = gradebook_data['evaluaciones']
                    matriz_calificaciones = gradebook_data['matriz_calificaciones']
                    promedios_evaluaciones = gradebook_data['promedios_evaluaciones']
                    total_evaluaciones = gradebook_data['total_evaluaciones']
                    total_estudiantes = gradebook_data['total_estudiantes']
                    promedio_general = gradebook_data['promedio_general']
            
            except (ValueError, TypeError) as e:
                pass  # Silently handle errors
        
        return {
            'clases': clases,
            'filtro_clase_id': filtro_clase_id,
            'clase_seleccionada': clase_seleccionada,
            'evaluaciones': evaluaciones,
            'matriz_calificaciones': matriz_calificaciones,
            'promedios_evaluaciones': promedios_evaluaciones,
            'total_evaluaciones': total_evaluaciones,
            'total_estudiantes': total_estudiantes,
            'promedio_general': promedio_general,
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def get_gestionar_profesores_context(user, request_get_params, escuela_rbd, *, fail_on_integrity: bool = True):
        """
        Get context for gestionar_profesores page
        Requires request_get_params dict for filters and pagination
        """
        DashboardAdminService._validate_school_integrity(
            escuela_rbd,
            'DASHBOARD_GESTIONAR_PROFESORES_CONTEXT',
            fail_on_integrity=fail_on_integrity,
        )

        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
        from django.db.models import Count, Q, Sum

        from backend.apps.accounts.models import User, PerfilProfesor
        from backend.apps.cursos.models import Asignatura, Clase
        
        # Validate colegio setup first
        is_valid, result = DashboardAdminService._validate_colegio_setup(escuela_rbd)
        if not is_valid:
            return result  # Return error dict
        
        colegio = result['colegio']
        
        # Get filters
        filtro_buscar = request_get_params.get('buscar', '').strip()
        filtro_estado = request_get_params.get('estado', '')
        filtro_asignatura = request_get_params.get('asignatura', '')
        
        # Optimized query for profesores
        profesores_query = (
            User.objects.filter(
                rbd_colegio=escuela_rbd,
                perfil_profesor__isnull=False,
                is_active=True,
            )
            .select_related('role', 'perfil_profesor')
            .prefetch_related(
                'clases_impartidas__asignatura'
            )
            .annotate(
                clases_count=Count('clases_impartidas', filter=Q(clases_impartidas__activo=True)),
            )
            .order_by('apellido_paterno', 'apellido_materno', 'nombre')
        )
        
        # Apply filters
        if filtro_buscar:
            profesores_query = profesores_query.filter(
                Q(nombre__icontains=filtro_buscar) |
                Q(apellido_paterno__icontains=filtro_buscar) |
                Q(apellido_materno__icontains=filtro_buscar) |
                Q(rut__icontains=filtro_buscar) |
                Q(email__icontains=filtro_buscar)
            )
        
        if filtro_estado:
            profesores_query = profesores_query.filter(perfil_profesor__estado_laboral=filtro_estado)
        
        if filtro_asignatura:
            try:
                asignatura_id = int(filtro_asignatura)
                profesores_query = profesores_query.filter(clases__asignatura_id=asignatura_id)
            except (ValueError, TypeError):
                pass
        
        # Apply pagination
        per_page = 50
        page = request_get_params.get('page', 1)
        paginator = Paginator(profesores_query, per_page)

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Calculate statistics
        total_profesores = profesores_query.count()
        profesores_activos = PerfilProfesor.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_profesor__isnull=False,
            user__is_active=True,
            estado_laboral='Activo'
        ).count()
        
        # Total clases asignadas
        total_clases = Clase.objects.filter(
            colegio=colegio,
            profesor__is_active=True,
            activo=True
        ).count()
        
        # Total horas semanales
        total_horas = Asignatura.objects.filter(
            colegio=colegio,
            activa=True
        ).aggregate(total=Sum('horas_semanales'))['total'] or 0
        
        # Get asignaturas for filter
        asignaturas = Asignatura.objects.filter(
            colegio=colegio,
            activa=True
        ).order_by('nombre')
        
        return {
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'profesores': page_obj,  # Maintain compatibility
            'total_profesores': total_profesores,
            'profesores_activos': profesores_activos,
            'total_clases': total_clases,
            'total_horas': total_horas,
            'asignaturas': asignaturas,
            'filtro_buscar': filtro_buscar,
            'filtro_estado': filtro_estado,
            'filtro_asignatura': filtro_asignatura,
        }
        """
        Get context for gestionar_ciclos page
        Requires request_get_params dict for filters
        """
        """
        Get context for gestionar_ciclos page
        Requires request_get_params dict for filters
        """
        from backend.apps.institucion.models import Colegio, CicloAcademico
        
        # Get colegio
        colegio = Colegio.objects.get(rbd=escuela_rbd)
        
        # Get ciclos
        ciclos = CicloAcademico.objects.filter(
            colegio=colegio
        ).order_by('-fecha_inicio')
        
        # Calculate statistics
        total_ciclos = ciclos.count()
        ciclos_activos = ciclos.filter(estado='ACTIVO').count()
        ciclos_inactivos = ciclos.filter(estado='INACTIVO').count()
        
        # Prepare data for JavaScript
        ciclos_data = []
        for ciclo in ciclos:
            ciclos_data.append({
                'id': ciclo.id,
                'nombre': ciclo.nombre,
                'fecha_inicio': ciclo.fecha_inicio.strftime('%Y-%m-%d') if ciclo.fecha_inicio else '',
                'fecha_fin': ciclo.fecha_fin.strftime('%Y-%m-%d') if ciclo.fecha_fin else '',
                'descripcion': ciclo.descripcion or '',
                'estado': ciclo.estado,
            })
        
        return {
            'ciclos': ciclos,
            'total_ciclos': total_ciclos,
            'ciclos_activos': ciclos_activos,
            'ciclos_inactivos': ciclos_inactivos,
            'ciclos_data': ciclos_data,
        }

    @staticmethod
    def get_gestionar_ciclos_context(user, request_get_params, escuela_rbd):
        """
        Get context for gestionar_ciclos page
        Requires request_get_params dict for filters
        """
        DashboardAdminService._validate_school_integrity(escuela_rbd, 'DASHBOARD_GESTIONAR_CICLOS_CONTEXT')

        from backend.apps.institucion.models import Colegio, CicloAcademico
        
        # Get colegio
        colegio = Colegio.objects.get(rbd=escuela_rbd)
        
        # Get ciclos
        ciclos = CicloAcademico.objects.filter(
            colegio=colegio
        ).order_by('-fecha_inicio')
        
        # Calculate statistics
        total_ciclos = ciclos.count()
        ciclos_activos = ciclos.filter(estado='ACTIVO').count()
        ciclos_inactivos = ciclos.filter(estado='INACTIVO').count()
        
        # Prepare data for JavaScript
        ciclos_data = []
        for ciclo in ciclos:
            ciclos_data.append({
                'id': ciclo.id,
                'nombre': ciclo.nombre,
                'fecha_inicio': ciclo.fecha_inicio.strftime('%Y-%m-%d') if ciclo.fecha_inicio else '',
                'fecha_fin': ciclo.fecha_fin.strftime('%Y-%m-%d') if ciclo.fecha_fin else '',
                'descripcion': ciclo.descripcion or '',
                'estado': ciclo.estado,
            })
        
        return {
            'ciclos': ciclos,
            'total_ciclos': total_ciclos,
            'ciclos_activos': ciclos_activos,
            'ciclos_inactivos': ciclos_inactivos,
            'ciclos_data': ciclos_data,
        }

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'VIEW_REPORTS')
    def get_admin_reportes_context(user, request_get_params, escuela_rbd):
        """
        Get context for reportes page in admin mode (all classes)
        """
        DashboardAdminService._validate_school_integrity(escuela_rbd, 'DASHBOARD_ADMIN_REPORTES_CONTEXT')

        from backend.apps.institucion.models import Colegio
        from backend.apps.cursos.models import Clase
        from backend.apps.academico.services.academic_reports_service import AcademicReportsService
        
        colegio = Colegio.objects.get(rbd=escuela_rbd)
        
        # Get all active classes for the school
        clases = Clase.objects.filter(
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by(
            'asignatura__nombre', 'curso__nombre'
        )
        
        tipo_reporte = request_get_params.get('tipo', 'asistencia')
        filtro_clase_id = request_get_params.get('clase_id', '')
        fecha_inicio = request_get_params.get('fecha_inicio', '')
        fecha_fin = request_get_params.get('fecha_fin', '')
        
        reporte_data = None
        clase_seleccionada = None
        
        if filtro_clase_id:
            try:
                clase_id = int(filtro_clase_id)
                clase_seleccionada = clases.filter(id=clase_id).first()
                
                if clase_seleccionada:
                    fecha_inicio_parsed, fecha_fin_parsed = AcademicReportsService.parse_report_filters(fecha_inicio, fecha_fin)
                    reporte_data = AcademicReportsService.generate_report_data(
                        user, clase_seleccionada, tipo_reporte, fecha_inicio_parsed, fecha_fin_parsed
                    )
            
            except (ValueError, TypeError) as e:
                pass  # Silently handle errors
        
        return {
            'clases': clases,
            'tipo_reporte': tipo_reporte,
            'filtro_clase_id': filtro_clase_id,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'reporte_data': reporte_data,
            'clase_seleccionada': clase_seleccionada,
        }

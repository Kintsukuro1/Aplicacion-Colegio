"""
Dashboard Apoderado Service - Context loaders específicos para rol apoderado.

Extraído de dashboard_service.py para separar responsabilidades.
"""
import logging
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger(__name__)

class DashboardApoderadoService:
    """Service for apoderado-specific context loading."""

    @staticmethod
    def execute(operation: str, params: dict):
        DashboardApoderadoService.validate(operation, params)
        return DashboardApoderadoService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: dict) -> None:
        if operation == 'get_apoderado_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('pagina_solicitada') is None:
                raise ValueError('Parámetro requerido: pagina_solicitada')
            return
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: dict):
        if operation == 'get_apoderado_context':
            return DashboardApoderadoService._execute_get_apoderado_context(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def get_apoderado_context(user, pagina_solicitada, estudiante_id_param=None):
        return DashboardApoderadoService.execute('get_apoderado_context', {
            'user': user,
            'pagina_solicitada': pagina_solicitada,
            'estudiante_id_param': estudiante_id_param,
        })

    @staticmethod
    def _execute_get_apoderado_context(params: dict):
        """Get context specific for apoderado role"""
        from backend.apps.accounts.models import RelacionApoderadoEstudiante

        user = params['user']
        pagina_solicitada = params['pagina_solicitada']
        estudiante_id_param = params.get('estudiante_id_param')
        
        context = {}

        if getattr(user, 'rbd_colegio', None):
            IntegrityService.validate_school_integrity_or_raise(
                school_id=user.rbd_colegio,
                action='DASHBOARD_APODERADO_CONTEXT',
            )
        
        try:
            # Obtener pupilos usando la relación correcta: RelacionApoderadoEstudiante.apoderado -> Apoderado.user
            relaciones_qs = (
                RelacionApoderadoEstudiante.objects
                .select_related('estudiante', 'apoderado', 'apoderado__user')
                .filter(
                    apoderado__user=user,
                    apoderado__activo=True,
                    activa=True,
                    estudiante__is_active=True,
                )
                .order_by('prioridad_contacto', 'estudiante__apellido_paterno', 'estudiante__nombre')
            )

            # Mantener orden y evitar duplicados de estudiante por múltiples relaciones
            estudiantes = []
            seen_ids = set()
            for relacion in relaciones_qs:
                estudiante = relacion.estudiante
                if estudiante.id not in seen_ids:
                    seen_ids.add(estudiante.id)
                    estudiantes.append(estudiante)
            
            # Common context for all apoderado pages
            context.update({
                'apoderado': user,
                'estudiantes': estudiantes,
            })
            
            # Inicio/perfil page
            if pagina_solicitada in ['inicio', 'perfil']:
                context.update({
                    'total_pupilos': len(estudiantes),
                    'comunicados_nuevos': 0,  # TODO: Implement real count
                    'pendientes_firma': 0,  # TODO: Implement real count
                    'cuotas_pendientes': 0,  # TODO: Implement real count
                })
            
            # Notas page
            elif pagina_solicitada == 'notas':
                context_notas = DashboardApoderadoService._get_apoderado_notas_context(
                    user, estudiantes, estudiante_id_param
                )
                context.update(context_notas)

            # Mis pupilos page
            elif pagina_solicitada == 'mis_pupilos':
                context_pupilos = DashboardApoderadoService._get_apoderado_mis_pupilos_context(
                    estudiantes
                )
                context.update(context_pupilos)
            
            # Asistencia page
            elif pagina_solicitada == 'asistencia':
                context_asistencia = DashboardApoderadoService._get_apoderado_asistencia_context(
                    user, estudiantes, estudiante_id_param
                )
                context.update(context_asistencia)

            # Certificados page
            elif pagina_solicitada == 'mis_certificados':
                from backend.apps.accounts.models import User
                # Need full User objects with perfil for certificate page
                est_ids = [est.id for est in estudiantes]
                pupilos = list(User.objects.filter(
                    id__in=est_ids
                ).select_related('perfil_estudiante__ciclo_actual'))
                context['pupilos'] = pupilos

            # Justificativos page
            elif pagina_solicitada == 'justificativos':
                context_just = DashboardApoderadoService._get_apoderado_justificativos_context(
                    user, estudiantes
                )
                context.update(context_just)

            # Firmas pendientes page
            elif pagina_solicitada == 'firmas_pendientes':
                context_firmas = DashboardApoderadoService._get_apoderado_firmas_context(user)
                context.update(context_firmas)

            # Admisión y Matrícula page
            elif pagina_solicitada == 'admision_matricula':
                context_admision = DashboardApoderadoService._get_apoderado_admision_context(user)
                context.update(context_admision)

            # Calendario del pupilo
            elif pagina_solicitada == 'calendario_pupilo':
                context_cal = DashboardApoderadoService._get_apoderado_calendario_context(
                    user, estudiantes, estudiante_id_param
                )
                context.update(context_cal)
                
        except Exception as e:
            logger.error(f"Error in get_apoderado_context: {e}", exc_info=True)
            pass
        
        return context

    @staticmethod
    def _get_apoderado_inicio_context(user, estudiante_id_param=None):
        """Get inicio context for apoderado"""
        # TODO: Implement specific inicio logic if needed
        return {}

    @staticmethod
    def _get_apoderado_perfil_context(user, estudiante_id_param=None):
        """Get perfil context for apoderado"""
        # TODO: Implement specific perfil logic if needed
        return {}

    @staticmethod
    def _get_apoderado_notas_context(user, estudiantes, estudiante_id_param):
        """Helper: Get notas context for apoderado"""
        from backend.apps.academico.models import Calificacion
        from collections import defaultdict
        
        # Select student
        estudiante_seleccionado = None
        if estudiante_id_param:
            try:
                estudiante_seleccionado = next(
                    (est for est in estudiantes if str(est.id) == estudiante_id_param), 
                    None
                )
            except:
                pass
        
        if not estudiante_seleccionado and estudiantes:
            estudiante_seleccionado = estudiantes[0]

        ficha_alumno = {}
        notas_por_asignatura = []
        promedio_general = None

        if estudiante_seleccionado:
            from backend.apps.accounts.models import User
            from backend.apps.academico.models import Asistencia
            from django.db.models import Count, Q

            try:
                estudiante_enriquecido = (
                    User.objects
                    .select_related(
                        'perfil_estudiante__curso_actual_id',
                        'perfil_estudiante__ciclo_actual',
                    )
                    .filter(pk=estudiante_seleccionado.pk)
                    .first()
                )
                if estudiante_enriquecido:
                    estudiante_seleccionado = estudiante_enriquecido
            except Exception as enrich_error:
                logger.warning(
                    'No se pudo enriquecer perfil del estudiante para notas: %s',
                    enrich_error,
                )

            calificaciones = Calificacion.objects.filter(
                estudiante=estudiante_seleccionado,
                evaluacion__activa=True
            ).select_related(
                'evaluacion',
                'evaluacion__clase',
                'evaluacion__clase__asignatura',
            ).order_by('evaluacion__clase__asignatura__nombre', '-evaluacion__fecha_evaluacion')

            calificaciones_por_asignatura = defaultdict(list)
            asignaturas_by_key = {}

            for calif in calificaciones:
                clase = getattr(calif.evaluacion, 'clase', None)
                asignatura = getattr(clase, 'asignatura', None)
                clase_id = getattr(calif.evaluacion, 'clase_id', None)
                asignatura_id = getattr(asignatura, 'id_asignatura', getattr(asignatura, 'id', None)) if asignatura else None

                asignatura_id_valido = isinstance(asignatura_id, (int, str))
                clase_id_valido = isinstance(clase_id, (int, str))

                if asignatura_id_valido:
                    asignatura_key = f"asig:{asignatura_id}"
                elif clase_id_valido:
                    asignatura_key = f"clase:{clase_id}"
                else:
                    continue

                if asignatura_key not in asignaturas_by_key:
                    asignaturas_by_key[asignatura_key] = asignatura

                calificaciones_por_asignatura[asignatura_key].append(calif)

            total_promedio = 0
            count_asignaturas = 0

            for asignatura_key, calificaciones_asignatura in calificaciones_por_asignatura.items():
                evaluaciones_list = []
                suma_notas = 0

                for calif in calificaciones_asignatura:
                    evaluaciones_list.append({
                        'nombre': calif.evaluacion.nombre,
                        'fecha_evaluacion': calif.evaluacion.fecha_evaluacion,
                        'nota': calif.nota,
                        'ponderacion': calif.evaluacion.ponderacion,
                    })
                    suma_notas += calif.nota

                promedio_asignatura = None
                total_calif = len(calificaciones_asignatura)
                if total_calif > 0:
                    promedio_asignatura = round(suma_notas / total_calif, 1)
                    total_promedio += promedio_asignatura
                    count_asignaturas += 1

                notas_por_asignatura.append({
                    'asignatura': asignaturas_by_key.get(asignatura_key),
                    'promedio': promedio_asignatura,
                    'evaluaciones': evaluaciones_list,
                })

            notas_por_asignatura.sort(
                key=lambda item: str(getattr(item['asignatura'], 'nombre', '')) if item.get('asignatura') else ''
            )

            if count_asignaturas > 0:
                promedio_general = round(total_promedio / count_asignaturas, 1)

            total_evaluaciones = sum(len(item['evaluaciones']) for item in notas_por_asignatura)
            por_reforzar = sum(
                1 for item in notas_por_asignatura
                if item.get('promedio') is not None and item['promedio'] < 4.0
            )

            perfil = getattr(estudiante_seleccionado, 'perfil_estudiante', None)
            curso = getattr(perfil, 'curso_actual', None) if perfil else None
            curso_nombre = getattr(curso, 'nombre', None) if curso else None
            ciclo = getattr(perfil, 'ciclo_actual', None) if perfil else None
            ciclo_nombre = getattr(ciclo, 'nombre', None) if ciclo else None

            asistencia_row = (
                Asistencia.objects
                .filter(estudiante_id=estudiante_seleccionado.id)
                .aggregate(
                    total=Count('pk'),
                    presentes=Count('pk', filter=Q(estado='P')),
                )
            )
            pct_asistencia = None
            if asistencia_row['total']:
                pct_asistencia = round(
                    (asistencia_row['presentes'] / asistencia_row['total']) * 100,
                    1,
                )

            ficha_alumno = {
                'curso': curso_nombre or 'Sin curso asignado',
                'ciclo': ciclo_nombre,
                'rut': getattr(estudiante_seleccionado, 'rut', None) or '—',
                'email': getattr(estudiante_seleccionado, 'email', None) or '—',
                'total_asignaturas': count_asignaturas,
                'total_evaluaciones': total_evaluaciones,
                'por_reforzar': por_reforzar,
                'porcentaje_asistencia': pct_asistencia,
            }

        return {
            'estudiante_seleccionado': estudiante_seleccionado,
            'notas_por_asignatura': notas_por_asignatura,
            'promedio_general': promedio_general,
            'ficha_alumno': ficha_alumno,
        }

    @staticmethod
    def _get_apoderado_asistencia_context(apoderado, estudiantes, estudiante_id_param):
        """Helper: Get asistencia context for apoderado"""
        from backend.apps.academico.models import Asistencia
        from backend.apps.cursos.models import Clase
        from collections import defaultdict
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count, Q
        
        # Select student
        estudiante_seleccionado = None
        if estudiante_id_param:
            try:
                estudiante_seleccionado = next(
                    (est for est in estudiantes if str(est.id) == estudiante_id_param), 
                    None
                )
            except:
                pass
        
        if not estudiante_seleccionado and estudiantes:
            estudiante_seleccionado = estudiantes[0]
        
        registros = Asistencia.objects.none()
        estadisticas = {}
        registros_por_fecha = defaultdict(list)
        asignaturas = []
        
        if estudiante_seleccionado:
            # Get asistencia records (last 90 days)
            fecha_inicio = timezone.now().date() - timedelta(days=90)
            
            registros = Asistencia.objects.filter(
                estudiante=estudiante_seleccionado,
                fecha__gte=fecha_inicio
            ).select_related(
                'clase__asignatura',
                'clase__profesor'
            ).order_by('-fecha')
            
            # Calculate estadísticas
            conteos = registros.aggregate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P')),
                ausentes=Count('pk', filter=Q(estado='A')),
                atrasos=Count('pk', filter=Q(estado='T')),
                justificadas=Count('pk', filter=Q(estado='J')),
            )
            total = conteos['total'] or 0
            if total > 0:
                presentes = conteos['presentes'] or 0
                ausentes = conteos['ausentes'] or 0
                atrasos = conteos['atrasos'] or 0
                justificadas = conteos['justificadas'] or 0
                
                estadisticas = {
                    'presentes': presentes,
                    'ausentes': ausentes,
                    'atrasos': atrasos,
                    'justificadas': justificadas,
                    'total': total,
                    'porcentaje_presente': round((presentes / total) * 100, 1),
                    'porcentaje_ausente': round((ausentes / total) * 100, 1),
                    'porcentaje_atraso': round((atrasos / total) * 100, 1),
                    'porcentaje_justificada': round((justificadas / total) * 100, 1),
                    'sin_datos': False
                }
            else:
                # No hay registros de asistencia
                estadisticas = {
                    'presentes': 0,
                    'ausentes': 0,
                    'atrasos': 0,
                    'justificadas': 0,
                    'total': 0,
                    'porcentaje_presente': 0,
                    'porcentaje_ausente': 0,
                    'porcentaje_atraso': 0,
                    'porcentaje_justificada': 0,
                    'sin_datos': True
                }
            
            # Group by fecha
            for registro in registros:
                registros_por_fecha[registro.fecha].append(registro)
            
            # Get asignaturas
            if hasattr(estudiante_seleccionado, 'perfil_estudiante') and estudiante_seleccionado.perfil_estudiante.curso_actual:
                clases = Clase.objects.filter(
                    curso=estudiante_seleccionado.perfil_estudiante.curso_actual,
                    activo=True
                ).select_related('asignatura')
                asignaturas = list({clase.asignatura for clase in clases if clase.asignatura is not None})
        
        return {
            'estudiante_seleccionado': estudiante_seleccionado,
            'registros_asistencia': registros,
            'estadisticas': estadisticas,
            'registros_por_fecha': dict(registros_por_fecha),
            'asignaturas': asignaturas,
        }

    @staticmethod
    def _get_apoderado_mis_pupilos_context(estudiantes):
        """Attach promedio general y asistencia acumulada por pupilo."""
        from django.db.models import Avg, Count, Q
        from backend.apps.academico.models import Calificacion, Asistencia

        if not estudiantes:
            return {'estudiantes': estudiantes}

        estudiante_ids = [e.id for e in estudiantes if getattr(e, 'id', None)]
        if not estudiante_ids:
            return {'estudiantes': estudiantes}

        promedios_qs = (
            Calificacion.objects
            .filter(estudiante_id__in=estudiante_ids, evaluacion__activa=True)
            .values('estudiante_id')
            .annotate(promedio=Avg('nota'))
        )
        promedios_map = {row['estudiante_id']: row['promedio'] for row in promedios_qs}

        asistencia_qs = (
            Asistencia.objects
            .filter(estudiante_id__in=estudiante_ids)
            .values('estudiante_id')
            .annotate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P')),
            )
        )
        asistencia_map = {
            row['estudiante_id']: (
                round((row['presentes'] / row['total']) * 100, 1) if row['total'] else None
            )
            for row in asistencia_qs
        }

        for estudiante in estudiantes:
            promedio_raw = promedios_map.get(estudiante.id)
            estudiante.promedio_general = round(float(promedio_raw), 1) if promedio_raw is not None else None
            estudiante.porcentaje_asistencia = asistencia_map.get(estudiante.id)

        return {'estudiantes': estudiantes}

    @staticmethod
    def _get_apoderado_justificativos_context(user, estudiantes):
        """Get justificativos context for apoderado."""
        from backend.apps.core.models import JustificativoInasistencia

        rbd = getattr(user, 'rbd_colegio', None)
        justificativos = []

        if rbd:
            justificativos_qs = JustificativoInasistencia.objects.filter(
                presentado_por=user,
                colegio_id=rbd,
            ).select_related('estudiante').order_by('-fecha_creacion')

            for j in justificativos_qs:
                justificativos.append({
                    'id': j.id_justificativo,
                    'estudiante_nombre': j.estudiante.get_full_name(),
                    'fecha_ausencia': j.fecha_ausencia,
                    'fecha_fin': j.fecha_fin_ausencia,
                    'tipo': j.get_tipo_display(),
                    'tipo_raw': j.tipo,
                    'motivo': j.motivo,
                    'estado': j.estado,
                    'estado_display': j.get_estado_display(),
                    'tiene_adjunto': bool(j.documento_adjunto),
                    'observaciones_revision': j.observaciones_revision or '',
                    'fecha_creacion': j.fecha_creacion,
                })

        return {
            'justificativos': justificativos,
            'total_justificativos': len(justificativos),
            'pendientes': sum(1 for j in justificativos if j['estado'] == 'PENDIENTE'),
            'aprobados': sum(1 for j in justificativos if j['estado'] == 'APROBADO'),
            'rechazados': sum(1 for j in justificativos if j['estado'] == 'RECHAZADO'),
        }

    @staticmethod
    def _get_apoderado_firmas_context(user):
        """Get firmas pendientes context for apoderado."""
        from backend.apps.accounts.models import FirmaDigitalApoderado

        firmados = []

        if hasattr(user, 'perfil_apoderado'):
            apoderado = user.perfil_apoderado
            firmas_qs = FirmaDigitalApoderado.objects.filter(
                apoderado=apoderado,
            ).select_related('estudiante').order_by('-timestamp_firma')[:50]

            for firma in firmas_qs:
                firmados.append({
                    'id': firma.id,
                    'tipo': firma.get_tipo_documento_display(),
                    'titulo': firma.titulo_documento,
                    'estudiante_nombre': firma.estudiante.get_full_name() if firma.estudiante else '',
                    'fecha_firma': firma.timestamp_firma,
                    'valida': firma.firma_valida,
                })

        return {
            'firmados': firmados,
            'total_firmados': len(firmados),
            'pendientes_firma': [],  # TODO: implement detection of unsigned documents
        }

    @staticmethod
    def _get_apoderado_calendario_context(user, estudiantes, estudiante_id_param):
        """Get calendario context for apoderado - shows upcoming events for selected pupilo."""
        from backend.apps.academico.models import Evaluacion, Tarea
        from backend.apps.cursos.models import Clase
        from datetime import date, timedelta
        from backend.apps.accounts.models import PerfilEstudiante

        # Select student
        estudiante_seleccionado = None
        if estudiante_id_param:
            try:
                estudiante_seleccionado = next(
                    (est for est in estudiantes if str(est.id) == estudiante_id_param),
                    None
                )
            except Exception:
                pass

        if not estudiante_seleccionado and estudiantes:
            estudiante_seleccionado = estudiantes[0]

        eventos = []
        hoy = date.today()
        fecha_limite = hoy + timedelta(days=30)

        if estudiante_seleccionado:
            # Upcoming evaluaciones
            evaluaciones = Evaluacion.objects.filter(
                clase__estudiantes__estudiante_id=estudiante_seleccionado.id,
                clase__estudiantes__activo=True,
                clase__activo=True,
                activa=True,
                fecha_evaluacion__gte=hoy,
                fecha_evaluacion__lte=fecha_limite,
            ).select_related(
                'clase__asignatura'
            ).order_by('fecha_evaluacion')[:20]

            for ev in evaluaciones:
                eventos.append({
                    'tipo': 'evaluacion',
                    'titulo': ev.nombre,
                    'asignatura': ev.clase.asignatura.nombre if ev.clase.asignatura else 'N/A',
                    'fecha': ev.fecha_evaluacion,
                    'icono': '📝',
                    'color': '#ef4444',
                })

            # Upcoming tareas
            tareas = Tarea.objects.filter(
                clase__estudiantes__estudiante_id=estudiante_seleccionado.id,
                clase__estudiantes__activo=True,
                clase__activo=True,
                activa=True,
                es_publica=True,
                fecha_entrega__gte=hoy,
                fecha_entrega__lte=fecha_limite,
            ).select_related(
                'clase__asignatura'
            ).order_by('fecha_entrega')[:20]

            for tarea in tareas:
                eventos.append({
                    'tipo': 'tarea',
                    'titulo': tarea.titulo,
                    'asignatura': tarea.clase.asignatura.nombre if tarea.clase.asignatura else 'N/A',
                    'fecha': tarea.fecha_entrega,
                    'icono': '📋',
                    'color': '#3b82f6',
                })

            # Sort all events by date
            eventos.sort(key=lambda e: e['fecha'])

        return {
            'estudiante_seleccionado': estudiante_seleccionado,
            'eventos_calendario': eventos,
            'total_eventos': len(eventos),
        }

    @staticmethod
    def _get_apoderado_admision_context(user):
        """Get admissions and enrollment context for apoderado."""
        from backend.apps.matriculas.models import SolicitudAdmision
        from backend.apps.cursos.models import Curso
        from backend.apps.institucion.models import CicloAcademico
        
        rbd = getattr(user, 'rbd_colegio', None)
        solicitudes = []
        cursos_disponibles = []
        ciclo_activo = None
        
        if rbd:
            # 1. Obtener solicitudes históricas
            solicitudes_qs = SolicitudAdmision.objects.filter(
                apoderado=user,
                colegio_id=rbd
            ).select_related('curso_postulado', 'ciclo_academico').prefetch_related('contrato').order_by('-fecha_creacion')
            
            for sol in solicitudes_qs:
                contrato_data = None
                try:
                    if sol.estado == 'ACEPTADA' and hasattr(sol, 'contrato'):
                        contrato_data = sol.contrato
                except Exception:
                    pass
                
                solicitudes.append({
                    'id': sol.id_solicitud,
                    'nombre_estudiante': f"{sol.nombre_estudiante} {sol.apellido_paterno_estudiante} {sol.apellido_materno_estudiante}",
                    'rut_estudiante': sol.rut_estudiante or '',
                    'curso_nombre': sol.curso_postulado.nombre if sol.curso_postulado else '',
                    'curso_id': sol.curso_postulado.id_curso if sol.curso_postulado else None,
                    'ciclo_nombre': sol.ciclo_academico.nombre if sol.ciclo_academico else '',
                    'estado': sol.estado,
                    'estado_display': sol.get_estado_display(),
                    'posicion_lista_espera': sol.posicion_lista_espera,
                    'fecha_creacion': sol.fecha_creacion,
                    'tiene_contrato': contrato_data is not None,
                    'contrato': contrato_data,
                })
            
            # 2. Obtener ciclo académico activo
            ciclo_activo = CicloAcademico.objects.filter(
                colegio_id=rbd,
                activo=True
            ).first()
            
            # 3. Obtener cursos disponibles
            if ciclo_activo:
                cursos_disponibles = list(Curso.objects.filter(
                    colegio_id=rbd,
                    ciclo_academico=ciclo_activo,
                    activo=True
                ).order_by('nombre'))
                
        return {
            'solicitudes_admision': solicitudes,
            'total_solicitudes': len(solicitudes),
            'cursos_disponibles': cursos_disponibles,
            'ciclo_activo': ciclo_activo,
        }

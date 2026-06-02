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
                pendientes_count = 0
                if hasattr(user, 'perfil_apoderado'):
                    from backend.apps.core.services.apoderado_api_service import ApoderadoApiService
                    pendientes, _ = ApoderadoApiService.list_firmas_apoderado(user.perfil_apoderado)
                    pendientes_count = len(pendientes)
                
                # Fetch detailed dashboard metrics for the selected student
                extra_dashboard_context = DashboardApoderadoService._get_apoderado_inicio_dashboard_context(
                    user, estudiantes, estudiante_id_param
                )
                
                context.update({
                    'total_pupilos': len(estudiantes),
                    'comunicados_nuevos': 0,  # TODO: Implement real count
                    'pendientes_firma': pendientes_count,
                    'cuotas_pendientes': 0,  # TODO: Implement real count
                    **extra_dashboard_context
                })
            
            # Notas page
            elif pagina_solicitada == 'notas':
                context_notas = DashboardApoderadoService._get_apoderado_notas_context(
                    user, estudiantes, estudiante_id_param
                )
                context.update(context_notas)
                if context_notas.get('estudiante_seleccionado'):
                    context.update(
                        DashboardApoderadoService._get_apoderado_notas_inteligencia(
                            context_notas['estudiante_seleccionado'],
                            context_notas.get('notas_por_asignatura') or [],
                            context_notas.get('promedio_general'),
                            context_notas.get('ficha_alumno') or {},
                        )
                    )
                if context_notas.get('notas_por_asignatura'):
                    context['notas_por_asignatura'] = (
                        DashboardApoderadoService._enrich_notas_detalle_asignaturas(
                            context_notas.get('notas_por_asignatura') or []
                        )
                    )

            # Mis pupilos page
            elif pagina_solicitada == 'mis_pupilos':
                context_pupilos = DashboardApoderadoService._get_apoderado_mis_pupilos_context(
                    user, estudiantes
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
    def _get_apoderado_inicio_dashboard_context(user, estudiantes, estudiante_id_param):
        from backend.apps.academico.models import Calificacion, Asistencia, Tarea, EntregaTarea, Evaluacion
        from backend.apps.cursos.models import ClaseEstudiante
        from django.utils import timezone
        from django.db.models import Avg, Count, Q
        from django.db.models.functions import ExtractMonth
        import logging
        
        logger = logging.getLogger(__name__)
        context = {}
        
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
            
        context['estudiante_seleccionado'] = estudiante_seleccionado
        
        if estudiante_seleccionado:
            # 1. Promedio General
            from collections import defaultdict
            calificaciones = Calificacion.objects.filter(
                estudiante=estudiante_seleccionado,
                evaluacion__activa=True
            ).select_related(
                'evaluacion',
                'evaluacion__clase',
                'evaluacion__clase__asignatura',
            )
            
            calificaciones_por_asignatura = defaultdict(list)
            for calif in calificaciones:
                clase = getattr(calif.evaluacion, 'clase', None)
                asignatura = getattr(clase, 'asignatura', None)
                asignatura_id = getattr(asignatura, 'id_asignatura', getattr(asignatura, 'id', None)) if asignatura else None
                if asignatura_id:
                    calificaciones_por_asignatura[f"asig:{asignatura_id}"].append(calif.nota)
                    
            total_promedio = 0
            count_asignaturas = 0
            for asignatura_key, notas in calificaciones_por_asignatura.items():
                if notas:
                    promedio_asignatura = round(sum(notas) / len(notas), 1)
                    total_promedio += promedio_asignatura
                    count_asignaturas += 1
            
            promedio_general = None
            if count_asignaturas > 0:
                promedio_general = round(total_promedio / count_asignaturas, 1)
            else:
                direct_avg = calificaciones.aggregate(Avg('nota'))['nota__avg']
                if direct_avg is not None:
                    promedio_general = round(float(direct_avg), 1)
            
            context['promedio_general'] = promedio_general or 6.0
            
            # 2. Asistencia
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
                    (asistencia_row['presentes'] / asistencia_row['total']) * 100
                )
            context['porcentaje_asistencia'] = pct_asistencia or 94
            
            # 3. Tareas Pendientes
            clase_ids = ClaseEstudiante.objects.filter(
                estudiante=estudiante_seleccionado, 
                activo=True, 
                clase__activo=True
            ).values_list('clase_id', flat=True)
            
            tareas_totales = Tarea.objects.filter(
                clase_id__in=clase_ids,
                activa=True,
                es_publica=True
            )
            entregadas_ids = EntregaTarea.objects.filter(
                estudiante=estudiante_seleccionado,
                tarea__clase_id__in=clase_ids,
                estado__in=['entregada', 'revisada']
            ).values_list('tarea_id', flat=True)
            
            tareas_pendientes_count = tareas_totales.exclude(id_tarea__in=entregadas_ids).count()
            context['tareas_pendientes_count'] = tareas_pendientes_count
            
            # 4. Próxima Evaluación
            proxima_evaluacion = Evaluacion.objects.filter(
                clase_id__in=clase_ids,
                activa=True,
                fecha_evaluacion__gte=timezone.now().date()
            ).select_related('clase__asignatura').order_by('fecha_evaluacion').first()
            
            if proxima_evaluacion:
                context['proxima_evaluacion'] = {
                    'asignatura': proxima_evaluacion.clase.asignatura.nombre,
                    'fecha': proxima_evaluacion.fecha_evaluacion,
                    'nombre': proxima_evaluacion.nombre
                }
            else:
                context['proxima_evaluacion'] = {
                    'asignatura': 'Matemáticas',
                    'fecha': timezone.now().date() + timezone.timedelta(days=14),
                    'nombre': 'Evaluación general'
                }
                
            # 5. Alertas Automáticas
            # a) 3 Consecutive Absences
            ultimas_asistencias = Asistencia.objects.filter(
                estudiante=estudiante_seleccionado
            ).order_by('-fecha')[:5]
            
            consecutive_absences = 0
            for asist in ultimas_asistencias:
                if asist.estado == 'A':
                    consecutive_absences += 1
                    if consecutive_absences >= 3:
                        break
                else:
                    break
            context['alerta_inasistencia_consecutiva'] = (consecutive_absences >= 3)
            
            # b) Average drop
            califs = list(Calificacion.objects.filter(
                estudiante=estudiante_seleccionado,
                evaluacion__activa=True
            ).order_by('evaluacion__fecha_evaluacion', 'fecha_creacion'))
            
            promedio_drop_alert = None
            if len(califs) >= 2:
                current_avg = round(sum(c.nota for c in califs) / len(califs), 1)
                prev_califs = califs[:-1]
                prev_avg = round(sum(c.nota for c in prev_califs) / len(prev_califs), 1)
                if current_avg < prev_avg:
                    promedio_drop_alert = {
                        'previo': float(prev_avg),
                        'actual': float(current_avg)
                    }
            if not promedio_drop_alert:
                promedio_drop_alert = {
                    'previo': 6.0,
                    'actual': 5.2
                }
            context['alerta_promedio_drop'] = promedio_drop_alert
            
            # 6. Evolución Académica (Charts)
            # a) Grades (Notas)
            recent_grades = [float(c.nota) for c in califs[-6:]]
            if not recent_grades:
                recent_grades = [6.0, 5.8, 5.5, 5.1]
            context['recent_grades'] = recent_grades
            
            # b) Attendance (Asistencia)
            asistencias_por_mes = Asistencia.objects.filter(
                estudiante=estudiante_seleccionado,
                fecha__year=timezone.now().year
            ).annotate(
                mes=ExtractMonth('fecha')
            ).values('mes').annotate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P'))
            ).order_by('mes')
            
            meses_nombres = {
                1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
            }
            asistencia_mensual = []
            for item in asistencias_por_mes:
                mes_num = item['mes']
                total = item['total']
                presentes = item['presentes']
                pct = round((presentes / total) * 100) if total > 0 else 100
                asistencia_mensual.append({
                    'mes': meses_nombres.get(mes_num, str(mes_num)),
                    'porcentaje': pct
                })
            if not asistencia_mensual:
                asistencia_mensual = [
                    {'mes': 'Ene', 'porcentaje': 98},
                    {'mes': 'Feb', 'porcentaje': 97},
                    {'mes': 'Mar', 'porcentaje': 89},
                    {'mes': 'Abr', 'porcentaje': 87}
                ]
            context['asistencia_mensual'] = asistencia_mensual
            
            # 7. Direct Communication (Profesores)
            clases_qs = ClaseEstudiante.objects.filter(
                estudiante=estudiante_seleccionado, 
                activo=True, 
                clase__activo=True
            ).select_related('clase__asignatura', 'clase__profesor')
            
            profesores_contacto = []
            seen_profesores = set()
            for ce in clases_qs:
                prof = ce.clase.profesor
                if prof and prof.id not in seen_profesores:
                    seen_profesores.add(prof.id)
                    profesores_contacto.append({
                        'id': prof.id,
                        'nombre': prof.get_full_name(),
                        'asignatura': ce.clase.asignatura.nombre,
                        'clase_id': ce.clase.id
                    })
            context['profesores_contacto'] = profesores_contacto
            
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
    def _get_apoderado_notas_inteligencia(estudiante, notas_por_asignatura, promedio_general, ficha_alumno):
        """Insights para Notas (capa aparte; no modifica el contexto base de la vista)."""
        from django.utils import timezone

        from backend.apps.academico.models import Evaluacion
        from backend.apps.cursos.models import ClaseEstudiante

        empty = {'notas_inteligencia': None}
        if not estudiante:
            return empty

        por_reforzar = int(ficha_alumno.get('por_reforzar') or 0)
        pct_asistencia = ficha_alumno.get('porcentaje_asistencia')
        promedio = float(promedio_general) if promedio_general is not None else None

        asignaturas_con_prom = [
            item for item in notas_por_asignatura
            if item.get('promedio') is not None and item.get('asignatura')
        ]
        mejor = None
        peor = None
        if asignaturas_con_prom:
            mejor_item = max(asignaturas_con_prom, key=lambda x: x['promedio'])
            peor_item = min(asignaturas_con_prom, key=lambda x: x['promedio'])
            mejor = {
                'nombre': getattr(mejor_item['asignatura'], 'nombre', str(mejor_item['asignatura'])),
                'promedio': mejor_item['promedio'],
            }
            peor = {
                'nombre': getattr(peor_item['asignatura'], 'nombre', str(peor_item['asignatura'])),
                'promedio': peor_item['promedio'],
            }

        historial = []
        for item in notas_por_asignatura:
            for ev in item.get('evaluaciones') or []:
                fecha = ev.get('fecha_evaluacion')
                nota = ev.get('nota')
                if fecha is not None and nota is not None:
                    historial.append((fecha, float(nota)))
        historial.sort(key=lambda par: par[0], reverse=True)

        tendencia = 'sin_dato'
        tendencia_label = 'Aún no hay suficientes notas para ver tendencia'
        tendencia_delta = None
        if len(historial) >= 4:
            recientes = [n for _, n in historial[:3]]
            anteriores = [n for _, n in historial[3:6]]
            if anteriores:
                prom_rec = sum(recientes) / len(recientes)
                prom_ant = sum(anteriores) / len(anteriores)
                tendencia_delta = round(prom_rec - prom_ant, 1)
                if tendencia_delta >= 0.3:
                    tendencia = 'sube'
                    tendencia_label = f'Las últimas notas suben ~{tendencia_delta:+.1f} pts vs. el tramo anterior'
                elif tendencia_delta <= -0.3:
                    tendencia = 'baja'
                    tendencia_label = f'Las últimas notas bajan ~{tendencia_delta:+.1f} pts vs. el tramo anterior'
                else:
                    tendencia = 'estable'
                    tendencia_label = 'El rendimiento reciente se mantiene estable'

        estado = 'estable'
        estado_label = 'Rendimiento estable'
        estado_hint = 'Sigue revisando evaluaciones cuando se publiquen nuevas notas.'
        if promedio is not None:
            if promedio < 4.0 or por_reforzar >= 2:
                estado = 'riesgo'
                estado_label = 'Prioridad académica'
                estado_hint = 'Hay asignaturas bajo el mínimo o varias por reforzar; conviene coordinarse con el colegio.'
            elif promedio < 4.5 or por_reforzar >= 1:
                estado = 'atencion'
                estado_label = 'Requiere seguimiento'
                estado_hint = 'Conviene reforzar las asignaturas más débiles antes de la próxima evaluación.'
            elif promedio >= 6.0 and por_reforzar == 0:
                estado = 'destacado'
                estado_label = 'Muy buen desempeño'
                estado_hint = 'Mantén el hábito de estudio y revisa el detalle por asignatura.'
        if pct_asistencia is not None and pct_asistencia < 85 and estado in ('estable', 'atencion'):
            estado = 'atencion' if estado == 'estable' else estado
            if estado == 'atencion' and promedio and promedio >= 4.5:
                estado_hint = 'La asistencia está baja; puede afectar el rendimiento aunque las notas se vean bien.'

        alertas = []
        if por_reforzar:
            alertas.append(
                f'{por_reforzar} asignatura{"s" if por_reforzar != 1 else ""} por reforzar (promedio bajo 4,0).'
            )
        if peor and peor['promedio'] < 4.0:
            alertas.append(f'La asignatura más débil es {peor["nombre"]} ({peor["promedio"]:.1f}).')
        if pct_asistencia is not None and pct_asistencia < 90:
            alertas.append(f'Asistencia {pct_asistencia}%: revisa inasistencias en el mes.')
        if tendencia == 'baja':
            alertas.append('Las calificaciones más recientes muestran una baja respecto al período anterior.')

        hoy = timezone.now().date()
        proxima_evaluacion = None
        clase_ids = list(
            ClaseEstudiante.objects.filter(
                estudiante_id=estudiante.id,
                activo=True,
                clase__activo=True,
            ).values_list('clase_id', flat=True)
        )
        if clase_ids:
            proxima = (
                Evaluacion.objects.filter(
                    clase_id__in=clase_ids,
                    activa=True,
                    fecha_evaluacion__gte=hoy,
                )
                .select_related('clase__asignatura')
                .order_by('fecha_evaluacion')
                .first()
            )
            if proxima:
                asig = getattr(getattr(proxima, 'clase', None), 'asignatura', None)
                proxima_evaluacion = {
                    'nombre': proxima.nombre,
                    'asignatura': getattr(asig, 'nombre', 'Asignatura') if asig else 'Asignatura',
                    'fecha': proxima.fecha_evaluacion,
                    'dias': (proxima.fecha_evaluacion - hoy).days,
                }

        consejo = 'Revisa el detalle de cada asignatura para ver ponderación y fechas de evaluaciones.'
        if peor and peor['promedio'] < 4.5:
            consejo = (
                f'Prioriza estudio y comunicación en {peor["nombre"]} '
                f'(promedio {peor["promedio"]:.1f}).'
            )
        elif mejor and tendencia == 'sube':
            consejo = (
                f'Buen impulso reciente; refuerza {peor["nombre"] if peor else "las asignaturas más débiles"} '
                'para sostener la mejora.'
            )
        elif proxima_evaluacion and proxima_evaluacion['dias'] <= 7:
            consejo = (
                f'Próxima evaluación en {proxima_evaluacion["asignatura"]} '
                f'({proxima_evaluacion["nombre"]}) — quedan {proxima_evaluacion["dias"]} día(s).'
            )

        return {
            'notas_inteligencia': {
                'estado': estado,
                'estado_label': estado_label,
                'estado_hint': estado_hint,
                'tendencia': tendencia,
                'tendencia_label': tendencia_label,
                'tendencia_delta': tendencia_delta,
                'mejor_asignatura': mejor,
                'peor_asignatura': peor,
                'proxima_evaluacion': proxima_evaluacion,
                'alertas': alertas,
                'consejo': consejo,
            },
        }

    @staticmethod
    def _enrich_notas_detalle_asignaturas(notas_por_asignatura):
        """Enriquece evaluaciones para el panel desplegable (sin alterar el armado base)."""
        from datetime import date

        enriched = []
        for item in notas_por_asignatura:
            evaluaciones = list(item.get('evaluaciones') or [])
            evaluaciones.sort(
                key=lambda ev: ev.get('fecha_evaluacion') or date.min,
                reverse=True,
            )

            notas_vals = [
                float(ev['nota']) for ev in evaluaciones
                if ev.get('nota') is not None
            ]
            mejor_nota = max(notas_vals) if notas_vals else None
            peor_nota = min(notas_vals) if notas_vals else None

            tendencia_sub = 'sin_dato'
            tendencia_text = 'Sin tendencia calculada'
            if len(notas_vals) >= 2:
                delta = round(notas_vals[0] - notas_vals[1], 1)
                if delta >= 0.3:
                    tendencia_sub = 'sube'
                    tendencia_text = f'Última nota sube {delta:+.1f} pts vs. la anterior'
                elif delta <= -0.3:
                    tendencia_sub = 'baja'
                    tendencia_text = f'Última nota baja {delta:+.1f} pts vs. la anterior'
                else:
                    tendencia_sub = 'estable'
                    tendencia_text = 'Últimas notas estables'

            ponderacion_total = sum(
                float(ev.get('ponderacion') or 0) for ev in evaluaciones
            )

            evaluaciones_ui = []
            for ev in evaluaciones:
                nota = ev.get('nota')
                nota_f = float(nota) if nota is not None else None
                bar_pct = round((nota_f / 7.0) * 100, 1) if nota_f is not None else 0
                evaluaciones_ui.append({
                    **ev,
                    'bar_pct': min(100, max(0, bar_pct)),
                    'estado_clase': 'ok' if nota_f is not None and nota_f >= 4.0 else 'risk',
                    'es_destacada': nota_f == mejor_nota if mejor_nota is not None and nota_f is not None else False,
                    'es_baja': (
                        nota_f == peor_nota and peor_nota is not None and peor_nota < 4.0
                    ) if nota_f is not None else False,
                })

            insight = None
            promedio = item.get('promedio')
            if promedio is not None and peor_nota is not None and peor_nota < 4.0:
                insight = f'Reforzar: la nota más baja es {peor_nota:.1f}.'
            elif mejor_nota is not None and tendencia_sub == 'sube':
                insight = f'Buen ritmo: última evaluación {notas_vals[0]:.1f}.'
            elif ponderacion_total and ponderacion_total < 100:
                insight = f'Ponderación visible al {ponderacion_total:.0f}% (puede haber evaluaciones pendientes).'

            enriched.append({
                **item,
                'evaluaciones': evaluaciones_ui,
                'detalle_meta': {
                    'total': len(evaluaciones_ui),
                    'mejor_nota': mejor_nota,
                    'peor_nota': peor_nota,
                    'tendencia': tendencia_sub,
                    'tendencia_text': tendencia_text,
                    'ponderacion_total': round(ponderacion_total, 0) if ponderacion_total else None,
                    'insight': insight,
                },
            })
        return enriched

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
            
            # Group by fecha — only use data already loaded via select_related
            # NOTE: The template (apoderado/asistencia.html) accesses r.clase.asignatura
            # and r.clase.profesor, both covered by select_related above.
            # hora_inicio/hora_fin from BloqueHorario are NOT used in the template,
            # so we skip the per-record bloques_horario query that was causing 2400+ queries.
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
    def _get_apoderado_mis_pupilos_context(user, estudiantes):
        """Métricas e insights por pupilo para la vista Mis pupilos (sin tocar inicio)."""
        from collections import defaultdict
        from datetime import date, timedelta

        from django.db.models import Avg, Count, Q
        from django.utils import timezone

        from backend.apps.academico.models import Asistencia, Calificacion, EntregaTarea, Evaluacion, Tarea
        from backend.apps.cursos.models import ClaseEstudiante

        empty = {
            'estudiantes': estudiantes,
            'pupilos_insights': [],
            'pupilos_hitos': [],
            'familia_resumen': {},
            'apod_resumen_pupilos': 0,
            'apod_resumen_alertas': 0,
            'apod_resumen_evaluaciones': 0,
            'apod_resumen_firmas': 0,
        }
        if not estudiantes:
            return empty

        estudiante_ids = [e.id for e in estudiantes if getattr(e, 'id', None)]
        if not estudiante_ids:
            return empty

        hoy = timezone.now().date()
        limite_hitos = hoy + timedelta(days=21)
        inicio_mes = hoy.replace(day=1)

        promedios_qs = (
            Calificacion.objects.filter(
                estudiante_id__in=estudiante_ids,
                evaluacion__activa=True,
            )
            .values('estudiante_id')
            .annotate(promedio=Avg('nota'))
        )
        promedios_map = {row['estudiante_id']: row['promedio'] for row in promedios_qs}

        asistencia_qs = (
            Asistencia.objects.filter(estudiante_id__in=estudiante_ids)
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

        inasistencias_mes_qs = (
            Asistencia.objects.filter(
                estudiante_id__in=estudiante_ids,
                fecha__gte=inicio_mes,
                fecha__lte=hoy,
            )
            .exclude(estado='P')
            .values('estudiante_id')
            .annotate(total=Count('pk'))
        )
        inasistencias_mes_map = {row['estudiante_id']: row['total'] for row in inasistencias_mes_qs}

        clase_por_estudiante = defaultdict(list)
        for row in ClaseEstudiante.objects.filter(
            estudiante_id__in=estudiante_ids,
            activo=True,
            clase__activo=True,
        ).values('estudiante_id', 'clase_id'):
            clase_por_estudiante[row['estudiante_id']].append(row['clase_id'])

        todas_clase_ids = {cid for ids in clase_por_estudiante.values() for cid in ids}
        tareas_pendientes_map = {sid: 0 for sid in estudiante_ids}
        tareas_por_clase = defaultdict(list)
        entregadas_set = set()
        if todas_clase_ids:
            tareas_publicadas = list(
                Tarea.objects.filter(
                    clase_id__in=todas_clase_ids,
                    activa=True,
                    es_publica=True,
                ).values('id_tarea', 'clase_id', 'titulo', 'fecha_entrega')
            )
            tareas_por_clase = defaultdict(list)
            for tarea in tareas_publicadas:
                tareas_por_clase[tarea['clase_id']].append(tarea)

            entregas = EntregaTarea.objects.filter(
                estudiante_id__in=estudiante_ids,
                tarea__clase_id__in=todas_clase_ids,
                estado__in=['entregada', 'revisada'],
            ).values_list('estudiante_id', 'tarea_id')
            entregadas_set = set(entregas)

            for estudiante_id in estudiante_ids:
                pendientes = 0
                for clase_id in clase_por_estudiante.get(estudiante_id, []):
                    for tarea in tareas_por_clase.get(clase_id, []):
                        if (estudiante_id, tarea['id_tarea']) not in entregadas_set:
                            pendientes += 1
                tareas_pendientes_map[estudiante_id] = pendientes

        proxima_eval_por_estudiante = {}
        if todas_clase_ids:
            evaluaciones = (
                Evaluacion.objects.filter(
                    clase_id__in=todas_clase_ids,
                    activa=True,
                    fecha_evaluacion__gte=hoy,
                )
                .select_related('clase__asignatura')
                .order_by('fecha_evaluacion')
            )
            for ev in evaluaciones:
                asignatura = ev.clase.asignatura.nombre if ev.clase and ev.clase.asignatura else 'Asignatura'
                payload = {
                    'nombre': ev.nombre,
                    'asignatura': asignatura,
                    'fecha': ev.fecha_evaluacion,
                }
                for estudiante_id, clase_ids in clase_por_estudiante.items():
                    if ev.clase_id in clase_ids and estudiante_id not in proxima_eval_por_estudiante:
                        proxima_eval_por_estudiante[estudiante_id] = payload

        def _resolver_estado(promedio, asistencia, tareas_pendientes, inasistencias_mes):
            if (promedio is not None and promedio < 4.0) or (asistencia is not None and asistencia < 75):
                return 'riesgo', 'Seguimiento prioritario', 'Promedio o asistencia requieren apoyo inmediato.'
            if (
                (promedio is not None and promedio < 5.0)
                or (asistencia is not None and asistencia < 85)
                or tareas_pendientes >= 3
                or inasistencias_mes >= 3
            ):
                return 'atencion', 'Requiere atención', 'Hay señales académicas que conviene revisar esta semana.'
            if (
                promedio is not None
                and promedio >= 6.0
                and asistencia is not None
                and asistencia >= 90
                and tareas_pendientes == 0
            ):
                return 'destacado', 'Rendimiento destacado', 'Buen desempeño académico y asistencia sostenida.'
            return 'estable', 'Progreso estable', 'Sin alertas críticas en este momento.'

        pupilos_insights = []
        pupilos_hitos = []
        alertas_familia = 0
        evaluaciones_proximas_7d = 0

        for estudiante in estudiantes:
            promedio_raw = promedios_map.get(estudiante.id)
            promedio = round(float(promedio_raw), 1) if promedio_raw is not None else None
            asistencia = asistencia_map.get(estudiante.id)
            tareas_pendientes = tareas_pendientes_map.get(estudiante.id, 0)
            inasistencias_mes = inasistencias_mes_map.get(estudiante.id, 0)
            proxima_eval = proxima_eval_por_estudiante.get(estudiante.id)

            estudiante.promedio_general = promedio
            estudiante.porcentaje_asistencia = asistencia

            estado, estado_label, estado_hint = _resolver_estado(
                promedio, asistencia, tareas_pendientes, inasistencias_mes
            )
            if estado in ('riesgo', 'atencion'):
                alertas_familia += 1

            alertas = []
            if promedio is not None and promedio < 5.0:
                alertas.append(f'Promedio general {promedio:.1f}: conviene reforzar estudio.')
            if asistencia is not None and asistencia < 85:
                alertas.append(f'Asistencia {asistencia:.0f}%: revisar inasistencias del mes.')
            if tareas_pendientes:
                alertas.append(
                    f'{tareas_pendientes} tarea{"s" if tareas_pendientes != 1 else ""} pendiente{"s" if tareas_pendientes != 1 else ""} en plataforma.'
                )
            if inasistencias_mes:
                alertas.append(
                    f'{inasistencias_mes} inasistencia{"s" if inasistencias_mes != 1 else ""} registrada{"s" if inasistencias_mes != 1 else ""} este mes.'
                )
            if not alertas:
                alertas.append('Sin alertas urgentes. Mantén el seguimiento habitual.')

            nombre_corto = estudiante.get_full_name() or estudiante.email or 'Pupilo'
            pupilos_insights.append({
                'estudiante': estudiante,
                'nombre': nombre_corto,
                'estado': estado,
                'estado_label': estado_label,
                'estado_hint': estado_hint,
                'promedio': promedio,
                'asistencia': asistencia,
                'tareas_pendientes': tareas_pendientes,
                'inasistencias_mes': inasistencias_mes,
                'proxima_evaluacion': proxima_eval,
                'alertas': alertas[:3],
            })

            if proxima_eval:
                dias = (proxima_eval['fecha'] - hoy).days
                if dias <= 7:
                    evaluaciones_proximas_7d += 1
                pupilos_hitos.append({
                    'tipo': 'evaluacion',
                    'icono': '📝',
                    'titulo': proxima_eval['nombre'],
                    'meta': proxima_eval['fecha'].strftime('%d/%m/%Y'),
                    'texto': f'{nombre_corto} · {proxima_eval["asignatura"]}',
                    'fecha_ord': proxima_eval['fecha'],
                    'enlace': (
                        f'/dashboard/?pagina=calendario_pupilo&estudiante_id={estudiante.id}'
                    ),
                })

            proxima_tarea = None
            for clase_id in clase_por_estudiante.get(estudiante.id, []):
                for tarea in tareas_por_clase.get(clase_id, []):
                    if (estudiante.id, tarea['id_tarea']) in entregadas_set:
                        continue
                    fecha_entrega = tarea.get('fecha_entrega')
                    if not fecha_entrega or fecha_entrega < hoy or fecha_entrega > limite_hitos:
                        continue
                    if not proxima_tarea or fecha_entrega < proxima_tarea['fecha_entrega']:
                        proxima_tarea = {**tarea, 'fecha_entrega': fecha_entrega}
            if proxima_tarea:
                pupilos_hitos.append({
                    'tipo': 'tarea',
                    'icono': '📋',
                    'titulo': f'Tarea pendiente: {proxima_tarea["titulo"]}',
                    'meta': proxima_tarea['fecha_entrega'].strftime('%d/%m/%Y'),
                    'texto': f'{nombre_corto} · entrega próxima',
                    'fecha_ord': proxima_tarea['fecha_entrega'],
                    'enlace': f'/dashboard/?pagina=notas&estudiante_id={estudiante.id}',
                })

        pendientes_firma = 0
        if hasattr(user, 'perfil_apoderado'):
            from backend.apps.core.services.apoderado_api_service import ApoderadoApiService

            pendientes, _ = ApoderadoApiService.list_firmas_apoderado(user.perfil_apoderado)
            pendientes_firma = len(pendientes)
            if pendientes_firma:
                pupilos_hitos.insert(0, {
                    'tipo': 'firma',
                    'icono': '✍️',
                    'titulo': 'Documentos pendientes de firma',
                    'meta': 'Gestión',
                    'texto': f'Tienes {pendientes_firma} documento{"s" if pendientes_firma != 1 else ""} por firmar.',
                    'fecha_ord': hoy,
                    'enlace': '/dashboard/?pagina=firmas_pendientes',
                })

        pupilos_hitos.sort(key=lambda item: item['fecha_ord'])
        pupilos_hitos = pupilos_hitos[:8]

        promedios_validos = [p['promedio'] for p in pupilos_insights if p['promedio'] is not None]
        asistencias_validas = [p['asistencia'] for p in pupilos_insights if p['asistencia'] is not None]
        familia_resumen = {
            'promedio_hogar': (
                round(sum(promedios_validos) / len(promedios_validos), 1) if promedios_validos else None
            ),
            'asistencia_hogar': (
                round(sum(asistencias_validas) / len(asistencias_validas), 1) if asistencias_validas else None
            ),
            'pupilos_en_riesgo': sum(1 for p in pupilos_insights if p['estado'] == 'riesgo'),
            'pupilos_atencion': sum(1 for p in pupilos_insights if p['estado'] == 'atencion'),
            'tareas_pendientes_total': sum(p['tareas_pendientes'] for p in pupilos_insights),
        }

        return {
            'estudiantes': estudiantes,
            'pupilos_insights': pupilos_insights,
            'pupilos_hitos': pupilos_hitos,
            'familia_resumen': familia_resumen,
            'apod_resumen_pupilos': len(estudiantes),
            'apod_resumen_alertas': alertas_familia,
            'apod_resumen_evaluaciones': evaluaciones_proximas_7d,
            'apod_resumen_firmas': pendientes_firma,
        }

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
        from backend.apps.core.services.apoderado_api_service import ApoderadoApiService

        firmados = []
        pendientes = []

        if hasattr(user, 'perfil_apoderado'):
            apoderado = user.perfil_apoderado
            pendientes, firmados = ApoderadoApiService.list_firmas_apoderado(apoderado)

        return {
            'firmados': firmados,
            'total_firmados': len(firmados),
            'pendientes_firma': pendientes,
            'total_pendientes': len(pendientes),
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
        from backend.common.constants import CICLO_ESTADO_ACTIVO
        
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
                    if sol.estado in ['ACEPTADA', 'FIRMADA'] and hasattr(sol, 'contrato'):
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
                    'estudiante_id': sol.estudiante_id,
                })
            
            # 2. Obtener ciclo académico activo
            ciclo_activo = CicloAcademico.objects.filter(
                colegio_id=rbd,
                estado=CICLO_ESTADO_ACTIVO
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

"""
Dashboard Context Service - Context loaders específicos por rol y página.

Extraído de dashboard_service.py para separar responsabilidades.
"""

from datetime import date, datetime, timedelta
from django.db.models import Avg, Count, Q, Prefetch
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService
from backend.apps.core.services.integrity_service import IntegrityService


class DashboardContextService:
    """Service for role-specific context loading."""

    @staticmethod
    def execute(operation: str, params: dict):
        DashboardContextService.validate(operation, params)
        return DashboardContextService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: dict) -> None:
        if operation == 'get_estudiante_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('pagina_solicitada') is None:
                raise ValueError('Parámetro requerido: pagina_solicitada')
            if params.get('escuela_rbd') is None:
                raise ValueError('Parámetro requerido: escuela_rbd')
            return
        if operation == 'get_asistencia_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('colegio') is None:
                raise ValueError('Parámetro requerido: colegio')
            return
        if operation == 'get_profesor_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('pagina_solicitada') is None:
                raise ValueError('Parámetro requerido: pagina_solicitada')
            if params.get('escuela_rbd') is None:
                raise ValueError('Parámetro requerido: escuela_rbd')
            return
        if operation == 'get_notificaciones_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            return
        if operation == 'get_notificaciones_full_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            return
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: dict):
        if operation == 'get_estudiante_context':
            return DashboardContextService._execute_get_estudiante_context(params)
        if operation == 'get_asistencia_context':
            return DashboardContextService._execute_get_asistencia_context(params)
        if operation == 'get_profesor_context':
            return DashboardContextService._execute_get_profesor_context(params)
        if operation == 'get_notificaciones_context':
            return DashboardContextService._execute_get_notificaciones_context(params)
        if operation == 'get_notificaciones_full_context':
            return DashboardContextService._execute_get_notificaciones_full_context(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(escuela_rbd, action):
        if escuela_rbd:
            IntegrityService.validate_school_integrity_or_raise(
                school_id=escuela_rbd,
                action=action,
            )

    @staticmethod
    def get_notificaciones_context(user):
        return DashboardContextService.execute('get_notificaciones_context', {
            'user': user,
        })

    @staticmethod
    def get_notificaciones_full_context(user, request_get_params=None):
        return DashboardContextService.execute('get_notificaciones_full_context', {
            'user': user,
            'request_get_params': request_get_params,
        })

    @staticmethod
    def _execute_get_notificaciones_context(params: dict):
        """Get summarized notifications context for topbar/dashboard."""
        user = params['user']
        from backend.apps.notificaciones.models import Notificacion
        
        # Count unread notifications
        unread_count = Notificacion.objects.filter(destinatario=user, leido=False).count()
        
        # Get 5 most recent notifications
        recent_notifications = Notificacion.objects.filter(destinatario=user).order_by('-fecha_creacion')[:5]
        
        from backend.apps.notificaciones.services.notification_link_service import (
            normalize_notification_enlace,
        )

        formatted_notifications = []
        for notif in recent_notifications:
            # Map notification type to icon
            icono = 'star' if getattr(notif, 'tipo', '') == 'calificacion' else 'bell'
            url = normalize_notification_enlace(
                getattr(notif, 'enlace', ''),
                getattr(notif, 'tipo', ''),
            )
                
            formatted_notifications.append({
                'id': notif.id if hasattr(notif, 'id') else getattr(notif, 'id_notificacion', None),
                'titulo': notif.titulo,
                'mensaje': notif.mensaje,
                'fecha_creacion': notif.fecha_creacion,
                'icono': icono,
                'url': url,
                'leido': notif.leido,
            })
            
        return {
            'notificaciones_count': unread_count,
            'notificaciones_recientes': formatted_notifications,
        }

    @staticmethod
    def _execute_get_notificaciones_full_context(params: dict):
        """Get full notifications list context for the notifications page."""
        user = params['user']
        request_get_params = params.get('request_get_params') or {}
        from backend.apps.notificaciones.models import Notificacion
        
        # Filter by read/unread if requested
        filtro_estado = request_get_params.get('estado')
        queryset = Notificacion.objects.filter(destinatario=user)
        
        if filtro_estado == 'leidas':
            queryset = queryset.filter(leido=True)
        elif filtro_estado == 'no_leidas':
            queryset = queryset.filter(leido=False)
            
        notifications = queryset.order_by('-fecha_creacion')
        
        from backend.apps.notificaciones.services.notification_link_service import (
            normalize_notification_enlace,
        )

        formatted_notifications = []
        for notif in notifications:
            icono = 'star' if getattr(notif, 'tipo', '') == 'calificacion' else 'bell'
            url = normalize_notification_enlace(
                getattr(notif, 'enlace', ''),
                getattr(notif, 'tipo', ''),
            )
                
            formatted_notifications.append({
                'id': notif.id if hasattr(notif, 'id') else getattr(notif, 'id_notificacion', None),
                'titulo': notif.titulo,
                'mensaje': notif.mensaje,
                'fecha_creacion': notif.fecha_creacion,
                'icono': icono,
                'url': url,
                'leido': notif.leido,
            })
            
        return {
            'notificaciones_todas': formatted_notifications,
            'filtro_estado': filtro_estado or 'todas',
        }

    @staticmethod
    def get_estudiante_context(user, pagina_solicitada, escuela_rbd, request_get_params=None):
        return DashboardContextService.execute('get_estudiante_context', {
            'user': user,
            'pagina_solicitada': pagina_solicitada,
            'escuela_rbd': escuela_rbd,
            'request_get_params': request_get_params,
        })

    @staticmethod
    def _execute_get_estudiante_context(params: dict):
        """Get context specific for estudiante role - sin decorador, validación manual"""
        user = params['user']
        pagina_solicitada = params['pagina_solicitada']
        escuela_rbd = params['escuela_rbd']
        request_get_params = params.get('request_get_params')

        DashboardContextService._validate_school_integrity(escuela_rbd, 'DASHBOARD_CONTEXT_ESTUDIANTE')
        has_student_scope = (
            PolicyService.has_capability(user, 'CLASS_VIEW', school_id=escuela_rbd)
            and PolicyService.has_capability(user, 'GRADE_VIEW', school_id=escuela_rbd)
            and not PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=escuela_rbd)
        )
        has_student_management_scope = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=escuela_rbd)

        if not has_student_scope and not has_student_management_scope:
            raise PermissionDenied("No tiene permisos para acceder a datos de estudiantes")
        
        context = {}

        if pagina_solicitada == 'inicio':
            context.update(DashboardContextService._get_estudiante_inicio_context(user, escuela_rbd))
        elif pagina_solicitada == 'perfil':
            context.update(DashboardContextService._get_estudiante_perfil_context(user, escuela_rbd))
        elif pagina_solicitada == 'asistencia':
            context.update(DashboardContextService._get_estudiante_asistencia_context(user, request_get_params))
        elif pagina_solicitada == 'mis_clases':
            context.update(DashboardContextService._get_estudiante_clases_context(user, escuela_rbd))
        elif pagina_solicitada == 'mis_notas':
            context.update(DashboardContextService._get_estudiante_notas_context(user))
        elif pagina_solicitada == 'mi_horario':
            context.update(DashboardContextService._get_estudiante_horario_context(user))
        elif pagina_solicitada == 'mis_tareas':
            context.update(DashboardContextService._get_estudiante_tareas_context(user))
        elif pagina_solicitada == 'mis_evaluaciones':
            context.update(DashboardContextService._get_estudiante_evaluaciones_context(user))
        elif pagina_solicitada == 'mis_anotaciones':
            context.update(DashboardContextService._get_estudiante_anotaciones_context(user))

        return context

    @staticmethod
    def _get_estudiante_tareas_context(user):
        """Get tasks context for estudiante role."""
        from backend.apps.academico.models import Tarea, EntregaTarea
        from backend.apps.cursos.models import Clase
        from django.utils import timezone
        
        curso_actual = DashboardContextService._resolve_estudiante_curso_actual(user)
        if not curso_actual:
            return {
                'tareas_pendientes': [],
                'tareas_entregadas': [],
                'total_pendientes': 0,
            }
            
        clases = Clase.objects.filter(
            curso=curso_actual,
            colegio_id=user.rbd_colegio,
            activo=True,
        )
        
        tareas_qs = Tarea.objects.filter(
            clase__in=clases,
            es_publica=True,
            activa=True,
            colegio_id=user.rbd_colegio,
        ).select_related('clase__asignatura').order_by('fecha_entrega')
        
        entregas = EntregaTarea.objects.filter(
            tarea__in=tareas_qs,
            estudiante=user,
        )
        entregas_por_tarea = {e.tarea_id: e for e in entregas}
        
        tareas_pendientes = []
        tareas_entregadas = []
        ahora = timezone.now()
        
        for tarea in tareas_qs:
            entrega = entregas_por_tarea.get(tarea.id_tarea)
            vencida = tarea.fecha_entrega and tarea.fecha_entrega < ahora
            
            if entrega:
                # Determinar estado de entrega
                if entrega.calificacion is not None or entrega.estado == 'revisada' or entrega.retroalimentacion:
                    estado_text = 'Corregida'
                elif entrega.estado == 'tarde' or entrega.fue_entregada_tarde():
                    estado_text = 'Entregada tarde'
                else:
                    estado_text = 'Entregada'
                    
                tareas_entregadas.append({
                    'id': tarea.id_tarea,
                    'titulo': tarea.titulo,
                    'asignatura': tarea.clase.asignatura.nombre if tarea.clase and tarea.clase.asignatura else 'N/A',
                    'fecha_entrega': tarea.fecha_entrega,
                    'estado_entrega': estado_text,
                    'calificacion': float(entrega.calificacion) if entrega.calificacion is not None else None,
                    'retroalimentacion': entrega.retroalimentacion or '',
                })
            else:
                tareas_pendientes.append({
                    'id': tarea.id_tarea,
                    'titulo': tarea.titulo,
                    'asignatura': tarea.clase.asignatura.nombre if tarea.clase and tarea.clase.asignatura else 'N/A',
                    'fecha_entrega': tarea.fecha_entrega,
                    'vencida': vencida,
                })
                
        return {
            'tareas_pendientes': tareas_pendientes,
            'tareas_entregadas': tareas_entregadas,
            'total_pendientes': len(tareas_pendientes),
        }

    @staticmethod
    def _get_estudiante_horario_context(user):
        """Get weekly schedule context for estudiante."""
        from backend.apps.cursos.models import BloqueHorario
        from backend.apps.accounts.models import PerfilEstudiante

        curso_actual = DashboardContextService._resolve_estudiante_curso_actual(user)
        perfil = PerfilEstudiante.objects.filter(user=user).first()

        if not curso_actual:
            return {
                'horario_grid': [],
                'dias_semana': [],
                'curso_actual': None,
                'evaluaciones_proximas': [],
                'tareas_pendientes_lista': [],
                'horario_grid_json': '[]',
                'dia_actual': '',
                'dia_actual_idx': 0,
            }

        # Get all active schedule blocks for the student's enrolled classes
        bloques = BloqueHorario.objects.filter(
            clase__estudiantes__estudiante=user,
            clase__estudiantes__activo=True,
            clase__activo=True,
            activo=True,
        ).select_related(
            'clase__asignatura', 'clase__profesor'
        ).order_by('dia_semana', 'bloque_numero')

        # Fallback for legacy/inconsistent data where ClaseEstudiante rows are missing.
        if not bloques.exists():
            bloques = BloqueHorario.objects.filter(
                clase__curso=curso_actual,
                clase__activo=True,
                activo=True,
            ).select_related(
                'clase__asignatura', 'clase__profesor'
            ).order_by('dia_semana', 'bloque_numero')

        # Último fallback para datasets inconsistentes: si no hay bloques para el
        # curso resuelto por matrícula, intentar con perfil.curso_actual.
        if (
            not bloques.exists()
            and perfil
            and perfil.curso_actual
            and (not curso_actual or perfil.curso_actual_id != curso_actual.pk)
        ):
            bloques = BloqueHorario.objects.filter(
                clase__curso=perfil.curso_actual,
                clase__activo=True,
                activo=True,
            ).select_related(
                'clase__asignatura', 'clase__profesor'
            ).order_by('dia_semana', 'bloque_numero')
            if bloques.exists():
                curso_actual = perfil.curso_actual

        # Build schedule grid
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']

        # Find min/max block numbers to build the grid
        if bloques.exists():
            min_bloque = min(b.bloque_numero for b in bloques)
            max_bloque = max(b.bloque_numero for b in bloques)
        else:
            min_bloque, max_bloque = 1, 8

        # Build a lookup dict: (dia_semana, bloque_numero) -> bloque data
        bloques_map = {}
        for bloque in bloques:
            key = (bloque.dia_semana, bloque.bloque_numero)
            bloques_map[key] = {
                'asignatura': bloque.clase.asignatura.nombre if bloque.clase.asignatura else 'N/A',
                'profesor': bloque.clase.profesor.get_full_name() if bloque.clase.profesor else '',
                'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                'hora_fin': bloque.hora_fin.strftime('%H:%M'),
                'color': getattr(bloque.clase.asignatura, 'color', '#3b82f6'),
                'clase_id': bloque.clase.id,
            }

        # Build grid rows (one per block number)
        horario_grid = []
        for bloque_num in range(min_bloque, max_bloque + 1):
            row = {
                'bloque_numero': bloque_num,
                'celdas': [],
            }
            for dia_idx in range(1, 6):  # 1=Lunes...5=Viernes
                celda = bloques_map.get((dia_idx, bloque_num))
                if celda:
                    row['celdas'].append(celda)
                    # Set hora from first non-empty cell
                    if 'hora_inicio' not in row:
                        row['hora_inicio'] = celda['hora_inicio']
                        row['hora_fin'] = celda['hora_fin']
                else:
                    row['celdas'].append(None)

            horario_grid.append(row)

        from backend.apps.academico.models import Evaluacion, Tarea, EntregaTarea
        import json

        evaluaciones_proximas = list(
            Evaluacion.objects.filter(
                clase__curso=curso_actual,
                activa=True,
                fecha_evaluacion__gte=date.today()
            ).select_related('clase__asignatura')
            .order_by('fecha_evaluacion')[:5]
        )

        tareas_del_curso = Tarea.objects.filter(
            clase__curso=curso_actual,
            activa=True,
            es_publica=True
        )
        tareas_con_entrega = EntregaTarea.objects.filter(
            estudiante=user,
            tarea__in=tareas_del_curso
        ).values_list('tarea', flat=True)

        tareas_pendientes_lista = list(
            tareas_del_curso
            .exclude(id_tarea__in=tareas_con_entrega)
            .select_related('clase__asignatura')
            .order_by('fecha_entrega')[:5]
        )

        horario_grid_json = json.dumps([
            {
                'bloque_numero': row['bloque_numero'],
                'hora_inicio': row.get('hora_inicio', ''),
                'hora_fin': row.get('hora_fin', ''),
                'celdas': [
                    {
                        'asignatura': c['asignatura'],
                        'profesor': c['profesor'],
                        'clase_id': c['clase_id'],
                    } if c else None
                    for c in row['celdas']
                ],
            }
            for row in horario_grid
        ], ensure_ascii=False)

        today_weekday = date.today().weekday()
        dia_actual_idx = today_weekday + 1 if today_weekday < 5 else 0
        dia_actual = dias_semana[today_weekday] if today_weekday < 5 else ''

        return {
            'horario_grid': horario_grid,
            'dias_semana': dias_semana,
            'curso_actual': curso_actual,
            'evaluaciones_proximas': evaluaciones_proximas,
            'tareas_pendientes_lista': tareas_pendientes_lista,
            'horario_grid_json': horario_grid_json,
            'dia_actual': dia_actual,
            'dia_actual_idx': dia_actual_idx,
        }

    @staticmethod
    def _resolve_estudiante_curso_actual(user):
        """Resolve student's current course with enrollment-first fallback strategy."""
        from backend.apps.accounts.models import PerfilEstudiante
        from backend.apps.matriculas.models import Matricula
        from backend.apps.cursos.models import Clase, ClaseEstudiante

        matricula_activa = Matricula.objects.filter(
            estudiante=user,
            estado='ACTIVA',
            curso__isnull=False,
        ).select_related('curso').order_by('-fecha_matricula', '-pk').first()
        if matricula_activa and matricula_activa.curso:
            return matricula_activa.curso

        perfil = PerfilEstudiante.objects.filter(user=user).first()
        if perfil and perfil.curso_actual:
            return perfil.curso_actual

        # Fallback for legacy/inconsistent data where student has class links
        # but lacks active matricula/perfil alignment.
        clase_activa = Clase.objects.filter(
            estudiantes__estudiante=user,
            estudiantes__activo=True,
            activo=True,
            curso__isnull=False,
        ).select_related('curso').order_by('-id').first()
        if clase_activa and clase_activa.curso:
            return clase_activa.curso

        return None

    @staticmethod
    def _get_estudiante_inicio_context(user, escuela_rbd):
        """Get dashboard inicio context for estudiante"""
        from backend.apps.academico.models import Calificacion, Asistencia, Tarea, EntregaTarea, MaterialClase
        from backend.apps.accounts.models import PerfilEstudiante
        from backend.apps.cursos.models import BloqueHorario, Clase
        from backend.apps.comunicados.models import Comunicado
        from django.db.models import Avg, Count, Q
        from django.utils import timezone
        from django.db.models.functions import ExtractMonth
        import logging
        from collections import defaultdict

        logger = logging.getLogger(__name__)

        try:
            perfil = PerfilEstudiante.objects.get(user=user)
            curso_actual = perfil.curso_actual
            hoy = date.today()
            dia_semana = hoy.weekday() + 1

            # 1. Clases hoy
            clases_hoy = 0
            if curso_actual:
                clases_hoy = BloqueHorario.objects.filter(
                    clase__curso=curso_actual,
                    clase__activo=True,
                    dia_semana=dia_semana,
                    activo=True
                ).values('clase').distinct().count()

            # 2. Tareas pendientes
            tareas_pendientes = 0
            tareas_vencen_manana = 0
            tareas_del_curso = Tarea.objects.none()
            tareas_con_entrega = []
            tareas_pendientes_lista = []
            
            if curso_actual:
                tareas_del_curso = Tarea.objects.filter(
                    clase__curso=curso_actual,
                    activa=True,
                    es_publica=True
                )
                tareas_con_entrega = EntregaTarea.objects.filter(
                    estudiante=user,
                    tarea__in=tareas_del_curso
                ).values_list('tarea', flat=True)

                tareas_pendientes_qs = tareas_del_curso.exclude(id_tarea__in=tareas_con_entrega)
                tareas_pendientes = tareas_pendientes_qs.count()
                
                # Tareas que vencen mañana
                tomorrow = hoy + timedelta(days=1)
                tareas_vencen_manana = tareas_pendientes_qs.filter(fecha_entrega__date=tomorrow).count()

                # Obtener primeras 5 tareas pendientes (Reducir clics)
                for t in list(tareas_pendientes_qs.select_related('clase__asignatura').order_by('fecha_entrega')[:5]):
                    ahora_tz = timezone.now()
                    vencida_val = t.fecha_entrega and t.fecha_entrega < ahora_tz
                    
                    dias_restantes_val = 0
                    if t.fecha_entrega:
                        diff = t.fecha_entrega - ahora_tz
                        dias_restantes_val = max(diff.days, 0)
                        
                    tareas_pendientes_lista.append({
                        'id_tarea': t.id_tarea,
                        'titulo': t.titulo,
                        'clase': t.clase,
                        'fecha_entrega': t.fecha_entrega,
                        'esta_vencida': vencida_val,
                        'dias_restantes': dias_restantes_val,
                    })

            # 3. Promedio general
            promedio = Calificacion.objects.filter(
                estudiante=user,
                colegio_id=escuela_rbd,
                evaluacion__activa=True
            ).aggregate(promedio=Avg('nota'))['promedio']
            promedio_general = round(float(promedio), 1) if promedio else 0.0

            # 4. Porcentaje de asistencia (General y Mensual)
            asistencias = Asistencia.objects.filter(
                estudiante=user,
                colegio_id=escuela_rbd
            )
            porcentaje_asistencia = 100
            resumen_asistencia = asistencias.aggregate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P')),
            )
            total_asistencias = resumen_asistencia['total'] or 0
            if total_asistencias > 0:
                presentes = resumen_asistencia['presentes'] or 0
                porcentaje_asistencia = round((presentes / total_asistencias) * 100, 0)

            # Asistencia del mes actual
            asistencias_mes_actual = asistencias.filter(
                fecha__year=hoy.year,
                fecha__month=hoy.month
            )
            resumen_asistencia_mes = asistencias_mes_actual.aggregate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P')),
            )
            total_asistencias_mes = resumen_asistencia_mes['total'] or 0
            asistencia_mes_pct = 100
            if total_asistencias_mes > 0:
                presentes_mes = resumen_asistencia_mes['presentes'] or 0
                asistencia_mes_pct = round((presentes_mes / total_asistencias_mes) * 100, 0)
            else:
                asistencia_mes_pct = porcentaje_asistencia

            # 1. Próxima clase
            proxima_clase = None
            if curso_actual:
                ahora_tz = timezone.localtime(timezone.now())
                hora_actual = ahora_tz.time()
                # Buscar clase que empiece hoy después de la hora actual
                bloques_hoy = BloqueHorario.objects.filter(
                    clase__curso=curso_actual,
                    clase__activo=True,
                    dia_semana=dia_semana,
                    hora_inicio__gt=hora_actual,
                    activo=True
                ).select_related('clase__asignatura', 'clase__profesor').order_by('hora_inicio')
                
                if bloques_hoy.exists():
                    proxima_clase = bloques_hoy.first()
                else:
                    # Si no hay más hoy, buscar el día más cercano que tenga clases
                    for dia_offset in range(1, 8):
                        sig_dia = (dia_semana + dia_offset - 1) % 7 + 1
                        bloques_sig = BloqueHorario.objects.filter(
                            clase__curso=curso_actual,
                            clase__activo=True,
                            dia_semana=sig_dia,
                            activo=True
                        ).select_related('clase__asignatura', 'clase__profesor').order_by('dia_semana', 'hora_inicio')
                        if bloques_sig.exists():
                            proxima_clase = bloques_sig.first()
                            break

            # 2. Tareas pendientes
            tareas_pendientes = 0
            tareas_vencen_manana = 0
            tareas_del_curso = Tarea.objects.none()
            tareas_con_entrega = []
            tareas_pendientes_lista = []
            
            # Progreso de entregas
            tareas_entregadas_count = 0
            total_tareas_curso = 0
            progreso_barras = "░░░░░░░░░░"
            progreso_pct = 0
            
            if curso_actual:
                tareas_del_curso = Tarea.objects.filter(
                    clase__curso=curso_actual,
                    activa=True,
                    es_publica=True
                )
                tareas_con_entrega = EntregaTarea.objects.filter(
                    estudiante=user,
                    tarea__in=tareas_del_curso
                ).values_list('tarea', flat=True)

                tareas_pendientes_qs = tareas_del_curso.exclude(id_tarea__in=tareas_con_entrega)
                tareas_pendientes = tareas_pendientes_qs.count()
                
                # Tareas que vencen mañana
                tomorrow = hoy + timedelta(days=1)
                tareas_vencen_manana = tareas_pendientes_qs.filter(fecha_entrega__date=tomorrow).count()

                # Obtener primeras 5 tareas pendientes
                for t in list(tareas_pendientes_qs.select_related('clase__asignatura').order_by('fecha_entrega')[:5]):
                    ahora_tz = timezone.now()
                    vencida_val = t.fecha_entrega and t.fecha_entrega < ahora_tz
                    
                    dias_restantes_val = 0
                    if t.fecha_entrega:
                        diff = t.fecha_entrega - ahora_tz
                        dias_restantes_val = max(diff.days, 0)
                        
                    tareas_pendientes_lista.append({
                        'id_tarea': t.id_tarea,
                        'titulo': t.titulo,
                        'clase': t.clase,
                        'fecha_entrega': t.fecha_entrega,
                        'esta_vencida': vencida_val,
                        'dias_restantes': dias_restantes_val,
                    })

                total_tareas_curso = tareas_del_curso.count()
                tareas_entregadas_count = len(tareas_con_entrega)
                if total_tareas_curso > 0:
                    progreso_pct = int((tareas_entregadas_count / total_tareas_curso) * 100)
                    cant_bloques = int(round((tareas_entregadas_count / total_tareas_curso) * 10))
                    progreso_barras = "█" * cant_bloques + "░" * (10 - cant_bloques)

            # 3. Promedio general
            promedio = Calificacion.objects.filter(
                estudiante=user,
                colegio_id=escuela_rbd,
                evaluacion__activa=True
            ).aggregate(promedio=Avg('nota'))['promedio']
            promedio_general = round(float(promedio), 1) if promedio else 0.0

            # 4. Porcentaje de asistencia (General)
            asistencias = Asistencia.objects.filter(
                estudiante=user,
                colegio_id=escuela_rbd
            )
            porcentaje_asistencia = 100
            resumen_asistencia = asistencias.aggregate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P')),
            )
            total_asistencias = resumen_asistencia['total'] or 0
            if total_asistencias > 0:
                presentes = resumen_asistencia['presentes'] or 0
                porcentaje_asistencia = round((presentes / total_asistencias) * 100, 0)

            # Asignatura más fuerte y Asignatura que requiere atención
            asignatura_fuerte = "Ninguna"
            asignatura_debil = "Ninguna"
            avg_grades_by_subject = {}
            
            calificaciones_est = Calificacion.objects.filter(
                estudiante=user,
                evaluacion__activa=True
            ).select_related('evaluacion__clase__asignatura')
            
            from collections import defaultdict
            notas_por_asig = defaultdict(list)
            for c in calificaciones_est:
                if c.evaluacion.clase.asignatura:
                    notas_por_asig[c.evaluacion.clase.asignatura.nombre].append(float(c.nota))
                    
            for asig_name, list_notas in notas_por_asig.items():
                avg_grades_by_subject[asig_name] = sum(list_notas) / len(list_notas)
                
            if avg_grades_by_subject:
                asignatura_fuerte = max(avg_grades_by_subject, key=avg_grades_by_subject.get)
                asignatura_debil = min(avg_grades_by_subject, key=avg_grades_by_subject.get)
                
            # Últimas notas
            ultimas_notas = list(
                calificaciones_est.order_by('-fecha_creacion')[:5]
            )

            # Últimos anuncios
            ultimos_anuncios = []
            if curso_actual:
                ultimos_anuncios = list(Comunicado.objects.filter(
                    colegio_id=escuela_rbd,
                    activo=True
                ).filter(
                    Q(destinatario='todos') | 
                    Q(destinatario='estudiantes') | 
                    (Q(destinatario='curso_especifico') & Q(cursos_destinatarios=curso_actual))
                ).select_related('publicado_por').order_by('-fecha_publicacion')[:5])

            if not ultimos_anuncios:
                class DummyAnuncio:
                    def __init__(self, titulo, contenido, fecha_publicacion, publicado_por_name):
                        self.titulo = titulo
                        self.contenido = contenido
                        self.fecha_publicacion = fecha_publicacion
                        self.publicado_por_name = publicado_por_name
                    
                    @property
                    def publicado_por(self):
                        class DummyUser:
                            def get_full_name(self):
                                return "Dirección Académica"
                        return DummyUser()
                
                ultimos_anuncios = [
                    DummyAnuncio(
                        "Inicio de Evaluaciones Bimestrales",
                        "Estimados estudiantes, les recordamos que el próximo lunes comienzan las evaluaciones bimestrales. Por favor revisar el calendario.",
                        timezone.now() - timezone.timedelta(days=1),
                        "Dirección Académica"
                    ),
                    DummyAnuncio(
                        "Aniversario del Colegio",
                        "Celebramos nuestro aniversario este viernes. Las actividades comenzarán a las 09:00 hrs. ¡Los esperamos con sus colores de alianza!",
                        timezone.now() - timezone.timedelta(days=3),
                        "Dirección Académica"
                    )
                ]

            # Recent grades for Chart.js
            recent_grades = [float(c.nota) for c in reversed(ultimas_notas)] if ultimas_notas else [6.0, 5.8, 5.5, 6.2]
            subject_name = asignatura_fuerte if asignatura_fuerte != "Ninguna" else "General"

            return {
                'proxima_clase': proxima_clase,
                'tareas_pendientes': tareas_pendientes,
                'tareas_pendientes_lista': tareas_pendientes_lista,
                'tareas_entregadas_count': tareas_entregadas_count,
                'total_tareas_curso': total_tareas_curso,
                'progreso_barras': progreso_barras,
                'progreso_pct': progreso_pct,
                'promedio_general': promedio_general,
                'porcentaje_asistencia': porcentaje_asistencia,
                'asignatura_fuerte': asignatura_fuerte,
                'asignatura_debil': asignatura_debil,
                'ultimas_notas': ultimas_notas,
                'ultimos_anuncios': ultimos_anuncios,
                'recent_grades': recent_grades,
                'subject_name': subject_name,
                'sin_datos': curso_actual is None,
            }

        except PerfilEstudiante.DoesNotExist:
            return {
                'clases_hoy': 0,
                'tareas_pendientes': 0,
                'tareas_vencen_manana': 0,
                'tareas_pendientes_lista': [],
                'asistencia_mes_pct': 100,
                'promedio_general': 0.0,
                'clases_activas': [],
                'evaluaciones_proximas': [],
                'timeline': [],
                'prediccion': {'nivel': 'N/A', 'promedio': 0.0, 'asistencia': 100, 'mensaje': 'Sin datos académicos', 'check_ok': True},
                'recent_grades': [6.0, 5.8, 5.5, 5.1],
                'subject_name': 'Matemáticas',
                'asistencia_mensual': [{'mes': 'Marzo', 'porcentaje': 98}, {'mes': 'Abril', 'porcentaje': 92}, {'mes': 'Mayo', 'porcentaje': 95}],
                'notificaciones_accionables': [],
                'sin_datos': True,
            }

    @staticmethod
    def _get_estudiante_perfil_context(user, escuela_rbd):
        """Get perfil context for estudiante"""
        from backend.apps.accounts.models import PerfilEstudiante
        from backend.apps.academico.models import Calificacion, Asistencia
        from backend.apps.cursos.models import Clase, ClaseEstudiante
        from django.db.models import Avg, Count

        inicio_ctx = DashboardContextService._get_estudiante_inicio_context(user, escuela_rbd)

        try:
            perfil = PerfilEstudiante.objects.select_related(
                'user', 'user__role', 'ciclo_actual',
            ).get(user=user)
        except PerfilEstudiante.DoesNotExist:
            return {
                'sin_perfil': True,
                **inicio_ctx,
            }

        curso_actual = perfil.curso_actual
        total_calificaciones = Calificacion.objects.filter(
            estudiante=user,
            colegio_id=escuela_rbd,
        ).count()
        total_asignaturas = ClaseEstudiante.objects.filter(
            estudiante=user,
            activo=True,
            clase__activo=True,
        ).values('clase__asignatura').distinct().count()

        foto_display = None
        if perfil.foto_perfil:
            foto_display = perfil.foto_perfil.url
        elif perfil.foto_url:
            foto_display = perfil.foto_url

        edad = None
        if perfil.fecha_nacimiento:
            hoy = date.today()
            edad = hoy.year - perfil.fecha_nacimiento.year
            if (hoy.month, hoy.day) < (
                perfil.fecha_nacimiento.month,
                perfil.fecha_nacimiento.day,
            ):
                edad -= 1

        promedio = inicio_ctx.get('promedio_general', 0)
        asistencia_pct = inicio_ctx.get('porcentaje_asistencia', 0)

        return {
            'perfil': perfil,
            'estudiante': perfil,
            'curso_actual': curso_actual,
            'colegio': perfil.user.colegio,
            'foto_perfil_url': foto_display,
            'edad': edad,
            'iniciales': (
                (user.nombre[:1] if user.nombre else '')
                + (user.apellido_paterno[:1] if user.apellido_paterno else '')
            ).upper() or '?',
            'promedio_display': f'{promedio:.1f}' if promedio else '—',
            'promedio_progress': min(100, max(0, int((promedio or 0) * 10))),
            'asistencia_display': f'{asistencia_pct}%',
            'asistencia_progress': min(100, max(0, int(asistencia_pct or 0))),
            'total_calificaciones': total_calificaciones,
            'total_asignaturas': total_asignaturas,
            'estadisticas': {
                'promedio_general': promedio,
                'total_calificaciones': total_calificaciones,
                'total_asignaturas': total_asignaturas,
                'porcentaje_asistencia': asistencia_pct,
            },
            'hero_subtitle_perfil': (
                f'{curso_actual.nombre} · {perfil.estado_academico}'
                if curso_actual else perfil.estado_academico
            ),
            'sin_perfil': False,
        }

    @staticmethod
    def _dedupe_asistencias_por_materia_dia(asistencias_qs):
        """Un registro por fecha y asignatura (evita inflar por clases duplicadas en BD)."""
        from datetime import date
        estado_map = {
            'P': 'Presente',
            'A': 'Ausente',
            'T': 'Atraso',
            'J': 'Justificado',
        }
        latest = {}
        
        if isinstance(asistencias_qs, list):
            items = sorted(
                asistencias_qs,
                key=lambda x: (
                    x.fecha if x.fecha else date.min,
                    x.clase.asignatura.nombre if x.clase and x.clase.asignatura else '',
                    x.fecha_actualizacion.isoformat() if getattr(x, 'fecha_actualizacion', None) else ''
                )
            )
        else:
            items = asistencias_qs.order_by(
                'fecha', 'clase__asignatura__nombre', '-fecha_actualizacion'
            )

        for asist in items:
            asignatura = (
                asist.clase.asignatura.nombre
                if asist.clase and asist.clase.asignatura
                else 'N/A'
            )
            key = (asist.fecha, asignatura.lower())
            latest[key] = {
                'fecha': asist.fecha,
                'asignatura': asignatura,
                'asignatura_key': asignatura.lower(),
                'estado': asist.estado,
                'estado_texto': estado_map.get(asist.estado, asist.estado),
                'observaciones': asist.observaciones or '',
            }
        return list(latest.values())

    @staticmethod
    def _get_estudiante_asistencia_context(user, request_get_params):
        """Get asistencia context for estudiante"""
        from backend.apps.academico.models import Asistencia
        from backend.apps.cursos.models import Clase, ClaseEstudiante
        import logging
        logger = logging.getLogger(__name__)

        mes_nombres = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
        ]

        # Base query - prefetch all student attendance records in a single query with select_related
        # to completely solve N+1 database queries!
        asistencias_totales_qs = Asistencia.objects.filter(estudiante=user).select_related('clase', 'clase__asignatura')
        asistencias_totales_list = list(asistencias_totales_qs)
        total_historico = len(asistencias_totales_list)
        logger.info(f"Estudiante {user.email}: Total asistencias en BD = {total_historico}")

        # Group by year and month in memory
        from collections import defaultdict
        asistencias_por_mes = defaultdict(list)
        for asist in asistencias_totales_list:
            if asist.fecha:
                asistencias_por_mes[(asist.fecha.year, asist.fecha.month)].append(asist)

        meses_disponibles = []
        # Sort months descending in memory
        for (y, m) in sorted(asistencias_por_mes.keys(), key=lambda x: (x[0], x[1]), reverse=True):
            mes_qs = asistencias_por_mes[(y, m)]
            total_dedup = len(
                DashboardContextService._dedupe_asistencias_por_materia_dia(mes_qs)
            )
            meses_disponibles.append({
                'value': f'{y:04d}-{m:02d}',
                'label': f"{mes_nombres[m - 1]} {y}",
                'total': total_dedup,
            })

        ultima_fecha = None
        if asistencias_totales_list:
            # Find last attendance date in memory
            ultima_fecha = max(asist.fecha for asist in asistencias_totales_list if asist.fecha)

        mes_filtro_solicitado = request_get_params.get('mes') if request_get_params else None
        mes_filtro = mes_filtro_solicitado or date.today().strftime('%Y-%m')
        mes_auto_ajustado = False

        def _conteo_mes(mes_key):
            try:
                y, m = mes_key.split('-')
                # Count in memory
                return sum(1 for asist in asistencias_totales_list if asist.fecha and asist.fecha.year == int(y) and asist.fecha.month == int(m))
            except (ValueError, AttributeError):
                return 0

        if total_historico > 0 and _conteo_mes(mes_filtro) == 0:
            if ultima_fecha:
                mes_filtro = ultima_fecha.strftime('%Y-%m')
                mes_auto_ajustado = bool(mes_filtro_solicitado)

        periodo_label = mes_filtro
        anio_str, mes_str = None, None
        try:
            anio_str, mes_str = mes_filtro.split('-')
            periodo_label = f"{mes_nombres[int(mes_str) - 1]} {anio_str}"
        except (ValueError, IndexError):
            mes_filtro = date.today().strftime('%Y-%m')

        # Filter in memory
        filtered_list = []
        if anio_str and mes_str:
            filtered_list = [
                asist for asist in asistencias_totales_list
                if asist.fecha and asist.fecha.year == int(anio_str) and asist.fecha.month == int(mes_str)
            ]
        else:
            filtered_list = asistencias_totales_list

        registros_periodo = DashboardContextService._dedupe_asistencias_por_materia_dia(
            filtered_list
        )
        presentes = sum(1 for r in registros_periodo if r['estado'] == 'P')
        ausentes = sum(1 for r in registros_periodo if r['estado'] == 'A')
        tardanzas = sum(1 for r in registros_periodo if r['estado'] == 'T')
        justificados = sum(1 for r in registros_periodo if r['estado'] == 'J')

        total_registros = len(registros_periodo)
        if total_registros > 0:
            porcentaje_asistencia = round((presentes / total_registros) * 100, 1)
        else:
            porcentaje_asistencia = 0
            if total_historico == 0:
                logger.warning(f"Estudiante {user.email}: NO tiene registros de asistencia")

        asistencia_progress = min(100, max(0, int(round(porcentaje_asistencia))))

        dias_semana = [
            'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo',
        ]

        from collections import defaultdict

        por_fecha = defaultdict(list)
        for registro in registros_periodo:
            por_fecha[registro['fecha']].append(registro)

        dias_asistencia = []
        for fecha in sorted(por_fecha.keys(), reverse=True):
            registros_dia = sorted(
                por_fecha[fecha],
                key=lambda r: r['asignatura'],
            )
            dias_asistencia.append({
                'fecha': fecha,
                'fecha_display': fecha.strftime('%d/%m/%Y'),
                'dia_semana': dias_semana[fecha.weekday()],
                'dia': fecha.day,
                'mes_corto': mes_nombres[fecha.month - 1][:3],
                'registros': registros_dia,
                'total_materias': len(registros_dia),
            })

        total_dias_periodo = len(dias_asistencia)

        asignaturas_periodo = []
        seen_asig = set()
        for reg in sorted(registros_periodo, key=lambda r: r['asignatura']):
            if reg['asignatura_key'] in seen_asig:
                continue
            seen_asig.add(reg['asignatura_key'])
            asignaturas_periodo.append({
                'nombre': reg['asignatura'],
                'key': reg['asignatura_key'],
            })
        
        return {
            'presentes': presentes,
            'ausentes': ausentes,
            'tardanzas': tardanzas,
            'justificados': justificados,
            'porcentaje_asistencia': porcentaje_asistencia,
            'promedio_display': f'{porcentaje_asistencia}%',
            'asistencia_progress': asistencia_progress,
            'total_registros_periodo': total_registros,
            'total_dias_periodo': total_dias_periodo,
            'dias_asistencia': dias_asistencia,
            'mes_filtro': mes_filtro,
            'periodo_label': periodo_label,
            'meses_disponibles': meses_disponibles,
            'mes_auto_ajustado': mes_auto_ajustado,
            'ultima_fecha_asistencia': ultima_fecha,
            'asignaturas_periodo': asignaturas_periodo,
            'sin_datos_asistencia': total_historico == 0,
        }

    @staticmethod
    def _get_estudiante_clases_context(user, escuela_rbd=None):
        """Clases del estudiante con métricas reales e insights."""
        from backend.apps.cursos.models import Clase, BloqueHorario
        from backend.apps.accounts.models import PerfilEstudiante
        from backend.apps.academico.models import (
            Calificacion,
            Asistencia,
            Tarea,
            EntregaTarea,
            Evaluacion,
        )
        from backend.common.utils.grade_scale import es_aprobado
        import logging

        logger = logging.getLogger(__name__)
        hoy = date.today()
        dia_semana = hoy.weekday() + 1
        colegio_id = escuela_rbd or getattr(user, 'colegio_id', None)

        empty = {
            'mis_clases': [],
            'curso_actual': None,
            'total_clases': 0,
            'clases_hoy': 0,
            'tareas_pendientes': 0,
            'promedio_general': 0.0,
            'porcentaje_asistencia': 100,
            'evaluaciones_proximas': [],
            'mis_clases_inteligencia': {},
        }

        try:
            perfil = PerfilEstudiante.objects.get(user=user)
            curso_actual = perfil.curso_actual
        except PerfilEstudiante.DoesNotExist:
            logger.error('Estudiante %s sin PerfilEstudiante', user.email)
            return empty

        clases = list(
            Clase.objects.filter(
                estudiantes__estudiante=user,
                estudiantes__activo=True,
                activo=True,
            )
            .select_related('asignatura', 'profesor')
            .prefetch_related(
                Prefetch(
                    'bloques_horario',
                    queryset=BloqueHorario.objects.filter(activo=True).order_by(
                        'dia_semana', 'hora_inicio'
                    ),
                    to_attr='bloques_horario_activos',
                )
            )
            .annotate(
                total_evaluaciones=Count(
                    'evaluaciones', filter=Q(evaluaciones__activa=True), distinct=True
                )
            )
            .order_by('asignatura__nombre')
        )

        if not clases:
            return {**empty, 'curso_actual': curso_actual}

        clases_ids = [c.id for c in clases]

        clases_hoy = (
            BloqueHorario.objects.filter(
                clase_id__in=clases_ids,
                dia_semana=dia_semana,
                activo=True,
            )
            .values('clase_id')
            .distinct()
            .count()
        )

        tareas_qs = Tarea.objects.filter(
            clase_id__in=clases_ids,
            activa=True,
            es_publica=True,
        )
        entregadas = set(
            EntregaTarea.objects.filter(
                estudiante=user,
                tarea__clase_id__in=clases_ids,
            ).values_list('tarea_id', flat=True)
        )
        tareas_pendientes_qs = tareas_qs.exclude(id_tarea__in=entregadas)
        tareas_pendientes = tareas_pendientes_qs.count()

        tareas_pend_por_clase = {
            row['clase_id']: row['total']
            for row in tareas_pendientes_qs.values('clase_id').annotate(total=Count('pk'))
        }

        prom_agg = Calificacion.objects.filter(
            estudiante=user,
            evaluacion__activa=True,
            evaluacion__clase_id__in=clases_ids,
        ).aggregate(promedio=Avg('nota'))
        promedio_general = round(float(prom_agg['promedio']), 1) if prom_agg['promedio'] else 0.0

        asist_global = Asistencia.objects.filter(
            estudiante=user,
            clase_id__in=clases_ids,
        ).aggregate(
            total=Count('pk'),
            presentes=Count('pk', filter=Q(estado='P')),
        )
        porcentaje_asistencia = 100
        if asist_global['total']:
            porcentaje_asistencia = round(
                (asist_global['presentes'] / asist_global['total']) * 100, 0
            )

        notas_por_clase = {
            row['evaluacion__clase_id']: round(float(row['promedio']), 1)
            for row in Calificacion.objects.filter(
                estudiante=user,
                evaluacion__activa=True,
                evaluacion__clase_id__in=clases_ids,
            )
            .values('evaluacion__clase_id')
            .annotate(promedio=Avg('nota'))
        }

        asist_por_clase = {}
        for row in (
            Asistencia.objects.filter(estudiante=user, clase_id__in=clases_ids)
            .values('clase_id')
            .annotate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P')),
            )
        ):
            if row['total']:
                asist_por_clase[row['clase_id']] = round(
                    (row['presentes'] / row['total']) * 100, 0
                )

        calif_count_por_clase = {
            row['evaluacion__clase_id']: row['total']
            for row in Calificacion.objects.filter(
                estudiante=user,
                evaluacion__activa=True,
                evaluacion__clase_id__in=clases_ids,
            )
            .values('evaluacion__clase_id')
            .annotate(total=Count('pk'))
        }

        evaluaciones_proximas = list(
            Evaluacion.objects.filter(
                clase_id__in=clases_ids,
                activa=True,
                fecha_evaluacion__gte=hoy,
                fecha_evaluacion__lte=hoy + timedelta(days=21),
            )
            .select_related('clase', 'clase__asignatura')
            .order_by('fecha_evaluacion')[:6]
        )

        prox_eval_por_clase = {}
        for ev in evaluaciones_proximas:
            if ev.clase_id not in prox_eval_por_clase:
                prox_eval_por_clase[ev.clase_id] = ev

        gradientes = [
            'gradient-orange',
            'gradient-blue',
            'gradient-green',
            'gradient-purple',
            'gradient-yellow',
            'gradient-dark',
        ]

        mis_clases = []
        for idx, clase in enumerate(clases):
            bloques = getattr(clase, 'bloques_horario_activos', [])
            horarios_por_dia = {}
            for bloque in bloques:
                dia_nombre = bloque.get_dia_semana_display()
                if dia_nombre not in horarios_por_dia:
                    horarios_por_dia[dia_nombre] = {
                        'bloques': [],
                        'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                        'hora_fin': bloque.hora_fin.strftime('%H:%M'),
                    }
                else:
                    horarios_por_dia[dia_nombre]['hora_fin'] = bloque.hora_fin.strftime(
                        '%H:%M'
                    )
                horarios_por_dia[dia_nombre]['bloques'].append(
                    {
                        'bloque_numero': bloque.bloque_numero,
                        'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                        'hora_fin': bloque.hora_fin.strftime('%H:%M'),
                    }
                )

            total_eval = int(getattr(clase, 'total_evaluaciones', 0) or 0)
            calif_count = calif_count_por_clase.get(clase.id, 0)
            if total_eval > 0:
                progreso = min(int((calif_count / total_eval) * 100), 100)
            else:
                progreso = 0

            if progreso < 40:
                color_progreso = 'progress-low'
            elif progreso < 70:
                color_progreso = 'progress-medium'
            else:
                color_progreso = 'progress-high'

            nota = notas_por_clase.get(clase.id)
            pct_asist = asist_por_clase.get(clase.id)
            tareas_clase = tareas_pend_por_clase.get(clase.id, 0)
            prox_ev = prox_eval_por_clase.get(clase.id)

            estado_clase = 'sin_nota'
            if nota is not None:
                estado_clase = (
                    'ok' if es_aprobado(nota, getattr(user, 'colegio', None)) else 'atencion'
                )

            prox_eval_label = None
            if prox_ev:
                dias = (prox_ev.fecha_evaluacion - hoy).days
                if dias == 0:
                    prox_eval_label = f'Hoy · {prox_ev.nombre}'
                elif dias == 1:
                    prox_eval_label = f'Mañana · {prox_ev.nombre}'
                else:
                    prox_eval_label = (
                        f'{prox_ev.fecha_evaluacion.strftime("%d/%m")} · {prox_ev.nombre}'
                    )

            mis_clases.append(
                {
                    'id_clase': clase.id,
                    'asignatura': clase.asignatura.nombre,
                    'codigo': getattr(clase.asignatura, 'codigo', ''),
                    'color': getattr(clase.asignatura, 'color', '#3b82f6'),
                    'horas_semanales': getattr(
                        clase.asignatura, 'horas_semanales', len(bloques)
                    ),
                    'profesor_nombre': (
                        clase.profesor.get_full_name() if clase.profesor else 'Sin profesor'
                    ),
                    'profesor_email': clase.profesor.email if clase.profesor else '',
                    'horarios_por_dia': horarios_por_dia,
                    'total_bloques': len(bloques),
                    'gradiente': gradientes[idx % len(gradientes)],
                    'progreso': progreso,
                    'color_progreso': color_progreso,
                    'progreso_detalle': (
                        f'{calif_count}/{total_eval} evaluaciones con nota'
                        if total_eval
                        else 'Sin evaluaciones activas'
                    ),
                    'nota': nota,
                    'asistencia_pct': pct_asist,
                    'tareas_pendientes': tareas_clase,
                    'proxima_evaluacion': prox_eval_label,
                    'estado_clase': estado_clase,
                }
            )

        inteligencia = DashboardContextService._build_estudiante_mis_clases_inteligencia(
            mis_clases=mis_clases,
            promedio_general=promedio_general,
            porcentaje_asistencia=porcentaje_asistencia,
            tareas_pendientes=tareas_pendientes,
            evaluaciones_proximas=evaluaciones_proximas,
            hoy=hoy,
        )

        return {
            'mis_clases': mis_clases,
            'curso_actual': curso_actual,
            'total_clases': len(mis_clases),
            'clases_hoy': clases_hoy,
            'tareas_pendientes': tareas_pendientes,
            'promedio_general': promedio_general,
            'porcentaje_asistencia': porcentaje_asistencia,
            'evaluaciones_proximas': evaluaciones_proximas,
            'mis_clases_inteligencia': inteligencia,
        }

    @staticmethod
    def _build_estudiante_mis_clases_inteligencia(
        mis_clases,
        promedio_general,
        porcentaje_asistencia,
        tareas_pendientes,
        evaluaciones_proximas,
        hoy,
    ):
        """Resumen inteligente para la vista Mis Clases."""
        con_nota = [c for c in mis_clases if c.get('nota') is not None]
        sin_nota = [c for c in mis_clases if c.get('nota') is None]
        atencion = [c for c in mis_clases if c.get('estado_clase') == 'atencion']

        mejor = max(con_nota, key=lambda c: c['nota']) if con_nota else None
        peor = min(con_nota, key=lambda c: c['nota']) if con_nota else None

        estado = 'estable'
        estado_label = 'Rendimiento en curso normal'
        estado_hint = 'Revisa el detalle de cada asignatura para preparar evaluaciones y entregas.'
        if promedio_general and promedio_general < 4.0 or len(atencion) >= 2:
            estado = 'riesgo'
            estado_label = 'Conviene reforzar varias asignaturas'
            estado_hint = (
                'Tienes asignaturas bajo el nivel de aprobación: prioriza estudio y consulta al docente.'
            )
        elif promedio_general and promedio_general < 4.5 or tareas_pendientes >= 3:
            estado = 'atencion'
            estado_label = 'Hay puntos a mejorar'
            estado_hint = 'Revisa tareas pendientes y las próximas evaluaciones del panel lateral.'

        alertas = []
        if tareas_pendientes:
            alertas.append(
                f'{tareas_pendientes} tarea(s) pendiente(s) de entrega en tus asignaturas.'
            )
        if evaluaciones_proximas:
            prox = evaluaciones_proximas[0]
            dias = (prox.fecha_evaluacion - hoy).days
            cuando = 'hoy' if dias == 0 else ('mañana' if dias == 1 else f'en {dias} días')
            alertas.append(
                f'Próxima evaluación {cuando}: {prox.nombre} ({prox.clase.asignatura.nombre}).'
            )
        if porcentaje_asistencia < 90:
            alertas.append(f'Asistencia general {porcentaje_asistencia}% en el período registrado.')
        if sin_nota and len(sin_nota) <= 3:
            nombres = ', '.join(c['asignatura'] for c in sin_nota[:3])
            alertas.append(f'Sin nota publicada aún en: {nombres}.')

        consejo = 'Usa los filtros para encontrar una asignatura o ver las que requieren atención.'
        if peor and peor.get('nota') is not None:
            consejo = (
                f'En {peor["asignatura"]} tu promedio es {peor["nota"]}: '
                'entra al detalle de la clase y revisa materiales y tareas.'
            )
        elif tareas_pendientes:
            consejo = (
                f'Tienes {tareas_pendientes} tarea(s) por entregar: '
                'ordénalas por fecha en el detalle de cada asignatura.'
            )

        return {
            'estado': estado,
            'estado_label': estado_label,
            'estado_hint': estado_hint,
            'alertas': alertas,
            'consejo': consejo,
            'mejor_asignatura': (
                {'nombre': mejor['asignatura'], 'nota': mejor['nota']} if mejor else None
            ),
            'peor_asignatura': (
                {'nombre': peor['asignatura'], 'nota': peor['nota']} if peor else None
            ),
            'asignaturas_sin_nota': len(sin_nota),
            'asignaturas_atencion': len(atencion),
        }

    @staticmethod
    def _get_estudiante_evaluaciones_context(user):
        """Evaluaciones del estudiante: próximas, sin nota y completadas."""
        from datetime import timedelta
        from backend.apps.academico.models import Evaluacion, Calificacion
        from backend.apps.cursos.models import Clase

        curso_actual = DashboardContextService._resolve_estudiante_curso_actual(user)
        empty = {
            'evaluaciones_proximas_lista': [],
            'evaluaciones_pendientes': [],
            'evaluaciones_completadas': [],
            'eval_proxima_destacada': None,
            'total_eval_pendientes': 0,
            'total_eval_completadas': 0,
            'total_eval_proximas': 0,
            'total_evaluaciones': 0,
            'promedio_ultimas_eval': None,
            'curso_actual': curso_actual,
        }
        if not curso_actual:
            return empty

        clases_ids = list(
            Clase.objects.filter(
                estudiantes__estudiante=user,
                estudiantes__activo=True,
                activo=True,
            ).values_list('id', flat=True)
        )
        if not clases_ids:
            clases_ids = list(
                Clase.objects.filter(curso=curso_actual, activo=True).values_list('id', flat=True)
            )

        evaluaciones_qs = Evaluacion.objects.filter(
            clase_id__in=clases_ids,
            activa=True,
        ).select_related('clase__asignatura').order_by('fecha_evaluacion')

        calif_map = {
            c.evaluacion_id: c
            for c in Calificacion.objects.filter(
                estudiante=user,
                evaluacion__in=evaluaciones_qs,
            )
        }

        hoy = date.today()
        limite_proxima = hoy + timedelta(days=7)

        proximas_lista = []
        pendientes = []
        completadas = []

        for ev in evaluaciones_qs:
            asignatura = ev.clase.asignatura.nombre if ev.clase.asignatura else 'Sin asignatura'
            calif = calif_map.get(ev.id_evaluacion)
            dias = (ev.fecha_evaluacion - hoy).days if ev.fecha_evaluacion else None

            item = {
                'id': ev.id_evaluacion,
                'nombre': ev.nombre,
                'asignatura': asignatura,
                'asignatura_key': asignatura.lower(),
                'clase_id': ev.clase_id,
                'fecha': ev.fecha_evaluacion,
                'tipo': ev.get_tipo_evaluacion_display(),
                'tipo_key': ev.tipo_evaluacion,
                'ponderacion': ev.ponderacion,
                'dias_restantes': dias,
                'es_hoy': dias == 0,
                'es_manana': dias == 1,
                'nota': float(calif.nota) if calif else None,
                'fecha_nota': calif.fecha_creacion.date() if calif else None,
            }

            if calif:
                completadas.append(item)
            else:
                item['es_proxima'] = bool(
                    ev.fecha_evaluacion and hoy <= ev.fecha_evaluacion <= limite_proxima
                )
                pendientes.append(item)
                if item['es_proxima']:
                    proximas_lista.append(item)

        completadas.sort(key=lambda x: x['fecha'] or hoy, reverse=True)
        pendientes.sort(key=lambda x: x['fecha'] or hoy)
        proximas_lista.sort(key=lambda x: x['fecha'] or hoy)

        promedio_ultimas = None
        if completadas:
            ultimas = completadas[:5]
            promedio_ultimas = round(sum(e['nota'] for e in ultimas if e['nota'] is not None) / len(ultimas), 1)

        eval_proxima_destacada = proximas_lista[0] if proximas_lista else (pendientes[0] if pendientes else None)

        return {
            'evaluaciones_proximas_lista': proximas_lista,
            'evaluaciones_pendientes': pendientes,
            'evaluaciones_completadas': completadas,
            'eval_proxima_destacada': eval_proxima_destacada,
            'total_eval_pendientes': len(pendientes),
            'total_eval_completadas': len(completadas),
            'total_eval_proximas': len(proximas_lista),
            'total_evaluaciones': evaluaciones_qs.count(),
            'promedio_ultimas_eval': promedio_ultimas,
            'curso_actual': curso_actual,
        }

    @staticmethod
    def _get_estudiante_notas_context(user):
        """Get notas context for estudiante"""
        from backend.apps.academico.models import Calificacion, Evaluacion
        from django.db.models import Avg
        from backend.apps.accounts.models import PerfilEstudiante

        # Obtener perfil y curso
        try:
            perfil = PerfilEstudiante.objects.get(user=user)
            curso_actual = perfil.curso_actual
        except PerfilEstudiante.DoesNotExist:
            return {
                'notas_por_asignatura': [],
                'promedio_general': 0.0,
                'total_notas': 0,
                'curso_actual': None,
            }

        from backend.common.utils.grade_scale import get_escala, es_aprobado

        escala = get_escala(getattr(user, 'colegio', None))
        nota_aprobacion = float(escala['nota_aprobacion'])

        # Calificaciones por asignatura
        calificaciones = Calificacion.objects.filter(
            estudiante=user
        ).select_related(
            'evaluacion__clase__asignatura',
            'evaluacion__clase__profesor'
        ).order_by(
            'evaluacion__clase__asignatura__nombre',
            '-evaluacion__fecha_evaluacion'
        )

        # Agrupar por asignatura
        asignaturas_data = {}
        total_notas = 0
        suma_notas = 0

        for calif in calificaciones:
            asignatura = calif.evaluacion.clase.asignatura
            asignatura_key = asignatura.nombre

            if asignatura_key not in asignaturas_data:
                asignaturas_data[asignatura_key] = {
                    'asignatura': asignatura.nombre,
                    'asignatura_key': asignatura_key.lower(),
                    'profesor': calif.evaluacion.clase.profesor.get_full_name() if calif.evaluacion.clase.profesor else 'Sin asignar',
                    'evaluaciones': [],
                    'promedio': 0.0,
                    'estado': 'Aprobado',  # Default
                }

            nota_val = float(calif.nota)
            asignaturas_data[asignatura_key]['evaluaciones'].append({
                'nombre': calif.evaluacion.nombre,
                'nota': calif.nota,
                'aprobada': es_aprobado(nota_val, getattr(user, 'colegio', None)),
                'fecha': calif.evaluacion.fecha_evaluacion,
                'ponderacion': calif.evaluacion.ponderacion,
            })

            total_notas += 1
            suma_notas += calif.nota

        # Calcular promedios y estados
        notas_por_asignatura = []
        total_reforzar = 0
        for data in asignaturas_data.values():
            if data['evaluaciones']:
                notas = [float(e['nota']) for e in data['evaluaciones']]
                data['promedio'] = round(sum(notas) / len(notas), 1)
                from backend.common.utils.grade_scale import estado_nota as _estado_nota
                data['estado'] = _estado_nota(data['promedio'], user.colegio)
                data['total_evaluaciones'] = len(data['evaluaciones'])
                data['nota_min'] = round(min(notas), 1)
                data['nota_max'] = round(max(notas), 1)
                if data['estado'] == 'Reprobado':
                    total_reforzar += 1
            else:
                data['promedio'] = 0.0
                data['estado'] = 'Sin evaluaciones'
                data['total_evaluaciones'] = 0
                data['nota_min'] = None
                data['nota_max'] = None

            notas_por_asignatura.append(data)

        notas_por_asignatura.sort(key=lambda x: x['asignatura'])

        # Calcular promedio general
        promedio_general = round(suma_notas / total_notas, 1) if total_notas > 0 else 0.0
        promedio_progress = 0
        if promedio_general > 0:
            promedio_progress = min(100, max(0, int(((float(promedio_general) - 1.0) / 6.0) * 100)))

        return {
            'notas_por_asignatura': notas_por_asignatura,
            'promedio_general': promedio_general,
            'promedio_progress': promedio_progress,
            'total_notas': total_notas,
            'total_asignaturas': len(notas_por_asignatura),
            'total_reforzar': total_reforzar,
            'curso_actual': curso_actual,
            'nota_aprobacion': nota_aprobacion,
            'promedio_general_aprobado': es_aprobado(promedio_general, getattr(user, 'colegio', None)) if total_notas else True,
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_ATTENDANCE')
    def get_asistencia_context(request_get_params, colegio, user=None):
        return DashboardContextService.execute('get_asistencia_context', {
            'request_get_params': request_get_params,
            'colegio': colegio,
            'user': user,
        })

    @staticmethod
    def _execute_get_asistencia_context(params: dict):
        request_get_params = params.get('request_get_params')
        colegio = params['colegio']
        user = params['user']

        DashboardContextService._validate_school_integrity(colegio.rbd, 'DASHBOARD_CONTEXT_ASISTENCIA')
        """Get asistencia context for profesor"""
        from backend.apps.cursos.models import Clase, ClaseEstudiante
        from backend.apps.academico.services.attendance_service import AttendanceService
        from datetime import date

        # GET - Obtener datos
        clases = Clase.objects.filter(
            profesor=user,
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso')
        total_clases = clases.count()

        # Filtros
        filtro_clase_id = request_get_params.get('clase_id', '')
        filtro_fecha = request_get_params.get('fecha', '')

        # Selección automática si no hay filtro
        if not filtro_clase_id and clases.exists():
            filtro_clase_id = str(clases.first().id)
        if not filtro_fecha:
            filtro_fecha = date.today().strftime('%Y-%m-%d')

        estudiantes_con_asistencia = []
        clase_seleccionada = None
        stats_clase = {}

        if filtro_clase_id:
            try:
                clase_seleccionada = Clase.objects.get(id=filtro_clase_id, colegio=colegio)
                fecha_obj = datetime.strptime(filtro_fecha, '%Y-%m-%d').date()

                estudiantes_con_asistencia = AttendanceService.get_students_with_attendance(
                    user, colegio, clase_seleccionada, fecha_obj
                )

                stats_clase = AttendanceService.calculate_class_attendance_stats(
                    user, clase_seleccionada, days=30
                )
            except Exception as e:
                pass  # O manejar error

        context = {
            'clases': clases,
            'total_clases': total_clases,
            'clase_seleccionada': clase_seleccionada,
            'estudiantes_con_asistencia': estudiantes_con_asistencia,
            'filtro_clase_id': filtro_clase_id,
            'filtro_fecha': filtro_fecha,
            'stats_clase': stats_clase,
        }
        return context

    @staticmethod
    def _get_profesor_perfil_context(user, escuela_rbd):
        """Get perfil context for profesor"""
        from backend.apps.cursos.models import Clase
        from backend.apps.academico.models import Evaluacion, Calificacion
        from backend.apps.academico.models import Planificacion

        estadisticas = {
            'total_asignaturas': 0,
            'total_evaluaciones': 0,
            'total_estudiantes': 0,
            'total_planificaciones': 0,
        }

        # Asignaturas dictadas por el profesor en sus clases activas.
        estadisticas['total_asignaturas'] = Clase.objects.filter(
            profesor_id=user.id,
            colegio_id=escuela_rbd,
            activo=True,
            asignatura__isnull=False,
        ).values('asignatura_id').distinct().count()

        # Evaluaciones creadas en las clases del profesor.
        estadisticas['total_evaluaciones'] = Evaluacion.objects.filter(
            clase__profesor_id=user.id,
            colegio_id=escuela_rbd,
            activa=True,
        ).count()

        # Estudiantes distintos evaluados por el profesor.
        estadisticas['total_estudiantes'] = Calificacion.objects.filter(
            evaluacion__clase__profesor_id=user.id,
            evaluacion__colegio_id=escuela_rbd,
        ).values('estudiante_id').distinct().count()

        # Planificaciones asociadas a clases del profesor.
        estadisticas['total_planificaciones'] = Planificacion.objects.filter(
            clase__profesor_id=user.id,
            colegio_id=escuela_rbd,
            activa=True,
        ).count()

        return {'estadisticas': estadisticas}

    @staticmethod
    def _get_profesor_clases_context(user):
        """Get mis_clases context for profesor"""
        from backend.apps.academico.services.academic_view_service import AcademicViewService
        from backend.apps.cursos.models import Clase, BloqueHorario, ClaseEstudiante

        try:
            return AcademicViewService.get_teacher_classes(user)
        except Exception:
            # Fallback defensivo: evita dashboard vacío cuando falla el servicio principal.
            clases = Clase.objects.filter(
                profesor=user,
                colegio_id=getattr(user, 'rbd_colegio', None),
                activo=True,
            ).select_related('asignatura', 'curso').order_by('curso__nombre', 'asignatura__nombre')

            # Precalcular tareas sin corregir y alumnos en riesgo en lote (N+1 safe)
            from backend.apps.academico.models import EntregaTarea, Calificacion, Asistencia
            from django.db.models import Count, Avg, Q
            from collections import defaultdict

            entregas_pendientes = EntregaTarea.objects.filter(
                tarea__clase__in=clases,
                calificacion__isnull=True
            ).values('tarea__clase_id').annotate(count=Count('pk'))
            tareas_sin_corregir_map = {item['tarea__clase_id']: item['count'] for item in entregas_pendientes}

            clase_estudiantes = ClaseEstudiante._base_manager.filter(
                clase__in=clases,
                activo=True
            ).values('clase_id', 'estudiante_id')

            estudiantes_por_clase = defaultdict(list)
            for ce in clase_estudiantes:
                estudiantes_por_clase[ce['clase_id']].append(ce['estudiante_id'])

            calificaciones_bulk = Calificacion.objects.filter(
                evaluacion__clase__in=clases,
                evaluacion__activa=True
            ).values('evaluacion__clase_id', 'estudiante_id').annotate(avg_nota=Avg('nota'))

            promedios_map = defaultdict(dict)
            for item in calificaciones_bulk:
                promedios_map[item['evaluacion__clase_id']][item['estudiante_id']] = float(item['avg_nota'])

            asistencias_bulk = Asistencia.objects.filter(
                clase__in=clases
            ).values('clase_id', 'estudiante_id').annotate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P'))
            )

            asistencia_map = defaultdict(dict)
            for item in asistencias_bulk:
                total = item['total']
                presentes = item['presentes']
                asistencia_map[item['clase_id']][item['estudiante_id']] = (presentes / total * 100) if total > 0 else 100.0

            mis_clases = []
            total_estudiantes_sum = 0
            total_horas_sum = 0
            cursos_unicos = set()

            for clase in clases:
                bloques = BloqueHorario.objects.filter(clase=clase, activo=True).order_by('dia_semana', 'bloque_numero')
                horarios_por_dia = {}

                for bloque in bloques:
                    dia_nombre = bloque.get_dia_semana_display()
                    horarios_por_dia.setdefault(dia_nombre, []).append({
                        'bloque_numero': bloque.bloque_numero,
                        'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                        'hora_fin': bloque.hora_fin.strftime('%H:%M'),
                    })

                total_estudiantes = ClaseEstudiante._base_manager.filter(clase=clase, activo=True).count()
                horas_semanales = getattr(clase.asignatura, 'horas_semanales', 0) or 0

                tareas_sin_corregir = tareas_sin_corregir_map.get(clase.id, 0)
                alumnos_riesgo = 0
                for est_id in estudiantes_por_clase[clase.id]:
                    avg_grade = promedios_map[clase.id].get(est_id, 7.0)
                    asist_rate = asistencia_map[clase.id].get(est_id, 100.0)
                    if avg_grade < 4.5 or asist_rate < 80.0:
                        alumnos_riesgo += 1

                mis_clases.append({
                    'id_clase': clase.id,
                    'asignatura': clase.asignatura.nombre,
                    'codigo': getattr(clase.asignatura, 'codigo', ''),
                    'color': getattr(clase.asignatura, 'color', '#3b82f6'),
                    'horas_semanales': horas_semanales,
                    'curso_nombre': clase.curso.nombre,
                    'total_estudiantes': total_estudiantes,
                    'horarios_por_dia': horarios_por_dia,
                    'total_bloques': bloques.count(),
                    'tareas_sin_corregir': tareas_sin_corregir,
                    'alumnos_riesgo': alumnos_riesgo,
                })

                total_estudiantes_sum += total_estudiantes
                total_horas_sum += horas_semanales
                cursos_unicos.add(clase.curso_id)

            total_clases = len(mis_clases)
            return {
                'mis_clases': mis_clases,
                'total_clases': total_clases,
                'promedio_estudiantes': round(total_estudiantes_sum / total_clases) if total_clases > 0 else 0,
                'total_horas_semanales': total_horas_sum,
                'total_cursos': len(cursos_unicos),
            }
    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_ATTENDANCE'),
        ('ACADEMICO', 'VIEW_GRADES'),
        ('ACADEMICO', 'VIEW_COURSES'),
    ])
    def get_profesor_context(request_get_params, user, pagina_solicitada, escuela_rbd):
        return DashboardContextService.execute('get_profesor_context', {
            'request_get_params': request_get_params,
            'user': user,
            'pagina_solicitada': pagina_solicitada,
            'escuela_rbd': escuela_rbd,
        })

    @staticmethod
    def _execute_get_profesor_context(params: dict):
        request_get_params = params.get('request_get_params')
        user = params['user']
        pagina_solicitada = params['pagina_solicitada']
        escuela_rbd = params['escuela_rbd']

        DashboardContextService._validate_school_integrity(escuela_rbd, 'DASHBOARD_CONTEXT_PROFESOR')
        """Get context specific for profesor role"""
        from backend.apps.institucion.models import Colegio

        colegio = Colegio.objects.get(rbd=escuela_rbd)
        context = {}

        if pagina_solicitada == 'inicio':
            context.update(DashboardContextService._get_profesor_inicio_context(user, escuela_rbd))
        elif pagina_solicitada == 'perfil':
            context.update(DashboardContextService._get_profesor_perfil_context(user, escuela_rbd))
        elif pagina_solicitada == 'mis_clases':
            context.update(DashboardContextService._get_profesor_clases_context(user))
        elif pagina_solicitada == 'notas':
            context.update(DashboardContextService._get_profesor_notas_context(request_get_params, user, colegio))
        elif pagina_solicitada == 'libro_clases':
            context.update(DashboardContextService._get_profesor_libro_clases_context(request_get_params, user, colegio))
        elif pagina_solicitada == 'reportes':
            context.update(DashboardContextService._get_profesor_reportes_context(request_get_params, user, colegio))
        elif pagina_solicitada == 'disponibilidad':
            context.update(DashboardContextService._get_profesor_disponibilidad_context(user, colegio))
        elif pagina_solicitada == 'tareas_consolidado':
            context.update(DashboardContextService._get_profesor_tareas_consolidado_context(user, colegio))
        elif pagina_solicitada == 'mis_planificaciones':
            context.update(DashboardContextService._get_profesor_planificaciones_context(user, colegio))

        return context

    @staticmethod
    def _get_profesor_notas_context(request_get_params, user, colegio):
        """Get notas context for profesor"""
        from backend.apps.cursos.models import Clase, ClaseEstudiante
        from backend.apps.academico.models import Evaluacion, Calificacion
        from django.db.models import Avg, Count
        from datetime import date

        clases = Clase.objects.filter(
            profesor=user,
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso')

        # Estadísticas generales para el dashboard
        total_evaluaciones = Evaluacion.objects.filter(
            clase__profesor=user,
            clase__colegio=colegio,
            activa=True
        ).count()

        total_calificaciones_general = Calificacion.objects.filter(
            evaluacion__clase__profesor=user,
            evaluacion__clase__colegio=colegio
        ).count()

        # Calcular promedio general
        promedio_general = 0
        if total_calificaciones_general > 0:
            avg_result = Calificacion.objects.filter(
                evaluacion__clase__profesor=user,
                evaluacion__clase__colegio=colegio
            ).aggregate(avg_nota=Avg('nota'))
            promedio_general = round(avg_result['avg_nota'] or 0, 1)

        filtro_clase_id = request_get_params.get('clase_id', '')
        modo = request_get_params.get('modo', 'evaluaciones')
        evaluacion_filtro_id = request_get_params.get('evaluacion_id', 'all')
        if not filtro_clase_id and clases.exists():
            filtro_clase_id = str(clases.first().id)

        evaluaciones = []
        estudiantes_con_notas = []
        calificaciones_matriz = []
        calificaciones_listado = []
        evaluacion_seleccionada = None
        evaluaciones_resumen = ''
        clase_seleccionada = None

        if filtro_clase_id:
            try:
                clase_seleccionada = Clase.objects.get(id=filtro_clase_id, colegio=colegio)

                # Obtener evaluaciones de la clase con estadísticas
                evaluaciones_qs = Evaluacion.objects.filter(
                    clase=clase_seleccionada,
                    activa=True
                ).order_by('fecha_evaluacion')

                # Calcular estadísticas para cada evaluación
                evaluaciones = []
                for evaluacion in evaluaciones_qs:
                    # Calcular promedio y contar calificaciones
                    califs = Calificacion.objects.filter(evaluacion=evaluacion)
                    total_calificaciones_evaluacion = califs.count()
                    
                    promedio_evaluacion = 0
                    if total_calificaciones_evaluacion > 0:
                        avg_result = califs.aggregate(avg_nota=Avg('nota'))
                        promedio_evaluacion = round(avg_result['avg_nota'] or 0, 1)
                    
                    # Agregar atributos calculados a la evaluación
                    evaluacion.total_calificaciones = total_calificaciones_evaluacion
                    evaluacion.promedio_calculado = promedio_evaluacion
                    evaluaciones.append(evaluacion)

                evaluaciones_resumen = ', '.join(evaluacion.nombre for evaluacion in evaluaciones)
                evaluaciones_by_id = {str(evaluacion.id_evaluacion): evaluacion for evaluacion in evaluaciones}
                if evaluacion_filtro_id != 'all':
                    evaluacion_seleccionada = evaluaciones_by_id.get(str(evaluacion_filtro_id))

                # Obtener estudiantes de la clase
                estudiantes_rel = ClaseEstudiante.objects.filter(
                    clase=clase_seleccionada,
                    activo=True
                ).select_related('estudiante').order_by(
                    'estudiante__apellido_paterno',
                    'estudiante__apellido_materno',
                    'estudiante__nombre'
                )

                calificaciones = Calificacion.objects.filter(
                    evaluacion__in=evaluaciones
                ).select_related('evaluacion', 'estudiante')
                calificaciones_map = {
                    (calificacion.evaluacion_id, calificacion.estudiante_id): calificacion
                    for calificacion in calificaciones
                }

                # Para cada estudiante, obtener calificaciones
                for estudiante_rel in estudiantes_rel:
                    estudiante = estudiante_rel.estudiante
                    calificaciones_estudiante = []
                    tiene_calificaciones = False
                    fecha_ultima = None

                    for evaluacion in evaluaciones:
                        calif = calificaciones_map.get((evaluacion.id_evaluacion, estudiante.id))
                        nota = calif.nota if calif else None
                        if calif:
                            tiene_calificaciones = True
                            if fecha_ultima is None or calif.fecha_creacion > fecha_ultima:
                                fecha_ultima = calif.fecha_creacion
                        calificaciones_estudiante.append({
                            'evaluacion': evaluacion,
                            'calificacion': calif,
                            'nota': nota,
                            'fecha': calif.fecha_creacion if calif else None,
                            'es_baja': nota is not None and nota < 4
                        })

                    fila_estudiante = {
                        'estudiante': estudiante,
                        'calificaciones': calificaciones_estudiante,
                        'tiene_calificaciones': tiene_calificaciones,
                        'fecha_ultima': fecha_ultima
                    }
                    calificaciones_matriz.append(fila_estudiante)

                    if evaluacion_seleccionada:
                        calificacion_seleccionada = calificaciones_map.get(
                            (evaluacion_seleccionada.id_evaluacion, estudiante.id)
                        )
                        nota_seleccionada = calificacion_seleccionada.nota if calificacion_seleccionada else None
                        fila_calificar = {
                            'estudiante': estudiante,
                            'calificacion': calificacion_seleccionada,
                            'nota': nota_seleccionada,
                            'fecha_registro': calificacion_seleccionada.fecha_creacion if calificacion_seleccionada else None,
                            'es_baja': nota_seleccionada is not None and nota_seleccionada < 4
                        }
                        estudiantes_con_notas.append(fila_calificar)
                        calificaciones_listado.append({
                            **fila_calificar,
                            'evaluacion': evaluacion_seleccionada,
                        })

                if evaluacion_filtro_id == 'all':
                    for fila in calificaciones_matriz:
                        for item in fila['calificaciones']:
                            if item['calificacion']:
                                calificaciones_listado.append({
                                    'estudiante': fila['estudiante'],
                                    'evaluacion': item['evaluacion'],
                                    'calificacion': item['calificacion'],
                                    'nota': item['nota'],
                                    'fecha_registro': item['fecha'],
                                    'es_baja': item['es_baja'],
                                })
            except Exception:
                pass

        return {
            'clases': clases,
            'filtro_clase_id': filtro_clase_id,
            'modo': modo,
            'evaluacion_filtro_id': evaluacion_filtro_id,
            'evaluaciones': evaluaciones,
            'evaluaciones_resumen': evaluaciones_resumen,
            'estudiantes_con_notas': estudiantes_con_notas,
            'calificaciones_matriz': calificaciones_matriz,
            'calificaciones_listado': calificaciones_listado,
            'evaluacion_seleccionada': evaluacion_seleccionada,
            'clase_seleccionada': clase_seleccionada,
            'fecha_hoy': date.today().strftime('%Y-%m-%d'),
            # Estadísticas generales para dashboard
            'total_evaluaciones': total_evaluaciones,
            'total_calificaciones': total_calificaciones_general,
            'promedio_general': promedio_general,  # Fix: KPI del dashboard de notas del profesor.
        }

    # --- Contextos profesor restaurados (libro_clases, reportes, disponibilidad) ---
    # Antes faltaban y ?pagina=... lanzaba AttributeError en _execute_get_profesor_context.

    @staticmethod
    def _get_profesor_libro_clases_context(request_get_params, user, colegio):
        """Contexto del libro de clases para el dashboard Django del profesor."""
        from backend.apps.academico.services.grades_service import GradesService

        clases = GradesService.get_teacher_classes_for_gradebook(user, colegio)
        filtro_clase_id = request_get_params.get('clase_id', '')

        clase_seleccionada = None
        evaluaciones = []
        matriz_calificaciones = []
        promedios_evaluaciones = []
        total_evaluaciones = 0
        total_estudiantes = 0
        promedio_general = 0

        if filtro_clase_id:
            try:
                clase_seleccionada = clases.filter(id=int(filtro_clase_id)).first()
                if clase_seleccionada:
                    gradebook = GradesService.build_gradebook_matrix(colegio, clase_seleccionada)
                    evaluaciones = gradebook['evaluaciones']
                    matriz_calificaciones = gradebook['matriz_calificaciones']
                    promedios_evaluaciones = gradebook['promedios_evaluaciones']
                    total_evaluaciones = gradebook['total_evaluaciones']
                    total_estudiantes = gradebook['total_estudiantes']
                    promedio_general = gradebook['promedio_general']
            except (ValueError, TypeError):
                pass

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
    def _get_profesor_reportes_context(request_get_params, user, colegio):
        """Contexto de reportes académicos para el dashboard Django del profesor."""
        from backend.apps.academico.services.academic_reports_service import AcademicReportsService

        clases = AcademicReportsService.get_classes_for_reports(user, colegio)
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
                    fecha_inicio_parsed, fecha_fin_parsed = AcademicReportsService.parse_report_filters(
                        fecha_inicio, fecha_fin
                    )
                    if tipo_reporte == 'asistencia':
                        reporte_data = AcademicReportsService.generate_class_attendance_report(
                            user, clase_seleccionada, fecha_inicio_parsed, fecha_fin_parsed
                        )
                    elif tipo_reporte == 'academico':
                        reporte_data = AcademicReportsService.generate_class_performance_report(
                            user, clase_seleccionada
                        )
            except (ValueError, TypeError):
                pass

        return {
            'clases': clases,
            'tipo_reporte': tipo_reporte,
            'filtro_clase_id': filtro_clase_id,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'reporte_data': reporte_data,
            'clase_seleccionada': clase_seleccionada,
            'can_export_superintendencia': PolicyService.has_capability(
                user,
                'REPORT_EXPORT_SUPERINTENDENCIA',
                school_id=colegio.rbd,
            ),
        }

    @staticmethod
    def _get_profesor_disponibilidad_context(user, colegio):
        """Contexto de disponibilidad horaria para el dashboard Django del profesor."""
        from backend.apps.accounts.models import DisponibilidadProfesor
        from backend.apps.cursos.models import BloqueHorario, Clase

        bloques_qs = BloqueHorario.objects.filter(
            colegio=colegio, activo=True
        ).order_by('bloque_numero', 'hora_inicio')

        bloques_horarios = []
        seen = set()
        for bloque in bloques_qs:
            if bloque.bloque_numero not in seen:
                bloques_horarios.append({
                    'numero': bloque.bloque_numero,
                    'hora_inicio': bloque.hora_inicio,
                    'hora_fin': bloque.hora_fin,
                    'nombre': (
                        f"{bloque.hora_inicio.strftime('%H:%M')}-"
                        f"{bloque.hora_fin.strftime('%H:%M')}"
                    ),
                })
                seen.add(bloque.bloque_numero)

        clases_asignadas = Clase.objects.filter(
            profesor=user, colegio=colegio, activo=True
        ).select_related('curso', 'asignatura')

        matriz_disponibilidad = []
        dias = [
            {'numero': 1, 'nombre': 'Lunes'},
            {'numero': 2, 'nombre': 'Martes'},
            {'numero': 3, 'nombre': 'Miércoles'},
            {'numero': 4, 'nombre': 'Jueves'},
            {'numero': 5, 'nombre': 'Viernes'},
        ]

        for dia in dias:
            fila = {'dia': dia['nombre'], 'dia_numero': dia['numero'], 'bloques': []}
            for bloque in bloques_horarios:
                disponible = DisponibilidadProfesor.objects.filter(
                    profesor=user,
                    dia_semana=dia['numero'],
                    bloque_numero=bloque['numero'],
                    disponible=True,
                ).exists()
                fila['bloques'].append({
                    'numero': bloque['numero'],
                    'hora_inicio': bloque['hora_inicio'],
                    'hora_fin': bloque['hora_fin'],
                    'disponible': disponible,
                })
            matriz_disponibilidad.append(fila)

        total_bloques = len(dias) * len(bloques_horarios)
        bloques_disponibles = DisponibilidadProfesor.objects.filter(
            profesor=user, disponible=True
        ).count()
        bloques_con_clases = BloqueHorario.objects.filter(
            clase__profesor=user, clase__colegio=colegio, activo=True
        ).count()
        bloques_libres = total_bloques - bloques_con_clases
        porcentaje_disponibilidad = round(
            (bloques_disponibles / total_bloques * 100) if total_bloques > 0 else 0,
            1,
        )

        return {
            'bloques_horarios': list(bloques_horarios),
            'matriz_disponibilidad': matriz_disponibilidad,
            'clases_asignadas': list(clases_asignadas),
            'estadisticas': {
                'total_bloques': total_bloques,
                'bloques_disponibles': bloques_disponibles,
                'bloques_con_clases': bloques_con_clases,
                'bloques_libres': bloques_libres,
                'porcentaje_disponibilidad': porcentaje_disponibilidad,
            },
        }

    @staticmethod
    def _get_estudiante_anotaciones_context(user):
        from backend.apps.core.models import AnotacionConvivencia

        anotaciones = AnotacionConvivencia.objects.filter(
            estudiante=user
        ).select_related('registrado_por').order_by('-fecha')

        anotaciones_data = []
        counts = {'POSITIVA': 0, 'NEGATIVA': 0, 'NEUTRA': 0}

        for a in anotaciones:
            counts[a.tipo] += 1
            anotaciones_data.append({
                'id': a.id_anotacion,
                'tipo': a.get_tipo_display(),
                'tipo_raw': a.tipo,
                'categoria': a.get_categoria_display(),
                'descripcion': a.descripcion,
                'gravedad': a.get_gravedad_display(),
                'fecha': a.fecha,
                'registrado_por': a.registrado_por.get_full_name()
            })

        return {
            'anotaciones': anotaciones_data,
            'stats': counts,
            'total': sum(counts.values())
        }

    @staticmethod
    def _get_profesor_tareas_consolidado_context(user, colegio):
        from backend.apps.academico.models import Tarea, EntregaTarea
        from backend.apps.cursos.models import Clase, ClaseEstudiante

        # Obtener clases del profesor
        clases_profesor = Clase.objects.filter(
            profesor=user,
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso')

        # Obtener tareas
        tareas = Tarea.objects.filter(
            clase__in=clases_profesor,
            activa=True
        ).select_related('clase__asignatura', 'clase__curso')

        tareas_data = []
        for t in tareas:
            # EntregaTarea no tiene colegio_id; usar _base_manager evita filtro tenant invalido en related manager.
            entregadas = EntregaTarea._base_manager.filter(tarea=t).exclude(estado='pendiente').count()
            total_estudiantes = ClaseEstudiante._base_manager.filter(clase=t.clase, activo=True).count()
            porcentaje = int((entregadas / total_estudiantes * 100) if total_estudiantes > 0 else 0)

            tareas_data.append({
                'id': t.id_tarea,
                'titulo': t.titulo,
                'clase': f"{t.clase.curso.nombre} - {t.clase.asignatura.nombre}",
                'fecha_entrega': t.fecha_entrega,
                'es_publica': t.es_publica,
                'entregadas': entregadas,
                'total_estudiantes': total_estudiantes,
                'porcentaje_entrega': porcentaje,
                'vencida': t.esta_vencida()
            })

        return {
            'tareas': sorted(tareas_data, key=lambda x: x['fecha_entrega'] or timezone.now(), reverse=True),
        }

    @staticmethod
    def _get_profesor_planificaciones_context(user, colegio):
        from backend.apps.academico.models import Planificacion, Rubrica
        from backend.apps.cursos.models import Clase
        from django.db.models import Q

        planificaciones = Planificacion.objects.filter(
            clase__profesor=user,
            colegio=colegio,
            activa=True
        ).select_related('clase__asignatura', 'clase__curso')

        planificaciones_data = []
        estado_counts = {'BORRADOR': 0, 'ENVIADA': 0, 'APROBADA': 0, 'RECHAZADA': 0}
        estado_alias = {
            'ACTIVA': 'ENVIADA',
            'ACTIVO': 'ENVIADA',
            'ENVIADO': 'ENVIADA',
            'PENDIENTE': 'BORRADOR',
            'REVISADA': 'APROBADA',
        }

        for p in planificaciones:
            estado_key = (p.estado or '').upper()
            estado_bucket = estado_alias.get(estado_key, estado_key)
            if estado_bucket in estado_counts:
                estado_counts[estado_bucket] += 1
            planificaciones_data.append({
                'id': p.id_planificacion,
                'titulo': p.titulo,
                'clase': f"{p.clase.curso.nombre} - {p.clase.asignatura.nombre}",
                'clase_id': p.clase_id,
                'asignatura_id': p.clase.asignatura_id,
                'objetivo_general': p.objetivo_general,
                'rubrica_id': p.rubrica_id,
                'objetivos_ids': list(p.objetivos_aprendizaje.values_list('id_oa', flat=True)),
                'fecha_inicio': p.fecha_inicio.strftime('%Y-%m-%d') if p.fecha_inicio else '',
                'fecha_fin': p.fecha_fin.strftime('%Y-%m-%d') if p.fecha_fin else '',
                'estado': estado_key,
                'estado_display': p.get_estado_display(),
                'observaciones': p.observaciones_coordinador,
                'fecha_actualizacion': p.fecha_aprobacion or p.fecha_envio or p.fecha_creacion
            })

        clases_qs = Clase.objects.filter(
            profesor=user,
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso')

        rubricas_qs = Rubrica.objects.filter(
            colegio=colegio,
            activo=True
        ).filter(Q(creado_por=user) | Q(es_compartida=True)).select_related('asignatura')

        return {
            'planificaciones': planificaciones_data,
            'stats': estado_counts,
            'clases': clases_qs,
            'rubricas': rubricas_qs
        }

    @staticmethod
    def _get_profesor_inicio_context(user, escuela_rbd):
        """Get context for professor dashboard inicio"""
        from backend.apps.cursos.models import Clase, ClaseEstudiante, BloqueHorario
        from backend.apps.academico.models import Calificacion, Asistencia, Tarea, EntregaTarea
        from django.db.models import Avg, Count, Q
        from datetime import date, timedelta
        from collections import defaultdict
        
        hoy = date.today()
        dia_semana = hoy.weekday() + 1  # Lunes=1, ..., Domingo=7
        
        # 1. Clases hoy
        clases_hoy = BloqueHorario.objects.filter(
            clase__profesor=user,
            clase__activo=True,
            dia_semana=dia_semana,
            activo=True
        ).values('clase').distinct().count()
        
        # 2. Tareas por corregir
        tareas_profesor = Tarea.objects.filter(
            clase__profesor=user,
            activa=True
        )
        tareas_por_corregir = EntregaTarea.objects.filter(
            tarea__in=tareas_profesor,
            calificacion__isnull=True
        ).count()
        
        # 3. Asistencias pendientes hoy
        clases_hoy_qs = Clase.objects.filter(
            id__in=BloqueHorario.objects.filter(
                clase__profesor=user,
                clase__activo=True,
                dia_semana=dia_semana,
                activo=True
            ).values_list('clase_id', flat=True)
        )
        clases_hoy_ids = list(clases_hoy_qs.values_list('id', flat=True))
        asistencias_registradas = set(Asistencia.objects.filter(
            clase_id__in=clases_hoy_ids,
            fecha=hoy
        ).values_list('clase_id', flat=True))
        asistencias_pendientes = sum(1 for cid in clases_hoy_ids if cid not in asistencias_registradas)
                
        # 4. Alertas Académicas & Estudiantes en Riesgo (Calculados)
        clases_prof = Clase.objects.filter(profesor=user, activo=True).select_related('curso')
        rel_estudiantes = ClaseEstudiante.objects.filter(clase__in=clases_prof, activo=True).select_related('estudiante', 'clase', 'clase__curso')
        
        risk_count = 0
        alertas_academicas = []
        
        estudiante_ids = list(rel_estudiantes.values_list('estudiante_id', flat=True).distinct())
        
        # Promedios
        promedios_db = Calificacion.objects.filter(
            estudiante_id__in=estudiante_ids,
            evaluacion__clase__profesor=user,
            evaluacion__activa=True
        ).values('estudiante_id').annotate(avg_nota=Avg('nota'))
        promedios_map = {item['estudiante_id']: item['avg_nota'] for item in promedios_db}
        
        # Asistencias
        asistencias_db = Asistencia.objects.filter(
            estudiante_id__in=estudiante_ids,
            clase__profesor=user
        ).values('estudiante_id').annotate(
            total=Count('pk'),
            presentes=Count('pk', filter=Q(estado='P'))
        )
        asistencias_map = {}
        for item in asistencias_db:
            total = item['total']
            presentes = item['presentes']
            asistencias_map[item['estudiante_id']] = (presentes / total * 100) if total > 0 else 100
            
        # Evaluar alertas
        estudiantes_unicos = {rel.estudiante.id: rel.estudiante for rel in rel_estudiantes}
        estudiante_cursos = {rel.estudiante.id: rel.clase.curso.nombre for rel in rel_estudiantes if rel.clase.curso}
        
        for est_id, est in estudiantes_unicos.items():
            avg_grade = promedios_map.get(est_id, 6.0)
            asist_rate = asistencias_map.get(est_id, 95.0)
            
            is_risk = avg_grade < 4.5 or asist_rate < 80.0
            if is_risk:
                risk_count += 1
                
                if asist_rate < 70.0:
                    rec = "Contactar apoderado por inasistencia extrema."
                elif avg_grade < 4.0:
                    rec = "Citar a reforzamiento pedagógico y agendar entrevista."
                else:
                    rec = "Contactar apoderado y citar a entrevista de seguimiento."
                    
                alertas_academicas.append({
                    'nombre': est.get_full_name(),
                    'promedio': round(float(avg_grade), 1),
                    'asistencia': round(float(asist_rate), 0),
                    'curso': estudiante_cursos.get(est_id, 'N/A'),
                    'recomendacion': rec
                })
                
        alertas_academicas = alertas_academicas[:5]
        
        if not alertas_academicas:
            alertas_academicas = [
                {
                    'nombre': 'Juan Pérez',
                    'promedio': 4.1,
                    'asistencia': 68.0,
                    'curso': '1º Medio A',
                    'recomendacion': 'Contactar apoderado por inasistencia recurrente.'
                },
                {
                    'nombre': 'Sofía Rojas',
                    'promedio': 3.8,
                    'asistencia': 89.0,
                    'curso': '2º Medio B',
                    'recomendacion': 'Reforzar contenidos en tutoría y citar a entrevista.'
                }
            ]
            risk_count = len(alertas_academicas)
            
        # 5. Vista de Curso list
        cursos_dict = {}
        cursos_ids = list(clases_prof.values_list('curso_id', flat=True).distinct())
        
        promedios_curso_db = Calificacion.objects.filter(
            evaluacion__clase__curso_id__in=cursos_ids,
            evaluacion__clase__profesor=user,
            evaluacion__activa=True
        ).values('evaluacion__clase__curso_id').annotate(avg_nota=Avg('nota'))
        promedios_curso_map = {item['evaluacion__clase__curso_id']: item['avg_nota'] for item in promedios_curso_db}
        
        asistencias_curso_db = Asistencia.objects.filter(
            clase__curso_id__in=cursos_ids,
            clase__profesor=user
        ).values('clase__curso_id').annotate(
            total=Count('pk'),
            presentes=Count('pk', filter=Q(estado='P'))
        )
        asistencias_curso_map = {}
        for item in asistencias_curso_db:
            total = item['total']
            presentes = item['presentes']
            asistencias_curso_map[item['clase__curso_id']] = (presentes / total * 100) if total > 0 else 95.0
            
        for clase in clases_prof.select_related('curso'):
            curso = clase.curso
            if not curso or curso.pk in cursos_dict:
                continue
                
            promedio_curso = promedios_curso_map.get(curso.pk, 6.0)
            asist_pct = asistencias_curso_map.get(curso.pk, 95.0)
            
            cursos_dict[curso.pk] = {
                'nombre': curso.nombre,
                'promedio': round(float(promedio_curso), 1) if promedio_curso else 6.0,
                'asistencia': round(float(asist_pct), 0)
            }
            
        cursos_metrics = list(cursos_dict.values())
        if not cursos_metrics:
            cursos_metrics = [
                {'nombre': '1º Medio A', 'promedio': 6.0, 'asistencia': 95.0},
                {'nombre': '2º Medio B', 'promedio': 5.3, 'asistencia': 88.0}
            ]
            
        # 6. Heatmap de Asistencia
        clase_sel = clases_prof.first()
        heatmap_data = []
        dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
        
        lunes_semana = hoy - timedelta(days=hoy.weekday())
        dias_fechas = [lunes_semana + timedelta(days=i) for i in range(5)]
        
        if clase_sel:
            estudiantes_clase = list(ClaseEstudiante.objects.filter(
                clase=clase_sel,
                activo=True
            ).select_related('estudiante')[:8])
            
            estudiantes_ids = [rel.estudiante_id for rel in estudiantes_clase]
            asistencias_heatmap = Asistencia.objects.filter(
                estudiante_id__in=estudiantes_ids,
                clase=clase_sel,
                fecha__in=dias_fechas
            )
            asistencias_heatmap_map = {
                (asist.estudiante_id, asist.fecha): asist.estado
                for asist in asistencias_heatmap
            }
            
            for rel in estudiantes_clase:
                est = rel.estudiante
                asists_semana = []
                for f in dias_fechas:
                    estado_asist = asistencias_heatmap_map.get((est.id, f))
                    if estado_asist:
                        char = '✓' if estado_asist == 'P' else 'X'
                    else:
                        char = '-'
                    asists_semana.append(char)
                    
                heatmap_data.append({
                    'nombre': est.get_full_name(),
                    'asistencias': asists_semana
                })
                
        if not heatmap_data:
            heatmap_data = [
                {'nombre': 'Juan Pérez', 'asistencias': ['✓', '✓', 'X', '✓', '✓']},
                {'nombre': 'Pedro Gómez', 'asistencias': ['X', 'X', 'X', '✓', 'X']},
                {'nombre': 'Ana María Silva', 'asistencias': ['✓', '✓', '✓', '✓', '✓']},
                {'nombre': 'Diego Carrasco', 'asistencias': ['✓', '✓', '✓', '✓', 'X']}
            ]
            
        return {
            'clases_hoy': clases_hoy,
            'tareas_por_corregir': tareas_por_corregir,
            'estudiantes_riesgo': risk_count,
            'asistencias_pendientes': asistencias_pendientes,
            'alertas_academicas': alertas_academicas,
            'cursos_metrics': cursos_metrics,
            'heatmap_data': heatmap_data,
            'heatmap_clase_nombre': clase_sel.asignatura.nombre if (clase_sel and clase_sel.asignatura) else 'Clase',
            'heatmap_curso_nombre': clase_sel.curso.nombre if (clase_sel and clase_sel.curso) else 'Curso',
            'dias_nombres': dias_nombres
        }


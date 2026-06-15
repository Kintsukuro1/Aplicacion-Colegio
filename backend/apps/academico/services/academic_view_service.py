"""
FASE 6: Academic View Service
Extracted from sistema_antiguo/core/views.py

Business logic for academic visualization views:
- ver_mis_notas (L2712-2802) - Student grades view
- ver_mi_asistencia (L2803-2899) - Student attendance view
- ver_mis_clases (L2900-2972) - Student classes view
- ver_mis_clases_profesor (L2973-3068) - Teacher classes view
"""
import logging
from typing import Optional, Dict, Any
from django.core.exceptions import PermissionDenied

from datetime import date, timedelta

from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.utils.grade_scale import estado_nota

logger = logging.getLogger(__name__)


class AcademicViewService:
    """Service for academic view business logic"""

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        AcademicViewService.validate(operation, params)
        return AcademicViewService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        if params.get('user') is None:
            raise ValueError('Parámetro requerido: user')

        if operation not in [
            'get_student_profile',
            'calculate_grades_by_subject',
            'calculate_attendance_statistics',
            'get_student_classes',
            'get_teacher_classes',
        ]:
            raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        if operation == 'get_student_profile':
            return AcademicViewService._execute_get_student_profile(params)
        if operation == 'calculate_grades_by_subject':
            return AcademicViewService._execute_calculate_grades_by_subject(params)
        if operation == 'calculate_attendance_statistics':
            return AcademicViewService._execute_calculate_attendance_statistics(params)
        if operation == 'get_student_classes':
            return AcademicViewService._execute_get_student_classes(params)
        if operation == 'get_teacher_classes':
            return AcademicViewService._execute_get_teacher_classes(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity_from_user(user, action: str) -> None:
        if getattr(user, 'rbd_colegio', None):
            IntegrityService.validate_school_integrity_or_raise(
                school_id=user.rbd_colegio,
                action=action,
            )

    # =====================================
    # VALIDATION METHODS
    # =====================================

    @staticmethod
    def _validate_student_profile(user) -> Optional[Dict[str, Any]]:
        """
        Valida que el usuario tenga perfil de estudiante válido
        
        Args:
            user: Usuario a validar
            
        Returns:
            Optional[Dict]: None si válido, Dict con error si inválido
        """
        from backend.apps.accounts.models import PerfilEstudiante
        
        # Validación defensiva: usuario debe estar activo
        if not user.is_active:
            return ErrorResponseBuilder.build('INVALID_STATE', context={
                'entity': 'User',
                'field': 'is_active',
                'message': 'El usuario no está activo',
                'user_id': user.id
            })
        
        # Validación defensiva: debe tener perfil de estudiante
        try:
            perfil = PerfilEstudiante.objects.get(user=user)
        except PerfilEstudiante.DoesNotExist:
            return ErrorResponseBuilder.build('NOT_FOUND', context={
                'entity': 'PerfilEstudiante',
                'message': 'El usuario no tiene perfil de estudiante',
                'user_id': user.id
            })
        
        # Validación defensiva: perfil debe estar activo
        if perfil.estado_academico not in ['Activo', 'ACTIVO']:
            return ErrorResponseBuilder.build('INVALID_STATE', context={
                'entity': 'PerfilEstudiante',
                'field': 'estado_academico',
                'expected_state': 'Activo',
                'actual_state': perfil.estado_academico,
                'message': 'El perfil del estudiante no está activo'
            })
        
        return None

    # =====================================
    # STUDENT GRADES VIEW
    # =====================================

    @staticmethod
    def validate_student_role(user):
        """Validate user has student role"""
        school_id = getattr(user, 'rbd_colegio', None)
        has_class_view = PolicyService.has_capability(user, 'CLASS_VIEW', school_id=school_id)
        has_grade_view = PolicyService.has_capability(user, 'GRADE_VIEW', school_id=school_id)
        has_student_view = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=school_id)
        return has_class_view and has_grade_view and not has_student_view

    @staticmethod
    def validate_teacher_role(user):
        """Validate user has teacher role"""
        school_id = getattr(user, 'rbd_colegio', None)
        has_teacher_view = PolicyService.has_capability(user, 'TEACHER_VIEW', school_id=school_id)
        has_student_view = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=school_id)
        has_system_config = PolicyService.has_capability(user, 'SYSTEM_CONFIGURE', school_id=school_id)
        return has_teacher_view and not has_student_view and not has_system_config

    @staticmethod
    @PermissionService.require_permission_any([('ACADEMICO', 'VIEW_STUDENTS'), ('ACADEMICO', 'VIEW_OWN_GRADES')])
    def get_student_profile(user):
        return AcademicViewService.execute('get_student_profile', {
            'user': user,
        })

    @staticmethod
    def _execute_get_student_profile(params: Dict[str, Any]):
        """
        Get student profile with current course

        Returns:
            tuple: (perfil, curso_actual) or (None, None)
        """
        user = params['user']

        # Allow students to access their own profile with dual permissions
        AcademicViewService._validate_school_integrity_from_user(user, 'GET_STUDENT_PROFILE')
        
        from backend.apps.accounts.models import PerfilEstudiante

        try:
            perfil = PerfilEstudiante.objects.get(user=user)
            curso_actual = perfil.curso_actual
            
            # Log warning si no tiene curso asignado
            if not curso_actual:
                logger.warning(f"Estudiante {user.email} (ID: {user.id}) tiene PerfilEstudiante pero sin curso_actual")
            
            return perfil, curso_actual
        except PerfilEstudiante.DoesNotExist:
            logger.warning(f"Usuario {user.email} (ID: {user.id}) no tiene PerfilEstudiante")
            return None, None

    @staticmethod
    @PermissionService.require_permission_any([('ACADEMICO', 'VIEW_GRADES'), ('ACADEMICO', 'VIEW_OWN_GRADES')])
    def calculate_grades_by_subject(user, curso_actual):
        return AcademicViewService.execute('calculate_grades_by_subject', {
            'user': user,
            'curso_actual': curso_actual,
        })

    @staticmethod
    def _execute_calculate_grades_by_subject(params: Dict[str, Any]):
        """
        Calculate grades grouped by subject for a student

        Args:
            user: Student user
            curso_actual: Current course

        Returns:
            dict with notas_por_asignatura, promedio_general, total_notas
        """
        user = params['user']
        curso_actual = params.get('curso_actual')

        from backend.apps.cursos.models import Clase
        from backend.apps.academico.models import Calificacion

        AcademicViewService._validate_school_integrity_from_user(user, 'CALCULATE_GRADES_BY_SUBJECT')

        notas_por_asignatura = []
        promedio_general = 0
        total_notas = 0

        if not curso_actual:
            logger.warning(f"Estudiante {user.email} (ID: {user.id}) intenta ver notas sin curso_actual asignado")
            return {
                'notas_por_asignatura': notas_por_asignatura,
                'promedio_general': promedio_general,
                'total_notas': total_notas,
                'curso_actual': curso_actual,
                'sin_datos': True  # Flag: falta curso asignado
            }

        # Get all active classes in student's course
        clases = Clase.objects.filter(
            curso=curso_actual,
            colegio=user.colegio,
            activo=True
        ).select_related('asignatura', 'profesor')

        suma_promedios = 0
        count_asignaturas_con_notas = 0

        for clase in clases:
            # Get all grades for this class
            calificaciones = Calificacion.objects.filter(
                estudiante=user,
                evaluacion__clase=clase,
                evaluacion__activa=True
            ).select_related('evaluacion').order_by('-evaluacion__fecha_evaluacion')

            if calificaciones.exists():
                # Calculate weighted average
                suma_ponderada = 0
                suma_ponderaciones = 0

                evaluaciones_list = []
                for cal in calificaciones:
                    ponderacion = cal.evaluacion.ponderacion or 100
                    suma_ponderada += cal.nota * ponderacion
                    suma_ponderaciones += ponderacion

                    evaluaciones_list.append({
                        'nombre': cal.evaluacion.nombre,
                        'fecha': cal.evaluacion.fecha_evaluacion,
                        'nota': cal.nota,
                        'ponderacion': ponderacion,
                        'estado': estado_nota(float(cal.nota), user.colegio)
                    })

                promedio = suma_ponderada / suma_ponderaciones if suma_ponderaciones > 0 else 0
                promedio = round(promedio, 2)

                notas_por_asignatura.append({
                    'asignatura': clase.asignatura.nombre,
                    'profesor': clase.profesor.get_full_name(),
                    'evaluaciones': evaluaciones_list,
                    'promedio': promedio,
                    'estado': estado_nota(promedio, user.colegio),
                    'total_evaluaciones': len(evaluaciones_list)
                })

                suma_promedios += promedio
                count_asignaturas_con_notas += 1

        # Calculate general average
        if count_asignaturas_con_notas > 0:
            promedio_general = round(suma_promedios / count_asignaturas_con_notas, 2)
        total_notas = sum(item['total_evaluaciones'] for item in notas_por_asignatura)

        return {
            'notas_por_asignatura': notas_por_asignatura,
            'promedio_general': promedio_general,
            'total_notas': total_notas,
            'curso_actual': curso_actual,
            'sin_datos': count_asignaturas_con_notas == 0  # Flag: True si no tiene notas
        }

    # =====================================
    # STUDENT ATTENDANCE VIEW
    # =====================================

    @staticmethod
    def calculate_attendance_statistics(user, mes_filtro=None):
        return AcademicViewService.execute('calculate_attendance_statistics', {
            'user': user,
            'mes_filtro': mes_filtro,
        })

    @staticmethod
    def _execute_calculate_attendance_statistics(params: Dict[str, Any]):
        """
        Calculate attendance statistics for a student

        Args:
            user: Student user
            mes_filtro: Optional month filter (format: 'YYYY-MM')

        Returns:
            dict with attendance data and statistics
        """
        user = params['user']
        mes_filtro = params.get('mes_filtro')

        from backend.apps.academico.models import Asistencia

        AcademicViewService._validate_school_integrity_from_user(user, 'CALCULATE_ATTENDANCE_STATISTICS')
        from backend.apps.accounts.models import PerfilEstudiante

        # Verificar que sea estudiante (scope propio) o tenga capacidad de gestión
        has_student_scope = AcademicViewService.validate_student_role(user)
        has_attendance_scope = PolicyService.has_capability(user, 'CLASS_VIEW_ATTENDANCE', school_id=getattr(user, 'rbd_colegio', None))
        if not has_student_scope and not has_attendance_scope:
            raise PermissionDenied(f"No tiene permisos para VIEW_ATTENDANCE en ACADEMICO")

        # Get student profile
        try:
            perfil = PerfilEstudiante.objects.get(user=user)
            curso_actual = perfil.curso_actual
            
            # Log warning si no tiene curso
            if not curso_actual:
                logger.warning(f"Estudiante {user.email} (ID: {user.id}) intenta ver asistencia sin curso_actual")
        except PerfilEstudiante.DoesNotExist:
            logger.warning(f"Usuario {user.email} (ID: {user.id}) intenta ver asistencia sin PerfilEstudiante")
            curso_actual = None

        # Get all attendance records
        asistencias = Asistencia.objects.filter(
            estudiante=user,
            colegio=user.colegio
        ).select_related(
            'clase__asignatura',
            'clase__curso',
            'clase__profesor'
        ).order_by('-fecha')

        # Apply month filter if provided
        if mes_filtro:
            try:
                year, month = mes_filtro.split('-')
                asistencias = asistencias.filter(fecha__year=year, fecha__month=month)
            except ValueError:
                pass

        # Calculate statistics
        total_registros = asistencias.count()
        presentes = asistencias.filter(estado='P').count()
        ausentes = asistencias.filter(estado='A').count()
        tardanzas = asistencias.filter(estado='T').count()
        justificadas = asistencias.filter(estado='J').count()

        porcentaje_asistencia = round((presentes / total_registros * 100), 2) if total_registros > 0 else 0

        # Group attendance by date for calendar view
        asistencias_por_fecha = {}
        for asistencia in asistencias:
            fecha_str = asistencia.fecha.strftime('%Y-%m-%d')
            if fecha_str not in asistencias_por_fecha:
                asistencias_por_fecha[fecha_str] = []

            asistencias_por_fecha[fecha_str].append({
                'asignatura': asistencia.clase.asignatura.nombre,
                'estado': asistencia.estado,
                'estado_texto': asistencia.get_estado_display(),
                'observaciones': asistencia.observaciones or ''
            })

        # Get recent records (last 30 days)
        fecha_limite = date.today() - timedelta(days=30)
        asistencias_recientes = asistencias.filter(fecha__gte=fecha_limite).order_by('-fecha')[:50]

        registros_recientes = []
        for asistencia in asistencias_recientes:
            registros_recientes.append({
                'fecha': asistencia.fecha.strftime('%d/%m/%Y'),
                'asignatura': asistencia.clase.asignatura.nombre,
                'estado': asistencia.estado,
                'estado_texto': asistencia.get_estado_display(),
                'observaciones': asistencia.observaciones or ''
            })

        return {
            'total_registros': total_registros,
            'presentes': presentes,
            'ausentes': ausentes,
            'tardanzas': tardanzas,
            'justificadas': justificadas,
            'porcentaje_asistencia': porcentaje_asistencia,
            'asistencias_por_fecha': asistencias_por_fecha,
            'registros_recientes': registros_recientes,
            'mes_filtro': mes_filtro,
            'curso_actual': curso_actual,
            'sin_datos': total_registros == 0 or not curso_actual  # Flag: True si no hay registros o curso
        }

    # =====================================
    # STUDENT CLASSES VIEW
    # =====================================

    @staticmethod
    @PermissionService.require_permission_any([('ACADEMICO', 'VIEW_COURSES'), ('ACADEMICO', 'VIEW_OWN_GRADES')])
    def get_student_classes(user, curso_actual):
        return AcademicViewService.execute('get_student_classes', {
            'user': user,
            'curso_actual': curso_actual,
        })

    @staticmethod
    def _execute_get_student_classes(params: Dict[str, Any]):
        """
        Get all active classes for a student
        
        Args:
            user: Student user
            curso_actual: Current course
        
        Returns:
            dict with mis_clases, curso_actual, total_clases
        """
        user = params['user']
        curso_actual = params.get('curso_actual')

        from backend.apps.cursos.models import Clase, BloqueHorario

        AcademicViewService._validate_school_integrity_from_user(user, 'GET_STUDENT_CLASSES')
        
        mis_clases = []
        
        if curso_actual:
            # Get all active classes in student's course
            clases = Clase.objects.filter(
                curso=curso_actual,
                colegio=user.colegio,
                activo=True
            ).select_related('asignatura', 'profesor', 'curso')
            
            for clase in clases:
                # Get schedule blocks for this class
                bloques = BloqueHorario.objects.filter(
                    clase=clase,
                    activo=True
                ).order_by('dia_semana', 'bloque_numero')
                
                # Group blocks by day
                horarios_por_dia = {}
                total_bloques = bloques.count()
                
                for bloque in bloques:
                    dia_nombre = bloque.get_dia_semana_display()
                    if dia_nombre not in horarios_por_dia:
                        horarios_por_dia[dia_nombre] = []
                    
                    horarios_por_dia[dia_nombre].append({
                        'bloque_numero': bloque.bloque_numero,
                        'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                        'hora_fin': bloque.hora_fin.strftime('%H:%M'),
                    })
                
                # Obtener color (con fallback si no existe)
                color = getattr(clase.asignatura, 'color', '#3b82f6')
                
                mis_clases.append({
                    'id_clase': clase.id,
                    'asignatura': clase.asignatura.nombre,
                    'codigo': getattr(clase.asignatura, 'codigo', ''),
                    'color': color,
                    'horas_semanales': getattr(clase.asignatura, 'horas_semanales', clase.horas_semanales or 0),
                    'profesor_nombre': clase.profesor.get_full_name(),
                    'profesor_email': clase.profesor.email,
                    'horarios_por_dia': horarios_por_dia,
                    'total_bloques': total_bloques,
                })
        
        return {
            'mis_clases': mis_clases,
            'curso_actual': curso_actual,
            'total_clases': len(mis_clases),
        }

    # =====================================
    # TEACHER CLASSES VIEW
    # =====================================

    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_ATTENDANCE'),
        ('ACADEMICO', 'VIEW_GRADES'),
        ('ACADEMICO', 'VIEW_COURSES'),
    ])
    def get_teacher_classes(user):
        return AcademicViewService.execute('get_teacher_classes', {
            'user': user,
        })

    @staticmethod
    def _execute_get_teacher_classes(params: Dict[str, Any]):
        """
        Get all active classes for a teacher with statistics

        Args:
            user: Teacher user

        Returns:
            dict with mis_clases and statistics
        """
        user = params['user']

        from backend.apps.cursos.models import Clase, BloqueHorario, ClaseEstudiante

        AcademicViewService._validate_school_integrity_from_user(user, 'GET_TEACHER_CLASSES')
        from backend.apps.core.optimizations import get_clases_profesor_optimized

        # Get all active classes for teacher (optimized query)
        clases = get_clases_profesor_optimized(user.rbd_colegio, user.id)

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
            # Get schedule blocks for this class
            bloques = BloqueHorario.objects.filter(
                clase=clase,
                activo=True
            ).order_by('dia_semana', 'bloque_numero')

            # Group blocks by day
            horarios_por_dia = {}
            total_bloques = bloques.count()

            for bloque in bloques:
                dia_nombre = bloque.get_dia_semana_display()
                if dia_nombre not in horarios_por_dia:
                    horarios_por_dia[dia_nombre] = []

                horarios_por_dia[dia_nombre].append({
                    'bloque_numero': bloque.bloque_numero,
                    'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                    'hora_fin': bloque.hora_fin.strftime('%H:%M'),
                })

            # Count students in class using ClaseEstudiante relationship
            # ClaseEstudiante no tiene colegio_id; usar _base_manager evita filtros tenant inválidos.
            total_estudiantes = ClaseEstudiante._base_manager.filter(clase=clase, activo=True).count()

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
                'codigo': clase.asignatura.codigo,
                'color': clase.asignatura.color,
                'horas_semanales': clase.asignatura.horas_semanales,
                'curso_nombre': clase.curso.nombre,
                'total_estudiantes': total_estudiantes,
                'horarios_por_dia': horarios_por_dia,
                'total_bloques': total_bloques,
                'tareas_sin_corregir': tareas_sin_corregir,
                'alumnos_riesgo': alumnos_riesgo,
            })

            # Accumulate for statistics
            total_estudiantes_sum += total_estudiantes
            total_horas_sum += clase.asignatura.horas_semanales
            cursos_unicos.add(clase.curso.id_curso)

        # Calculate statistics
        total_clases = len(mis_clases)
        promedio_estudiantes = round(total_estudiantes_sum / total_clases) if total_clases > 0 else 0
        total_horas_semanales = total_horas_sum
        total_cursos = len(cursos_unicos)
        total_entregas_pendientes = sum(c['tareas_sin_corregir'] for c in mis_clases)
        total_alumnos_riesgo = sum(c['alumnos_riesgo'] for c in mis_clases)
        clases_requieren_atencion = sum(
            1 for c in mis_clases if c['tareas_sin_corregir'] > 0 or c['alumnos_riesgo'] > 0
        )

        return {
            'mis_clases': mis_clases,
            'total_clases': total_clases,
            'promedio_estudiantes': promedio_estudiantes,
            'total_horas_semanales': total_horas_semanales,
            'total_cursos': total_cursos,
            'total_entregas_pendientes': total_entregas_pendientes,
            'total_alumnos_riesgo': total_alumnos_riesgo,
            'clases_requieren_atencion': clases_requieren_atencion,
        }
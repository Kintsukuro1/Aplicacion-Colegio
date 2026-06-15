"""
Servicio de reportes académicos.
Genera reportes de asistencia, rendimiento académico y boletines.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Any
from django.db.models import Avg

from backend.common.services import PermissionService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.services.policy_service import PolicyService


class AcademicReportsService:
    """Service para generación de reportes académicos"""

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        AcademicReportsService.validate(operation, params)
        return AcademicReportsService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        if params.get('user') is None:
            raise ValueError('Parámetro requerido: user')

        if operation == 'generate_student_academic_report':
            if params.get('estudiante') is None:
                raise ValueError('Parámetro requerido: estudiante')
            return

        if operation in ['generate_class_attendance_report', 'generate_class_performance_report']:
            if params.get('clase') is None:
                raise ValueError('Parámetro requerido: clase')

        if operation == 'generate_class_attendance_report':
            if params.get('fecha_inicio') is None:
                raise ValueError('Parámetro requerido: fecha_inicio')
            if params.get('fecha_fin') is None:
                raise ValueError('Parámetro requerido: fecha_fin')
            return

        if operation == 'generate_class_performance_report':
            return

        if operation != 'generate_student_academic_report':
            raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        if operation == 'generate_student_academic_report':
            return AcademicReportsService._execute_generate_student_academic_report(params)
        if operation == 'generate_class_attendance_report':
            return AcademicReportsService._execute_generate_class_attendance_report(params)
        if operation == 'generate_class_performance_report':
            return AcademicReportsService._execute_generate_class_performance_report(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(colegio_rbd: int, action: str) -> None:
        IntegrityService.validate_school_integrity_or_raise(
            school_id=colegio_rbd,
            action=action,
        )

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_REPORTS')
    def generate_student_academic_report(user, estudiante, periodo: str = 'anual') -> Dict:
        return AcademicReportsService.execute('generate_student_academic_report', {
            'user': user,
            'estudiante': estudiante,
            'periodo': periodo,
        })

    @staticmethod
    def _execute_generate_student_academic_report(params: Dict[str, Any]) -> Dict:
        """
        Genera reporte académico completo de un estudiante.

        Args:
            estudiante: Estudiante
            periodo: Período del reporte ('semestre1', 'semestre2', 'anual', etc.)

        Returns:
            Dict: Reporte académico completo
        
        Raises:
            PrerequisiteException: Si el estudiante no tiene curso o perfil válido
        """
        estudiante = params['estudiante']
        periodo = params.get('periodo', 'anual')

        from backend.apps.academico.models import Calificacion, Asistencia
        from backend.apps.accounts.models import User

        if estudiante.rbd_colegio:
            AcademicReportsService._validate_school_integrity(
                estudiante.rbd_colegio,
                'GENERATE_STUDENT_ACADEMIC_REPORT'
            )
        
        # VALIDACIÓN DEFENSIVA: Verificar que estudiante esté activo
        if not estudiante.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'estudiante_id': estudiante.id,
                    'message': f'No se puede generar reporte: el estudiante {estudiante.email} está inactivo'
                }
            )
        
        # VALIDACIÓN DEFENSIVA: Verificar que tenga perfil de estudiante
        try:
            perfil = estudiante.perfil_estudiante
        except Exception:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'estudiante_id': estudiante.id,
                    'message': f'No se puede generar reporte: el estudiante {estudiante.email} no tiene perfil estudiantil'
                }
            )
        
        # VALIDACIÓN DEFENSIVA: Verificar que tenga curso actual
        curso = perfil.curso_actual
        if not curso:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'estudiante_id': estudiante.id,
                    'message': f'No se puede generar reporte: el estudiante {estudiante.nombre} {estudiante.apellido_paterno} no tiene curso asignado'
                }
            )

        # Calificaciones por asignatura
        asignaturas_data = []
        clases = curso.clases.filter(activo=True).select_related('asignatura')

        for clase in clases:
            calificaciones = Calificacion.objects.filter(
                estudiante=estudiante,
                evaluacion__clase=clase,
                evaluacion__activa=True
            ).select_related('evaluacion')

            if calificaciones:
                suma_ponderada = 0
                suma_ponderaciones = 0

                for calif in calificaciones:
                    ponderacion = float(calif.evaluacion.ponderacion or 100)
                    suma_ponderada += float(calif.nota) * ponderacion
                    suma_ponderaciones += ponderacion

                nota_final = suma_ponderada / suma_ponderaciones if suma_ponderaciones > 0 else 0
                nota_final = round(nota_final, 1)

                asignaturas_data.append({
                    'asignatura': clase.asignatura.nombre,
                    'nota_final': nota_final,
                    'estado': 'Aprobado' if nota_final >= 4.0 else 'Reprobado'
                })

        # Estadísticas de asistencia
        fecha_inicio = date.today() - timedelta(days=30)
        asistencias = Asistencia.objects.filter(
            estudiante=estudiante,
            fecha__gte=fecha_inicio
        )

        total_clases = asistencias.count()
        presentes = asistencias.filter(estado='P').count()
        porcentaje_asistencia = round((presentes / total_clases * 100), 1) if total_clases > 0 else 0

        # Promedio general
        notas_finales = [data['nota_final'] for data in asignaturas_data if data['nota_final'] > 0]
        promedio_general = sum(notas_finales) / len(notas_finales) if notas_finales else 0
        promedio_general = round(promedio_general, 1)

        return {
            'estudiante': {
                'nombre': estudiante.nombre,
                'apellido_paterno': estudiante.apellido_paterno,
                'apellido_materno': estudiante.apellido_materno,
                'rut': estudiante.rut
            },
            'curso': curso.nombre,
            'periodo': periodo,
            'asignaturas': asignaturas_data,
            'promedio_general': promedio_general,
            'asistencia': {
                'total_clases': total_clases,
                'presentes': presentes,
                'porcentaje': porcentaje_asistencia
            },
            'fecha_generacion': date.today()
        }

    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_ATTENDANCE'),
        ('ACADEMICO', 'VIEW_GRADES'),
        ('ACADEMICO', 'VIEW_REPORTS'),
    ])
    def generate_class_attendance_report(user, clase, fecha_inicio: date, fecha_fin: date) -> Dict:
        return AcademicReportsService.execute('generate_class_attendance_report', {
            'user': user,
            'clase': clase,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        })

    @staticmethod
    def _execute_generate_class_attendance_report(params: Dict[str, Any]) -> Dict:
        """
        Genera reporte de asistencia de una clase en un período.
        Optimizado para evitar queries N+1.

        Args:
            clase: Clase
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período

        Returns:
            Dict: Reporte de asistencia de la clase
        
        Raises:
            PrerequisiteException: Si la clase está inactiva
        """
        clase = params['clase']
        fecha_inicio = params['fecha_inicio']
        fecha_fin = params['fecha_fin']

        from backend.apps.academico.models import Asistencia
        from backend.apps.accounts.models import User
        from django.db.models import Count, Q, Case, When, IntegerField

        AcademicReportsService._validate_school_integrity(
            clase.colegio.rbd,
            'GENERATE_CLASS_ATTENDANCE_REPORT'
        )
        
        # VALIDACIÓN DEFENSIVA: Verificar que la clase esté activa
        if not clase.activo:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'clase_id': clase.id_clase,
                    'message': f'No se puede generar reporte: la clase {clase.asignatura.nombre} está inactiva'
                }
            )

        # Obtener estudiantes con sus estadísticas de asistencia en una sola query
        estudiantes = User.objects.filter(
            clases_matriculadas__clase=clase,
            clases_matriculadas__activo=True,
            is_active=True
        ).select_related('perfil_estudiante').annotate(
            total_clases=Count(
                'asistencias',
                filter=Q(
                    asistencias__clase=clase,
                    asistencias__fecha__gte=fecha_inicio,
                    asistencias__fecha__lte=fecha_fin
                )
            ),
            presentes=Count(
                'asistencias',
                filter=Q(
                    asistencias__clase=clase,
                    asistencias__fecha__gte=fecha_inicio,
                    asistencias__fecha__lte=fecha_fin,
                    asistencias__estado='P'
                )
            ),
            ausentes=Count(
                'asistencias',
                filter=Q(
                    asistencias__clase=clase,
                    asistencias__fecha__gte=fecha_inicio,
                    asistencias__fecha__lte=fecha_fin,
                    asistencias__estado='A'
                )
            ),
            tardanzas=Count(
                'asistencias',
                filter=Q(
                    asistencias__clase=clase,
                    asistencias__fecha__gte=fecha_inicio,
                    asistencias__fecha__lte=fecha_fin,
                    asistencias__estado='T'
                )
            ),
            justificadas=Count(
                'asistencias',
                filter=Q(
                    asistencias__clase=clase,
                    asistencias__fecha__gte=fecha_inicio,
                    asistencias__fecha__lte=fecha_fin,
                    asistencias__estado='J'
                )
            )
        ).distinct().order_by('apellido_paterno', 'nombre')

        # Construir reporte por estudiante
        estudiantes_report = []
        total_presentes = 0
        total_ausentes = 0
        total_tardanzas = 0
        total_justificadas = 0

        for estudiante in estudiantes:
            total_clases = estudiante.total_clases
            presentes = estudiante.presentes
            ausentes = estudiante.ausentes
            tardanzas = estudiante.tardanzas
            justificadas = estudiante.justificadas
            
            porcentaje = round((presentes / total_clases * 100), 1) if total_clases > 0 else 0

            estudiantes_report.append({
                'estudiante': estudiante,
                'total_clases': total_clases,
                'presentes': presentes,
                'ausentes': ausentes,
                'tardanzas': tardanzas,
                'justificadas': justificadas,
                'porcentaje': porcentaje
            })

            total_presentes += presentes
            total_ausentes += ausentes
            total_tardanzas += tardanzas
            total_justificadas += justificadas

        total_registros = total_presentes + total_ausentes + total_tardanzas + total_justificadas
        porcentaje_general = round((total_presentes / total_registros * 100), 1) if total_registros > 0 else 0
        porcentaje_ausencias = round((total_ausentes / total_registros * 100), 1) if total_registros > 0 else 0
        porcentaje_tardanzas = round((total_tardanzas / total_registros * 100), 1) if total_registros > 0 else 0

        return {
            'clase': clase,
            'periodo': {
                'inicio': fecha_inicio,
                'fin': fecha_fin
            },
            'asistencia_por_estudiante': estudiantes_report,
            'estadisticas_generales': {
                'total_registros': total_registros,
                'presentes': total_presentes,
                'ausentes': total_ausentes,
                'tardanzas': total_tardanzas,
                'justificadas': total_justificadas,
                'porcentaje_asistencia': porcentaje_general,
                'porcentaje_ausencias': porcentaje_ausencias,
                'porcentaje_tardanzas': porcentaje_tardanzas
            }
        }

    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_ATTENDANCE'),
        ('ACADEMICO', 'VIEW_GRADES'),
        ('ACADEMICO', 'VIEW_REPORTS'),
    ])
    def generate_class_performance_report(user, clase) -> Dict:
        return AcademicReportsService.execute('generate_class_performance_report', {
            'user': user,
            'clase': clase,
        })

    @staticmethod
    def _execute_generate_class_performance_report(params: Dict[str, Any]) -> Dict:
        """
        Genera reporte de rendimiento académico de una clase.
        Altamente optimizado para evitar consultas N+1.

        Args:
            clase: Clase

        Returns:
            Dict: Reporte de rendimiento de la clase
        """
        clase = params['clase']

        from backend.apps.academico.models import Calificacion
        from backend.apps.accounts.models import User

        # 1. Obtener todos los estudiantes activos en una única query
        estudiantes = User.objects.filter(
            clases_matriculadas__clase=clase,
            clases_matriculadas__activo=True,
            is_active=True
        ).select_related('perfil_estudiante').distinct().order_by('apellido_paterno', 'nombre')

        # 2. Cargar todas las calificaciones y evaluaciones asociadas de una única vez
        calificaciones_all = Calificacion.objects.filter(
            evaluacion__clase=clase,
            evaluacion__activa=True
        ).select_related('evaluacion', 'estudiante')

        # 3. Agrupar en memoria para evitar consultas N+1 repetidas
        calificaciones_por_estudiante = {}
        calificaciones_por_evaluacion = {}
        evaluaciones = set()
        
        for calif in calificaciones_all:
            calificaciones_por_estudiante.setdefault(calif.estudiante_id, []).append(calif)
            calificaciones_por_evaluacion.setdefault(calif.evaluacion_id, []).append(calif)
            evaluaciones.add(calif.evaluacion)

        estudiantes_report = []
        notas_clase = []
        rendimiento_estudiantes = []

        for estudiante in estudiantes:
            # Obtener desde memoria
            calificaciones = calificaciones_por_estudiante.get(estudiante.id, [])

            if calificaciones:
                suma_ponderada = 0
                suma_ponderaciones = 0
                notas_estudiante = []

                for calif in calificaciones:
                    ponderacion = float(calif.evaluacion.ponderacion or 100)
                    suma_ponderada += float(calif.nota) * ponderacion
                    suma_ponderaciones += ponderacion
                    notas_estudiante.append(float(calif.nota))

                nota_final = suma_ponderada / suma_ponderaciones if suma_ponderaciones > 0 else 0
                nota_final = round(nota_final, 1)
                notas_clase.append(nota_final)

                # Determinar nivel basado en la nota
                if nota_final >= 6.0:
                    nivel = 'Excelente'
                elif nota_final >= 5.0:
                    nivel = 'Bueno'
                elif nota_final >= 4.0:
                    nivel = 'Suficiente'
                else:
                    nivel = 'Insuficiente'

                rendimiento_estudiantes.append({
                    'estudiante': estudiante,
                    'posicion': 0,  # Se calculará después
                    'promedio': nota_final,
                    'nota_maxima': max(notas_estudiante) if notas_estudiante else 0,
                    'nota_minima': min(notas_estudiante) if notas_estudiante else 0,
                    'total_evaluaciones': len(calificaciones),
                    'nivel': nivel,
                    'estado': 'Aprobado' if nota_final >= 4.0 else 'Reprobado'
                })

                estudiantes_report.append({
                    'estudiante': estudiante,
                    'nota_final': nota_final,
                    'estado': 'Aprobado' if nota_final >= 4.0 else 'Reprobado',
                    'total_evaluaciones': len(calificaciones)
                })
            else:
                # Caso sin evaluaciones registrado
                rendimiento_estudiantes.append({
                    'estudiante': estudiante,
                    'posicion': 0,
                    'promedio': 0,
                    'nota_maxima': 0,
                    'nota_minima': 0,
                    'total_evaluaciones': 0,
                    'nivel': 'Sin evaluaciones',
                    'estado': 'Sin evaluaciones'
                })

                estudiantes_report.append({
                    'estudiante': estudiante,
                    'nota_final': None,
                    'estado': 'Sin evaluaciones',
                    'total_evaluaciones': 0
                })

        # Calcular posiciones
        rendimiento_ordenado = sorted(rendimiento_estudiantes, key=lambda x: x['promedio'], reverse=True)
        for i, item in enumerate(rendimiento_ordenado, 1):
            item['posicion'] = i

        promedio_clase = sum(notas_clase) / len(notas_clase) if notas_clase else 0
        promedio_clase = round(promedio_clase, 1)

        aprobados = len([n for n in notas_clase if n >= 4.0])
        reprobados = len([n for n in notas_clase if n < 4.0])
        porcentaje_aprobacion = round((aprobados / len(notas_clase) * 100), 1) if notas_clase else 0

        # Calcular distribución de notas
        distribucion = {
            'rango_1_3': len([n for n in notas_clase if 1.0 <= n < 4.0]),
            'rango_4_5': len([n for n in notas_clase if 4.0 <= n < 5.0]),
            'rango_5_6': len([n for n in notas_clase if 5.0 <= n < 6.0]),
            'rango_6_7': len([n for n in notas_clase if 6.0 <= n <= 7.0])
        }

        # Calcular rendimiento por evaluación utilizando memoria agrupada
        rendimiento_evaluaciones = []
        for evaluacion in evaluaciones:
            califs_eval = calificaciones_por_evaluacion.get(evaluacion.id_evaluacion, [])
            notas_eval = [float(c.nota) for c in califs_eval]
            if notas_eval:
                promedio_eval = sum(notas_eval) / len(notas_eval)
                rendimiento_evaluaciones.append({
                    'evaluacion': evaluacion.nombre,
                    'fecha': evaluacion.fecha_evaluacion,
                    'promedio': round(promedio_eval, 1),
                    'nota_maxima': max(notas_eval),
                    'nota_minima': min(notas_eval),
                    'total_estudiantes': len(notas_eval)
                })

        return {
            'clase': clase,
            'total_estudiantes': len(estudiantes),
            'total_evaluaciones': len(evaluaciones),
            'promedio_curso': promedio_clase,
            'aprobados': aprobados,
            'reprobados': reprobados,
            'porcentaje_aprobacion': porcentaje_aprobacion,
            'distribucion': distribucion,
            'rendimiento_estudiantes': rendimiento_ordenado,
            'rendimiento_evaluaciones': rendimiento_evaluaciones,
            'estudiantes': estudiantes_report
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_REPORTS')
    def generate_academic_summary(user, colegio, curso) -> Dict:
        """
        Genera resumen académico de un curso completo.

        Args:
            colegio: Colegio
            curso: Curso

        Returns:
            Dict: Resumen académico del curso
        """
        from backend.apps.cursos.models import Clase
        from backend.apps.academico.models import Calificacion, Asistencia

        clases = Clase.objects.filter(
            colegio=colegio,
            curso=curso,
            activo=True
        ).select_related('asignatura')

        resumen_asignaturas = []

        for clase in clases:
            # Estadísticas de calificaciones
            calificaciones = Calificacion.objects.filter(
                evaluacion__clase=clase,
                evaluacion__activa=True
            )

            promedio_asignatura = calificaciones.aggregate(Avg('nota'))['nota__avg'] or 0
            promedio_asignatura = round(promedio_asignatura, 1)

            # Estadísticas de asistencia (último mes)
            fecha_inicio = date.today() - timedelta(days=30)
            asistencias = Asistencia.objects.filter(
                clase=clase,
                fecha__gte=fecha_inicio
            )

            total_asistencias = asistencias.count()
            presentes = asistencias.filter(estado='P').count()
            porcentaje_asistencia = round((presentes / total_asistencias * 100), 1) if total_asistencias > 0 else 0

            resumen_asignaturas.append({
                'asignatura': clase.asignatura.nombre,
                'profesor': clase.profesor.get_full_name() if clase.profesor else 'Sin asignar',
                'total_estudiantes': curso.perfil_estudiante_set.count(),
                'promedio_asignatura': promedio_asignatura,
                'total_calificaciones': calificaciones.count(),
                'porcentaje_asistencia': porcentaje_asistencia
            })

        return {
            'curso': curso.nombre,
            'asignaturas': resumen_asignaturas,
            'fecha_generacion': date.today()
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_REPORTS')
    def parse_report_filters(user, get_data: Dict) -> Dict:
        """
        Parsea y valida los filtros de reportes desde request.GET.

        Args:
            get_data: Datos del request.GET

        Returns:
            Dict: Filtros parseados con valores por defecto
        """
        from datetime import datetime, timedelta
        
        tipo_reporte = get_data.get('tipo', 'asistencia')
        filtro_clase_id = get_data.get('clase_id', '')
        fecha_inicio_str = get_data.get('fecha_inicio', '')
        fecha_fin_str = get_data.get('fecha_fin', '')
        
        # Parsear fechas con valores por defecto
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date() if fecha_inicio_str else date.today() - timedelta(days=30)
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else date.today()
        except ValueError:
            fecha_inicio = date.today() - timedelta(days=30)
            fecha_fin = date.today()
        
        return {
            'tipo_reporte': tipo_reporte,
            'filtro_clase_id': filtro_clase_id,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_COURSES')
    def get_available_classes(user, colegio) -> List:
        """
        Obtiene lista de clases disponibles para reportes.

        Args:
            colegio: Colegio

        Returns:
            List: Lista de clases con información básica
        """
        from backend.apps.cursos.models import Clase
        
        return list(Clase.objects.filter(
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by('asignatura__nombre'))

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_REPORTS')
    def get_class_report_data(user, colegio, clase_id: str, fecha_inicio: date, fecha_fin: date) -> Dict:
        """
        Obtiene datos de reporte para una clase específica.

        Args:
            colegio: Colegio
            clase_id: ID de la clase
            fecha_inicio: Fecha inicio del período
            fecha_fin: Fecha fin del período

        Returns:
            Dict: Datos del reporte
        """
        from backend.apps.cursos.models import Clase
        
        try:
            clase = Clase.objects.get(id=int(clase_id), colegio=colegio)
            
            # Aquí se podría agregar lógica específica del reporte
            # Por ahora retornamos datos básicos
            return {
                'clase': clase,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'reporte_data': {}  # Placeholder para datos específicos
            }
        except (ValueError, Clase.DoesNotExist):
            return None

    @staticmethod
    def parse_report_filters(fecha_inicio_str: str, fecha_fin_str: str) -> Tuple[date, date]:
        """
        Parsea fechas de filtros de reporte.

        Args:
            fecha_inicio_str: Fecha inicio como string
            fecha_fin_str: Fecha fin como string

        Returns:
            Tuple[date, date]: Fechas parseadas
        """
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date() if fecha_inicio_str else date.today() - timedelta(days=30)
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else date.today()
        except ValueError:
            fecha_inicio = date.today() - timedelta(days=30)
            fecha_fin = date.today()
        
        return fecha_inicio, fecha_fin

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_COURSES')
    def get_available_classes_for_reports(user, colegio) -> List:
        """
        Obtiene clases disponibles para reportes.

        Args:
            colegio: Colegio

        Returns:
            List: QuerySet de clases
        """
        from backend.apps.cursos.models import Clase
        
        return Clase.objects.filter(
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by('asignatura__nombre')

    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_ATTENDANCE'),
        ('ACADEMICO', 'VIEW_GRADES'),
        ('ACADEMICO', 'VIEW_COURSES'),
    ])
    def get_classes_for_reports(user, colegio):
        """
        Obtiene clases disponibles para reportes según el rol del usuario.

        Args:
            user: Usuario (profesor o administrador)
            colegio: Colegio

        Returns:
            QuerySet: Clases disponibles según el rol
        """
        from backend.apps.cursos.models import Clase

        school_id = getattr(user, 'rbd_colegio', None)
        has_school_scope = PolicyService.has_capability(user, 'DASHBOARD_VIEW_SCHOOL', school_id=school_id)
        has_config_scope = PolicyService.has_capability(user, 'SYSTEM_CONFIGURE', school_id=school_id)
        
        # Administradores pueden ver todas las clases del colegio
        if has_school_scope and has_config_scope:
            return Clase.objects.filter(
                colegio=colegio,
                activo=True
            ).select_related('asignatura', 'curso', 'profesor').order_by('asignatura__nombre')
        
        # Profesores solo ven sus clases
        return Clase.objects.filter(
            profesor=user,
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by('asignatura__nombre')

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_COURSES')
    def get_selected_class_for_report(user, colegio, clase_id_str: str):
        """
        Obtiene clase seleccionada para reporte.

        Args:
            colegio: Colegio
            clase_id_str: ID de clase como string

        Returns:
            Clase or None
        """
        from backend.apps.cursos.models import Clase
        
        if not clase_id_str:
            return None
            
        try:
            clase_id = int(clase_id_str)
            return Clase.objects.filter(
                colegio=colegio,
                activo=True,
                id=clase_id
            ).select_related('asignatura', 'curso', 'profesor').first()
        except (ValueError, TypeError):
            return None

    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_REPORTS'),
        ('ADMINISTRATIVO', 'VIEW_REPORTS')
    ])
    def generate_report_data(user, clase_seleccionada, tipo_reporte: str, fecha_inicio: date, fecha_fin: date) -> Dict:
        """
        Genera datos del reporte según tipo.

        Args:
            clase_seleccionada: Clase seleccionada
            tipo_reporte: Tipo de reporte ('asistencia' o 'academico')
            fecha_inicio: Fecha inicio
            fecha_fin: Fecha fin

        Returns:
            Dict: Datos del reporte
        """
        if not clase_seleccionada:
            return {}
            
        if tipo_reporte == 'asistencia':
            return AcademicReportsService.generate_class_attendance_report(
                user, clase_seleccionada, fecha_inicio, fecha_fin
            )
        elif tipo_reporte == 'academico':
            return AcademicReportsService.generate_class_performance_report(
                user, clase_seleccionada
            )
        
        return {}

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_COURSES')
    def validate_and_get_class_for_export(user, colegio, clase_id_str: str):
        """
        Valida y obtiene clase para exportación.

        Args:
            colegio: Colegio
            clase_id_str: ID de clase como string

        Returns:
            Clase or HttpResponse con error
        """
        from django.http import HttpResponse
        from backend.apps.cursos.models import Clase
        
        if not clase_id_str:
            return HttpResponse('Debe seleccionar una clase', status=400)
        
        try:
            clase_id = int(clase_id_str)
            clase_seleccionada = Clase.objects.filter(
                colegio=colegio,
                activo=True,
                id=clase_id
            ).select_related('asignatura', 'curso', 'profesor').first()
            
            if not clase_seleccionada:
                return HttpResponse('Clase no encontrada', status=404)
                
            return clase_seleccionada
        except (ValueError, TypeError):
            return HttpResponse('ID de clase inválido', status=400)

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_REPORTS')
    def prepare_export_data(user, colegio, tipo_reporte: str, clase_id_str: str, fecha_inicio_str: str, fecha_fin_str: str):
        """
        Prepara datos para exportación.

        Args:
            colegio: Colegio
            tipo_reporte: Tipo de reporte
            clase_id_str: ID de clase
            fecha_inicio_str: Fecha inicio
            fecha_fin_str: Fecha fin

        Returns:
            Tuple: (clase_seleccionada, fecha_inicio, fecha_fin, reporte_data) o HttpResponse con error
        """
        from django.http import HttpResponse
        
        # Validar y obtener clase
        clase_result = AcademicReportsService.validate_and_get_class_for_export(user, colegio, clase_id_str)
        if isinstance(clase_result, HttpResponse):
            return clase_result
        
        clase_seleccionada = clase_result
        
        # Parsear fechas
        fecha_inicio, fecha_fin = AcademicReportsService.parse_report_filters(fecha_inicio_str, fecha_fin_str)
        
        # Generar datos del reporte
        reporte_data = AcademicReportsService.generate_report_data(
            user, clase_seleccionada, tipo_reporte, fecha_inicio, fecha_fin
        )
        
        if not reporte_data:
            return HttpResponse('No hay datos para el reporte', status=400)
        
        return clase_seleccionada, fecha_inicio, fecha_fin, reporte_data

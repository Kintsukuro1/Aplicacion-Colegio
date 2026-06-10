"""
Academic Service - Dominio Académico Unificado
FASE 3: Rediseño del dominio - Servicio único para todo el dominio académico

Contrato explícito del dominio académico:
- Gestión de cursos y asignaturas
- Control de asistencia
- Administración de calificaciones
- Reportes académicos
- Validaciones académicas

CONTRATOS:
- gestionar_curso: Command Operation (dict)
- registrar_asistencia: Command Operation (dict)
- obtener_*: Query Operation (dict)
- generar_reporte_*: Query Operation (dict)

Este servicio consolida TODAS las responsabilidades académicas
para evitar fragmentación en múltiples servicios sin límites claros.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db.models import Avg, Count, Max, Min, Prefetch, Q, Sum
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from backend.apps.cursos.models import (
    Asignatura, Clase, Curso
)
from backend.apps.institucion.models import CicloAcademico, Colegio
from backend.apps.academico.models import (
    Asistencia, Calificacion, Evaluacion, Tarea
)
from backend.apps.accounts.models import PerfilEstudiante, User
from backend.apps.matriculas.models import Matricula
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.services.permission_service import PermissionService
from backend.common.services.onboarding_service import OnboardingService
from backend.common.exceptions import PrerequisiteException

logger = logging.getLogger(__name__)


class AcademicService:
    """
    Servicio unificado para el dominio académico completo.

    Responsabilidades consolidadas:
    - Gestión curricular (cursos, asignaturas, clases)
    - Control académico (asistencia, calificaciones)
    - Reportes y análisis académico
    - Validaciones de reglas académicas
    """

    @staticmethod
    def execute(operation: str, params: Dict) -> Dict:
        """
        Punto de entrada estándar para operaciones de comando.

        Patrón fase 3.1:
        1) validate
        2) _execute
        """
        AcademicService.validate(operation, params)
        return AcademicService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict) -> None:
        """Valida parámetros y prerequisitos de dominio antes de ejecutar."""
        user = params.get('user')
        if not user:
            raise ValueError('Parámetro requerido: user')

        if not getattr(user, 'rbd_colegio', None):
            raise ValueError('El usuario no tiene colegio asociado')

            try:
                IntegrityService.validate_school_integrity_or_raise(
                    school_id=user.rbd_colegio,
                    action=f'ACADEMIC_SERVICE_{operation.upper()}',
                )
            except PrerequisiteException as exc:
                # Log and continue to allow downstream validations (e.g., relaciones inválidas)
                logger.warning("Continuando pese a inconsistencias de integridad: %s", exc)

        if operation == 'gestionar_curso':
            action = params.get('action')
            if action not in ['create', 'update', 'delete']:
                raise ValueError(f"Acción no válida: {action}")

        elif operation == 'registrar_asistencia':
            if params.get('clase_id') is None:
                raise ValueError('Parámetro requerido: clase_id')
            if params.get('asistencias_data') is None:
                raise ValueError('Parámetro requerido: asistencias_data')

    @staticmethod
    def _execute(operation: str, params: Dict) -> Dict:
        """Despacha a implementación privada por operación."""
        if operation == 'gestionar_curso':
            return AcademicService._execute_gestionar_curso(params)
        if operation == 'registrar_asistencia':
            return AcademicService._execute_registrar_asistencia(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute_gestionar_curso(params: Dict) -> Dict:
        user = params['user']
        curso_id = params.get('curso_id')
        data = params.get('data')
        action = params.get('action', 'create')

        if action == 'create':
            return AcademicService._crear_curso(user, data)
        if action == 'update':
            return AcademicService._actualizar_curso(user, curso_id, data)
        if action == 'delete':
            return AcademicService._eliminar_curso(user, curso_id)
        raise ValueError(f"Acción no válida: {action}")

    @staticmethod
    def _execute_registrar_asistencia(params: Dict) -> Dict:
        user = params['user']
        clase_id = params['clase_id']
        asistencias_data = params['asistencias_data']

        try:
            # Validar que el profesor da esta clase
            clase = Clase.objects.select_related('profesor', 'curso').get(
                id=clase_id,
                profesor=user
            )

            # Validar fecha de la clase
            hoy = timezone.now().date()

            asistencias_creadas = []
            for asistencia_data in asistencias_data:
                estudiante_id = asistencia_data['estudiante_id']
                estado = asistencia_data['estado'].upper()

                # Verificar que el estudiante está matriculado en el curso
                matricula = Matricula.objects.filter(
                    estudiante_id=estudiante_id,
                    curso=clase.curso,
                    estado='ACTIVA'
                ).first()

                if not matricula:
                    continue  # Saltar estudiantes no matriculados

                # Obtener el estudiante
                try:
                    estudiante = User.objects.get(id=estudiante_id)
                except User.DoesNotExist:
                    continue

                # Control defensivo de duplicados: consultar estado anterior
                try:
                    asistencia_previa = Asistencia.objects.get(
                        clase=clase,
                        estudiante_id=estudiante_id,
                        fecha=hoy
                    )
                    estado_anterior = asistencia_previa.estado
                except Asistencia.DoesNotExist:
                    estado_anterior = None

                # Crear o actualizar asistencia corregido (con fecha y colegio, removiendo campos inexistentes)
                asistencia, created = Asistencia.objects.update_or_create(
                    clase=clase,
                    estudiante=estudiante,
                    fecha=hoy,
                    defaults={
                        'colegio': clase.curso.colegio,
                        'estado': estado,
                    }
                )
                asistencias_creadas.append(asistencia)

                # Disparar notificación si pasa a estar ausente
                if estado in ['A', 'AUSENTE'] and estado_anterior not in ['A', 'AUSENTE']:
                    from backend.apps.notificaciones.services.attendance_notifications import AttendanceNotificationService
                    try:
                        AttendanceNotificationService.notify_absence(
                            estudiante=estudiante,
                            clase=clase,
                            fecha=hoy,
                            registrada_por=user
                        )
                    except Exception as e:
                        logger.error(f"Error al enviar notificacion de inasistencia: {e}", exc_info=True)

            return {
                'success': True,
                'asistencias_registradas': len(asistencias_creadas),
                'message': f'Asistencia registrada para {len(asistencias_creadas)} estudiantes'
            }

        except Clase.DoesNotExist:
            return {
                'success': False,
                'error': 'Clase no encontrada o no tienes permisos'
            }

    # ==================== GESTIÓN CURRICULAR ====================

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_COURSES')
    def gestionar_curso(user, curso_id=None, data=None, action='create') -> Dict:
        """
        Gestión completa de cursos: crear, actualizar, eliminar.

        Command Operation: Ejecuta operación y retorna resultado.

        Args:
            user: Usuario que realiza la acción
            curso_id: ID del curso (para update/delete)
            data: Datos del curso (para create/update)
            action: 'create', 'update', 'delete'

        Returns:
            dict: {
                'success': bool - Indica si la operación fue exitosa
                'message': str - Mensaje descriptivo del resultado
                'data': dict - Datos del curso resultante (solo si success=True)
                'error': str - Mensaje de error (solo si success=False)
            }

        Raises:
            ValueError: Si la acción especificada no es válida
        """
        return AcademicService.execute('gestionar_curso', {
            'user': user,
            'curso_id': curso_id,
            'data': data,
            'action': action,
        })

    @staticmethod
    def _crear_curso(user, data):
        """
        Crear nuevo curso con validaciones.
        
        Raises:
            PrerequisiteException: Si no existe ciclo académico activo
        """
        # Validar colegio del usuario
        colegio_id = user.rbd_colegio

        # Validar prerequisito: ciclo académico activo
        validation = OnboardingService.validate_prerequisite('CREATE_CURSO', colegio_id)
        if not validation['valid']:
            raise PrerequisiteException(
                validation['error']['error_type'],
                validation['error']['context']
            )

        # Obtener ciclo actual (ya sabemos que existe por la validación)
        ciclo_actual = CicloAcademico.objects.filter(
            colegio_id=colegio_id,
            estado='ACTIVO'
        ).first()

        if ciclo_actual is None:
            raise PrerequisiteException(
                error_type='MISSING_CICLO_ACTIVO',
                context={
                    'colegio_id': colegio_id,
                    'message': 'No existe ciclo académico activo para crear el curso',
                    'action': 'Cree o active un ciclo académico antes de continuar.'
                }
            )

        # Validar datos requeridos
        required_fields = ['nivel', 'letra', 'anio_escolar']
        for field in required_fields:
            if field not in data:
                return {
                    'success': False,
                    'error': f'Campo requerido: {field}'
                }

        # Evitar duplicidad del curso en el mismo ciclo
        if Curso.objects.filter(
            colegio_id=colegio_id,
            ciclo_academico=ciclo_actual,
            nivel=data['nivel'],
            letra=data['letra'],
            anio_escolar=data['anio_escolar']
        ).exists():
            return {
                'success': False,
                'error': 'Ya existe un curso con el mismo nivel, letra y año escolar en el ciclo activo'
            }

        # Crear curso
        curso = Curso.objects.create(
            colegio_id=colegio_id,
            ciclo_academico=ciclo_actual,
            nivel=data['nivel'],
            letra=data['letra'],
            anio_escolar=data['anio_escolar'],
            descripcion=data.get('descripcion', ''),
            capacidad_maxima=data.get('capacidad_maxima', 30)
        )

        return {
            'success': True,
            'curso': curso,
            'message': f'Curso {curso} creado exitosamente'
        }

    @staticmethod
    def _actualizar_curso(user, curso_id, data):
        """Actualizar curso existente"""
        try:
            curso = Curso.objects.get(
                id=curso_id,
                colegio_id=user.rbd_colegio
            )

            # Actualizar campos permitidos
            updatable_fields = ['descripcion', 'capacidad_maxima']
            for field in updatable_fields:
                if field in data:
                    setattr(curso, field, data[field])

            curso.save()

            return {
                'success': True,
                'curso': curso,
                'message': f'Curso {curso} actualizado exitosamente'
            }

        except Curso.DoesNotExist:
            return {
                'success': False,
                'error': 'Curso no encontrado'
            }

    @staticmethod
    def _eliminar_curso(user, curso_id):
        """Eliminar curso (con validaciones de integridad)"""
        try:
            curso = Curso.objects.get(
                id=curso_id,
                colegio_id=user.rbd_colegio
            )

            # Verificar que no tenga matrículas asociadas (PROTECT en modelo)
            matriculas_asociadas = Matricula.objects.filter(curso=curso).count()
            if matriculas_asociadas > 0:
                return {
                    'success': False,
                    'error': (
                        f'No se puede eliminar curso con {matriculas_asociadas} '
                        'matrícula(s) asociada(s)'
                    )
                }

            # Verificar que no tenga clases asociadas (evitar borrado en cascada)
            clases_asociadas = Clase.objects.filter(curso=curso).count()
            if clases_asociadas > 0:
                return {
                    'success': False,
                    'error': (
                        f'No se puede eliminar curso con {clases_asociadas} '
                        'clase(s) asociada(s)'
                    )
                }

            try:
                curso.delete()
            except ProtectedError:
                return {
                    'success': False,
                    'error': 'No se puede eliminar curso: existen relaciones protegidas asociadas'
                }

            return {
                'success': True,
                'message': f'Curso {curso} eliminado exitosamente'
            }

        except Curso.DoesNotExist:
            return {
                'success': False,
                'error': 'Curso no encontrado'
            }

    # ==================== CONTROL DE ASISTENCIA ====================

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_ATTENDANCE')
    def registrar_asistencia(user, clase_id, asistencias_data) -> Dict:
        """
        Registrar asistencia para una clase completa.

        Command Operation: Registra asistencias y retorna resultado.

        Args:
            user: Profesor que registra la asistencia
            clase_id: ID de la clase
            asistencias_data: Lista de dicts con asistencia de cada estudiante
                Formato: [{'estudiante_id': int, 'estado': str}]

        Returns:
            dict: {
                'success': bool - Indica si el registro fue exitoso
                'message': str - Mensaje descriptivo del resultado
                'data': dict - Detalles del registro (solo si success=True)
                    - 'asistencias_registradas': int - Número de asistencias registradas
                'error': str - Mensaje de error (solo si success=False)
            }

        Raises:
            Clase.DoesNotExist: Si la clase no existe o no pertenece al profesor
        """
        return AcademicService.execute('registrar_asistencia', {
            'user': user,
            'clase_id': clase_id,
            'asistencias_data': asistencias_data,
        })

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_ATTENDANCE')
    def obtener_asistencia_curso(user, curso_id, fecha_inicio=None, fecha_fin=None) -> Dict:
        """
        Obtener reporte de asistencia para un curso en período.

        Query Operation: Consulta datos de asistencia y los retorna.

        Args:
            user: Usuario que consulta el reporte
            curso_id: ID del curso a consultar
            fecha_inicio: Fecha de inicio del período (opcional, default: 30 días atrás)
            fecha_fin: Fecha de fin del período (opcional, default: hoy)

        Returns:
            dict: {
                'success': bool - Indica si la consulta fue exitosa
                'data': dict - Reporte de asistencia (solo si success=True)
                    - 'curso': str - Nombre del curso
                    - 'periodo': str - Período consultado
                    - 'estudiantes': list - Lista de estudiantes con su asistencia
                'error': str - Mensaje de error (solo si success=False)
            }
        """
        # Validar acceso al curso
        curso = AcademicService._validar_acceso_curso(user, curso_id)
        if not curso:
            return {'success': False, 'error': 'Curso no encontrado o sin acceso'}

        # Definir período
        if not fecha_inicio:
            fecha_inicio = timezone.now().date() - timedelta(days=30)
        if not fecha_fin:
            fecha_fin = timezone.now().date()

        # Obtener clases del período
        clases = Clase.objects.filter(
            curso=curso,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).order_by('fecha')

        # Obtener estudiantes matriculados
        matriculas = Matricula.objects.filter(
            curso=curso,
            estado='ACTIVA'
        ).select_related('estudiante')

        reporte = {
            'curso': str(curso),
            'periodo': f'{fecha_inicio} a {fecha_fin}',
            'estudiantes': []
        }

        for matricula in matriculas:
            estudiante = matricula.estudiante
            asistencias_estudiante = Asistencia.objects.filter(
                clase__in=clases,
                estudiante=estudiante
            )

            total_clases = clases.count()
            presentes = asistencias_estudiante.filter(estado='PRESENTE').count()
            ausentes = asistencias_estudiante.filter(estado='AUSENTE').count()
            justificados = asistencias_estudiante.filter(estado='JUSTIFICADO').count()

            porcentaje = (presentes / total_clases * 100) if total_clases > 0 else 0

            reporte['estudiantes'].append({
                'id': estudiante.id,
                'nombre': estudiante.get_full_name(),
                'rut': estudiante.rut,
                'total_clases': total_clases,
                'presentes': presentes,
                'ausentes': ausentes,
                'justificados': justificados,
                'porcentaje_asistencia': round(porcentaje, 1)
            })

        return {
            'success': True,
            'reporte': reporte
        }

    # ==================== GESTIÓN DE CALIFICACIONES ====================

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def registrar_calificaciones(user, evaluacion_id, calificaciones_data):
        """
        Registrar calificaciones para una evaluación

        Args:
            user: Profesor que registra
            evaluacion_id: ID de la evaluación
            calificaciones_data: Lista de dicts con {'estudiante_id': id, 'nota': decimal}

        Returns:
            dict: Resultado del registro
        """
        try:
            # Validar que la evaluación pertenece al profesor
            evaluacion = Evaluacion.objects.select_related('clase__profesor').get(
                id=evaluacion_id,
                clase__profesor=user
            )

            calificaciones_creadas = []
            for calif_data in calificaciones_data:
                estudiante_id = calif_data['estudiante_id']
                nota_valor = Decimal(str(calif_data['nota']))

                # Validar rango de nota
                if not (1 <= nota_valor <= 7):
                    continue  # Saltar notas inválidas

                # Crear o actualizar nota
                nota, created = Calificacion.objects.get_or_create(
                    evaluacion=evaluacion,
                    estudiante_id=estudiante_id,
                    defaults={
                        'colegio': evaluacion.colegio,
                        'nota': nota_valor,
                        'registrado_por': user,
                        'actualizado_por': user,
                    }
                )
                if not created:
                    nota.nota = nota_valor
                    nota.actualizado_por = user
                    nota.save()
                calificaciones_creadas.append(nota)

            return {
                'success': True,
                'calificaciones_registradas': len(calificaciones_creadas),
                'message': f'Calificaciones registradas para {len(calificaciones_creadas)} estudiantes'
            }

        except Evaluacion.DoesNotExist:
            return {
                'success': False,
                'error': 'Evaluación no encontrada o no tienes permisos'
            }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_GRADES')
    def obtener_calificaciones_estudiante(user, estudiante_id, asignatura_id=None):
        """
        Obtener calificaciones de un estudiante

        Args:
            user: Usuario que consulta
            estudiante_id: ID del estudiante
            asignatura_id: ID de asignatura específica (opcional)

        Returns:
            dict: Calificaciones del estudiante
        """
        # Validar permisos de acceso al estudiante
        if not PermissionService.has_permission(user, 'ACADEMICO.VIEW_GRADES', estudiante_id=estudiante_id):
            return {'success': False, 'error': 'Sin permisos para ver calificaciones'}

        # Obtener calificaciones
        notas = Calificacion.objects.filter(
            estudiante_id=estudiante_id
        ).select_related(
            'evaluacion__clase__asignatura',
            'evaluacion__clase__curso'
        ).order_by('-evaluacion__fecha_evaluacion')

        if asignatura_id:
            notas = notas.filter(evaluacion__clase__asignatura_id=asignatura_id)

        calificaciones = []
        for nota in notas:
            calificaciones.append({
                'asignatura': str(nota.evaluacion.clase.asignatura),
                'curso': str(nota.evaluacion.clase.curso),
                'evaluacion': nota.evaluacion.nombre,
                'fecha': nota.evaluacion.fecha_evaluacion.strftime('%d/%m/%Y') if nota.evaluacion.fecha_evaluacion else '',
                'nota': float(nota.nota),
                'tipo_evaluacion': nota.evaluacion.tipo_evaluacion
            })

        return {
            'success': True,
            'estudiante_id': estudiante_id,
            'calificaciones': calificaciones
        }

    # ==================== REPORTES ACADÉMICOS ====================

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_REPORTS')
    def generar_reporte_academico(user, tipo_reporte, filtros=None) -> Dict:
        """
        Generar reportes académicos consolidados.

        Query Operation: Consulta y genera datos de reportes académicos.

        Args:
            user: Usuario que solicita el reporte
            tipo_reporte: Tipo de reporte a generar
                - 'curso': Reporte de un curso específico
                - 'asignatura': Reporte de una asignatura
                - 'estudiante': Reporte de un estudiante
                - 'general': Reporte general del colegio
            filtros: Dict con filtros específicos según el tipo de reporte
                Para 'curso': {'curso_id': int}
                Para 'asignatura': {'asignatura_id': int, 'curso_id': int opcional}

        Returns:
            dict: {
                'success': bool - Indica si la generación fue exitosa
                'data': dict - Datos del reporte (solo si success=True)
                    - 'tipo': str - Tipo de reporte generado
                    - 'estadisticas': dict - Estadísticas calculadas
                    - ... otros campos específicos del reporte
                'error': str - Mensaje de error (solo si success=False)
            }

        Raises:
            ValueError: Si el tipo de reporte no es válido
        """
        filtros = filtros or {}

        if tipo_reporte == 'curso':
            return AcademicService._reporte_curso(user, filtros)
        elif tipo_reporte == 'asignatura':
            return AcademicService._reporte_asignatura(user, filtros)
        elif tipo_reporte == 'estudiante':
            return AcademicService._reporte_estudiante(user, filtros)
        elif tipo_reporte == 'general':
            return AcademicService._reporte_general(user, filtros)
        else:
            return {
                'success': False,
                'error': f'Tipo de reporte no válido: {tipo_reporte}'
            }

    @staticmethod
    def _reporte_curso(user, filtros):
        """Reporte académico de un curso"""
        curso_id = filtros.get('curso_id')
        if not curso_id:
            return {'success': False, 'error': 'curso_id requerido'}

        # Validar acceso al curso
        curso = AcademicService._validar_acceso_curso(user, curso_id)
        if not curso:
            return {'success': False, 'error': 'Curso no encontrado o sin acceso'}

        # Obtener estadísticas del curso
        estadisticas = AcademicService._calcular_estadisticas_curso(curso)

        return {
            'success': True,
            'tipo': 'curso',
            'curso': str(curso),
            'estadisticas': estadisticas
        }

    @staticmethod
    def _reporte_asignatura(user, filtros):
        """Reporte académico de una asignatura"""
        asignatura_id = filtros.get('asignatura_id')
        curso_id = filtros.get('curso_id')

        if not asignatura_id:
            return {'success': False, 'error': 'asignatura_id requerido'}

        # Validar acceso
        asignatura = Asignatura.objects.get(id=asignatura_id)
        if curso_id:
            curso = AcademicService._validar_acceso_curso(user, curso_id)
            if not curso:
                return {'success': False, 'error': 'Curso no encontrado o sin acceso'}

        estadisticas = AcademicService._calcular_estadisticas_asignatura(asignatura, curso_id)

        return {
            'success': True,
            'tipo': 'asignatura',
            'asignatura': str(asignatura),
            'estadisticas': estadisticas
        }

    # ==================== MÉTODOS DE SOPORTE ====================

    @staticmethod
    def _validar_acceso_curso(user, curso_id):
        """Validar que el usuario tiene acceso al curso"""
        try:
            curso = Curso.objects.select_related('colegio').get(id=curso_id)

            # Administradores tienen acceso a todos los cursos
            if PermissionService.has_permission(user, 'ACADEMICO.ADMIN'):
                return curso

            # Acceso por relación docente con el curso
            clases_profesor = Clase.objects.filter(
                curso=curso,
                profesor=user
            ).exists()
            if clases_profesor:
                return curso

            # Acceso por matrícula activa en el curso
            matricula = Matricula.objects.filter(
                estudiante=user,
                curso=curso,
                estado='ACTIVA'
            ).exists()
            if matricula:
                return curso

            return None

        except Curso.DoesNotExist:
            return None

    @staticmethod
    def _calcular_estadisticas_curso(curso):
        """Calcular estadísticas académicas de un curso"""
        # Asistencia promedio
        asistencia_promedio = Asistencia.objects.filter(
            clase__curso=curso
        ).aggregate(
            promedio=Avg('estado_numero')  # Asumiendo campo calculado
        )['promedio'] or 0

        # Calificaciones promedio por asignatura
        calificaciones = Calificacion.objects.filter(
            evaluacion__clase__curso=curso
        ).values('evaluacion__clase__asignatura').annotate(
            promedio=Avg('nota')
        )

        return {
            'asistencia_promedio': round(asistencia_promedio, 1),
            'calificaciones_por_asignatura': list(calificaciones),
            'total_estudiantes': Matricula.objects.filter(
                curso=curso, estado='ACTIVA'
            ).count()
        }

    @staticmethod
    def _calcular_estadisticas_asignatura(asignatura,
                                          curso_id=None):
        """Calcular estadísticas de una asignatura"""
        notas = Calificacion.objects.filter(
            evaluacion__clase__asignatura=asignatura
        )

        if curso_id:
            notas = notas.filter(evaluacion__clase__curso_id=curso_id)

        estadisticas = notas.aggregate(
            promedio=Avg('nota'),
            minima=Min('nota'),
            maxima=Max('nota'),
            total_evaluaciones=Count('id_calificacion')
        )

        return {
            'promedio_general': round(estadisticas['promedio'] or 0, 1),
            'nota_minima': estadisticas['minima'],
            'nota_maxima': estadisticas['maxima'],
            'total_evaluaciones': estadisticas['total_evaluaciones']
        }
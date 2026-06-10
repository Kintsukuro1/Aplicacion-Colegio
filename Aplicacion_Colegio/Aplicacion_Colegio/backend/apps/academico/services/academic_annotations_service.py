"""
Servicio de anotaciones académicas.
Maneja observaciones, comentarios y anotaciones académicas.
"""
from datetime import date
from typing import Dict, List, Optional, Any

from backend.common.services import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService


class AcademicAnnotationsService:
    """Service para gestión de anotaciones académicas"""

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        AcademicAnnotationsService.validate(operation, params)
        return AcademicAnnotationsService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(AcademicAnnotationsService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(colegio_rbd: int, action: str) -> None:
        IntegrityService.validate_school_integrity_or_raise(
            school_id=colegio_rbd,
            action=action,
        )

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_ATTENDANCE')
    def add_attendance_observation(user, colegio, asistencia_id: int, observacion: str) -> Optional[Dict[str, Any]]:
        """
        Agrega o actualiza una observación en un registro de asistencia.

        Args:
            user: Usuario realizando la operación
            colegio: Colegio
            asistencia_id: ID de la asistencia
            observacion: Texto de la observación

        Returns:
            Optional[Dict]: None si exitoso, Dict con error si falla
        """
        from backend.apps.academico.models import Asistencia

        AcademicAnnotationsService._validate_school_integrity(
            colegio.rbd,
            'ADD_ATTENDANCE_OBSERVATION'
        )

        # Validación defensiva: verificar que la asistencia existe
        try:
            asistencia = Asistencia.objects.get(
                id_asistencia=asistencia_id,
                colegio=colegio
            )
        except Asistencia.DoesNotExist:
            return ErrorResponseBuilder.build('NOT_FOUND', context={
                'entity': 'Asistencia',
                'id': asistencia_id,
                'message': 'El registro de asistencia no existe o no pertenece a este colegio'
            })
        
        # Validación defensiva: verificar que la clase esté activa
        if not asistencia.clase.activo:
            return ErrorResponseBuilder.build('INVALID_STATE', context={
                'entity': 'Clase',
                'field': 'activo',
                'message': 'No se pueden agregar observaciones a clases inactivas',
                'clase_id': asistencia.clase.id_clase
            })
        
        # Validación defensiva: verificar que el estudiante esté activo
        if not asistencia.estudiante.is_active:
            return ErrorResponseBuilder.build('INVALID_STATE', context={
                'entity': 'User',
                'field': 'is_active',
                'message': 'No se pueden agregar observaciones a estudiantes inactivos',
                'estudiante_id': asistencia.estudiante.id
            })
        
        asistencia.observaciones = observacion
        asistencia.save()
        return None

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_STUDENTS')
    def get_student_academic_annotations(user, estudiante, fecha_desde: date = None) -> List[Dict]:
        """
        Obtiene todas las anotaciones académicas de un estudiante.

        Args:
            estudiante: Estudiante
            fecha_desde: Fecha desde la cual buscar (opcional)

        Returns:
            List[Dict]: Lista de anotaciones académicas
        """
        from backend.apps.academico.models import Asistencia

        anotaciones = []

        # Observaciones de asistencia
        asistencias = Asistencia.objects.filter(
            estudiante=estudiante
        ).exclude(observaciones__isnull=True).exclude(observaciones='')

        if fecha_desde:
            asistencias = asistencias.filter(fecha__gte=fecha_desde)

        for asistencia in asistencias:
            anotaciones.append({
                'tipo': 'asistencia',
                'fecha': asistencia.fecha,
                'asignatura': asistencia.clase.asignatura.nombre,
                'contenido': asistencia.observaciones,
                'estado': asistencia.get_estado_display()
            })

        # Comentarios en calificaciones (si existieran)
        # Aquí podríamos agregar lógica para comentarios en calificaciones
        # si se agregan campos de comentarios en el futuro

        # Ordenar por fecha descendente
        anotaciones.sort(key=lambda x: x['fecha'], reverse=True)

        return anotaciones

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_COURSES')
    def get_class_academic_annotations(user, clase, fecha_desde: date = None) -> List[Dict]:
        """
        Obtiene todas las anotaciones académicas de una clase.

        Args:
            clase: Clase
            fecha_desde: Fecha desde la cual buscar (opcional)

        Returns:
            List[Dict]: Lista de anotaciones académicas de la clase
        """
        from backend.apps.academico.models import Asistencia

        asistencias = Asistencia.objects.filter(
            clase=clase
        ).exclude(observaciones__isnull=True).exclude(observaciones='').select_related('estudiante')

        if fecha_desde:
            asistencias = asistencias.filter(fecha__gte=fecha_desde)

        anotaciones = []
        for asistencia in asistencias:
            anotaciones.append({
                'tipo': 'asistencia',
                'fecha': asistencia.fecha,
                'estudiante': asistencia.estudiante.get_full_name(),
                'contenido': asistencia.observaciones,
                'estado': asistencia.get_estado_display()
            })

        # Ordenar por fecha descendente
        anotaciones.sort(key=lambda x: x['fecha'], reverse=True)

        return anotaciones

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def create_academic_note(user, colegio, estudiante, clase, tipo: str, contenido: str, fecha: date = None) -> Optional[Dict[str, Any]]:
        """
        Crea una nota académica general para un estudiante.

        Args:
            user: Usuario realizando la operación
            colegio: Colegio
            estudiante: Estudiante
            clase: Clase (opcional)
            tipo: Tipo de nota ('positiva', 'negativa', 'observacion', etc.)
            contenido: Contenido de la nota
            fecha: Fecha de la nota (default: hoy)

        Returns:
            Optional[Dict]: None si exitoso, Dict con error si falla
        """
        AcademicAnnotationsService._validate_school_integrity(
            colegio.rbd,
            'CREATE_ACADEMIC_NOTE'
        )

        # Validación defensiva: verificar que el estudiante esté activo
        if not estudiante.is_active:
            return ErrorResponseBuilder.build('INVALID_STATE', context={
                'entity': 'User',
                'field': 'is_active',
                'message': 'No se pueden crear notas académicas para estudiantes inactivos',
                'estudiante_id': estudiante.id
            })
        
        # Validación defensiva: verificar que la clase esté activa
        if clase and not clase.activo:
            return ErrorResponseBuilder.build('INVALID_STATE', context={
                'entity': 'Clase',
                'field': 'activo',
                'message': 'No se pueden crear notas académicas para clases inactivas',
                'clase_id': clase.id_clase
            })
        
        # Validación defensiva: verificar que el estudiante pertenezca al colegio
        if estudiante.rbd_colegio != colegio.rbd:
            return ErrorResponseBuilder.build('INVALID_RELATIONSHIP', context={
                'entity': 'User',
                'related_entity': 'Colegio',
                'message': 'El estudiante no pertenece a este colegio',
                'estudiante_rbd': estudiante.rbd_colegio,
                'colegio_rbd': colegio.rbd
            })

        # Validación defensiva: verificar relación clase-colegio
        if clase and clase.colegio_id != colegio.rbd:
            return ErrorResponseBuilder.build('INVALID_RELATIONSHIP', context={
                'entity': 'Clase',
                'related_entity': 'Colegio',
                'message': 'La clase no pertenece al colegio informado',
                'clase_id': clase.id_clase,
                'clase_colegio': clase.colegio_id,
                'colegio_rbd': colegio.rbd
            })

        # Validación defensiva: verificar relación estudiante-ciclo de la clase
        if clase and getattr(estudiante, 'perfil_estudiante', None):
            ciclo_estudiante = estudiante.perfil_estudiante.ciclo_actual_id
            if ciclo_estudiante and ciclo_estudiante != clase.curso.ciclo_academico_id:
                return ErrorResponseBuilder.build('INVALID_RELATIONSHIP', context={
                    'entity': 'User',
                    'related_entity': 'Clase',
                    'message': 'El estudiante no pertenece al ciclo académico de la clase',
                    'estudiante_id': estudiante.id,
                    'clase_id': clase.id_clase,
                    'ciclo_estudiante_id': ciclo_estudiante,
                    'ciclo_clase_id': clase.curso.ciclo_academico_id
                })

        if not fecha:
            fecha = date.today()

        from backend.apps.academico.models import Asistencia

        asistencia, created = Asistencia.objects.get_or_create(
            colegio=colegio,
            clase=clase,
            estudiante=estudiante,
            fecha=fecha,
            defaults={
                'estado': 'P',  # Presente por defecto
                'observaciones': f"[{tipo.upper()}] {contenido}"
            }
        )

        if not created:
            # Si ya existe, agregar a las observaciones existentes
            observacion_existente = asistencia.observaciones or ""
            asistencia.observaciones = f"{observacion_existente}\n[{tipo.upper()}] {contenido}".strip()
            asistencia.save()

        return None

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_STUDENTS')
    def get_academic_notes_summary(user, estudiante) -> Dict:
        """
        Obtiene un resumen de las anotaciones académicas de un estudiante.

        Args:
            estudiante: Estudiante

        Returns:
            Dict: Resumen de anotaciones
        """
        anotaciones = AcademicAnnotationsService.get_student_academic_annotations(estudiante)

        total_anotaciones = len(anotaciones)

        # Contar por tipo (si tuviéramos tipos definidos)
        tipos = {}
        for anotacion in anotaciones:
            tipo = anotacion.get('tipo', 'general')
            tipos[tipo] = tipos.get(tipo, 0) + 1

        # Anotaciones recientes (últimos 30 días)
        fecha_limite = date.today()
        recientes = [a for a in anotaciones if (fecha_limite - a['fecha']).days <= 30]

        return {
            'total_anotaciones': total_anotaciones,
            'anotaciones_por_tipo': tipos,
            'anotaciones_recientes': len(recientes),
            'ultima_anotacion': anotaciones[0] if anotaciones else None
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def update_evaluation_comment(user, colegio, calificacion_id: int, comentario: str) -> bool:
        """
        Actualiza el comentario de una calificación.

        Args:
            colegio: Colegio
            calificacion_id: ID de la calificación
            comentario: Nuevo comentario

        Returns:
            bool: True si se actualizó correctamente
        """
        # Nota: Actualmente el modelo Calificacion no tiene campo de comentario
        # Este método está preparado para cuando se agregue ese campo
        from backend.apps.academico.models import Calificacion

        AcademicAnnotationsService._validate_school_integrity(
            colegio.rbd,
            'UPDATE_EVALUATION_COMMENT'
        )

        try:
            calificacion = Calificacion.objects.get(
                id_calificacion=calificacion_id,
                colegio=colegio
            )
            # calificacion.comentario = comentario  # Campo no existe aún
            # calificacion.save()
            return True
        except Calificacion.DoesNotExist:
            return False
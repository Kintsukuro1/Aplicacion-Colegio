"""
Servicio de gestión de notas y evaluaciones académicas.
Maneja calificaciones, evaluaciones y cálculos académicos.
"""
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
from django.db.models import Count, Avg
from django.db import transaction
import logging

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService
from backend.common.services.onboarding_service import OnboardingService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('academico')


class GradesService:
    """Service para gestión de notas y evaluaciones académicas"""

    EVALUATION_PUBLISH_STATES = {'BORRADOR', 'EN_REVISION', 'PUBLICADA', 'APROBADA'}

    @staticmethod
    def validations(data: Dict[str, Any]) -> None:
        required = ['colegio', 'evaluacion', 'estudiante', 'nota', 'registrado_por']
        for field in required:
            if data.get(field) is None:
                raise ValueError(f'Parámetro requerido: {field}')

        nota = Decimal(str(data['nota']))
        escala = GradesService._get_escala(data['colegio'])
        if nota < escala['nota_minima'] or nota > escala['nota_maxima']:
            raise ValueError(
                f"La nota debe estar entre {escala['nota_minima']} y {escala['nota_maxima']}"
            )

    @staticmethod
    def create(data: Dict[str, Any]):
        from backend.apps.academico.models import Calificacion

        GradesService.validations(data)
        GradesService._validate_school_integrity(data['colegio'], 'CALIFICACION_CREATE')
        return Calificacion.objects.create(
            colegio=data['colegio'],
            evaluacion=data['evaluacion'],
            estudiante=data['estudiante'],
            nota=data['nota'],
            registrado_por=data['registrado_por'],
            actualizado_por=data.get('actualizado_por', data['registrado_por']),
        )

    @staticmethod
    def update(calificacion_id: int, data: Dict[str, Any]):
        calificacion = GradesService.get(calificacion_id)
        payload = {
            'colegio': data.get('colegio', calificacion.colegio),
            'evaluacion': data.get('evaluacion', calificacion.evaluacion),
            'estudiante': data.get('estudiante', calificacion.estudiante),
            'nota': data.get('nota', calificacion.nota),
            'registrado_por': data.get('registrado_por', calificacion.registrado_por),
            'actualizado_por': data.get('actualizado_por', calificacion.actualizado_por),
        }
        GradesService.validations(payload)
        GradesService._validate_school_integrity(payload['colegio'], 'CALIFICACION_UPDATE')

        calificacion.colegio = payload['colegio']
        calificacion.evaluacion = payload['evaluacion']
        calificacion.estudiante = payload['estudiante']
        calificacion.nota = payload['nota']
        calificacion.registrado_por = payload['registrado_por']
        calificacion.actualizado_por = payload.get('actualizado_por')
        calificacion.save()
        return calificacion

    @staticmethod
    def delete(calificacion_id: int) -> None:
        calificacion = GradesService.get(calificacion_id)
        GradesService._validate_school_integrity(calificacion.colegio, 'CALIFICACION_DELETE')
        calificacion.delete()

    @staticmethod
    def get(calificacion_id: int):
        from backend.apps.academico.models import Calificacion

        return Calificacion.objects.select_related(
            'colegio',
            'evaluacion',
            'estudiante',
            'registrado_por',
            'actualizado_por',
        ).get(id_calificacion=calificacion_id)

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        GradesService.validate(operation, params)
        return GradesService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(GradesService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _get_escala(colegio):
        """Obtiene la escala de notas configurada para el colegio."""
        from backend.apps.institucion.models import ConfiguracionAcademica
        return ConfiguracionAcademica.get_escala_para_colegio(colegio)

    @staticmethod
    def _validate_school_integrity(colegio, action: str) -> None:
        """Valida integridad del colegio antes de operaciones críticas."""
        action_map = {
            'CALIFICACION_CREATE': IntegrityService.validate_calificaciones_creation,
            'CALIFICACION_UPDATE': IntegrityService.validate_calificaciones_update,
            'CALIFICACION_DELETE': IntegrityService.validate_calificaciones_deletion,
        }
        validator = action_map.get(action)
        if validator is not None:
            validator(colegio)
            return

        IntegrityService.validate_school_integrity_or_raise(
            school_id=colegio.rbd,
            action=action,
        )

    @staticmethod
    def _build_preguntas_desde_post(post_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        preguntas: List[Dict[str, Any]] = []

        for indice in range(1, 5):
            enunciado = (post_data.get(f'pregunta_{indice}_enunciado') or '').strip()
            if not enunciado:
                continue

            tipo = (post_data.get(f'pregunta_{indice}_tipo') or 'opcion_multiple').strip()
            respuesta_texto = (post_data.get(f'pregunta_{indice}_respuesta_texto') or '').strip()
            pregunta = {
                'tipo': tipo,
                'enunciado': enunciado,
                'orden': indice,
                'puntaje_maximo': post_data.get(f'pregunta_{indice}_puntaje') or '1.0',
                'respuesta_correcta_texto': respuesta_texto,
                'respuesta_correcta_normalizada': respuesta_texto,
                'requiere_revision_docente': str(
                    post_data.get(f'pregunta_{indice}_requiere_revision_docente', '')
                ).lower() in ('1', 'true', 'on', 'yes', 'si', 'sí'),
                'activa': True,
            }

            if tipo == 'opcion_multiple':
                opciones: List[Dict[str, Any]] = []
                for opcion_indice in range(1, 5):
                    texto = (post_data.get(f'pregunta_{indice}_opcion_{opcion_indice}_texto') or '').strip()
                    if not texto:
                        continue
                    opciones.append(
                        {
                            'texto': texto,
                            'es_correcta': str(
                                post_data.get(f'pregunta_{indice}_opcion_{opcion_indice}_correcta', '')
                            ).lower() in ('1', 'true', 'on', 'yes', 'si', 'sí'),
                            'orden': opcion_indice,
                        }
                    )

                if not opciones:
                    raise ValueError(f'La pregunta {indice} debe tener al menos una opción.')
                if not any(opcion['es_correcta'] for opcion in opciones):
                    raise ValueError(f'Debe marcar al menos una opción correcta en la pregunta {indice}.')
                pregunta['opciones'] = opciones
            else:
                if not respuesta_texto:
                    raise ValueError(f'La pregunta {indice} requiere respuesta correcta escrita.')

            preguntas.append(pregunta)

        return preguntas

    @staticmethod
    def _get_primary_activity(evaluacion):
        actividad = evaluacion.actividades_resolubles.order_by('-fecha_actualizacion').first()
        if actividad is not None:
            evaluacion.actividad_resoluble_principal = actividad
            evaluacion.estado_publicacion = actividad.estado
            evaluacion.modalidad_publicacion = actividad.modalidad
        else:
            evaluacion.actividad_resoluble_principal = None
            evaluacion.estado_publicacion = 'SIN_ACTIVIDAD'
            evaluacion.modalidad_publicacion = None
        return actividad

    @staticmethod
    def _notificar_revision_pendiente(evaluacion, user) -> None:
        from backend.apps.notificaciones.models import Notificacion

        destinatario = evaluacion.clase.profesor or user
        Notificacion.objects.create(
            destinatario=destinatario,
            tipo='evaluacion',
            titulo=f'Revisión pendiente: {evaluacion.nombre}',
            mensaje='La evaluación quedó pendiente de revisión antes de su publicación.',
            enlace=f'/dashboard/?pagina=notas&clase_id={evaluacion.clase_id}',
            prioridad='alta',
        )

    @staticmethod
    def _notificar_publicacion_evaluacion(evaluacion, user) -> None:
        from backend.apps.notificaciones.models import Notificacion

        enlace_estudiante = f'/estudiante/clase/{evaluacion.clase_id}/?evaluacion={evaluacion.id_evaluacion}'
        for clase_estudiante in evaluacion.clase.estudiantes.select_related('estudiante').filter(activo=True):
            Notificacion.objects.create(
                destinatario=clase_estudiante.estudiante,
                tipo='evaluacion',
                titulo=f'Evaluación disponible: {evaluacion.nombre}',
                mensaje='La evaluación fue aprobada y ya está disponible.',
                enlace=enlace_estudiante,
                prioridad='normal',
            )

        profesor = evaluacion.clase.profesor or user
        if profesor:
            Notificacion.objects.create(
                destinatario=profesor,
                tipo='evaluacion',
                titulo=f'Evaluación publicada: {evaluacion.nombre}',
                mensaje='La evaluación fue aprobada correctamente.',
                enlace=f'/dashboard/?pagina=notas&clase_id={evaluacion.clase_id}',
                prioridad='normal',
            )

    @staticmethod
    def approve_evaluation_publication(user, colegio, evaluacion_id: int) -> bool:
        from backend.apps.academico.models import Evaluacion

        GradesService._validate_school_integrity(colegio, 'APPROVE_EVALUATION_PUBLICATION')
        evaluacion = Evaluacion.objects.select_related('clase').prefetch_related('actividades_resolubles').get(
            id_evaluacion=evaluacion_id,
            colegio=colegio,
        )

        GradesService._validate_clase_relationships(evaluacion.clase, colegio)
        actividad = GradesService._get_primary_activity(evaluacion)
        if actividad is None:
            raise ValueError('La evaluación no tiene una actividad resoluble asociada.')
        if actividad.estado == 'APROBADA':
            return True
        if actividad.modalidad == 'PDF' and not actividad.archivo_pdf:
            raise ValueError('La evaluación en formato PDF requiere un archivo adjunto.')
        if actividad.es_online() and not actividad.preguntas.exists():
            raise ValueError('La evaluación online requiere al menos una pregunta configurada.')

        actividad.estado = 'APROBADA'
        actividad.requiere_aprobacion_docente = False
        actividad.activa = True
        actividad.save(update_fields=['estado', 'requiere_aprobacion_docente', 'activa', 'fecha_actualizacion'])

        GradesService._notificar_publicacion_evaluacion(evaluacion, user)
        return True

    @staticmethod
    def _validate_clase_active_state(clase) -> None:
        """
        Valida que la clase y sus relaciones estén en estado activo.
        
        Args:
            clase: Objeto Clase a validar
            
        Raises:
            PrerequisiteException: Si la clase, curso o ciclo no están válidos
        """
        if not clase.activo:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Clase',
                    'field': 'activa',
                    'clase_id': getattr(clase, 'id_clase', getattr(clase, 'id', None)),
                    'message': 'La clase no está activa.',
                    'action': 'Seleccione una clase activa o reactive esta clase.'
                }
            )
        
        if not clase.curso.activo:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Clase',
                    'related_entity': 'Curso',
                    'curso_id': clase.curso.id_curso,
                    'message': 'El curso asociado a esta clase no está activo.',
                    'action': 'Active el curso antes de registrar evaluaciones.'
                }
            )
        
        if clase.curso.ciclo_academico.estado != 'ACTIVO':
            raise PrerequisiteException(
                error_type='STATE_MISMATCH',
                context={
                    'entity': 'Clase',
                    'related_entity': 'CicloAcademico',
                    'expected_state': 'ACTIVO',
                    'actual_state': clase.curso.ciclo_academico.estado,
                    'ciclo_nombre': clase.curso.ciclo_academico.nombre,
                    'message': f'El ciclo académico {clase.curso.ciclo_academico.nombre} no está activo.',
                    'action': 'No se pueden registrar evaluaciones en ciclos académicos cerrados.'
                }
            )

    @staticmethod
    def _validate_clase_relationships(clase, colegio) -> None:
        """Valida relaciones críticas de clase antes de crear evaluación."""
        if clase.colegio_id != colegio.rbd:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Clase',
                    'related_entity': 'Colegio',
                    'clase_id': getattr(clase, 'id_clase', getattr(clase, 'id', None)),
                    'clase_colegio': clase.colegio_id,
                    'colegio_rbd': colegio.rbd,
                    'message': 'La clase no pertenece al colegio informado.',
                    'action': 'Seleccione una clase del colegio actual.'
                }
            )

        if not clase.profesor_id:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Clase',
                    'related_entity': 'Profesor',
                    'clase_id': getattr(clase, 'id_clase', getattr(clase, 'id', None)),
                    'message': 'La clase no tiene profesor asignado.',
                    'action': 'Asigne un profesor antes de crear evaluaciones.'
                }
            )

        if not clase.profesor.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Profesor',
                    'field': 'is_active',
                    'profesor_id': clase.profesor_id,
                    'message': 'El profesor asignado a la clase está inactivo.',
                    'action': 'Active el profesor o asigne otro profesor activo.'
                }
            )

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def create_evaluation(
        user,
        colegio,
        clase,
        nombre: str,
        fecha_evaluacion,
        ponderacion: Decimal,
        periodo=None,
        tipo_evaluacion: str = 'sumativa',
        es_recuperacion: bool = False,
    ):
        """
        Crea una nueva evaluación para una clase.

        Args:
            colegio: Colegio
            clase: Clase para la evaluación
            nombre: Nombre de la evaluación
            fecha_evaluacion: Fecha de la evaluación
            ponderacion: Ponderación de la evaluación

        Returns:
            Evaluacion: Evaluación creada o dict con error
            
        Raises:
            PrerequisiteException: Si falta configuración inicial del colegio
        """
        from backend.apps.academico.models import Evaluacion

        # VALIDACIÓN DEFENSIVA: Verificar relaciones de clase
        GradesService._validate_clase_relationships(clase, colegio)

        GradesService._validate_school_integrity(colegio, 'CREATE_EVALUATION')
        
        # Validar prerequisitos de configuración
        OnboardingService.validate_prerequisite('CREATE_EVALUACION', colegio.rbd)

        # VALIDACIÓN DEFENSIVA: Verificar estado de la clase
        GradesService._validate_clase_active_state(clase)

        return Evaluacion.objects.create(
            colegio=colegio,
            clase=clase,
            nombre=nombre,
            fecha_evaluacion=fecha_evaluacion,
            ponderacion=ponderacion,
            periodo=periodo,
            tipo_evaluacion=tipo_evaluacion,
            es_recuperacion=es_recuperacion,
        )

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def update_evaluation(
        user,
        colegio,
        evaluacion_id: int,
        nombre: str,
        fecha_evaluacion,
        ponderacion: Decimal,
        periodo=None,
        tipo_evaluacion: Optional[str] = None,
        es_recuperacion: Optional[bool] = None,
    ) -> bool:
        """
        Actualiza una evaluación existente.

        Args:
            colegio: Colegio
            evaluacion_id: ID de la evaluación
            nombre: Nuevo nombre
            fecha_evaluacion: Nueva fecha
            ponderacion: Nueva ponderación

        Returns:
            bool: True si se actualizó correctamente
        """
        from backend.apps.academico.models import Evaluacion

        GradesService._validate_school_integrity(colegio, 'UPDATE_EVALUATION')

        try:
            evaluacion = Evaluacion.objects.get(
                id_evaluacion=evaluacion_id,
                colegio=colegio
            )
            evaluacion.nombre = nombre
            evaluacion.fecha_evaluacion = fecha_evaluacion
            evaluacion.ponderacion = ponderacion
            if periodo is not None:
                evaluacion.periodo = periodo
            if tipo_evaluacion:
                evaluacion.tipo_evaluacion = tipo_evaluacion
            if es_recuperacion is not None:
                evaluacion.es_recuperacion = es_recuperacion
            evaluacion.save()
            return True
        except Evaluacion.DoesNotExist:
            return False

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def delete_evaluation(user, colegio, evaluacion_id: int) -> bool:
        """
        Desactiva una evaluación (soft delete).

        Args:
            colegio: Colegio
            evaluacion_id: ID de la evaluación

        Returns:
            bool: True si se desactivó correctamente
        """
        from backend.apps.academico.models import Evaluacion

        GradesService._validate_school_integrity(colegio, 'DELETE_EVALUATION')

        try:
            evaluacion = Evaluacion.objects.get(
                id_evaluacion=evaluacion_id,
                colegio=colegio
            )
            evaluacion.activa = False
            evaluacion.save()
            return True
        except Evaluacion.DoesNotExist:
            return False

    @staticmethod
    def get_evaluations_for_class(clase) -> List:
        """
        Obtiene todas las evaluaciones activas de una clase con conteo de calificaciones.

        Args:
            clase: Clase

        Returns:
            List: Evaluaciones con total_calificaciones anotado
        """
        from backend.apps.academico.models import Evaluacion

        evaluaciones = Evaluacion.objects.filter(
            clase=clase,
            activa=True
        ).prefetch_related('actividades_resolubles').annotate(
            total_calificaciones=Count('calificaciones'),
            promedio_calculado=Avg('calificaciones__nota')
        ).order_by('-fecha_evaluacion')

        for evaluacion in evaluaciones:
            GradesService._get_primary_activity(evaluacion)

        return list(evaluaciones)

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def register_grades_for_evaluation(user, evaluacion, notas_dict: Dict[int, Decimal], colegio=None) -> int:
        """
        Registra calificaciones para una evaluación.

        Args:
            evaluacion: Evaluación
            notas_dict: Dict con {estudiante_id: nota}
            user: Usuario que registra las calificaciones (opcional)

        Returns:
            int: Cantidad de calificaciones registradas, o dict con error
        """
        from backend.apps.academico.models import Calificacion
        from backend.apps.accounts.models import User

        target_school = colegio if colegio is not None else evaluacion.colegio
        GradesService._validate_school_integrity(target_school, 'REGISTER_GRADES_FOR_EVALUATION')

        # VALIDACIÓN DEFENSIVA: Verificar estado de la clase antes de registrar notas
        GradesService._validate_clase_active_state(evaluacion.clase)

        # VALIDACIÓN DEFENSIVA: Verificar que la evaluación esté activa
        if not evaluacion.activa:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Evaluacion',
                    'field': 'activa',
                    'evaluacion_id': evaluacion.id_evaluacion,
                    'message': 'La evaluación no está activa.',
                    'action': 'No se pueden registrar notas en evaluaciones inactivas.'
                }
            )

        count = 0
        escala = GradesService._get_escala(target_school)
        nota_min = float(escala['nota_minima'])
        nota_max = float(escala['nota_maxima'])
        for estudiante_id, nota in notas_dict.items():
            if nota is not None and nota_min <= nota <= nota_max:
                try:
                    estudiante = User.objects.get(id=estudiante_id, rbd_colegio=evaluacion.colegio.rbd)
                    
                    # VALIDACIÓN DEFENSIVA: Verificar que el estudiante tenga matrícula activa en el ciclo actual
                    if hasattr(estudiante, 'perfil_estudiante'):
                        if estudiante.perfil_estudiante.ciclo_actual != evaluacion.clase.curso.ciclo_academico:
                            logger.warning(
                                f"Estudiante {estudiante_id} no pertenece al ciclo {evaluacion.clase.curso.ciclo_academico.nombre}, "
                                f"está en ciclo {estudiante.perfil_estudiante.ciclo_actual.nombre if estudiante.perfil_estudiante.ciclo_actual else 'sin ciclo'}"
                            )
                            continue
                    
                    defaults = {'nota': nota}
                    if user:
                        defaults.update({
                            'registrado_por': user,
                            'actualizado_por': user
                        })
                    Calificacion.objects.update_or_create(
                        colegio=evaluacion.colegio,
                        evaluacion=evaluacion,
                        estudiante=estudiante,
                        defaults=defaults
                    )
                    count += 1
                except User.DoesNotExist:
                    logger.warning(f"Estudiante {estudiante_id} no encontrado en colegio {evaluacion.colegio.rbd}")
                    continue

        return count

    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_GRADES'),
        ('ACADEMICO', 'VIEW_OWN_GRADES')
    ])
    def get_students_with_grades(user, colegio, evaluacion) -> List[Dict]:
        """
        Obtiene lista de estudiantes con sus calificaciones para una evaluación.

        Args:
            colegio: Colegio
            evaluacion: Evaluación seleccionada

        Returns:
            List[Dict]: Lista con estudiante, calificacion y nota, o dict con error
        """
        from backend.apps.academico.models import Calificacion
        from backend.apps.accounts.models import User

        # VALIDACIÓN DEFENSIVA: Verificar estado de la clase
        clase_error = GradesService._validate_clase_active_state(evaluacion.clase)
        if clase_error:
            logger.warning(f"Intento de consultar notas de evaluación {evaluacion.id_evaluacion} con clase inválida")
            return clase_error

        # Obtener solo estudiantes del ciclo activo correspondiente a la clase
        estudiantes = User.objects.filter(
            rbd_colegio=colegio.rbd,
            perfil_estudiante__isnull=False,
            is_active=True,
            perfil_estudiante__ciclo_actual=evaluacion.clase.curso.ciclo_academico
        ).select_related('perfil_estudiante').order_by('apellido_paterno', 'nombre')

        calificaciones_dict = {}
        calificaciones = Calificacion.objects.filter(
            evaluacion=evaluacion
        ).select_related('estudiante')

        for calif in calificaciones:
            calificaciones_dict[calif.estudiante.id] = calif

        estudiantes_con_notas = []
        for estudiante in estudiantes:
            calif = calificaciones_dict.get(estudiante.id)
            estudiantes_con_notas.append({
                'estudiante': estudiante,
                'calificacion': calif,
                'nota': calif.nota if calif else None
            })

        return estudiantes_con_notas

    @staticmethod
    def calculate_student_final_grade(estudiante, clase) -> Dict:
        """
        Calcula la nota final de un estudiante en una clase (promedio ponderado).

        Args:
            estudiante: Estudiante
            clase: Clase

        Returns:
            Dict: Información de la nota final
        """
        from backend.apps.academico.models import Calificacion

        calificaciones = Calificacion.objects.filter(
            estudiante=estudiante,
            evaluacion__clase=clase,
            evaluacion__activa=True
        ).select_related('evaluacion')

        if not calificaciones:
            return {
                'nota_final': None,
                'estado': 'Sin evaluaciones',
                'detalle': [],
                'sin_datos': True  # Flag: falta datos estructurales
            }

        suma_ponderada = 0
        suma_ponderaciones = 0
        detalle = []

        for calif in calificaciones:
            ponderacion = float(calif.evaluacion.ponderacion or 100)
            suma_ponderada += float(calif.nota) * ponderacion
            suma_ponderaciones += ponderacion
            detalle.append({
                'evaluacion': calif.evaluacion.nombre,
                'nota': calif.nota,
                'ponderacion': ponderacion
            })

        nota_final = suma_ponderada / suma_ponderaciones if suma_ponderaciones > 0 else 0

        # Obtener escala del colegio para redondeo y aprobación
        escala = GradesService._get_escala(
            getattr(clase, 'colegio', None) or
            (calificaciones[0].colegio if calificaciones else None)
        ) if calificaciones else {'nota_aprobacion': Decimal('4.0'), 'redondeo_decimales': 1}
        nota_final = round(nota_final, escala['redondeo_decimales'])

        estado = 'Aprobado' if nota_final >= float(escala['nota_aprobacion']) else 'Reprobado'

        return {
            'nota_final': nota_final,
            'estado': estado,
            'detalle': detalle,
            'sin_datos': False  # Flag: hay datos válidos
        }

    @staticmethod
    @PermissionService.require_permission_any([
        ('ACADEMICO', 'VIEW_GRADES'),
        ('ACADEMICO', 'VIEW_OWN_GRADES')
    ])
    def build_gradebook_matrix(user, colegio, clase) -> Dict[str, Any]:
        """
        Construye la matriz completa del libro de clases (estudiantes x evaluaciones).

        Args:
            colegio: Colegio
            clase: Clase seleccionada

        Returns:
            Dict: Contiene evaluaciones, matriz_calificaciones, promedios_evaluaciones, estadísticas
        """
        from backend.apps.academico.models import Evaluacion, Calificacion
        from backend.apps.accounts.models import User
        from collections import defaultdict

        evaluaciones = Evaluacion.objects.filter(
            clase=clase,
            activa=True
        ).order_by('fecha_evaluacion', 'nombre')

        estudiantes = User.objects.filter(
            rbd_colegio=colegio.rbd,
            perfil_estudiante__isnull=False,
            is_active=True,
            perfil_estudiante__ciclo_actual=clase.curso.ciclo_academico
        ).select_related('perfil_estudiante').order_by('apellido_paterno', 'apellido_materno', 'nombre')

        escala_gb = GradesService._get_escala(colegio)
        nota_aprob = float(escala_gb['nota_aprobacion'])

        # Cargar calificaciones en masa para evitar consulta N+1 por estudiante
        calificaciones_qs = Calificacion.objects.filter(
            evaluacion__clase=clase,
            evaluacion__activa=True
        )
        
        calificaciones_by_estudiante = defaultdict(dict)
        for cal in calificaciones_qs:
            calificaciones_by_estudiante[cal.estudiante_id][cal.evaluacion_id] = cal.nota

        matriz_calificaciones = []

        for estudiante in estudiantes:
            calificaciones_dict = calificaciones_by_estudiante.get(estudiante.pk, {})

            notas_fila = []
            suma_ponderada = 0
            suma_ponderaciones = 0

            for evaluacion in evaluaciones:
                nota = calificaciones_dict.get(evaluacion.pk)
                notas_fila.append(nota)

                if nota is not None:
                    ponderacion = float(evaluacion.ponderacion or 100)
                    suma_ponderada += float(nota) * ponderacion
                    suma_ponderaciones += ponderacion

            promedio = suma_ponderada / suma_ponderaciones if suma_ponderaciones > 0 else None
            promedio = round(promedio, 2) if promedio is not None else None

            matriz_calificaciones.append({
                'estudiante': estudiante,
                'notas': notas_fila,
                'promedio': promedio,
                'estado': 'Aprobado' if promedio and promedio >= nota_aprob else 'Reprobado' if promedio else 'Sin notas',
                'sin_datos': promedio is None  # Flag: True si no tiene notas
            })

        promedios_evaluaciones = []
        for i, evaluacion in enumerate(evaluaciones):
            notas_evaluacion = [
                fila['notas'][i]
                for fila in matriz_calificaciones
                if fila['notas'][i] is not None
            ]
            promedio_eval = sum(notas_evaluacion) / len(notas_evaluacion) if notas_evaluacion else None
            promedios_evaluaciones.append(round(promedio_eval, 2) if promedio_eval is not None else None)

        total_evaluaciones = evaluaciones.count()
        total_estudiantes = len(matriz_calificaciones)

        promedios = [fila['promedio'] for fila in matriz_calificaciones if fila['promedio'] is not None]
        promedio_general = sum(promedios) / len(promedios) if promedios else 0
        promedio_general = round(promedio_general, 2)

        return {
            'evaluaciones': list(evaluaciones),
            'matriz_calificaciones': matriz_calificaciones,
            'promedios_evaluaciones': promedios_evaluaciones,
            'total_evaluaciones': total_evaluaciones,
            'total_estudiantes': total_estudiantes,
            'promedio_general': promedio_general,
            'sin_datos': total_evaluaciones == 0 or not promedios  # Flag: True si no hay evaluaciones o promedios
        }

    @staticmethod
    def calculate_class_grades_stats(clase) -> Dict:
        """
        Calcula estadísticas de calificaciones de una clase.

        Args:
            clase: Clase

        Returns:
            Dict: Estadísticas de calificaciones
        """
        from backend.apps.academico.models import Evaluacion, Calificacion

        evaluaciones = Evaluacion.objects.filter(clase=clase, activa=True)
        total_evaluaciones = evaluaciones.count()

        calificaciones_clase = Calificacion.objects.filter(
            evaluacion__clase=clase,
            evaluacion__activa=True
        )
        total_calificaciones = calificaciones_clase.count()
        promedio_general = calificaciones_clase.aggregate(Avg('nota'))['nota__avg'] or 0
        promedio_general = round(promedio_general, 2)

        return {
            'total_evaluaciones': total_evaluaciones,
            'total_calificaciones': total_calificaciones,
            'promedio_general': promedio_general,
            'sin_datos': total_evaluaciones == 0 or total_calificaciones == 0  # Flag: True si no hay datos
        }

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def process_evaluation_action(user, colegio, post_data: Dict, files: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Procesa una acción de evaluación (crear, editar, eliminar).

        Args:
            user: Usuario que realiza la acción
            colegio: Colegio
            post_data: Datos del POST request

        Returns:
            Dict: Resultado con 'success', 'message', y 'redirect_url' si aplica
        """
        from backend.apps.cursos.models import Clase
        from django.urls import reverse
        
        try:
            action = post_data.get('accion')
            school_id = getattr(user, 'rbd_colegio', None)
            is_teacher_scope = PolicyService.has_capability(user, 'TEACHER_VIEW', school_id=school_id)
            is_admin_scope = PolicyService.has_capability(user, 'SYSTEM_CONFIGURE', school_id=school_id)
            archivos = files or {}
            
            if action == 'crear_evaluacion':
                clase_id = int(post_data.get('clase_id', 0))
                clase = Clase.objects.get(id=clase_id, colegio=colegio, activo=True)
                periodo = post_data.get('periodo') or None
                tipo_evaluacion = post_data.get('tipo_evaluacion') or 'sumativa'
                es_recuperacion = str(post_data.get('es_recuperacion', '')).lower() in ('1', 'true', 'on', 'si', 'sí')
                formato_evaluacion = (post_data.get('formato_evaluacion') or 'form').strip().lower()
                archivo_pdf = archivos.get('archivo_pdf')
                preguntas = GradesService._build_preguntas_desde_post(post_data)
                preguntas_payload = preguntas if formato_evaluacion != 'pdf' else None
                inferir_desde_pdf = formato_evaluacion == 'pdf' and archivo_pdf is not None

                if formato_evaluacion == 'pdf':
                    if not archivo_pdf:
                        return {'success': False, 'message': 'Debes adjuntar un PDF para este formato.'}
                elif not preguntas:
                    return {'success': False, 'message': 'Debes crear al menos una pregunta para la evaluación.'}
                
                # Validar permisos
                is_valid, error_msg = CommonValidations.validate_class_ownership(user, clase)
                if not is_valid:
                    return {'success': False, 'message': error_msg}

                with transaction.atomic():
                    evaluacion = GradesService.create_evaluation(
                        user=user,
                        colegio=colegio,
                        clase=clase,
                        nombre=post_data.get('nombre'),
                        fecha_evaluacion=post_data.get('fecha') or post_data.get('fecha_evaluacion'),
                        ponderacion=Decimal(post_data.get('ponderacion', '100.00')),
                        periodo=periodo,
                        tipo_evaluacion=tipo_evaluacion,
                        es_recuperacion=es_recuperacion,
                    )
                    from backend.apps.academico.services.resoluble_service import ResolubleService

                    ResolubleService.create_or_update_activity(
                        actor=user,
                        payload={
                            'origen_tipo': 'evaluacion',
                            'origen_id': evaluacion.id_evaluacion,
                            'titulo': evaluacion.nombre,
                            'modalidad': 'MIXTA' if formato_evaluacion == 'pdf' else 'ONLINE',
                            'archivo_pdf': archivo_pdf,
                            'requiere_aprobacion_docente': True,
                            'auto_correccion_activa': True,
                            'estado': 'EN_REVISION',
                            'activa': True,
                            'preguntas': preguntas_payload,
                            'inferir_desde_pdf': inferir_desde_pdf,
                        },
                    )
                    GradesService._notificar_revision_pendiente(evaluacion, user)

                return {
                    'success': True,
                    'message': 'Evaluación creada. Quedó pendiente de revisión antes de publicarse.',
                    'redirect_url': f"{reverse('dashboard')}?pagina=notas&clase_id={clase.id}"
                }
                
            elif action == 'editar_evaluacion':
                clase_id = int(post_data.get('clase_id', 0))
                clase = Clase.objects.get(id=clase_id, colegio=colegio, activo=True)
                periodo = post_data.get('periodo') or None
                tipo_evaluacion = post_data.get('tipo_evaluacion') or None
                es_recuperacion = None
                if post_data.get('es_recuperacion') is not None:
                    es_recuperacion = str(post_data.get('es_recuperacion', '')).lower() in ('1', 'true', 'on', 'si', 'sí')
                formato_evaluacion = (post_data.get('formato_evaluacion') or 'form').strip().lower()
                archivo_pdf = archivos.get('archivo_pdf')
                preguntas_presentes = any(
                    (post_data.get(f'pregunta_{indice}_enunciado') or '').strip()
                    for indice in range(1, 5)
                )
                preguntas = GradesService._build_preguntas_desde_post(post_data) if preguntas_presentes else None
                inferir_desde_pdf = formato_evaluacion == 'pdf' and archivo_pdf is not None

                actividad_existente = None
                from backend.apps.academico.models import Evaluacion
                actividad_existente = Evaluacion.objects.prefetch_related('actividades_resolubles').filter(
                    id_evaluacion=int(post_data.get('id')),
                    colegio=colegio,
                ).first()
                actividad_actual = None
                if formato_evaluacion == 'pdf' and archivo_pdf is None and actividad_existente is not None:
                    actividad_actual = actividad_existente.actividades_resolubles.order_by('-fecha_actualizacion').first()
                    if actividad_actual and actividad_actual.archivo_pdf:
                        archivo_pdf = actividad_actual.archivo_pdf
                elif actividad_existente is not None:
                    actividad_actual = actividad_existente.actividades_resolubles.order_by('-fecha_actualizacion').first()
                if formato_evaluacion == 'pdf' and not archivo_pdf and not (actividad_actual and actividad_actual.archivo_pdf):
                    return {'success': False, 'message': 'Debes adjuntar un PDF para cambiar el formato a PDF.'}
                if formato_evaluacion != 'pdf' and not preguntas_presentes and not (actividad_actual and actividad_actual.preguntas.exists()):
                    return {'success': False, 'message': 'Debes crear preguntas para publicar una evaluación en formulario.'}
                
                # Validar permisos
                is_valid, error_msg = CommonValidations.validate_class_ownership(user, clase)
                if not is_valid:
                    return {'success': False, 'message': error_msg}
                
                success = GradesService.update_evaluation(
                    user=user,
                    colegio=colegio,
                    evaluacion_id=int(post_data.get('id')),
                    nombre=post_data.get('nombre'),
                    fecha_evaluacion=post_data.get('fecha') or post_data.get('fecha_evaluacion'),
                    ponderacion=Decimal(post_data.get('ponderacion')),
                    periodo=periodo,
                    tipo_evaluacion=tipo_evaluacion,
                    es_recuperacion=es_recuperacion,
                )
                if success:
                    from backend.apps.academico.models import Evaluacion
                    from backend.apps.academico.services.resoluble_service import ResolubleService

                    evaluacion = Evaluacion.objects.select_related('clase').prefetch_related('actividades_resolubles').get(
                        id_evaluacion=int(post_data.get('id')),
                        colegio=colegio,
                    )
                    preguntas_payload = preguntas if formato_evaluacion == 'pdf' or preguntas else None
                    ResolubleService.create_or_update_activity(
                        actor=user,
                        payload={
                            'origen_tipo': 'evaluacion',
                            'origen_id': evaluacion.id_evaluacion,
                            'titulo': evaluacion.nombre,
                            'modalidad': 'MIXTA' if formato_evaluacion == 'pdf' else 'ONLINE',
                            'archivo_pdf': archivo_pdf,
                            'requiere_aprobacion_docente': True,
                            'auto_correccion_activa': True,
                            'estado': 'EN_REVISION',
                            'activa': True,
                            **({'preguntas': None} if formato_evaluacion == 'pdf' else ({'preguntas': preguntas} if preguntas is not None else {})),
                            'inferir_desde_pdf': inferir_desde_pdf,
                        },
                    )
                    GradesService._notificar_revision_pendiente(evaluacion, user)
                    return {
                        'success': True,
                        'message': 'Evaluación actualizada. Quedó pendiente de revisión antes de publicarse.',
                        'redirect_url': f"{reverse('dashboard')}?pagina=notas&clase_id={clase.id}"
                    }
                else:
                    return {'success': False, 'message': 'No se encontró la evaluación.'}
            elif action == 'aprobar_publicacion_evaluacion':
                evaluacion_id = int(post_data.get('id', 0))

                from backend.apps.academico.models import Evaluacion

                evaluacion = Evaluacion.objects.select_related('clase').get(
                    id_evaluacion=evaluacion_id,
                    colegio=colegio,
                )

                if is_teacher_scope and not is_admin_scope:
                    is_valid, error_msg = CommonValidations.validate_class_ownership(user, evaluacion.clase)
                    if not is_valid:
                        return {'success': False, 'message': error_msg}

                GradesService.approve_evaluation_publication(user, colegio, evaluacion_id)
                return {
                    'success': True,
                    'message': 'La evaluación fue aprobada y publicada para los estudiantes.',
                    'redirect_url': f"{reverse('dashboard')}?pagina=notas&clase_id={evaluacion.clase_id}"
                }
                    
            elif action == 'eliminar_evaluacion':
                evaluacion_id = int(post_data.get('id', 0))
                
                # Obtener evaluación para validación de permisos
                from backend.apps.academico.models import Evaluacion
                evaluacion = Evaluacion.objects.select_related('clase').get(
                    id_evaluacion=evaluacion_id, colegio=colegio
                )
                
                if is_teacher_scope and not is_admin_scope:
                    is_valid, error_msg = CommonValidations.validate_class_ownership(user, evaluacion.clase)
                    if not is_valid:
                        return {'success': False, 'message': error_msg}
                
                success = GradesService.delete_evaluation(
                    user=user,
                    colegio=colegio,
                    evaluacion_id=evaluacion_id
                )
                if success:
                    return {
                        'success': True, 
                        'message': 'Evaluación desactivada exitosamente.',
                        'redirect_url': f"{reverse('dashboard')}?pagina=notas&clase_id={evaluacion.clase_id}"
                    }
                else:
                    return {'success': False, 'message': 'No se encontró la evaluación.'}
                    
        except PrerequisiteException as e:
            # Capturar errores de configuración incompleta
            return {
                'success': False,
                'message': e.error_dict['message'],
                'redirect_url': e.error_dict.get('action_url')
            }
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
    def process_grades_registration(user, colegio, post_data: Dict) -> Dict:
        """
        Procesa el registro de calificaciones para una evaluación.

        Args:
            user: Usuario que registra las calificaciones
            colegio: Colegio
            post_data: Datos del POST request

        Returns:
            Dict: Resultado con 'success', 'message', y 'redirect_url'
        """
        from django.urls import reverse
        
        try:
            school_id = getattr(user, 'rbd_colegio', None)
            is_teacher_scope = PolicyService.has_capability(user, 'TEACHER_VIEW', school_id=school_id)
            is_admin_scope = PolicyService.has_capability(user, 'SYSTEM_CONFIGURE', school_id=school_id)
            
            from backend.apps.academico.models import Evaluacion
            evaluacion = Evaluacion.objects.select_related('clase').get(
                id_evaluacion=post_data.get('evaluacion_id'),
                colegio=colegio
            )
            
            # Validar permisos
            if is_teacher_scope and not is_admin_scope:
                is_valid, error_msg = CommonValidations.validate_class_ownership(user, evaluacion.clase)
                if not is_valid:
                    return {'success': False, 'message': error_msg}
            
            # Extraer notas del POST
            escala = GradesService._get_escala(colegio)
            nota_min = float(escala['nota_minima'])
            nota_max = float(escala['nota_maxima'])
            grades_dict = {}
            for key in post_data.keys():
                if key.startswith('nota_'):
                    estudiante_id = int(key.replace('nota_', ''))
                    nota_str = post_data.get(key)
                    if nota_str and nota_str.strip():
                        try:
                            nota = Decimal(nota_str)
                            if nota_min <= float(nota) <= nota_max:
                                grades_dict[estudiante_id] = nota
                        except (ValueError, TypeError):
                            continue
            
            # Registrar calificaciones
            registered_count = GradesService.register_grades_for_evaluation(
                user=user,
                evaluacion=evaluacion,
                notas_dict=grades_dict,
                colegio=colegio
            )
            
            return {
                'success': True,
                'message': f'Calificaciones guardadas ({registered_count})',
                'redirect_url': f"{reverse('dashboard')}?pagina=notas&modo=calificar&clase_id={evaluacion.clase_id}&evaluacion_id={evaluacion.id_evaluacion}",
                'registered_count': registered_count
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error al registrar calificaciones: {str(e)}'}

    @staticmethod
    def get_teacher_classes_for_grades(user, colegio) -> List:
        """
        Obtiene clases del profesor para gestión de notas.

        Args:
            user: Usuario profesor
            colegio: Colegio

        Returns:
            List: QuerySet de clases
        """
        from backend.apps.cursos.models import Clase
        
        return Clase.objects.filter(
            profesor=user,
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso')

    @staticmethod
    def get_evaluations_for_class(clase) -> List:
        """
        Obtiene evaluaciones de una clase.

        Args:
            clase: Clase

        Returns:
            List: Lista de evaluaciones
        """
        from backend.apps.academico.models import Evaluacion
        
        return list(Evaluacion.objects.filter(
            clase=clase,
            activa=True
        ).order_by('-fecha_evaluacion'))

    @staticmethod
    def get_evaluation_by_id(colegio, evaluacion_id: int):
        """
        Obtiene una evaluación por ID.

        Args:
            colegio: Colegio
            evaluacion_id: ID de la evaluación

        Returns:
            Evaluacion or None
        """
        from backend.apps.academico.models import Evaluacion
        
        try:
            return Evaluacion.objects.get(
                id_evaluacion=evaluacion_id,
                colegio=colegio
            )
        except Evaluacion.DoesNotExist:
            return None

    @staticmethod
    def get_students_with_grades(colegio, evaluacion) -> List[Dict]:
        """
        Obtiene estudiantes con sus calificaciones para una evaluación.

        Args:
            colegio: Colegio
            evaluacion: Evaluacion

        Returns:
            List[Dict]: Lista de estudiantes con calificaciones
        """
        from backend.apps.accounts.models import User
        
        estudiantes = User.objects.filter(
            rbd_colegio=colegio.rbd,
            perfil_estudiante__isnull=False,
            is_active=True,
            perfil_estudiante__ciclo_actual=evaluacion.clase.curso.ciclo_academico
        ).select_related('perfil_estudiante').order_by('apellido_paterno', 'nombre')
        
        estudiantes_con_notas = []
        calificaciones_dict = {c.estudiante.id: c for c in evaluacion.calificaciones.all()}
        
        for estudiante in estudiantes:
            calificacion = calificaciones_dict.get(estudiante.id)
            estudiantes_con_notas.append({
                'estudiante': estudiante,
                'calificacion': calificacion.nota if calificacion else None,
                'fecha_registro': calificacion.fecha_creacion if calificacion else None
            })
        
        return estudiantes_con_notas

    @staticmethod
    def get_teacher_classes_for_gradebook(user, colegio) -> List:
        """
        Obtiene clases del profesor para libro de clases.

        Args:
            user: Usuario profesor
            colegio: Colegio

        Returns:
            List: QuerySet de clases
        """
        return GradesService.get_teacher_classes_for_grades(user, colegio)

    @staticmethod
    def build_gradebook_matrix(colegio, clase) -> Dict:
        """
        Construye matriz completa de calificaciones para libro de clases.

        Args:
            colegio: Colegio
            clase: Clase

        Returns:
            Dict: Datos de la matriz de calificaciones
        """
        from backend.apps.academico.models import Evaluacion, Calificacion
        from backend.apps.accounts.models import User
        from collections import defaultdict
        
        # Obtener evaluaciones
        evaluaciones = list(Evaluacion.objects.filter(
            clase=clase,
            activa=True
        ).order_by('fecha_evaluacion'))
        
        # Obtener estudiantes
        estudiantes = User.objects.filter(
            rbd_colegio=colegio.rbd,
            perfil_estudiante__isnull=False,
            is_active=True,
            perfil_estudiante__ciclo_actual=clase.curso.ciclo_academico
        ).select_related('perfil_estudiante').order_by('apellido_paterno', 'nombre')
        
        # Cargar calificaciones en masa para evitar consulta N+1 cuadrática
        calificaciones_qs = list(Calificacion.objects.filter(
            evaluacion__clase=clase,
            evaluacion__activa=True
        ))
        
        calificaciones_by_estudiante = defaultdict(dict)
        for cal in calificaciones_qs:
            calificaciones_by_estudiante[cal.estudiante_id][cal.evaluacion_id] = cal
            
        # Calcular en memoria acumuladores por evaluación
        valores_por_evaluacion = defaultdict(list)
        for cal in calificaciones_qs:
            if cal.nota is not None:
                valores_por_evaluacion[cal.evaluacion_id].append(float(cal.nota))

        escala_gb = GradesService._get_escala(colegio)
        nota_aprob = float(escala_gb['nota_aprobacion'])

        # Construir matriz
        matriz_calificaciones = []
        
        for estudiante in estudiantes:
            fila_estudiante = {
                'estudiante': estudiante,
                'notas': []
            }
            
            suma_notas = 0
            contador_notas = 0
            calificaciones_dict = calificaciones_by_estudiante.get(estudiante.pk, {})
            
            for evaluacion in evaluaciones:
                calificacion = calificaciones_dict.get(evaluacion.pk)
                nota_valor = float(calificacion.nota) if calificacion else None
                fila_estudiante['notas'].append(nota_valor)
                
                if nota_valor is not None:
                    suma_notas += nota_valor
                    contador_notas += 1
            
            # Calcular promedio del estudiante
            if contador_notas > 0:
                fila_estudiante['promedio'] = round(suma_notas / contador_notas, 1)
                fila_estudiante['estado'] = 'Aprobado' if fila_estudiante['promedio'] >= nota_aprob else 'Reprobado'
            else:
                fila_estudiante['promedio'] = None
                fila_estudiante['estado'] = 'Sin Notas'
            
            matriz_calificaciones.append(fila_estudiante)
        
        # Calcular promedios por evaluación en memoria
        promedios_evaluaciones = []
        for evaluacion in evaluaciones:
            notas_eval = valores_por_evaluacion.get(evaluacion.pk, [])
            promedio = sum(notas_eval) / len(notas_eval) if notas_eval else None
            promedios_evaluaciones.append(round(promedio, 1) if promedio is not None else None)
        
        # Estadísticas generales en memoria
        calificaciones_validas = [float(cal.nota) for cal in calificaciones_qs if cal.nota is not None]
        total_calificaciones = len(calificaciones_validas)
        
        promedio_general = 0
        if total_calificaciones > 0:
            promedio_general = sum(calificaciones_validas) / total_calificaciones
            promedio_general = round(promedio_general, 1)
        
        return {
            'evaluaciones': evaluaciones,
            'matriz_calificaciones': matriz_calificaciones,
            'promedios_evaluaciones': promedios_evaluaciones,
            'total_evaluaciones': len(evaluaciones),
            'total_estudiantes': len(matriz_calificaciones),
            'promedio_general': promedio_general
        }

    @staticmethod
    def get_student_grades_summary(user) -> Dict:
        """
        Obtiene resumen de notas del estudiante.

        Args:
            user: Usuario estudiante

        Returns:
            Dict: Resumen de notas por asignatura
        """
        from backend.apps.accounts.models import PerfilEstudiante
        
        try:
            perfil = PerfilEstudiante.objects.get(user=user)
            curso_actual = perfil.curso_actual
            
            if not curso_actual:
                return {'error': 'No course assigned'}
            
            # Obtener clases del curso
            clases = curso_actual.clases.filter(activo=True).select_related('asignatura', 'profesor')
            
            # Calcular notas por asignatura
            notas_por_asignatura = []
            for clase in clases:
                final_grade = GradesService.calculate_student_final_grade(user, clase)
                if final_grade['nota_final']:
                    # Obtener evaluaciones con fechas
                    from backend.apps.academico.models import Calificacion
                    evaluaciones_detalle = []
                    calificaciones = Calificacion.objects.filter(
                        estudiante=user,
                        evaluacion__clase=clase,
                        evaluacion__activa=True
                    ).select_related('evaluacion').order_by('evaluacion__fecha_evaluacion')
                    
                    for calif in calificaciones:
                        evaluaciones_detalle.append({
                            'nombre': calif.evaluacion.nombre,
                            'nota': calif.nota,
                            'ponderacion': calif.evaluacion.ponderacion,
                            'fecha': calif.evaluacion.fecha_evaluacion
                        })
                    
                    notas_por_asignatura.append({
                        'asignatura': clase.asignatura.nombre,
                        'promedio': final_grade['nota_final'],
                        'estado': final_grade['estado'],
                        'profesor': clase.profesor.get_full_name() if clase.profesor else 'Sin asignar',
                        'evaluaciones': evaluaciones_detalle,
                        'total_evaluaciones': len(evaluaciones_detalle)
                    })
            
            # Calcular promedio general
            promedio_general = (
                sum([n['promedio'] for n in notas_por_asignatura]) / len(notas_por_asignatura)
                if notas_por_asignatura else 0
            )
            promedio_general = round(float(promedio_general), 1)
            
            return {
                'notas_por_asignatura': notas_por_asignatura,
                'promedio_general': promedio_general,
                'total_notas': len(notas_por_asignatura),
                'curso_actual': curso_actual.nombre,
                'sin_datos': len(notas_por_asignatura) == 0
            }
            
        except PerfilEstudiante.DoesNotExist:
            logger.warning(f"PerfilEstudiante no encontrado para usuario {user.id}")
            return {
                'notas_por_asignatura': [],
                'promedio_general': 0,
                'total_notas': 0,
                'curso_actual': 'Sin curso',
                'sin_datos': True,
                'error': 'Student profile not found'
            }
        except Exception as e:
            logger.error(f"Error en get_student_grades_summary: {str(e)}")
            return {
                'notas_por_asignatura': [],
                'promedio_general': 0,
                'total_notas': 0,
                'curso_actual': 'Sin curso',
                'sin_datos': True,
                'error': f'Error: {str(e)}'
            }

    @staticmethod
    def get_student_classes_summary(user) -> Dict:
        """
        Obtiene resumen de clases del estudiante.

        Args:
            user: Usuario estudiante

        Returns:
            Dict: Resumen de clases
        """
        try:
            perfil = user.perfil_estudiante
            curso_actual = perfil.curso_actual
            
            if not curso_actual:
                return {'error': 'No tienes un curso asignado actualmente.'}
            
            from backend.apps.cursos.models import Clase
            clases = Clase.objects.filter(
                colegio=user.colegio,
                curso=curso_actual,
                activo=True
            ).select_related('asignatura', 'profesor').order_by('asignatura__nombre')
            
            return {
                'clases': [
                    {
                        'id': clase.id,
                        'asignatura': clase.asignatura.nombre,
                        'profesor': clase.profesor.get_full_name(),
                        'color': clase.asignatura.color,
                        'horas_semanales': clase.asignatura.horas_semanales
                    } for clase in clases
                ],
                'curso_actual': curso_actual.nombre,
                'total_clases': len(clases)
            }
            
        except Exception as e:
            return {'error': str(e)}

"""
Servicio de gestión de asistencia académica.
Maneja registro, consulta y estadísticas de asistencia de estudiantes.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from django.db.models import Count, Q
import logging

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.common.exceptions import PrerequisiteException
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('academico')


class AttendanceService:
    """Service para gestión de asistencia académica"""

    @staticmethod
    def validations(data: Dict[str, Any]) -> None:
        required = ['colegio', 'clase', 'estudiante', 'fecha', 'estado']
        for field in required:
            if data.get(field) is None:
                raise ValueError(f'Parámetro requerido: {field}')

        if data['estado'] not in [
            AttendanceService.PRESENTE,
            AttendanceService.AUSENTE,
            AttendanceService.TARDANZA,
            AttendanceService.JUSTIFICADA,
        ]:
            raise ValueError('Estado de asistencia inválido')

    @staticmethod
    def create(data: Dict[str, Any]):
        from backend.apps.academico.models import Asistencia

        AttendanceService.validations(data)
        AttendanceService._validate_school_integrity(data['colegio'], 'ASISTENCIA_CREATE')
        return Asistencia.objects.create(
            colegio=data['colegio'],
            clase=data['clase'],
            estudiante=data['estudiante'],
            fecha=data['fecha'],
            estado=data['estado'],
            tipo_asistencia=data.get('tipo_asistencia', 'Presencial'),
            observaciones=data.get('observaciones'),
        )

    @staticmethod
    def update(asistencia_id: int, data: Dict[str, Any]):
        asistencia = AttendanceService.get(asistencia_id)
        payload = {
            'colegio': data.get('colegio', asistencia.colegio),
            'clase': data.get('clase', asistencia.clase),
            'estudiante': data.get('estudiante', asistencia.estudiante),
            'fecha': data.get('fecha', asistencia.fecha),
            'estado': data.get('estado', asistencia.estado),
            'tipo_asistencia': data.get('tipo_asistencia', asistencia.tipo_asistencia),
            'observaciones': data.get('observaciones', asistencia.observaciones),
        }
        AttendanceService.validations(payload)
        AttendanceService._validate_school_integrity(payload['colegio'], 'ASISTENCIA_UPDATE')

        asistencia.colegio = payload['colegio']
        asistencia.clase = payload['clase']
        asistencia.estudiante = payload['estudiante']
        asistencia.fecha = payload['fecha']
        asistencia.estado = payload['estado']
        asistencia.tipo_asistencia = payload['tipo_asistencia']
        asistencia.observaciones = payload['observaciones']
        asistencia.save()
        return asistencia

    @staticmethod
    def delete(asistencia_id: int) -> None:
        asistencia = AttendanceService.get(asistencia_id)
        AttendanceService._validate_school_integrity(asistencia.colegio, 'ASISTENCIA_DELETE')
        asistencia.delete()

    @staticmethod
    def get(asistencia_id: int):
        from backend.apps.academico.models import Asistencia

        return Asistencia.objects.select_related('colegio', 'clase', 'estudiante').get(id_asistencia=asistencia_id)

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        AttendanceService.validate(operation, params)
        return AttendanceService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(AttendanceService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')

    # Estados de asistencia
    PRESENTE = 'P'
    AUSENTE = 'A'
    TARDANZA = 'T'
    JUSTIFICADA = 'J'

    ESTADOS_CHOICES = [
        (PRESENTE, 'Presente'),
        (AUSENTE, 'Ausente'),
        (TARDANZA, 'Tardanza'),
        (JUSTIFICADA, 'Justificada'),
    ]

    @staticmethod
    def _validate_school_integrity(colegio, action: str) -> None:
        """Valida integridad del colegio antes de operaciones críticas."""
        action_map = {
            'ASISTENCIA_CREATE': IntegrityService.validate_asistencia_creation,
            'ASISTENCIA_UPDATE': IntegrityService.validate_asistencia_update,
            'ASISTENCIA_DELETE': IntegrityService.validate_asistencia_deletion,
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
    def _validate_clase_for_attendance(clase) -> None:
        """
        Valida que la clase esté en estado válido para registro de asistencia.
        
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
                    'field': 'activo',
                    'clase_id': clase.id_clase,
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
                    'action': 'Active el curso antes de registrar asistencia.'
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
                    'action': 'No se puede registrar asistencia en ciclos cerrados.'
                }
            )

    @staticmethod
    def get_students_for_class(user, colegio, clase) -> List[Dict]:
        """
        Obtiene lista de estudiantes de una clase para registro de asistencia.

        Args:
            colegio: Colegio
            clase: Clase

        Returns:
            List[Dict]: Lista de estudiantes con su información básica
        
        Raises:
            PrerequisiteException: Si la clase no está válida
        """
        from backend.apps.accounts.models import User

        AttendanceService._validate_school_integrity(colegio, 'GET_STUDENTS_FOR_CLASS')

        # VALIDACIÓN DEFENSIVA: Verificar estado de la clase
        AttendanceService._validate_clase_for_attendance(clase)

        # Obtener solo estudiantes del ciclo activo correspondiente a la clase
        estudiantes = User.objects.filter(
            rbd_colegio=colegio.rbd,
            perfil_estudiante__isnull=False,
            is_active=True,
            perfil_estudiante__ciclo_actual=clase.curso.ciclo_academico
        ).select_related('perfil_estudiante').order_by('apellido_paterno', 'nombre')

        return [{
            'id': estudiante.id,
            'nombre': estudiante.nombre,
            'apellido_paterno': estudiante.apellido_paterno,
            'apellido_materno': estudiante.apellido_materno,
            'rut': estudiante.rut
        } for estudiante in estudiantes]

    @staticmethod
    def register_attendance_for_class(user, colegio, clase, fecha, estudiantes_estados: Dict[int, str]) -> int:
        """
        Registra la asistencia para una clase en una fecha específica.

        Args:
            colegio: Colegio
            clase: Clase para registrar asistencia
            fecha: Fecha de la asistencia (date object)
            estudiantes_estados: Dict con {estudiante_id: estado} ('P', 'A', 'T', 'J')

        Returns:
            int: Cantidad de asistencias registradas
        
        Raises:
            PrerequisiteException: Si la clase no es válida o fecha fuera de rango
        """
        from backend.apps.academico.models import Asistencia
        from backend.apps.accounts.models import User

        AttendanceService._validate_school_integrity(colegio, 'REGISTER_ATTENDANCE_FOR_CLASS')

        # VALIDACIÓN DEFENSIVA: Verificar estado de la clase
        AttendanceService._validate_clase_for_attendance(clase)

        # VALIDACIÓN DEFENSIVA: Verificar que la fecha esté dentro del ciclo académico
        ciclo = clase.curso.ciclo_academico
        if fecha < ciclo.fecha_inicio or fecha > ciclo.fecha_fin:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Asistencia',
                    'field': 'fecha',
                    'fecha': str(fecha),
                    'ciclo_inicio': str(ciclo.fecha_inicio),
                    'ciclo_fin': str(ciclo.fecha_fin),
                    'message': f'La fecha {fecha} está fuera del rango del ciclo académico {ciclo.nombre}.',
                    'action': f'Seleccione una fecha entre {ciclo.fecha_inicio} y {ciclo.fecha_fin}.'
                }
            )

        count = 0
        for estudiante_id, estado in estudiantes_estados.items():
            if estado in [AttendanceService.PRESENTE, AttendanceService.AUSENTE,
                         AttendanceService.TARDANZA, AttendanceService.JUSTIFICADA]:
                try:
                    estudiante = User.objects.get(id=estudiante_id, rbd_colegio=colegio.rbd)
                    
                    # VALIDACIÓN DEFENSIVA: Verificar que el estudiante pertenezca al ciclo correcto
                    if hasattr(estudiante, 'perfil_estudiante'):
                        if estudiante.perfil_estudiante.ciclo_actual != ciclo:
                            logger.warning(
                                f"Estudiante {estudiante_id} no pertenece al ciclo {ciclo.nombre}, "
                                f"está en ciclo {estudiante.perfil_estudiante.ciclo_actual.nombre if estudiante.perfil_estudiante.ciclo_actual else 'sin ciclo'}"
                            )
                            continue
                    
                    # Control defensivo de duplicados: consultar estado anterior
                    try:
                        asistencia_previa = Asistencia.objects.get(
                            colegio=colegio,
                            clase=clase,
                            estudiante=estudiante,
                            fecha=fecha
                        )
                        estado_anterior = asistencia_previa.estado
                    except Asistencia.DoesNotExist:
                        estado_anterior = None

                    Asistencia.objects.update_or_create(
                        colegio=colegio,
                        clase=clase,
                        estudiante=estudiante,
                        fecha=fecha,
                        defaults={'estado': estado}
                    )
                    count += 1

                    # Disparar notificación si pasa a estar ausente
                    if estado in [AttendanceService.AUSENTE, 'AUSENTE', 'A'] and estado_anterior not in [AttendanceService.AUSENTE, 'AUSENTE', 'A']:
                        from backend.apps.notificaciones.services.attendance_notifications import AttendanceNotificationService
                        try:
                            AttendanceNotificationService.notify_absence(
                                estudiante=estudiante,
                                clase=clase,
                                fecha=fecha,
                                registrada_por=user
                            )
                        except Exception as e:
                            logger.error(f"Error al enviar notificacion de inasistencia en AttendanceService: {e}", exc_info=True)
                except User.DoesNotExist:
                    logger.warning(f"Estudiante {estudiante_id} no encontrado en colegio {colegio.rbd}")
                    continue

        return count

    @staticmethod
    def update_attendance_observation(user, colegio, asistencia_id: int, observaciones: str) -> bool:
        """
        Actualiza las observaciones de un registro de asistencia.

        Args:
            colegio: Colegio
            asistencia_id: ID de la asistencia
            observaciones: Texto de observaciones

        Returns:
            bool: True si se actualizó correctamente
        """
        from backend.apps.academico.models import Asistencia

        AttendanceService._validate_school_integrity(colegio, 'UPDATE_ATTENDANCE_OBSERVATION')

        try:
            asistencia = Asistencia.objects.get(
                id_asistencia=asistencia_id,
                colegio=colegio
            )
            asistencia.observaciones = observaciones
            asistencia.save()
            return True
        except Asistencia.DoesNotExist:
            return False

    @staticmethod
    def get_students_with_attendance(user, colegio, clase, fecha_filtro: date) -> List[Dict]:
        """
        Obtiene lista de estudiantes con su asistencia para una clase y fecha.

        Args:
            colegio: Colegio
            clase: Clase seleccionada
            fecha_filtro: Fecha para buscar asistencia

        Returns:
            List[Dict]: Lista con estudiante, asistencia y estado
        """
        from backend.apps.academico.models import Asistencia
        from backend.apps.accounts.models import User
        from backend.apps.cursos.models import ClaseEstudiante

        inscripciones = ClaseEstudiante._base_manager.filter(
            clase=clase,
            activo=True,
        ).select_related('estudiante').order_by(
            'estudiante__apellido_paterno',
            'estudiante__nombre',
        )

        if inscripciones.exists():
            estudiantes = [rel.estudiante for rel in inscripciones if rel.estudiante.is_active]
        else:
            estudiantes = list(
                User.objects.filter(
                    rbd_colegio=colegio.rbd,
                    perfil_estudiante__isnull=False,
                    is_active=True,
                    perfil_estudiante__ciclo_actual=clase.curso.ciclo_academico,
                ).select_related('perfil_estudiante').order_by('apellido_paterno', 'nombre')
            )
            if not estudiantes:
                # Clases con historial de asistencia pero sin filas en clase_estudiante (p. ej. tras restore)
                estudiante_ids = (
                    Asistencia.objects.filter(clase=clase)
                    .values_list('estudiante_id', flat=True)
                    .distinct()
                )
                estudiantes = list(
                    User.objects.filter(id__in=estudiante_ids, is_active=True).order_by(
                        'apellido_paterno', 'nombre'
                    )
                )

        asistencias_dict = {}
        asistencias = Asistencia.objects.filter(
            clase=clase,
            fecha=fecha_filtro
        ).select_related('estudiante')

        for asistencia in asistencias:
            asistencias_dict[asistencia.estudiante.id] = asistencia

        estudiantes_con_asistencia = []
        for estudiante in estudiantes:
            asistencia = asistencias_dict.get(estudiante.id)
            estudiantes_con_asistencia.append({
                'estudiante': estudiante,
                'asistencia': asistencia,
                'estado': asistencia.estado if asistencia else 'P',
                'observaciones': (asistencia.observaciones or '') if asistencia else '',
            })

        return estudiantes_con_asistencia

    @staticmethod
    def calculate_class_attendance_stats(user, clase, days: int = 30) -> Dict:
        """
        Calcula estadísticas de asistencia de una clase en los últimos N días.

        Args:
            clase: Clase para calcular estadísticas
            days: Cantidad de días hacia atrás (default 30)

        Returns:
            Dict: Estadísticas de asistencia
        """
        from backend.apps.academico.models import Asistencia

        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=days)
        periodo_ancorado = False

        asistencias_mes = Asistencia.objects.filter(
            clase=clase,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        )

        if not asistencias_mes.exists():
            ultima_fecha = (
                Asistencia.objects.filter(clase=clase)
                .order_by('-fecha')
                .values_list('fecha', flat=True)
                .first()
            )
            if ultima_fecha:
                fecha_fin = ultima_fecha
                fecha_inicio = fecha_fin - timedelta(days=days)
                periodo_ancorado = True
                asistencias_mes = Asistencia.objects.filter(
                    clase=clase,
                    fecha__gte=fecha_inicio,
                    fecha__lte=fecha_fin,
                )

        total_registros = asistencias_mes.count()
        presentes = asistencias_mes.filter(estado='P').count()
        ausentes = asistencias_mes.filter(estado='A').count()
        tardanzas = asistencias_mes.filter(estado='T').count()
        justificadas = asistencias_mes.filter(estado='J').count()

        porcentaje = round((presentes / total_registros * 100), 1) if total_registros > 0 else 0

        return {
            'total_registros': total_registros,
            'presentes': presentes,
            'ausentes': ausentes,
            'tardanzas': tardanzas,
            'justificadas': justificadas,
            'porcentaje_asistencia': porcentaje,
            'periodo_desde': fecha_inicio,
            'periodo_hasta': fecha_fin,
            'periodo_ancorado': periodo_ancorado,
        }

    @staticmethod
    def get_student_attendance_stats(user, estudiante, clase, periodo_dias: int = 30) -> Dict:
        """
        Calcula estadísticas de asistencia de un estudiante en una clase.

        Args:
            estudiante: Estudiante
            clase: Clase
            periodo_dias: Período en días para calcular estadísticas

        Returns:
            Dict: Estadísticas de asistencia del estudiante
        """
        from backend.apps.academico.models import Asistencia

        fecha_inicio = date.today() - timedelta(days=periodo_dias)

        asistencias = Asistencia.objects.filter(
            estudiante=estudiante,
            clase=clase,
            fecha__gte=fecha_inicio
        )

        total_clases = asistencias.count()
        presentes = asistencias.filter(estado='P').count()
        ausentes = asistencias.filter(estado='A').count()
        tardanzas = asistencias.filter(estado='T').count()
        justificadas = asistencias.filter(estado='J').count()

        porcentaje = round((presentes / total_clases * 100), 1) if total_clases > 0 else 0

        return {
            'total_clases': total_clases,
            'presentes': presentes,
            'ausentes': ausentes,
            'tardanzas': tardanzas,
            'justificadas': justificadas,
            'porcentaje_asistencia': porcentaje
        }

    @staticmethod
    def process_attendance_action(user, colegio, post_data: Dict) -> Dict:
        """
        Procesa una acción de asistencia (registrar, actualizar_observacion).

        Args:
            user: Usuario que realiza la acción
            colegio: Colegio
            post_data: Datos del POST request

        Returns:
            Dict: Resultado con 'success', 'message'
        """
        try:
            action = post_data.get('accion')
            
            if action == 'registrar_asistencia':
                from backend.apps.cursos.models import Clase
                clase_id = int(post_data.get('clase_id', 0))
                fecha_str = post_data.get('fecha', '').strip()
                
                if not clase_id or not fecha_str:
                    return {'success': False, 'message': 'Faltan datos para registrar asistencia.'}
                
                clase = Clase.objects.select_related('curso', 'profesor').get(
                    id=clase_id, colegio=colegio, activo=True
                )
                
                # Validar permisos
                is_valid, error_msg = CommonValidations.validate_class_ownership(user, clase)
                if not is_valid:
                    return {'success': False, 'message': error_msg}
                
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                
                # Extraer estados de asistencia del POST
                estudiantes_estados = {}
                for key in post_data.keys():
                    if key.startswith('asistencia_'):
                        estudiante_id = int(key.replace('asistencia_', ''))
                        estado = post_data.get(key, '').strip()
                        if estado:
                            estudiantes_estados[estudiante_id] = estado
                
                count = AttendanceService.register_attendance_for_class(
                    user, colegio, clase, fecha, estudiantes_estados
                )
                return {
                    'success': True,
                    'message': f'Asistencia registrada para {fecha_str}.'
                }
                
            elif action == 'actualizar_observacion':
                asistencia_id = int(post_data.get('asistencia_id', 0))
                observaciones = post_data.get('observaciones', '').strip() or None
                
                if not asistencia_id:
                    return {'success': False, 'message': 'Asistencia inválida.'}
                
                # Validar permisos obteniendo la asistencia
                from backend.apps.academico.models import Asistencia
                asistencia = Asistencia.objects.select_related('clase').get(
                    id_asistencia=asistencia_id, colegio=colegio
                )

                is_valid, error_msg = CommonValidations.validate_class_ownership(user, asistencia.clase)
                if not is_valid:
                    return {'success': False, 'message': error_msg}
                
                success = AttendanceService.update_attendance_observation(
                    user, colegio, asistencia_id, observaciones
                )
                if success:
                    return {'success': True, 'message': 'Observación actualizada exitosamente.'}
                else:
                    return {'success': False, 'message': 'No se encontró la asistencia.'}
                    
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}
                    
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}

    @staticmethod
    def get_teacher_classes_data(user) -> Dict:
        """
        Obtiene datos completos de clases para un profesor.

        Args:
            user: Usuario profesor

        Returns:
            Dict: Datos de clases con filtros y estadísticas
        """
        from backend.apps.cursos.models import Clase
        from backend.apps.institucion.models import Colegio
        
        colegio = user.colegio
        clases = Clase.objects.filter(
            profesor=user,
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso')
        
        return {
            'clases': clases,
            'total_clases': clases.count(),
            'colegio': colegio
        }

    @staticmethod
    def get_student_attendance_summary(user, mes_filtro: int = None, anio_filtro: int = None) -> Dict:
        """
        Obtiene resumen de asistencia del estudiante.

        Args:
            user: Usuario estudiante
            mes_filtro: Mes para filtrar (opcional)
            anio_filtro: Año para filtrar (opcional)

        Returns:
            Dict: Resumen de asistencia
        """
        from backend.apps.academico.models import Asistencia
        from datetime import date
        
        if mes_filtro is None:
            mes_filtro = date.today().month
        if anio_filtro is None:
            anio_filtro = date.today().year
        
        try:
            # Obtener asistencias (sin slice inicial para permitir filtros)
            asistencias_base = Asistencia.objects.filter(
                estudiante=user
            )
            
            total = asistencias_base.count()
            presentes = asistencias_base.filter(estado='P').count()
            ausentes = asistencias_base.filter(estado='A').count()
            tardanzas = asistencias_base.filter(estado='T').count()
            justificadas = asistencias_base.filter(estado='J').count()
            
            porcentaje = round((presentes / total * 100), 1) if total > 0 else 0
            
            # Obtener registros recientes DESPUÉS de los filtros
            asistencias_recientes = asistencias_base.order_by('-fecha')[:10]
            
            return {
                'total_registros': total,
                'presentes': presentes,
                'ausentes': ausentes,
                'tardanzas': tardanzas,
                'justificadas': justificadas,
                'porcentaje_asistencia': porcentaje,
                'asistencias_recientes': [
                    {
                        'fecha': a.fecha,
                        'estado': a.get_estado_display(),
                        'clase': a.clase.asignatura.nombre
                    } for a in asistencias_recientes
                ],
                'mes_filtro': mes_filtro
            }
            
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_teacher_classes_with_stats(user) -> Dict:
        """
        Obtiene clases del profesor con estadísticas básicas.

        Args:
            user: Usuario profesor

        Returns:
            Dict: Clases con estadísticas
        """
        try:
            from backend.apps.cursos.models import Clase
            from backend.apps.academico.models import Asistencia
            from datetime import datetime
            
            clases = Clase.objects.filter(
                colegio=user.colegio,
                profesor=user,
                activo=True
            ).select_related('curso', 'asignatura').order_by('curso__nombre', 'asignatura__nombre')
            
            # Construir datos de clases con estadísticas
            clases_data = []
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            for clase in clases:
                # Estadísticas de estudiantes
                total_estudiantes = clase.curso.perfil_estudiante_set.filter(
                    estado_academico='Activo'
                ).count()
                
                # Estadísticas de asistencia del mes actual
                asistencias_mes = Asistencia.objects.filter(
                    clase=clase,
                    fecha__year=current_year,
                    fecha__month=current_month
                )
                
                total_asistencias = asistencias_mes.count()
                presentes = asistencias_mes.filter(estado='P').count()
                ausentes = asistencias_mes.filter(estado='A').count()
                
                clases_data.append({
                    'id': clase.id,
                    'curso': clase.curso.nombre,
                    'asignatura': clase.asignatura.nombre,
                    'color': clase.asignatura.color,
                    'total_estudiantes': total_estudiantes,
                    'asistencias_mes': {
                        'total': total_asistencias,
                        'presentes': presentes,
                        'ausentes': ausentes,
                        'porcentaje_asistencia': (presentes / total_asistencias * 100) if total_asistencias > 0 else 0
                    }
                })
            
            return {
                'clases': clases_data,
                'total_clases': len(clases_data)
            }
            
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_class_for_user(user, clase_id: int) -> Optional[Any]:
        """
        Obtiene clase validando que pertenezca al colegio del usuario y esté activa.
        """
        from backend.apps.cursos.models import Clase
        try:
            return Clase.objects.get(id=clase_id, colegio=user.colegio, activo=True)
        except Clase.DoesNotExist:
            return None

    @staticmethod
    def prepare_attendance_data_from_post(user, post_data: Dict, perfiles) -> Dict[int, Dict]:
        """
        Prepara datos de asistencia desde POST data.
        """
        attendance_data = {}
        for perfil in perfiles:
            estudiante_id = perfil.user.id
            estado = post_data.get(f'estado_{estudiante_id}')
            observaciones = post_data.get(f'obs_{estudiante_id}', '')
            
            if estado:
                attendance_data[estudiante_id] = {
                    'estado': estado,
                    'observaciones': observaciones
                }
        return attendance_data

    @staticmethod
    def get_student_profile_and_course(user):
        """
        Obtiene perfil de estudiante y curso actual.
        """
        try:
            perfil = user.perfil_estudiante
            curso_actual = perfil.curso_actual
            return perfil, curso_actual
        except Exception:
            return None, None
    @staticmethod
    def get_active_students(user, curso):
        """
        Obtiene estudiantes activos de un curso.
        """
        from backend.apps.matriculas.models import Matricula
        return Matricula.objects.filter(
            curso=curso,
            estado='Activo'
        ).select_related('estudiante__user')

    @staticmethod
    def parse_date_from_string(fecha_str: str) -> date:
        """
        Parsea una fecha desde string.
        """
        from datetime import datetime
        return datetime.strptime(fecha_str, '%Y-%m-%d').date()

    @staticmethod
    def get_attendance_report(user, clase, mes: int, anio: int) -> Dict:
        """Reporte de asistencia por clase en un mes/año (totales + detalle por estudiante)."""
        from backend.apps.academico.models import Asistencia
        from backend.apps.cursos.models import ClaseEstudiante

        is_valid, _ = CommonValidations.validate_class_ownership(user, clase)
        if not is_valid:
            empty_stats = {
                'porcentaje': 0,
                'presentes': 0,
                'tardanzas': 0,
                'ausentes': 0,
                'justificadas': 0,
                'total_registros': 0,
                'dias_con_registro': 0,
            }
            return {'estudiantes_stats': [], 'stats_generales': empty_stats}

        asistencias_mes = Asistencia.objects.filter(
            clase=clase,
            fecha__month=mes,
            fecha__year=anio,
        )
        total_registros = asistencias_mes.count()
        presentes_g = asistencias_mes.filter(estado='P').count()
        ausentes_g = asistencias_mes.filter(estado='A').count()
        tardanzas_g = asistencias_mes.filter(estado='T').count()
        justificadas_g = asistencias_mes.filter(estado='J').count()
        dias_con_registro = asistencias_mes.values('fecha').distinct().count()
        porcentaje_g = (
            round((presentes_g / total_registros) * 100, 1) if total_registros > 0 else 0
        )

        estudiantes_stats = []
        inscripciones = ClaseEstudiante._base_manager.filter(
            clase=clase,
            activo=True,
        ).select_related('estudiante').order_by(
            'estudiante__apellido_paterno',
            'estudiante__apellido_materno',
            'estudiante__nombre',
        )

        for rel in inscripciones:
            estudiante = rel.estudiante
            if not estudiante.is_active:
                continue
            qs = asistencias_mes.filter(estudiante=estudiante)
            total = qs.count()
            presentes = qs.filter(estado='P').count()
            ausentes = qs.filter(estado='A').count()
            tardanzas = qs.filter(estado='T').count()
            justificadas = qs.filter(estado='J').count()
            porcentaje = round((presentes / total) * 100, 1) if total > 0 else 0
            estudiantes_stats.append({
                'estudiante': estudiante,
                'total': total,
                'presentes': presentes,
                'ausentes': ausentes,
                'tardanzas': tardanzas,
                'justificadas': justificadas,
                'porcentaje': porcentaje,
            })

        return {
            'estudiantes_stats': estudiantes_stats,
            'stats_generales': {
                'porcentaje': porcentaje_g,
                'presentes': presentes_g,
                'tardanzas': tardanzas_g,
                'ausentes': ausentes_g,
                'justificadas': justificadas_g,
                'total_registros': total_registros,
                'dias_con_registro': dias_con_registro,
            },
        }

    @staticmethod
    def get_months_list():
        """
        Lista de meses para filtros.
        """
        return [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ]

    @staticmethod
    def get_years_list():
        """
        Lista de años para filtros.
        """
        from datetime import date
        current_year = date.today().year
        return list(range(current_year - 2, current_year + 3))

    @staticmethod
    def get_month_name(mes: int) -> str:
        """
        Obtiene nombre del mes.
        """
        months = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        return months.get(mes, '')

    @staticmethod
    def get_student_attendance_for_month(user, perfil, mes: int, anio: int):
        """
        Obtiene asistencia de estudiante para un mes específico.
        """
        # Implementation would go here
        return []

    @staticmethod
    def get_student_attendance_by_subject(user, perfil, mes: int, anio: int):
        """
        Obtiene estadísticas de asistencia por asignatura.
        """
        # Implementation would go here
        return []
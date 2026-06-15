"""
Servicio de gestión de profesores y asignación de clases.
Asegura integridad relacional al desactivar profesores.
"""
import logging
from typing import Dict, List, Any
from django.db.models import Q

from backend.apps.accounts.models import Role, User
from backend.apps.cursos.models import Clase
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException

logger = logging.getLogger('cursos')


class ProfesorService:
    """Service para gestión segura de profesores"""

    @staticmethod
    def validations(data: Dict[str, Any], *, profesor_id: int | None = None) -> None:
        required = ['email', 'nombre', 'apellido_paterno']
        for field in required:
            if not str(data.get(field, '')).strip():
                raise ValueError(f'Campo requerido: {field}')

        email = str(data['email']).strip().lower()
        query = User.objects.filter(email=email)
        if profesor_id is not None:
            query = query.exclude(id=profesor_id)
        if query.exists():
            raise ValueError('Ya existe un usuario con ese email')

    @staticmethod
    def create(data: Dict[str, Any]) -> User:
        ProfesorService.validations(data)
        if data.get('rbd_colegio'):
            IntegrityService.validate_profesor_creation(data['rbd_colegio'])
        role, _ = Role.objects.get_or_create(nombre='Profesor')
        profesor = User.objects.create_user(
            email=str(data['email']).strip().lower(),
            password=data.get('password'),
            nombre=str(data['nombre']).strip(),
            apellido_paterno=str(data['apellido_paterno']).strip(),
            apellido_materno=(str(data.get('apellido_materno') or '').strip() or None),
            rut=(str(data.get('rut') or '').strip() or None),
            role=role,
            rbd_colegio=data.get('rbd_colegio'),
            is_active=bool(data.get('is_active', True)),
        )
        return profesor

    @staticmethod
    def update(profesor_id: int, data: Dict[str, Any]) -> User:
        profesor = ProfesorService.get(profesor_id)
        payload = {
            'email': data.get('email', profesor.email),
            'nombre': data.get('nombre', profesor.nombre),
            'apellido_paterno': data.get('apellido_paterno', profesor.apellido_paterno),
            'apellido_materno': data.get('apellido_materno', profesor.apellido_materno),
            'rut': data.get('rut', profesor.rut),
            'rbd_colegio': data.get('rbd_colegio', profesor.rbd_colegio),
            'is_active': data.get('is_active', profesor.is_active),
        }
        ProfesorService.validations(payload, profesor_id=profesor_id)

        if payload.get('rbd_colegio'):
            IntegrityService.validate_profesor_update(payload['rbd_colegio'])

        profesor.email = str(payload['email']).strip().lower()
        profesor.nombre = str(payload['nombre']).strip()
        profesor.apellido_paterno = str(payload['apellido_paterno']).strip()
        profesor.apellido_materno = (str(payload.get('apellido_materno') or '').strip() or None)
        profesor.rut = (str(payload.get('rut') or '').strip() or None)
        profesor.rbd_colegio = payload.get('rbd_colegio')
        profesor.is_active = bool(payload.get('is_active', True))
        profesor.save()
        return profesor

    @staticmethod
    def delete(profesor_id: int) -> Dict:
        return ProfesorService.deactivate_profesor_safely(profesor_id)

    @staticmethod
    def get(profesor_id: int) -> User:
        return User.objects.get(
            id=profesor_id,
            perfil_profesor__isnull=False,
        )

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        """Punto de entrada estándar del servicio (fase 3.1)."""
        ProfesorService.validate(operation, params)
        return ProfesorService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        """Valida parámetros mínimos por operación."""
        if operation in [
            'validate_can_deactivate_profesor',
            'deactivate_profesor_safely',
            'validate_profesor_active_for_clase',
            'get_profesor_clases_summary',
        ] and params.get('profesor_id') is None:
            raise ValueError('Parámetro requerido: profesor_id')

        if operation == 'validate_clase_has_active_profesor' and params.get('clase_id') is None:
            raise ValueError('Parámetro requerido: clase_id')

        if operation not in [
            'validate_can_deactivate_profesor',
            'deactivate_profesor_safely',
            'validate_profesor_active_for_clase',
            'get_profesor_clases_summary',
            'validate_clase_has_active_profesor',
        ]:
            raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        """Despacha operaciones a implementaciones privadas."""
        if operation == 'validate_can_deactivate_profesor':
            return ProfesorService._execute_validate_can_deactivate_profesor(params)
        if operation == 'deactivate_profesor_safely':
            return ProfesorService._execute_deactivate_profesor_safely(params)
        if operation == 'validate_profesor_active_for_clase':
            return ProfesorService._execute_validate_profesor_active_for_clase(params)
        if operation == 'get_profesor_clases_summary':
            return ProfesorService._execute_get_profesor_clases_summary(params)
        if operation == 'validate_clase_has_active_profesor':
            return ProfesorService._execute_validate_clase_has_active_profesor(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity_for_profesor(profesor: User, action: str) -> None:
        if profesor.rbd_colegio:
            if action in {'VALIDATE_CAN_DEACTIVATE_PROFESOR', 'DEACTIVATE_PROFESOR_SAFELY'}:
                IntegrityService.validate_profesor_deletion(profesor.rbd_colegio)
                return

            IntegrityService.validate_school_integrity_or_raise(
                school_id=profesor.rbd_colegio,
                action=action,
            )

    @staticmethod
    def validate_can_deactivate_profesor(profesor_id: int) -> None:
        return ProfesorService.execute('validate_can_deactivate_profesor', {
            'profesor_id': profesor_id,
        })

    @staticmethod
    def _execute_validate_can_deactivate_profesor(params: Dict[str, Any]) -> None:
        """
        Valida que un profesor pueda ser desactivado.
        
        Args:
            profesor_id: ID del profesor (User) a desactivar
            
        Raises:
            PrerequisiteException: Si el profesor tiene clases activas asignadas
        """
        profesor_id = params['profesor_id']

        try:
            profesor = User.objects.get(id=profesor_id)
        except User.DoesNotExist:
            raise PrerequisiteException(
                error_type='NOT_FOUND',
                context={'profesor_id': profesor_id, 'message': f'El profesor con ID {profesor_id} no existe.'}
            )

        ProfesorService._validate_school_integrity_for_profesor(
            profesor,
            action='VALIDATE_CAN_DEACTIVATE_PROFESOR'
        )
        
        # Contar clases activas asignadas a este profesor
        clases_activas = Clase.objects.filter(
            profesor=profesor,
            activo=True
        ).count()
        
        if clases_activas > 0:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Profesor',
                    'related_entity': 'Clase',
                    'profesor_id': profesor_id,
                    'profesor_nombre': profesor.get_full_name(),
                    'clases_activas': clases_activas,
                    'message': f'El profesor {profesor.get_full_name()} tiene {clases_activas} clase(s) activa(s) asignada(s).',
                    'action': 'Desactive o reasigne las clases antes de desactivar al profesor.'
                }
            )
        
        logger.info(f"Profesor {profesor.get_full_name()} (ID: {profesor_id}) puede ser desactivado")

    @staticmethod
    def deactivate_profesor_safely(profesor_id: int) -> Dict:
        return ProfesorService.execute('deactivate_profesor_safely', {
            'profesor_id': profesor_id,
        })

    @staticmethod
    def _execute_deactivate_profesor_safely(params: Dict[str, Any]) -> Dict:
        """
        Desactiva un profesor de forma segura.
        - Valida que no tenga clases activas
        - Desvincula de clases inactivas (SET NULL)
        - Desactiva al profesor
        
        Args:
            profesor_id: ID del profesor
            
        Returns:
            Dict con resultado de la operación
            
        Raises:
            PrerequisiteException: Si el profesor tiene clases activas
        """
        profesor_id = params['profesor_id']

        # Validar prerequisitos
        ProfesorService.validate_can_deactivate_profesor(profesor_id)
        
        profesor = User.objects.get(id=profesor_id)
        
        # Contar clases inactivas que quedarán sin profesor
        clases_inactivas = Clase.objects.filter(
            profesor=profesor,
            activo=False
        ).count()
        
        # Desvincular de clases inactivas (SET NULL se aplica automáticamente)
        # Solo para logging
        if clases_inactivas > 0:
            logger.info(f"Desvinculando profesor {profesor.get_full_name()} de {clases_inactivas} clases inactivas")
            Clase.objects.filter(profesor=profesor, activo=False).update(profesor=None)
        
        # Desactivar profesor
        profesor.is_active = False
        profesor.save()
        
        logger.warning(f"Profesor {profesor.get_full_name()} (ID: {profesor_id}) desactivado exitosamente")
        
        return {
            'success': True,
            'profesor_id': profesor_id,
            'profesor_nombre': profesor.get_full_name(),
            'clases_inactivas_desvinculadas': clases_inactivas,
            'message': f'Profesor desactivado exitosamente. {clases_inactivas} clase(s) inactiva(s) desvinculadas.'
        }

    @staticmethod
    def validate_profesor_active_for_clase(profesor_id: int) -> None:
        return ProfesorService.execute('validate_profesor_active_for_clase', {
            'profesor_id': profesor_id,
        })

    @staticmethod
    def _execute_validate_profesor_active_for_clase(params: Dict[str, Any]) -> None:
        """
        Valida que un profesor esté activo antes de asignarlo a una clase.
        
        Args:
            profesor_id: ID del profesor
            
        Raises:
            PrerequisiteException: Si el profesor no está activo
        """
        profesor_id = params['profesor_id']

        try:
            profesor = User.objects.get(id=profesor_id)
        except User.DoesNotExist:
            raise PrerequisiteException(
                error_type='NOT_FOUND',
                context={'profesor_id': profesor_id, 'message': f'El profesor con ID {profesor_id} no existe.'}
            )

        ProfesorService._validate_school_integrity_for_profesor(
            profesor,
            action='VALIDATE_PROFESOR_ACTIVE_FOR_CLASE'
        )
        
        if not profesor.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Profesor',
                    'field': 'is_active',
                    'profesor_id': profesor_id,
                    'profesor_nombre': profesor.get_full_name(),
                    'message': f'El profesor {profesor.get_full_name()} no está activo.',
                    'action': 'Active al profesor antes de asignarlo a una clase.'
                }
            )

    @staticmethod
    def get_profesor_clases_summary(profesor_id: int) -> Dict:
        return ProfesorService.execute('get_profesor_clases_summary', {
            'profesor_id': profesor_id,
        })

    @staticmethod
    def _execute_get_profesor_clases_summary(params: Dict[str, Any]) -> Dict:
        """
        Obtiene resumen de clases asignadas a un profesor.
        
        Args:
            profesor_id: ID del profesor
            
        Returns:
            Dict con estadísticas de clases
        """
        profesor_id = params['profesor_id']

        try:
            profesor = User.objects.get(id=profesor_id)
        except User.DoesNotExist:
            return {
                'exists': False,
                'profesor_id': profesor_id
            }
        
        total_clases = Clase.objects.filter(profesor=profesor).count()
        clases_activas = Clase.objects.filter(profesor=profesor, activo=True).count()
        clases_inactivas = total_clases - clases_activas
        
        return {
            'exists': True,
            'profesor_id': profesor_id,
            'profesor_nombre': profesor.get_full_name(),
            'profesor_activo': profesor.is_active,
            'total_clases': total_clases,
            'clases_activas': clases_activas,
            'clases_inactivas': clases_inactivas,
            'can_deactivate': clases_activas == 0
        }

    @staticmethod
    def validate_clase_has_active_profesor(clase_id: int) -> None:
        return ProfesorService.execute('validate_clase_has_active_profesor', {
            'clase_id': clase_id,
        })

    @staticmethod
    def _execute_validate_clase_has_active_profesor(params: Dict[str, Any]) -> None:
        """
        Valida que una clase tenga un profesor activo asignado.
        
        Args:
            clase_id: ID de la clase
            
        Raises:
            PrerequisiteException: Si la clase no tiene profesor o el profesor no está activo
        """
        clase_id = params['clase_id']

        try:
            clase = Clase.objects.get(id=clase_id)
        except Clase.DoesNotExist:
            raise PrerequisiteException(
                error_type='NOT_FOUND',
                context={'clase_id': clase_id, 'message': f'La clase con ID {clase_id} no existe.'}
            )

        IntegrityService.validate_school_integrity_or_raise(
            school_id=clase.colegio.rbd,
            action='VALIDATE_CLASE_HAS_ACTIVE_PROFESOR',
        )
        
        if not clase.profesor:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Clase',
                    'field': 'profesor',
                    'clase_id': clase_id,
                    'message': f'La clase {clase} no tiene profesor asignado.',
                    'action': 'Asigne un profesor antes de activar la clase.'
                }
            )
        
        if not clase.profesor.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Clase',
                    'field': 'profesor.is_active',
                    'clase_id': clase_id,
                    'profesor_id': clase.profesor.id,
                    'profesor_nombre': clase.profesor.get_full_name(),
                    'message': f'El profesor {clase.profesor.get_full_name()} de la clase {clase} no está activo.',
                    'action': 'Active al profesor o reasigne la clase.'
                }
            )

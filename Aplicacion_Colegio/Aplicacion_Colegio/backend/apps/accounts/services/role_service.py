"""
Servicio de gestión de roles y permisos.
Asegura integridad relacional de roles.
"""
import logging
from typing import Dict, Any

from backend.apps.accounts.models import Role, User
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException

logger = logging.getLogger('accounts')


class RoleService:
    """Service para gestión segura de roles"""

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        """Punto de entrada estándar del servicio (fase 3.1)."""
        RoleService.validate(operation, params)
        return RoleService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        """Valida parámetros mínimos por operación."""
        if operation in ['validate_can_delete_role', 'get_role_usage_stats'] and params.get('role_id') is None:
            raise ValueError('Parámetro requerido: role_id')

        if operation not in ['validate_can_delete_role', 'get_role_usage_stats', 'assign_default_role_to_users_without_role']:
            raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        """Despacha operaciones a implementaciones privadas."""
        if operation == 'validate_can_delete_role':
            return RoleService._execute_validate_can_delete_role(params)
        if operation == 'get_role_usage_stats':
            return RoleService._execute_get_role_usage_stats(params)
        if operation == 'assign_default_role_to_users_without_role':
            return RoleService._execute_assign_default_role_to_users_without_role(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_integrity_for_role_scope(role):
        school_ids = (
            User.objects.filter(role=role, rbd_colegio__isnull=False)
            .values_list('rbd_colegio', flat=True)
            .distinct()
        )
        try:
            iter(school_ids)
        except TypeError:
            logger.debug('No se pudo iterar school_ids para validar integridad de rol')
            return
        for school_id in school_ids:
            IntegrityService.validate_school_integrity_or_raise(
                school_id=school_id,
                action='ROLE_SERVICE_OPERATION',
            )

    @staticmethod
    def _should_validate_role_integrity(role) -> bool:
        role_id = getattr(role, 'id', None)
        return isinstance(role_id, int)

    @staticmethod
    def validate_can_delete_role(role_id: int) -> None:
        return RoleService.execute('validate_can_delete_role', {
            'role_id': role_id,
        })

    @staticmethod
    def _execute_validate_can_delete_role(params: Dict[str, Any]) -> None:
        """
        Valida que un rol pueda ser eliminado sin romper integridad.
        
        Args:
            role_id: ID del rol a validar
            
        Raises:
            PrerequisiteException: Si el rol tiene usuarios activos asignados
        """
        role_id = params['role_id']

        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            raise PrerequisiteException(
                error_type='NOT_FOUND',
                context={'role_id': role_id, 'message': f'El rol con ID {role_id} no existe.'}
            )
        if RoleService._should_validate_role_integrity(role):
            RoleService._validate_integrity_for_role_scope(role)
        
        # Contar usuarios activos con este rol
        users_with_role = User.objects.filter(
            role=role, 
            is_active=True
        ).count()
        
        if users_with_role > 0:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Role',
                    'related_entity': 'User',
                    'role_id': role_id,
                    'role_name': role.nombre,
                    'users_count': users_with_role,
                    'message': f'El rol "{role.nombre}" tiene {users_with_role} usuario(s) activo(s) asignado(s).',
                    'action': 'Reasigne los usuarios a otro rol antes de eliminar este rol.'
                }
            )
        
        logger.info(f"Rol {role.nombre} (ID: {role_id}) puede ser eliminado de forma segura")

    @staticmethod
    def get_role_usage_stats(role_id: int) -> Dict:
        return RoleService.execute('get_role_usage_stats', {
            'role_id': role_id,
        })

    @staticmethod
    def _execute_get_role_usage_stats(params: Dict[str, Any]) -> Dict:
        """
        Obtiene estadísticas de uso de un rol.
        
        Args:
            role_id: ID del rol
            
        Returns:
            Dict con estadísticas de uso
        """
        role_id = params['role_id']

        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return {
                'exists': False,
                'role_id': role_id
            }
        if RoleService._should_validate_role_integrity(role):
            RoleService._validate_integrity_for_role_scope(role)
        
        total_users = User.objects.filter(role=role).count()
        active_users = User.objects.filter(role=role, is_active=True).count()
        inactive_users = total_users - active_users
        
        return {
            'exists': True,
            'role_id': role_id,
            'role_name': role.nombre,
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'can_delete': active_users == 0
        }

    @staticmethod
    def assign_default_role_to_users_without_role() -> int:
        return RoleService.execute('assign_default_role_to_users_without_role', {})

    @staticmethod
    def _execute_assign_default_role_to_users_without_role(params: Dict[str, Any]) -> int:
        """
        Asigna rol por defecto a usuarios que no tienen rol asignado.
        Útil para migración de datos.
        
        Returns:
            int: Cantidad de usuarios actualizados
        """
        school_ids = (
            User.objects.filter(role__isnull=True, rbd_colegio__isnull=False)
            .values_list('rbd_colegio', flat=True)
            .distinct()
        )
        for school_id in school_ids:
            IntegrityService.validate_school_integrity_or_raise(
                school_id=school_id,
                action='ASSIGN_DEFAULT_ROLE_TO_USERS_WITHOUT_ROLE',
            )

        # Buscar o crear rol "Usuario" por defecto
        default_role, created = Role.objects.get_or_create(nombre='Usuario')
        
        if created:
            logger.info(f"Rol por defecto 'Usuario' creado")
        
        # Actualizar usuarios sin rol
        users_without_role = User.objects.filter(role__isnull=True)
        count = users_without_role.count()
        
        if count > 0:
            users_without_role.update(role=default_role)
            logger.warning(f"Se asignó rol por defecto a {count} usuarios sin rol")
        
        return count

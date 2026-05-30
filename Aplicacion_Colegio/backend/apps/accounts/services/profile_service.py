"""
ProfileService - Servicio para gestión de perfiles de usuario

Este servicio centraliza la lógica de negocio para:
- Actualización de perfiles (estudiantes, profesores, administradores)
- Cambio de contraseñas con validaciones de seguridad
- Validación de roles y permisos

Migrando desde: sistema_antiguo/core/views.py (líneas 905-1128)
"""

import logging
from typing import Dict, Optional, Tuple, Any
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.hashers import check_password

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('accounts')
security_logger = logging.getLogger('accounts')


class ProfileService:
    """
    Servicio para gestión de perfiles de usuario
    """

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        ProfileService.validate(operation, params)
        return ProfileService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(ProfileService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')
    
    # Roles permitidos para cada tipo de operación
    ALLOWED_STUDENT_ROLES = ['Alumno']
    ALLOWED_STAFF_ROLES = ['Profesor', 'Administrador general', 'Administrador escolar']
    
    # Configuración de seguridad
    MIN_PASSWORD_LENGTH = 6
    MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024
    ALLOWED_PHOTO_CONTENT_TYPES = {
        'image/jpeg',
        'image/png',
        'image/webp',
    }
    
    @staticmethod
    def validate_role_for_student_operations(user) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario sea un estudiante

        Args:
            user: Usuario de Django

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        return CommonValidations.validate_student_permissions(user)

    @staticmethod
    def validate_role_for_staff_operations(user) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario sea profesor o administrador

        Args:
            user: Usuario de Django

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        return CommonValidations.validate_staff_permissions(user)
    
    @staticmethod
    def validate_email_format(email: str) -> Optional[Dict[str, Any]]:
        """
        Valida el formato de un email
        
        Args:
            email: Email a validar
            
        Returns:
            Optional[Dict]: None si válido, Dict con error si inválido
        """
        try:
            validate_email(email)
            return None
        except ValidationError:
            return ErrorResponseBuilder.build('VALIDATION_ERROR', context={
                'field': 'email',
                'value': email,
                'message': 'Email no válido'
            })
    
    @staticmethod
    def check_email_availability(email: str, user, User) -> Optional[Dict[str, Any]]:
        """
        Verifica que el email no esté en uso por otro usuario en el mismo colegio
        
        Args:
            email: Email a verificar
            user: Usuario actual
            User: Modelo User de Django
            
        Returns:
            Optional[Dict]: None si disponible, Dict con error si no disponible
        """
        if User.objects.filter(
            email=email, 
            rbd_colegio=user.rbd_colegio
        ).exclude(id=user.id).exists():
            return ErrorResponseBuilder.build('VALIDATION_ERROR', context={
                'field': 'email',
                'value': email,
                'message': 'El email ya está en uso por otro usuario'
            })
        return None

    @staticmethod
    def _validate_school_integrity_from_user(user, action: str) -> None:
        if getattr(user, 'rbd_colegio', None):
            IntegrityService.validate_school_integrity_or_raise(
                school_id=user.rbd_colegio,
                action=action,
            )

    @staticmethod
    def _get_student_profile(user):
        from backend.apps.accounts.models import PerfilEstudiante

        return PerfilEstudiante.objects.filter(user=user).first()

    @staticmethod
    def update_own_student_profile(user, data: Dict[str, Any], User=None) -> Tuple[bool, str]:
        """El estudiante actualiza su propio perfil (contacto y emergencia)."""
        ProfileService._validate_school_integrity_from_user(user, 'UPDATE_OWN_STUDENT_PROFILE')
        is_valid, error_msg = ProfileService.validate_role_for_student_operations(user)
        if not is_valid:
            return False, error_msg or 'Rol inválido'

        perfil = ProfileService._get_student_profile(user)
        if not perfil:
            return False, 'No se encontró tu perfil de estudiante'

        email = (data.get('email') or '').strip()
        if not email:
            return False, 'El email es obligatorio'

        error = ProfileService.validate_email_format(email)
        if error:
            return False, error['context']['message']

        if User:
            error = ProfileService.check_email_availability(email, user, User)
            if error:
                return False, error['context']['message']

        try:
            user.email = email
            user.save(update_fields=['email'])

            perfil.telefono = (data.get('telefono') or '').strip() or None
            perfil.telefono_movil = (data.get('telefono_movil') or '').strip() or None
            perfil.direccion = (data.get('direccion') or '').strip() or None
            perfil.contacto_emergencia_nombre = (
                (data.get('contacto_emergencia_nombre') or '').strip() or None
            )
            perfil.contacto_emergencia_relacion = (
                (data.get('contacto_emergencia_relacion') or '').strip() or None
            )
            perfil.contacto_emergencia_telefono = (
                (data.get('contacto_emergencia_telefono') or '').strip() or None
            )
            perfil.save()

            logger.info('Perfil propio actualizado - Usuario: %s', user.email)
            return True, 'Perfil actualizado correctamente'
        except Exception as exc:
            logger.error('Error actualizando perfil propio: %s', exc)
            return False, f'Error al actualizar perfil: {exc}'

    @staticmethod
    def upload_student_photo(user, image_file) -> Tuple[bool, str]:
        """Sube o reemplaza la foto de perfil del estudiante."""
        ProfileService._validate_school_integrity_from_user(user, 'UPLOAD_STUDENT_PHOTO')
        is_valid, error_msg = ProfileService.validate_role_for_student_operations(user)
        if not is_valid:
            return False, error_msg or 'Rol inválido'

        if not image_file:
            return False, 'Selecciona una imagen'

        content_type = getattr(image_file, 'content_type', '') or ''
        if content_type not in ProfileService.ALLOWED_PHOTO_CONTENT_TYPES:
            return False, 'Formato no permitido. Usa JPG, PNG o WebP'

        if image_file.size > ProfileService.MAX_PHOTO_SIZE_BYTES:
            return False, 'La imagen no puede superar 5 MB'

        perfil = ProfileService._get_student_profile(user)
        if not perfil:
            return False, 'No se encontró tu perfil de estudiante'

        try:
            if perfil.foto_perfil:
                perfil.foto_perfil.delete(save=False)
            perfil.foto_perfil = image_file
            perfil.save()
            logger.info('Foto de perfil actualizada - Usuario: %s', user.email)
            return True, 'Foto de perfil actualizada'
        except Exception as exc:
            logger.error('Error subiendo foto de perfil: %s', exc)
            return False, f'No se pudo guardar la foto: {exc}'

    @staticmethod
    def remove_student_photo(user) -> Tuple[bool, str]:
        """Elimina la foto de perfil del estudiante."""
        ProfileService._validate_school_integrity_from_user(user, 'REMOVE_STUDENT_PHOTO')
        perfil = ProfileService._get_student_profile(user)
        if not perfil or not perfil.foto_perfil:
            return False, 'No tienes foto de perfil para eliminar'
        try:
            perfil.foto_perfil.delete(save=True)
            return True, 'Foto de perfil eliminada'
        except Exception as exc:
            return False, f'Error al eliminar la foto: {exc}'

    @staticmethod
    def change_own_student_password(
        user,
        password_actual: str,
        password_nueva: str,
        password_confirmar: str,
        client_ip: str,
    ) -> Tuple[bool, str]:
        """El estudiante cambia su propia contraseña (sin permiso administrativo)."""
        ProfileService._validate_school_integrity_from_user(user, 'CHANGE_OWN_STUDENT_PASSWORD')
        is_valid, error_msg = ProfileService.validate_role_for_student_operations(user)
        if not is_valid:
            security_logger.warning(
                'Cambio de contraseña no autorizado - Usuario: %s, IP: %s',
                user.email,
                client_ip,
            )
            return False, error_msg

        is_valid, error_msg = ProfileService.validate_password_change(
            user, password_actual, password_nueva, password_confirmar, client_ip,
        )
        if not is_valid:
            return False, error_msg

        try:
            user.set_password(password_nueva)
            user.save()
            security_logger.info(
                'Contraseña propia cambiada - Usuario: %s, IP: %s',
                user.email,
                client_ip,
            )
            return True, 'Contraseña cambiada correctamente'
        except Exception as exc:
            logger.error('Error cambiando contraseña propia: %s', exc)
            return False, f'Error al cambiar contraseña: {exc}'
    
    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_USERS')
    def update_student_profile(user, email: str, telefono: str = None, direccion: str = None, User=None) -> Tuple[bool, str]:
        """
        Actualiza el perfil de un estudiante
        
        Args:
            user: Usuario estudiante
            email: Nuevo email
            telefono: Nuevo teléfono (opcional, no implementado aún en modelo)
            direccion: Nueva dirección (opcional, no implementado aún en modelo)
            User: Modelo User de Django
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        ProfileService._validate_school_integrity_from_user(user, 'UPDATE_STUDENT_PROFILE')
        # Validar rol
        is_valid, error_msg = ProfileService.validate_role_for_student_operations(user)
        if not is_valid:
            return False, error_msg or 'Rol inválido'
        
        # Validar email
        error = ProfileService.validate_email_format(email)
        if error:
            return False, error['context']['message']
        
        # Verificar disponibilidad de email
        if User:
            error = ProfileService.check_email_availability(email, user, User)
            if error:
                return False, error['context']['message']
        
        try:
            # Actualizar email
            user.email = email
            user.save()
            
            # TODO: Actualizar telefono y direccion cuando se agreguen esos campos al modelo
            # Por ahora solo actualizamos el email
            
            logger.info(
                f"Perfil de estudiante actualizado - Usuario: {user.username}, Email: {email}"
            )
            
            return True, "✔ Perfil actualizado correctamente"
            
        except Exception as e:
            logger.error(
                f"Error al actualizar perfil de estudiante - Usuario: {user.username}, Error: {str(e)}"
            )
            return False, f"Error al actualizar perfil: {str(e)}"
    
    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_USERS')
    def update_staff_profile(user, email: str, telefono: str = None, direccion: str = None, User=None) -> Tuple[bool, str]:
        """
        Actualiza el perfil de un profesor o administrador
        
        Args:
            user: Usuario profesor/administrador
            email: Nuevo email
            telefono: Nuevo teléfono (opcional, no implementado aún en modelo)
            direccion: Nueva dirección (opcional, no implementado aún en modelo)
            User: Modelo User de Django
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        ProfileService._validate_school_integrity_from_user(user, 'UPDATE_STAFF_PROFILE')
        # Validar rol
        is_valid, error_msg = ProfileService.validate_role_for_staff_operations(user)
        if not is_valid:
            return False, error_msg or 'Rol inválido'
        
        # Validar email
        error = ProfileService.validate_email_format(email)
        if error:
            return False, error['context']['message']
        
        # Verificar disponibilidad de email
        if User:
            error = ProfileService.check_email_availability(email, user, User)
            if error:
                return False, error['context']['message']
        
        try:
            # Actualizar email
            user.email = email
            user.save()
            
            # TODO: Actualizar telefono y direccion cuando se agreguen esos campos al modelo
            # Por ahora solo actualizamos el email
            
            logger.info(
                f"Perfil de staff actualizado - Usuario: {user.username}, Rol: {user.role.nombre}, Email: {email}"
            )
            
            return True, "✔ Perfil actualizado correctamente"
            
        except Exception as e:
            logger.error(
                f"Error al actualizar perfil de staff - Usuario: {user.username}, Error: {str(e)}"
            )
            return False, f"Error al actualizar perfil: {str(e)}"
    
    @staticmethod
    def validate_password_change(
        user, 
        password_actual: str, 
        password_nueva: str, 
        password_confirmar: str,
        client_ip: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida los datos para cambio de contraseña
        
        Args:
            user: Usuario de Django
            password_actual: Contraseña actual
            password_nueva: Nueva contraseña
            password_confirmar: Confirmación de nueva contraseña
            client_ip: IP del cliente
            
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        # Validar que las contraseñas nuevas coincidan
        if password_nueva != password_confirmar:
            security_logger.warning(
                f"Intento de cambio de contraseña con passwords no coincidentes - "
                f"Usuario: {user.username}, IP: {client_ip}"
            )
            return False, "Las contraseñas nuevas no coinciden"
        
        # Validar longitud mínima
        if len(password_nueva) < ProfileService.MIN_PASSWORD_LENGTH:
            return False, f"La contraseña debe tener al menos {ProfileService.MIN_PASSWORD_LENGTH} caracteres"
        
        # Verificar contraseña actual
        if not user.check_password(password_actual):
            security_logger.warning(
                f"Intento de cambio de contraseña con password actual incorrecta - "
                f"Usuario: {user.username}, IP: {client_ip}"
            )
            return False, "La contraseña actual es incorrecta"
        
        return True, None
    
    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_USERS')
    def change_student_password(
        user, 
        password_actual: str, 
        password_nueva: str, 
        password_confirmar: str,
        client_ip: str
    ) -> Tuple[bool, str]:
        """
        Cambia la contraseña de un estudiante
        
        Args:
            user: Usuario estudiante
            password_actual: Contraseña actual
            password_nueva: Nueva contraseña
            password_confirmar: Confirmación de nueva contraseña
            client_ip: IP del cliente
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        ProfileService._validate_school_integrity_from_user(user, 'CHANGE_STUDENT_PASSWORD')

        # Validar rol
        is_valid, error_msg = ProfileService.validate_role_for_student_operations(user)
        if not is_valid:
            security_logger.warning(
                f"Intento de acceso no autorizado a cambio de contraseña - "
                f"Usuario: {user.username}, IP: {client_ip}"
            )
            return False, error_msg
        
        # Validar datos de cambio de contraseña
        is_valid, error_msg = ProfileService.validate_password_change(
            user, password_actual, password_nueva, password_confirmar, client_ip
        )
        if not is_valid:
            return False, error_msg
        
        try:
            # Actualizar contraseña
            user.set_password(password_nueva)
            user.save()
            
            # Log de cambio exitoso
            security_logger.info(
                f"Contraseña cambiada exitosamente - Usuario: {user.username} (Estudiante), IP: {client_ip}"
            )
            
            return True, "✔ Contraseña cambiada correctamente"
            
        except Exception as e:
            logger.error(
                f"Error al cambiar contraseña - Usuario: {user.username}, Error: {str(e)}"
            )
            return False, f"Error al cambiar contraseña: {str(e)}"
    
    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_USERS')
    def change_staff_password(
        user, 
        password_actual: str, 
        password_nueva: str, 
        password_confirmar: str,
        client_ip: str
    ) -> Tuple[bool, str]:
        """
        Cambia la contraseña de un profesor o administrador
        
        Args:
            user: Usuario profesor/administrador
            password_actual: Contraseña actual
            password_nueva: Nueva contraseña
            password_confirmar: Confirmación de nueva contraseña
            client_ip: IP del cliente
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        ProfileService._validate_school_integrity_from_user(user, 'CHANGE_STAFF_PASSWORD')

        # Validar rol
        is_valid, error_msg = ProfileService.validate_role_for_staff_operations(user)
        if not is_valid:
            security_logger.warning(
                f"Intento de acceso no autorizado a cambio de contraseña - "
                f"Usuario: {user.username}, IP: {client_ip}"
            )
            return False, error_msg
        
        # Validar datos de cambio de contraseña
        is_valid, error_msg = ProfileService.validate_password_change(
            user, password_actual, password_nueva, password_confirmar, client_ip
        )
        if not is_valid:
            return False, error_msg
        
        try:
            # Actualizar contraseña
            user.set_password(password_nueva)
            user.save()
            
            # Log de cambio exitoso
            security_logger.info(
                f"Contraseña cambiada exitosamente - Usuario: {user.username} ({user.role.nombre}), IP: {client_ip}"
            )
            
            return True, "✔ Contraseña cambiada correctamente"
            
        except Exception as e:
            logger.error(
                f"Error al cambiar contraseña - Usuario: {user.username}, Error: {str(e)}"
            )
            return False, f"Error al cambiar contraseña: {str(e)}"

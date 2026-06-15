"""
ApoderadoService - Servicio para gestiÃ³n CRUD de apoderados

Este servicio centraliza la lÃ³gica de negocio para:
- Crear nuevos apoderados con perfil completo
- Editar datos de apoderados existentes
- Desactivar apoderados (soft delete)
- Relacionar apoderados con estudiantes
- Resetear contraseÃ±as de apoderados
- Listar y filtrar apoderados
- Calcular estadÃ­sticas
"""

import logging
import secrets
import string
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from django.db.models import Count, Q

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('accounts')


class ApoderadoService:
    """
    Servicio para gestiÃ³n completa de apoderados (CRUD + relaciones)
    """
    
    # Roles permitidos para gestiÃ³n de apoderados
    ALLOWED_ROLES = ['Administrador general', 'Administrador escolar']
    
    # Contraseña temporal por defecto (se genera de forma segura)
    DEFAULT_TEMP_PASSWORD = None

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        """Punto de entrada estÃ¡ndar para comandos del servicio (fase 3.1)."""
        ApoderadoService.validate(operation, params)
        return ApoderadoService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        """Valida parÃ¡metros mÃ­nimos requeridos por operaciÃ³n."""
        user = params.get('user')
        if user is None:
            raise ValueError('ParÃ¡metro requerido: user')

        if operation in ['create_apoderado', 'update_apoderado'] and params.get('data') is None:
            raise ValueError('ParÃ¡metro requerido: data')

        if operation in ['update_apoderado', 'deactivate_apoderado', 'reset_password'] and params.get('apoderado_id') is None:
            raise ValueError('ParÃ¡metro requerido: apoderado_id')

        if params.get('escuela_rbd') is None:
            raise ValueError('ParÃ¡metro requerido: escuela_rbd')

        if operation not in ['create_apoderado', 'update_apoderado', 'deactivate_apoderado', 'reset_password']:
            raise ValueError(f'OperaciÃ³n no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        """Despacha operaciones de comando a implementaciones privadas."""
        if operation == 'create_apoderado':
            return ApoderadoService._execute_create_apoderado(params)
        if operation == 'update_apoderado':
            return ApoderadoService._execute_update_apoderado(params)
        if operation == 'deactivate_apoderado':
            return ApoderadoService._execute_deactivate_apoderado(params)
        if operation == 'reset_password':
            return ApoderadoService._execute_reset_password(params)
        raise ValueError(f'OperaciÃ³n no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(escuela_rbd: str, action: str) -> None:
        """Valida integridad del colegio antes de operaciones crÃ­ticas de apoderados."""
        IntegrityService.validate_school_integrity_or_raise(
            school_id=int(escuela_rbd),
            action=action,
        )
    
    @staticmethod
    def _validar_prerequisitos_colegio(rbd_colegio: int) -> Optional[dict]:
        """
        Valida que el colegio exista y tenga ciclo acadÃ©mico activo.
        
        Args:
            rbd_colegio: RBD del colegio a validar
            
        Returns:
            None si todo estÃ¡ correcto, dict con error si hay problemas.
        """
        from backend.apps.institucion.models import Colegio, CicloAcademico
        
        # Validar que existe el colegio
        try:
            colegio = Colegio.objects.get(rbd=rbd_colegio)
        except Colegio.DoesNotExist:
            return ErrorResponseBuilder.build(
                'SCHOOL_NOT_CONFIGURED',
                context={'rbd_colegio': rbd_colegio, 'message': f'El colegio con RBD {rbd_colegio} no existe en el sistema'}
            )
        
        # Validar que existe ciclo acadÃ©mico activo
        ciclo_activo = CicloAcademico.objects.filter(colegio=colegio, estado='ACTIVO').first()
        if not ciclo_activo:
            return ErrorResponseBuilder.build(
                'MISSING_CICLO_ACTIVO',
                context={'rbd_colegio': rbd_colegio, 'colegio_nombre': colegio.nombre, 'message': f'El colegio {colegio.nombre} no tiene un ciclo academico activo. Debe crear uno antes de gestionar apoderados.', 'action_url': '/admin/institucion/cicloacademico/add/'}
            )
        
        return None
    
    @staticmethod
    def validate_admin_permissions(user) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario tenga permisos de administrador

        Args:
            user: Usuario de Django

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        try:
            has_access = PermissionService.has_permission(user, 'ACADEMICO', 'MANAGE_STUDENTS')
        except Exception as exc:
            return False, str(exc)

        if not has_access:
            return False, 'Acceso denegado'

        return True, None
    
    @staticmethod
    def generate_temp_password(rut: Optional[str]) -> str:
        """
        Genera una contraseÃ±a temporal basada en el RUT o usa contraseÃ±a por defecto
        
        Args:
            rut: RUT del apoderado (puede incluir puntos y guiÃ³n)
            
        Returns:
            str: ContraseÃ±a temporal
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(14))
    
    @staticmethod
    def validate_unique_email(email: str, User, exclude_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Verifica que el email no estÃ© en uso
        
        Args:
            email: Email a validar
            User: Modelo User de Django
            exclude_id: ID de usuario a excluir (para ediciÃ³n)
            
        Returns:
            Tuple[bool, Optional[str]]: (es_unico, mensaje_error)
        """
        query = User.objects.filter(email=email)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        
        if query.exists():
            return False, "Ya existe un usuario con ese email"
        
        return True, None
    
    @staticmethod
    def validate_unique_rut(rut: str, User, exclude_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Verifica que el RUT no estÃ© en uso
        
        Args:
            rut: RUT a validar
            User: Modelo User de Django
            exclude_id: ID de usuario a excluir (para ediciÃ³n)
            
        Returns:
            Tuple[bool, Optional[str]]: (es_unico, mensaje_error)
        """
        if not rut:
            return True, None  # RUT es opcional
        
        query = User.objects.filter(rut=rut)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        
        if query.exists():
            return False, "Ya existe un usuario con ese RUT"
        
        return True, None
    
    @staticmethod
    def _parsear_booleano(valor: str) -> bool:
        """Convierte string a booleano."""
        if not valor:
            return False
        return valor.lower() in ('true', '1', 'si', 'sÃ­', 'yes', 't', 'on')

    @staticmethod
    def create_profile_for_user(user):
        """Crea perfil de apoderado para un usuario existente."""
        from backend.apps.accounts.models import Apoderado

        if hasattr(user, 'perfil_apoderado'):
            return user.perfil_apoderado

        return Apoderado.objects.create(user=user)

    @staticmethod
    def link_student(*, apoderado, estudiante, parentesco: str, tipo_apoderado: str = 'principal'):
        """Crea vínculo apoderado-estudiante."""
        from backend.apps.accounts.models import RelacionApoderadoEstudiante

        relacion, _ = RelacionApoderadoEstudiante.objects.get_or_create(
            apoderado=apoderado,
            estudiante=estudiante,
            defaults={
                'tipo_apoderado': tipo_apoderado,
                'parentesco': parentesco,
                'activa': True,
            }
        )
        return relacion
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def create_apoderado(
        user,
        data: Dict,
        escuela_rbd: str,
        User,
        Role,
        Apoderado
    ) -> Tuple[bool, str, Optional[str]]:
        return ApoderadoService.execute('create_apoderado', {
            'user': user,
            'data': data,
            'escuela_rbd': escuela_rbd,
            'User': User,
            'Role': Role,
            'Apoderado': Apoderado,
        })

    @staticmethod
    def _execute_create_apoderado(params: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Crea un nuevo apoderado con su perfil completo
        
        Args:
            user: Usuario que realiza la acciÃ³n
            data: Diccionario con datos del formulario
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            Role: Modelo Role de Django
            Apoderado: Modelo Apoderado
            
        Returns:
            Tuple[bool, str, Optional[str]]: (exito, mensaje, contraseÃ±a_temporal)
        
        Raises:
            PrerequisiteException: Si el colegio no cumple prerequisitos
        """
        data = params['data']
        escuela_rbd = params['escuela_rbd']
        User = params['User']
        Role = params['Role']
        Apoderado = params['Apoderado']

        try:
            ApoderadoService._validate_school_integrity(escuela_rbd, 'CREATE_APODERADO')

            # VALIDACIÃ“N DEFENSIVA: Verificar prerequisitos del colegio
            error_prerequisito = ApoderadoService._validar_prerequisitos_colegio(int(escuela_rbd))
            if error_prerequisito:
                raise PrerequisiteException(
                    error_type=error_prerequisito['error_type'],
                    user_message=error_prerequisito['user_message'],
                    action_url=error_prerequisito.get('action_url'),
                    context=error_prerequisito.get('context', {})
                )
            
            # Obtener rol apoderado
            rol_apoderado = Role.objects.get(nombre='Apoderado')
            
            # Normalizar email
            email = data.get('email', '').strip().lower()
            rut = data.get('rut', '').strip()
            
            # Validar email Ãºnico
            is_unique, error_msg = ApoderadoService.validate_unique_email(email, User)
            if not is_unique:
                return False, error_msg, None
            
            # Validar RUT Ãºnico
            is_unique, error_msg = ApoderadoService.validate_unique_rut(rut, User)
            if not is_unique:
                return False, error_msg, None
            
            # Crear usuario
            apoderado_user = User(
                email=email,
                rut=rut if rut else None,
                nombre=data.get('nombre', '').strip(),
                apellido_paterno=data.get('apellido_paterno', '').strip(),
                apellido_materno=data.get('apellido_materno', '').strip() or None,
                role=rol_apoderado,
                rbd_colegio=escuela_rbd,
                is_active=True
            )
            
            # Generar y establecer contraseÃ±a temporal
            password_temp = ApoderadoService.generate_temp_password(rut)
            apoderado_user.set_password(password_temp)
            apoderado_user.save()
            
            # Crear perfil de apoderado
            perfil = Apoderado(
                user=apoderado_user,
                fecha_nacimiento=data.get('fecha_nacimiento') or None,
                direccion=data.get('direccion', '').strip() or None,
                telefono=data.get('telefono', '').strip() or None,
                telefono_movil=data.get('telefono_movil', '').strip() or None,
                ocupacion=data.get('ocupacion', '').strip() or None,
                lugar_trabajo=data.get('lugar_trabajo', '').strip() or None,
                telefono_trabajo=data.get('telefono_trabajo', '').strip() or None,
                puede_ver_notas=ApoderadoService._parsear_booleano(data.get('puede_ver_notas', 'true')),
                puede_ver_asistencia=ApoderadoService._parsear_booleano(data.get('puede_ver_asistencia', 'true')),
                puede_recibir_comunicados=ApoderadoService._parsear_booleano(data.get('puede_recibir_comunicados', 'true')),
                puede_firmar_citaciones=ApoderadoService._parsear_booleano(data.get('puede_firmar_citaciones', 'true')),
                puede_autorizar_salidas=ApoderadoService._parsear_booleano(data.get('puede_autorizar_salidas', 'false')),
                puede_ver_tareas=ApoderadoService._parsear_booleano(data.get('puede_ver_tareas', 'true')),
                puede_ver_materiales=ApoderadoService._parsear_booleano(data.get('puede_ver_materiales', 'true')),
                activo=True,
                observaciones=data.get('observaciones', '').strip() or None
            )
            perfil.save()
            
            logger.info(
                f"Apoderado creado - ID: {apoderado_user.id}, Nombre: {apoderado_user.nombre} {apoderado_user.apellido_paterno}"
            )
            
            return True, "âœ” Apoderado creado exitosamente. ContraseÃ±a temporal generada.", password_temp
            
        except Role.DoesNotExist:
            return False, "Rol apoderado no encontrado en el sistema", None
        except Exception as e:
            logger.error(f"Error al crear apoderado: {str(e)}")
            return False, f"Error al crear apoderado: {str(e)}", None
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def update_apoderado(
        user,
        apoderado_id: int,
        data: Dict,
        escuela_rbd: str,
        User,
        Apoderado
    ) -> Tuple[bool, str]:
        return ApoderadoService.execute('update_apoderado', {
            'user': user,
            'apoderado_id': apoderado_id,
            'data': data,
            'escuela_rbd': escuela_rbd,
            'User': User,
            'Apoderado': Apoderado,
        })

    @staticmethod
    def _execute_update_apoderado(params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Actualiza datos de un apoderado existente
        
        Args:
            user: Usuario que realiza la acciÃ³n
            apoderado_id: ID del apoderado a actualizar
            data: Diccionario con datos del formulario
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            Apoderado: Modelo Apoderado
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        apoderado_id = params['apoderado_id']
        data = params['data']
        escuela_rbd = params['escuela_rbd']
        User = params['User']
        Apoderado = params['Apoderado']

        try:
            ApoderadoService._validate_school_integrity(escuela_rbd, 'UPDATE_APODERADO')

            # Obtener apoderado
            apoderado_user = User.objects.get(
                id=apoderado_id,
                rbd_colegio=escuela_rbd,
                perfil_apoderado__isnull=False
            )
            
            # Actualizar datos bÃ¡sicos
            apoderado_user.nombre = data.get('nombre', '').strip()
            apoderado_user.apellido_paterno = data.get('apellido_paterno', '').strip()
            apoderado_user.apellido_materno = data.get('apellido_materno', '').strip() or None
            apoderado_user.rut = data.get('rut', '').strip() or None
            
            # Validar y actualizar email si cambiÃ³
            nuevo_email = data.get('email', '').strip().lower()
            if nuevo_email != apoderado_user.email:
                is_unique, error_msg = ApoderadoService.validate_unique_email(
                    nuevo_email, User, exclude_id=apoderado_id
                )
                if not is_unique:
                    return False, error_msg
                apoderado_user.email = nuevo_email
            
            apoderado_user.save()
            
            # Actualizar perfil
            perfil = apoderado_user.perfil_apoderado
            perfil.fecha_nacimiento = data.get('fecha_nacimiento') or None
            perfil.direccion = data.get('direccion', '').strip() or None
            perfil.telefono = data.get('telefono', '').strip() or None
            perfil.telefono_movil = data.get('telefono_movil', '').strip() or None
            perfil.ocupacion = data.get('ocupacion', '').strip() or None
            perfil.lugar_trabajo = data.get('lugar_trabajo', '').strip() or None
            perfil.telefono_trabajo = data.get('telefono_trabajo', '').strip() or None
            perfil.puede_ver_notas = ApoderadoService._parsear_booleano(data.get('puede_ver_notas', 'true'))
            perfil.puede_ver_asistencia = ApoderadoService._parsear_booleano(data.get('puede_ver_asistencia', 'true'))
            perfil.puede_recibir_comunicados = ApoderadoService._parsear_booleano(data.get('puede_recibir_comunicados', 'true'))
            perfil.puede_firmar_citaciones = ApoderadoService._parsear_booleano(data.get('puede_firmar_citaciones', 'true'))
            perfil.puede_autorizar_salidas = ApoderadoService._parsear_booleano(data.get('puede_autorizar_salidas', 'false'))
            perfil.puede_ver_tareas = ApoderadoService._parsear_booleano(data.get('puede_ver_tareas', 'true'))
            perfil.puede_ver_materiales = ApoderadoService._parsear_booleano(data.get('puede_ver_materiales', 'true'))
            perfil.observaciones = data.get('observaciones', '').strip() or None
            perfil.save()
            
            logger.info(f"Apoderado actualizado - ID: {apoderado_user.id}")
            
            return True, "âœ” Apoderado actualizado exitosamente"
            
        except User.DoesNotExist:
            return False, "Apoderado no encontrado"
        except Exception as e:
            logger.error(f"Error al actualizar apoderado: {str(e)}")
            return False, f"Error al actualizar apoderado: {str(e)}"
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def deactivate_apoderado(
        user,
        apoderado_id: int,
        escuela_rbd: str,
        User,
        Apoderado
    ) -> Tuple[bool, str]:
        return ApoderadoService.execute('deactivate_apoderado', {
            'user': user,
            'apoderado_id': apoderado_id,
            'escuela_rbd': escuela_rbd,
            'User': User,
            'Apoderado': Apoderado,
        })

    @staticmethod
    def _execute_deactivate_apoderado(params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Desactiva un apoderado (soft delete)
        
        Args:
            user: Usuario que realiza la acciÃ³n
            apoderado_id: ID del apoderado a desactivar
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            Apoderado: Modelo Apoderado
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        apoderado_id = params['apoderado_id']
        escuela_rbd = params['escuela_rbd']
        User = params['User']
        Apoderado = params['Apoderado']

        try:
            ApoderadoService._validate_school_integrity(escuela_rbd, 'DEACTIVATE_APODERADO')

            apoderado_user = User.objects.get(
                id=apoderado_id,
                rbd_colegio=escuela_rbd,
                perfil_apoderado__isnull=False
            )
            
            # VALIDACIÃ“N DEFENSIVA: Verificar que no tiene relaciones activas con estudiantes
            relaciones_activas = apoderado_user.apoderado_estudiantes.filter(
                estudiante__is_active=True
            ).count()
            
            if relaciones_activas > 0:
                logger.warning(
                    f"Intento de desactivar apoderado con {relaciones_activas} estudiantes activos - ID: {apoderado_id}"
                )
                return False, f"No se puede desactivar: el apoderado tiene {relaciones_activas} estudiante(s) activo(s) asociado(s)"
            
            # Desactivar usuario
            apoderado_user.is_active = False
            apoderado_user.save()
            
            # Desactivar perfil
            perfil = apoderado_user.perfil_apoderado
            perfil.activo = False
            perfil.fecha_inactivacion = datetime.now().date()
            perfil.save()
            
            logger.info(f"Apoderado desactivado - ID: {apoderado_user.id}")
            
            return True, "âœ” Apoderado desactivado exitosamente"
            
        except User.DoesNotExist:
            return False, "Apoderado no encontrado"
        except Exception as e:
            logger.error(f"Error al desactivar apoderado: {str(e)}")
            return False, f"Error al desactivar apoderado: {str(e)}"
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def reset_password(
        user,
        apoderado_id: int,
        escuela_rbd: str,
        User
    ) -> Tuple[bool, str, Optional[str]]:
        return ApoderadoService.execute('reset_password', {
            'user': user,
            'apoderado_id': apoderado_id,
            'escuela_rbd': escuela_rbd,
            'User': User,
        })

    @staticmethod
    def _execute_reset_password(params: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Resetea la contraseÃ±a de un apoderado
        
        Args:
            user: Usuario que realiza la acciÃ³n
            apoderado_id: ID del apoderado
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            
        Returns:
            Tuple[bool, str, Optional[str]]: (exito, mensaje, nueva_contraseÃ±a)
        """
        apoderado_id = params['apoderado_id']
        escuela_rbd = params['escuela_rbd']
        User = params['User']

        try:
            ApoderadoService._validate_school_integrity(escuela_rbd, 'RESET_APODERADO_PASSWORD')

            apoderado_user = User.objects.get(
                id=apoderado_id,
                rbd_colegio=escuela_rbd,
                perfil_apoderado__isnull=False
            )
            
            # Generar nueva contraseÃ±a temporal
            password_temp = ApoderadoService.generate_temp_password(apoderado_user.rut)
            apoderado_user.set_password(password_temp)
            apoderado_user.save()
            
            logger.info(f"ContraseÃ±a reseteada - Apoderado ID: {apoderado_user.id}")
            
            return True, f"âœ” ContraseÃ±a reseteada. Nueva contraseÃ±a temporal: {password_temp}", password_temp
            
        except User.DoesNotExist:
            return False, "Apoderado no encontrado", None
        except Exception as e:
            logger.error(f"Error al resetear contraseÃ±a: {str(e)}")
            return False, f"Error al resetear contraseÃ±a: {str(e)}", None
    
    @staticmethod
    def get_apoderados_stats(escuela_rbd: str, User, Apoderado) -> Dict:
        """
        Obtiene estadÃ­sticas de apoderados de un colegio
        
        Args:
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            Apoderado: Modelo Apoderado
            
        Returns:
            Dict: EstadÃ­sticas
        """
        try:
            total = User.objects.filter(
                rbd_colegio=escuela_rbd,
                perfil_apoderado__isnull=False
            ).count()
            
            activos = User.objects.filter(
                rbd_colegio=escuela_rbd,
                perfil_apoderado__isnull=False,
                is_active=True,
                perfil_apoderado__activo=True
            ).count()
            
            return {
                'total_apoderados': total,
                'apoderados_activos': activos,
                'apoderados_inactivos': total - activos
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estadÃ­sticas de apoderados: {str(e)}")
            return {
                'total_apoderados': 0,
                'apoderados_activos': 0,
                'apoderados_inactivos': 0
            }


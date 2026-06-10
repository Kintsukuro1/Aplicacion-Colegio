"""
StudentService - Servicio para gestión CRUD de estudiantes

Este servicio centraliza la lógica de negocio para:
- Crear nuevos estudiantes con perfil completo
- Editar datos de estudiantes existentes
- Desactivar estudiantes (soft delete)
- Asignar estudiantes a cursos
- Resetear contraseñas de estudiantes
- Listar y filtrar estudiantes
- Calcular estadísticas

Migrando desde: sistema_antiguo/core/views.py (líneas 1306-1567)
"""

import logging
import secrets
import string
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from django.db.models import Count, Q, Prefetch

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('accounts')


class StudentService:
    """
    Servicio para gestión completa de estudiantes (CRUD + asignación)
    """
    
    # Roles permitidos para gestión de estudiantes
    ALLOWED_ROLES = ['Administrador general', 'Administrador escolar']
    
    # Contraseña temporal por defecto
    DEFAULT_TEMP_PASSWORD = None

    @staticmethod
    def validations(data: Dict[str, Any], *, estudiante_id: Optional[int] = None) -> None:
        from backend.apps.accounts.models import User

        required = ['nombre', 'apellido_paterno', 'email']
        for field in required:
            if not str(data.get(field, '')).strip():
                raise ValueError(f'Campo requerido: {field}')

        email = str(data['email']).strip().lower()
        email_query = User.objects.filter(email=email)
        if estudiante_id is not None:
            email_query = email_query.exclude(id=estudiante_id)
        if email_query.exists():
            raise ValueError('Ya existe un usuario con ese email')

        rut = str(data.get('rut') or '').strip()
        if rut:
            rut_query = User.objects.filter(rut=rut)
            if estudiante_id is not None:
                rut_query = rut_query.exclude(id=estudiante_id)
            if rut_query.exists():
                raise ValueError('Ya existe un usuario con ese RUT')

    @staticmethod
    def create(user, data: Dict[str, Any], escuela_rbd: str):
        from backend.apps.accounts.models import PerfilEstudiante, Role, User

        StudentService.validations(data)
        return StudentService.create_student(
            user=user,
            data=data,
            escuela_rbd=escuela_rbd,
            User=User,
            Role=Role,
            PerfilEstudiante=PerfilEstudiante,
        )

    @staticmethod
    def update(user, estudiante_id: int, data: Dict[str, Any], escuela_rbd: str):
        from backend.apps.accounts.models import PerfilEstudiante, User

        StudentService.validations(data, estudiante_id=estudiante_id)
        return StudentService.update_student(
            user=user,
            estudiante_id=estudiante_id,
            data=data,
            escuela_rbd=escuela_rbd,
            User=User,
            PerfilEstudiante=PerfilEstudiante,
        )

    @staticmethod
    def delete(user, estudiante_id: int, escuela_rbd: str):
        from backend.apps.accounts.models import User

        return StudentService.deactivate_student(
            user=user,
            estudiante_id=estudiante_id,
            escuela_rbd=escuela_rbd,
            User=User,
        )

    @staticmethod
    def get(estudiante_id: int, escuela_rbd: str):
        from backend.apps.accounts.models import User

        return User.objects.select_related('role').get(
            id=estudiante_id,
            rbd_colegio=escuela_rbd,
            perfil_estudiante__isnull=False,
        )

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        """Punto de entrada estándar para comandos del servicio (fase 3.1)."""
        StudentService.validate(operation, params)
        return StudentService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        """Valida parámetros mínimos requeridos por operación."""
        user = params.get('user')
        if user is None:
            raise ValueError('Parámetro requerido: user')

        if operation in ['create_student', 'update_student'] and params.get('data') is None:
            raise ValueError('Parámetro requerido: data')

        if operation in ['update_student', 'deactivate_student', 'assign_to_course', 'reset_password'] and params.get('estudiante_id') is None:
            raise ValueError('Parámetro requerido: estudiante_id')

        if operation == 'assign_to_course' and params.get('curso_id') is None:
            raise ValueError('Parámetro requerido: curso_id')

        if params.get('escuela_rbd') is None:
            raise ValueError('Parámetro requerido: escuela_rbd')

        if operation not in ['create_student', 'update_student', 'deactivate_student', 'assign_to_course', 'reset_password']:
            raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        """Despacha operaciones de comando a implementaciones privadas."""
        if operation == 'create_student':
            return StudentService._execute_create_student(params)
        if operation == 'update_student':
            return StudentService._execute_update_student(params)
        if operation == 'deactivate_student':
            return StudentService._execute_deactivate_student(params)
        if operation == 'assign_to_course':
            return StudentService._execute_assign_to_course(params)
        if operation == 'reset_password':
            return StudentService._execute_reset_password(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(escuela_rbd: str, action: str) -> None:
        """Valida integridad del colegio antes de operaciones críticas de estudiantes."""
        action_map = {
            'CREATE_STUDENT': IntegrityService.validate_estudiante_creation,
            'UPDATE_STUDENT': IntegrityService.validate_estudiante_update,
            'DEACTIVATE_STUDENT': IntegrityService.validate_estudiante_deletion,
        }
        validator = action_map.get(action)
        if validator is not None:
            validator(escuela_rbd)
            return

        IntegrityService.validate_school_integrity_or_raise(
            school_id=int(escuela_rbd),
            action=action,
        )
    
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
        Genera una contraseña temporal basada en el RUT o usa contraseña por defecto
        
        Args:
            rut: RUT del estudiante (puede incluir puntos y guión)
            
        Returns:
            str: Contraseña temporal
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(14))
    
    @staticmethod
    def validate_unique_email(email: str, User, exclude_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Verifica que el email no esté en uso
        
        Args:
            email: Email a validar
            User: Modelo User de Django
            exclude_id: ID de usuario a excluir (para edición)
            
        Returns:
            Optional[Dict]: None si válido, Dict con error si inválido
        """
        query = User.objects.filter(email=email)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        
        if query.exists():
            return ErrorResponseBuilder.build('VALIDATION_ERROR', context={
                'field': 'email',
                'value': email,
                'message': 'Ya existe un usuario con ese email'
            })
        
        return None
    
    @staticmethod
    def validate_unique_rut(rut: str, User, exclude_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Verifica que el RUT no esté en uso
        
        Args:
            rut: RUT a validar
            User: Modelo User de Django
            exclude_id: ID de usuario a excluir (para edición)
            
        Returns:
            Optional[Dict]: None si válido, Dict con error si inválido
        """
        if not rut:
            return None  # RUT es opcional
        
        query = User.objects.filter(rut=rut)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        
        if query.exists():
            return ErrorResponseBuilder.build('VALIDATION_ERROR', context={
                'field': 'rut',
                'value': rut,
                'message': 'Ya existe un usuario con ese RUT'
            })
        
        return None
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def create_student(
        user,
        data: Dict,
        escuela_rbd: str,
        User,
        Role,
        PerfilEstudiante
    ) -> Tuple[bool, str, Optional[str]]:
        return StudentService.execute('create_student', {
            'user': user,
            'data': data,
            'escuela_rbd': escuela_rbd,
            'User': User,
            'Role': Role,
            'PerfilEstudiante': PerfilEstudiante,
        })

    @staticmethod
    def _execute_create_student(params: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Crea un nuevo estudiante con su perfil completo
        
        Args:
            data: Diccionario con datos del formulario
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            Role: Modelo Role de Django
            PerfilEstudiante: Modelo PerfilEstudiante
            
        Returns:
            Tuple[bool, str, Optional[str]]: (exito, mensaje, contraseña_temporal)
        """
        data = params['data']
        escuela_rbd = params['escuela_rbd']
        User = params['User']
        Role = params['Role']
        PerfilEstudiante = params['PerfilEstudiante']

        try:
            StudentService._validate_school_integrity(escuela_rbd, 'CREATE_STUDENT')

            # Obtener rol estudiante
            rol_estudiante = Role.objects.get(nombre='Alumno')
            
            # Normalizar email
            email = data.get('email', '').strip().lower()
            rut = data.get('rut', '').strip()
            
            # Validar email único
            error = StudentService.validate_unique_email(email, User)
            if error:
                return False, error['context']['message'], None
            
            # Validar RUT único
            error = StudentService.validate_unique_rut(rut, User)
            if error:
                return False, error['context']['message'], None
            
            # Crear usuario
            estudiante = User(
                email=email,
                rut=rut if rut else None,
                nombre=data.get('nombre', '').strip(),
                apellido_paterno=data.get('apellido_paterno', '').strip(),
                apellido_materno=data.get('apellido_materno', '').strip() or None,
                role=rol_estudiante,
                rbd_colegio=escuela_rbd,
                is_active=True
            )
            
            # Generar y establecer contraseña temporal
            password_temp = StudentService.generate_temp_password(rut)
            estudiante.set_password(password_temp)
            estudiante.save()
            
            # Crear perfil extendido
            perfil = PerfilEstudiante(
                user=estudiante,
                fecha_nacimiento=data.get('fecha_nacimiento') or None,
                direccion=data.get('direccion', '').strip() or None,
                telefono=data.get('telefono', '').strip() or None,
                contacto_emergencia_nombre=data.get('contacto_emergencia_nombre', '').strip() or None,
                contacto_emergencia_telefono=data.get('contacto_emergencia_telefono', '').strip() or None,
                apoderado_nombre=data.get('apoderado_nombre', '').strip() or None,
                apoderado_rut=data.get('apoderado_rut', '').strip() or None,
                apoderado_email=data.get('apoderado_email', '').strip() or None,
                apoderado_telefono=data.get('apoderado_telefono', '').strip() or None,
                estado_academico='Activo',
                fecha_ingreso=data.get('fecha_ingreso') or None,
            )
            perfil.save()
            
            logger.info(
                f"Estudiante creado - ID: {estudiante.id}, Nombre: {estudiante.nombre} {estudiante.apellido_paterno}"
            )
            
            return True, "✔ Estudiante creado exitosamente. Contraseña temporal generada.", password_temp
            
        except Role.DoesNotExist:
            return False, "Rol estudiante no encontrado en el sistema", None
        except Exception as e:
            logger.error(f"Error al crear estudiante: {str(e)}")
            return False, f"Error al crear estudiante: {str(e)}", None
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def update_student(
        user,
        estudiante_id: int,
        data: Dict,
        escuela_rbd: str,
        User,
        PerfilEstudiante
    ) -> Tuple[bool, str]:
        return StudentService.execute('update_student', {
            'user': user,
            'estudiante_id': estudiante_id,
            'data': data,
            'escuela_rbd': escuela_rbd,
            'User': User,
            'PerfilEstudiante': PerfilEstudiante,
        })

    @staticmethod
    def _execute_update_student(params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Actualiza datos de un estudiante existente
        
        Args:
            estudiante_id: ID del estudiante a actualizar
            data: Diccionario con datos del formulario
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            PerfilEstudiante: Modelo PerfilEstudiante
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        estudiante_id = params['estudiante_id']
        data = params['data']
        escuela_rbd = params['escuela_rbd']
        User = params['User']
        PerfilEstudiante = params['PerfilEstudiante']

        try:
            StudentService._validate_school_integrity(escuela_rbd, 'UPDATE_STUDENT')

            # Obtener estudiante
            estudiante = User.objects.get(
                id=estudiante_id,
                rbd_colegio=escuela_rbd,
                perfil_estudiante__isnull=False
            )
            
            # Actualizar datos básicos
            estudiante.nombre = data.get('nombre', '').strip()
            estudiante.apellido_paterno = data.get('apellido_paterno', '').strip()
            estudiante.apellido_materno = data.get('apellido_materno', '').strip() or None
            estudiante.rut = data.get('rut', '').strip() or None
            
            # Validar y actualizar email si cambió
            nuevo_email = data.get('email', '').strip().lower()
            if nuevo_email != estudiante.email:
                error = StudentService.validate_unique_email(
                    nuevo_email, User, exclude_id=estudiante_id
                )
                if error:
                    return False, error['context']['message']
                estudiante.email = nuevo_email
            
            estudiante.save()
            
            # Actualizar perfil
            perfil, created = PerfilEstudiante.objects.get_or_create(user=estudiante)
            perfil.fecha_nacimiento = data.get('fecha_nacimiento') or None
            perfil.direccion = data.get('direccion', '').strip() or None
            perfil.telefono = data.get('telefono', '').strip() or None
            perfil.contacto_emergencia_nombre = data.get('contacto_emergencia_nombre', '').strip() or None
            perfil.contacto_emergencia_telefono = data.get('contacto_emergencia_telefono', '').strip() or None
            perfil.apoderado_nombre = data.get('apoderado_nombre', '').strip() or None
            perfil.apoderado_rut = data.get('apoderado_rut', '').strip() or None
            perfil.apoderado_email = data.get('apoderado_email', '').strip() or None
            perfil.apoderado_telefono = data.get('apoderado_telefono', '').strip() or None
            perfil.estado_academico = data.get('estado_academico', 'Activo')
            perfil.fecha_ingreso = data.get('fecha_ingreso') or None
            perfil.observaciones = data.get('observaciones', '').strip() or None
            perfil.save()
            
            logger.info(
                f"Estudiante actualizado - ID: {estudiante.id}, Nombre: {estudiante.nombre} {estudiante.apellido_paterno}"
            )
            
            return True, "✔ Estudiante actualizado exitosamente"
            
        except User.DoesNotExist:
            return False, "Estudiante no encontrado"
        except Exception as e:
            logger.error(f"Error al actualizar estudiante: {str(e)}")
            return False, f"Error al actualizar estudiante: {str(e)}"
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def deactivate_student(
        user,
        estudiante_id: int,
        escuela_rbd: str,
        User
    ) -> Tuple[bool, str]:
        return StudentService.execute('deactivate_student', {
            'user': user,
            'estudiante_id': estudiante_id,
            'escuela_rbd': escuela_rbd,
            'User': User,
        })

    @staticmethod
    def _execute_deactivate_student(params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Desactiva un estudiante (soft delete)
        
        Args:
            estudiante_id: ID del estudiante a desactivar
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        estudiante_id = params['estudiante_id']
        escuela_rbd = params['escuela_rbd']
        User = params['User']

        try:
            StudentService._validate_school_integrity(escuela_rbd, 'DEACTIVATE_STUDENT')
            from backend.apps.matriculas.models import Matricula

            estudiante = User.objects.get(
                id=estudiante_id,
                rbd_colegio=escuela_rbd,
                perfil_estudiante__isnull=False
            )

            matriculas_activas = Matricula.objects.filter(
                estudiante=estudiante,
                estado='ACTIVA'
            ).count()
            if matriculas_activas > 0:
                return False, (
                    f'No se puede desactivar: el estudiante tiene {matriculas_activas} '
                    'matrícula(s) activa(s)'
                )
            
            # Desactivar usuario
            estudiante.is_active = False
            estudiante.save()
            
            # Actualizar estado en perfil
            if hasattr(estudiante, 'perfil_estudiante'):
                estudiante.perfil_estudiante.estado_academico = 'Retirado'
                estudiante.perfil_estudiante.save()
            
            logger.info(
                f"Estudiante desactivado - ID: {estudiante.id}, Nombre: {estudiante.nombre} {estudiante.apellido_paterno}"
            )
            
            return True, "✔ Estudiante desactivado"
            
        except User.DoesNotExist:
            return False, "Estudiante no encontrado"
        except Exception as e:
            logger.error(f"Error al desactivar estudiante: {str(e)}")
            return False, f"Error al desactivar estudiante: {str(e)}"
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def assign_to_course(
        user,
        estudiante_id: int,
        curso_id: int,
        escuela_rbd: str,
        User,
        Curso,
        PerfilEstudiante
    ) -> Tuple[bool, str]:
        return StudentService.execute('assign_to_course', {
            'user': user,
            'estudiante_id': estudiante_id,
            'curso_id': curso_id,
            'escuela_rbd': escuela_rbd,
            'User': User,
            'Curso': Curso,
            'PerfilEstudiante': PerfilEstudiante,
        })

    @staticmethod
    def _execute_assign_to_course(params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Asigna un estudiante a un curso
        
        Args:
            estudiante_id: ID del estudiante
            curso_id: ID del curso
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            Curso: Modelo Curso de Django
            PerfilEstudiante: Modelo PerfilEstudiante
            
        Returns:
            Tuple[bool, str]: (exito, mensaje)
        """
        estudiante_id = params['estudiante_id']
        curso_id = params['curso_id']
        escuela_rbd = params['escuela_rbd']
        User = params['User']
        Curso = params['Curso']
        PerfilEstudiante = params['PerfilEstudiante']

        try:
            StudentService._validate_school_integrity(escuela_rbd, 'ASSIGN_STUDENT_TO_COURSE')

            estudiante = User.objects.get(
                id=estudiante_id,
                rbd_colegio=escuela_rbd,
                perfil_estudiante__isnull=False
            )
            
            curso = Curso.objects.get(
                id_curso=curso_id,
                colegio__rbd=escuela_rbd
            )
            
            # Actualizar perfil con ciclo actual
            perfil, created = PerfilEstudiante.objects.get_or_create(user=estudiante)
            if not perfil.ciclo_actual:
                perfil.ciclo_actual = curso.ciclo_academico
                perfil.save()
            
            logger.info(
                f"Estudiante asignado a curso - Estudiante ID: {estudiante.id}, Curso: {curso.nombre}"
            )
            
            return True, f"✔ Estudiante asignado a {curso.nombre}"
            
        except User.DoesNotExist:
            return False, "Estudiante no encontrado"
        except Curso.DoesNotExist:
            return False, "Curso no encontrado"
        except Exception as e:
            logger.error(f"Error al asignar estudiante a curso: {str(e)}")
            return False, f"Error al asignar estudiante a curso: {str(e)}"
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def reset_password(
        user,
        estudiante_id: int,
        escuela_rbd: str,
        User
    ) -> Tuple[bool, str, Optional[str]]:
        return StudentService.execute('reset_password', {
            'user': user,
            'estudiante_id': estudiante_id,
            'escuela_rbd': escuela_rbd,
            'User': User,
        })

    @staticmethod
    def _execute_reset_password(params: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Resetea la contraseña de un estudiante
        
        Args:
            estudiante_id: ID del estudiante
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            
        Returns:
            Tuple[bool, str, Optional[str]]: (exito, mensaje, nueva_contraseña)
        """
        estudiante_id = params['estudiante_id']
        escuela_rbd = params['escuela_rbd']
        User = params['User']

        try:
            StudentService._validate_school_integrity(escuela_rbd, 'RESET_STUDENT_PASSWORD')

            estudiante = User.objects.get(
                id=estudiante_id,
                rbd_colegio=escuela_rbd,
                perfil_estudiante__isnull=False
            )
            
            # Generar nueva contraseña temporal
            nueva_password = StudentService.generate_temp_password(estudiante.rut)
            estudiante.set_password(nueva_password)
            estudiante.save()
            
            logger.info(
                f"Contraseña reseteada - Estudiante ID: {estudiante.id}, Nombre: {estudiante.nombre} {estudiante.apellido_paterno}"
            )
            
            return True, "✔ Contraseña reseteada y lista para entrega segura.", nueva_password
            
        except User.DoesNotExist:
            return False, "Estudiante no encontrado", None
        except Exception as e:
            logger.error(f"Error al resetear contraseña: {str(e)}")
            return False, f"Error al resetear contraseña: {str(e)}", None
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_STUDENTS')
    def list_students(
        user,
        escuela_rbd: str,
        User,
        PerfilEstudiante,
        filtro_curso: Optional[str] = None,
        filtro_estado: Optional[str] = None,
        filtro_busqueda: Optional[str] = None
    ) -> List:
        """
        Lista estudiantes con filtros opcionales
        
        Args:
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            PerfilEstudiante: Modelo PerfilEstudiante
            filtro_curso: ID de curso para filtrar (opcional)
            filtro_estado: Estado académico para filtrar (opcional)
            filtro_busqueda: Texto para buscar en nombre, apellido, RUT, email (opcional)
            
        Returns:
            List: QuerySet de estudiantes
        """
        # Construir query base
        estudiantes_query = User.objects.filter(
            rbd_colegio=escuela_rbd,
            perfil_estudiante__isnull=False,
            is_active=True
        ).select_related('role').prefetch_related(
            Prefetch('perfil_estudiante', queryset=PerfilEstudiante.objects.all())
        )
        
        # Aplicar filtro de búsqueda
        if filtro_busqueda:
            estudiantes_query = estudiantes_query.filter(
                Q(nombre__icontains=filtro_busqueda) |
                Q(apellido_paterno__icontains=filtro_busqueda) |
                Q(apellido_materno__icontains=filtro_busqueda) |
                Q(rut__icontains=filtro_busqueda) |
                Q(email__icontains=filtro_busqueda)
            )
        
        # Aplicar filtro de curso
        if filtro_curso:
            try:
                ciclo_id = int(filtro_curso)
                estudiantes_query = estudiantes_query.filter(perfil_estudiante__ciclo_actual=ciclo_id)
            except (ValueError, TypeError):
                pass
        
        # Aplicar filtro de estado
        if filtro_estado:
            estudiantes_query = estudiantes_query.filter(perfil_estudiante__estado_academico=filtro_estado)
        
        # Ordenar por apellidos y nombre
        return estudiantes_query.order_by('apellido_paterno', 'apellido_materno', 'nombre')
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_STUDENTS')
    def get_statistics(
        user,
        escuela_rbd: str,
        User,
        PerfilEstudiante
    ) -> Dict:
        """
        Calcula estadísticas de estudiantes
        
        Args:
            escuela_rbd: RBD del colegio
            User: Modelo User de Django
            PerfilEstudiante: Modelo PerfilEstudiante
            
        Returns:
            Dict: Diccionario con estadísticas
        """
        # Total de estudiantes activos
        total_estudiantes = User.objects.filter(
            rbd_colegio=escuela_rbd,
            perfil_estudiante__isnull=False,
            is_active=True
        ).count()
        
        # Estudiantes por estado
        stats_estados = PerfilEstudiante.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_estudiante__isnull=False,
            user__is_active=True
        ).values('estado_academico').annotate(total=Count('id'))
        
        estudiantes_activos = sum(
            s['total'] for s in stats_estados if s['estado_academico'] == 'Activo'
        )
        
        # Estudiantes sin curso
        estudiantes_sin_curso = PerfilEstudiante.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_estudiante__isnull=False,
            user__is_active=True,
            ciclo_actual__isnull=True
        ).count()
        
        # Estudiantes por ciclo
        stats_cursos = PerfilEstudiante.objects.filter(
            user__rbd_colegio=escuela_rbd,
            user__perfil_estudiante__isnull=False,
            user__is_active=True,
            ciclo_actual__isnull=False
        ).values('ciclo_actual').annotate(total=Count('id'))
        
        total_cursos_con_estudiantes = len(stats_cursos)
        
        return {
            'total_estudiantes': total_estudiantes,
            'estudiantes_activos': estudiantes_activos,
            'estudiantes_sin_curso': estudiantes_sin_curso,
            'total_cursos_con_estudiantes': total_cursos_con_estudiantes,
        }
    
    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'VIEW_STUDENTS')
    def get_available_courses(escuela_rbd: str, Curso) -> List:
        """
        Obtiene cursos disponibles para asignación
        
        Args:
            escuela_rbd: RBD del colegio
            Curso: Modelo Curso de Django
            
        Returns:
            List: QuerySet de cursos disponibles
        """
        anio_actual = datetime.now().year
        
        cursos = Curso.objects.filter(
            colegio__rbd=escuela_rbd,
            activo=True,
            anio_escolar__gte=anio_actual - 1  # Incluir año anterior, actual y futuros
        ).select_related('nivel').order_by('-anio_escolar', 'nivel__nombre', 'nombre')
        
        return cursos

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def process_student_action(user, escuela_rbd: str, post_data: Dict) -> Dict:
        """
        Procesa una acción de gestión de estudiantes.

        Args:
            user: Usuario que realiza la acción
            escuela_rbd: RBD de la escuela
            post_data: Datos del POST request

        Returns:
            Dict: Resultado con 'success', 'message', y datos adicionales si aplica
        """
        from backend.apps.accounts.models import User, Role, PerfilEstudiante
        from backend.apps.cursos.models import Curso
        
        try:
            accion = post_data.get('accion')
            
            if accion == 'crear':
                success, message, password = StudentService.create_student(
                    user=user,
                    data=post_data,
                    escuela_rbd=escuela_rbd,
                    User=User,
                    Role=Role,
                    PerfilEstudiante=PerfilEstudiante
                )
                return {
                    'success': success,
                    'message': message,
                    'password': password if success else None
                }
                
            elif accion == 'editar':
                estudiante_id = int(post_data.get('id'))
                success, message = StudentService.update_student(
                    user=user,
                    estudiante_id=estudiante_id,
                    data=post_data,
                    escuela_rbd=escuela_rbd,
                    User=User,
                    PerfilEstudiante=PerfilEstudiante
                )
                return {
                    'success': success,
                    'message': message
                }
                
            elif accion == 'eliminar':
                estudiante_id = int(post_data.get('id'))
                success, message = StudentService.deactivate_student(
                    user=user,
                    estudiante_id=estudiante_id,
                    escuela_rbd=escuela_rbd,
                    User=User
                )
                return {
                    'success': success,
                    'message': message
                }
                
            elif accion == 'asignar_curso':
                estudiante_id = int(post_data.get('estudiante_id'))
                curso_id = int(post_data.get('curso_id'))
                success, message = StudentService.assign_to_course(
                    user=user,
                    estudiante_id=estudiante_id,
                    curso_id=curso_id,
                    escuela_rbd=escuela_rbd,
                    User=User,
                    Curso=Curso,
                    PerfilEstudiante=PerfilEstudiante
                )
                return {
                    'success': success,
                    'message': message
                }
                
            elif accion == 'resetear_password':
                estudiante_id = int(post_data.get('id'))
                success, message, password = StudentService.reset_password(
                    user=user,
                    estudiante_id=estudiante_id,
                    escuela_rbd=escuela_rbd,
                    User=User
                )
                return {
                    'success': success,
                    'message': message,
                    'password': password if success else None
                }
                
            else:
                return {
                    'success': False,
                    'message': 'Acción no reconocida'
                }
                
        except Exception as e:
            logger.error(f"Error procesando acción de estudiante: {str(e)}")
            return {
                'success': False,
                'message': f'Error al procesar la solicitud: {str(e)}'
            }


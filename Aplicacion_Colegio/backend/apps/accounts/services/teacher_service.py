"""
TeacherService - Servicio para gestión CRUD de profesores

Este servicio centraliza la lógica de negocio para:
- Crear nuevos profesores con perfil completo (PerfilProfesor)
- Editar datos de profesores existentes y sus perfiles
- Desactivar profesores (soft delete)
- Resetear contraseñas de profesores
"""

import logging
import secrets
import string
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from django.db import transaction
from django.db.models import Q

from backend.common.services import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('accounts')


class TeacherService:
    """
    Servicio para gestión completa de profesores (CRUD)
    """

    @staticmethod
    def validations(data: Dict[str, Any], *, profesor_id: Optional[int] = None) -> None:
        from backend.apps.accounts.models import User

        required = ['nombre', 'apellido_paterno', 'email']
        for field in required:
            if not str(data.get(field, '')).strip():
                raise ValueError(f'Campo requerido: {field}')

        email = str(data['email']).strip().lower()
        email_query = User.objects.filter(email=email)
        if profesor_id is not None:
            email_query = email_query.exclude(id=profesor_id)
        if email_query.exists():
            raise ValueError('Ya existe un usuario con ese email')

        rut = str(data.get('rut') or '').strip()
        if rut:
            rut_query = User.objects.filter(rut=rut)
            if profesor_id is not None:
                rut_query = rut_query.exclude(id=profesor_id)
            if rut_query.exists():
                raise ValueError('Ya existe un usuario con ese RUT')

    @staticmethod
    def generate_temp_password() -> str:
        """Genera una contraseña temporal segura."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(14))

    @staticmethod
    def _parse_date(valor: Any):
        if not valor or not str(valor).strip():
            return None
        try:
            val_str = str(valor).strip()
            return datetime.strptime(val_str, '%Y-%m-%d').date()
        except ValueError:
            return None

    @staticmethod
    def _parse_int(valor: Any, default=0):
        if not valor or not str(valor).strip():
            return default
        try:
            return int(str(valor).strip())
        except ValueError:
            return default

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')  # Reutiliza permiso administrativo escolar
    def create_teacher(
        user,
        data: Dict[str, Any],
        escuela_rbd: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Crea un nuevo profesor con su perfil de profesor completo.
        
        Args:
            user: Usuario que realiza la acción
            data: Datos del formulario
            escuela_rbd: RBD del colegio
            
        Returns:
            Tuple[bool, str, Optional[str]]: (exito, mensaje, contrasena_temporal)
        """
        from backend.apps.accounts.models import User, Role, PerfilProfesor

        try:
            TeacherService.validations(data)
            
            # Obtener rol Profesor
            rol_profesor = Role.objects.filter(nombre__iexact="Profesor").first() or Role.objects.filter(nombre__iexact="Docente").first()
            if not rol_profesor:
                return False, "El rol 'Profesor' no está configurado en el sistema", None

            email = data.get('email', '').strip().lower()
            rut = data.get('rut', '').strip() or None

            with transaction.atomic():
                # Crear el usuario base
                profesor = User(
                    email=email,
                    rut=rut,
                    nombre=data.get('nombre', '').strip(),
                    apellido_paterno=data.get('apellido_paterno', '').strip(),
                    apellido_materno=data.get('apellido_materno', '').strip() or None,
                    role=rol_profesor,
                    rbd_colegio=escuela_rbd,
                    is_active=True
                )
                password_temp = TeacherService.generate_temp_password()
                profesor.set_password(password_temp)
                profesor.save()

                # Crear el perfil del profesor
                PerfilProfesor.objects.create(
                    user=profesor,
                    fecha_nacimiento=TeacherService._parse_date(data.get('fecha_nacimiento')),
                    direccion=data.get('direccion', '').strip() or None,
                    telefono=data.get('telefono', '').strip() or None,
                    telefono_movil=data.get('telefono_movil', '').strip() or None,
                    especialidad=data.get('especialidad', '').strip() or None,
                    titulo_profesional=data.get('titulo_profesional', '').strip() or None,
                    universidad=data.get('universidad', '').strip() or None,
                    anio_titulacion=TeacherService._parse_int(data.get('anio_titulacion'), default=None),
                    fecha_ingreso=TeacherService._parse_date(data.get('fecha_ingreso')) or datetime.now().date(),
                    estado_laboral=data.get('estado_laboral', 'Activo') or 'Activo',
                    horas_semanales_contrato=TeacherService._parse_int(data.get('horas_semanales_contrato'), default=44),
                    horas_no_lectivas=TeacherService._parse_int(data.get('horas_no_lectivas'), default=0),
                    observaciones=data.get('observaciones', '').strip() or None
                )

            logger.info(f"Profesor creado - ID: {profesor.id}, Nombre: {profesor.get_full_name()} por {user.email}")
            return True, "✔ Profesor creado exitosamente. Contraseña temporal generada.", password_temp

        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error al crear profesor: {str(e)}")
            return False, f"Error al crear profesor: {str(e)}", None

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def update_teacher(
        user,
        profesor_id: int,
        data: Dict[str, Any],
        escuela_rbd: str
    ) -> Tuple[bool, str]:
        """
        Actualiza los datos de un profesor y su perfil.
        """
        from backend.apps.accounts.models import User, PerfilProfesor

        try:
            TeacherService.validations(data, profesor_id=profesor_id)

            profesor = User.objects.get(
                id=profesor_id,
                rbd_colegio=escuela_rbd,
                perfil_profesor__isnull=False
            )

            with transaction.atomic():
                # Actualizar usuario
                profesor.nombre = data.get('nombre', '').strip()
                profesor.apellido_paterno = data.get('apellido_paterno', '').strip()
                profesor.apellido_materno = data.get('apellido_materno', '').strip() or None
                profesor.rut = data.get('rut', '').strip() or None

                nuevo_email = data.get('email', '').strip().lower()
                if nuevo_email != profesor.email:
                    profesor.email = nuevo_email
                profesor.save()

                # Actualizar o crear perfil
                perfil, _ = PerfilProfesor.objects.get_or_create(user=profesor)
                perfil.fecha_nacimiento = TeacherService._parse_date(data.get('fecha_nacimiento'))
                perfil.direccion = data.get('direccion', '').strip() or None
                perfil.telefono = data.get('telefono', '').strip() or None
                perfil.telefono_movil = data.get('telefono_movil', '').strip() or None
                perfil.especialidad = data.get('especialidad', '').strip() or None
                perfil.titulo_profesional = data.get('titulo_profesional', '').strip() or None
                perfil.universidad = data.get('universidad', '').strip() or None
                perfil.anio_titulacion = TeacherService._parse_int(data.get('anio_titulacion'), default=None)
                
                if data.get('fecha_ingreso'):
                    perfil.fecha_ingreso = TeacherService._parse_date(data.get('fecha_ingreso'))
                
                perfil.estado_laboral = data.get('estado_laboral', 'Activo') or 'Activo'
                perfil.horas_semanales_contrato = TeacherService._parse_int(data.get('horas_semanales_contrato'), default=44)
                perfil.horas_no_lectivas = TeacherService._parse_int(data.get('horas_no_lectivas'), default=0)
                perfil.observaciones = data.get('observaciones', '').strip() or None
                perfil.save()

            logger.info(f"Profesor actualizado - ID: {profesor.id}, Nombre: {profesor.get_full_name()} por {user.email}")
            return True, "✔ Profesor actualizado exitosamente"

        except User.DoesNotExist:
            return False, "Profesor no encontrado"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Error al actualizar profesor: {str(e)}")
            return False, f"Error al actualizar profesor: {str(e)}"

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def deactivate_teacher(
        user,
        profesor_id: int,
        escuela_rbd: str
    ) -> Tuple[bool, str]:
        """
        Desactiva a un profesor (soft delete).
        """
        from backend.apps.accounts.models import User

        try:
            profesor = User.objects.get(
                id=profesor_id,
                rbd_colegio=escuela_rbd,
                perfil_profesor__isnull=False
            )

            # Validar si tiene clases activas asignadas antes de desactivar
            from backend.apps.cursos.models import Clase
            clases_activas = Clase.objects.filter(profesor=profesor, activo=True).count()
            if clases_activas > 0:
                return False, f"No se puede desactivar: el profesor tiene {clases_activas} clase(s) activa(s) asignada(s)"

            with transaction.atomic():
                profesor.is_active = False
                profesor.save()

                if hasattr(profesor, 'perfil_profesor'):
                    profesor.perfil_profesor.estado_laboral = 'Retirado'
                    profesor.perfil_profesor.save()

            logger.info(f"Profesor desactivado - ID: {profesor.id} por {user.email}")
            return True, "✔ Profesor desactivado correctamente"

        except User.DoesNotExist:
            return False, "Profesor no encontrado"
        except Exception as e:
            logger.error(f"Error al desactivar profesor: {str(e)}")
            return False, f"Error al desactivar profesor: {str(e)}"

    @staticmethod
    @PermissionService.require_permission('ACADEMICO', 'MANAGE_STUDENTS')
    def reset_password(
        user,
        profesor_id: int,
        escuela_rbd: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Resetea la contraseña de un profesor generando una contraseña temporal.
        """
        from backend.apps.accounts.models import User

        try:
            profesor = User.objects.get(
                id=profesor_id,
                rbd_colegio=escuela_rbd,
                perfil_profesor__isnull=False
            )

            password_temp = TeacherService.generate_temp_password()
            profesor.set_password(password_temp)
            profesor.save()

            logger.info(f"Contraseña de profesor reseteada - ID: {profesor.id} por {user.email}")
            return True, "✔ Contraseña reseteada exitosamente. Contraseña temporal generada.", password_temp

        except User.DoesNotExist:
            return False, "Profesor no encontrado", None
        except Exception as e:
            logger.error(f"Error al resetear contraseña de profesor: {str(e)}")
            return False, f"Error al resetear contraseña: {str(e)}", None

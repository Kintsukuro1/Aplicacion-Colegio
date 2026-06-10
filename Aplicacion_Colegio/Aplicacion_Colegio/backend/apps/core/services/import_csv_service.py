"""Servicio de importación CSV para estudiantes, profesores y apoderados.

Siguiendo reglas del proyecto: toda la lógica de negocio en servicios.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from django.contrib.auth.hashers import make_password
from django.db import transaction

from backend.apps.accounts.models import Apoderado, PerfilEstudiante, PerfilProfesor, Role, User
from backend.apps.institucion.models import CicloAcademico, Colegio
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.error_response import ErrorResponseBuilder

logger = logging.getLogger(__name__)


class ImportacionCSVService:
    """Servicio para importar usuarios desde archivos CSV."""

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    @staticmethod
    def get_importar_datos_dashboard(rbd_colegio: int) -> Dict:
        """
        Obtiene datos para la vista de importación de datos.

        Incluye listados resumidos y totales por rol para el colegio.
        """
        rol_estudiante = (
            Role.objects.filter(nombre__iexact="Alumno").first()
            or Role.objects.filter(nombre__iexact="Estudiante").first()
        )
        rol_profesor = Role.objects.filter(nombre__iexact="Profesor").first()
        rol_apoderado = Role.objects.filter(nombre__iexact="Apoderado").first()

        estudiantes_qs = User.objects.filter(rbd_colegio=rbd_colegio)
        profesores_qs = User.objects.filter(rbd_colegio=rbd_colegio)
        apoderados_qs = User.objects.filter(rbd_colegio=rbd_colegio)

        if rol_estudiante:
            estudiantes_qs = estudiantes_qs.filter(role=rol_estudiante)
        else:
            estudiantes_qs = estudiantes_qs.none()

        if rol_profesor:
            profesores_qs = profesores_qs.filter(role=rol_profesor)
        else:
            profesores_qs = profesores_qs.none()

        if rol_apoderado:
            apoderados_qs = apoderados_qs.filter(role=rol_apoderado)
        else:
            apoderados_qs = apoderados_qs.none()

        return {
            "estudiantes": estudiantes_qs.select_related("perfil_estudiante").order_by(
                "apellido_paterno", "nombre"
            )[:50],
            "profesores": profesores_qs.select_related("perfil_profesor").order_by(
                "apellido_paterno", "nombre"
            )[:50],
            "apoderados": apoderados_qs.select_related("perfil_apoderado").order_by(
                "apellido_paterno", "nombre"
            )[:50],
            "total_estudiantes": estudiantes_qs.count(),
            "total_profesores": profesores_qs.count(),
            "total_apoderados": apoderados_qs.count(),
        }

    @staticmethod
    def execute(operation: str, params: Dict):
        ImportacionCSVService.validate(operation, params)
        return ImportacionCSVService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict) -> None:
        if operation in ['importar_estudiantes', 'importar_profesores', 'importar_apoderados']:
            if params.get('archivo') is None:
                raise ValueError('Parámetro requerido: archivo')
            if params.get('rbd_colegio') is None:
                raise ValueError('Parámetro requerido: rbd_colegio')
            return
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict):
        if operation == 'importar_estudiantes':
            return ImportacionCSVService._execute_importar_estudiantes(params)
        if operation == 'importar_profesores':
            return ImportacionCSVService._execute_importar_profesores(params)
        if operation == 'importar_apoderados':
            return ImportacionCSVService._execute_importar_apoderados(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(rbd_colegio: int, action: str) -> None:
        """Valida integridad del colegio antes de importaciones masivas."""
        try:
            IntegrityService.validate_school_integrity_or_raise(
                school_id=rbd_colegio,
                action=action,
            )
        except PrerequisiteException as exc:
            logger.warning("Continuing despite integrity inconsistencies for %s: %s", action, exc)

    @staticmethod
    def _validar_prerequisitos_colegio(rbd_colegio: int) -> Optional[dict]:
        """
        Valida que el colegio exista, esté activo y tenga ciclo académico activo.
        
        Returns:
            None si todo está correcto, dict con error si hay problemas.
        """
        # Validar que existe el colegio
        try:
            colegio = Colegio.objects.get(rbd=rbd_colegio)
        except Colegio.DoesNotExist:
            return ErrorResponseBuilder.build(
                'SCHOOL_NOT_CONFIGURED',
                user_message=f'El colegio con RBD {rbd_colegio} no existe en el sistema',
                context={'rbd_colegio': rbd_colegio}
            )
        
        # Validar que el colegio esté activo
        if not getattr(colegio, 'activo', True):
            return ErrorResponseBuilder.build(
                'INVALID_STATE',
                user_message=f'El colegio {colegio.nombre} no está activo. No se pueden importar usuarios.',
                action_url='/admin/seleccionar_escuela/',
                context={'rbd_colegio': rbd_colegio, 'colegio_nombre': colegio.nombre}
            )
        
        # Validar que existe ciclo académico activo
        ciclo_activo = CicloAcademico.objects.filter(colegio=colegio, estado='ACTIVO').first()
        if not ciclo_activo:
            return ErrorResponseBuilder.build(
                'MISSING_CICLO_ACTIVO',
                user_message=f'El colegio {colegio.nombre} no tiene un ciclo académico activo. Debe crear uno antes de importar usuarios.',
                action_url='/admin/academico/cicloacademico/add/',
                context={'rbd_colegio': rbd_colegio, 'colegio_nombre': colegio.nombre}
            )
        
        return None

    @staticmethod
    def validar_archivo(archivo) -> Tuple[bool, str]:
        """Valida que el archivo sea CSV y no exceda el tamaño máximo."""
        if not archivo.name.endswith('.csv'):
            return False, "El archivo debe ser un CSV (.csv)"
        
        if archivo.size > ImportacionCSVService.MAX_FILE_SIZE:
            return False, f"El archivo excede el tamaño máximo de 5 MB"
        
        return True, ""

    @staticmethod
    def _parsear_booleano(valor: str) -> bool:
        """Convierte string a booleano."""
        if not valor:
            return False
        return valor.strip().lower() in ('true', '1', 'si', 'sí', 'yes', 't')

    @staticmethod
    def _parsear_fecha(valor: str):
        """Convierte string a fecha en formato YYYY-MM-DD."""
        if not valor or not valor.strip():
            return None
        try:
            return datetime.strptime(valor.strip(), '%Y-%m-%d').date()
        except ValueError:
            return None

    @staticmethod
    def _parsear_entero(valor: str, default=None):
        """Convierte string a entero."""
        if not valor or not valor.strip():
            return default
        try:
            return int(valor.strip())
        except ValueError:
            return default

    @staticmethod
    def importar_estudiantes(archivo, rbd_colegio: int) -> Tuple[int, int, List[str]]:
        return ImportacionCSVService.execute('importar_estudiantes', {
            'archivo': archivo,
            'rbd_colegio': rbd_colegio,
        })

    @staticmethod
    def _execute_importar_estudiantes(params: Dict) -> Tuple[int, int, List[str]]:
        """
        Importa estudiantes desde archivo CSV.
        
        Returns:
            Tuple[exitosos, fallidos, errores]
        
        Raises:
            PrerequisiteException: Si el colegio no cumple prerequisitos
        """
        archivo = params['archivo']
        rbd_colegio = params['rbd_colegio']

        # Validar prerequisitos del colegio ANTES de procesar archivo
        error_prerequisito = ImportacionCSVService._validar_prerequisitos_colegio(rbd_colegio)
        if error_prerequisito:
            raise PrerequisiteException(
                error_type=error_prerequisito['error_type'],
                user_message=error_prerequisito['user_message'],
                action_url=error_prerequisito.get('action_url'),
                context=error_prerequisito.get('context', {})
            )

        ImportacionCSVService._validate_school_integrity(rbd_colegio, 'IMPORTAR_ESTUDIANTES')
        
        valido, mensaje = ImportacionCSVService.validar_archivo(archivo)
        if not valido:
            return 0, 0, [mensaje]

        rol_estudiante = (
            Role.objects.filter(nombre__iexact="Alumno").first()
            or Role.objects.filter(nombre__iexact="Estudiante").first()
        )
        if not rol_estudiante:
            return 0, 0, ["No existe un rol de estudiante en el sistema"]

        exitosos = 0
        fallidos = 0
        errores = []

        try:
            contenido = archivo.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(contenido))

            for idx, fila in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    with transaction.atomic():
                        # Validar campos obligatorios
                        email = fila.get('email', '').strip()
                        nombre = fila.get('nombre', '').strip()
                        apellido_paterno = fila.get('apellido_paterno', '').strip()
                        rut = fila.get('rut', '').strip()
                        password = fila.get('password', '').strip()

                        if not all([email, nombre, apellido_paterno, rut, password]):
                            errores.append(f"Fila {idx}: Faltan campos obligatorios (email, nombre, apellido_paterno, rut, password)")
                            fallidos += 1
                            continue

                        if len(password) < 12:
                            errores.append(f"Fila {idx}: La contraseña debe tener al menos 12 caracteres")
                            fallidos += 1
                            continue

                        # Verificar si el usuario ya existe
                        if User.objects.filter(email=email).exists():
                            errores.append(f"Fila {idx}: Ya existe un usuario con el email {email}")
                            fallidos += 1
                            continue

                        if User.objects.filter(rut=rut).exists():
                            errores.append(f"Fila {idx}: Ya existe un usuario con el RUT {rut}")
                            fallidos += 1
                            continue

                        # Crear usuario
                        user = User.objects.create(
                            email=email,
                            nombre=nombre,
                            apellido_paterno=apellido_paterno,
                            apellido_materno=fila.get('apellido_materno', '').strip() or None,
                            rut=rut,
                            role=rol_estudiante,
                            rbd_colegio=rbd_colegio,
                            password=make_password(password),
                            is_active=True
                        )

                        # Crear perfil de estudiante
                        PerfilEstudiante.objects.create(
                            user=user,
                            fecha_nacimiento=ImportacionCSVService._parsear_fecha(fila.get('fecha_nacimiento', '')),
                            direccion=fila.get('direccion', '').strip() or None,
                            telefono=fila.get('telefono', '').strip() or None,
                            telefono_movil=fila.get('telefono_movil', '').strip() or None,
                            contacto_emergencia_nombre=fila.get('contacto_emergencia_nombre', '').strip() or None,
                            contacto_emergencia_relacion=fila.get('contacto_emergencia_relacion', '').strip() or None,
                            contacto_emergencia_telefono=fila.get('contacto_emergencia_telefono', '').strip() or None,
                            grupo_sanguineo=fila.get('grupo_sanguineo', '').strip() or None,
                            alergias=fila.get('alergias', '').strip() or None,
                            condiciones_medicas=fila.get('condiciones_medicas', '').strip() or None,
                            tiene_nee=ImportacionCSVService._parsear_booleano(fila.get('tiene_nee', '')),
                            tipo_nee=fila.get('tipo_nee', '').strip() or None,
                            descripcion_nee=fila.get('descripcion_nee', '').strip() or None,
                            requiere_pie=ImportacionCSVService._parsear_booleano(fila.get('requiere_pie', '')),
                            fecha_ingreso=ImportacionCSVService._parsear_fecha(fila.get('fecha_ingreso', '')),
                            estado_academico=fila.get('estado_academico', 'Activo').strip() or 'Activo',
                            observaciones=fila.get('observaciones', '').strip() or None
                        )

                        exitosos += 1

                except Exception as e:
                    errores.append(f"Fila {idx}: Error al procesar - {str(e)}")
                    fallidos += 1

        except UnicodeDecodeError:
            errores.append("Error al leer el archivo. Asegúrate de que esté codificado en UTF-8")
        except Exception as e:
            errores.append(f"Error general al procesar el archivo: {str(e)}")

        return exitosos, fallidos, errores

    @staticmethod
    def importar_profesores(archivo, rbd_colegio: int) -> Tuple[int, int, List[str]]:
        return ImportacionCSVService.execute('importar_profesores', {
            'archivo': archivo,
            'rbd_colegio': rbd_colegio,
        })

    @staticmethod
    def _execute_importar_profesores(params: Dict) -> Tuple[int, int, List[str]]:
        """
        Importa profesores desde archivo CSV.
        
        Returns:
            Tuple[exitosos, fallidos, errores]
        
        Raises:
            PrerequisiteException: Si el colegio no cumple prerequisitos
        """
        archivo = params['archivo']
        rbd_colegio = params['rbd_colegio']

        # Validar prerequisitos del colegio ANTES de procesar archivo
        error_prerequisito = ImportacionCSVService._validar_prerequisitos_colegio(rbd_colegio)
        if error_prerequisito:
            raise PrerequisiteException(
                error_type=error_prerequisito['error_type'],
                user_message=error_prerequisito['user_message'],
                action_url=error_prerequisito.get('action_url'),
                context=error_prerequisito.get('context', {})
            )

        ImportacionCSVService._validate_school_integrity(rbd_colegio, 'IMPORTAR_PROFESORES')
        
        valido, mensaje = ImportacionCSVService.validar_archivo(archivo)
        if not valido:
            return 0, 0, [mensaje]

        rol_profesor = Role.objects.filter(nombre__iexact="Profesor").first()
        if not rol_profesor:
            return 0, 0, ["No existe el rol 'Profesor' en el sistema"]

        exitosos = 0
        fallidos = 0
        errores = []

        try:
            contenido = archivo.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(contenido))

            for idx, fila in enumerate(reader, start=2):
                try:
                    with transaction.atomic():
                        # Validar campos obligatorios
                        email = fila.get('email', '').strip()
                        nombre = fila.get('nombre', '').strip()
                        apellido_paterno = fila.get('apellido_paterno', '').strip()
                        rut = fila.get('rut', '').strip()
                        password = fila.get('password', '').strip()

                        if not all([email, nombre, apellido_paterno, rut, password]):
                            errores.append(f"Fila {idx}: Faltan campos obligatorios (email, nombre, apellido_paterno, rut, password)")
                            fallidos += 1
                            continue

                        if len(password) < 12:
                            errores.append(f"Fila {idx}: La contraseña debe tener al menos 12 caracteres")
                            fallidos += 1
                            continue

                        # Verificar si el usuario ya existe
                        if User.objects.filter(email=email).exists():
                            errores.append(f"Fila {idx}: Ya existe un usuario con el email {email}")
                            fallidos += 1
                            continue

                        if User.objects.filter(rut=rut).exists():
                            errores.append(f"Fila {idx}: Ya existe un usuario con el RUT {rut}")
                            fallidos += 1
                            continue

                        # Crear usuario
                        user = User.objects.create(
                            email=email,
                            nombre=nombre,
                            apellido_paterno=apellido_paterno,
                            apellido_materno=fila.get('apellido_materno', '').strip() or None,
                            rut=rut,
                            role=rol_profesor,
                            rbd_colegio=rbd_colegio,
                            password=make_password(password),
                            is_active=True
                        )

                        # Crear perfil de profesor
                        PerfilProfesor.objects.create(
                            user=user,
                            fecha_nacimiento=ImportacionCSVService._parsear_fecha(fila.get('fecha_nacimiento', '')),
                            direccion=fila.get('direccion', '').strip() or None,
                            telefono=fila.get('telefono', '').strip() or None,
                            telefono_movil=fila.get('telefono_movil', '').strip() or None,
                            especialidad=fila.get('especialidad', '').strip() or None,
                            titulo_profesional=fila.get('titulo_profesional', '').strip() or None,
                            universidad=fila.get('universidad', '').strip() or None,
                            anio_titulacion=ImportacionCSVService._parsear_entero(fila.get('anio_titulacion', '')),
                            fecha_ingreso=ImportacionCSVService._parsear_fecha(fila.get('fecha_ingreso', '')),
                            estado_laboral=fila.get('estado_laboral', 'Activo').strip() or 'Activo',
                            horas_semanales_contrato=ImportacionCSVService._parsear_entero(fila.get('horas_semanales_contrato', ''), default=44),
                            horas_no_lectivas=ImportacionCSVService._parsear_entero(fila.get('horas_no_lectivas', ''), default=0),
                            observaciones=fila.get('observaciones', '').strip() or None
                        )

                        exitosos += 1

                except Exception as e:
                    errores.append(f"Fila {idx}: Error al procesar - {str(e)}")
                    fallidos += 1

        except UnicodeDecodeError:
            errores.append("Error al leer el archivo. Asegúrate de que esté codificado en UTF-8")
        except Exception as e:
            errores.append(f"Error general al procesar el archivo: {str(e)}")

        return exitosos, fallidos, errores

    @staticmethod
    def importar_apoderados(archivo, rbd_colegio: int) -> Tuple[int, int, List[str]]:
        return ImportacionCSVService.execute('importar_apoderados', {
            'archivo': archivo,
            'rbd_colegio': rbd_colegio,
        })

    @staticmethod
    def _execute_importar_apoderados(params: Dict) -> Tuple[int, int, List[str]]:
        """
        Importa apoderados desde archivo CSV.
        
        Returns:
            Tuple[exitosos, fallidos, errores]
        
        Raises:
            PrerequisiteException: Si el colegio no cumple prerequisitos
        """
        archivo = params['archivo']
        rbd_colegio = params['rbd_colegio']

        # Validar prerequisitos del colegio ANTES de procesar archivo
        error_prerequisito = ImportacionCSVService._validar_prerequisitos_colegio(rbd_colegio)
        if error_prerequisito:
            raise PrerequisiteException(
                error_type=error_prerequisito['error_type'],
                user_message=error_prerequisito['user_message'],
                action_url=error_prerequisito.get('action_url'),
                context=error_prerequisito.get('context', {})
            )

        ImportacionCSVService._validate_school_integrity(rbd_colegio, 'IMPORTAR_APODERADOS')
        
        valido, mensaje = ImportacionCSVService.validar_archivo(archivo)
        if not valido:
            return 0, 0, [mensaje]

        rol_apoderado = Role.objects.filter(nombre__iexact="Apoderado").first()
        if not rol_apoderado:
            return 0, 0, ["No existe el rol 'Apoderado' en el sistema"]

        exitosos = 0
        fallidos = 0
        errores = []

        try:
            contenido = archivo.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(contenido))

            for idx, fila in enumerate(reader, start=2):
                try:
                    with transaction.atomic():
                        # Validar campos obligatorios
                        email = fila.get('email', '').strip()
                        nombre = fila.get('nombre', '').strip()
                        apellido_paterno = fila.get('apellido_paterno', '').strip()
                        rut = fila.get('rut', '').strip()
                        password = fila.get('password', '').strip()

                        if not all([email, nombre, apellido_paterno, rut, password]):
                            errores.append(f"Fila {idx}: Faltan campos obligatorios (email, nombre, apellido_paterno, rut, password)")
                            fallidos += 1
                            continue

                        if len(password) < 12:
                            errores.append(f"Fila {idx}: La contraseña debe tener al menos 12 caracteres")
                            fallidos += 1
                            continue

                        # Verificar si el usuario ya existe
                        if User.objects.filter(email=email).exists():
                            errores.append(f"Fila {idx}: Ya existe un usuario con el email {email}")
                            fallidos += 1
                            continue

                        if User.objects.filter(rut=rut).exists():
                            errores.append(f"Fila {idx}: Ya existe un usuario con el RUT {rut}")
                            fallidos += 1
                            continue

                        # Crear usuario
                        user = User.objects.create(
                            email=email,
                            nombre=nombre,
                            apellido_paterno=apellido_paterno,
                            apellido_materno=fila.get('apellido_materno', '').strip() or None,
                            rut=rut,
                            role=rol_apoderado,
                            rbd_colegio=rbd_colegio,
                            password=make_password(password),
                            is_active=True
                        )

                        # Crear perfil de apoderado
                        Apoderado.objects.create(
                            user=user,
                            fecha_nacimiento=ImportacionCSVService._parsear_fecha(fila.get('fecha_nacimiento', '')),
                            direccion=fila.get('direccion', '').strip() or None,
                            telefono=fila.get('telefono', '').strip() or None,
                            telefono_movil=fila.get('telefono_movil', '').strip() or None,
                            ocupacion=fila.get('ocupacion', '').strip() or None,
                            lugar_trabajo=fila.get('lugar_trabajo', '').strip() or None,
                            telefono_trabajo=fila.get('telefono_trabajo', '').strip() or None,
                            puede_ver_notas=ImportacionCSVService._parsear_booleano(fila.get('puede_ver_notas', 'True')),
                            puede_ver_asistencia=ImportacionCSVService._parsear_booleano(fila.get('puede_ver_asistencia', 'True')),
                            puede_recibir_comunicados=ImportacionCSVService._parsear_booleano(fila.get('puede_recibir_comunicados', 'True')),
                            puede_firmar_citaciones=ImportacionCSVService._parsear_booleano(fila.get('puede_firmar_citaciones', 'True')),
                            puede_autorizar_salidas=ImportacionCSVService._parsear_booleano(fila.get('puede_autorizar_salidas', 'False')),
                            puede_ver_tareas=ImportacionCSVService._parsear_booleano(fila.get('puede_ver_tareas', 'True')),
                            puede_ver_materiales=ImportacionCSVService._parsear_booleano(fila.get('puede_ver_materiales', 'True')),
                            activo=True,
                            observaciones=fila.get('observaciones', '').strip() or None
                        )

                        exitosos += 1

                except Exception as e:
                    errores.append(f"Fila {idx}: Error al procesar - {str(e)}")
                    fallidos += 1

        except UnicodeDecodeError:
            errores.append("Error al leer el archivo. Asegúrate de que esté codificado en UTF-8")
        except Exception as e:
            errores.append(f"Error general al procesar el archivo: {str(e)}")

        return exitosos, fallidos, errores

    @staticmethod
    def generar_plantilla_estudiantes() -> str:
        """Genera plantilla CSV de ejemplo para estudiantes."""
        plantilla = (
            "email,nombre,apellido_paterno,apellido_materno,rut,password,fecha_nacimiento,direccion,telefono,"
            "telefono_movil,contacto_emergencia_nombre,contacto_emergencia_relacion,contacto_emergencia_telefono,"
            "grupo_sanguineo,alergias,condiciones_medicas,tiene_nee,tipo_nee,descripcion_nee,requiere_pie,"
            "fecha_ingreso,estado_academico,observaciones\n"
            "juan.perez@ejemplo.cl,Juan,Pérez,González,12345678-9,ContraseñaSegura123,2010-05-15,"
            "Calle Ejemplo 123,+56912345678,+56912345678,María González,Madre,+56987654321,O+,"
            "Ninguna,Ninguna,False,,,False,2024-03-01,Activo,Estudiante de ejemplo\n"
            "maria.silva@ejemplo.cl,María,Silva,Rodriguez,98765432-1,OtraContraseña456,2011-08-20,"
            "Avenida Principal 456,+56923456789,+56923456789,Pedro Silva,Padre,+56976543210,A+,"
            "Polen,Asma leve,True,TEL,Trastorno específico del lenguaje,True,2024-03-01,Activo,Requiere apoyo PIE"
        )
        return plantilla

    @staticmethod
    def generar_plantilla_profesores() -> str:
        """Genera plantilla CSV de ejemplo para profesores."""
        plantilla = (
            "email,nombre,apellido_paterno,apellido_materno,rut,password,fecha_nacimiento,direccion,telefono,"
            "telefono_movil,especialidad,titulo_profesional,universidad,anio_titulacion,fecha_ingreso,"
            "estado_laboral,horas_semanales_contrato,horas_no_lectivas,observaciones\n"
            "carlos.martinez@ejemplo.cl,Carlos,Martínez,López,11222333-4,ProfesorSeguro123,1985-03-10,"
            "Calle Docente 789,+56934567890,+56934567890,Matemáticas,Profesor de Matemáticas,"
            "Universidad de Chile,2008,2024-03-01,Activo,44,8,Profesor jefe 5°A\n"
            "ana.rodriguez@ejemplo.cl,Ana,Rodríguez,Fernández,55666777-8,OtraClaveProfe456,1990-11-25,"
            "Avenida Educación 321,+56945678901,+56945678901,Lenguaje y Comunicación,"
            "Profesora de Lenguaje,Pontificia Universidad Católica,2013,2024-03-01,Activo,44,10,"
            "Coordinadora de departamento"
        )
        return plantilla

    @staticmethod
    def generar_plantilla_apoderados() -> str:
        """Genera plantilla CSV de ejemplo para apoderados."""
        plantilla = (
            "email,nombre,apellido_paterno,apellido_materno,rut,password,fecha_nacimiento,direccion,telefono,"
            "telefono_movil,ocupacion,lugar_trabajo,telefono_trabajo,puede_ver_notas,puede_ver_asistencia,"
            "puede_recibir_comunicados,puede_firmar_citaciones,puede_autorizar_salidas,puede_ver_tareas,"
            "puede_ver_materiales,observaciones\n"
            "ricardo.gomez@ejemplo.cl,Ricardo,Gómez,Pinto,22333444-5,ApoderadoSeguro123,1980-06-15,"
            "Calle Familia 456,+56956789012,+56956789012,Ingeniero,Empresa XYZ,+56222334455,"
            "True,True,True,True,False,True,True,Apoderado principal de 2 estudiantes\n"
            "patricia.castro@ejemplo.cl,Patricia,Castro,Muñoz,77888999-0,OtraClaveApod456,1982-09-30,"
            "Avenida Hogar 789,+56967890123,+56967890123,Contadora,Consultora ABC,+56233445566,"
            "True,True,True,True,True,True,True,Apoderado secundario"
        )
        return plantilla


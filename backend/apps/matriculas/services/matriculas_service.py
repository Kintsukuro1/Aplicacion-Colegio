"""
MatriculasService - Servicio para gestión de matrículas y pagos

Este servicio centraliza la lógica de negocio para:
- Obtener matrículas activas de estudiantes
- Gestionar relaciones apoderado-estudiante
- Calcular estados de cuenta y totales
- Obtener historial de pagos
- Verificar permisos de acceso
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from django.db import transaction
from django.db.models import Sum, Q
from django.core.exceptions import ObjectDoesNotExist

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.common.exceptions import PrerequisiteException
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('matriculas')


class MatriculasService:
    """
    Servicio para gestión completa de matrículas y pagos
    """

    @staticmethod
    def _has_profile(user, profile_attr: str) -> bool:
        try:
            return getattr(user, profile_attr, None) is not None
        except (ObjectDoesNotExist, AttributeError):
            return False

    @staticmethod
    def _is_student_or_apoderado(user) -> bool:
        return MatriculasService._has_profile(user, 'perfil_estudiante') or MatriculasService._has_profile(user, 'perfil_apoderado')

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        """
        Punto de entrada estándar para operaciones del servicio.

        Patrón fase 3.1:
        1) validate
        2) _execute
        """
        MatriculasService.validate(operation, params)
        return MatriculasService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        """Valida parámetros mínimos requeridos por operación."""
        if operation == 'create':
            if params.get('estudiante_id') is None:
                raise ValueError('Parámetro requerido: estudiante_id')
            if params.get('colegio_rbd') is None:
                raise ValueError('Parámetro requerido: colegio_rbd')
            return

        if operation == 'change_status':
            if params.get('matricula_id') is None:
                raise ValueError('Parámetro requerido: matricula_id')
            if not params.get('new_status'):
                raise ValueError('Parámetro requerido: new_status')
            return

        if operation == 'delete':
            if params.get('matricula_id') is None:
                raise ValueError('Parámetro requerido: matricula_id')
            return

        if operation == 'get_active_matricula_for_user':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('escuela_rbd') is None:
                raise ValueError('Parámetro requerido: escuela_rbd')
            return

        if operation in ['get_estado_cuenta_data', 'get_pagos_data']:
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            return

        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        """Despacha la ejecución de operaciones del servicio."""
        if operation == 'create':
            return MatriculasService._execute_create(params)
        if operation == 'change_status':
            return MatriculasService._execute_change_status(params)
        if operation == 'delete':
            return MatriculasService._execute_delete(params)
        if operation == 'get_active_matricula_for_user':
            return MatriculasService._execute_get_active_matricula_for_user(params)
        if operation == 'get_estado_cuenta_data':
            return MatriculasService._execute_get_estado_cuenta_data(params)
        if operation == 'get_pagos_data':
            return MatriculasService._execute_get_pagos_data(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def create(
        actor,
        estudiante_id: int,
        colegio_rbd: int,
        curso_id: Optional[int] = None,
        ciclo_academico_id: Optional[int] = None,
        valor_matricula: int = 0,
        valor_mensual: int = 0,
        observaciones: Optional[str] = None,
    ):
        return MatriculasService.execute('create', {
            'actor': actor,
            'estudiante_id': estudiante_id,
            'colegio_rbd': colegio_rbd,
            'curso_id': curso_id,
            'ciclo_academico_id': ciclo_academico_id,
            'valor_matricula': valor_matricula,
            'valor_mensual': valor_mensual,
            'observaciones': observaciones,
        })

    @staticmethod
    def _execute_create(params: Dict[str, Any]):
        from backend.apps.accounts.models import User
        from backend.apps.cursos.models import Curso
        from backend.apps.institucion.models import Colegio, CicloAcademico
        from ..models import Matricula

        colegio_rbd = int(params['colegio_rbd'])
        MatriculasService._validate_school_integrity(colegio_rbd, 'MATRICULA_CREATE')

        estudiante = User.objects.get(id=params['estudiante_id'])
        if estudiante.rbd_colegio is not None and int(estudiante.rbd_colegio) != colegio_rbd:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Matricula',
                    'related_entity': 'Estudiante',
                    'message': 'El estudiante no pertenece al colegio seleccionado.',
                }
            )

        colegio = Colegio.objects.get(rbd=colegio_rbd)
        ciclo_id = params.get('ciclo_academico_id')
        if ciclo_id:
            ciclo = CicloAcademico.objects.get(id=ciclo_id)
        else:
            ciclo = (
                CicloAcademico.objects.filter(colegio_id=colegio_rbd, estado='ACTIVO')
                .order_by('-fecha_inicio', '-id')
                .first()
            )
            if ciclo is None:
                raise PrerequisiteException(
                    error_type='MISSING_CICLO_ACTIVO',
                    context={
                        'colegio_rbd': colegio_rbd,
                        'message': 'No hay ciclo académico activo para crear matrícula.',
                    }
                )

        curso = None
        if params.get('curso_id'):
            curso = Curso.objects.get(id_curso=params['curso_id'])

        with transaction.atomic():
            return Matricula.objects.create(
                estudiante=estudiante,
                colegio=colegio,
                curso=curso,
                ciclo_academico=ciclo,
                estado='ACTIVA',
                valor_matricula=params.get('valor_matricula', 0),
                valor_mensual=params.get('valor_mensual', 0),
                observaciones=params.get('observaciones'),
            )

    @staticmethod
    def change_status(actor, matricula_id: int, new_status: str):
        return MatriculasService.execute('change_status', {
            'actor': actor,
            'matricula_id': matricula_id,
            'new_status': new_status,
        })

    @staticmethod
    def _execute_change_status(params: Dict[str, Any]):
        from ..models import Matricula

        valid_status = {'ACTIVA', 'SUSPENDIDA', 'RETIRADA', 'FINALIZADA'}
        new_status = str(params['new_status']).upper()
        if new_status not in valid_status:
            raise ValueError('Estado de matrícula inválido')

        matricula = Matricula.objects.select_related('colegio', 'ciclo_academico').get(id=params['matricula_id'])
        MatriculasService._validate_school_integrity(matricula.colegio_id, 'MATRICULA_CHANGE_STATUS')

        if new_status == 'ACTIVA':
            duplicada = Matricula.objects.filter(
                estudiante_id=matricula.estudiante_id,
                ciclo_academico_id=matricula.ciclo_academico_id,
                estado='ACTIVA',
            ).exclude(id=matricula.id)
            if duplicada.exists():
                raise PrerequisiteException(
                    error_type='DUPLICATE_ACTIVE_MATRICULA',
                    context={
                        'estudiante_id': matricula.estudiante_id,
                        'ciclo_academico_id': matricula.ciclo_academico_id,
                        'message': 'Ya existe una matrícula activa para el estudiante en el ciclo.',
                    }
                )

        matricula.estado = new_status
        matricula.save(update_fields=['estado'])
        return matricula

    @staticmethod
    def delete(actor, matricula_id: int) -> None:
        MatriculasService.execute('delete', {
            'actor': actor,
            'matricula_id': matricula_id,
        })

    @staticmethod
    def _execute_delete(params: Dict[str, Any]) -> None:
        from ..models import Matricula

        matricula = Matricula.objects.select_related('colegio').get(id=params['matricula_id'])
        MatriculasService._validate_school_integrity(matricula.colegio_id, 'MATRICULA_DELETE')

        if matricula.estado == 'ACTIVA':
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'matricula_id': matricula.id,
                    'message': 'No se puede eliminar una matrícula activa; cambie su estado primero.',
                }
            )

        matricula.delete()

    @staticmethod
    def _validate_student_profile(user) -> None:
        """
        Valida que el estudiante tenga perfil activo.
        
        Args:
            user: Usuario estudiante
        
        Raises:
            PrerequisiteException: Si el estudiante no tiene perfil válido
        """
        from backend.apps.accounts.models import PerfilEstudiante
        
        if not hasattr(user, 'perfil_estudiante'):
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'entity': 'Estudiante',
                    'field': 'perfil_estudiante',
                    'user_id': user.id,
                    'message': 'El estudiante no tiene un perfil registrado.',
                    'action': 'Contacte al administrador.'
                }
            )

    @staticmethod
    def _validate_colegio_has_active_ciclo(escuela_rbd: int) -> Any:
        """
        Valida que el colegio tenga un ciclo académico activo.
        
        Args:
            escuela_rbd: RBD del colegio
            
        Returns:
            CicloAcademico: El ciclo activo
        
        Raises:
            PrerequisiteException: Si el colegio no existe o no tiene ciclo activo
        """
        from backend.apps.institucion.models import CicloAcademico, Colegio
        
        # Verificar que el colegio existe
        try:
            colegio = Colegio.objects.get(rbd=escuela_rbd)
        except Colegio.DoesNotExist:
            raise PrerequisiteException(
                error_type='SCHOOL_NOT_CONFIGURED',
                context={
                    'rbd': escuela_rbd,
                    'message': f'No se encontró el colegio con RBD {escuela_rbd}'
                }
            )
        
        # Verificar que tiene ciclo activo
        try:
            ciclo_activo = CicloAcademico.objects.get(
                colegio_id=escuela_rbd,
                estado='ACTIVO'
            )
            return ciclo_activo
        except CicloAcademico.DoesNotExist:
            raise PrerequisiteException(
                error_type='MISSING_CICLO_ACTIVO',
                context={
                    'colegio_rbd': escuela_rbd,
                    'colegio_nombre': colegio.nombre,
                    'message': f'El colegio {colegio.nombre} no tiene un ciclo académico activo'
                }
            )

    @staticmethod
    def _validate_colegio_has_active_ciclo(escuela_rbd: int) -> Any:  # type: ignore[override]
        """
        Override defensivo:
        - evita MultipleObjectsReturned cuando hay más de un ciclo ACTIVO;
        - selecciona el más reciente por fecha_inicio.
        """
        from backend.apps.institucion.models import CicloAcademico, Colegio

        try:
            colegio = Colegio.objects.get(rbd=escuela_rbd)
        except Colegio.DoesNotExist:
            raise PrerequisiteException(
                error_type='SCHOOL_NOT_CONFIGURED',
                context={
                    'rbd': escuela_rbd,
                    'message': f'No se encontrÃ³ el colegio con RBD {escuela_rbd}'
                }
            )

        ciclo_activo = (
            CicloAcademico.objects.filter(
                colegio_id=escuela_rbd,
                estado='ACTIVO'
            )
            .order_by('-fecha_inicio', '-id')
            .first()
        )
        if ciclo_activo is None:
            raise PrerequisiteException(
                error_type='MISSING_CICLO_ACTIVO',
                context={
                    'colegio_rbd': escuela_rbd,
                    'colegio_nombre': colegio.nombre,
                    'message': f'El colegio {colegio.nombre} no tiene un ciclo acadÃ©mico activo'
                }
            )
        return ciclo_activo

    @staticmethod
    def _validate_school_integrity(escuela_rbd: int, action: str) -> None:
        """Valida integridad estructural antes de ejecutar lógica de negocio."""
        IntegrityService.validate_school_integrity_or_raise(
            school_id=escuela_rbd,
            action=action,
        )

    @staticmethod
    def get_active_matricula_for_user(user, escuela_rbd: int) -> Optional[Any]:
        return MatriculasService.execute('get_active_matricula_for_user', {
            'user': user,
            'escuela_rbd': escuela_rbd,
        })

    @staticmethod
    def _execute_get_active_matricula_for_user(params: Dict[str, Any]) -> Optional[Any]:
        """
        Obtiene la matrícula activa para un usuario (estudiante).
        Prioriza matrícula del año actual; si no existe, usa la más reciente activa.

        Args:
            user: Usuario estudiante
            escuela_rbd: ID del colegio

        Returns:
            Matricula or None: La matrícula activa encontrada
        
        Raises:
            PrerequisiteException: Si no tiene perfil válido o colegio sin ciclo activo
        """
        from ..models import Matricula

        user = params['user']
        escuela_rbd = params['escuela_rbd']

        # VALIDACIÓN DEFENSIVA: Verificar perfil del estudiante
        MatriculasService._validate_student_profile(user)

        # VALIDACIÓN DEFENSIVA: Verificar ciclo activo del colegio (propaga errores)
        ciclo_actual = MatriculasService._validate_colegio_has_active_ciclo(escuela_rbd)

        # VALIDACIÓN OBLIGATORIA: Integridad de dominio
        try:
            MatriculasService._validate_school_integrity(
                escuela_rbd,
                action='GET_ACTIVE_MATRICULA_FOR_USER'
            )
        except PrerequisiteException:
            return None
            
        qs = Matricula.objects.filter(
            estudiante=user, 
            colegio_id=escuela_rbd, 
            estado='ACTIVA'
        )

        # Primero intentar matrícula del ciclo actual
        matricula = qs.filter(ciclo_academico=ciclo_actual).order_by('-fecha_matricula').first()
        if matricula:
            return matricula

        # Si no, la más reciente de ciclos anteriores
        return qs.filter(ciclo_academico__fecha_fin__lt=ciclo_actual.fecha_inicio).order_by('-ciclo_academico__fecha_fin', '-fecha_matricula').first()

    @staticmethod
    def get_apoderado_estudiantes(user) -> Tuple[Optional[Any], List[Any]]:
        """
        Obtiene los estudiantes asociados a un apoderado

        Args:
            user: Usuario apoderado

        Returns:
            Tuple: (apoderado, lista_de_estudiantes)
        """
        from backend.apps.accounts.models import Apoderado, RelacionApoderadoEstudiante

        try:
            apoderado = Apoderado.objects.get(user=user)
        except Apoderado.DoesNotExist:
            return None, []

        relaciones = (
            RelacionApoderadoEstudiante.objects.filter(apoderado=apoderado, activa=True)
            .select_related('estudiante')
            .order_by('prioridad_contacto', 'estudiante__apellido_paterno', 'estudiante__nombre')
        )
        estudiantes = [rel.estudiante for rel in relaciones]
        return apoderado, estudiantes

    @staticmethod
    def apoderado_puede_ver_estudiante(apoderado, estudiante) -> bool:
        """
        Verifica si un apoderado puede ver información de un estudiante

        Args:
            apoderado: Instancia del modelo Apoderado
            estudiante: Instancia del modelo User (estudiante)

        Returns:
            bool: True si tiene permiso
        """
        from backend.apps.accounts.models import RelacionApoderadoEstudiante

        return RelacionApoderadoEstudiante.objects.filter(
            apoderado=apoderado,
            estudiante=estudiante,
            activa=True,
        ).exists()

    @staticmethod
    def get_estado_cuenta_data(user, estudiante_seleccionado=None) -> Dict[str, Any]:
        return MatriculasService.execute('get_estado_cuenta_data', {
            'user': user,
            'estudiante_seleccionado': estudiante_seleccionado,
        })

    @staticmethod
    def _execute_get_estado_cuenta_data(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene todos los datos necesarios para mostrar el estado de cuenta

        Args:
            user: Usuario que hace la consulta (estudiante o apoderado)
            estudiante_seleccionado: Estudiante específico (para apoderados)

        Returns:
            Dict: Datos del estado de cuenta o {'error': mensaje}
        """
        from ..models import Cuota

        user = params['user']
        estudiante_seleccionado = params.get('estudiante_seleccionado')

        if not MatriculasService._is_student_or_apoderado(user):
            return {'error': 'No tienes permisos para ver esta página.'}

        # Determinar estudiante objetivo
        estudiante_obj = estudiante_seleccionado or user
        escuela_rbd = estudiante_obj.rbd_colegio

        if not escuela_rbd:
            return {'error': 'El estudiante no tiene colegio asignado.'}

        # VALIDACIÓN DEFENSIVA: Verificar perfil del estudiante
        try:
            MatriculasService._validate_student_profile(estudiante_obj)
        except PrerequisiteException as e:
            return {'error': e.context.get('message', 'El estudiante no tiene un perfil válido.')}

        # VALIDACIÓN DEFENSIVA: Verificar ciclo activo del colegio
        try:
            ciclo_activo = MatriculasService._validate_colegio_has_active_ciclo(escuela_rbd)
        except PrerequisiteException as e:
            return {'error': e.context.get('message', 'El colegio no tiene un ciclo académico activo.')}

        # VALIDACIÓN OBLIGATORIA: Integridad de dominio
        try:
            MatriculasService._validate_school_integrity(
                escuela_rbd,
                action='GET_ESTADO_CUENTA_DATA'
            )
        except PrerequisiteException as e:
            return {'error': e.context.get('message', 'Se detectaron inconsistencias en los datos del colegio.')}

        # Obtener matrícula activa
        matricula = MatriculasService.get_active_matricula_for_user(estudiante_obj, escuela_rbd)
        if not matricula:
            return {'error': f'No se encontró una matrícula activa para {estudiante_obj.get_full_name()}.'}

        # VALIDACIÓN DEFENSIVA: Verificar que la matrícula corresponde al ciclo activo
        if matricula.ciclo_academico != ciclo_activo:
            logger.warning(
                f"Matrícula {matricula.id_matricula} del estudiante {estudiante_obj.id} "
                f"corresponde a ciclo {matricula.ciclo_academico.nombre} pero el ciclo activo es {ciclo_activo.nombre}"
            )
            # Permitir ver datos históricos pero advertir
            
        # Obtener cuotas con query explícita para evitar inconsistencias del reverse manager tenant-aware
        cuotas = Cuota.objects.filter(
            matricula=matricula,
            matricula__colegio_id=escuela_rbd,
        ).order_by('anio', 'mes', 'numero_cuota')

        # Calcular totales
        total_arancel = cuotas.aggregate(total=Sum('monto_original'))['total'] or 0
        total_descuentos = cuotas.aggregate(total=Sum('monto_descuento'))['total'] or 0
        total_a_pagar = cuotas.aggregate(total=Sum('monto_final'))['total'] or 0
        total_pagado = cuotas.aggregate(total=Sum('monto_pagado'))['total'] or 0
        saldo_pendiente = total_a_pagar - total_pagado
        cuotas_vencidas = cuotas.filter(estado__in=['VENCIDA', 'PAGADA_PARCIAL']).count()

        return {
            'matricula': matricula,
            'cuotas': cuotas,
            'estudiante': estudiante_obj,
            'totales': {
                'total_arancel': total_arancel,
                'total_descuentos': total_descuentos,
                'total_a_pagar': total_a_pagar,
                'total_pagado': total_pagado,
                'saldo_pendiente': saldo_pendiente,
                'cuotas_vencidas': cuotas_vencidas,
            },
        }

    @staticmethod
    def get_pagos_data(user, estudiante_seleccionado=None) -> Dict[str, Any]:
        return MatriculasService.execute('get_pagos_data', {
            'user': user,
            'estudiante_seleccionado': estudiante_seleccionado,
        })

    @staticmethod
    def _execute_get_pagos_data(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene todos los datos necesarios para mostrar el historial de pagos

        Args:
            user: Usuario que hace la consulta (estudiante o apoderado)
            estudiante_seleccionado: Estudiante específico (para apoderados)

        Returns:
            Dict: Datos de pagos o {'error': mensaje}
        """
        from ..models import Pago

        user = params['user']
        estudiante_seleccionado = params.get('estudiante_seleccionado')

        if not MatriculasService._is_student_or_apoderado(user):
            return {'error': 'No tienes permisos para ver esta página.'}

        # Determinar estudiante objetivo
        estudiante_obj = estudiante_seleccionado or user
        escuela_rbd = estudiante_obj.rbd_colegio

        if not escuela_rbd:
            return {'error': 'El estudiante no tiene colegio asignado.'}

        # VALIDACIÓN DEFENSIVA: Verificar perfil del estudiante
        try:
            MatriculasService._validate_student_profile(estudiante_obj)
        except PrerequisiteException as e:
            return {'error': e.context.get('message', 'El estudiante no tiene un perfil válido.')}

        # VALIDACIÓN DEFENSIVA: Verificar ciclo activo del colegio
        try:
            ciclo_activo = MatriculasService._validate_colegio_has_active_ciclo(escuela_rbd)
        except PrerequisiteException as e:
            return {'error': e.context.get('message', 'El colegio no tiene un ciclo académico activo.')}

        # VALIDACIÓN OBLIGATORIA: Integridad de dominio
        try:
            MatriculasService._validate_school_integrity(
                escuela_rbd,
                action='GET_PAGOS_DATA'
            )
        except PrerequisiteException as e:
            return {'error': e.context.get('message', 'Se detectaron inconsistencias en los datos del colegio.')}

        # Obtener pagos del ciclo activo prioritariamente
        pagos = (
            Pago.objects.filter(
                estudiante=estudiante_obj, 
                cuota__matricula__colegio_id=escuela_rbd,
                cuota__matricula__ciclo_academico=ciclo_activo
            )
            .select_related('cuota', 'cuota__matricula')
            .order_by('-fecha_pago')
        )

        total_pagado = pagos.aggregate(total=Sum('monto'))['total'] or 0

        return {
            'pagos': pagos,
            'total_pagado': total_pagado,
            'estudiante': estudiante_obj,
        }

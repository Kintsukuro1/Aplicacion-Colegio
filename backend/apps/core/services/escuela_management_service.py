"""
Escuela Management Service - Lógica de negocio para gestión de colegios por administradores generales.

Extraído de backend/apps/core/views/seleccionar_escuela.py para separar responsabilidades.
"""

from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from typing import List, Dict, Any

from backend.apps.institucion.models import (
    Colegio, Region, Comuna, TipoEstablecimiento,
    DependenciaAdministrativa, ColegioInfraestructura, TipoInfraestructura, CicloAcademico
)
from backend.apps.subscriptions.models import Plan
from backend.apps.subscriptions.services.subscription_service import SubscriptionService
from backend.apps.accounts.models import User
from backend.apps.accounts.services.user_service import UserService
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.services import PermissionService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.error_response import ErrorResponseBuilder


class EscuelaManagementService:
    """Servicio para gestión de colegios."""

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]):
        EscuelaManagementService.validate(operation, params)
        return EscuelaManagementService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        if params.get('user') is None:
            raise ValueError('Parámetro requerido: user')

        if operation in ['crear_colegio', 'crear_admin_escolar'] and params.get('data') is None:
            raise ValueError('Parámetro requerido: data')

        if operation in ['eliminar_colegio', 'entrar_escuela'] and params.get('rbd') is None:
            raise ValueError('Parámetro requerido: rbd')

        if operation == 'cambiar_plan_colegio':
            if params.get('rbd') is None:
                raise ValueError('Parámetro requerido: rbd')
            if params.get('plan_codigo') is None:
                raise ValueError('Parámetro requerido: plan_codigo')

        if operation not in [
            'crear_colegio',
            'crear_admin_escolar',
            'eliminar_colegio',
            'cambiar_plan_colegio',
            'obtener_datos_seleccionar_escuela',
            'entrar_escuela',
        ]:
            raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]):
        if operation == 'crear_colegio':
            return EscuelaManagementService._execute_crear_colegio(params)
        if operation == 'crear_admin_escolar':
            return EscuelaManagementService._execute_crear_admin_escolar(params)
        if operation == 'eliminar_colegio':
            return EscuelaManagementService._execute_eliminar_colegio(params)
        if operation == 'cambiar_plan_colegio':
            return EscuelaManagementService._execute_cambiar_plan_colegio(params)
        if operation == 'obtener_datos_seleccionar_escuela':
            return EscuelaManagementService._execute_obtener_datos_seleccionar_escuela(params)
        if operation == 'entrar_escuela':
            return EscuelaManagementService._execute_entrar_escuela(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(rbd_colegio: int, action: str) -> None:
        """Valida integridad del colegio antes de operaciones críticas."""
        IntegrityService.validate_school_integrity_or_raise(
            school_id=rbd_colegio,
            action=action,
        )

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_SYSTEM')
    def crear_colegio(user, data: Dict[str, Any]) -> Colegio:
        return EscuelaManagementService.execute('crear_colegio', {
            'user': user,
            'data': data,
        })

    @staticmethod
    def _execute_crear_colegio(params: Dict[str, Any]) -> Colegio:
        """Crear un nuevo colegio con infraestructura si es presencial.
        
        Raises:
            PrerequisiteException: Si hay datos duplicados o inválidos
        """
        data = params['data']

        with transaction.atomic():
            # VALIDACIÓN DEFENSIVA: Verificar que RBD no exista
            if Colegio.objects.filter(rbd=data['rbd']).exists():
                raise PrerequisiteException(
                    error_type='VALIDATION_ERROR',
                    user_message=f"Ya existe un colegio con RBD {data['rbd']}",
                    context={'rbd': data['rbd']}
                )
            
            # VALIDACIÓN DEFENSIVA: Verificar que RUT no exista
            if Colegio.objects.filter(rut_establecimiento=data['rut_establecimiento']).exists():
                raise PrerequisiteException(
                    error_type='VALIDATION_ERROR',
                    user_message=f"Ya existe un colegio con RUT {data['rut_establecimiento']}",
                    context={'rut_establecimiento': data['rut_establecimiento']}
                )
            
            tipo = get_object_or_404(TipoEstablecimiento, id_tipo_establecimiento=data['tipo_establecimiento'])

            colegio = Colegio.objects.create(
                rbd=data['rbd'],
                nombre=data['nombre'],
                rut_establecimiento=data['rut_establecimiento'],
                tipo_establecimiento=tipo,
                dependencia_id=data['dependencia'],
                comuna_id=data['comuna_id'],
                direccion=data['direccion'],
                telefono=data.get('telefono', ''),
                correo=data.get('email', ''),
                web=data.get('web', ''),
                capacidad_maxima=data.get('capacidad_maxima', 1000),
            )

            # Infraestructura si es presencial
            if tipo.nombre == 'Presencial':
                infra_data = {
                    'Salas de Clases': data.get('infra_salas', 0),
                    'Laboratorio de Computación': data.get('infra_laboratorio', 0),
                    'Biblioteca': data.get('infra_biblioteca', 0),
                    'Gimnasio': data.get('infra_gimnasio', 0),
                    'Comedor': data.get('infra_comedor', 0),
                }

                for tipo_nombre, cantidad in infra_data.items():
                    if int(cantidad) > 0:
                        tipo_infra, _ = TipoInfraestructura.objects.get_or_create(nombre=tipo_nombre)
                        ColegioInfraestructura.objects.create(
                            colegio=colegio,
                            tipo_infra=tipo_infra,
                            cantidad=int(cantidad)
                        )

            return colegio

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_SYSTEM')
    def crear_admin_escolar(user, data: Dict[str, Any]) -> User:
        return EscuelaManagementService.execute('crear_admin_escolar', {
            'user': user,
            'data': data,
        })

    @staticmethod
    def _execute_crear_admin_escolar(params: Dict[str, Any]) -> User:
        """Crear administrador escolar para un colegio.
        
        Raises:
            PrerequisiteException: Si hay datos duplicados o colegio sin ciclo activo
        """
        data = params['data']

        with transaction.atomic():
            colegio = get_object_or_404(Colegio, rbd=data['rbd_admin'])

            EscuelaManagementService._validate_school_integrity(
                rbd_colegio=colegio.rbd,
                action='CREAR_ADMIN_ESCOLAR'
            )
            
            # VALIDACIÓN DEFENSIVA: Verificar que el colegio tenga ciclo activo
            ciclo_activo = CicloAcademico.objects.filter(colegio=colegio, estado='ACTIVO').first()
            if not ciclo_activo:
                raise PrerequisiteException(
                    error_type='MISSING_CICLO_ACTIVO',
                    user_message=f'El colegio {colegio.nombre} no tiene un ciclo académico activo. Debe crear uno antes de agregar administradores.',
                    action_url='/admin/institucion/cicloacademico/add/',
                    context={'rbd_colegio': colegio.rbd, 'colegio_nombre': colegio.nombre}
                )
            
            # VALIDACIÓN DEFENSIVA: Verificar que email no exista
            if User.objects.filter(email=data['email_admin']).exists():
                raise PrerequisiteException(
                    error_type='VALIDATION_ERROR',
                    user_message=f"Ya existe un usuario con el email {data['email_admin']}",
                    context={'email': data['email_admin']}
                )
            
            # VALIDACIÓN DEFENSIVA: Verificar que RUT no exista
            if data.get('rut_admin') and User.objects.filter(rut=data['rut_admin']).exists():
                raise PrerequisiteException(
                    error_type='VALIDATION_ERROR',
                    user_message=f"Ya existe un usuario con RUT {data['rut_admin']}",
                    context={'rut': data['rut_admin']}
                )
            
            usuario = UserService.create_user(
                actor=params.get('user'),
                email=data['email_admin'],
                role_name='Administrador escolar',
                nombre=data['nombre_admin'],
                apellido_paterno=data['apellido_paterno_admin'],
                apellido_materno=data.get('apellido_materno_admin', ''),
                password=data['contrasena_admin'],
                rut=data.get('rut_admin'),
                rbd_colegio=colegio.rbd,
                is_active=True,
            )

            return usuario

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_SYSTEM')
    def eliminar_colegio(user, rbd: str) -> str:
        return EscuelaManagementService.execute('eliminar_colegio', {
            'user': user,
            'rbd': rbd,
        })

    @staticmethod
    def _execute_eliminar_colegio(params: Dict[str, Any]) -> str:
        """Eliminar un colegio.
        
        Raises:
            PrerequisiteException: Si el colegio tiene usuarios activos o ciclos activos
        """
        rbd = params['rbd']

        with transaction.atomic():
            colegio = get_object_or_404(Colegio, rbd=rbd)

            EscuelaManagementService._validate_school_integrity(
                rbd_colegio=colegio.rbd,
                action='ELIMINAR_COLEGIO'
            )
            
            # VALIDACIÓN DEFENSIVA: Verificar que no tenga usuarios activos
            usuarios_activos = User.objects.filter(rbd_colegio=rbd, is_active=True).count()
            if usuarios_activos > 0:
                raise PrerequisiteException(
                    error_type='INVALID_STATE',
                    user_message=f'No se puede eliminar el colegio {colegio.nombre}: tiene {usuarios_activos} usuario(s) activo(s)',
                    context={'rbd': rbd, 'usuarios_activos': usuarios_activos}
                )
            
            # VALIDACIÓN DEFENSIVA: Verificar que no tenga ciclos académicos activos
            ciclos_activos = CicloAcademico.objects.filter(colegio=colegio, estado='ACTIVO').count()
            if ciclos_activos > 0:
                raise PrerequisiteException(
                    error_type='INVALID_STATE',
                    user_message=f'No se puede eliminar el colegio {colegio.nombre}: tiene {ciclos_activos} ciclo(s) académico(s) activo(s). Ciérrelos primero.',
                    action_url='/admin/institucion/cicloacademico/',
                    context={'rbd': rbd, 'ciclos_activos': ciclos_activos}
                )
            
            nombre = colegio.nombre
            try:
                colegio.delete()
            except ProtectedError as exc:
                raise PrerequisiteException(
                    error_type='INVALID_STATE',
                    user_message=(
                        f'No se puede eliminar el colegio {colegio.nombre}: '
                        'existen registros protegidos asociados.'
                    ),
                    context={
                        'rbd': rbd,
                        'error': str(exc)
                    }
                )
            return nombre

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'MANAGE_SYSTEM')
    def cambiar_plan_colegio(user, rbd: str, plan_codigo: str) -> tuple[Colegio, Plan]:
        return EscuelaManagementService.execute('cambiar_plan_colegio', {
            'user': user,
            'rbd': rbd,
            'plan_codigo': plan_codigo,
        })

    @staticmethod
    def _execute_cambiar_plan_colegio(params: Dict[str, Any]) -> tuple[Colegio, Plan]:
        """Cambiar el plan de suscripción de un colegio."""
        rbd = params['rbd']
        plan_codigo = params['plan_codigo']

        with transaction.atomic():
            colegio = get_object_or_404(Colegio, rbd=rbd)
            plan = get_object_or_404(Plan, codigo=plan_codigo)

            EscuelaManagementService._validate_school_integrity(
                rbd_colegio=colegio.rbd,
                action='CAMBIAR_PLAN_COLEGIO'
            )

            SubscriptionService.upsert_school_subscription(
                colegio_rbd=colegio.rbd,
                plan_codigo=plan.codigo,
            )

            return colegio, plan

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'VIEW_REPORTS')
    def obtener_datos_seleccionar_escuela(user) -> Dict[str, Any]:
        return EscuelaManagementService.execute('obtener_datos_seleccionar_escuela', {
            'user': user,
        })

    @staticmethod
    def _execute_obtener_datos_seleccionar_escuela(params: Dict[str, Any]) -> Dict[str, Any]:
        """Obtener datos para la vista de selección de escuela."""
        escuelas = Colegio.objects.select_related(
            'comuna__region',
            'tipo_establecimiento',
            'dependencia',
            'subscription',
            'subscription__plan'
        ).all().order_by('nombre')

        # Agregar info de suscripción
        for escuela in escuelas:
            try:
                if hasattr(escuela, 'subscription') and escuela.subscription:
                    subscription = escuela.subscription
                    escuela.subscription_info = {
                        'plan': subscription.plan,
                        'status': subscription.status,
                        'get_status_display': subscription.get_status_display(),
                        'dias_restantes': (subscription.fecha_fin - timezone.now().date()).days if subscription.fecha_fin else 0,
                    }
                else:
                    escuela.subscription_info = None
            except Exception:
                escuela.subscription_info = None

        planes = Plan.objects.all().order_by('orden_visualizacion')
        regiones = Region.objects.all().order_by('nombre')
        comunas = Comuna.objects.select_related('region').all().order_by('nombre')
        tipos_establecimiento = TipoEstablecimiento.objects.all().order_by('nombre')
        dependencias = DependenciaAdministrativa.objects.all().order_by('nombre')

        comunas_data = [
            {
                'id_comuna': c.id_comuna,
                'nombre': c.nombre,
                'region_id': c.region.id_region if c.region else None
            }
            for c in comunas
        ]

        return {
            'escuelas': escuelas,
            'planes': planes,
            'regiones': regiones,
            'comunas': comunas,
            'comunas_data': comunas_data,
            'tipos_establecimiento': tipos_establecimiento,
            'dependencias': dependencias,
        }

    @staticmethod
    @PermissionService.require_permission('ADMINISTRATIVO', 'VIEW_REPORTS')
    def entrar_escuela(user, rbd: str) -> Colegio:
        return EscuelaManagementService.execute('entrar_escuela', {
            'user': user,
            'rbd': rbd,
        })

    @staticmethod
    def _execute_entrar_escuela(params: Dict[str, Any]) -> Colegio:
        """Obtener colegio para entrar como admin general."""
        rbd = params['rbd']
        return get_object_or_404(Colegio, rbd=rbd)
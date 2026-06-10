"""
Validaciones comunes reutilizables para services.

Este módulo contiene validaciones que se repiten en múltiples services
para mantener consistencia y reducir duplicación de código.
"""

from typing import Tuple, Optional
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from backend.common.capabilities import CAPABILITIES, LEGACY_PERMISSION_TO_CAPABILITY
from backend.common.services.policy_service import PolicyService


class CommonValidations:
    """
    Validaciones comunes para services
    """

    CAPABILITY_ALIASES = {
        'crear_usuario': 'USER_CREATE',
        'modificar_usuario': 'USER_EDIT',
        'eliminar_usuario': 'USER_DELETE',
        'crear_curso': 'COURSE_CREATE',
        'modificar_curso': 'COURSE_EDIT',
        'eliminar_curso': 'COURSE_DELETE',
        'crear_clase': 'CLASS_CREATE',
        'modificar_clase': 'CLASS_EDIT',
        'eliminar_clase': 'CLASS_DELETE',
        'crear_matricula': 'ENROLLMENT_CREATE',
        'modificar_matricula': 'ENROLLMENT_EDIT',
        'eliminar_matricula': 'ENROLLMENT_DELETE',
        'crear_comunicado': 'ANNOUNCEMENT_CREATE',
        'modificar_comunicado': 'ANNOUNCEMENT_EDIT',
        'eliminar_comunicado': 'ANNOUNCEMENT_DELETE',
        'ver_datos_sensibles': 'STUDENT_VIEW_CONFIDENTIAL',
        'exportar_datos': 'REPORT_EXPORT',
        'ver_logs_sistema': 'AUDIT_VIEW',
    }

    @staticmethod
    def _validate_capability(user, capability: str, *, school_id: Optional[int] = None, deny_message: str = 'Acceso denegado') -> Tuple[bool, Optional[str]]:
        if not user or not user.is_authenticated:
            return False, 'Usuario no autenticado'

        if not capability:
            return False, 'Capability requerida inválida'

        if not PolicyService.has_capability(user, capability, school_id=school_id):
            return False, deny_message

        return True, None

    @staticmethod
    def _resolve_required_permission(required_permission: str) -> Optional[str]:
        if not required_permission:
            return None

        candidate = str(required_permission).strip().upper()
        if candidate in CAPABILITIES:
            return candidate

        legacy_candidate = str(required_permission).strip()
        if legacy_candidate in LEGACY_PERMISSION_TO_CAPABILITY:
            return LEGACY_PERMISSION_TO_CAPABILITY[legacy_candidate]

        return CommonValidations.CAPABILITY_ALIASES.get(legacy_candidate.lower())

    @staticmethod
    def validate_admin_permissions(user) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario tenga permisos de administrador

        Args:
            user: Usuario de Django

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        return CommonValidations._validate_capability(
            user,
            'USER_ASSIGN_ROLE',
            deny_message='Acceso denegado: Solo administradores pueden realizar esta acción'
        )

    @staticmethod
    def validate_teacher_permissions(user, required_role: str = 'Profesor') -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario tenga permisos de profesor

        Args:
            user: Usuario de Django
            required_role: Rol requerido (default: 'Profesor')

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False, 'Usuario no autenticado'

        has_teacher_scope = PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE')
        has_admin_scope = PolicyService.has_capability(user, 'USER_ASSIGN_ROLE')
        if not has_teacher_scope or has_admin_scope:
            return False, 'Acceso denegado: Solo profesores pueden realizar esta acción'

        return True, None

    @staticmethod
    def validate_student_permissions(user) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario sea estudiante

        Args:
            user: Usuario de Django

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False, 'Usuario no autenticado'

        has_student_scope = PolicyService.has_capability(user, 'CLASS_VIEW')
        has_teacher_scope = PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE')
        has_admin_scope = PolicyService.has_capability(user, 'USER_ASSIGN_ROLE')
        if not has_student_scope or has_teacher_scope or has_admin_scope:
            return False, 'Acceso denegado: Solo estudiantes pueden realizar esta acción'

        return True, None

    @staticmethod
    def validate_staff_permissions(user) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario sea profesor o administrador

        Args:
            user: Usuario de Django

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        has_teacher_cap = PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE')
        has_admin_cap = PolicyService.has_capability(user, 'USER_ASSIGN_ROLE')
        if not has_teacher_cap and not has_admin_cap:
            return False, 'Acceso denegado: Solo profesores y administradores pueden realizar esta acción'

        return True, None

    @staticmethod
    def validate_class_ownership(user, clase) -> Tuple[bool, Optional[str]]:
        """
        Valida que el profesor sea el propietario de la clase

        Args:
            user: Usuario profesor
            clase: Instancia de Clase

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if clase.profesor_id != user.id:
            return False, "No tienes permisos para modificar esta clase"

        return True, None

    @staticmethod
    def validate_school_membership(user, colegio) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario pertenezca al colegio especificado

        Args:
            user: Usuario de Django
            colegio: Instancia de Colegio

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if user.rbd_colegio != colegio.rbd:
            return False, "El usuario no pertenece a este colegio"

        return True, None

    # ==================== NUEVAS VALIDACIONES PARA FASE 4 ====================

    @staticmethod
    def validate_financial_advisor_permissions(user) -> Tuple[bool, Optional[str]]:
        """
        Valida permisos de asesor financiero

        Args:
            user: Usuario de Django

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        return CommonValidations._validate_capability(
            user,
            'FINANCE_VIEW_SUBSCRIPTIONS',
            deny_message='Acceso denegado: Solo asesores financieros pueden realizar esta acción'
        )

    @staticmethod
    def validate_financial_data(data: dict, operation_type: str = 'create') -> Tuple[bool, Optional[str]]:
        """
        Valida datos financieros con reglas de negocio específicas

        Args:
            data: Diccionario con datos financieros
            operation_type: Tipo de operación ('create', 'update', 'delete')

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        errors = []

        # Validar montos
        if 'monto' in data:
            try:
                monto = Decimal(str(data['monto']))
                if monto <= 0:
                    errors.append("El monto debe ser mayor a cero")
                if monto > Decimal('10000000'):  # Límite arbitrario alto
                    errors.append("El monto excede el límite permitido")
            except (InvalidOperation, ValueError):
                errors.append("El monto debe ser un número válido")

        if 'monto_total' in data:
            try:
                monto_total = Decimal(str(data['monto_total']))
                if monto_total <= 0:
                    errors.append("El monto total debe ser mayor a cero")
            except (InvalidOperation, ValueError):
                errors.append("El monto total debe ser un número válido")

        # Validar fechas
        if 'fecha_vencimiento' in data:
            try:
                fecha = timezone.datetime.fromisoformat(data['fecha_vencimiento'].replace('Z', '+00:00'))
                if fecha < timezone.now():
                    errors.append("La fecha de vencimiento no puede ser en el pasado")
            except (ValueError, AttributeError):
                errors.append("La fecha de vencimiento debe tener un formato válido")

        if 'fecha_emision' in data:
            try:
                fecha = timezone.datetime.fromisoformat(data['fecha_emision'].replace('Z', '+00:00'))
                if fecha > timezone.now():
                    errors.append("La fecha de emisión no puede ser en el futuro")
            except (ValueError, AttributeError):
                errors.append("La fecha de emisión debe tener un formato válido")

        # Validar porcentajes
        if 'porcentaje' in data:
            try:
                porcentaje = Decimal(str(data['porcentaje']))
                if not (0 <= porcentaje <= 100):
                    errors.append("El porcentaje debe estar entre 0 y 100")
            except (InvalidOperation, ValueError):
                errors.append("El porcentaje debe ser un número válido")

        # Validar textos
        text_fields = ['descripcion', 'motivo', 'observaciones']
        for field in text_fields:
            if field in data and data[field]:
                if len(str(data[field])) > 500:
                    errors.append(f"El campo {field} no puede exceder 500 caracteres")
                # Validar caracteres peligrosos
                if re.search(r'[<>]', str(data[field])):
                    errors.append(f"El campo {field} contiene caracteres no permitidos")

        # Validar IDs numéricos
        id_fields = ['estudiante_id', 'colegio_id', 'curso_id', 'cuota_id']
        for field in id_fields:
            if field in data and data[field] is not None:
                try:
                    int(data[field])
                except (ValueError, TypeError):
                    errors.append(f"El campo {field} debe ser un ID válido")

        if errors:
            return False, "; ".join(errors)

        return True, None

    @staticmethod
    def validate_beca_data(data: dict, operation_type: str = 'create') -> Tuple[bool, Optional[str]]:
        """
        Validaciones específicas para becas

        Args:
            data: Datos de la beca
            operation_type: Tipo de operación

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        # Validaciones generales financieras
        is_valid, error_msg = CommonValidations.validate_financial_data(data, operation_type)
        if not is_valid:
            return False, error_msg

        # Validaciones específicas de becas
        errors = []

        if operation_type == 'create':
            required_fields = ['estudiante_id', 'tipo_beca', 'monto', 'motivo']
            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append(f"El campo {field} es obligatorio")

        # Validar tipo de beca
        tipos_validos = ['merito_academico', 'situacion_economica', 'deporte', 'arte', 'otra']
        if 'tipo_beca' in data and data['tipo_beca'] not in tipos_validos:
            errors.append("Tipo de beca no válido")

        # Compatibilidad: en el flujo actual se envía matricula_id bajo la clave estudiante_id
        if 'estudiante_id' in data and data.get('estudiante_id') is not None:
            from backend.apps.matriculas.models import Matricula
            try:
                matricula = Matricula.objects.select_related('estudiante').get(id=int(data['estudiante_id']))
                if matricula.estado != 'ACTIVA':
                    errors.append("La matrícula debe estar activa")
            except (Matricula.DoesNotExist, TypeError, ValueError):
                errors.append("Matrícula no encontrada")

        if errors:
            return False, "; ".join(errors)

        return True, None

    @staticmethod
    def validate_boleta_data(data: dict, operation_type: str = 'create') -> Tuple[bool, Optional[str]]:
        """
        Validaciones específicas para boletas

        Args:
            data: Datos de la boleta
            operation_type: Tipo de operación

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        # Validaciones generales financieras
        is_valid, error_msg = CommonValidations.validate_financial_data(data, operation_type)
        if not is_valid:
            return False, error_msg

        # Validaciones específicas de boletas
        errors = []

        if operation_type == 'create':
            required_fields = ['estudiante_id', 'cuota_id', 'monto_total']
            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append(f"El campo {field} es obligatorio")

        # Validar estado de boleta
        estados_validos = ['pendiente', 'pagada', 'vencida', 'anulada']
        if 'estado' in data and data['estado'] not in estados_validos:
            errors.append("Estado de boleta no válido")

        # Validar que la cuota existe y pertenece a una matrícula activa
        if 'cuota_id' in data and data.get('cuota_id') is not None:
            from backend.apps.matriculas.models import Cuota
            try:
                cuota = Cuota.objects.select_related('matricula').get(id=int(data['cuota_id']))
                if cuota.matricula.estado != 'ACTIVA':
                    errors.append("La cuota debe pertenecer a una matrícula activa")
            except (Cuota.DoesNotExist, TypeError, ValueError):
                errors.append("Cuota no encontrada")

        if errors:
            return False, "; ".join(errors)

        return True, None

    @staticmethod
    def validate_csrf_and_permissions(request, required_permission: str = None, colegio_id: int = None) -> Tuple[bool, Optional[str]]:
        """
        Valida CSRF token y permisos en una sola función

        Args:
            request: Request de Django
            required_permission: Permiso requerido (opcional)
            colegio_id: ID del colegio para validar acceso (opcional)

        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        # Validar CSRF para métodos no GET
        if request.method not in ['GET', 'HEAD', 'OPTIONS']:
            csrf_token = request.META.get('HTTP_X_CSRFTOKEN') or request.POST.get('csrfmiddlewaretoken')
            if not csrf_token:
                return False, "Token CSRF requerido"

        # Validar autenticación
        if not request.user or not request.user.is_authenticated:
            return False, "Usuario no autenticado"

        # Validar permiso específico si se requiere
        if required_permission:
            capability = CommonValidations._resolve_required_permission(required_permission)
            if not capability:
                return False, f"Permiso/capability no reconocido: {required_permission}"

            if not PolicyService.has_capability(request.user, capability, school_id=colegio_id):
                return False, f"No tiene el permiso requerido: {required_permission}"

        # Validar acceso al colegio si se especifica y no hubo validación previa por capability
        if colegio_id and not required_permission:
            user_school = getattr(request.user, 'rbd_colegio', None)
            has_global_scope = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
            if not has_global_scope and str(user_school) != str(colegio_id):
                return False, 'No tiene acceso a este colegio'

        return True, None

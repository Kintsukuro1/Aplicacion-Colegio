from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from functools import wraps
from typing import Optional, Dict, Any
import logging

from backend.common.capabilities import LEGACY_PERMISSION_TO_CAPABILITY
from backend.common.services.policy_service import PolicyService
from backend.common.utils.auth_helpers import normalizar_rol

logger = logging.getLogger(__name__)


class PermissionService:
    """
    Servicio centralizado para gestión de permisos con validación granular
    de acciones específicas en el sistema educativo.
    """

    # Definición de permisos por módulo y acción
    PERMISSIONS = {
        # Módulo Académico
        'ACADEMICO': {
            'VIEW_GRADES': 'Ver calificaciones',
            'EDIT_GRADES': 'Editar calificaciones',
            'VIEW_ATTENDANCE': 'Ver asistencia',
            'EDIT_ATTENDANCE': 'Editar asistencia',
            'VIEW_COURSES': 'Ver cursos',
            'MANAGE_COURSES': 'Gestionar cursos',
            'VIEW_STUDENTS': 'Ver estudiantes',
            'MANAGE_STUDENTS': 'Gestionar estudiantes',
            'VIEW_OWN_GRADES': 'Ver calificaciones propias',
            'VIEW_CHILD_GRADES': 'Ver calificaciones de hijos',
            'VIEW_OWN_ATTENDANCE': 'Ver asistencia propia',
            'VIEW_CHILD_ATTENDANCE': 'Ver asistencia de hijos',
        },

        # Módulo Financiero
        'FINANCIERO': {
            'VIEW_FINANCIAL_DASHBOARD': 'Ver dashboard financiero',
            'VIEW_PAYMENTS': 'Ver pagos',
            'PROCESS_PAYMENTS': 'Procesar pagos',
            'VIEW_SCHOLARSHIPS': 'Ver becas',
            'PROCESS_SCHOLARSHIPS': 'Procesar becas',
            'MANAGE_SCHOLARSHIPS': 'Gestionar becas',
            'VIEW_FEES': 'Ver cuotas',
            'MANAGE_FEES': 'Gestionar cuotas',
            'VIEW_FINANCIAL_REPORTS': 'Ver reportes financieros',
            'VIEW_ACCOUNT_STATEMENTS': 'Ver estados de cuenta',
            'VIEW_INVOICES': 'Ver boletas',
            'PROCESS_INVOICES': 'Procesar boletas',
        },

        # Módulo de Comunicación
        'COMUNICACION': {
            'SEND_MESSAGES': 'Enviar mensajes',
            'VIEW_MESSAGES': 'Ver mensajes',
            'VIEW_COMMUNICATIONS': 'Ver comunicados',
            'MANAGE_ANNOUNCEMENTS': 'Gestionar comunicados',
        },

        # Módulo Administrativo
        'ADMINISTRATIVO': {
            'MANAGE_USERS': 'Gestionar usuarios',
            'VIEW_REPORTS': 'Ver reportes',
            'MANAGE_SYSTEM': 'Gestionar sistema',
            'VIEW_AUDIT_LOGS': 'Ver logs de auditoría',
            'MANAGE_SCHOOLS': 'Gestionar escuelas',
            'MANAGE_SUBSCRIPTIONS': 'Gestionar suscripciones',
            'VIEW_GLOBAL_STATS': 'Ver estadísticas globales',
            'VIEW_SECURITY_MONITORING': 'Ver monitoreo de seguridad',
        },

        # Módulo de Matrículas
        'MATRICULAS': {
            'VIEW_ENROLLMENTS': 'Ver matrículas',
            'PROCESS_ENROLLMENTS': 'Procesar matrículas',
            'MANAGE_ENROLLMENTS': 'Gestionar matrículas',
        }
    }

    @staticmethod
    def has_permission(user: User, module: str, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Verifica si un usuario tiene permiso para realizar una acción específica.

        Args:
            user: Usuario de Django
            module: Módulo del sistema (ej: 'ACADEMICO', 'FINANCIERO')
            action: Acción específica (ej: 'EDIT_GRADES', 'VIEW_PAYMENTS')
            context: Contexto adicional para validación (ej: {'student_id': 123, 'course_id': 456})

        Returns:
            bool: True si tiene permiso, False en caso contrario
        """
        if not user or not user.is_authenticated:
            return False

        # Verificar si el usuario está activo
        if not user.is_active:
            return False

        permission_key = f"{module}.{action}"

        # Regla de seguridad: gestión de usuarios (legacy) exige alcance global.
        if permission_key == 'ADMINISTRATIVO.MANAGE_USERS':
            if not PolicyService.has_capability(user, 'USER_MANAGE_GLOBAL'):
                logger.warning(f"Permiso denegado: {user.email} intentó {permission_key}")
                return False

        mapped_capability = LEGACY_PERMISSION_TO_CAPABILITY.get(permission_key)
        if not mapped_capability:
            logger.warning(f"Permiso legacy sin mapeo a capability: {permission_key}")
            return False

        if not PolicyService.authorize(user, mapped_capability, context=context):
            logger.warning(f"Permiso denegado: {user.email} intentó {permission_key}")
            return False
        return True

    @staticmethod
    def _get_role_permissions(role_name: str) -> list:
        """
        Obtiene la lista de permisos permitidos para un rol específico.
        
        Args:
            role_name: Nombre del rol normalizado ('admin', 'profesor', 'estudiante', etc.)
        
        Returns:
            Lista de permisos en formato 'MODULO.ACCION'
        """
        role_permissions = {
            'admin_general': [
                # Super Admin - Acceso total a todo el sistema (multi-tenant)
                'ADMINISTRATIVO.MANAGE_USERS', 'ADMINISTRATIVO.VIEW_REPORTS',
                'ADMINISTRATIVO.MANAGE_SYSTEM', 'ADMINISTRATIVO.VIEW_AUDIT_LOGS',
                'ADMINISTRATIVO.MANAGE_SCHOOLS', 'ADMINISTRATIVO.MANAGE_SUBSCRIPTIONS',
                'ADMINISTRATIVO.VIEW_GLOBAL_STATS', 'ADMINISTRATIVO.VIEW_SECURITY_MONITORING',
                'COMUNICACION.SEND_MESSAGES', 'COMUNICACION.VIEW_MESSAGES',
                'COMUNICACION.VIEW_COMMUNICATIONS', 'COMUNICACION.MANAGE_ANNOUNCEMENTS',
                'ACADEMICO.VIEW_GRADES', 'ACADEMICO.EDIT_GRADES',
                'ACADEMICO.VIEW_ATTENDANCE', 'ACADEMICO.EDIT_ATTENDANCE',
                'ACADEMICO.VIEW_COURSES', 'ACADEMICO.MANAGE_COURSES',
                'ACADEMICO.VIEW_STUDENTS', 'ACADEMICO.MANAGE_STUDENTS',
                'ACADEMICO.VIEW_REPORTS',
                'FINANCIERO.VIEW_PAYMENTS', 'FINANCIERO.PROCESS_PAYMENTS',
                'FINANCIERO.VIEW_SCHOLARSHIPS', 'FINANCIERO.MANAGE_SCHOLARSHIPS',
                'FINANCIERO.VIEW_FEES', 'FINANCIERO.MANAGE_FEES',
                'FINANCIERO.VIEW_FINANCIAL_REPORTS',
                'MATRICULAS.VIEW_ENROLLMENTS', 'MATRICULAS.PROCESS_ENROLLMENTS',
                'MATRICULAS.MANAGE_ENROLLMENTS'
            ],
            'admin': [
                # Permisos administrativos generales - gestión de usuarios y sistema
                'ADMINISTRATIVO.MANAGE_USERS', 'ADMINISTRATIVO.VIEW_REPORTS',
                'ADMINISTRATIVO.MANAGE_SYSTEM', 'ADMINISTRATIVO.VIEW_AUDIT_LOGS',
                'COMUNICACION.SEND_MESSAGES', 'COMUNICACION.VIEW_MESSAGES',
                'COMUNICACION.VIEW_COMMUNICATIONS', 'COMUNICACION.MANAGE_ANNOUNCEMENTS',
                # Acceso total académico
                'ACADEMICO.VIEW_GRADES', 'ACADEMICO.EDIT_GRADES',
                'ACADEMICO.VIEW_ATTENDANCE', 'ACADEMICO.EDIT_ATTENDANCE',
                'ACADEMICO.VIEW_COURSES', 'ACADEMICO.MANAGE_COURSES',
                'ACADEMICO.VIEW_STUDENTS', 'ACADEMICO.MANAGE_STUDENTS',
                'ACADEMICO.VIEW_REPORTS',
            ],
            'admin_escolar': [
                # Permisos administrativos escolares
                'ADMINISTRATIVO.VIEW_REPORTS',
                'ACADEMICO.VIEW_GRADES', 'ACADEMICO.EDIT_GRADES',
                'ACADEMICO.VIEW_ATTENDANCE', 'ACADEMICO.EDIT_ATTENDANCE',
                'ACADEMICO.VIEW_COURSES', 'ACADEMICO.MANAGE_COURSES',
                'ACADEMICO.VIEW_STUDENTS', 'ACADEMICO.MANAGE_STUDENTS',
                'ACADEMICO.VIEW_REPORTS',
                'FINANCIERO.VIEW_PAYMENTS', 'FINANCIERO.VIEW_SCHOLARSHIPS',
                'FINANCIERO.VIEW_FEES', 'FINANCIERO.VIEW_FINANCIAL_REPORTS',
                'COMUNICACION.SEND_MESSAGES', 'COMUNICACION.VIEW_MESSAGES',
                'COMUNICACION.VIEW_COMMUNICATIONS', 'COMUNICACION.MANAGE_ANNOUNCEMENTS',
                'MATRICULAS.VIEW_ENROLLMENTS', 'MATRICULAS.PROCESS_ENROLLMENTS',
                'MATRICULAS.MANAGE_ENROLLMENTS'
            ],
            'profesor': [
                # Permisos limitados para profesores
                'ACADEMICO.VIEW_GRADES', 'ACADEMICO.EDIT_GRADES',
                'ACADEMICO.VIEW_ATTENDANCE', 'ACADEMICO.EDIT_ATTENDANCE',
                'ACADEMICO.VIEW_COURSES', 'ACADEMICO.VIEW_STUDENTS',
                'ACADEMICO.VIEW_REPORTS',
                'COMUNICACION.SEND_MESSAGES', 'COMUNICACION.VIEW_MESSAGES',
                'COMUNICACION.VIEW_COMMUNICATIONS'
            ],
            'estudiante': [
                # Permisos básicos para estudiantes - solo ven sus propios datos
                'ACADEMICO.VIEW_OWN_GRADES', 'ACADEMICO.VIEW_OWN_ATTENDANCE',
                'ACADEMICO.VIEW_COURSES',
                'COMUNICACION.SEND_MESSAGES', 'COMUNICACION.VIEW_MESSAGES',
                'COMUNICACION.VIEW_COMMUNICATIONS',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS',
                'MATRICULAS.VIEW_ENROLLMENTS', 'FINANCIERO.VIEW_PAYMENTS'
            ],
            'apoderado': [
                # Permisos para apoderados
                'ACADEMICO.VIEW_CHILD_GRADES', 'ACADEMICO.VIEW_CHILD_ATTENDANCE',
                'ACADEMICO.VIEW_COURSES',
                'FINANCIERO.VIEW_PAYMENTS', 'FINANCIERO.VIEW_FEES',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS',
                'MATRICULAS.VIEW_ENROLLMENTS'
            ],
            'asesor_financiero': [
                # Permisos financieros
                'FINANCIERO.VIEW_FINANCIAL_DASHBOARD',
                'FINANCIERO.VIEW_PAYMENTS', 'FINANCIERO.PROCESS_PAYMENTS',
                'FINANCIERO.VIEW_SCHOLARSHIPS', 'FINANCIERO.PROCESS_SCHOLARSHIPS',
                'FINANCIERO.MANAGE_SCHOLARSHIPS',
                'FINANCIERO.VIEW_FEES', 'FINANCIERO.MANAGE_FEES',
                'FINANCIERO.VIEW_FINANCIAL_REPORTS',
                'FINANCIERO.VIEW_ACCOUNT_STATEMENTS',
                'FINANCIERO.VIEW_INVOICES', 'FINANCIERO.PROCESS_INVOICES',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS'
            ],
            'coordinador_academico': [
                'ACADEMICO.VIEW_GRADES', 'ACADEMICO.VIEW_ATTENDANCE',
                'ACADEMICO.VIEW_COURSES', 'ACADEMICO.VIEW_STUDENTS',
                'ACADEMICO.VIEW_REPORTS',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS',
            ],
            'inspector_convivencia': [
                'ACADEMICO.VIEW_ATTENDANCE', 'ACADEMICO.EDIT_ATTENDANCE',
                'ACADEMICO.VIEW_STUDENTS',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS',
            ],
            'psicologo_orientador': [
                'ACADEMICO.VIEW_GRADES', 'ACADEMICO.VIEW_ATTENDANCE',
                'ACADEMICO.VIEW_STUDENTS', 'ACADEMICO.VIEW_REPORTS',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS',
            ],
            'soporte_tecnico_escolar': [
                'ADMINISTRATIVO.VIEW_REPORTS', 'ADMINISTRATIVO.VIEW_AUDIT_LOGS',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS',
            ],
            'bibliotecario_digital': [
                'ACADEMICO.VIEW_COURSES', 'ACADEMICO.VIEW_STUDENTS',
                'COMUNICACION.VIEW_MESSAGES', 'COMUNICACION.VIEW_COMMUNICATIONS',
                'COMUNICACION.MANAGE_ANNOUNCEMENTS',
            ],
        }

        return role_permissions.get(role_name, [])

    @staticmethod
    def require_permission(module: str, action: str):
        """
        Decorador para requerir permisos específicos en vistas Django y métodos de servicios.

        Uso en vistas Django:
            @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
            def my_view(request):
                # Vista protegida
                pass

        Uso en métodos de servicio:
            @PermissionService.require_permission('ACADEMICO', 'EDIT_GRADES')
            def update_grades(self, user, student_id, grades):
                # Método protegido
                pass
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Determinar el usuario según el contexto
                user = None
                
                # Caso 1: Vista Django - primer argumento es request
                if len(args) > 0 and hasattr(args[0], 'user') and hasattr(args[0].user, 'is_authenticated'):
                    user = args[0].user
                # Caso 2: Método estático - primer argumento es user
                elif len(args) > 0 and hasattr(args[0], 'is_authenticated'):
                    user = args[0]
                # Caso 3: Método de instancia - segundo argumento es user
                elif len(args) > 1 and hasattr(args[1], 'is_authenticated'):
                    user = args[1]
                # Caso 4: User pasado como kwarg
                elif 'user' in kwargs and hasattr(kwargs['user'], 'is_authenticated'):
                    user = kwargs['user']
                # Caso 5: Request pasado como kwarg
                elif 'request' in kwargs and hasattr(kwargs['request'], 'user') and hasattr(kwargs['request'].user, 'is_authenticated'):
                    user = kwargs['request'].user

                if not user:
                    raise ValueError("No se pudo determinar el usuario en el método decorado")

                # Extraer contexto de los kwargs si está disponible
                context = kwargs.get('context', {})

                if not PermissionService.has_permission(user, module, action, context):
                    logger.warning(f"Acceso denegado: {getattr(user, 'email', 'Anonymous')} "
                                 f"intentó ejecutar {func.__name__} en {module}.{action}")
                    raise PermissionDenied(f"No tiene permisos para {action} en {module}")

                return func(*args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def require_permission_any(permission_list: list):
        """
        Decorador para requerir AL MENOS UNO de los permisos especificados.
        Útil para permitir acceso a múltiples roles con diferentes permisos.

        Uso en vistas Django:
            @PermissionService.require_permission_any([
                ('ACADEMICO', 'VIEW_GRADES'),
                ('ACADEMICO', 'VIEW_OWN_GRADES')
            ])
            def view_grades(request, student_id):
                # Vista protegida - accesible por profesores o estudiantes
                pass

        Uso en métodos de servicio:
            @PermissionService.require_permission_any([
                ('ACADEMICO', 'VIEW_GRADES'),
                ('ACADEMICO', 'VIEW_OWN_GRADES')
            ])
            def view_grades(self, user, student_id):
                # Método protegido
                pass
        
        Args:
            permission_list: Lista de tuplas (módulo, acción)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Determinar el usuario según el contexto
                user = None
                
                # Caso 1: Vista Django - primer argumento es request
                if len(args) > 0 and hasattr(args[0], 'user') and hasattr(args[0].user, 'is_authenticated'):
                    user = args[0].user
                # Caso 2: Método estático - primer argumento es user
                elif len(args) > 0 and hasattr(args[0], 'is_authenticated'):
                    user = args[0]
                # Caso 3: Método de instancia - segundo argumento es user
                elif len(args) > 1 and hasattr(args[1], 'is_authenticated'):
                    user = args[1]
                # Caso 4: User pasado como kwarg
                elif 'user' in kwargs and hasattr(kwargs['user'], 'is_authenticated'):
                    user = kwargs['user']

                if not user:
                    raise ValueError("No se pudo determinar el usuario en el método decorado.")

                # Extraer contexto de los kwargs si está disponible
                context = kwargs.get('context', {})

                # Verificar si tiene al menos uno de los permisos
                has_any_permission = False
                for module, action in permission_list:
                    if PermissionService.has_permission(user, module, action, context):
                        has_any_permission = True
                        break

                if not has_any_permission:
                    permissions_str = ', '.join([f"{m}.{a}" for m, a in permission_list])
                    logger.warning(f"Acceso denegado: {getattr(user, 'email', 'Anonymous')} "
                                 f"intentó ejecutar {func.__name__} sin ninguno de los permisos: {permissions_str}")
                    raise PermissionDenied(f"No tiene ninguno de los permisos requeridos: {permissions_str}")

                return func(*args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def get_user_permissions(user: User) -> Dict[str, list]:
        """
        Obtiene todos los permisos disponibles para un usuario específico.
        
        Args:
            user: Usuario de Django
        
        Returns:
            Dict con permisos organizados por módulo
        """
        if not user or not user.is_authenticated:
            return {}

        capability_to_legacy = {
            capability: legacy
            for legacy, capability in LEGACY_PERMISSION_TO_CAPABILITY.items()
        }

        user_capabilities = PolicyService.get_user_capabilities(user)
        role_permissions = [
            capability_to_legacy[cap]
            for cap in user_capabilities
            if cap in capability_to_legacy
        ]

        if not role_permissions:
            user_role = getattr(user, 'role', None)
            role_normalized = normalizar_rol(user_role.nombre) if user_role else None
            if not role_normalized:
                return {}
            role_permissions = PermissionService._get_role_permissions(role_normalized)

        # Organizar por módulos
        permissions_by_module = {}
        for perm in role_permissions:
            try:
                module, action = perm.split('.', 1)
                if module not in permissions_by_module:
                    permissions_by_module[module] = []
                permissions_by_module[module].append(action)
            except ValueError:
                logger.warning(f"Formato de permiso inválido: {perm}")
                continue

        return permissions_by_module

    @staticmethod
    def check_bulk_permissions(user: User, permission_checks: list) -> Dict[str, bool]:
        """
        Verifica múltiples permisos de una vez.

        Args:
            user: Usuario de Django
            permission_checks: Lista de tuplas (module, action) o (module, action, context)

        Returns:
            Dict con resultados de cada verificación en formato 'MODULO.ACCION': bool
        """
        results = {}
        for check in permission_checks:
            if len(check) == 3:
                module, action, context = check
            elif len(check) == 2:
                module, action = check
                context = None
            else:
                logger.warning(f"Formato de verificación inválido: {check}")
                continue

            key = f"{module}.{action}"
            results[key] = PermissionService.has_permission(user, module, action, context)

        return results

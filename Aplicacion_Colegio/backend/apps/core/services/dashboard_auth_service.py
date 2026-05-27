"""
Dashboard Auth Service - Autenticación y contexto básico del dashboard.

Extraído de dashboard_service.py para separar responsabilidades.

CONTRATOS:
- get_user_context: Query Operation (dict)
- get_sidebar_template: Transform Operation (str)
- validate_page_access: Validation Operation (tuple)
"""

import logging
from typing import Dict, Optional, Tuple
from backend.common.utils.auth_helpers import normalizar_rol
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException
from backend.common.services.policy_service import PolicyService


logger = logging.getLogger(__name__)


PAGE_CAPABILITIES_ANY = {
    'inicio': {'DASHBOARD_VIEW_SELF', 'DASHBOARD_VIEW_SCHOOL', 'DASHBOARD_VIEW_ANALYTICS'},
    'perfil': {'DASHBOARD_VIEW_SELF', 'DASHBOARD_VIEW_SCHOOL', 'DASHBOARD_VIEW_ANALYTICS'},
    'notificaciones': {'DASHBOARD_VIEW_SELF', 'DASHBOARD_VIEW_SCHOOL', 'DASHBOARD_VIEW_ANALYTICS'},
    'mi_escuela': {'SYSTEM_CONFIGURE'},
    'infraestructura': {'SYSTEM_CONFIGURE'},
    'gestionar_escuelas': {'SYSTEM_CONFIGURE'},
    'escuelas': {'SYSTEM_CONFIGURE'},
    'usuarios': {'USER_VIEW'},
    'planes': {'SYSTEM_MANAGE_SUBSCRIPTIONS', 'FINANCE_VIEW_SUBSCRIPTIONS'},
    'estadisticas_globales': {'DASHBOARD_VIEW_ANALYTICS'},
    'reportes_financieros': {'REPORT_VIEW_FINANCIAL'},
    'configuracion': {'SYSTEM_CONFIGURE'},
    'auditoria': {'AUDIT_VIEW', 'SYSTEM_VIEW_AUDIT'},
    'monitoreo_seguridad': {'AUDIT_VIEW', 'SYSTEM_VIEW_AUDIT'},
    'mis_clases': {'CLASS_VIEW'},
    'mi_horario': {'CLASS_VIEW'},
    'mis_tareas': {'CLASS_VIEW'},
    'mis_anotaciones': {'STUDENT_VIEW'},
    'tareas_consolidado': {'CLASS_VIEW'},
    'mis_planificaciones': {'CLASS_VIEW'},
    'asistencia': {'CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE'},
    'mis_evaluaciones': {'GRADE_VIEW'},
    'notas': {'GRADE_VIEW'},
    'mis_notas': {'GRADE_VIEW'},
    'libro_notas': {'GRADE_VIEW'},
    'libro_clases': {'CLASS_VIEW'},
    'mis_certificados': {'REPORT_VIEW_BASIC', 'REPORT_VIEW_ACADEMIC'},
    'disponibilidad': {'CLASS_VIEW', 'CLASS_TAKE_ATTENDANCE'},
    'reportes': {'REPORT_VIEW_BASIC', 'REPORT_VIEW_ACADEMIC', 'REPORT_VIEW_FINANCIAL'},
    'informes_reportes': {'REPORT_VIEW_BASIC', 'REPORT_VIEW_ACADEMIC', 'REPORT_VIEW_FINANCIAL'},
    'gestionar_estudiantes': {'STUDENT_VIEW'},
    'gestionar_apoderados': {'STUDENT_VIEW'},
    'gestionar_cursos': {'COURSE_VIEW'},
    'gestionar_ciclos': {'COURSE_VIEW'},
    'gestionar_asignaturas': {'COURSE_VIEW'},
    'gestionar_profesores': {'TEACHER_VIEW'},
    'mis_pupilos': {'STUDENT_VIEW'},
    'justificativos': {'STUDENT_VIEW', 'JUSTIFICATION_VIEW'},
    'firmas_pendientes': {'STUDENT_VIEW'},
    'admision_matricula': {'STUDENT_VIEW'},
    'calendario_pupilo': {'STUDENT_VIEW', 'CLASS_VIEW'},
    'calendario_eventos': {'ANNOUNCEMENT_VIEW', 'ANNOUNCEMENT_CREATE', 'ANNOUNCEMENT_EDIT', 'ANNOUNCEMENT_DELETE'},
    'solicitud_reuniones': {'CLASS_VIEW', 'SYSTEM_CONFIGURE', 'SYSTEM_ADMIN'},
    'active_sessions': {'AUDIT_VIEW', 'SYSTEM_ADMIN'},
    'password_history': {'AUDIT_VIEW', 'SYSTEM_ADMIN'},
    'dashboard_financiero': {'FINANCE_VIEW'},
    'estados_cuenta': {'FINANCE_VIEW'},
    'pagos': {'FINANCE_VIEW', 'FINANCE_MANAGE_PAYMENTS'},
    'cuotas': {'FINANCE_VIEW'},
    'becas': {'FINANCE_VIEW'},
    'boletas': {'FINANCE_VIEW'},
    'configuracion_transbank': {'SYSTEM_CONFIGURE', 'FINANCE_EDIT'},

    # Coordinador Académico
    'rendimiento': {'DASHBOARD_VIEW_ANALYTICS', 'GRADE_VIEW_ANALYTICS'},
    'planificacion': {'PLANNING_VIEW', 'PLANNING_APPROVE'},

    # Inspector Convivencia
    'anotaciones': {'DISCIPLINE_VIEW', 'DISCIPLINE_CREATE'},
    'justificativos': {'JUSTIFICATION_VIEW', 'JUSTIFICATION_APPROVE'},

    # Psicólogo Orientador
    'entrevistas': {'COUNSELING_VIEW', 'COUNSELING_CREATE'},
    'derivaciones': {'REFERRAL_VIEW', 'REFERRAL_CREATE'},
    'ficha_estudiante': {'STUDENT_VIEW_CONFIDENTIAL'},
    'citaciones_casos': {'COUNSELING_VIEW', 'COUNSELING_CREATE'},

    # Soporte Técnico
    'tickets': {'SUPPORT_VIEW_TICKETS', 'SUPPORT_RESOLVE_TICKET'},
    'actividad': {'SYSTEM_VIEW_AUDIT'},

    # Bibliotecario Digital
    'catalogo': {'LIBRARY_VIEW', 'LIBRARY_CREATE'},
    'prestamos': {'LIBRARY_MANAGE_LOANS'},
}

MENU_ITEM_CAPABILITIES_ANY = {
    'comunicados': {'ANNOUNCEMENT_VIEW'},
    'mensajes': {'ANNOUNCEMENT_VIEW'},
    'estado_cuenta': {'FINANCE_VIEW'},
    'mis_pagos': {'FINANCE_VIEW'},
    'tareas': {'CLASS_VIEW'},
    'calendario': {'CLASS_VIEW'},
    'dashboard_graficos': {'DASHBOARD_VIEW_ANALYTICS', 'GRADE_VIEW_ANALYTICS'},
    'monitoreo_seguridad': {'AUDIT_VIEW', 'SYSTEM_VIEW_AUDIT'},
}


class DashboardAuthService:
    """Service for dashboard authentication and basic context."""

    @staticmethod
    def execute(operation: str, params: Dict) -> object:
        DashboardAuthService.validate(operation, params)
        return DashboardAuthService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict) -> None:
        if operation == 'get_user_context':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            return
        if operation == 'validate_page_access':
            if params.get('rol') is None:
                raise ValueError('Parámetro requerido: rol')
            if params.get('pagina_solicitada') is None:
                raise ValueError('Parámetro requerido: pagina_solicitada')
            return
        if operation == 'get_navigation_access':
            if params.get('rol') is None:
                raise ValueError('Parámetro requerido: rol')
            return
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict) -> object:
        if operation == 'get_user_context':
            return DashboardAuthService._execute_get_user_context(params)
        if operation == 'validate_page_access':
            return DashboardAuthService._execute_validate_page_access(params)
        if operation == 'get_navigation_access':
            return DashboardAuthService._execute_get_navigation_access(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def get_user_context(user, session) -> Optional[Dict]:
        return DashboardAuthService.execute('get_user_context', {
            'user': user,
            'session': session,
        })

    @staticmethod
    def _resolve_dashboard_role(user) -> str:
        role_name = getattr(getattr(user, 'role', None), 'nombre', None)
        normalized_role = normalizar_rol(role_name)
        if normalized_role:
            return normalized_role

        if PolicyService.has_capability(user, 'SYSTEM_ADMIN') is True:
            return 'admin_general'
        if PolicyService.has_capability(user, 'SYSTEM_CONFIGURE') is True:
            return 'admin_escolar'
        if PolicyService.has_capability(user, 'FINANCE_VIEW') is True and PolicyService.has_capability(
            user, 'DASHBOARD_VIEW_SCHOOL'
        ) is True:
            return 'asesor_financiero'
        if PolicyService.has_capability(user, 'STUDENT_VIEW') is True and PolicyService.has_capability(
            user, 'DASHBOARD_VIEW_SELF'
        ) is True and hasattr(user, 'perfil_apoderado'):
            return 'apoderado'
        if PolicyService.has_capability(user, 'CLASS_VIEW') is True and PolicyService.has_capability(
            user, 'GRADE_VIEW'
        ) is True and hasattr(user, 'perfil_estudiante'):
            return 'estudiante'
        if PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE') is True or PolicyService.has_capability(
            user, 'TEACHER_VIEW'
        ) is True:
            return 'profesor'
        return None

    @staticmethod
    def _execute_get_user_context(params: Dict) -> Optional[Dict]:
        """
        Obtiene contexto básico del usuario para dashboard.

        Query Operation: Retorna datos de usuario o None si inválido.

        Args:
            user: Instancia de User
            session: Objeto de sesión de Django

        Returns:
            dict: {
                'success': bool - Siempre True si retorna datos
                'data': dict - Contexto del usuario con rol, nombre, escuela
                'error': str - Solo si hay error
            } or None si sesión inválida

        Raises:
            No lanza excepciones - retorna None para estados inválidos
        """
        user = params['user']
        session = params.get('session')

        rol = DashboardAuthService._resolve_dashboard_role(user)
        is_system_admin = (PolicyService.has_capability(user, 'SYSTEM_ADMIN') is True) and rol in {'admin_general'}
        can_configure_school = PolicyService.has_capability(user, 'SYSTEM_CONFIGURE') is True

        nombre_usuario = user.get_full_name() or getattr(user, 'username', None) or user.email
        id_usuario = user.id

        # Multi-tenant school data
        escuela_rbd = user.rbd_colegio
        escuela_nombre = user.colegio.nombre if user.colegio else 'Sistema'

        # Usuarios con capacidad de configuración pueden usar override de sesión
        if can_configure_school or is_system_admin:
            if is_system_admin and not escuela_rbd:
                # Admin de sistema puede operar sin escuela fija
                escuela_rbd = None
                escuela_nombre = 'Sistema'
            else:
                # Use session override if available
                session_rbd = session.get('admin_rbd_activo') if session else None
                if session_rbd:
                    escuela_rbd = session_rbd
                    escuela_nombre = session.get('admin_colegio_nombre', 'Escuela')
                elif not escuela_rbd:
                    # Requiere una escuela activa cuando no es administrador de sistema
                    if not is_system_admin:
                        return None

        # For other roles, verify school assignment
        elif not escuela_rbd:
            return None  # Invalid session

        if escuela_rbd:
            try:
                IntegrityService.validate_school_integrity_or_raise(
                    school_id=escuela_rbd,
                    action='DASHBOARD_GET_USER_CONTEXT',
                )
            except PrerequisiteException:
                # Permitir acceso a dashboard/checklist/wizard para administradores
                # cuando la escuela estÃ¡ en onboarding y tiene setup incompleto.
                if not (can_configure_school or is_system_admin):
                    raise
                logger.info(
                    "Integrity check deferred for onboarding admin context (school=%s, user=%s)",
                    escuela_rbd,
                    id_usuario,
                )

        return {
            'success': True,
            'data': {
                'rol': rol,
                'nombre_usuario': nombre_usuario,
                'id_usuario': id_usuario,
                'escuela_rbd': escuela_rbd,
                'escuela_nombre': escuela_nombre,
            }
        }

    @staticmethod
    def get_sidebar_template(rol: str) -> str:
        """
        Obtiene template de sidebar según rol del usuario.

        Transform Operation: Retorna path del template.

        Args:
            rol (str): Rol normalizado del usuario

        Returns:
            str: Path del template de sidebar (ej: 'sidebars/sidebar_admin.html')
        """
        rol = normalizar_rol(rol)
        sidebar_map = {
            'admin': 'sidebars/sidebar_admin.html',
            'admin_general': 'sidebars/sidebar_admin.html',
            'admin_escolar': 'sidebars/sidebar_admin_escuela.html',
            'profesor': 'sidebars/sidebar_profesor.html',
            'estudiante': 'sidebars/sidebar_estudiante.html',
            'apoderado': 'sidebars/sidebar_apoderado.html',
            'asesor_financiero': 'sidebars/sidebar_asesor_financiero.html',
            'coordinador_academico': 'sidebars/sidebar_coordinador_academico.html',
            'inspector_convivencia': 'sidebars/sidebar_inspector_convivencia.html',
            'psicologo_orientador': 'sidebars/sidebar_psicologo_orientador.html',
            'soporte_tecnico_escolar': 'sidebars/sidebar_soporte_tecnico.html',
            'bibliotecario_digital': 'sidebars/sidebar_bibliotecario_digital.html',
        }
        return sidebar_map.get(rol, 'sidebars/sidebar_default.html')

    @staticmethod
    def validate_page_access(
        rol: str,
        pagina_solicitada: str,
        user=None,
        school_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        return DashboardAuthService.execute('validate_page_access', {
            'rol': rol,
            'pagina_solicitada': pagina_solicitada,
            'user': user,
            'school_id': school_id,
        })

    @staticmethod
    def _execute_validate_page_access(params: Dict) -> Tuple[bool, str]:
        """
        Valida si el usuario tiene acceso a la página solicitada.

        Validation Operation: Retorna validación y template correspondiente.

        Args:
            rol (str): Rol normalizado del usuario
            pagina_solicitada (str): Nombre de la página solicitada

        Returns:
            tuple: (bool, str) - (tiene_acceso, template_path)
                - (True, 'template_path') si tiene acceso
                - (False, 'acceso_denegado.html') si no tiene acceso
        """
        rol = params['rol']
        pagina_solicitada = params['pagina_solicitada']
        user = params.get('user')
        school_id = params.get('school_id')

        from backend.common.utils.permissions import get_paginas_por_rol

        paginas_permitidas = get_paginas_por_rol(rol)
        template_pagina = paginas_permitidas.get(
            pagina_solicitada,
            'compartido/acceso_denegado.html'
        )

        if user is not None:
            capabilities = PAGE_CAPABILITIES_ANY.get(pagina_solicitada)

            if capabilities is not None:
                has_access = any(
                    PolicyService.has_capability(user, capability, school_id=school_id)
                    for capability in capabilities
                )
                if not has_access:
                    return False, 'compartido/acceso_denegado.html'

                if template_pagina == 'compartido/acceso_denegado.html' and pagina_solicitada in {'inicio', 'perfil'}:
                    fallback_templates = {
                        'inicio': 'compartido/inicio_modulos.html',
                        'perfil': 'compartido/perfil.html',
                    }
                    template_pagina = fallback_templates[pagina_solicitada]

                return True, template_pagina

        if pagina_solicitada not in paginas_permitidas:
            return False, 'compartido/acceso_denegado.html'

        return True, template_pagina

    @staticmethod
    def get_navigation_access(rol: str, user=None, school_id: Optional[int] = None) -> Dict:
        return DashboardAuthService.execute('get_navigation_access', {
            'rol': rol,
            'user': user,
            'school_id': school_id,
        })

    @staticmethod
    def _execute_get_navigation_access(params: Dict) -> Dict:
        rol = params['rol']
        user = params.get('user')
        school_id = params.get('school_id')

        from backend.common.utils.permissions import get_paginas_por_rol

        paginas_permitidas = get_paginas_por_rol(rol)
        paginas_habilitadas = []

        for pagina in paginas_permitidas.keys():
            required_capabilities = PAGE_CAPABILITIES_ANY.get(pagina)

            if user is None or required_capabilities is None:
                paginas_habilitadas.append(pagina)
                continue

            has_access = any(
                PolicyService.has_capability(user, capability, school_id=school_id)
                for capability in required_capabilities
            )
            if has_access:
                paginas_habilitadas.append(pagina)

        menu_access = {}
        for menu_key, required_capabilities in MENU_ITEM_CAPABILITIES_ANY.items():
            if user is None:
                menu_access[menu_key] = True
                continue

            menu_access[menu_key] = any(
                PolicyService.has_capability(user, capability, school_id=school_id)
                for capability in required_capabilities
            )

        return {
            'paginas_habilitadas': paginas_habilitadas,
            'menu_access': menu_access,
        }

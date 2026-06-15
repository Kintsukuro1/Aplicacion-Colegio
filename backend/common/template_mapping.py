"""
Mapeo de Templates por Rol
===========================

Define qué templates puede acceder cada rol de usuario en el sistema.
Usado por las vistas para determinar qué template renderizar según el rol.
"""

from backend.common.constants import ROLE_GROUPS

# Mapeo de vistas a templates por rol
TEMPLATE_MAPPING = {
    # ===================
    # MÓDULO ACADÉMICO
    # ===================
    
    # Vista: Mis Notas / Calificaciones
    'mis_notas': {
        'estudiante': 'frontend/templates/academico/estudiante/mis_notas.html',
        'apoderado': 'frontend/templates/academico/apoderado/notas_hijo.html',  # ✅ COMPLETADO
        'profesor': 'frontend/templates/academico/profesor/gestionar_notas.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/academico/estudiante/mis_notas.html',
    },
    
    # Vista: Asistencia
    'asistencia': {
        'estudiante': 'frontend/templates/academico/estudiante/mi_asistencia.html',
        'apoderado': 'frontend/templates/academico/apoderado/asistencia_hijo.html',  # ✅ COMPLETADO
        'profesor': 'frontend/templates/academico/profesor/registrar_asistencia.html',  # ✅ COMPLETADO
        'inspector': 'frontend/templates/academico/admin/reporte_asistencia.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/academico/estudiante/mi_asistencia.html',
    },
    
    # Vista: Tareas
    'tareas': {
        'estudiante': 'frontend/templates/academico/estudiante/mis_tareas.html',
        'apoderado': 'frontend/templates/academico/apoderado/tareas_hijo.html',  # ✅ COMPLETADO
        'profesor': 'frontend/templates/academico/profesor/gestionar_tareas.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/academico/estudiante/mis_tareas.html',
    },
    
    # Vista: Dashboard / Inicio
    'inicio': {
        'estudiante': 'frontend/templates/academico/estudiante/inicio.html',
        'apoderado': 'frontend/templates/academico/apoderado/inicio.html',  # ✅ COMPLETADO
        'profesor': 'frontend/templates/academico/profesor/inicio.html',  # ✅ COMPLETADO
        'admin': 'frontend/templates/academico/admin/inicio.html',  # ✅ COMPLETADO (con condicional para admin/admin_escolar)
        'admin_escolar': 'frontend/templates/academico/admin/inicio.html',  # ✅ COMPLETADO (usa mismo template con condicional)
        'default': 'frontend/templates/academico/estudiante/inicio.html',
    },
    
    # Vista: Perfil
    'perfil': {
        'estudiante': 'frontend/templates/academico/estudiante/perfil.html',
        'apoderado': 'frontend/templates/academico/apoderado/perfil.html',  # ✅ COMPLETADO
        'profesor': 'frontend/templates/academico/profesor/perfil.html',  # ✅ COMPLETADO
        'admin': 'frontend/templates/academico/admin/perfil.html',  # ✅ COMPLETADO (con condicional para admin/admin_escolar)
        'admin_escolar': 'frontend/templates/academico/admin/perfil.html',  # ✅ COMPLETADO (usa mismo template con condicional)
        'default': 'frontend/templates/academico/estudiante/perfil.html',
    },
    
    # ===================
    # MÓDULO COMUNICACIÓN
    # ===================
    
    # Vista: Comunicados
    'comunicados': {
        'estudiante': 'frontend/templates/comunicados/estudiante/lista.html',  # TODO: Crear
        'apoderado': 'frontend/templates/comunicados/apoderado/lista.html',  # TODO: Crear
        'profesor': 'frontend/templates/comunicados/profesor/lista.html',  # TODO: Crear
        'admin': 'frontend/templates/comunicados/admin/gestionar.html',  # TODO: Crear
        'default': 'frontend/templates/comunicados/estudiante/lista.html',
    },
    
    # Vista: Mensajería
    'mensajeria': {
        'estudiante': 'frontend/templates/mensajeria/estudiante/bandeja.html',  # ✅ COMPLETADO
        'apoderado': 'frontend/templates/mensajeria/apoderado/bandeja.html',  # ✅ COMPLETADO
        'profesor': 'frontend/templates/mensajeria/profesor/bandeja.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/mensajeria/estudiante/bandeja.html',
    },
    
    # ===================
    # MÓDULO ASESOR FINANCIERO
    # ===================
    
    # Vista: Dashboard Asesor Financiero
    'inicio_asesor': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/inicio.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/inicio.html',
    },
    
    # Vista: Dashboard Financiero con Gráficos
    'dashboard_financiero': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/dashboard.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/dashboard.html',
    },
    
    # Vista: Gestión de Pagos
    'pagos': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/pagos.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/pagos.html',
    },
    
    # Vista: Estados de Cuenta
    'estados_cuenta': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/estados_cuenta.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/estados_cuenta.html',
    },
    
    # Vista: Gestión de Cuotas
    'cuotas': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/cuotas.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/cuotas.html',
    },
    
    # Vista: Gestión de Becas
    'becas': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/becas.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/becas.html',
    },
    
    # Vista: Generación de Boletas
    'boletas': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/boletas.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/boletas.html',
    },
    
    # Vista: Reportes Financieros
    'reportes': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/reportes.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/reportes.html',
    },
    
    # Vista: Configuración Transbank
    'configuracion_transbank': {
        'asesor_financiero': 'frontend/templates/asesor_financiero/configuracion_transbank.html',  # ✅ COMPLETADO
        'default': 'frontend/templates/asesor_financiero/configuracion_transbank.html',
    },
}


def get_template_for_role(view_name: str, role_name: str) -> str:
    """
    Obtiene el template correcto según la vista y el rol del usuario.
    
    Args:
        view_name: Nombre de la vista (ej: 'mis_notas', 'asistencia')
        role_name: Nombre del rol del usuario (ej: 'estudiante', 'profesor')
    
    Returns:
        str: Path del template a renderizar
    
    Ejemplo:
        >>> get_template_for_role('mis_notas', 'estudiante')
        'frontend/templates/academico/estudiante/mis_notas.html'
        
        >>> get_template_for_role('mis_notas', 'profesor')
        'frontend/templates/academico/profesor/gestionar_notas.html'
    """
    if view_name not in TEMPLATE_MAPPING:
        raise ValueError(f"Vista '{view_name}' no encontrada en TEMPLATE_MAPPING")
    
    view_templates = TEMPLATE_MAPPING[view_name]
    
    # Buscar template específico para el rol
    if role_name in view_templates:
        return view_templates[role_name]
    
    # Buscar por grupo de rol
    role_group = None
    for group_name, roles in ROLE_GROUPS.items():
        if role_name in roles:
            role_group = group_name
            break
    
    if role_group and role_group in view_templates:
        return view_templates[role_group]
    
    # Usar template por defecto
    return view_templates.get('default', 'frontend/templates/base_app.html')


def get_available_views_for_role(role_name: str) -> dict:
    """
    Obtiene todas las vistas disponibles para un rol específico.
    
    Args:
        role_name: Nombre del rol del usuario
    
    Returns:
        dict: Diccionario {view_name: template_path} de vistas accesibles
    
    Ejemplo:
        >>> views = get_available_views_for_role('estudiante')
        >>> 'mis_notas' in views
        True
    """
    available_views = {}
    
    for view_name in TEMPLATE_MAPPING.keys():
        try:
            template = get_template_for_role(view_name, role_name)
            available_views[view_name] = template
        except ValueError:
            continue
    
    return available_views


# Mapeo de URLs a view_name (para uso en vistas)
URL_TO_VIEW_NAME = {
    'mis_notas_estudiante': 'mis_notas',
    'mi_asistencia_estudiante': 'asistencia',
    'ver_tareas_estudiante': 'tareas',
    'dashboard': 'inicio',
    'perfil_estudiante': 'perfil',
    'comunicados:lista': 'comunicados',
    'mensajeria:bandeja_mensajes': 'mensajeria',
}


def get_template_from_url_name(url_name: str, role_name: str) -> str:
    """
    Obtiene el template correcto desde el nombre de la URL.
    
    Args:
        url_name: Nombre de la URL (ej: 'mis_notas_estudiante')
        role_name: Nombre del rol del usuario
    
    Returns:
        str: Path del template a renderizar
    
    Ejemplo:
        >>> get_template_from_url_name('mis_notas_estudiante', 'estudiante')
        'frontend/templates/academico/estudiante/mis_notas.html'
    """
    view_name = URL_TO_VIEW_NAME.get(url_name)
    
    if not view_name:
        raise ValueError(f"URL '{url_name}' no encontrada en URL_TO_VIEW_NAME")
    
    return get_template_for_role(view_name, role_name)


# Templates completados (Fase 1 + Fase 2 + Fase 3)
COMPLETED_TEMPLATES = [
    # Fase 1: Estudiante (5 templates)
    'frontend/templates/academico/estudiante/mis_notas.html',
    'frontend/templates/academico/estudiante/mi_asistencia.html',
    'frontend/templates/academico/estudiante/mis_tareas.html',
    'frontend/templates/academico/estudiante/inicio.html',
    'frontend/templates/academico/estudiante/perfil.html',
    
    # Fase 2: Profesor (5 templates)
    'frontend/templates/academico/profesor/gestionar_notas.html',
    'frontend/templates/academico/profesor/registrar_asistencia.html',
    'frontend/templates/academico/profesor/gestionar_tareas.html',
    'frontend/templates/academico/profesor/inicio.html',
    'frontend/templates/academico/profesor/perfil.html',
    
    # Fase 3: Apoderado (5 templates)
    'frontend/templates/academico/apoderado/notas_hijo.html',
    'frontend/templates/academico/apoderado/asistencia_hijo.html',
    'frontend/templates/academico/apoderado/tareas_hijo.html',
    'frontend/templates/academico/apoderado/inicio.html',
    
    # Fase 4: Admin (3 templates - con condicionales para admin/admin_escolar)
    'frontend/templates/academico/admin/inicio.html',
    'frontend/templates/academico/admin/perfil.html',
    'frontend/templates/academico/admin/reporte_asistencia.html',
    'frontend/templates/academico/apoderado/perfil.html',
]Admin (4 templates)
    'frontend/templates/academico/admin/reporte_asistencia.html',
    'frontend/templates/academico/admin/inicio.html',
    'frontend/templates/academico/admin/perfil.html',
    
    # Comunicados (4 templates)
    'frontend/templates/comunicados/estudiante/lista.html',
    'frontend/templates/comunicados/apoderado/lista.html',
    'frontend/templates/comunicados/profesor/lista.html',
    'frontend/templates/comunicados/admin/gestionar.html',
    
    # Mensajería (3 templates)
    'frontend/templates/mensajeria/estudiante/bandeja.html',
    'frontend/templates/mensajeria/apoderado/bandeja.html',
    'frontend/templates/mensajeria/profesor/bandeja.html',
    
    # Fase 6: Asesor Financiero (9 templates)
    'frontend/templates/asesor_financiero/inicio.html',
    'frontend/templates/asesor_financiero/dashboard.html',
    'frontend/templates/asesor_financiero/pagos.html',
    'frontend/templates/asesor_financiero/estados_cuenta.html',
    'frontend/templates/asesor_financiero/cuotas.html',
    'frontend/templates/asesor_financiero/becas.html',
    'frontend/templates/asesor_financiero/boletas.html',
    'frontend/templates/asesor_financiero/reportes.html',
    'frontend/templates/asesor_financiero/configuracion_transbank.html',
]

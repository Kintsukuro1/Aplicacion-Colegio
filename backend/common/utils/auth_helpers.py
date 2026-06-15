"""
Utilidades para normalización de roles
Asegura consistencia entre 'Alumno' y 'estudiante', etc.
"""

def normalizar_rol(nombre_rol):
    """
    Normaliza el nombre de un rol a su formato estándar interno.
    
    Args:
        nombre_rol: Nombre del rol como aparece en la BD (ej: 'Alumno', 'Profesor', 'Admin')
    
    Returns:
        str: Nombre normalizado del rol (minúsculas, formato estándar)
    
    Ejemplos:
        'Alumno' -> 'estudiante'
        'Profesor' -> 'profesor'
        'Admin' -> 'admin'
        'Asesor Financiero' -> 'asesor_financiero'
    """
    if not nombre_rol:
        return None

    if not isinstance(nombre_rol, str):
        nombre_rol = str(nombre_rol)
    
    # Diccionario de mapeo de roles
    mapeo_roles = {
        # Estudiantes
        'alumno': 'estudiante',
        'estudiante': 'estudiante',
        'pupilo': 'estudiante',
        
        # Profesores
        'profesor': 'profesor',
        'docente': 'profesor',
        'teacher': 'profesor',
        
        # Administradores
        'admin': 'admin',
        'administrador': 'admin',
        'administrator': 'admin',
        
        # Administrador Escolar
        'admin escolar': 'admin_escolar',
        'admin_escolar': 'admin_escolar',
        'administrador_escolar': 'admin_escolar',
        'administrador escolar': 'admin_escolar',
        'director': 'admin_escolar',
        
        # Coordinador Académico / UTP
        'coordinador academico': 'coordinador_academico',
        'coordinador_academico': 'coordinador_academico',
        'coordinador académico': 'coordinador_academico',
        'coordinador académico / jefe utp': 'coordinador_academico',

        # Jefe UTP (rol propio — supervisión académica + SEP)
        'jefe utp': 'jefe_utp',
        'jefe_utp': 'jefe_utp',
        'utp': 'jefe_utp',

        # Inspector / Convivencia
        'inspector': 'inspector_convivencia',
        'inspector convivencia': 'inspector_convivencia',
        'preceptor': 'inspector_convivencia',
        'encargado de convivencia': 'inspector_convivencia',
        'encargado_convivencia': 'inspector_convivencia',
        'inspector_convivencia': 'inspector_convivencia',

        # Psicólogo / Orientador
        'psicologo educacional': 'psicologo_orientador',
        'psicólogo educacional': 'psicologo_orientador',
        'psicologo orientador': 'psicologo_orientador',
        'psicólogo orientador': 'psicologo_orientador',
        'orientador': 'psicologo_orientador',
        'psicologo_orientador': 'psicologo_orientador',

        # Soporte Técnico Escolar
        'soporte tecnico escolar': 'soporte_tecnico_escolar',
        'soporte técnico escolar': 'soporte_tecnico_escolar',
        'soporte tecnico': 'soporte_tecnico_escolar',
        'soporte técnico': 'soporte_tecnico_escolar',
        'soporte_tecnico_escolar': 'soporte_tecnico_escolar',

        # Bibliotecario / Recursos Digitales
        'bibliotecario': 'bibliotecario_digital',
        'gestor de recursos digitales': 'bibliotecario_digital',
        'bibliotecario_digital': 'bibliotecario_digital',
        
        # Administrador General (Super Admin)
        'admin general': 'admin_general',
        'admin_general': 'admin_general',
        'administrador_general': 'admin_general',
        'administrador general': 'admin_general',
        'super admin': 'admin_general',
        'super_admin': 'admin_general',
        
        # Apoderados
        'apoderado': 'apoderado',
        'tutor': 'apoderado',
        'padre': 'apoderado',
        'madre': 'apoderado',
        'guardian': 'apoderado',
        
        # Asesor Financiero
        'asesor financiero': 'asesor_financiero',
        'asesor_financiero': 'asesor_financiero',
        'asesor-financiero': 'asesor_financiero',
        'contador': 'asesor_financiero',
        'tesorero': 'asesor_financiero',
    }
    
    # Normalizar: quitar espacios extras, convertir a minúsculas
    rol_limpio = ' '.join(nombre_rol.lower().strip().split())
    
    # Buscar en el mapeo
    return mapeo_roles.get(rol_limpio, rol_limpio.replace(' ', '_'))


def _normalized_role_from_user(user):
    role_name = getattr(getattr(user, 'role', None), 'nombre', None)
    return normalizar_rol(role_name)


def _has_capability(user, capability):
    try:
        from backend.common.services.policy_service import PolicyService
        return PolicyService.has_capability(user, capability)
    except Exception:
        return False


def es_estudiante(user):
    """Verifica si un usuario tiene rol de estudiante"""
    if not user:
        return False
    if hasattr(user, 'perfil_estudiante'):
        return True
    if (
        _has_capability(user, 'CLASS_VIEW')
        and _has_capability(user, 'GRADE_VIEW')
        and not _has_capability(user, 'STUDENT_VIEW')
        and not _has_capability(user, 'SYSTEM_CONFIGURE')
        and not _has_capability(user, 'SYSTEM_ADMIN')
    ):
        return True
    return _normalized_role_from_user(user) == 'estudiante'


def es_profesor(user):
    """Verifica si un usuario tiene rol de profesor"""
    if not user:
        return False
    if hasattr(user, 'perfil_profesor'):
        return True
    if (
        _has_capability(user, 'CLASS_TAKE_ATTENDANCE')
        and not _has_capability(user, 'SYSTEM_CONFIGURE')
        and not _has_capability(user, 'SYSTEM_ADMIN')
    ):
        return True
    return _normalized_role_from_user(user) == 'profesor'


def es_apoderado(user):
    """Verifica si un usuario tiene rol de apoderado"""
    if not user:
        return False
    if hasattr(user, 'perfil_apoderado'):
        return True
    if (
        _has_capability(user, 'STUDENT_VIEW')
        and _has_capability(user, 'DASHBOARD_VIEW_SELF')
        and not _has_capability(user, 'SYSTEM_CONFIGURE')
        and not _has_capability(user, 'SYSTEM_ADMIN')
        and not _has_capability(user, 'CLASS_TAKE_ATTENDANCE')
    ):
        return True
    return _normalized_role_from_user(user) == 'apoderado'


def es_admin(user):
    """Verifica si un usuario tiene rol de administrador"""
    if not user:
        return False

    # Camino principal capability-first
    if _has_capability(user, 'SYSTEM_ADMIN'):
        return True
    if _has_capability(user, 'SYSTEM_CONFIGURE'):
        return True

    rol = _normalized_role_from_user(user)
    return rol in ['admin', 'admin_escolar', 'admin_general']


def obtener_nombre_rol_display(nombre_rol):
    """
    Obtiene el nombre de display amigable de un rol.
    
    Args:
        nombre_rol: Nombre del rol normalizado o sin normalizar
    
    Returns:
        str: Nombre amigable para mostrar al usuario
    """
    rol_normalizado = normalizar_rol(nombre_rol)
    
    nombres_display = {
        'estudiante': 'Estudiante',
        'profesor': 'Profesor',
        'admin': 'Administrador',
        'admin_escolar': 'Administrador Escolar',
        'coordinador_academico': 'Coordinador Académico',
        'jefe_utp': 'Jefe UTP',
        'inspector_convivencia': 'Inspector / Encargado de Convivencia',
        'psicologo_orientador': 'Psicólogo Educacional / Orientador',
        'soporte_tecnico_escolar': 'Soporte Técnico Escolar',
        'bibliotecario_digital': 'Bibliotecario / Gestor de Recursos Digitales',
        'apoderado': 'Apoderado',
        'asesor_financiero': 'Asesor Financiero',
    }
    
    fallback = str(nombre_rol).title() if nombre_rol is not None else 'Sin Rol'
    return nombres_display.get(rol_normalizado, fallback)

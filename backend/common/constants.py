"""
Constantes globales del sistema.

Incluye definiciones de grupos de roles, configuraciones compartidas,
y otras constantes reutilizables en toda la aplicación.
"""

# ============================================================================
# GRUPOS FUNCIONALES DE ROLES
# ============================================================================

ROLE_GROUPS = {
    'docentes': [
        'profesor',
        'coordinador',
        'jefe_utp',
        'inspector',
    ],
    'administrativos': [
        'admin',
        'admin_escolar',
        'secretario',
        'contador',
    ],
    'apoyo': [
        'psicologo',
        'orientador',
        'bibliotecario',
        'auxiliar',
    ],
    'estudiantes': [
        'estudiante',
    ],
    'apoderados': [
        'apoderado',
        'tutor_legal',
    ],
}

# Roles con permisos de gestión académica completa
ACADEMIC_ADMIN_ROLES = ROLE_GROUPS['administrativos'] + ROLE_GROUPS['docentes']

# Roles que pueden ver información de estudiantes
STUDENT_INFO_VIEWERS = (
    ROLE_GROUPS['docentes'] + 
    ROLE_GROUPS['administrativos'] + 
    ROLE_GROUPS['apoyo'] + 
    ROLE_GROUPS['apoderados']
)

# Roles que pueden registrar asistencia
ATTENDANCE_RECORDERS = ROLE_GROUPS['docentes'] + ['admin_escolar', 'inspector']

# Roles que pueden gestionar evaluaciones
EVALUATION_MANAGERS = ['profesor', 'coordinador', 'jefe_utp', 'admin_escolar']


# ============================================================================
# CONFIGURACIÓN DE NAVEGACIÓN
# ============================================================================

# ============================================================================
# CONSTANTES DE NEGOCIO - ONBOARDING Y VALIDACIONES
# ============================================================================

# Estados de Ciclo Académico
CICLO_ESTADO_ACTIVO = "ACTIVO"
CICLO_ESTADO_PLANIFICACION = "PLANIFICACION"
CICLO_ESTADO_EVALUACION = "EVALUACION"
CICLO_ESTADO_FINALIZADO = "FINALIZADO"
CICLO_ESTADO_CERRADO = "CERRADO"

# Estados de Matrícula
ESTADO_MATRICULA_ACTIVA = "ACTIVA"
ESTADO_MATRICULA_PENDIENTE = "PENDIENTE"
ESTADO_MATRICULA_RETIRADA = "RETIRADA"
ESTADO_MATRICULA_TRASLADADA = "TRASLADADA"
ESTADO_MATRICULA_EGRESADA = "EGRESADA"

# Roles de Usuario (códigos normalizados)
ROL_ADMIN_GENERAL = "ADMIN_GENERAL"
ROL_ADMIN = "ADMIN"
ROL_ADMIN_ESCOLAR = "ADMIN_ESCOLAR"
ROL_PROFESOR = "PROFESOR"
ROL_ESTUDIANTE = "ESTUDIANTE"
ROL_APODERADO = "APODERADO"
ROL_ASESOR_FINANCIERO = "ASESOR_FINANCIERO"

# ============================================================================
# ESTADOS GENERALES (LEGACY)
# ============================================================================

ESTADO_ACTIVO = 'activo'
ESTADO_INACTIVO = 'inactivo'
ESTADO_SUSPENDIDO = 'suspendido'

ESTADOS_CHOICES = [
    (ESTADO_ACTIVO, 'Activo'),
    (ESTADO_INACTIVO, 'Inactivo'),
    (ESTADO_SUSPENDIDO, 'Suspendido'),
]


# ============================================================================
# UTILIDADES
# ============================================================================

def get_role_group(role_name):
    """
    Obtiene el grupo funcional al que pertenece un rol.
    
    Args:
        role_name (str): Nombre del rol
        
    Returns:
        str: Nombre del grupo ('docentes', 'administrativos', etc.) o None
    """
    for group_name, roles in ROLE_GROUPS.items():
        if role_name in roles:
            return group_name
    return None


def is_in_role_group(role_name, group_name):
    """
    Verifica si un rol pertenece a un grupo específico.
    
    Args:
        role_name (str): Nombre del rol
        group_name (str): Nombre del grupo a verificar
        
    Returns:
        bool: True si el rol pertenece al grupo
    """
    return role_name in ROLE_GROUPS.get(group_name, [])




"""
ErrorResponseBuilder - Sistema centralizado de manejo de errores estructurados.

Este módulo proporciona una única fuente de verdad para la construcción
de respuestas de error consistentes en toda la aplicación.

Principios:
- Una constante de error = un mensaje específico
- Mensajes centralizados (no dispersos en views)
- Acción clara para el usuario (action_url)
- Conversión automática a Django messages framework
"""

from django.contrib import messages


# ============================================================================
# CONSTANTES DE ERRORES - ONBOARDING
# ============================================================================

# Prerequisitos de configuración
MISSING_CICLO_ACTIVO = "MISSING_CICLO_ACTIVO"
MISSING_COURSES = "MISSING_COURSES"
MISSING_TEACHERS_ASSIGNED = "MISSING_TEACHERS_ASSIGNED"
MISSING_STUDENTS_ENROLLED = "MISSING_STUDENTS_ENROLLED"

# Errores de validación
INVALID_PREREQUISITE = "INVALID_PREREQUISITE"
INVALID_CURSO_STATE = "INVALID_CURSO_STATE"
INVALID_PROFESOR_STATE = "INVALID_PROFESOR_STATE"
INVALID_ASIGNATURA_STATE = "INVALID_ASIGNATURA_STATE"
INVALID_MATRICULA_STATE = "INVALID_MATRICULA_STATE"
DUPLICATE_ACTIVE_MATRICULA = "DUPLICATE_ACTIVE_MATRICULA"
VALIDATION_ERROR = "VALIDATION_ERROR"
AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"

# Errores de permisos
PERMISSION_DENIED = "PERMISSION_DENIED"
SCHOOL_NOT_CONFIGURED = "SCHOOL_NOT_CONFIGURED"
NOT_FOUND = "NOT_FOUND"

# Errores de integridad de datos
DATA_INCONSISTENCY = "DATA_INCONSISTENCY"
INVALID_RELATIONSHIP = "INVALID_RELATIONSHIP"
ORPHANED_ENTITY = "ORPHANED_ENTITY"
STATE_MISMATCH = "STATE_MISMATCH"
INVALID_STATE = "INVALID_STATE"


# ============================================================================
# MENSAJES DE ERROR - FUENTE DE VERDAD
# ============================================================================

ERROR_MESSAGES = {
    # Onboarding
    MISSING_CICLO_ACTIVO: (
        "Debes crear un Ciclo Académico activo antes de continuar. "
        "El ciclo académico define el período escolar actual."
    ),
    MISSING_COURSES: (
        "Debes crear al menos un curso antes de continuar. "
        "Los cursos son necesarios para organizar a los estudiantes."
    ),
    MISSING_TEACHERS_ASSIGNED: (
        "Debes asignar al menos un profesor a una clase antes de continuar. "
        "Los profesores son necesarios para impartir las asignaturas."
    ),
    MISSING_STUDENTS_ENROLLED: (
        "Debes matricular al menos un estudiante antes de continuar. "
        "Los estudiantes son el núcleo del sistema académico."
    ),
    
    # Validaciones
    INVALID_PREREQUISITE: (
        "No se puede realizar esta acción porque faltan prerequisitos. "
        "Completa primero los pasos de configuración requeridos."
    ),
    INVALID_CURSO_STATE: (
        "El curso no está en un estado válido para esta operación. "
        "Verifica que el curso esté activo y tenga un ciclo académico asignado."
    ),
    INVALID_PROFESOR_STATE: (
        "El profesor no está en un estado válido para esta operación. "
        "Verifica que el profesor esté activo antes de asignarlo a una clase."
    ),
    INVALID_ASIGNATURA_STATE: (
        "La asignatura no está en un estado válido para esta operación. "
        "Verifica que la asignatura esté activa antes de crear una clase."
    ),
    INVALID_MATRICULA_STATE: (
        "El estudiante no tiene una matrícula activa. "
        "Verifica el estado de la matrícula antes de continuar."
    ),
    DUPLICATE_ACTIVE_MATRICULA: (
        "El estudiante ya tiene una matrícula activa en este ciclo académico. "
        "No se pueden tener múltiples matrículas activas en el mismo período."
    ),
    
    # Autenticación
    'VALIDATION_ERROR': (
        "Los datos ingresados no cumplen con los requisitos de validación. "
        "Verifica que todos los campos estén correctos e inténtalo de nuevo."
    ),
    'AUTHENTICATION_FAILED': (
        "Las credenciales proporcionadas son incorrectas. "
        "Verifica tu correo electrónico y contraseña."
    ),
    
    # Permisos
    PERMISSION_DENIED: (
        "No tienes permisos para realizar esta acción. "
        "Contacta al administrador si crees que esto es un error."
    ),
    'NOT_FOUND': (
        "El recurso solicitado no existe o ha sido eliminado. "
        "Verifica que la información sea correcta."
    ),
    SCHOOL_NOT_CONFIGURED: (
        "Tu escuela aún no ha completado la configuración inicial. "
        "Completa el proceso de configuración para comenzar a usar el sistema."
    ),
    
    # Integridad de datos
    DATA_INCONSISTENCY: (
        "Se detectaron inconsistencias en los datos del sistema. "
        "Algunos registros tienen estados o relaciones inválidas que requieren corrección."
    ),
    INVALID_RELATIONSHIP: (
        "Este registro referencia a otros datos que ya no existen o están inactivos. "
        "Actualiza o desactiva este registro para mantener la consistencia."
    ),
    ORPHANED_ENTITY: (
        "Este registro no puede funcionar correctamente porque depende de datos que fueron eliminados. "
        "Reasigna las relaciones o elimina este registro."
    ),
    STATE_MISMATCH: (
        "El estado de este registro no es consistente con sus datos relacionados. "
        "Por ejemplo, un registro activo que depende de datos inactivos."
    ),
    INVALID_STATE: (
        "Este registro está en un estado inválido que no permite la operación solicitada. "
        "Verifica que cumpla con los requisitos de estado antes de continuar."
    ),
}


# ============================================================================
# URLS DE ACCIÓN POR ERROR
# ============================================================================

DEFAULT_ACTION_URL = "/setup/checklist/"

ERROR_ACTION_URLS = {
    MISSING_CICLO_ACTIVO: "/dashboard/?pagina=gestionar_ciclos",
    MISSING_COURSES: "/admin_escolar/gestionar_cursos/",
    MISSING_TEACHERS_ASSIGNED: "/admin_escolar/gestionar_cursos/",
    MISSING_STUDENTS_ENROLLED: "/admin_escolar/gestionar_estudiantes/",
    INVALID_PREREQUISITE: DEFAULT_ACTION_URL,
    SCHOOL_NOT_CONFIGURED: DEFAULT_ACTION_URL,
    DATA_INCONSISTENCY: "/admin_escolar/verificar_datos/",
    INVALID_RELATIONSHIP: "/admin_escolar/verificar_datos/",
    ORPHANED_ENTITY: "/admin_escolar/verificar_datos/",
    STATE_MISMATCH: "/admin_escolar/verificar_datos/",
    INVALID_STATE: "/admin_escolar/verificar_datos/",
}


# ============================================================================
# ErrorResponseBuilder - Construcción de Respuestas
# ============================================================================

class ErrorResponseBuilder:
    """
    Constructor centralizado de respuestas de error estructuradas.
    
    Responsabilidades:
    - Construir objetos de error consistentes
    - Traducir códigos a mensajes
    - Resolver URLs de acción
    - Integrar con Django messages framework
    
    Uso:
        error = ErrorResponseBuilder.build('MISSING_CICLO_ACTIVO')
        redirect_url = error['action_url']
        ErrorResponseBuilder.to_django_message(request, error)
    """
    
    @staticmethod
    def build(error_type, context=None):
        """
        Construye un objeto de error estructurado.
        
        Args:
            error_type (str): Constante de error (ej: MISSING_CICLO_ACTIVO)
            context (dict, optional): Contexto adicional para el error
            
        Returns:
            dict: {
                'error_type': str,
                'user_message': str,
                'action_url': str,
                'context': dict
            }
            
        Raises:
            KeyError: Si el error_type no está definido en ERROR_MESSAGES
        """
        if error_type not in ERROR_MESSAGES:
            raise KeyError(
                f"Error type '{error_type}' no está definido en ERROR_MESSAGES. "
                f"Agrega el mensaje correspondiente antes de usar este código."
            )
        
        context = context or {}
        
        return {
            'error_type': error_type,
            'user_message': ERROR_MESSAGES[error_type],
            'action_url': ErrorResponseBuilder._resolve_action_url(error_type, context),
            'context': context,
        }
    
    @staticmethod
    def _resolve_action_url(error_type, context):
        """
        Resuelve la URL de acción para un tipo de error.
        
        Args:
            error_type (str): Constante de error
            context (dict): Contexto que puede contener 'action_url' custom
            
        Returns:
            str: URL donde el usuario debe dirigirse
        """
        # Si el context tiene action_url explícito, usar ese
        if 'action_url' in context:
            return context['action_url']
        
        # Buscar URL por defecto del error
        return ERROR_ACTION_URLS.get(error_type, DEFAULT_ACTION_URL)
    
    @staticmethod
    def to_django_message(request, error_dict, level='error'):
        """
        Convierte un error estructurado a Django messages framework.
        
        Args:
            request: HttpRequest de Django
            error_dict (dict): Objeto de error construido con build()
            level (str): Nivel del mensaje ('error', 'warning', 'info')
            
        Returns:
            str: action_url para redirección
            
        Example:
            error = ErrorResponseBuilder.build('MISSING_CICLO_ACTIVO')
            redirect_url = ErrorResponseBuilder.to_django_message(request, error)
            return redirect(redirect_url)
        """
        level_map = {
            'error': messages.error,
            'warning': messages.warning,
            'info': messages.info,
            'success': messages.success,
        }
        
        message_func = level_map.get(level, messages.error)
        message_func(request, error_dict['user_message'])
        
        return error_dict['action_url']


# ============================================================================
# Helpers de Validación
# ============================================================================

def validate_error_type(error_type):
    """
    Valida que un tipo de error esté definido.
    
    Args:
        error_type (str): Constante de error
        
    Returns:
        bool: True si está definido
        
    Raises:
        KeyError: Si no está definido
    """
    if error_type not in ERROR_MESSAGES:
        raise KeyError(f"Error type '{error_type}' no definido")
    return True


def get_all_error_types():
    """
    Obtiene lista de todos los tipos de error definidos.
    
    Returns:
        list: Lista de constantes de error
    """
    return list(ERROR_MESSAGES.keys())


# ============================================================================
# GUÍA DE USO DE TIPOS DE ERROR
# ============================================================================

"""
DIFERENCIAS CLAVE: ERRORES DE SETUP vs ERRORES DE DATOS

┌─────────────────────────────────────────────────────────────────────────┐
│ ERRORES DE SETUP (Onboarding)                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ • MISSING_CICLO_ACTIVO - No existe ciclo académico activo              │
│ • MISSING_COURSES - No existen cursos creados                          │
│ • MISSING_TEACHERS_ASSIGNED - No hay profesores asignados              │
│ • MISSING_STUDENTS_ENROLLED - No hay estudiantes matriculados          │
│ • SCHOOL_NOT_CONFIGURED - Configuración inicial incompleta             │
│                                                                          │
│ CUÁNDO USAR:                                                            │
│ - El sistema está vacío o recién configurado                           │
│ - Falta completar pasos de configuración inicial                       │
│ - El usuario debe CREAR datos que no existen                           │
│                                                                          │
│ CARACTERÍSTICA:                                                         │
│ - Previenen operaciones cuando no hay datos base                       │
│ - Se resuelven CREANDO nuevos registros                                │
│ - Son temporales (desaparecen al completar setup)                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ ERRORES DE INTEGRIDAD DE DATOS                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ • DATA_INCONSISTENCY - Datos corruptos o contradictorios               │
│ • INVALID_RELATIONSHIP - Referencia a entidad inexistente/inactiva     │
│ • ORPHANED_ENTITY - Entidad sin padre válido                           │
│ • STATE_MISMATCH - Estados inconsistentes entre relacionados           │
│ • INVALID_STATE - Estado individual inválido para operación            │
│                                                                          │
│ CUÁNDO USAR:                                                            │
│ - Los datos YA EXISTEN pero están mal                                  │
│ - Hay relaciones rotas por eliminaciones/cambios                       │
│ - Estados no coherentes entre entidades relacionadas                   │
│                                                                          │
│ CARACTERÍSTICA:                                                         │
│ - Detectan problemas en datos existentes                               │
│ - Se resuelven CORRIGIENDO o LIMPIANDO datos                           │
│ - Indican problemas de calidad de datos                                │
└─────────────────────────────────────────────────────────────────────────┘

EJEMPLOS PRÁCTICOS:

❌ ERROR (Confundir tipos):
    # Matricula activa con curso inactivo
    if not Curso.objects.filter(activo=True).exists():
        raise MISSING_COURSES  # ¡MAL! Los cursos existen, solo están inactivos
        
✅ CORRECTO:
    if not Curso.objects.filter(activo=True).exists():
        if Curso.objects.exists():
            raise STATE_MISMATCH  # Hay cursos pero ninguno activo
        else:
            raise MISSING_COURSES  # Realmente no hay cursos


❌ ERROR:
    # User con rbd_colegio que no existe
    if user.rbd_colegio and not Colegio.objects.filter(rbd=user.rbd_colegio).exists():
        raise SCHOOL_NOT_CONFIGURED  # ¡MAL! El colegio no está "sin configurar"
        
✅ CORRECTO:
    if user.rbd_colegio and not Colegio.objects.filter(rbd=user.rbd_colegio).exists():
        raise ORPHANED_ENTITY  # El usuario referencia un colegio inexistente


❌ ERROR:
    # Matricula con estado='ACTIVA' pero curso.activo=False
    if matricula.estado == 'ACTIVA' and not matricula.curso.activo:
        raise INVALID_PREREQUISITE  # ¡MAL! No es un prerequisito, es inconsistencia
        
✅ CORRECTO:
    if matricula.estado == 'ACTIVA' and not matricula.curso.activo:
        raise STATE_MISMATCH  # Matricula activa con curso inactivo


REGLA GENERAL:
┌────────────────────────────────────────────────────────────────────┐
│ Si el error se resuelve CREANDO → Error de SETUP                  │
│ Si el error se resuelve CORRIGIENDO → Error de INTEGRIDAD         │
└────────────────────────────────────────────────────────────────────┘

ESPECÍFICOS DE INTEGRIDAD:

• DATA_INCONSISTENCY:
  - Uso: Cuando múltiples campos/registros tienen valores contradictorios
  - Ejemplo: Curso con fecha_inicio > fecha_fin
  - Ejemplo: Ciclo ACTIVO pero fecha_fin ya pasó

• INVALID_RELATIONSHIP:
  - Uso: FK apunta a registro que no existe o está inactivo
  - Ejemplo: Clase.profesor_id apunta a User inactivo
  - Ejemplo: Matricula.curso_id apunta a curso eliminado

• ORPHANED_ENTITY:
  - Uso: Registro existe pero su padre fue eliminado/desactivado
  - Ejemplo: User con rbd_colegio de colegio inexistente
  - Ejemplo: Evaluación de clase que ya no existe

• STATE_MISMATCH:
  - Uso: Estados de padre e hijo son incompatibles
  - Ejemplo: Matricula ACTIVA pero curso inactivo
  - Ejemplo: Clase activa pero ciclo_academico CERRADO

• INVALID_STATE:
  - Uso: Estado único de entidad no permite operación
  - Ejemplo: Intentar matricular en curso con estado='ELIMINADO'
  - Ejemplo: Crear evaluación en ciclo con estado='CERRADO'
"""

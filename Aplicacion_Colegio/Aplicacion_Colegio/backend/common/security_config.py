"""
Configuraciones de seguridad para Fase 4
Constantes y configuraciones centralizadas para validaciones de seguridad
"""
from decimal import Decimal


# ==================== CONFIGURACIONES DE SEGURIDAD ====================

# Límites financieros
MONTO_MAXIMO_BECA = Decimal('1000000')  # Monto máximo por beca
MONTO_MAXIMO_BOLETA = Decimal('5000000')  # Monto máximo por boleta
MONTO_MAXIMO_CUOTA = Decimal('2000000')  # Monto máximo por cuota

# Límites de texto
MAX_LONGITUD_DESCRIPCION = 500
MAX_LONGITUD_MOTIVO = 300
MAX_LONGITUD_OBSERVACIONES = 1000

# Límites temporales
DIAS_MAXIMO_VENCIMIENTO_CUOTA = 365  # Máximo 1 año para vencimiento de cuotas
DIAS_MAXIMO_DURACION_BECA = 365 * 4  # Máximo 4 años para becas

# Configuraciones de auditoría
AUDIT_CATEGORIAS = {
    'seguridad': 'seguridad',
    'estudiantes': 'estudiantes',
    'academico': 'academico',
    'financiero': 'estudiantes',  # Las operaciones financieras van en estudiantes
}

AUDIT_NIVELES = {
    'info': 'info',
    'warning': 'warning',
    'critical': 'critical',
}

# ==================== CONSTANTES DE VALIDACIÓN ====================

# Tipos válidos de beca
TIPOS_BECA_VALIDOS = [
    'merito_academico',
    'situacion_economica',
    'deporte',
    'arte',
    'otra'
]

# Estados válidos de boleta
ESTADOS_BOLETA_VALIDOS = [
    'pendiente',
    'pagada',
    'vencida',
    'anulada'
]

# Estados válidos de beca
ESTADOS_BECA_VALIDOS = [
    'SOLICITADA',
    'EN_REVISION',
    'APROBADA',
    'VIGENTE',
    'RECHAZADA',
    'VENCIDA',
    'CANCELADA'
]

# ==================== CONFIGURACIONES DE RATE LIMITING ====================

# Límite de operaciones por hora por usuario
RATE_LIMITS = {
    'crear_beca': 10,  # máximo 10 becas por hora
    'crear_boleta': 50,  # máximo 50 boletas por hora
    'aprobar_beca': 20,  # máximo 20 aprobaciones por hora
    'modificar_cuota': 30,  # máximo 30 modificaciones por hora
}

# ==================== CONFIGURACIONES DE ENCRIPTACIÓN ====================

# Algoritmos de encriptación permitidos
ENCRYPTION_ALGORITHMS = [
    'AES-256-GCM',
    'RSA-2048',
]

# ==================== CONFIGURACIONES DE AUTENTICACIÓN ====================

# Tiempo de expiración de tokens (en segundos)
TOKEN_EXPIRATION_TIME = 3600  # 1 hora

# Número máximo de intentos de login fallidos
MAX_LOGIN_ATTEMPTS = 5

# Tiempo de bloqueo después de intentos fallidos (en minutos)
LOGIN_BLOCK_TIME = 15

# ==================== FUNCIONES DE VALIDACIÓN DE SEGURIDAD ====================

def validar_monto_financiero(monto, tipo_operacion, max_monto=None):
    """
    Valida montos financieros según el tipo de operación

    Args:
        monto (Decimal): Monto a validar
        tipo_operacion (str): Tipo de operación ('beca', 'boleta', 'cuota')
        max_monto (Decimal, optional): Monto máximo personalizado

    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if max_monto is None:
        limites = {
            'beca': MONTO_MAXIMO_BECA,
            'boleta': MONTO_MAXIMO_BOLETA,
            'cuota': MONTO_MAXIMO_CUOTA,
        }
        max_monto = limites.get(tipo_operacion, Decimal('1000000'))

    if monto <= 0:
        return False, "El monto debe ser mayor a cero"

    if monto > max_monto:
        return False, f"El monto excede el límite permitido de ${max_monto}"

    return True, None


def validar_texto_seguro(texto, max_longitud=None, campo="texto"):
    """
    Valida que el texto no contenga caracteres peligrosos y respete longitud

    Args:
        texto (str): Texto a validar
        max_longitud (int, optional): Longitud máxima permitida
        campo (str): Nombre del campo para mensajes de error

    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if not texto:
        return True, None  # Permitir textos vacíos

    if max_longitud and len(texto) > max_longitud:
        return False, f"El campo {campo} no puede exceder {max_longitud} caracteres"

    # Validar caracteres peligrosos (scripting, HTML, etc.)
    import re
    if re.search(r'[<>]', texto):
        return False, f"El campo {campo} contiene caracteres no permitidos"

    return True, None


def validar_fecha_futura(fecha, max_dias=None, campo="fecha"):
    """
    Valida que una fecha no sea en el pasado y no exceda límites

    Args:
        fecha (date): Fecha a validar
        max_dias (int, optional): Máximo número de días en el futuro
        campo (str): Nombre del campo para mensajes de error

    Returns:
        tuple: (es_valido, mensaje_error)
    """
    from django.utils import timezone

    hoy = timezone.now().date()

    if fecha < hoy:
        return False, f"La {campo} no puede ser en el pasado"

    if max_dias and (fecha - hoy).days > max_dias:
        return False, f"La {campo} no puede ser más de {max_dias} días en el futuro"

    return True, None


def validar_acceso_multi_tenant(user, rbd_solicitado):
    """
    Valida acceso multi-tenant básico

    Args:
        user: Usuario de Django
        rbd_solicitado: RBD del colegio solicitado

    Returns:
        tuple: (tiene_acceso, mensaje_error)
    """
    from backend.common.services.policy_service import PolicyService

    if not user or not user.is_authenticated:
        return False, "Usuario no autenticado"

    # Administrador de sistema tiene acceso global
    if PolicyService.has_capability(user, 'SYSTEM_ADMIN'):
        return True, None

    # Otros roles solo acceden a su colegio
    if user.rbd_colegio != rbd_solicitado:
        return False, "No tiene acceso a este colegio"

    return True, None
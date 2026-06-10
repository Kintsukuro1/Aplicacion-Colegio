"""
Servicios de seguridad — Semana 7-8.

1. Cifrado at-rest de datos sensibles (NEE/PIE, alergias, condiciones médicas)
2. Auditoría de acceso a datos confidenciales
3. Historial de contraseñas (no reutilización)
"""
import hashlib
import logging
from base64 import b64decode, b64encode
from functools import wraps

from django.conf import settings

from backend.apps.auditoria.models import AuditoriaEvento
from backend.apps.security.models import ActiveSession, PasswordHistory

logger = logging.getLogger('security')


# ═══════════════════════════════════════════════
# 1. CIFRADO AT-REST PARA CAMPOS SENSIBLES
# ═══════════════════════════════════════════════

class FieldEncryption:
    """
    Cifrado simétrico usando Fernet (cryptography).
    Fallback a base64 si la librería no está instalada.

    Uso: cifrar datos NEE/PIE, alergias y condiciones médicas
    que deben protegerse según Ley 19.628 (Protección de Datos Personales Chile).
    """
    _fernet = None

    @classmethod
    def _get_fernet(cls):
        if cls._fernet is None:
            try:
                from cryptography.fernet import Fernet
                key = hashlib.sha256(
                    settings.SECRET_KEY.encode('utf-8')
                ).digest()
                cls._fernet = Fernet(b64encode(key))
            except ImportError:
                cls._fernet = False
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Cifra un texto. Retorna string prefijado con 'enc::'."""
        if not plaintext:
            return plaintext
        fernet = cls._get_fernet()
        if fernet and fernet is not False:
            encrypted = fernet.encrypt(plaintext.encode('utf-8'))
            return f'enc::{encrypted.decode("utf-8")}'
        encoded = b64encode(plaintext.encode('utf-8')).decode('utf-8')
        return f'b64::{encoded}'

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """Descifra un texto cifrado."""
        if not ciphertext:
            return ciphertext
        if ciphertext.startswith('enc::'):
            fernet = cls._get_fernet()
            if fernet and fernet is not False:
                try:
                    return fernet.decrypt(
                        ciphertext[5:].encode('utf-8')
                    ).decode('utf-8')
                except Exception:
                    logger.error('Error descifrando campo — posible cambio de SECRET_KEY')
                    return '[DATOS CIFRADOS — ERROR DE DESCIFRADO]'
        if ciphertext.startswith('b64::'):
            try:
                return b64decode(ciphertext[5:]).decode('utf-8')
            except Exception:
                return ciphertext
        return ciphertext

    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        """Verifica si un valor ya está cifrado."""
        if not value:
            return False
        return value.startswith('enc::') or value.startswith('b64::')


# ═══════════════════════════════════════════════
# 2. AUDITORÍA DE ACCESO A DATOS CONFIDENCIALES
# ═══════════════════════════════════════════════

SENSITIVE_FIELDS = {
    'PerfilEstudiante': [
        'alergias', 'condiciones_medicas', 'descripcion_nee',
        'grupo_sanguineo', 'contacto_emergencia', 'contacto_emergencia_telefono',
    ],
    'EntrevistaOrientacion': ['motivo', 'observaciones', 'acuerdos'],
    'DerivacionExterna': ['motivo', 'diagnostico', 'observaciones'],
}


def audit_sensitive_access(model_name: str, object_id, user, fields_accessed: list = None, ip: str = ''):
    """
    Registra en AuditoriaEvento el acceso a datos confidenciales.
    """
    try:
        role_name = getattr(getattr(user, 'role', None), 'nombre', '') if user else ''
        AuditoriaEvento.objects.create(
            accion='ACCESO_DATOS_SENSIBLES',
            categoria='SEGURIDAD',
            descripcion=f'Acceso a datos confidenciales de {model_name} #{object_id}',
            usuario_id=user.id if user else None,
            usuario_rut=getattr(user, 'rut', '') or '' if user else '',
            usuario_nombre=user.get_full_name() if user else '',
            usuario_email=getattr(user, 'email', '') if user else '',
            usuario_rol=role_name,
            colegio_rbd=str(getattr(user, 'rbd_colegio', '') or '') if user else '',
            ip_address=ip or '127.0.0.1',
            metadata={
                'modelo': model_name,
                'object_id': str(object_id),
                'campos_accedidos': fields_accessed or [],
            },
        )
    except Exception as e:
        logger.error(f'Error registrando auditoría de datos sensibles: {e}')


def audit_sensitive_view(model_name: str):
    """
    Decorador para vistas que retornan datos confidenciales.
    Registra automáticamente quién accedió y a qué campos.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                object_id = kwargs.get('pk') or kwargs.get('student_id') or 'list'
                ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
                    or request.META.get('REMOTE_ADDR', '')
                audit_sensitive_access(
                    model_name=model_name,
                    object_id=object_id,
                    user=request.user,
                    fields_accessed=SENSITIVE_FIELDS.get(model_name, []),
                    ip=ip,
                )
            return response
        return wrapper
    return decorator


# ═══════════════════════════════════════════════
# 3. HISTORIAL DE CONTRASEÑAS
# ═══════════════════════════════════════════════

PASSWORD_HISTORY_DEPTH = 5


def check_password_reuse(user, raw_password: str) -> bool:
    """
    Verifica si el password fue usado recientemente.
    Returns True si reutilizado (debe bloquearse).
    """
    from django.contrib.auth.hashers import check_password

    recent = PasswordHistory.objects.filter(
        user=user
    ).order_by('-created_at')[:PASSWORD_HISTORY_DEPTH]

    for entry in recent:
        if check_password(raw_password, entry.password_hash):
            return True
    return False


def record_password_change(user, raw_password: str):
    """Registra el password actual en el historial tras un cambio."""
    from django.contrib.auth.hashers import make_password

    PasswordHistory.objects.create(
        user=user,
        password_hash=make_password(raw_password),
    )

    old_entries = PasswordHistory.objects.filter(
        user=user
    ).order_by('-created_at')[PASSWORD_HISTORY_DEPTH:]
    if old_entries.exists():
        PasswordHistory.objects.filter(
            id__in=old_entries.values_list('id', flat=True)
        ).delete()

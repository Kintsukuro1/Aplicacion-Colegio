"""
Modelos de seguridad — Semana 7-8.

1. PasswordHistory — Historial de contraseñas para prevenir reutilización
2. ActiveSession — Sesiones activas por dispositivo con revocación remota
"""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

import logging

logger = logging.getLogger('security')


class PasswordHistory(models.Model):
    """
    Almacena hashes de contraseñas anteriores para prevenir reutilización.
    Según buenas prácticas: no repetir las últimas N contraseñas.
    """
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='password_history'
    )
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'security_password_history'
        ordering = ['-created_at']
        verbose_name = 'Historial de Contraseña'
        verbose_name_plural = 'Historial de Contraseñas'

    def __str__(self):
        return f'{self.user.email} — {self.created_at:%Y-%m-%d}'


class ActiveSession(models.Model):
    """
    Registro de sesiones activas por dispositivo.
    Permite al usuario ver desde dónde se ha conectado y cerrar sesiones remotas.
    """
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='active_sessions'
    )
    token_jti = models.CharField(
        max_length=64, unique=True,
        help_text='JTI del refresh token activo'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default='')
    device_type = models.CharField(
        max_length=20, default='unknown',
        choices=[
            ('desktop', 'Escritorio'),
            ('mobile', 'Móvil'),
            ('tablet', 'Tablet'),
            ('unknown', 'Desconocido'),
        ]
    )
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'security_active_session'
        ordering = ['-last_activity']
        verbose_name = 'Sesión Activa'
        verbose_name_plural = 'Sesiones Activas'

    def __str__(self):
        return f'{self.user.email} — {self.device_type} — {self.ip_address}'

    @staticmethod
    def detect_device_type(user_agent: str) -> str:
        ua_lower = (user_agent or '').lower()
        if any(m in ua_lower for m in ('iphone', 'android', 'mobile')):
            return 'mobile'
        if any(t in ua_lower for t in ('ipad', 'tablet')):
            return 'tablet'
        return 'desktop'

    @classmethod
    def register_session(cls, user, token_jti: str, request):
        """Registra una nueva sesión tras login exitoso."""
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
            or request.META.get('REMOTE_ADDR', '0.0.0.0')
        ua = request.META.get('HTTP_USER_AGENT', '')

        return cls.objects.update_or_create(
            token_jti=token_jti,
            defaults={
                'user': user,
                'ip_address': ip,
                'user_agent': ua,
                'device_type': cls.detect_device_type(ua),
                'is_active': True,
            }
        )

    @classmethod
    def revoke_session(cls, user, session_id: int) -> bool:
        """Revoca una sesión activa (cierre remoto)."""
        try:
            session = cls.objects.get(id=session_id, user=user, is_active=True)
            session.is_active = False
            session.save(update_fields=['is_active'])

            # Intentar blacklistear el token
            try:
                from rest_framework_simplejwt.token_blacklist.models import (
                    BlacklistedToken,
                    OutstandingToken,
                )
                outstanding = OutstandingToken.objects.filter(jti=session.token_jti).first()
                if outstanding:
                    BlacklistedToken.objects.get_or_create(token=outstanding)
            except Exception:
                pass

            logger.info(f'Sesión revocada — user={user.email} session={session_id}')
            return True
        except cls.DoesNotExist:
            return False

    @classmethod
    def cleanup_expired(cls, days: int = 30):
        """Limpia sesiones inactivas antiguas."""
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = cls.objects.filter(
            last_activity__lt=cutoff
        ).delete()
        if deleted:
            logger.info(f'Sesiones expiradas eliminadas: {deleted}')

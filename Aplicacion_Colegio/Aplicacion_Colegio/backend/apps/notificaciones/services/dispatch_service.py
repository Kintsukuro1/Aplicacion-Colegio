import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

from backend.apps.notificaciones.models import DispositivoMovil, PreferenciaNotificacion
from backend.apps.notificaciones.services.email_service import NotificationEmailService
from backend.apps.notificaciones.services.push_service import NotificationPushService

logger = logging.getLogger(__name__)


class NotificationDispatchService:
    """Servicio central de entrega multi-canal de notificaciones."""

    @staticmethod
    def _group_name_for_user(user_id: int) -> str:
        return f'notificaciones_user_{user_id}'

    @staticmethod
    def _build_payload(notification) -> dict:
        return {
            'id': notification.id,
            'tipo': notification.tipo,
            'titulo': notification.titulo,
            'mensaje': notification.mensaje,
            'enlace': notification.enlace,
            'prioridad': notification.prioridad,
            'leido': notification.leido,
            'fecha_creacion': notification.fecha_creacion.isoformat() if notification.fecha_creacion else None,
        }

    @classmethod
    def dispatch_realtime(cls, notification) -> None:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        payload = cls._build_payload(notification)
        async_to_sync(channel_layer.group_send)(
            cls._group_name_for_user(notification.destinatario_id),
            {
                'type': 'notification.message',
                'payload': payload,
            },
        )

    @classmethod
    def dispatch_channels(cls, notification) -> dict:
        lock_key = f"notification_dispatch_lock:{notification.id}"
        if not cache.add(lock_key, '1', timeout=30):
            return {
                'email_sent': False,
                'push': {'sent': 0, 'failed': 0, 'disabled': True},
                'skipped': 'duplicate_dispatch_locked',
            }

        # Siempre distribuir en tiempo real para UI web/movil conectada.
        try:
            cls.dispatch_realtime(notification)

            preference = PreferenciaNotificacion.obtener_o_crear_defecto(
                notification.destinatario,
                notification.tipo,
            )

            result = {
                'email_sent': False,
                'push': {'sent': 0, 'failed': 0, 'disabled': True},
            }

            if preference.puede_enviar_por_canal('email'):
                try:
                    result['email_sent'] = NotificationEmailService.send_notification_email(notification)
                except Exception:
                    logger.exception('Error enviando email transaccional de notificacion id=%s', notification.id)

            if preference.puede_enviar_por_canal('push'):
                devices = list(
                    DispositivoMovil.objects.filter(
                        usuario=notification.destinatario,
                        activo=True,
                    )
                )
                result['push'] = NotificationPushService.send_to_devices(notification, devices)

            return result
        finally:
            cache.delete(lock_key)

    @classmethod
    def dispatch_bulk(cls, notifications) -> None:
        for notification in notifications:
            try:
                cls.dispatch_channels(notification)
            except Exception:
                logger.exception('Error despachando notificacion bulk id=%s', getattr(notification, 'id', None))

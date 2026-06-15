import logging
from importlib import import_module

from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationPushService:
    """Entrega push usando Firebase Cloud Messaging (FCM)."""

    _initialized = False
    _enabled = False

    @classmethod
    def _bootstrap_firebase(cls):
        if cls._initialized:
            return

        cls._initialized = True
        try:
            firebase_admin = import_module('firebase_admin')
            credentials = import_module('firebase_admin.credentials')

            cred_file = getattr(settings, 'FCM_CREDENTIALS_FILE', '').strip()
            cred_json = getattr(settings, 'FCM_CREDENTIALS_JSON', '').strip()

            if not cred_file and not cred_json:
                logger.info('FCM no configurado: faltan credenciales.')
                cls._enabled = False
                return

            if not firebase_admin._apps:
                if cred_file:
                    cred = credentials.Certificate(cred_file)
                else:
                    cred = credentials.Certificate(cred_json)
                firebase_admin.initialize_app(cred)

            cls._enabled = True
        except Exception:
            logger.exception('No fue posible inicializar Firebase Admin SDK.')
            cls._enabled = False

    @classmethod
    def send_to_devices(cls, notification, devices):
        cls._bootstrap_firebase()
        if not cls._enabled:
            return {'sent': 0, 'failed': len(devices), 'disabled': True}

        try:
            messaging = import_module('firebase_admin.messaging')
        except Exception:
            logger.exception('Firebase Admin SDK no disponible en runtime.')
            return {'sent': 0, 'failed': len(devices), 'disabled': True}

        sent = 0
        failed = 0

        for device in devices:
            token = (device.token_fcm or '').strip()
            if not token:
                failed += 1
                continue

            message = messaging.Message(
                token=token,
                notification=messaging.Notification(
                    title=notification.titulo,
                    body=notification.mensaje[:200],
                ),
                data={
                    'notification_id': str(notification.id),
                    'tipo': notification.tipo,
                    'prioridad': notification.prioridad,
                    'enlace': notification.enlace or '',
                },
            )

            try:
                messaging.send(message)
                sent += 1
                device.total_notificaciones_enviadas += 1
                device.save(update_fields=['total_notificaciones_enviadas', 'ultima_actividad'])
            except Exception:
                failed += 1
                device.total_notificaciones_fallidas += 1
                device.save(update_fields=['total_notificaciones_fallidas', 'ultima_actividad'])
                logger.exception('Error enviando push a dispositivo id=%s', device.id)

        return {'sent': sent, 'failed': failed, 'disabled': False}

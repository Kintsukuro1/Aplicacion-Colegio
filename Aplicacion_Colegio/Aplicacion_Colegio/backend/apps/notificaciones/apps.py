from django.apps import AppConfig


class NotificacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.apps.notificaciones'

    def ready(self):
        # Registra listeners de eventos del modulo (post_save Notificacion).
        import backend.apps.notificaciones.signals  # noqa: F401

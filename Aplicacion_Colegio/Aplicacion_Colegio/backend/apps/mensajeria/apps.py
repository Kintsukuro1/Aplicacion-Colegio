from django.apps import AppConfig


class MensajeriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.apps.mensajeria'

    def ready(self):
        from . import signals  # noqa: F401

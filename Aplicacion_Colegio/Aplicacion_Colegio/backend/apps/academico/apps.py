from django.apps import AppConfig


class AcademicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.apps.academico'

    def ready(self):
        from . import signals  # noqa: F401

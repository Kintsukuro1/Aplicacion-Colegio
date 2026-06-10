from django.apps import AppConfig


class ComunicadosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.apps.comunicados'
    verbose_name = 'Comunicados y Circulares'
    
    def ready(self):
        from . import signals

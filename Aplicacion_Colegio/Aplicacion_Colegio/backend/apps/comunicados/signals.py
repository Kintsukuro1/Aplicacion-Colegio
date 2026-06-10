# comunicados/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Comunicado
from backend.apps.comunicados.services.comunicados_service import ComunicadosService


@receiver(post_save, sender=Comunicado)
def notificar_nuevo_comunicado(sender, instance, created, **kwargs):
    """
    Crea notificaciones para los destinatarios cuando se publica un comunicado.
    """
    if not created:
        return

    ComunicadosService.notify_new_comunicado(instance)

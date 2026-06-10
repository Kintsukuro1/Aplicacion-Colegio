from django.db.models.signals import post_save
from django.dispatch import receiver

from backend.apps.notificaciones.models import Notificacion
from backend.apps.notificaciones.services.dispatch_service import NotificationDispatchService


@receiver(post_save, sender=Notificacion)
def dispatch_notification_channels(sender, instance, created, **kwargs):
    if not created:
        return
    NotificationDispatchService.dispatch_channels(instance)

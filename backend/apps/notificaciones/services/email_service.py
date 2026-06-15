from django.conf import settings
from django.core.mail import send_mail


class NotificationEmailService:
    """Entrega de notificaciones por correo electronico."""

    @staticmethod
    def send_notification_email(notification) -> bool:
        if not getattr(settings, 'NOTIFICATIONS_EMAIL_ENABLED', True):
            return False

        user = notification.destinatario
        if not getattr(user, 'email', None):
            return False

        subject = f"[Colegio] {notification.titulo}"
        message = (
            f"{notification.mensaje}\n\n"
            f"Tipo: {notification.get_tipo_display()}\n"
            f"Prioridad: {notification.get_prioridad_display()}\n"
        )
        if notification.enlace:
            message += f"Enlace: {notification.enlace}\n"

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True

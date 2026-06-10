"""
Servicio de notificaciones para el sistema de onboarding
Gestiona la creación y verificación de notificaciones de configuración pendiente
"""
from datetime import datetime, timedelta
from django.utils import timezone
from backend.apps.notificaciones.models import Notificacion
from backend.common.services.onboarding_service import OnboardingService


class OnboardingNotificationService:
    """Servicio para gestionar notificaciones del sistema de onboarding"""
    
    # Cooldown period: no enviar notificaciones más frecuentemente que esto
    NOTIFICATION_COOLDOWN_HOURS = 24
    
    @classmethod
    def should_notify_setup_incomplete(cls, user, escuela_rbd):
        """
        Determina si se debe notificar al usuario sobre configuración incompleta
        
        Args:
            user: Usuario a notificar
            escuela_rbd: RBD del colegio
            
        Returns:
            tuple (bool, dict): (debe_notificar, setup_status)
        """
        # Verificar estado de configuración
        setup_status = OnboardingService.get_setup_status(escuela_rbd)
        
        # Si está completo, no notificar
        if setup_status['setup_complete']:
            return False, setup_status
        
        # Verificar si ya existe una notificación reciente no leída
        cooldown_time = timezone.now() - timedelta(hours=cls.NOTIFICATION_COOLDOWN_HOURS)
        recent_notifications = Notificacion.objects.filter(
            destinatario=user,
            tipo='sistema',
            titulo__icontains='Configuración Inicial',
            fecha_creacion__gte=cooldown_time
        ).exists()
        
        # No notificar si ya hay una notificación reciente
        if recent_notifications:
            return False, setup_status
        
        return True, setup_status
    
    @classmethod
    def create_setup_notification(cls, user, setup_status):
        """
        Crea una notificación informando sobre la configuración incompleta
        
        Args:
            user: Usuario a notificar
            setup_status: Estado de configuración del OnboardingService
            
        Returns:
            Notificacion: Notificación creada
        """
        # Contar pasos pendientes
        pending_steps = [
            step['nombre'] 
            for step in setup_status['steps'] 
            if not step['completado']
        ]
        
        pending_count = len(pending_steps)
        total_steps = len(setup_status['steps'])
        
        # Construir mensaje
        if pending_count == total_steps:
            titulo = "🚀 Completa la Configuración Inicial del Colegio"
            mensaje = (
                f"Bienvenido/a. Para comenzar a usar el sistema, necesitas completar "
                f"{pending_count} pasos de configuración inicial:\n\n"
                f"{'  • ' + chr(10) + '  • '.join(pending_steps)}\n\n"
                f"Haz clic aquí para ver el checklist de configuración."
            )
        else:
            completed_count = total_steps - pending_count
            titulo = "⚙️ Configuración Inicial Incompleta"
            mensaje = (
                f"Has completado {completed_count} de {total_steps} pasos de configuración.\n\n"
                f"Pasos pendientes:\n"
                f"{'  • ' + chr(10) + '  • '.join(pending_steps)}\n\n"
                f"Completa la configuración para desbloquear todas las funcionalidades."
            )
        
        # Crear notificación
        notificacion = Notificacion.objects.create(
            destinatario=user,
            tipo='sistema',
            titulo=titulo,
            mensaje=mensaje,
            enlace='/setup/checklist/',
            prioridad='alta',
            leido=False
        )
        
        return notificacion
    
    @classmethod
    def notify_if_needed(cls, user, escuela_rbd):
        """
        Verifica y crea notificación si es necesario
        
        Args:
            user: Usuario a notificar
            escuela_rbd: RBD del colegio
            
        Returns:
            Notificacion | None: Notificación creada o None si no se creó
        """
        should_notify, setup_status = cls.should_notify_setup_incomplete(user, escuela_rbd)
        
        if should_notify:
            return cls.create_setup_notification(user, setup_status)
        
        return None

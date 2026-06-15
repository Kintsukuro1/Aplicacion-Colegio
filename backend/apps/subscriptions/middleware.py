"""
Middleware de Suscripción
=========================

Inyecta información de suscripción en el request para que esté disponible
en todas las vistas sin necesidad de consultar la BD cada vez.
"""

from django.utils.deprecation import MiddlewareMixin
from backend.apps.subscriptions.models import Subscription, UsageLog


class SubscriptionMiddleware(MiddlewareMixin):
    """
    Middleware que agrega información de suscripción al request.
    
    Agrega los siguientes atributos al request:
    - request.subscription: Objeto Subscription del colegio actual
    - request.plan: Objeto Plan de la suscripción
    - request.usage: Objeto UsageLog del período actual
    - request.is_tester: Boolean, True si es plan TESTER ilimitado
    - request.is_trial: Boolean, True si es plan TRIAL
    """
    
    def process_request(self, request):
        # Solo para usuarios autenticados
        if not request.user.is_authenticated:
            request.subscription = None
            request.plan = None
            request.usage = None
            request.is_tester = False
            request.is_trial = False
            return
        
        # Administradores generales (sin RBD) no tienen suscripción
        if request.user.rbd_colegio is None:
            request.subscription = None
            request.plan = None
            request.usage = None
            request.is_tester = False
            request.is_trial = False
            request.is_admin_general = True
            return
        
        request.is_admin_general = False
        
        # Obtener la suscripción del colegio
        try:
            subscription = Subscription.objects.select_related('plan').get(
                colegio__rbd=request.user.rbd_colegio
            )
            request.subscription = subscription
            request.plan = subscription.plan
            request.is_tester = subscription.plan.is_unlimited
            request.is_trial = subscription.plan.is_trial
            
            # Obtener el registro de uso del período actual
            request.usage = UsageLog.get_current_period(subscription)
            
        except Subscription.DoesNotExist:
            # No debería pasar si el signal funciona correctamente,
            # pero por seguridad establecemos None
            request.subscription = None
            request.plan = None
            request.usage = None
            request.is_tester = False
            request.is_trial = False

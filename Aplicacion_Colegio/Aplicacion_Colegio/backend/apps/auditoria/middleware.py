"""
Middleware de Auditoría
Captura el usuario y request actual para usarlo en las señales.
"""

from backend.apps.auditoria.signals import set_current_user, set_current_request


class AuditoriaMiddleware:
    """
    Middleware que captura el usuario y request actual
    para que las señales puedan registrar quién hizo cada acción.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Establecer usuario y request en thread-local storage
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)
        
        set_current_request(request)
        
        response = self.get_response(request)
        
        # Limpiar después de la request
        set_current_user(None)
        set_current_request(None)
        
        return response

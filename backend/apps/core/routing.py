"""
Configuración de routing principal para Django Channels
Maneja tanto HTTP como WebSocket
"""
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

# Aplicación ASGI para Django (HTTP)
django_asgi_app = get_asgi_application()

# Importar routing de apps
try:
    import backend.apps.notificaciones.routing as notificaciones_routing
    websocket_patterns = notificaciones_routing.websocket_urlpatterns
except ImportError:
    # Si no existe el módulo, usar lista vacía
    websocket_patterns = []

# Configuración del router de protocolos
application = ProtocolTypeRouter({
    # HTTP tradicional
    "http": django_asgi_app,
    
    # WebSocket con autenticación y validación de hosts
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_patterns)
        )
    ),
})

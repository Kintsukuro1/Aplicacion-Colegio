from django.urls import path

from backend.apps.mensajeria import views
from backend.apps.mensajeria.views.nueva_conversacion import crear_nueva_conversacion

app_name = 'mensajeria'

urlpatterns = [
    # Bandeja
    path('bandeja/', views.bandeja_mensajes, name='bandeja_mensajes'),

    # Alias usado por algunos templates legacy
    path('mensajes/', views.bandeja_mensajes, name='mensajes'),

    # Crear nueva conversación
    path('nueva/', crear_nueva_conversacion, name='crear_nueva_conversacion'),

    # Conversación
    path('conversacion/<int:id_conversacion>/', views.ver_conversacion, name='ver_conversacion'),

    # Embebido por clase
    path('clase/<int:id_clase>/mensajes/', views.mensajes_clase, name='mensajes_clase'),
]

# comunicados/urls.py
from django.urls import path
from . import views

app_name = 'comunicados'

urlpatterns = [
    # URLs originales
    path('', views.lista_comunicados, name='lista'),
    path('<int:comunicado_id>/', views.detalle_comunicado, name='detalle'),
    path('crear/', views.crear_comunicado, name='crear'),
    path('<int:comunicado_id>/estadisticas/', views.estadisticas_comunicado, name='estadisticas'),
    
    # Confirmaciones masivas
    path('<int:comunicado_id>/confirmaciones-masivas/', views.confirmaciones_masivas, name='confirmaciones_masivas'),
    path('<int:comunicado_id>/enviar-recordatorio/', views.enviar_recordatorio_masivo, name='enviar_recordatorio'),
    
    # Estadísticas avanzadas
    path('<int:comunicado_id>/dashboard/', views.estadisticas_dashboard, name='dashboard'),
    
    # Plantillas
    path('plantillas/', views.lista_plantillas, name='plantillas'),
    path('plantillas/crear/', views.crear_plantilla, name='crear_plantilla'),
    path('plantillas/<int:plantilla_id>/editar/', views.editar_plantilla, name='editar_plantilla'),
    path('plantillas/<int:plantilla_id>/eliminar/', views.eliminar_plantilla, name='eliminar_plantilla'),
    path('plantillas/<int:plantilla_id>/usar/', views.usar_plantilla, name='usar_plantilla'),
]

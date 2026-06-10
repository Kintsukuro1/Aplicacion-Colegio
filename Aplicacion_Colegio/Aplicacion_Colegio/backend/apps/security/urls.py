"""
FASE 15: Security URLs Configuration
Security monitoring and IP unblocking routes
"""

from django.urls import path
from backend.apps.security.views import (
    monitoreo_seguridad,
    desbloquear_ip,
)

urlpatterns = [
    # Security monitoring (FASE 15)
    path('monitoreo/', monitoreo_seguridad, name='monitoreo_seguridad'),
    path('desbloquear-ip/', desbloquear_ip, name='desbloquear_ip'),
]

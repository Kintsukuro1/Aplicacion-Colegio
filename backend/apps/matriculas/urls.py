from django.urls import path

from backend.apps.matriculas import views

app_name = 'matriculas'

urlpatterns = [
    path('mi-estado-cuenta/', views.mi_estado_cuenta, name='mi_estado_cuenta'),
    path('mis-pagos/', views.mis_pagos, name='mis_pagos'),
]

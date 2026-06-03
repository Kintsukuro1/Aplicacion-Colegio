"""
URLs del módulo accounts refactorizado
"""
from django.urls import path
from backend.apps.accounts.views import auth, profile, student

app_name = 'accounts'

urlpatterns = [
    # Autenticación
    path('', auth.index, name='index'),
    path('login/', auth.login_view, name='login'),
    path('login/staff/', auth.login_staff_view, name='login_staff'),
    path('logout/', auth.logout_view, name='logout'),
    
    # Perfiles
    path('perfil/estudiante/actualizar/', profile.actualizar_perfil_estudiante, name='actualizar_perfil_estudiante'),
    path('perfil/profesor/actualizar/', profile.actualizar_perfil_profesor, name='actualizar_perfil_profesor'),
    path('perfil/estudiante/cambiar-password/', profile.cambiar_password_estudiante, name='cambiar_password_estudiante'),
    path('perfil/profesor/cambiar-password/', profile.cambiar_password_profesor, name='cambiar_password_profesor'),
    
    # Gestión de Estudiantes (Admin)
    path('estudiantes/gestionar/', student.gestionar_estudiantes, name='accounts_gestionar_estudiantes'),
]

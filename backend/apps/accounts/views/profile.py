"""
Profile Views - Vistas ligeras para gestión de perfiles
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import update_session_auth_hash
from axes.helpers import get_client_ip_address

from backend.apps.accounts.services.profile_service import ProfileService
from backend.apps.accounts.models import User


def _redirect_perfil():
    return redirect(f"{reverse('dashboard')}?pagina=perfil")


@login_required()
def actualizar_perfil_estudiante(request):
    """Actualiza contacto y datos editables del perfil del estudiante."""
    if request.method != 'POST':
        return _redirect_perfil()

    if request.POST.get('eliminar_foto'):
        success, message = ProfileService.remove_student_photo(request.user)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return _redirect_perfil()

    if request.FILES.get('foto_perfil'):
        success, message = ProfileService.upload_student_photo(
            request.user,
            request.FILES['foto_perfil'],
        )
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return _redirect_perfil()

    data = {
        'email': request.POST.get('email', ''),
        'telefono': request.POST.get('telefono', ''),
        'telefono_movil': request.POST.get('telefono_movil', ''),
        'direccion': request.POST.get('direccion', ''),
        'contacto_emergencia_nombre': request.POST.get('contacto_emergencia_nombre', ''),
        'contacto_emergencia_relacion': request.POST.get('contacto_emergencia_relacion', ''),
        'contacto_emergencia_telefono': request.POST.get('contacto_emergencia_telefono', ''),
    }
    success, message = ProfileService.update_own_student_profile(
        user=request.user,
        data=data,
        User=User,
    )
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return _redirect_perfil()


@login_required()
def actualizar_perfil_profesor(request):
    """Vista para actualizar el perfil de un profesor o administrador."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()

        success, message = ProfileService.update_staff_profile(
            user=request.user,
            email=email,
            telefono=telefono,
            direccion=direccion,
            User=User,
        )
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

    return _redirect_perfil()


@login_required()
@ratelimit(key='user', rate='5/h', method='POST', block=True)
def cambiar_password_estudiante(request):
    """Cambio de contraseña por el propio estudiante."""
    if request.method == 'POST':
        password_actual = request.POST.get('password_actual')
        password_nueva = request.POST.get('password_nueva')
        password_confirmar = request.POST.get('password_confirmar')
        client_ip = get_client_ip_address(request)

        success, message = ProfileService.change_own_student_password(
            user=request.user,
            password_actual=password_actual,
            password_nueva=password_nueva,
            password_confirmar=password_confirmar,
            client_ip=client_ip,
        )
        if success:
            update_session_auth_hash(request, request.user)
            messages.success(request, message)
        else:
            messages.error(request, message)

    return _redirect_perfil()


@login_required()
@ratelimit(key='user', rate='5/h', method='POST', block=True)
def cambiar_password_profesor(request):
    """Cambio de contraseña para profesor o administrador."""
    if request.method == 'POST':
        password_actual = request.POST.get('password_actual')
        password_nueva = request.POST.get('password_nueva')
        password_confirmar = request.POST.get('password_confirmar')
        client_ip = get_client_ip_address(request)

        success, message = ProfileService.change_staff_password(
            user=request.user,
            password_actual=password_actual,
            password_nueva=password_nueva,
            password_confirmar=password_confirmar,
            client_ip=client_ip,
        )
        if success:
            update_session_auth_hash(request, request.user)
            messages.success(request, message)
        else:
            messages.error(request, message)

    return _redirect_perfil()

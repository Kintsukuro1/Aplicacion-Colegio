"""
Vistas de autenticación - Solo orquestación, sin lógica de negocio
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from datetime import datetime
from backend.apps.accounts.services.auth_service import AuthService

from backend.apps.accounts.forms import SecureLoginForm


def index(request):
    """Vista de inicio/landing page"""
    return render(request, "index.html")


@require_http_methods(["GET", "POST"])
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def login_view(request):
    """
    Vista de login - Orquestador ligero
    
    Delega toda la lógica a AuthService
    Solo se encarga de:
    - Recibir request
    - Validar formulario
    - Llamar al servicio
    - Renderizar respuesta
    """
    if request.method == "POST":
        form = SecureLoginForm(request.POST)
        
        if form.is_valid():
            # Extraer datos del formulario
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            captcha_response = request.POST.get("h-captcha-response", "")
            
            # Login unificado con perfil seleccionado: estudiante, apoderado o personal
            perfil = request.POST.get('perfil') or request.POST.get('rol') or 'estudiante'
            result = AuthService.perform_login(
                request=request,
                username=username,
                password=password,
                captcha_response=captcha_response,
                remember_me=remember_me,
                login_type=perfil,
            )
            
            # Manejar resultado
            if result['success']:
                messages.success(request, f"¡Bienvenido/a {result['user'].get_full_name()}!")
                scope = AuthService.resolve_login_scope(result['user'])
                if scope:
                    request.session['last_rol'] = scope
                return redirect('dashboard')
            else:
                # Mostrar mensaje de error estructurado
                if result.get('error') and isinstance(result['error'], dict):
                    messages.error(request, result['error'].get('user_message', 'Error de autenticación.'))
                else:
                    messages.error(request, 'Error de autenticación.')
        else:
            # Formulario inválido
            client_ip = AuthService.get_client_ip(request)
            import logging
            security_logger = logging.getLogger('security')
            security_logger.warning(
                f"[SEGURIDAD] Intento de login con datos inválidos - IP: {client_ip}, "
                f"Errores: {form.errors.as_json()}"
            )
            messages.error(request, "Los datos ingresados no son válidos. Por favor, revisa e intenta nuevamente.")
    else:
        # GET request - mostrar formulario vacío
        form = SecureLoginForm()
    
    # Detectar tipo de usuario (staff o estudiante/apoderado)
    tipo_usuario = request.GET.get('tipo', 'estudiante')
    rol = request.GET.get('rol', None)
    
    # Seleccionar template según tipo de usuario
    template_name = "login_staff.html" if tipo_usuario == 'staff' else "login.html"
    
    # Renderizar template
    return render(request, template_name, {
        "form": form,
        "year": datetime.now().year,
        "hcaptcha_enabled": settings.HCAPTCHA_ENABLED,
        "hcaptcha_sitekey": settings.HCAPTCHA_SITEKEY,
        "rol": rol,
    })


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Vista de logout - Orquestador ligero
    
    Delega logout al servicio y renderiza respuesta
    """
    # Capturar estado ANTES de logout — auth_logout() borra la sesión y resetea request.user
    is_staff_user = (
        request.user.is_authenticated
        and getattr(request.user, 'is_staff', False)
    )
    last_rol = request.session.get('last_rol')

    username, was_authenticated = AuthService.logout_user(request)

    if was_authenticated:
        messages.success(request, "Has cerrado sesión exitosamente.")

    return redirect('accounts:login')


@require_http_methods(["GET", "POST"])
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def login_staff_view(request):
    """
    Vista de login para personal (profesores/administradores)
    
    Renderiza el template de staff con diseño de pantalla dividida
    """
    if request.method == "POST":
        form = SecureLoginForm(request.POST)
        
        if form.is_valid():
            # Extraer datos del formulario
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            captcha_response = request.POST.get("h-captcha-response", "")
            
            # Delegar a servicio (login tipo 'staff' para profesores/administradores)
            result = AuthService.perform_login(
                request=request,
                username=username,
                password=password,
                captcha_response=captcha_response,
                remember_me=remember_me,
                login_type='staff'
            )
            
            # Manejar resultado
            if result['success']:
                messages.success(request, f"¡Bienvenido/a {result['user'].get_full_name()}!")
                request.session['last_rol'] = 'staff'
                return redirect('dashboard')
            else:
                # Mostrar mensaje de error estructurado
                if result.get('error') and isinstance(result['error'], dict):
                    messages.error(request, result['error'].get('user_message', 'Error de autenticación.'))
                else:
                    messages.error(request, 'Error de autenticación.')
        else:
            # Formulario inválido
            client_ip = AuthService.get_client_ip(request)
            import logging
            security_logger = logging.getLogger('security')
            security_logger.warning(
                f"[SEGURIDAD] Intento de login con datos inválidos - IP: {client_ip}, "
                f"Errores: {form.errors.as_json()}"
            )
            messages.error(request, "Los datos ingresados no son válidos. Por favor, revisa e intenta nuevamente.")
    else:
        # GET request - mostrar formulario vacío
        form = SecureLoginForm()
    
    # Renderizar template de staff
    return render(request, "login_staff.html", {
        "form": form,
        "year": datetime.now().year,
        "hcaptcha_enabled": settings.HCAPTCHA_ENABLED,
        "hcaptcha_sitekey": settings.HCAPTCHA_SITEKEY,
    })

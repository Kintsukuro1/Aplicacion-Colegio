"""
Vista para que el administrador general seleccione o administre colegios
"""
import logging
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from backend.apps.core.services.escuela_management_service import EscuelaManagementService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.dashboard_helpers import build_dashboard_context

logger = logging.getLogger(__name__)

User = get_user_model()


@login_required(login_url='accounts:login')
def seleccionar_escuela(request):
    """
    Vista para que el administrador GENERAL seleccione o administre colegios
    Solo accesible por usuarios con rol 'Administrador general'
    """
    # Verificar que sea administrador GENERAL
    if not PolicyService.has_capability(request.user, 'SYSTEM_ADMIN'):
        messages.error(request, 'Acceso denegado. Solo administradores generales pueden acceder.')
        return redirect('dashboard')
    
    # MANEJAR POST: Crear colegio
    if request.method == 'POST' and 'crear_escuela' in request.POST:
        try:
            colegio = EscuelaManagementService.crear_colegio(request.user, request.POST)
            messages.success(request, f'✓ Colegio "{colegio.nombre}" creado exitosamente.')
            return redirect('seleccionar_escuela')
        except Exception:
            logger.exception('Error al crear el colegio')
            messages.error(request, 'Ocurrió un error al crear el colegio. Contacte al administrador.')
    
    # MANEJAR POST: Crear administrador escolar
    elif request.method == 'POST' and 'crear_admin_escolar' in request.POST:
        try:
            usuario = EscuelaManagementService.crear_admin_escolar(request.user, request.POST)
            colegio = usuario.rbd_colegio
            messages.success(request, f'✓ Administrador "{usuario.get_full_name()}" creado exitosamente para {colegio.nombre}')
            return redirect('seleccionar_escuela')
        except Exception:
            logger.exception('Error al crear administrador escolar')
            messages.error(request, 'Ocurrió un error al crear el administrador. Contacte al administrador del sistema.')
    
    # MANEJAR POST: Eliminar colegio
    elif request.method == 'POST' and 'eliminar_escuela' in request.POST:
        try:
            nombre_colegio = EscuelaManagementService.eliminar_colegio(request.user, request.POST.get('rbd'))
            messages.success(request, f'✓ Colegio "{nombre_colegio}" eliminado exitosamente.')
            return redirect('seleccionar_escuela')
        except Exception:
            logger.exception('Error al eliminar el colegio')
            messages.error(request, 'Ocurrió un error al eliminar el colegio. Contacte al administrador.')
    
    # MANEJAR POST: Cambiar plan
    elif request.method == 'POST' and 'cambiar_plan' in request.POST:
        try:
            colegio, plan = EscuelaManagementService.cambiar_plan_colegio(
                request.user,
                request.POST.get('rbd_plan'),
                request.POST.get('plan_codigo')
            )
            messages.success(request, f'✓ Plan cambiado a "{plan.nombre}" para {colegio.nombre}')
            return redirect('seleccionar_escuela')
        except Exception:
            logger.exception('Error al cambiar plan')
            messages.error(request, 'Ocurrió un error al cambiar el plan. Contacte al administrador.')
    
    mensaje = None
    tipo_mensaje = None

    try:
        data = EscuelaManagementService.obtener_datos_seleccionar_escuela(request.user)
    except Exception:
        logger.exception('Error al cargar datos de selección de escuelas')
        data = {
            'escuelas': [],
            'planes': [],
            'regiones': [],
            'comunas': [],
            'comunas_data': [],
            'tipos_establecimiento': [],
            'dependencias': [],
        }
        mensaje = "Ocurrió un error al cargar los colegios. Contacte al administrador."
        tipo_mensaje = 'error'

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='gestionar_escuelas',
        content_template='admin/seleccionar_escuela.html',
    )
    if redirect_response:
        return redirect_response

    context.update({
        **data,
        'mensaje': mensaje,
        'tipo_mensaje': tipo_mensaje,
    })

    return render(request, 'dashboard.html', context)


@login_required(login_url='accounts:login')
def entrar_escuela(request, rbd):
    """
    Vista para que el administrador general entre a una escuela específica
    """
    if not PolicyService.has_capability(request.user, 'SYSTEM_ADMIN'):
        messages.error(request, 'Acceso denegado.')
        return redirect('dashboard')

    try:
        colegio = EscuelaManagementService.entrar_escuela(request.user, rbd)

        request.session['admin_rbd_activo'] = int(colegio.rbd)
        request.session['admin_colegio_nombre'] = colegio.nombre
        request.session.modified = True
        request.session.save()

        messages.success(request, f'Has ingresado a {colegio.nombre}')

        next_destino = (request.GET.get('next') or '').strip()
        if next_destino == 'importar_datos':
            return redirect('importar_datos')

        return redirect(f"{reverse('dashboard')}?school_ctx={colegio.rbd}")

    except Exception:
        messages.error(request, 'Colegio no encontrado')
        return redirect('seleccionar_escuela')


@login_required(login_url='accounts:login')
def salir_escuela(request):
    """Quita el colegio activo de la sesión del administrador general."""
    if not PolicyService.has_capability(request.user, 'SYSTEM_ADMIN'):
        messages.error(request, 'Acceso denegado.')
        return redirect('dashboard')

    request.session.pop('admin_rbd_activo', None)
    request.session.pop('admin_colegio_nombre', None)
    request.session.modified = True
    request.session.save()
    messages.info(request, 'Has salido del contexto escolar. Estás en la consola global.')
    return redirect('dashboard')

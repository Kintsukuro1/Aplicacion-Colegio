"""
Vistas para el rol de Administrador General
Maneja operaciones CRUD para entidades globales del sistema
"""
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from backend.apps.core.services.admin_general_escuelas_query_service import AdminGeneralEscuelasQueryService
from backend.apps.core.services.colegio_service import ColegioService
from backend.apps.core.services.dashboard_auth_service import DashboardAuthService
from backend.common.services.policy_service import PolicyService
from backend.apps.core.views import load_dashboard_context

logger = logging.getLogger(__name__)


def _is_system_admin(user):
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN') is True


@login_required
def gestionar_escuelas(request):
    """
    Vista principal para gestión de escuelas
    Lista todas las escuelas con opciones de CRUD
    """
    # Verificar permisos usando el sistema de dashboard
    user_context = DashboardAuthService.get_user_context(request.user, request.session)
    if not user_context or not _is_system_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta página")
        return redirect('dashboard')

    # Obtener filtros
    region_id = request.GET.get('region')
    tipo_id = request.GET.get('tipo_establecimiento')
    dependencia_id = request.GET.get('dependencia')
    search = request.GET.get('search')

    # Base queryset
    escuelas = AdminGeneralEscuelasQueryService.list_escuelas(
        region_id=region_id,
        tipo_id=tipo_id,
        dependencia_id=dependencia_id,
        search=search,
    )

    # Paginación
    paginator = Paginator(escuelas, 20)  # 20 escuelas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Datos para filtros
    regiones, tipos_establecimiento, dependencias = AdminGeneralEscuelasQueryService.list_filter_data()

    # Usar el contexto del dashboard para mantener consistencia
    base_context = load_dashboard_context(request)

    context = {
        **base_context,
        'pagina_actual': 'escuelas',
        'content_template': 'admin/escuelas.html',
        'escuelas': page_obj,
        'regiones': regiones,
        'tipos_establecimiento': tipos_establecimiento,
        'dependencias': dependencias,
        'filtros_activos': {
            'region': region_id,
            'tipo_establecimiento': tipo_id,
            'dependencia': dependencia_id,
            'search': search,
        }
    }

    return render(request, 'dashboard.html', context)


@login_required
def agregar_escuela(request):
    """
    Vista para agregar una nueva escuela
    """
    # Verificar permisos usando el sistema de dashboard
    user_context = DashboardAuthService.get_user_context(request.user, request.session)
    if not user_context or not _is_system_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta página")
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            escuela = ColegioService.create(
                user=request.user,
                data={
                    'rbd': request.POST['rbd'],
                    'rut_establecimiento': request.POST['rut_establecimiento'],
                    'nombre': request.POST['nombre'],
                    'direccion': request.POST.get('direccion'),
                    'telefono': request.POST.get('telefono'),
                    'email': request.POST.get('correo'),
                    'web': request.POST.get('web'),
                    'capacidad_maxima': request.POST.get('capacidad_maxima') or None,
                    'fecha_fundacion': request.POST.get('fecha_fundacion') or None,
                    'comuna_id': request.POST['comuna'],
                    'tipo_establecimiento': request.POST['tipo_establecimiento'],
                    'dependencia': request.POST['dependencia'],
                },
            )

            messages.success(request, f"Escuela '{escuela.nombre}' agregada exitosamente")
            return redirect('/dashboard/?pagina=escuelas')

        except Exception:
            logger.exception("Error al agregar escuela")
            messages.error(request, "Ocurrió un error al agregar la escuela. Contacte al administrador.")

    # Datos para el formulario
    regiones, tipos_establecimiento, dependencias = AdminGeneralEscuelasQueryService.list_filter_data(include_comunas=True)

    # Usar el contexto del dashboard
    base_context = load_dashboard_context(request)

    context = {
        **base_context,
        'pagina_actual': 'escuelas',
        'content_template': 'admin/escuela_form.html',
        'regiones': regiones,
        'tipos_establecimiento': tipos_establecimiento,
        'dependencias': dependencias,
        'modo': 'agregar'
    }

    return render(request, 'dashboard.html', context)


@login_required
def editar_escuela(request, rbd):
    """
    Vista para editar una escuela existente
    """
    # Verificar permisos usando el sistema de dashboard
    user_context = DashboardAuthService.get_user_context(request.user, request.session)
    if not user_context or not _is_system_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta página")
        return redirect('dashboard')

    escuela = AdminGeneralEscuelasQueryService.get_escuela_detail_or_none(rbd)
    if escuela is None:
        messages.error(request, "No se encontró la escuela solicitada")
        return redirect('/dashboard/?pagina=escuelas')

    if request.method == 'POST':
        try:
            escuela = ColegioService.update(
                user=request.user,
                rbd=escuela.rbd,
                data={
                    'rut_establecimiento': request.POST['rut_establecimiento'],
                    'nombre': request.POST['nombre'],
                    'direccion': request.POST.get('direccion'),
                    'telefono': request.POST.get('telefono'),
                    'correo': request.POST.get('correo'),
                    'web': request.POST.get('web'),
                    'capacidad_maxima': request.POST.get('capacidad_maxima') or None,
                    'fecha_fundacion': request.POST.get('fecha_fundacion') or None,
                    'comuna_id': request.POST['comuna'],
                    'tipo_establecimiento_id': request.POST['tipo_establecimiento'],
                    'dependencia_id': request.POST['dependencia'],
                },
            )

            messages.success(request, f"Escuela '{escuela.nombre}' actualizada exitosamente")
            return redirect('/dashboard/?pagina=escuelas')

        except Exception:
            logger.exception("Error al actualizar escuela")
            messages.error(request, "Ocurrió un error al actualizar la escuela. Contacte al administrador.")

    # Datos para el formulario
    regiones, tipos_establecimiento, dependencias = AdminGeneralEscuelasQueryService.list_filter_data(include_comunas=True)

    # Usar el contexto del dashboard
    base_context = load_dashboard_context(request)

    context = {
        **base_context,
        'pagina_actual': 'escuelas',
        'content_template': 'admin/escuela_form.html',
        'escuela': escuela,
        'regiones': regiones,
        'tipos_establecimiento': tipos_establecimiento,
        'dependencias': dependencias,
        'modo': 'editar'
    }

    return render(request, 'dashboard.html', context)


@login_required
def detalle_escuela(request, rbd):
    """
    Vista para ver detalles de una escuela
    """
    # Verificar permisos usando el sistema de dashboard
    user_context = DashboardAuthService.get_user_context(request.user, request.session)
    if not user_context or not _is_system_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta página")
        return redirect('dashboard')

    escuela = AdminGeneralEscuelasQueryService.get_escuela_detail_or_none(rbd)
    if escuela is None:
        messages.error(request, "No se encontró la escuela solicitada")
        return redirect('/dashboard/?pagina=escuelas')

    # Estadísticas de la escuela
    total_usuarios, total_profesores, total_estudiantes = AdminGeneralEscuelasQueryService.get_user_counts_by_school(rbd)

    # Usar el contexto del dashboard
    base_context = load_dashboard_context(request)

    context = {
        **base_context,
        'pagina_actual': 'escuelas',
        'content_template': 'admin/escuela_detalle.html',
        'escuela': escuela,
        'total_usuarios': total_usuarios,
        'total_profesores': total_profesores,
        'total_estudiantes': total_estudiantes,
    }

    return render(request, 'dashboard.html', context)


@login_required
@require_POST
def eliminar_escuela(request, rbd):
    """
    Vista para eliminar una escuela (con confirmación)
    """
    # Verificar permisos
    user_context = DashboardAuthService.get_user_context(request.user, request.session)
    if not user_context or not _is_system_admin(request.user):
        messages.error(request, "No tienes permisos para realizar esta acción")
        return JsonResponse({'success': False, 'message': 'Permisos insuficientes'})

    try:
        escuela = AdminGeneralEscuelasQueryService.get_escuela_detail_or_none(rbd)
        if escuela is None:
            return JsonResponse({'success': False, 'message': 'Escuela no encontrada'})

        # Verificar si hay usuarios asociados
        usuarios_asociados = AdminGeneralEscuelasQueryService.has_users_for_school(rbd)
        if usuarios_asociados:
            return JsonResponse({
                'success': False,
                'message': 'No se puede eliminar la escuela porque tiene usuarios asociados'
            })

        nombre = ColegioService.delete(
            user=request.user,
            rbd=escuela.rbd,
        )

        messages.success(request, f"Escuela '{nombre}' eliminada exitosamente")
        return JsonResponse({'success': True})

    except Exception:
        logger.exception("Error al eliminar escuela")
        return JsonResponse({'success': False, 'message': 'Error interno del servidor'})


@login_required
def ajax_comunas_por_region(request, region_id):
    """
    Vista AJAX para obtener comunas de una región
    """
    comunas = AdminGeneralEscuelasQueryService.list_comunas_by_region(region_id)
    data = [{'id': comuna.id_comuna, 'nombre': comuna.nombre} for comuna in comunas]
    return JsonResponse({'comunas': data})
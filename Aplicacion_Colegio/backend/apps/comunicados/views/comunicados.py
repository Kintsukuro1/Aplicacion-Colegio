# comunicados/views/comunicados.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from ..models import Comunicado
from ..services import ComunicadosService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.common.services.policy_service import PolicyService
from datetime import datetime


def _build_dashboard_shell_context(request, pagina_actual: str = 'comunicados'):
    user_context = DashboardService.get_user_context(request.user, request.session)

    if user_context is not None:
        context_data = user_context['data']
        rol = context_data['rol']
        escuela_rbd = context_data['escuela_rbd']
        escuela_nombre = context_data['escuela_nombre']
        nombre_usuario = context_data['nombre_usuario']
        id_usuario = context_data['id_usuario']
    else:
        rol = 'estudiante'
        escuela_rbd = request.user.rbd_colegio
        escuela_nombre = request.user.colegio.nombre if hasattr(request.user, 'colegio') and request.user.colegio else 'Sistema'
        nombre_usuario = request.user.get_full_name()
        id_usuario = request.user.id

    navigation_access = DashboardService.get_navigation_access(
        rol,
        user=request.user,
        school_id=escuela_rbd,
    )

    return {
        'sidebar_template': DashboardService.get_sidebar_template(rol),
        'content_template': '',
        'rol': rol,
        'nombre_usuario': nombre_usuario,
        'id_usuario': id_usuario,
        'escuela_rbd': escuela_rbd,
        'escuela_nombre': escuela_nombre,
        'year': datetime.now().year,
        'pagina_actual': pagina_actual,
        **navigation_access,
    }


@login_required
def lista_comunicados(request):
    """Vista para listar comunicados según el rol del usuario."""
    try:
        PolicyService.require_capability(
            request.user,
            'ANNOUNCEMENT_VIEW',
            school_id=request.user.rbd_colegio,
        )
    except PermissionDenied:
        messages.error(request, 'No tienes permiso para ver comunicados.')
        return redirect('dashboard')

    # Obtener comunicados usando el service
    comunicados = ComunicadosService.get_comunicados_for_user(request.user)

    shell_context = _build_dashboard_shell_context(request)
    rol_normalizado = str(shell_context.get('rol', '')).lower()

    if rol_normalizado == 'estudiante':
        alumno_ctx = ComunicadosService.get_alumno_comunicados_context(
            request.user,
            request.GET,
        )
        context = {
            'tipos': Comunicado.TIPOS,
            **alumno_ctx,
            **shell_context,
        }
        return render(request, 'comunicados/lista_comunicados_alumno.html', context)

    tipo_filtro = request.GET.get('tipo')
    comunicados = ComunicadosService.filter_comunicados_by_type(comunicados, tipo_filtro)
    ComunicadosService.mark_comunicados_as_read_for_user(request.user, comunicados)
    context = {
        'comunicados': comunicados,
        'tipo_filtro': tipo_filtro,
        'tipos': Comunicado.TIPOS,
        **shell_context,
    }
    return render(request, 'comunicados/lista_comunicados.html', context)


@login_required
def detalle_comunicado(request, comunicado_id):
    """Vista para ver el detalle de un comunicado."""
    try:
        PolicyService.require_capability(
            request.user,
            'ANNOUNCEMENT_VIEW',
            school_id=request.user.rbd_colegio,
        )
    except PermissionDenied:
        messages.error(request, 'No tienes permiso para ver este comunicado.')
        return redirect('dashboard')

    comunicado = ComunicadosService.get_comunicado_or_none(comunicado_id)
    if comunicado is None:
        messages.error(request, 'Comunicado no encontrado.')
        return redirect('comunicados:lista')

    # Verificar permisos usando el service
    if not ComunicadosService.can_user_view_comunicado(request.user, comunicado):
        messages.error(request, 'No tienes permiso para ver este comunicado.')
        return redirect('comunicados:lista')

    # Marcar como leído usando el service
    ComunicadosService.mark_comunicado_as_read(request.user, comunicado)

    # Confirmar asistencia usando el service
    if request.method == 'POST' and request.POST.get('confirmar_asistencia'):
        try:
            ComunicadosService.confirm_attendance_to_comunicado(request.user, comunicado)
            messages.success(request, '✓ Asistencia confirmada.')
            return redirect('comunicados:detalle', comunicado_id=comunicado_id)
        except Exception as e:
            messages.error(request, f'Error al confirmar asistencia: {str(e)}')

    # Obtener confirmación del usuario usando el service
    confirmacion = ComunicadosService.get_user_confirmacion_for_comunicado(request.user, comunicado)

    shell_context = _build_dashboard_shell_context(request)
    rol_normalizado = str(shell_context.get('rol', '')).lower()

    if rol_normalizado == 'estudiante':
        alumno_ctx = ComunicadosService.get_alumno_comunicados_context(
            request.user,
            request.GET,
        )
        context = {
            'comunicado': comunicado,
            'confirmacion': confirmacion,
            **alumno_ctx,
            **shell_context,
        }
        return render(request, 'comunicados/detalle_comunicado_alumno.html', context)

    context = {
        'comunicado': comunicado,
        'confirmacion': confirmacion,
        **shell_context,
    }
    return render(request, 'comunicados/detalle_comunicado.html', context)


@login_required
def crear_comunicado(request):
    """Vista para crear un nuevo comunicado (solo admin escolar)."""
    if not (
        PolicyService.has_capability(
            request.user,
            'ANNOUNCEMENT_CREATE',
            school_id=request.user.rbd_colegio,
        )
        and PolicyService.has_capability(
            request.user,
            'SYSTEM_CONFIGURE',
            school_id=request.user.rbd_colegio,
        )
    ):
        messages.error(request, 'No tienes permiso para crear comunicados.')
        return redirect('comunicados:lista')

    if request.method == 'POST':
        # Usar el service para crear el comunicado
        result = ComunicadosService.create_comunicado(request.user, request.POST, request.FILES)

        if 'error' in result:
            messages.error(request, result['error'])
            # Re-renderizar el formulario con errores
            cursos = ComunicadosService.get_active_courses_for_user(request.user)
            context = {
                'tipos': Comunicado.TIPOS,
                'destinatarios': Comunicado.DESTINATARIOS,
                'cursos': cursos,
            }
            return render(request, 'comunicados/crear_comunicado.html', context)

        # Éxito
        messages.success(request, f'✓ Comunicado "{result["comunicado"].titulo}" publicado exitosamente.')
        return redirect('detalle_comunicado', comunicado_id=result['comunicado'].id_comunicado)

    # GET - Mostrar formulario
    cursos = ComunicadosService.get_active_courses_for_user(request.user)

    context = {
        'tipos': Comunicado.TIPOS,
        'destinatarios': Comunicado.DESTINATARIOS,
        'cursos': cursos,
    }

    return render(request, 'comunicados/crear_comunicado.html', context)


@login_required
def estadisticas_comunicado(request, comunicado_id):
    """Vista para ver estadísticas de un comunicado (solo admin)."""
    if not PolicyService.has_capability(
        request.user,
        'REPORT_VIEW_BASIC',
        school_id=request.user.rbd_colegio,
    ):
        messages.error(request, 'No tienes permiso para ver estadísticas de comunicados.')
        return redirect('comunicados:lista')

    # Usar el service para obtener estadísticas
    result = ComunicadosService.get_comunicado_statistics(request.user, comunicado_id)

    if 'error' in result:
        messages.error(request, result['error'])
        return redirect('comunicados:lista')

    context = {
        'comunicado': result['comunicado'],
        'confirmaciones': result['confirmaciones'],
        'stats': result['stats'],
    }

    return render(request, 'comunicados/estadisticas_comunicado.html', context)

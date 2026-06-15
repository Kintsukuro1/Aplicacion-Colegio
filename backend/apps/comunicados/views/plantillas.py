# comunicados/views/plantillas.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..services import ComunicadosService
from backend.common.services.policy_service import PolicyService


@login_required
def lista_plantillas(request):
    """
    Lista todas las plantillas disponibles para el colegio.
    """
    school_id = getattr(request.user, 'rbd_colegio', None)
    can_manage = (
        PolicyService.has_capability(request.user, 'ANNOUNCEMENT_CREATE', school_id=school_id)
        or PolicyService.has_capability(request.user, 'ANNOUNCEMENT_EDIT', school_id=school_id)
    )
    if not can_manage:
        messages.error(request, 'No tienes permiso para gestionar plantillas.')
        return redirect('comunicados:lista')

    data = ComunicadosService.get_plantillas_for_colegio(request.user)
    return render(request, 'comunicados/lista_plantillas.html', data)


@login_required
def crear_plantilla(request):
    """
    Crea una nueva plantilla de comunicado.
    """
    school_id = getattr(request.user, 'rbd_colegio', None)
    can_create = (
        PolicyService.has_capability(request.user, 'ANNOUNCEMENT_CREATE', school_id=school_id)
        and PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE', school_id=school_id)
    )
    if not can_create:
        messages.error(request, 'No tienes permiso para crear plantillas.')
        return redirect('comunicados:plantillas')

    if request.method == 'POST':
        try:
            plantilla = ComunicadosService.crear_plantilla(request.user, request.POST)
            messages.success(request, f'Plantilla "{plantilla.nombre}" creada exitosamente.')
            return redirect('comunicados:plantillas')
        except Exception as e:
            messages.error(request, f'Error al crear plantilla: {str(e)}')

    context = ComunicadosService.get_plantilla_creation_form_context()
    return render(request, 'comunicados/crear_plantilla.html', context)


@login_required
def editar_plantilla(request, plantilla_id):
    """
    Edita una plantilla existente.
    """
    school_id = getattr(request.user, 'rbd_colegio', None)
    can_edit = (
        PolicyService.has_capability(request.user, 'ANNOUNCEMENT_EDIT', school_id=school_id)
        and PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE', school_id=school_id)
    )
    if not can_edit:
        messages.error(request, 'No tienes permiso para editar plantillas.')
        return redirect('comunicados:plantillas')

    try:
        if request.method == 'POST':
            plantilla = ComunicadosService.actualizar_plantilla(request.user, plantilla_id, request.POST)
            messages.success(request, f'Plantilla "{plantilla.nombre}" actualizada.')
            return redirect('comunicados:plantillas')

        plantilla = ComunicadosService.get_plantilla_for_user(request.user, plantilla_id)
    except PermissionError as e:
        messages.error(request, str(e))
        return redirect('comunicados:plantillas')
    except Exception as e:
        messages.error(request, f'Error al actualizar plantilla: {str(e)}')
        return redirect('comunicados:plantillas')

    context = ComunicadosService.get_plantilla_edit_form_context(plantilla)
    return render(request, 'comunicados/editar_plantilla.html', context)


@login_required
@require_http_methods(["POST"])
def eliminar_plantilla(request, plantilla_id):
    """
    Desactiva una plantilla (soft delete).
    """
    school_id = getattr(request.user, 'rbd_colegio', None)
    can_delete = (
        PolicyService.has_capability(request.user, 'ANNOUNCEMENT_DELETE', school_id=school_id)
        and PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE', school_id=school_id)
    )
    if not can_delete:
        return JsonResponse({'success': False, 'error': 'No tienes permiso'}, status=403)

    try:
        ComunicadosService.eliminar_plantilla(request.user, plantilla_id)
        return JsonResponse({'success': True})
    except PermissionError:
        return JsonResponse(
            {'success': False, 'error': 'No tienes permiso para eliminar esta plantilla'},
            status=403,
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def usar_plantilla(request, plantilla_id):
    """
    Crea un nuevo comunicado basado en una plantilla.
    """
    try:
        plantilla = ComunicadosService.get_active_plantilla_for_user(request.user, plantilla_id)
    except PermissionError as e:
        messages.error(request, str(e))
        return redirect('comunicados:plantillas')

    if request.method == 'POST':
        try:
            comunicado = ComunicadosService.create_comunicado_from_template(
                request.user,
                plantilla,
                request.POST,
            )
            messages.success(request, f'Comunicado creado desde plantilla "{plantilla.nombre}".')
            return redirect('comunicados:detalle', comunicado_id=comunicado.id_comunicado)
        except Exception as e:
            messages.error(request, f'Error al crear comunicado desde plantilla: {str(e)}')

    context = ComunicadosService.get_template_usage_context(request.user, plantilla)
    return render(request, 'comunicados/usar_plantilla.html', context)

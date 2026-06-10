# comunicados/views/confirmaciones.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..services import ComunicadosService
from backend.common.services.policy_service import PolicyService


@login_required
def confirmaciones_masivas(request, comunicado_id):
    """
    Vista para gestionar confirmaciones de lectura de forma masiva.
    """
    school_id = getattr(request.user, 'rbd_colegio', None)
    can_manage = (
        PolicyService.has_capability(request.user, 'ANNOUNCEMENT_VIEW', school_id=school_id)
        and (
            PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE', school_id=school_id)
            or PolicyService.has_capability(request.user, 'ANNOUNCEMENT_EDIT', school_id=school_id)
        )
    )
    if not can_manage:
        from django.contrib import messages

        messages.error(request, 'No tienes permiso para gestionar confirmaciones.')
        return redirect('comunicados:lista')

    comunicado = ComunicadosService.get_comunicado_or_none(comunicado_id)
    if comunicado is None:
        from django.contrib import messages

        messages.error(request, 'Comunicado no encontrado.')
        return redirect('comunicados:lista')

    if hasattr(request.user, 'colegio') and comunicado.colegio != request.user.colegio:
        from django.contrib import messages

        messages.error(request, 'No tienes permiso para ver este comunicado.')
        return redirect('comunicados:lista')

    filtro = request.GET.get('filtro', 'todos')
    data = ComunicadosService.get_massive_confirmations_context(
        request.user,
        comunicado,
        filtro=filtro,
        recalcular=bool(request.GET.get('recalcular')),
    )

    context = {
        'comunicado': comunicado,
        'estadisticas': data['estadisticas'],
        'confirmaciones': data['confirmaciones'],
        'confirmaciones_por_rol': data['confirmaciones_por_rol'],
        'filtro_actual': filtro,
        'total_confirmaciones': data['total_confirmaciones'],
    }
    return render(request, 'comunicados/confirmaciones_masivas.html', context)


@login_required
@require_http_methods(["POST"])
def enviar_recordatorio_masivo(request, comunicado_id):
    """
    Envía recordatorios a usuarios pendientes de lectura.
    """
    school_id = getattr(request.user, 'rbd_colegio', None)
    can_remind = (
        PolicyService.has_capability(request.user, 'ANNOUNCEMENT_EDIT', school_id=school_id)
        and PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE', school_id=school_id)
    )
    if not can_remind:
        return JsonResponse(
            {
                'success': False,
                'error': 'No tienes permiso para enviar recordatorios',
            },
            status=403,
        )

    comunicado = ComunicadosService.get_comunicado_or_none(comunicado_id)
    if comunicado is None:
        return JsonResponse(
            {
                'success': False,
                'error': 'Comunicado no encontrado',
            },
            status=404,
        )
    notificaciones_creadas = ComunicadosService.send_massive_reminders(request.user, comunicado)

    return JsonResponse(
        {
            'success': True,
            'mensaje': f'Se enviaron {notificaciones_creadas} recordatorios',
            'notificaciones_enviadas': notificaciones_creadas,
        }
    )

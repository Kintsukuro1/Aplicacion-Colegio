import logging
import os

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from backend.apps.core.services.estudiante_api_service import EstudianteApiService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


def _validate_uploaded_file(uploaded_file):
    if not uploaded_file:
        raise ValueError('Debes subir un archivo para entregar la tarea.')

    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)
    if uploaded_file.size and uploaded_file.size > max_size:
        raise ValueError('El archivo excede el tamano maximo permitido.')

    allowed_exts = getattr(settings, 'ALLOWED_UPLOAD_EXTENSIONS', None)
    if allowed_exts:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in allowed_exts:
            raise ValueError('Tipo de archivo no permitido.')

    allowed_mimes = getattr(settings, 'ALLOWED_MIME_TYPES', None)
    content_type = getattr(uploaded_file, 'content_type', None)
    if allowed_mimes and content_type and content_type not in allowed_mimes:
        raise ValueError('Tipo MIME no permitido.')


@jwt_or_session_auth_required
@require_POST
def entregar_tarea(request):
    """
    Subir una entrega de tarea para el estudiante activo.
    """
    try:
        can_view_class = PolicyService.has_capability(request.user, 'CLASS_VIEW')
        can_manage_class = (
            PolicyService.has_capability(request.user, 'CLASS_EDIT')
            or PolicyService.has_capability(request.user, 'CLASS_TAKE_ATTENDANCE')
        )
        if not (can_view_class and not can_manage_class):
            return JsonResponse({'success': False, 'error': 'No tienes permisos de estudiante'}, status=403)

        tarea_id = request.POST.get('tarea_id')
        comentario = request.POST.get('comentario', '')
        archivo = request.FILES.get('archivo')

        if not tarea_id or not archivo:
            return JsonResponse({'success': False, 'error': 'Faltan datos obligatorios'}, status=400)

        _validate_uploaded_file(archivo)

        tarea = EstudianteApiService.get_tarea_activa_or_none(tarea_id)
        if not tarea:
            return JsonResponse({'success': False, 'error': 'Tarea no encontrada'}, status=404)

        entrega_existente = EstudianteApiService.get_entrega_existente(tarea, request.user)
        if entrega_existente:
            EstudianteApiService.actualizar_entrega(
                entrega_existente,
                archivo=archivo,
                comentario=comentario,
                fecha_entrega=timezone.now(),
            )
        else:
            EstudianteApiService.crear_entrega(
                tarea=tarea,
                estudiante=request.user,
                archivo=archivo,
                comentario=comentario,
            )

        return JsonResponse({'success': True, 'mensaje': 'Tarea entregada exitosamente'})

    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:
        logger.error('Error al entregar tarea: %s', str(exc))
        return JsonResponse({'success': False, 'error': 'Ocurrio un error al procesar la entrega'}, status=500)

import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.apps.core.services.system_health_service import SystemHealthService

logger = logging.getLogger(__name__)


@require_GET
def healthcheck(request):
    """Endpoint de salud del sistema para monitoreo operativo."""
    rbd = request.GET.get('rbd')

    try:
        payload = SystemHealthService.get_system_health(rbd_colegio=rbd)
        payload['request_id'] = getattr(request, 'request_id', None)
        http_status = 200 if payload.get('is_healthy') else 503
        return JsonResponse(payload, status=http_status)
    except Exception as exc:
        logger.exception('Healthcheck error: %s', exc)
        return JsonResponse(
            {
                'is_healthy': False,
                'error_type': 'HEALTHCHECK_ERROR',
                'message': 'Internal error',
                'request_id': getattr(request, 'request_id', None),
            },
            status=503,
        )

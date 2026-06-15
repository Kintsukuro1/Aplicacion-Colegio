"""Middleware para registrar latencia y errores por endpoint."""

import time

from backend.apps.core.services.operational_metrics_service import OperationalMetricsService


class OperationalMetricsMiddleware:
    """Registra metricas operativas de requests API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if request.path.startswith('/api/'):
            OperationalMetricsService.record_request(
                endpoint=request.path,
                status_code=getattr(response, 'status_code', 500),
                duration_ms=elapsed_ms,
            )
        return response

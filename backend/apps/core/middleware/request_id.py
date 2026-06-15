"""Middleware para correlacion de requests via X-Request-ID."""

import uuid

from django.conf import settings

from backend.common.utils.request_context import clear_request_id, set_request_id


class RequestIdMiddleware:
    """Asegura request-id en cada request y lo propaga en la respuesta."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = (request.headers.get('X-Request-ID') or '').strip()
        request_id = incoming if incoming else uuid.uuid4().hex

        request.request_id = request_id
        set_request_id(request_id)

        try:
            response = self.get_response(request)
        finally:
            clear_request_id()

        response['X-Request-ID'] = request_id
        response['Access-Control-Expose-Headers'] = self._merge_exposed_headers(
            response.get('Access-Control-Expose-Headers', ''),
            'X-Request-ID',
        )
        return response

    @staticmethod
    def _merge_exposed_headers(current: str, extra: str) -> str:
        existing = [item.strip() for item in (current or '').split(',') if item.strip()]
        lowered = {item.lower() for item in existing}
        if extra.lower() not in lowered:
            existing.append(extra)
        return ', '.join(existing)

from django.conf import settings


class ApiDeprecationHeadersMiddleware:
    """Agrega headers de deprecacion por version de API de forma configurable."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        path = request.path or ""
        if not path.startswith("/api/v1/"):
            return response

        deprecation_map = getattr(settings, "API_DEPRECATION_MAP", {}) or {}
        v1_cfg = deprecation_map.get("1.0", {})
        enabled = bool(v1_cfg.get("enabled", False))

        if not enabled:
            return response

        response["Deprecation"] = "true"

        sunset = v1_cfg.get("sunset")
        if sunset:
            response["Sunset"] = str(sunset)

        doc_url = v1_cfg.get("doc_url")
        if doc_url:
            response["Link"] = f'<{doc_url}>; rel="deprecation"; type="text/html"'

        message = v1_cfg.get("message")
        if message:
            response["X-API-Deprecation-Message"] = str(message)

        return response

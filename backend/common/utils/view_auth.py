"""Decoradores de autenticacion para vistas Django legacy JSON."""

from __future__ import annotations

from functools import wraps

from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def jwt_or_session_auth_required(view_func):
    """Permite autenticar por sesion Django o por JWT Bearer.

    Se usa en vistas function-based que no pasan por DRF y, por tanto,
    no ejecutan autenticacion JWT automaticamente.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return view_func(request, *args, **kwargs)

        try:
            auth_result = JWTAuthentication().authenticate(request)
        except (InvalidToken, TokenError):
            auth_result = None

        if auth_result is None:
            return JsonResponse({"success": False, "error": "Autenticacion requerida"}, status=401)

        auth_user, _token = auth_result
        request.user = auth_user
        request._cached_user = auth_user
        return view_func(request, *args, **kwargs)

    return _wrapped

"""Tenant isolation middleware."""

from django.http import HttpResponseForbidden

from backend.common.tenancy import (
    reset_current_tenant_school_id,
    set_current_tenant_school_id,
)
from backend.common.services.policy_service import PolicyService


class TenantMiddleware:
    """
    Sets request-scoped tenant context and blocks cross-school parameter access.
    """

    SCHOOL_PARAM_KEYS = {"rbd", "rbd_colegio", "escuela_rbd", "colegio"}

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _is_global_scope_user(user) -> bool:
        if not user or not user.is_authenticated:
            return True
        if user.is_superuser:
            return True

        if PolicyService.has_capability(user, "SYSTEM_ADMIN"):
            return True
        return False

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _extract_requested_school_ids(self, request) -> set[int]:
        requested = set()

        resolver_match = getattr(request, "resolver_match", None)
        if resolver_match and getattr(resolver_match, "kwargs", None):
            for key in self.SCHOOL_PARAM_KEYS:
                if key in resolver_match.kwargs:
                    parsed = self._to_int(resolver_match.kwargs.get(key))
                    if parsed is not None:
                        requested.add(parsed)

        for key in self.SCHOOL_PARAM_KEYS:
            parsed_get = self._to_int(request.GET.get(key))
            if parsed_get is not None:
                requested.add(parsed_get)
            parsed_post = self._to_int(request.POST.get(key))
            if parsed_post is not None:
                requested.add(parsed_post)

        return requested

    def __call__(self, request):
        user = getattr(request, "user", None)
        school_id = getattr(user, "rbd_colegio", None) if getattr(user, "is_authenticated", False) else None
        tenant_from_subdomain = getattr(request, "tenant_school_id", None)
        if self._is_global_scope_user(user):
            tenant_school_id = tenant_from_subdomain
        else:
            tenant_school_id = school_id
        token = set_current_tenant_school_id(tenant_school_id)

        try:
            if school_id is not None and not self._is_global_scope_user(user):
                requested_school_ids = self._extract_requested_school_ids(request)
                if any(requested_id != school_id for requested_id in requested_school_ids):
                    return HttpResponseForbidden("Acceso cross-colegio bloqueado por TenantMiddleware")

            response = self.get_response(request)
            return response
        finally:
            reset_current_tenant_school_id(token)

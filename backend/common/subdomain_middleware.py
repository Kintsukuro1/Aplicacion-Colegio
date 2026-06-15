"""Middleware para resolver tenant por subdominio."""

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from backend.apps.institucion.models import Colegio


class SubdomainMiddleware:
    """
    Resuelve el subdominio del host y lo mapea a un colegio.

    Fase 2: Enforce que usuarios autenticados solo accedan su propio colegio por subdominio.
    
    Ejemplo: colegio1.redpanda.cl -> slug=colegio1
    Solo users con rbd_colegio=1 pueden acceder a colegio1.redpanda.cl
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _extract_host(request):
        host = request.get_host().split(":", 1)[0].strip().lower()
        return host

    def _is_root_domain(self, host):
        root_domain = str(getattr(settings, "TENANT_ROOT_DOMAIN", "")).strip().lower()
        if not root_domain:
            return True
        return host == root_domain

    def __call__(self, request):
        host = self._extract_host(request)

        request.subdomain = None
        request.is_subdomain = False
        request.tenant_school_id = None
        request.tenant_school = None

        # Soporte explícito para dev local: /api/v1/tenant/info/?slug=colegio-a
        slug_override = request.GET.get("slug")
        if slug_override:
            colegio = Colegio.objects.all_schools().filter(slug=slug_override).first()
            if colegio is not None:
                request.subdomain = slug_override
                request.is_subdomain = True
                request.tenant_school_id = colegio.rbd
                request.tenant_school = colegio
            return self.get_response(request)

        if host in {"localhost", "127.0.0.1"} or self._is_root_domain(host):
            return self.get_response(request)

        parts = host.split(".")
        if len(parts) > 2:
            subdomain = parts[0]
            colegio = Colegio.objects.all_schools().filter(slug=subdomain).first()
            if colegio is not None:
                request.subdomain = subdomain
                request.is_subdomain = True
                request.tenant_school_id = colegio.rbd
                request.tenant_school = colegio
                
                # Fase 2: Enforce multi-tenancy para usuarios autenticados
                if request.user and request.user.is_authenticated:
                    user_rbd = getattr(request.user, 'rbd_colegio', None)
                    if user_rbd and user_rbd != colegio.rbd:
                        # Usuario intenta acceder a un colegio que no es el suyo
                        if request.path.startswith('/api/'):
                            return JsonResponse(
                                {'detail': 'No tienes acceso a este colegio.'},
                                status=403
                            )
                        raise PermissionDenied('No tienes acceso a este colegio.')

        return self.get_response(request)

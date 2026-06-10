"""Helpers de cache multi-tenant para evitar contaminacion entre colegios."""

from django.core.cache import cache


class TenantCacheService:
    """Genera claves cache namespaced por tenant y permite invalidacion por prefijo."""

    @staticmethod
    def build_key(namespace: str, *, tenant_id=None, scope=None, user_id=None) -> str:
        tenant_part = f"tenant:{tenant_id}" if tenant_id is not None else 'tenant:global'
        scope_part = f"scope:{scope}" if scope else 'scope:default'
        user_part = f"user:{user_id}" if user_id is not None else 'user:any'
        return f"{namespace}:{tenant_part}:{scope_part}:{user_part}"

    @staticmethod
    def invalidate_namespace(namespace: str, *, tenant_id=None) -> int:
        """Intenta invalidar por patron cuando el backend lo soporta."""
        prefix = f"{namespace}:tenant:{tenant_id}" if tenant_id is not None else f"{namespace}:"

        delete_pattern = getattr(cache, 'delete_pattern', None)
        if callable(delete_pattern):
            return int(delete_pattern(f"{prefix}*"))

        return 0

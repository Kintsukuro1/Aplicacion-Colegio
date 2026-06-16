"""Context processors globales para templates Django."""


def asset_version(_request):
    """Versión única para cache-bust de CSS/JS estáticos."""
    from django.conf import settings

    return {
        'asset_version': getattr(settings, 'ASSET_VERSION', '1'),
    }

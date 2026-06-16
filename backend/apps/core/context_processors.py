"""Context processors globales para templates Django."""


def asset_version(_request):
    """Versión única para cache-bust de CSS/JS estáticos."""
    from django.conf import settings

    return {
        'asset_version': getattr(settings, 'ASSET_VERSION', '1'),
    }


def portal_branding(_request):
    """Nombres de plataforma (empresa) y colegio para textos del portal."""
    from django.conf import settings

    return {
        'portal_platform_name': getattr(settings, 'PORTAL_PLATFORM_NAME', 'Raccademy'),
        'portal_school_name': getattr(settings, 'PORTAL_SCHOOL_NAME', 'Colegio Santa María'),
    }

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


def admin_school_context(request):
    """Colegio activo del admin general (sesión) para templates y sync JS."""
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return {'admin_school_bootstrap': None}

    from backend.common.services.policy_service import PolicyService

    if not PolicyService.has_capability(user, 'SYSTEM_ADMIN'):
        return {'admin_school_bootstrap': None}

    session = getattr(request, 'session', None)
    rbd = session.get('admin_rbd_activo') if session else None
    if not rbd:
        return {
            'admin_school_bootstrap': {
                'activo': False,
                'rbd': None,
                'nombre': None,
            },
        }

    from backend.apps.institucion.models import Colegio

    colegio = Colegio.objects.filter(rbd=rbd).only('rbd', 'nombre').first()
    if not colegio:
        if session is not None:
            session.pop('admin_rbd_activo', None)
            session.pop('admin_colegio_nombre', None)
            session.modified = True
        return {
            'admin_school_bootstrap': {
                'activo': False,
                'rbd': None,
                'nombre': None,
            },
        }

    if session is not None and session.get('admin_colegio_nombre') != colegio.nombre:
        session['admin_colegio_nombre'] = colegio.nombre
        session.modified = True

    return {
        'admin_school_bootstrap': {
            'activo': True,
            'rbd': colegio.rbd,
            'nombre': colegio.nombre,
        },
    }

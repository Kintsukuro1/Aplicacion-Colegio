"""Normaliza enlaces de notificaciones según tipo y portal del usuario."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

_CONVERSACION_RE = re.compile(r'^/mensajeria/conversacion/(\d+)/?', re.IGNORECASE)
_MENSAJE_TIPOS = frozenset({'mensaje_nuevo', 'mensaje'})
_MENSAJE_DASHBOARD_PAGINAS = frozenset({'mensajes', 'mensajeria', 'mensajería'})
_MENSAJERIA_BANDEJA = '/mensajeria/bandeja/'


def _is_mensajeria_dashboard_link(link: str) -> bool:
    if 'pagina=mensaje' in link or 'pagina=mensajeria' in link:
        return True
    parsed = urlparse(link)
    if parsed.path not in ('/dashboard', '/dashboard/') and not link.startswith('/dashboard?'):
        return False
    pagina = (parse_qs(parsed.query).get('pagina') or [''])[0].strip().lower()
    return pagina in _MENSAJE_DASHBOARD_PAGINAS or pagina.startswith('mensaj')


def _resolve_mensajeria_from_dashboard(link: str) -> str:
    parsed = urlparse(link)
    qs = parse_qs(parsed.query)
    for key in ('conversacion_id', 'id_conversacion', 'id'):
        raw = (qs.get(key) or [''])[0]
        if str(raw).isdigit():
            return f'/mensajeria/conversacion/{raw}/'
    return _MENSAJERIA_BANDEJA


def normalize_notification_enlace(enlace: Optional[str], tipo: Optional[str] = None) -> str:
    """
    Corrige enlaces legacy (p. ej. dashboard?pagina=mensajes|mensajeria) hacia rutas reales.
    """
    link = (enlace or '').strip()
    tipo_norm = (tipo or '').strip().lower()
    is_mensaje = tipo_norm in _MENSAJE_TIPOS

    conv = _CONVERSACION_RE.match(link)
    if conv:
        return f'/mensajeria/conversacion/{conv.group(1)}/'

    if is_mensaje or _is_mensajeria_dashboard_link(link) or link.startswith('/mensajeria'):
        if not link or link == '#':
            return _MENSAJERIA_BANDEJA

        if _is_mensajeria_dashboard_link(link):
            return _resolve_mensajeria_from_dashboard(link)

        if link.rstrip('/') in ('/mensajeria', '/mensajeria/bandeja', '/mensajeria/mensajes'):
            return _MENSAJERIA_BANDEJA

        if link.startswith('/mensajeria') and 'conversacion' not in link:
            return _MENSAJERIA_BANDEJA

    return link or '#'

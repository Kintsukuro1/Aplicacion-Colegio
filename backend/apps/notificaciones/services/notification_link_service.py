"""Normaliza enlaces de notificaciones según tipo y portal del usuario."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

_CONVERSACION_RE = re.compile(r'^/mensajeria/conversacion/(\d+)/?', re.IGNORECASE)
_ESTUDIANTE_INICIO_RE = re.compile(r'^/estudiante/inicio/?$', re.IGNORECASE)
_APODERADO_INICIO_RE = re.compile(r'^/apoderado/inicio/?', re.IGNORECASE)
_TAREA_TIPOS = frozenset({'tarea_nueva', 'tarea_calificada', 'tarea_entregada'})
_MENSAJE_TIPOS = frozenset({'mensaje_nuevo', 'mensaje'})
_MENSAJE_DASHBOARD_PAGINAS = frozenset({'mensajes', 'mensajeria', 'mensajería'})
_MENSAJERIA_BANDEJA = '/mensajeria/bandeja/'
_CLASE_DASHBOARD_SKIP = frozenset({'pagina', 'id', 'clase_id'})
_TIPO_DEFAULT_LINKS = {
    'calificacion': '/dashboard/?pagina=inicio',
    'asistencia': '/dashboard/?pagina=asistencia',
    'evaluacion': '/dashboard/?pagina=inicio',
    'alerta': '/dashboard/?pagina=inicio',
    'sistema': '/dashboard/?pagina=inicio',
    'tarea_nueva': '/dashboard/?pagina=mis_tareas',
    'tarea_calificada': '/dashboard/?pagina=mis_tareas',
    'tarea_entregada': '/dashboard/?pagina=tareas_consolidado',
    'comunicado_nuevo': '/comunicados/',
    'anuncio_nuevo': '/comunicados/',
    'urgente_nuevo': '/comunicados/',
    'mensaje_nuevo': _MENSAJERIA_BANDEJA,
    'mensaje': _MENSAJERIA_BANDEJA,
    'citacion_nueva': '/dashboard/?pagina=calendario_pupilo',
}


def _canonicalize_link(link: str) -> str:
    """Unifica rutas absolutas, relativas sin / y dashboard?pagina=… legacy."""
    raw = (link or '').strip()
    if not raw or raw == '#':
        return raw

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        path = parsed.path or '/dashboard'
        return f'{path}?{parsed.query}' if parsed.query else path

    if re.match(r'^dashboard(?:/|\?|$)', raw, re.IGNORECASE):
        return '/' + raw.lstrip('/')

    return raw


def _is_dashboard_path(path: str) -> bool:
    return (path or '').rstrip('/') == '/dashboard'


def _is_clase_dashboard_link(link: str) -> bool:
    link = _canonicalize_link(link)
    parsed = urlparse(link)
    if not _is_dashboard_path(parsed.path) and not re.match(r'^/dashboard(?:/|\?)', link, re.IGNORECASE):
        return False
    pagina = (parse_qs(parsed.query).get('pagina') or [''])[0].strip().lower()
    return pagina == 'clase'


def _resolve_clase_from_dashboard(link: str) -> str:
    link = _canonicalize_link(link)
    parsed = urlparse(link)
    qs = parse_qs(parsed.query)
    clase_id = (qs.get('id') or qs.get('clase_id') or [''])[0]
    if not str(clase_id).isdigit():
        return '/dashboard/?pagina=mis_clases'

    rest: list[tuple[str, str]] = []
    for key, values in qs.items():
        if key in _CLASE_DASHBOARD_SKIP:
            continue
        for value in values:
            rest.append((key, value))

    path = f'/estudiante/clase/{clase_id}/'
    if not rest:
        return path
    return f'{path}?{urlencode(rest)}'


def _is_mensajeria_dashboard_link(link: str) -> bool:
    if 'pagina=mensaje' in link or 'pagina=mensajeria' in link:
        return True
    parsed = urlparse(link)
    if parsed.path not in ('/dashboard', '/dashboard/') and not link.startswith('/dashboard?'):
        return False
    pagina = (parse_qs(parsed.query).get('pagina') or [''])[0].strip().lower()
    return pagina in _MENSAJE_DASHBOARD_PAGINAS or pagina.startswith('mensaj')


def _resolve_estudiante_inicio(tipo: Optional[str]) -> str:
    if (tipo or '').strip().lower() in _TAREA_TIPOS:
        return '/dashboard/?pagina=mis_tareas'
    return '/dashboard/?pagina=inicio'


def _resolve_apoderado_inicio(link: str) -> str:
    parsed = urlparse(link)
    base = '/dashboard/?pagina=inicio'
    if not parsed.query:
        return base
    return f'{base}&{parsed.query}'


def _resolve_mensajeria_from_dashboard(link: str) -> str:
    parsed = urlparse(link)
    qs = parse_qs(parsed.query)
    for key in ('conversacion_id', 'id_conversacion', 'id'):
        raw = (qs.get(key) or [''])[0]
        if str(raw).isdigit():
            return f'/mensajeria/conversacion/{raw}/'
    return _MENSAJERIA_BANDEJA


def resolve_default_notification_enlace(
    tipo: Optional[str] = None,
    titulo: Optional[str] = None,
    mensaje: Optional[str] = None,
) -> str:
    """Destino cuando la notificación no trae enlace explícito."""
    tipo_norm = (tipo or '').strip().lower()
    combined = f'{(titulo or "").strip().lower()} {(mensaje or "").strip().lower()}'

    if 'suscripci' in combined or ('vence' in combined and 'rbd' in combined):
        return '/dashboard/?pagina=reportes_financieros'
    if 'colegio registrado' in combined or 'nuevo colegio' in combined:
        return '/seleccionar-escuela/'
    if 'acceso no autorizado' in combined or (
        'intento' in combined and ('sesión' in combined or 'inicio de sesión' in combined)
    ):
        return '/dashboard/?pagina=monitoreo_seguridad'

    if tipo_norm == 'alerta':
        return '/dashboard/?pagina=monitoreo_seguridad'
    if tipo_norm == 'sistema':
        return '/dashboard/?pagina=inicio'

    return _TIPO_DEFAULT_LINKS.get(tipo_norm, '/dashboard/?pagina=notificaciones')


def normalize_notification_enlace(
    enlace: Optional[str],
    tipo: Optional[str] = None,
    titulo: Optional[str] = None,
    mensaje: Optional[str] = None,
) -> str:
    """
    Corrige enlaces legacy (p. ej. dashboard?pagina=mensajes|mensajeria) hacia rutas reales.
    """
    link = _canonicalize_link((enlace or '').strip())
    tipo_norm = (tipo or '').strip().lower()
    is_mensaje = tipo_norm in _MENSAJE_TIPOS

    if not link or link == '#':
        return resolve_default_notification_enlace(tipo_norm, titulo, mensaje)

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

    if _is_clase_dashboard_link(link):
        return _resolve_clase_from_dashboard(link)

    if _ESTUDIANTE_INICIO_RE.match(link):
        return _resolve_estudiante_inicio(tipo_norm)

    if _APODERADO_INICIO_RE.match(link):
        return _resolve_apoderado_inicio(link)

    return link

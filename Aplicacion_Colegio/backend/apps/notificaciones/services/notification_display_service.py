"""Metadatos de presentación para notificaciones en campana y página completa."""

from __future__ import annotations

import re
from typing import Any

from django.utils import timezone

from backend.apps.notificaciones.services.notification_link_service import (
    normalize_notification_enlace,
)

_TAREA_TIPOS = frozenset({'tarea_nueva', 'tarea_calificada', 'tarea_entregada'})
_MENSAJE_TIPOS = frozenset({'mensaje_nuevo', 'mensaje'})

_TIPO_META: dict[str, dict[str, str]] = {
    'calificacion': {
        'icono': '⭐',
        'categoria': 'Calificaciones',
        'accion': 'Ver notas',
        'mod': 'grades',
    },
    'asistencia': {
        'icono': '📋',
        'categoria': 'Asistencia',
        'accion': 'Ver asistencia',
        'mod': 'attendance',
    },
    'evaluacion': {
        'icono': '📊',
        'categoria': 'Evaluaciones',
        'accion': 'Ver evaluaciones',
        'mod': 'exams',
    },
    'alerta': {
        'icono': '⚠️',
        'categoria': 'Alertas',
        'accion': 'Revisar resumen',
        'mod': 'alert',
    },
    'tarea_nueva': {
        'icono': '📝',
        'categoria': 'Tareas',
        'accion': 'Ir a la tarea',
        'mod': 'tasks',
    },
    'tarea_entregada': {
        'icono': '📤',
        'categoria': 'Tareas',
        'accion': 'Ver entregas',
        'mod': 'tasks',
    },
    'tarea_calificada': {
        'icono': '✅',
        'categoria': 'Tareas',
        'accion': 'Ver calificación',
        'mod': 'tasks',
    },
    'comunicado_nuevo': {
        'icono': '📢',
        'categoria': 'Comunicados',
        'accion': 'Leer comunicado',
        'mod': 'comms',
    },
    'anuncio_nuevo': {
        'icono': '📢',
        'categoria': 'Comunicados',
        'accion': 'Leer anuncio',
        'mod': 'comms',
    },
    'urgente_nuevo': {
        'icono': '🚨',
        'categoria': 'Urgente',
        'accion': 'Abrir ahora',
        'mod': 'urgent',
    },
    'mensaje_nuevo': {
        'icono': '💬',
        'categoria': 'Mensajes',
        'accion': 'Abrir chat',
        'mod': 'messages',
    },
    'mensaje': {
        'icono': '💬',
        'categoria': 'Mensajes',
        'accion': 'Abrir chat',
        'mod': 'messages',
    },
    'citacion_nueva': {
        'icono': '📅',
        'categoria': 'Citaciones',
        'accion': 'Ver citación',
        'mod': 'citation',
    },
    'sistema': {
        'icono': '🔔',
        'categoria': 'Sistema',
        'accion': 'Ver detalle',
        'mod': 'system',
    },
}

_DEFAULT_META = {
    'icono': '🔔',
    'categoria': 'General',
    'accion': 'Ver más',
    'mod': 'default',
}

_TAREA_TITULO_RE = re.compile(
    r'^Nueva tarea:\s*(.+?)(?:\s*[-–—]\s*(.+))?$',
    re.IGNORECASE,
)


def _humanize_elapsed(fecha_creacion) -> str:
    if not fecha_creacion:
        return ''
    now = timezone.now()
    if timezone.is_naive(fecha_creacion):
        fecha_creacion = timezone.make_aware(fecha_creacion, timezone.get_current_timezone())
    delta = now - fecha_creacion
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return 'ahora'
    if minutes < 60:
        return f'hace {minutes} min'
    hours = minutes // 60
    if hours < 24:
        return f'hace {hours} h'
    days = hours // 24
    if days < 7:
        return f'hace {days} d'
    return fecha_creacion.strftime('%d/%m/%Y')


def _extract_contexto(titulo: str, mensaje: str, tipo: str) -> str:
    titulo = (titulo or '').strip()
    mensaje = (mensaje or '').strip()

    if tipo in _TAREA_TIPOS:
        match = _TAREA_TITULO_RE.match(titulo)
        if match:
            asignatura = (match.group(2) or '').strip()
            if asignatura:
                return asignatura
            return (match.group(1) or '').strip()
        if titulo.lower() == 'tareas pendientes':
            return 'Varias asignaturas'

    if tipo in _MENSAJE_TIPOS and ' de ' in titulo.lower():
        parte = titulo.split(' de ', 1)[-1].strip()
        if parte:
            return parte

    if tipo in {'comunicado_nuevo', 'anuncio_nuevo', 'urgente_nuevo'}:
        return 'Comunicado institucional'

    if tipo == 'calificacion':
        return 'Nueva calificación publicada'

    if tipo == 'evaluacion':
        return 'Evaluación programada'

    if tipo == 'asistencia':
        return 'Registro de asistencia'

    if tipo == 'alerta':
        return 'Seguimiento académico'

    if len(mensaje) <= 72:
        return mensaje
    return mensaje[:69] + '…'


def format_notification_for_ui(notif) -> dict[str, Any]:
    """Serializa una notificación con metadatos útiles para la UI."""
    tipo = (getattr(notif, 'tipo', None) or '').strip().lower()
    meta = _TIPO_META.get(tipo, _DEFAULT_META)
    prioridad = (getattr(notif, 'prioridad', None) or 'normal').strip().lower()
    url = normalize_notification_enlace(
        getattr(notif, 'enlace', ''),
        tipo,
        titulo=getattr(notif, 'titulo', ''),
        mensaje=getattr(notif, 'mensaje', ''),
    )
    titulo = getattr(notif, 'titulo', '') or ''
    mensaje = getattr(notif, 'mensaje', '') or ''
    leido = bool(getattr(notif, 'leido', False))
    fecha = getattr(notif, 'fecha_creacion', None)

    es_urgente = prioridad in ('alta', 'urgente') or tipo == 'urgente_nuevo'
    requiere_atencion = (not leido) and (
        es_urgente
        or tipo in _TAREA_TIPOS
        or tipo in _MENSAJE_TIPOS
        or tipo in {'comunicado_nuevo', 'anuncio_nuevo', 'urgente_nuevo', 'alerta'}
    )

    return {
        'id': getattr(notif, 'pk', None) or getattr(notif, 'id', None),
        'tipo': tipo,
        'tipo_label': notif.get_tipo_display() if hasattr(notif, 'get_tipo_display') else tipo,
        'titulo': titulo,
        'mensaje': mensaje,
        'contexto': _extract_contexto(titulo, mensaje, tipo),
        'fecha_creacion': fecha,
        'fecha_humana': _humanize_elapsed(fecha),
        'fecha_exacta': fecha.strftime('%d/%m/%Y %H:%M') if fecha else '',
        'icono': meta['icono'],
        'categoria': meta['categoria'],
        'accion_label': meta['accion'],
        'mod': meta['mod'],
        'url': url,
        'enlace': url,
        'leido': leido,
        'prioridad': prioridad,
        'prioridad_label': (
            notif.get_prioridad_display()
            if hasattr(notif, 'get_prioridad_display')
            else prioridad
        ),
        'es_urgente': es_urgente,
        'requiere_atencion': requiere_atencion,
    }


def build_notifications_page_summary(
    todas: list[dict[str, Any]],
    *,
    total: int,
    no_leidas: int,
) -> dict[str, Any]:
    """Resumen inteligente para el encabezado de la página."""
    leidas = max(total - no_leidas, 0)
    urgentes = sum(1 for n in todas if n.get('es_urgente') and not n.get('leido'))
    por_categoria: dict[str, int] = {}
    for item in todas:
        if item.get('leido'):
            continue
        cat = item.get('categoria') or 'General'
        por_categoria[cat] = por_categoria.get(cat, 0) + 1

    destacadas = [n for n in todas if n.get('requiere_atencion')][:3]
    sugerencia_texto = 'Estás al día con tus avisos.'
    sugerencia_url = '/dashboard/?pagina=inicio'

    if no_leidas > 0:
        cat_top = max(por_categoria.items(), key=lambda x: x[1])[0] if por_categoria else None
        if cat_top == 'Tareas':
            sugerencia_texto = (
                f'Tienes {por_categoria.get("Tareas", no_leidas)} aviso(s) de tareas sin revisar.'
            )
            sugerencia_url = '/dashboard/?pagina=mis_tareas'
        elif cat_top == 'Mensajes':
            sugerencia_texto = 'Tienes mensajes nuevos en tu bandeja.'
            sugerencia_url = '/mensajeria/bandeja/'
        elif cat_top == 'Comunicados' or cat_top == 'Urgente':
            sugerencia_texto = 'Hay comunicados que aún no has revisado.'
            sugerencia_url = '/comunicados/'
        elif urgentes:
            sugerencia_texto = f'{urgentes} aviso(s) requieren atención prioritaria.'
            sugerencia_url = destacadas[0]['url'] if destacadas else sugerencia_url
        else:
            sugerencia_texto = f'Tienes {no_leidas} notificación(es) pendiente(s) de revisar.'
            if destacadas:
                sugerencia_url = destacadas[0]['url']

    return {
        'total': total,
        'no_leidas': no_leidas,
        'leidas': leidas,
        'urgentes': urgentes,
        'por_categoria': por_categoria,
        'sugerencia_texto': sugerencia_texto,
        'sugerencia_url': sugerencia_url,
        'destacadas': destacadas,
    }

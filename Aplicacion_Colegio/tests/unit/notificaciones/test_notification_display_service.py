from types import SimpleNamespace

from backend.apps.notificaciones.services.notification_display_service import (
    build_notifications_page_summary,
    format_notification_for_ui,
)


def _notif(**kwargs):
    defaults = {
        'pk': 1,
        'tipo': 'tarea_nueva',
        'titulo': 'Nueva tarea: Tarea 2 - Tecnología',
        'mensaje': 'Se publicó una tarea en Tecnología.',
        'enlace': '/estudiante/inicio',
        'prioridad': 'normal',
        'leido': False,
        'fecha_creacion': None,
    }
    defaults.update(kwargs)
    obj = SimpleNamespace(**defaults)
    obj.get_tipo_display = lambda: 'Nueva Tarea'
    obj.get_prioridad_display = lambda: 'Normal'
    return obj


class TestFormatNotificationForUi:
    def test_tarea_extrae_asignatura_y_enlace_corregido(self):
        data = format_notification_for_ui(_notif())
        assert data['contexto'] == 'Tecnología'
        assert data['icono'] == '📝'
        assert data['accion_label'] == 'Ir a la tarea'
        assert data['url'] == '/dashboard/?pagina=mis_tareas'
        assert data['requiere_atencion'] is True

    def test_tareas_pendientes_contexto(self):
        data = format_notification_for_ui(_notif(
            tipo='tarea_nueva',
            titulo='Tareas pendientes',
            mensaje='Tienes 2 tareas pendientes por entregar.',
            enlace='/dashboard/?pagina=mis_tareas',
        ))
        assert data['contexto'] == 'Varias asignaturas'


class TestBuildNotificationsPageSummary:
    def test_sugerencia_tareas(self):
        items = [
            format_notification_for_ui(_notif()),
            format_notification_for_ui(_notif(pk=2, leido=True, titulo='Leída')),
        ]
        resumen = build_notifications_page_summary(items, total=2, no_leidas=1)
        assert resumen['no_leidas'] == 1
        assert 'tareas' in resumen['sugerencia_texto'].lower()
        assert resumen['sugerencia_url'] == '/dashboard/?pagina=mis_tareas'

from backend.apps.notificaciones.services.notification_link_service import (
    normalize_notification_enlace,
)


class TestNormalizeNotificationEnlace:
    def test_mensaje_nuevo_conversacion_se_mantiene(self):
        link = '/mensajeria/conversacion/42/'
        assert normalize_notification_enlace(link, 'mensaje_nuevo') == link

    def test_dashboard_pagina_mensajes_redirige_a_bandeja(self):
        assert (
            normalize_notification_enlace('/dashboard/?pagina=mensajes', 'mensaje_nuevo')
            == '/mensajeria/bandeja/'
        )

    def test_dashboard_pagina_mensajeria_redirige_a_bandeja(self):
        assert (
            normalize_notification_enlace('/dashboard/?pagina=mensajeria', 'mensaje_nuevo')
            == '/mensajeria/bandeja/'
        )

    def test_dashboard_pagina_mensajeria_con_conversacion(self):
        assert (
            normalize_notification_enlace(
                '/dashboard/?pagina=mensajeria&conversacion_id=9',
                'mensaje_nuevo',
            )
            == '/mensajeria/conversacion/9/'
        )

    def test_mensajeria_raiz_redirige_a_bandeja(self):
        assert normalize_notification_enlace('/mensajeria/', 'mensaje_nuevo') == '/mensajeria/bandeja/'

    def test_otros_tipos_no_cambian(self):
        link = '/comunicados/'
        assert normalize_notification_enlace(link, 'comunicado_nuevo') == link

    def test_dashboard_pagina_clase_redirige_a_detalle(self):
        assert (
            normalize_notification_enlace(
                '/dashboard/?pagina=clase&id=5&tarea=30',
                'tarea_entregada',
            )
            == '/estudiante/clase/5/?tarea=30'
        )

    def test_dashboard_pagina_clase_con_clase_id(self):
        assert (
            normalize_notification_enlace(
                '/dashboard/?pagina=clase&clase_id=12&tab=entregas',
                'alerta',
            )
            == '/estudiante/clase/12/?tab=entregas'
        )

    def test_estudiante_clase_path_se_mantiene(self):
        link = '/estudiante/clase/5/?tarea=30'
        assert normalize_notification_enlace(link, 'tarea_nueva') == link

    def test_dashboard_pagina_clase_sin_barra_inicial(self):
        assert (
            normalize_notification_enlace(
                'dashboard/?pagina=clase&id=5&tarea=30',
                'tarea_entregada',
            )
            == '/estudiante/clase/5/?tarea=30'
        )

    def test_dashboard_pagina_clase_url_absoluta(self):
        assert (
            normalize_notification_enlace(
                'http://127.0.0.1:8000/dashboard/?pagina=clase&id=5&tarea=30',
                'tarea_entregada',
            )
            == '/estudiante/clase/5/?tarea=30'
        )

    def test_estudiante_inicio_tareas_redirige_a_mis_tareas(self):
        assert (
            normalize_notification_enlace('/estudiante/inicio', 'tarea_nueva')
            == '/dashboard/?pagina=mis_tareas'
        )

    def test_estudiante_inicio_alerta_redirige_a_inicio_dashboard(self):
        assert (
            normalize_notification_enlace('/estudiante/inicio', 'alerta')
            == '/dashboard/?pagina=inicio'
        )

    def test_apoderado_inicio_legacy_con_estudiante_id(self):
        assert (
            normalize_notification_enlace(
                '/apoderado/inicio?estudiante_id=12',
                'alerta',
            )
            == '/dashboard/?pagina=inicio&estudiante_id=12'
        )

    def test_sin_enlace_suscripcion_admin(self):
        assert (
            normalize_notification_enlace(
                '',
                'sistema',
                titulo='Suscripción próxima a vencer',
                mensaje='La suscripción del Liceo vence en 7 días.',
            )
            == '/dashboard/?pagina=reportes_financieros'
        )

    def test_sin_enlace_acceso_no_autorizado(self):
        assert (
            normalize_notification_enlace(
                None,
                'alerta',
                titulo='Intento de acceso no autorizado',
                mensaje='Se detectaron 3 intentos fallidos de inicio de sesión.',
            )
            == '/dashboard/?pagina=monitoreo_seguridad'
        )

    def test_sin_enlace_nuevo_colegio(self):
        assert (
            normalize_notification_enlace(
                '',
                'sistema',
                titulo='Nuevo colegio registrado',
                mensaje='Se ha registrado un nuevo colegio en la plataforma.',
            )
            == '/seleccionar-escuela/'
        )

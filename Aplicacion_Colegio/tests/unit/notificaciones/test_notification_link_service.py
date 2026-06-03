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

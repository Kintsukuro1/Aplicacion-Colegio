from unittest.mock import Mock, patch

from backend.apps.core.services.class_detail_service import ClassDetailService


def _request(method="GET", role="Profesor"):
    req = Mock()
    req.method = method
    req.GET = Mock()
    req.GET.get.return_value = "0"
    req.POST = Mock()
    req.POST.get.return_value = None
    req.FILES = Mock()
    req.FILES.get.return_value = None
    req.user = Mock()
    req.user.id = 10
    req.user.rbd_colegio = 123
    req.user.colegio = Mock()
    req.user.colegio.rbd = 123
    req.user.role = Mock()
    req.user.role.nombre = role
    return req


class TestClassDetailService:
    @patch("backend.apps.core.services.class_detail_service.render")
    def test_handle_request_denies_unknown_role(self, mock_render):
        req = _request(role="Apoderado")
        mock_render.return_value = "DENIED"

        result = ClassDetailService.handle_request(req, 5)

        assert result == "DENIED"
        mock_render.assert_called_once()

    @patch("backend.apps.core.services.class_detail_service.redirect")
    @patch("backend.apps.core.services.class_detail_service.messages")
    @patch("backend.apps.core.services.class_detail_service.Clase")
    @patch("backend.apps.core.services.class_detail_service.PerfilEstudiante")
    def test_handle_request_alumno_without_access_redirects_dashboard(self, mock_perfil, mock_clase, mock_messages, mock_redirect):
        req = _request(role="Alumno")
        perfil = Mock()
        perfil.ciclo_actual = "CICLO"
        mock_perfil.objects.get.return_value = perfil

        class _ClaseDoesNotExist(Exception):
            pass

        class _PerfilDoesNotExist(Exception):
            pass

        mock_clase.DoesNotExist = _ClaseDoesNotExist
        mock_perfil.DoesNotExist = _PerfilDoesNotExist
        mock_clase.objects.select_related.return_value.get.side_effect = _ClaseDoesNotExist("no access")
        mock_redirect.return_value = "REDIRECT"

        result = ClassDetailService.handle_request(req, 99)

        assert result == "REDIRECT"
        mock_messages.error.assert_called_once()

    @patch("backend.apps.core.services.class_detail_service.render")
    @patch("backend.apps.core.services.class_detail_service.User")
    @patch("backend.apps.core.services.class_detail_service.BloqueHorario")
    @patch("backend.apps.core.services.class_detail_service.Clase")
    def test_handle_request_profesor_success_renders_template(self, mock_clase, mock_bloques, mock_user, mock_render):
        req = _request(role="Profesor")

        clase = Mock()
        clase.id = 1
        clase.profesor = req.user
        clase.colegio = req.user.colegio
        clase.asignatura = Mock()
        clase.curso = Mock()
        clase.curso.ciclo_academico = "CICLO"
        mock_clase.objects.select_related.return_value.get.return_value = clase

        bloque = Mock()
        bloque.get_dia_semana_display.return_value = "Lunes"
        bloque.hora_inicio.strftime.return_value = "08:00"
        bloque.hora_fin.strftime.return_value = "08:45"
        bloque.bloque_numero = 1
        from unittest.mock import MagicMock

        bloques_qs = MagicMock()
        bloques_qs.order_by.return_value = bloques_qs
        bloques_qs.__iter__.return_value = iter([bloque])
        bloques_qs.count.return_value = 1
        mock_bloques.objects.filter.return_value = bloques_qs

        students_qs = Mock()
        students_qs.exclude.return_value = students_qs
        students_qs.count.return_value = 1
        students_qs.order_by.return_value = students_qs
        mock_user.objects.filter.return_value = students_qs

        with patch("backend.apps.academico.models.Evaluacion") as mock_eval, \
             patch("backend.apps.academico.models.MaterialClase") as mock_material, \
             patch("backend.apps.academico.models.Tarea") as mock_tarea, \
             patch("backend.apps.academico.models.EntregaTarea") as mock_entrega, \
             patch("backend.apps.mensajeria.models.Anuncio") as mock_anuncio:
            eval_qs = MagicMock()
            eval_qs.order_by.return_value.__getitem__.return_value = []
            mock_eval.objects.filter.return_value = eval_qs

            materiales_qs = Mock()
            materiales_qs.select_related.return_value.order_by.return_value = materiales_qs
            materiales_qs.count.return_value = 0
            mock_material.objects.filter.return_value = materiales_qs

            tarea = Mock()
            mock_tarea.objects.filter.return_value.order_by.return_value = [tarea]
            mock_entrega.objects.filter.return_value.count.return_value = 0
            from unittest.mock import MagicMock
            pendientes_qs = MagicMock()
            pendientes_slice = Mock()
            pendientes_slice.count.return_value = 0
            pendientes_qs.__getitem__.return_value = pendientes_slice
            mock_entrega.objects.filter.return_value.select_related.return_value.order_by.return_value = pendientes_qs

            mock_anuncio.objects.filter.return_value = []
            mock_render.return_value = "OK"

            result = ClassDetailService.handle_request(req, 1)

        assert result == "OK"
        assert mock_render.call_args.args[1] == "profesor/detalle_clase.html"

    @patch("backend.apps.core.services.class_detail_service.redirect")
    @patch("backend.apps.core.services.class_detail_service.messages")
    @patch("backend.apps.core.services.class_detail_service.MaterialClaseService")
    def test_handle_request_post_profesor_actions_redirect(self, mock_material_service, mock_messages, mock_redirect):
        req = _request(method="POST", role="Profesor")
        mock_redirect.return_value = "REDIRECTED"

        req.POST.get.side_effect = lambda key, default=None: {
            "accion": "subir_material",
            "titulo": "Guia 1",
            "descripcion": "d",
            "es_publico": "1",
            "tipo_archivo": "documento",
        }.get(key, default)
        req.FILES.get.return_value = Mock()
        result_subir = ClassDetailService.handle_request(req, 7)

        req.POST.get.side_effect = lambda key, default=None: {
            "accion": "eliminar_material",
            "material_id": "11",
        }.get(key, default)
        result_eliminar = ClassDetailService.handle_request(req, 7)

        mock_material = Mock()
        mock_material.es_publico = False
        mock_material_service.toggle_visibility.return_value = mock_material
        req.POST.get.side_effect = lambda key, default=None: {
            "accion": "cambiar_visibilidad",
            "material_id": "12",
        }.get(key, default)
        result_visibilidad = ClassDetailService.handle_request(req, 7)

        assert result_subir == "REDIRECTED"
        assert result_eliminar == "REDIRECTED"
        assert result_visibilidad == "REDIRECTED"
        assert mock_messages.success.call_count == 3

    @patch("backend.apps.core.services.class_detail_service.render")
    @patch("backend.apps.core.services.class_detail_service.PerfilEstudiante")
    @patch("backend.apps.core.services.class_detail_service.Clase")
    @patch("backend.apps.core.services.class_detail_service.BloqueHorario")
    @patch("backend.apps.core.services.class_detail_service.User")
    def test_handle_request_alumno_success_covers_progress_tasks_and_anuncios(
        self,
        mock_user,
        mock_bloques,
        mock_clase,
        mock_perfil,
        mock_render,
    ):
        req = _request(role="Alumno")

        perfil = Mock()
        perfil.ciclo_actual = "CICLO"
        mock_perfil.objects.get.return_value = perfil

        clase = Mock()
        clase.id = 1
        clase.profesor = Mock()
        clase.colegio = req.user.colegio
        clase.asignatura = Mock()
        clase.curso = Mock()
        clase.curso.ciclo_academico = "CICLO"
        mock_clase.objects.select_related.return_value.get.return_value = clase

        bloque1 = Mock()
        bloque1.get_dia_semana_display.return_value = "Lunes"
        bloque1.hora_inicio.strftime.return_value = "08:00"
        bloque1.hora_fin.strftime.side_effect = ["08:45", "08:45", "08:45"]
        bloque1.bloque_numero = 1

        bloque2 = Mock()
        bloque2.get_dia_semana_display.return_value = "Lunes"
        bloque2.hora_inicio.strftime.return_value = "09:00"
        bloque2.hora_fin.strftime.side_effect = ["09:45", "09:45", "09:45", "09:45"]
        bloque2.bloque_numero = 2

        from unittest.mock import MagicMock

        bloques_qs = MagicMock()
        bloques_qs.order_by.return_value = bloques_qs
        bloques_qs.__iter__.return_value = iter([bloque1, bloque2])
        bloques_qs.count.return_value = 2
        mock_bloques.objects.filter.return_value = bloques_qs

        students_qs = Mock()
        students_qs.order_by.return_value = students_qs
        students_qs.exclude.return_value = students_qs
        students_qs.count.return_value = 5
        mock_user.objects.filter.return_value = students_qs

        with patch("backend.apps.academico.models.Evaluacion") as mock_eval, \
             patch("backend.apps.academico.models.Calificacion") as mock_calif, \
             patch("backend.apps.academico.models.MaterialClase") as mock_material, \
             patch("backend.apps.academico.models.Tarea") as mock_tarea, \
             patch("backend.apps.academico.models.EntregaTarea") as mock_entrega, \
             patch("backend.apps.mensajeria.models.Anuncio") as mock_anuncio:
            eval_qs_prox = MagicMock()
            eval_qs_prox.order_by.return_value.__getitem__.return_value = []
            mock_eval.objects.filter.side_effect = [eval_qs_prox, Mock(count=Mock(return_value=4))]

            mock_calif.objects.filter.return_value.count.return_value = 2

            materiales_qs = Mock()
            materiales_qs.select_related.return_value.order_by.return_value = materiales_qs
            materiales_qs.count.return_value = 1
            mock_material.objects.filter.return_value = materiales_qs

            tarea = Mock()
            tarea.get_estado.return_value = "pendiente"
            tarea.get_icono_estado.return_value = "📝"
            tarea.get_texto_estado.return_value = "Pendiente"
            mock_tarea.objects.filter.return_value.order_by.return_value = [tarea]
            mock_entrega.objects.filter.return_value.first.return_value = Mock()

            anuncio_no_leido = Mock()
            anuncio_no_leido.esta_leido_por.return_value = False
            anuncio_no_leido.anclado = True
            anuncio_no_leido.fecha_creacion.timestamp.return_value = 10

            anuncio_leido = Mock()
            anuncio_leido.esta_leido_por.return_value = True
            anuncio_leido.anclado = False
            anuncio_leido.fecha_creacion.timestamp.return_value = 1
            mock_anuncio.objects.filter.return_value = [anuncio_leido, anuncio_no_leido]

            mock_render.return_value = "ALUMNO_OK"
            result = ClassDetailService.handle_request(req, 1)

        assert result == "ALUMNO_OK"
        assert mock_render.call_args.args[1] == "estudiante/detalle_clase.html"

    @patch("backend.apps.core.services.class_detail_service.render")
    @patch("backend.apps.core.services.class_detail_service.User")
    @patch("backend.apps.core.services.class_detail_service.BloqueHorario")
    @patch("backend.apps.core.services.class_detail_service.Clase")
    def test_handle_request_profesor_ver_como_alumno_usa_template_estudiante(self, mock_clase, mock_bloques, mock_user, mock_render):
        req = _request(role="Profesor")
        req.GET.get.return_value = "1"

        clase = Mock()
        clase.id = 2
        clase.profesor = req.user
        clase.colegio = req.user.colegio
        clase.asignatura = Mock()
        clase.curso = Mock()
        clase.curso.ciclo_academico = "CICLO"
        mock_clase.objects.select_related.return_value.get.return_value = clase

        from unittest.mock import MagicMock

        bloques_qs = MagicMock()
        bloques_qs.order_by.return_value = bloques_qs
        bloques_qs.__iter__.return_value = iter([])
        bloques_qs.count.return_value = 0
        mock_bloques.objects.filter.return_value = bloques_qs

        students_qs = Mock()
        students_qs.count.return_value = 2
        students_qs.order_by.return_value = students_qs
        students_qs.exclude.return_value = students_qs
        mock_user.objects.filter.return_value = students_qs

        with patch("backend.apps.academico.models.Evaluacion") as mock_eval, \
             patch("backend.apps.academico.models.MaterialClase") as mock_material, \
             patch("backend.apps.academico.models.Tarea") as mock_tarea, \
             patch("backend.apps.academico.models.EntregaTarea") as mock_entrega, \
             patch("backend.apps.mensajeria.models.Anuncio") as mock_anuncio:
            eval_qs = MagicMock()
            eval_qs.order_by.return_value.__getitem__.return_value = []
            mock_eval.objects.filter.return_value = eval_qs

            materiales_qs = Mock()
            materiales_qs.select_related.return_value.order_by.return_value = materiales_qs
            materiales_qs.count.return_value = 0
            mock_material.objects.filter.return_value = materiales_qs

            tarea = Mock()
            mock_tarea.objects.filter.return_value.order_by.return_value = [tarea]
            mock_entrega.objects.filter.return_value.first.return_value = None

            mock_anuncio.objects.filter.return_value = []

            mock_render.return_value = "PROF_ALUMNO"
            result = ClassDetailService.handle_request(req, 2)

        assert result == "PROF_ALUMNO"
        assert mock_render.call_args.args[1] == "estudiante/detalle_clase.html"

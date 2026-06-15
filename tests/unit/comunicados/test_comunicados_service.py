from unittest.mock import Mock, patch

import pytest

from backend.apps.comunicados.services.comunicados_service import ComunicadosService


class _Data(dict):
    def getlist(self, key):
        value = self.get(key, [])
        return value if isinstance(value, list) else [value]


class _Files(dict):
    def getlist(self, key):
        value = self.get(key, [])
        return value if isinstance(value, list) else [value]


def _user(role_name="Administrador escolar"):
    user = Mock()
    user.username = "admin"
    user.id = 1
    user.is_active = True
    user.colegio = Mock()
    user.colegio.rbd = 123
    user.colegio.nombre = "Colegio Test"
    user.role = Mock()
    user.role.nombre = role_name
    return user


def _comunicado(destinatario="todos", colegio=None, requiere=False):
    comunicado = Mock()
    comunicado.destinatario = destinatario
    comunicado.colegio = colegio or Mock()
    comunicado.requiere_confirmacion = requiere
    comunicado.cursos_destinatarios = Mock()
    return comunicado


class TestComunicadosService:
    def test_validate_requires_create_params(self):
        with pytest.raises(ValueError):
            ComunicadosService.validate("create_comunicado", {"user": _user(), "data": _Data()})

    def test_execute_unsupported_raises(self):
        with pytest.raises(ValueError):
            ComunicadosService.execute("x", {})

    def test_execute_dispatches_create(self):
        with patch.object(ComunicadosService, "_execute_create_comunicado", return_value={"success": True}):
            res = ComunicadosService.execute("create_comunicado", {"user": _user(), "data": _Data(), "files": _Files()})
        assert res["success"] is True

    def test_filter_comunicados_by_type(self):
        qs = Mock()
        qs.filter.return_value = "filtered"
        assert ComunicadosService.filter_comunicados_by_type(qs, "urgente") == "filtered"
        assert ComunicadosService.filter_comunicados_by_type(qs, "") == qs

    def test_can_user_view_comunicado_false_by_school(self):
        user = _user("Profesor")
        comunicado = _comunicado(colegio=Mock())
        assert ComunicadosService.can_user_view_comunicado(user, comunicado) is False

    @patch("backend.apps.comunicados.services.comunicados_service.PolicyService.has_capability", side_effect=lambda _u, c, school_id=None: c == "SYSTEM_CONFIGURE")
    def test_can_user_view_comunicado_admin_true(self, _):
        user = _user("Administrador escolar")
        comunicado = _comunicado(colegio=user.colegio)
        assert ComunicadosService.can_user_view_comunicado(user, comunicado) is True

    @patch("backend.apps.comunicados.services.comunicados_service.PolicyService.has_capability")
    @patch("backend.apps.accounts.models.PerfilEstudiante")
    def test_can_user_view_comunicado_student_course_specific(self, mock_perfil, mock_has_capability):
        user = _user("Alumno")
        perfil = Mock()
        perfil.curso_actual = Mock()
        mock_perfil.objects.get.return_value = perfil

        def _has_capability(_u, capability, school_id=None):
            return capability in {"CLASS_VIEW", "GRADE_VIEW"}

        mock_has_capability.side_effect = _has_capability

        comunicado = _comunicado(destinatario="curso_especifico", colegio=user.colegio)
        comunicado.cursos_destinatarios.filter.return_value.exists.return_value = True
        assert ComunicadosService.can_user_view_comunicado(user, comunicado) is True

    @patch("backend.apps.comunicados.models.ConfirmacionLectura")
    def test_mark_comunicado_as_read_calls_confirm(self, mock_confirmacion):
        user = _user("Profesor")
        comunicado = _comunicado(colegio=user.colegio, requiere=True)
        conf = Mock()
        mock_confirmacion.objects.get_or_create.return_value = (conf, True)

        ComunicadosService.mark_comunicado_as_read(user, comunicado)
        conf.marcar_como_leido.assert_called_once()

    def test_confirm_attendance_returns_false_without_requirement(self):
        user = _user("Profesor")
        comunicado = _comunicado(colegio=user.colegio, requiere=False)
        assert ComunicadosService.confirm_attendance_to_comunicado(user, comunicado) is False

    @patch("backend.apps.comunicados.models.ConfirmacionLectura")
    def test_confirm_attendance_ok(self, mock_confirmacion):
        user = _user("Profesor")
        comunicado = _comunicado(colegio=user.colegio, requiere=True)
        conf = Mock()
        mock_confirmacion.objects.get_or_create.return_value = (conf, True)
        assert ComunicadosService.confirm_attendance_to_comunicado(user, comunicado) is True
        conf.confirmar_asistencia.assert_called_once()

    @patch("backend.apps.comunicados.services.comunicados_service.CommonValidations.validate_admin_permissions", return_value=(False, "denegado"))
    def test_get_comunicado_statistics_permission_error(self, _):
        res = ComunicadosService.get_comunicado_statistics(_user(), _comunicado(colegio=_user().colegio))
        assert res["error"] == "denegado"

    @patch("backend.apps.comunicados.models.ConfirmacionLectura")
    @patch("backend.apps.comunicados.services.comunicados_service.CommonValidations.validate_admin_permissions", return_value=(True, ""))
    def test_get_comunicado_statistics_success(self, _, mock_confirmacion):
        user = _user()
        comunicado = _comunicado(colegio=user.colegio)
        qs = mock_confirmacion.objects.filter.return_value
        qs.count.return_value = 4
        qs.filter.side_effect = [Mock(count=Mock(return_value=3)), Mock(count=Mock(return_value=2)), Mock(count=Mock(return_value=1))]

        res = ComunicadosService.get_comunicado_statistics(user, comunicado)
        assert res["stats"]["total"] == 4
        assert res["stats"]["leidos"] == 3
        assert res["stats"]["confirmados"] == 2
        assert res["stats"]["pendientes"] == 1

    @patch("backend.apps.comunicados.services.comunicados_service.CommonValidations.validate_admin_permissions", return_value=(False, "sin permiso"))
    def test_execute_create_comunicado_rejects_without_permissions(self, _):
        params = {"user": _user(), "data": _Data(), "files": _Files()}
        res = ComunicadosService._execute_create_comunicado(params)
        assert res["success"] is False
        assert "sin permiso" in res["message"]

    @patch("backend.apps.institucion.models.CicloAcademico")
    @patch("backend.apps.core.services.integrity_service.IntegrityService.validate_school_integrity_or_raise")
    @patch("backend.apps.comunicados.services.comunicados_service.CommonValidations.validate_admin_permissions", return_value=(True, ""))
    def test_execute_create_comunicado_invalid_datetime(self, _, __, mock_ciclo):
        mock_ciclo.objects.filter.return_value.first.return_value = Mock()

        params = {
            "user": _user(),
            "data": _Data({
                "tipo": "general",
                "titulo": "Aviso",
                "contenido": "Contenido",
                "destinatario": "todos",
                "fecha_evento": "invalid-date",
            }),
            "files": _Files(),
        }
        res = ComunicadosService._execute_create_comunicado(params)
        assert res["success"] is False
        assert "Formato de fecha inválido" in res["message"]

    @patch("backend.apps.comunicados.models.Comunicado")
    @patch("backend.apps.institucion.models.CicloAcademico")
    @patch("backend.apps.core.services.integrity_service.IntegrityService.validate_school_integrity_or_raise")
    @patch("backend.apps.comunicados.services.comunicados_service.CommonValidations.validate_admin_permissions", return_value=(True, ""))
    def test_execute_create_comunicado_success_minimal(self, _, __, mock_ciclo, mock_comunicado):
        mock_ciclo.objects.filter.return_value.first.return_value = Mock()
        creado = Mock()
        creado.titulo = "Aviso"
        mock_comunicado.objects.create.return_value = creado

        params = {
            "user": _user(),
            "data": _Data({
                "tipo": "general",
                "titulo": "Aviso",
                "contenido": "Contenido",
                "destinatario": "todos",
            }),
            "files": _Files(),
        }
        res = ComunicadosService._execute_create_comunicado(params)
        assert res["success"] is True
        assert res["comunicado"] == creado

    @patch("backend.apps.comunicados.models.PlantillaComunicado")
    def test_get_plantillas_for_colegio_groups_by_category(self, mock_plantilla):
        user = _user()
        p1 = Mock()
        p1.get_categoria_display.return_value = "General"
        p2 = Mock()
        p2.get_categoria_display.return_value = "General"
        p3 = Mock()
        p3.get_categoria_display.return_value = "Eventos"
        qs = Mock()
        qs.order_by.return_value = qs
        qs.__iter__ = Mock(return_value=iter([p1, p2, p3]))
        qs.count.return_value = 3
        mock_plantilla.objects.filter.return_value = qs

        data = ComunicadosService.get_plantillas_for_colegio(user)
        assert data["total_plantillas"] == 3
        assert len(data["plantillas_por_categoria"]["General"]) == 2
        assert len(data["plantillas_por_categoria"]["Eventos"]) == 1

    @patch("backend.apps.comunicados.models.PlantillaComunicado")
    @patch("backend.apps.comunicados.models.Comunicado")
    def test_get_plantilla_form_contexts(self, mock_comunicado, mock_plantilla):
        mock_plantilla.CATEGORIAS = [("general", "General")]
        mock_comunicado.TIPOS = [("comunicado", "Comunicado")]
        mock_comunicado.DESTINATARIOS = [("todos", "Todos")]

        plantilla_inst = Mock()
        plantilla_inst.get_variables_disponibles.return_value = ["{{curso}}"]
        mock_plantilla.return_value = plantilla_inst

        create_ctx = ComunicadosService.get_plantilla_creation_form_context()
        edit_ctx = ComunicadosService.get_plantilla_edit_form_context(plantilla_inst)

        assert "categorias" in create_ctx and "tipos" in create_ctx
        assert edit_ctx["plantilla"] is plantilla_inst
        assert edit_ctx["variables_disponibles"] == ["{{curso}}"]

    @patch("backend.apps.comunicados.models.PlantillaComunicado")
    def test_crud_plantilla_methods(self, mock_plantilla):
        user = _user()
        data = {
            "nombre": "Base",
            "categoria": "general",
            "descripcion": "desc",
            "titulo_plantilla": "Titulo {{curso}}",
            "contenido_plantilla": "Contenido {{curso}}",
            "tipo_default": "comunicado",
            "destinatario_default": "todos",
            "requiere_confirmacion": "on",
            "es_prioritario": "on",
        }

        creada = Mock(nombre="Base")
        mock_plantilla.objects.create.return_value = creada
        res_create = ComunicadosService.crear_plantilla(user, data)
        assert res_create is creada

        existente = Mock(colegio=user.colegio)
        with patch("django.shortcuts.get_object_or_404", return_value=existente):
            res_update = ComunicadosService.actualizar_plantilla(user, 1, data)
            assert res_update is existente
            existente.save.assert_called()

            res_delete = ComunicadosService.eliminar_plantilla(user, 1)
            assert res_delete is existente
            assert existente.activa is False

    def test_get_plantilla_for_user_permission_error(self):
        user = _user()
        other_plantilla = Mock(colegio=Mock())
        with patch("django.shortcuts.get_object_or_404", return_value=other_plantilla):
            with pytest.raises(PermissionError):
                ComunicadosService.get_plantilla_for_user(user, 1)

    def test_get_active_plantilla_for_user_permission_error(self):
        user = _user()
        other_plantilla = Mock(colegio=Mock())
        with patch("django.shortcuts.get_object_or_404", return_value=other_plantilla):
            with pytest.raises(PermissionError):
                ComunicadosService.get_active_plantilla_for_user(user, 1)

    @patch("backend.apps.cursos.models.Curso")
    def test_get_active_courses_for_user(self, mock_curso):
        user = _user()
        qs = Mock()
        mock_curso.objects.filter.return_value = qs
        assert ComunicadosService.get_active_courses_for_user(user) is qs

    @patch("backend.apps.comunicados.models.EstadisticaComunicado")
    @patch("backend.apps.comunicados.models.ConfirmacionLectura")
    def test_get_massive_confirmations_context_filters_and_groups(self, mock_confirmacion, mock_stats):
        user = _user()
        comunicado = Mock()

        stats = Mock()
        mock_stats.objects.get_or_create.return_value = (stats, True)

        prof_user = Mock(perfil_profesor=Mock())
        est_user = Mock(perfil_estudiante=Mock())
        apo_user = Mock(perfil_apoderado=Mock())

        conf_prof = Mock(usuario=prof_user)
        conf_est = Mock(usuario=est_user)
        conf_apo = Mock(usuario=apo_user)

        base_qs = Mock()
        base_qs.select_related.return_value = base_qs
        base_qs.order_by.return_value = base_qs
        base_qs.filter.return_value = [conf_prof, conf_est, conf_apo]
        base_qs.count.return_value = 3
        mock_confirmacion.objects.filter.return_value = base_qs

        data = ComunicadosService.get_massive_confirmations_context(user, comunicado, filtro="leidos", recalcular=True)
        stats.calcular_estadisticas.assert_called_once()
        assert data["total_confirmaciones"] == 3
        assert len(data["confirmaciones_por_rol"]["profesores"]) == 1
        assert len(data["confirmaciones_por_rol"]["estudiantes"]) == 1
        assert len(data["confirmaciones_por_rol"]["apoderados"]) == 1

    @patch("backend.apps.notificaciones.models.Notificacion")
    @patch("backend.apps.comunicados.models.ConfirmacionLectura")
    def test_send_massive_reminders_bulk_create_and_empty(self, mock_confirmacion, mock_notificacion):
        user = _user()
        comunicado = Mock(id_comunicado=99, titulo="Importante", es_prioritario=False)

        c1 = Mock(usuario=Mock())
        c2 = Mock(usuario=Mock())
        qs = Mock()
        qs.select_related.return_value = [c1, c2]
        mock_confirmacion.objects.filter.return_value = qs

        created_count = ComunicadosService.send_massive_reminders(user, comunicado)
        assert created_count == 2
        mock_notificacion.objects.bulk_create.assert_called_once()

        mock_notificacion.objects.bulk_create.reset_mock()
        qs_empty = Mock()
        qs_empty.select_related.return_value = []
        mock_confirmacion.objects.filter.return_value = qs_empty
        created_count_empty = ComunicadosService.send_massive_reminders(user, comunicado)
        assert created_count_empty == 0
        mock_notificacion.objects.bulk_create.assert_not_called()

    @patch("backend.apps.comunicados.models.Comunicado")
    def test_create_comunicado_from_template(self, mock_comunicado):
        user = _user()
        plantilla = Mock()
        plantilla.tipo_default = "comunicado"
        plantilla.destinatario_default = "todos"
        plantilla.renderizar.return_value = ("Titulo", "Contenido")

        creado = Mock()
        mock_comunicado.objects.create.return_value = creado

        data = {"var_curso": "1A", "requiere_confirmacion": "on", "es_prioritario": "on"}
        result = ComunicadosService.create_comunicado_from_template(user, plantilla, data)

        assert result is creado
        plantilla.incrementar_contador_uso.assert_called_once()

    @patch("backend.apps.comunicados.models.Comunicado")
    def test_get_template_usage_context_extracts_vars(self, mock_comunicado):
        user = _user()
        plantilla = Mock()
        plantilla.titulo_plantilla = "Aviso {{curso}}"
        plantilla.contenido_plantilla = "Hora {{hora}} Lugar {{lugar}}"
        mock_comunicado.TIPOS = [("comunicado", "Comunicado")]
        mock_comunicado.DESTINATARIOS = [("todos", "Todos")]

        with patch.object(ComunicadosService, "get_active_courses_for_user", return_value=["1A"]):
            ctx = ComunicadosService.get_template_usage_context(user, plantilla)

        assert sorted(ctx["variables"]) == ["curso", "hora", "lugar"]
        assert ctx["cursos"] == ["1A"]

    @patch("backend.apps.accounts.models.PerfilEstudiante")
    @patch("backend.apps.comunicados.models.Comunicado")
    @patch("backend.apps.comunicados.services.comunicados_service.PolicyService.has_capability")
    def test_get_comunicados_for_user_by_roles(self, mock_has_capability, mock_comunicado, mock_perfil):
        user = _user("Profesor")
        qs = Mock()
        qs.select_related.return_value.prefetch_related.return_value.order_by.return_value = "ordered"
        mock_comunicado.objects.filter.return_value = qs

        def _teacher_caps(_u, capability, school_id=None):
            return capability == "TEACHER_VIEW"

        mock_has_capability.side_effect = _teacher_caps
        assert ComunicadosService.get_comunicados_for_user(user) == "ordered"

        def _student_caps(_u, capability, school_id=None):
            return capability in {"CLASS_VIEW", "GRADE_VIEW"}

        mock_has_capability.side_effect = _student_caps
        perfil = Mock(curso_actual=Mock())
        mock_perfil.objects.get.return_value = perfil
        qs_est = Mock()
        qs_est.distinct.return_value = qs_est
        qs_est.select_related.return_value.prefetch_related.return_value.order_by.return_value = "ordered-est"
        mock_comunicado.objects.filter.return_value = qs_est
        assert ComunicadosService.get_comunicados_for_user(user) == "ordered-est"


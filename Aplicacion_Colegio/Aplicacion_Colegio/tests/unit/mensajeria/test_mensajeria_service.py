from unittest.mock import Mock, patch

import pytest

from backend.apps.mensajeria.services.mensajeria_service import MensajeriaService
from backend.common.exceptions import PrerequisiteException


def _user(user_id=1, active=True, rbd=123):
    user = Mock()
    user.id = user_id
    user.is_active = active
    user.rbd_colegio = rbd
    user.email = f"u{user_id}@test.cl"
    return user


def _clase(activa=True, profesor_id=1, rbd=123):
    clase = Mock()
    clase.activo = activa
    clase.profesor_id = profesor_id
    clase.id_clase = 55
    clase.colegio = Mock()
    clase.colegio.rbd = rbd
    clase.asignatura = Mock()
    clase.asignatura.nombre = "Matemáticas"
    clase.curso = Mock()
    clase.curso.ciclo_academico = "CICLO"
    return clase


class TestMensajeriaService:
    def test_validate_operation_required(self):
        with pytest.raises(ValueError):
            MensajeriaService.validate("", {})

    def test_validate_params_must_be_dict(self):
        with pytest.raises(ValueError):
            MensajeriaService.validate("x", [])

    def test_execute_unsupported_operation_raises(self):
        with pytest.raises(ValueError):
            MensajeriaService.execute("no_existe", {})

    def test_execute_dispatches_to_handler(self):
        with patch.object(MensajeriaService, "_execute_ping", return_value={"ok": True}, create=True):
            assert MensajeriaService.execute("ping", {}) == {"ok": True}

    @patch("backend.apps.accounts.models.PerfilEstudiante")
    def test_user_has_access_to_class_as_student(self, mock_perfil):
        user = _user(user_id=20)
        clase = _clase(profesor_id=1)
        perfil = Mock()
        perfil.estado_academico = "Activo"
        perfil.ciclo_actual = "CICLO"
        mock_perfil.objects.filter.return_value.first.return_value = perfil

        assert MensajeriaService.user_has_access_to_class(user, clase) is True

    @patch("backend.apps.accounts.models.PerfilEstudiante")
    def test_user_has_access_to_class_without_profile(self, mock_perfil):
        user = _user(user_id=20)
        clase = _clase(profesor_id=1)
        mock_perfil.objects.filter.return_value.first.return_value = None

        assert MensajeriaService.user_has_access_to_class(user, clase) is False

    def test_user_has_access_to_class_as_professor(self):
        user = _user(user_id=7)
        clase = _clase(profesor_id=7)
        assert MensajeriaService.user_has_access_to_class(user, clase) is True

    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_get_or_create_conversacion_rejects_inactive_class(self, _):
        clase = _clase(activa=False)
        with pytest.raises(TypeError):
            MensajeriaService.get_or_create_conversacion(clase, _user(1), _user(2))

    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_get_or_create_conversacion_rejects_inactive_user(self, _):
        clase = _clase()
        with pytest.raises(TypeError):
            MensajeriaService.get_or_create_conversacion(clase, _user(1, active=False), _user(2))

    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_get_or_create_conversacion_rejects_school_mismatch(self, _):
        clase = _clase(rbd=123)
        with pytest.raises(TypeError):
            MensajeriaService.get_or_create_conversacion(clase, _user(1, rbd=123), _user(2, rbd=999))

    @patch("backend.apps.mensajeria.models.Conversacion")
    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_get_or_create_conversacion_success_orders_participants(self, _, mock_conversacion):
        clase = _clase()
        u1 = _user(9)
        u2 = _user(3)

        conversacion = Mock()
        conversacion.ultima_actividad = "now"
        mock_conversacion.objects.get_or_create.return_value = (conversacion, True)

        with patch.object(MensajeriaService, "user_has_access_to_class", return_value=True):
            result = MensajeriaService.get_or_create_conversacion(clase, u1, u2)

        assert result == conversacion
        kwargs = mock_conversacion.objects.get_or_create.call_args.kwargs
        assert kwargs["participante1"].id == 3
        assert kwargs["participante2"].id == 9

    @patch("backend.apps.mensajeria.models.Conversacion")
    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_get_or_create_conversacion_updates_missing_last_activity(self, _, mock_conversacion):
        clase = _clase()
        conversacion = Mock()
        conversacion.ultima_actividad = None
        mock_conversacion.objects.get_or_create.return_value = (conversacion, False)

        with patch.object(MensajeriaService, "user_has_access_to_class", return_value=True):
            MensajeriaService.get_or_create_conversacion(clase, _user(1), _user(2))

        conversacion.save.assert_called_once()

    def test_validate_message_data_requires_content_or_file(self):
        ok, msg = MensajeriaService.validate_message_data("   ", None)
        assert ok is False
        assert "Escribe" in msg

    def test_validate_message_data_accepts_content(self):
        ok, msg = MensajeriaService.validate_message_data("hola", None)
        assert ok is True
        assert msg == ""

    def test_validate_destinatario_for_class_professor_ok(self):
        clase = _clase(profesor_id=5)
        destinatario = _user(5)
        ok, msg = MensajeriaService.validate_destinatario_for_class(clase, destinatario)
        assert ok is True
        assert msg == ""

    @patch("backend.apps.accounts.models.PerfilEstudiante")
    def test_validate_destinatario_for_class_invalid_student(self, mock_perfil):
        clase = _clase(profesor_id=5)
        destinatario = _user(7)
        perfil = Mock()
        perfil.ciclo_actual = "OTRO"
        mock_perfil.objects.filter.return_value.first.return_value = perfil

        ok, msg = MensajeriaService.validate_destinatario_for_class(clase, destinatario)
        assert ok is False
        assert "Destinatario inválido" in msg

    def test_validate_conversation_access(self):
        user = _user(1)
        conv = Mock()
        conv.participante1 = user
        conv.participante2 = _user(2)
        assert MensajeriaService.validate_conversation_access(user, conv) is True

    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_send_message_rejects_inactive_sender(self, _):
        conversacion = Mock()
        conversacion.clase = _clase(activa=True)
        conversacion.participante1_id = 1
        conversacion.participante2_id = 2
        with pytest.raises(TypeError):
            MensajeriaService.send_message(conversacion, _user(1, active=False), _user(2), "hola", None)

    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_send_message_rejects_non_participants(self, _):
        conversacion = Mock()
        conversacion.id = 99
        conversacion.clase = _clase(activa=True)
        conversacion.participante1_id = 1
        conversacion.participante2_id = 2
        with pytest.raises(TypeError):
            MensajeriaService.send_message(conversacion, _user(3), _user(2), "hola", None)

    @patch("backend.apps.mensajeria.models.Mensaje")
    @patch("backend.apps.mensajeria.services.mensajeria_service.IntegrityService.validate_school_integrity_or_raise")
    def test_send_message_success(self, _, mock_mensaje):
        conversacion = Mock()
        conversacion.id = 99
        conversacion.clase = _clase(activa=True)
        conversacion.participante1_id = 1
        conversacion.participante2_id = 2

        creado = Mock()
        mock_mensaje.objects.create.return_value = creado

        result = MensajeriaService.send_message(conversacion, _user(1), _user(2), "hola", None)
        assert result == creado
        conversacion.save.assert_called_once()

    @patch("django.shortcuts.get_object_or_404")
    @patch.object(MensajeriaService, "validate_conversation_access", return_value=False)
    def test_get_conversacion_for_user_without_access_returns_none(self, _, mock_get):
        conv = Mock()
        mock_get.return_value = conv
        assert MensajeriaService.get_conversacion_for_user(_user(1), 10) is None

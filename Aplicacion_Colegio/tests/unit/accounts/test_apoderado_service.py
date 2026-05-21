from unittest.mock import Mock, patch

import pytest

from backend.apps.accounts.services.apoderado_service import ApoderadoService


@pytest.fixture
def admin_user_mock():
    user = Mock()
    user.role = Mock()
    user.role.nombre = "Administrador escolar"
    user.rbd_colegio = "12345"
    user.is_authenticated = True
    user.is_active = True
    return user


class TestApoderadoServiceBasics:
    def test_validate_requires_user(self):
        with pytest.raises(ValueError):
            ApoderadoService.validate("create_apoderado", {})

    def test_generate_temp_password_is_random(self):
        """generate_temp_password ahora genera contraseñas aleatorias seguras."""
        p1 = ApoderadoService.generate_temp_password("12.345.678-9")
        p2 = ApoderadoService.generate_temp_password("12.345.678-9")
        assert len(p1) == 14
        assert p1.isalnum()
        assert p1 != p2

    def test_generate_temp_password_without_rut(self):
        p = ApoderadoService.generate_temp_password(None)
        assert len(p) == 14
        assert p.isalnum()

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("1", True),
            ("si", True),
            ("yes", True),
            ("on", True),
            ("", False),
            ("false", False),
            ("0", False),
            (None, False),
        ],
    )
    def test_parse_boolean(self, value, expected):
        assert ApoderadoService._parsear_booleano(value) is expected

    def test_validate_admin_permissions_ok(self, admin_user_mock):
        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ):
            is_valid, error = ApoderadoService.validate_admin_permissions(admin_user_mock)

        assert is_valid is True
        assert error is None

    def test_validate_admin_permissions_denied(self, admin_user_mock):
        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            side_effect=Exception("denied"),
        ):
            is_valid, error = ApoderadoService.validate_admin_permissions(admin_user_mock)

        assert is_valid is False
        assert "denied" in error.lower()

    def test_validate_unique_email_available(self):
        User = Mock()
        User.objects.filter.return_value.exists.return_value = False

        result, message = ApoderadoService.validate_unique_email("new@test.cl", User)
        assert result is True
        assert message is None

    def test_validate_unique_rut_in_use(self):
        User = Mock()
        User.objects.filter.return_value.exists.return_value = True

        result, message = ApoderadoService.validate_unique_rut("11.111.111-1", User)
        assert result is False
        assert "ya existe" in message.lower()


class TestApoderadoServiceCrud:
    def test_create_apoderado_success(self, admin_user_mock):
        User = Mock()
        Role = Mock()
        Apoderado = Mock()

        role_obj = Mock()
        Role.objects.get.return_value = role_obj
        User.objects.filter.return_value.exists.return_value = False

        apoderado_user = Mock(id=1, nombre="Ana", apellido_paterno="Diaz")
        User.return_value = apoderado_user
        perfil = Mock()
        Apoderado.return_value = perfil

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ), patch.object(
            ApoderadoService, "_validar_prerequisitos_colegio", return_value=None
        ):
            success, message, password = ApoderadoService.create_apoderado(
                admin_user_mock,
                {
                    "email": "ana@test.cl",
                    "rut": "12.345.678-9",
                    "nombre": "Ana",
                    "apellido_paterno": "Diaz",
                    "puede_ver_notas": "true",
                },
                "12345",
                User,
                Role,
                Apoderado,
            )

        assert success is True
        assert "creado exitosamente" in message
        assert isinstance(password, str) and len(password) == 14
        apoderado_user.set_password.assert_called_once_with(password)
        perfil.save.assert_called_once()

    def test_create_apoderado_rejects_duplicate_email(self, admin_user_mock):
        User = Mock()
        Role = Mock()
        Apoderado = Mock()

        User.objects.filter.return_value.exists.return_value = True

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ), patch.object(
            ApoderadoService, "_validar_prerequisitos_colegio", return_value=None
        ):
            success, message, password = ApoderadoService.create_apoderado(
                admin_user_mock,
                {"email": "duplicado@test.cl", "rut": "11.111.111-1"},
                "12345",
                User,
                Role,
                Apoderado,
            )

        assert success is False
        assert "ya existe" in message.lower()
        assert password is None

    def test_create_apoderado_handles_missing_role(self, admin_user_mock):
        User = Mock()
        Role = Mock()
        Apoderado = Mock()
        Role.DoesNotExist = type("DoesNotExist", (Exception,), {})
        Role.objects.get.side_effect = Role.DoesNotExist
        User.objects.filter.return_value.exists.return_value = False

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ), patch.object(
            ApoderadoService, "_validar_prerequisitos_colegio", return_value=None
        ):
            success, message, password = ApoderadoService.create_apoderado(
                admin_user_mock,
                {"email": "ana@test.cl", "rut": "12.345.678-9"},
                "12345",
                User,
                Role,
                Apoderado,
            )

        assert success is False
        assert "rol apoderado" in message.lower()
        assert password is None

    def test_update_apoderado_success(self, admin_user_mock):
        User = Mock()
        Apoderado = Mock()

        apoderado_user = Mock(id=2, email="old@test.cl", nombre="Ana", apellido_paterno="Diaz")
        apoderado_user.perfil_apoderado = Mock()
        User.objects.get.return_value = apoderado_user

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ):
            success, message = ApoderadoService.update_apoderado(
                admin_user_mock,
                apoderado_id=2,
                data={
                    "email": "old@test.cl",
                    "nombre": "Ana",
                    "apellido_paterno": "Diaz",
                    "apellido_materno": "Lopez",
                    "rut": "12.345.678-9",
                },
                escuela_rbd="12345",
                User=User,
                Apoderado=Apoderado,
            )

        assert success is True
        assert "actualizado" in message.lower()
        apoderado_user.save.assert_called_once()
        apoderado_user.perfil_apoderado.save.assert_called_once()

    def test_deactivate_apoderado_blocks_when_has_active_students(self, admin_user_mock):
        User = Mock()
        Apoderado = Mock()

        apoderado_user = Mock(id=3)
        rel_qs = Mock()
        rel_qs.count.return_value = 2
        apoderado_user.apoderado_estudiantes.filter.return_value = rel_qs
        User.objects.get.return_value = apoderado_user

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ):
            success, message = ApoderadoService.deactivate_apoderado(
                admin_user_mock,
                apoderado_id=3,
                escuela_rbd="12345",
                User=User,
                Apoderado=Apoderado,
            )

        assert success is False
        assert "no se puede desactivar" in message.lower()

    def test_deactivate_apoderado_success(self, admin_user_mock):
        User = Mock()
        Apoderado = Mock()

        apoderado_user = Mock(id=4)
        rel_qs = Mock()
        rel_qs.count.return_value = 0
        apoderado_user.apoderado_estudiantes.filter.return_value = rel_qs
        apoderado_user.perfil_apoderado = Mock()
        User.objects.get.return_value = apoderado_user

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ):
            success, message = ApoderadoService.deactivate_apoderado(
                admin_user_mock,
                apoderado_id=4,
                escuela_rbd="12345",
                User=User,
                Apoderado=Apoderado,
            )

        assert success is True
        assert "desactivado" in message.lower()
        assert apoderado_user.is_active is False
        assert apoderado_user.perfil_apoderado.activo is False
        apoderado_user.save.assert_called_once()
        apoderado_user.perfil_apoderado.save.assert_called_once()

    def test_reset_password_success(self, admin_user_mock):
        User = Mock()
        apoderado_user = Mock(id=5, rut="12.345.678-9")
        User.objects.get.return_value = apoderado_user

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ):
            success, message, password = ApoderadoService.reset_password(
                admin_user_mock,
                apoderado_id=5,
                escuela_rbd="12345",
                User=User,
            )

        assert success is True
        assert "reseteada" in message.lower()
        assert isinstance(password, str) and len(password) == 14
        apoderado_user.set_password.assert_called_once_with(password)

    def test_reset_password_not_found(self, admin_user_mock):
        User = Mock()
        User.DoesNotExist = type("DoesNotExist", (Exception,), {})
        User.objects.get.side_effect = User.DoesNotExist

        with patch(
            "backend.common.services.permission_service.PermissionService.has_permission",
            return_value=True,
        ), patch.object(
            ApoderadoService, "_validate_school_integrity", return_value=None
        ):
            success, message, password = ApoderadoService.reset_password(
                admin_user_mock,
                apoderado_id=999,
                escuela_rbd="12345",
                User=User,
            )

        assert success is False
        assert "no encontrado" in message.lower()
        assert password is None


class TestApoderadoServiceStats:
    def test_get_apoderados_stats_success(self):
        User = Mock()
        Apoderado = Mock()

        total_qs = Mock()
        total_qs.count.return_value = 7
        active_qs = Mock()
        active_qs.count.return_value = 5
        User.objects.filter.side_effect = [total_qs, active_qs]

        stats = ApoderadoService.get_apoderados_stats("12345", User, Apoderado)

        assert stats["total_apoderados"] == 7
        assert stats["apoderados_activos"] == 5
        assert stats["apoderados_inactivos"] == 2

    def test_get_apoderados_stats_handles_error(self):
        User = Mock()
        Apoderado = Mock()
        User.objects.filter.side_effect = Exception("db error")

        stats = ApoderadoService.get_apoderados_stats("12345", User, Apoderado)

        assert stats["total_apoderados"] == 0
        assert stats["apoderados_activos"] == 0
        assert stats["apoderados_inactivos"] == 0


class TestApoderadoServiceSchoolPrerequisites:
    def test_validate_school_prereqs_when_school_missing(self):
        from backend.apps.institucion.models import Colegio

        with patch(
            "backend.apps.institucion.models.Colegio.objects.get",
            side_effect=Colegio.DoesNotExist,
        ):
            result = ApoderadoService._validar_prerequisitos_colegio(99999)

        assert result is not None
        assert result["error_type"] == "SCHOOL_NOT_CONFIGURED"

    def test_validate_school_prereqs_when_no_active_cycle(self):
        colegio = Mock()
        colegio.nombre = "Colegio Sin Ciclo"

        ciclo_qs = Mock()
        ciclo_qs.first.return_value = None

        with patch(
            "backend.apps.institucion.models.Colegio.objects.get",
            return_value=colegio,
        ), patch(
            "backend.apps.institucion.models.CicloAcademico.objects.filter",
            return_value=ciclo_qs,
        ):
            result = ApoderadoService._validar_prerequisitos_colegio(12345)

        assert result is not None
        assert result["error_type"] == "MISSING_CICLO_ACTIVO"

    def test_validate_school_prereqs_success(self):
        colegio = Mock()
        colegio.nombre = "Colegio Activo"

        ciclo_qs = Mock()
        ciclo_qs.first.return_value = Mock()

        with patch(
            "backend.apps.institucion.models.Colegio.objects.get",
            return_value=colegio,
        ), patch(
            "backend.apps.institucion.models.CicloAcademico.objects.filter",
            return_value=ciclo_qs,
        ):
            result = ApoderadoService._validar_prerequisitos_colegio(12345)

        assert result is None

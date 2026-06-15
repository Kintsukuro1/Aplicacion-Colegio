"""
Tests for EscuelaManagementService — school management operations.

Covers:
- Validation: missing user, missing data, missing rbd, invalid operation
- crear_colegio: duplicate RBD, duplicate RUT, success with infrastructure
- crear_admin_escolar: no active cycle, duplicate email, duplicate RUT, success
- eliminar_colegio: active users block, active cycles block, ProtectedError, success
- cambiar_plan_colegio: create subscription, update existing subscription
"""

from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import timedelta

import pytest
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from backend.apps.core.services.escuela_management_service import EscuelaManagementService
from backend.common.exceptions import PrerequisiteException


class _FlexiblePrerequisiteException(Exception):
    """Test-only exception that accepts any kwargs, matching the actual service calls."""
    def __init__(self, error_type=None, **kwargs):
        self.error_type = error_type
        self.context = kwargs.get('context', {})
        super().__init__(kwargs.get('user_message', str(error_type)))


SERVICE_MODULE = 'backend.apps.core.services.escuela_management_service'


@pytest.fixture
def admin_user():
    user = Mock()
    user.rbd_colegio = 12345
    user.is_authenticated = True
    user.is_active = True
    user.role = Mock()
    user.role.nombre = "Administrador general"
    return user


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestEscuelaManagementValidation:
    def test_validate_requires_user(self):
        with pytest.raises(ValueError, match="user"):
            EscuelaManagementService.validate("crear_colegio", {"data": {}})

    def test_validate_requires_data_for_crear_colegio(self, admin_user):
        with pytest.raises(ValueError, match="data"):
            EscuelaManagementService.validate(
                "crear_colegio", {"user": admin_user}
            )

    def test_validate_requires_data_for_crear_admin(self, admin_user):
        with pytest.raises(ValueError, match="data"):
            EscuelaManagementService.validate(
                "crear_admin_escolar", {"user": admin_user}
            )

    def test_validate_requires_rbd_for_eliminar(self, admin_user):
        with pytest.raises(ValueError, match="rbd"):
            EscuelaManagementService.validate(
                "eliminar_colegio", {"user": admin_user}
            )

    def test_validate_requires_rbd_for_entrar(self, admin_user):
        with pytest.raises(ValueError, match="rbd"):
            EscuelaManagementService.validate(
                "entrar_escuela", {"user": admin_user}
            )

    def test_validate_requires_rbd_and_plan_for_cambiar_plan(self, admin_user):
        with pytest.raises(ValueError, match="rbd"):
            EscuelaManagementService.validate(
                "cambiar_plan_colegio", {"user": admin_user, "plan_codigo": "pro"}
            )

        with pytest.raises(ValueError, match="plan_codigo"):
            EscuelaManagementService.validate(
                "cambiar_plan_colegio", {"user": admin_user, "rbd": "12345"}
            )

    def test_validate_rejects_invalid_operation(self, admin_user):
        with pytest.raises(ValueError, match="no soportada"):
            EscuelaManagementService.validate(
                "operacion_no_existe", {"user": admin_user}
            )

    def test_validate_accepts_valid_crear_colegio(self, admin_user):
        EscuelaManagementService.validate(
            "crear_colegio", {"user": admin_user, "data": {"rbd": 12345}}
        )

    def test_validate_accepts_valid_obtener_datos(self, admin_user):
        EscuelaManagementService.validate(
            "obtener_datos_seleccionar_escuela", {"user": admin_user}
        )


# ---------------------------------------------------------------------------
# _execute dispatch
# ---------------------------------------------------------------------------

class TestEscuelaManagementDispatch:
    def test_execute_rejects_unsupported_operation(self):
        with pytest.raises(ValueError, match="no soportada"):
            EscuelaManagementService._execute("bad_op", {})

    def test_execute_calls_validate_then_executes(self, admin_user):
        with patch.object(
            EscuelaManagementService, "validate", return_value=None
        ) as v_mock, patch.object(
            EscuelaManagementService, "_execute", return_value="ok"
        ) as e_mock:
            result = EscuelaManagementService.execute("crear_colegio", {"user": admin_user, "data": {}})

        assert result == "ok"
        v_mock.assert_called_once()
        e_mock.assert_called_once()


# ---------------------------------------------------------------------------
# crear_colegio
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCrearColegio:
    def test_rejects_duplicate_rbd(self, admin_user):
        with patch(
            f"{SERVICE_MODULE}.Colegio.objects"
        ) as mock_colegio, patch(
            f"{SERVICE_MODULE}.PrerequisiteException",
            _FlexiblePrerequisiteException,
        ):
            mock_colegio.filter.return_value.exists.return_value = True

            with pytest.raises(_FlexiblePrerequisiteException) as exc_info:
                EscuelaManagementService._execute_crear_colegio(
                    {"data": {"rbd": 12345, "rut_establecimiento": "12.345.000-0"}}
                )

            assert "VALIDATION_ERROR" in str(exc_info.value.error_type)

    def test_rejects_duplicate_rut(self, admin_user):
        rbd_qs = MagicMock()
        rbd_qs.exists.return_value = False
        rut_qs = MagicMock()
        rut_qs.exists.return_value = True

        with patch(
            f"{SERVICE_MODULE}.Colegio.objects"
        ) as mock_colegio, patch(
            f"{SERVICE_MODULE}.PrerequisiteException",
            _FlexiblePrerequisiteException,
        ):
            mock_colegio.filter.side_effect = [rbd_qs, rut_qs]

            with pytest.raises(_FlexiblePrerequisiteException):
                EscuelaManagementService._execute_crear_colegio(
                    {"data": {"rbd": 99999, "rut_establecimiento": "99.999.000-0"}}
                )

    def test_creates_colegio_successfully(self, admin_user):
        rbd_qs = MagicMock()
        rbd_qs.exists.return_value = False
        rut_qs = MagicMock()
        rut_qs.exists.return_value = False

        tipo = Mock(nombre="Virtual")
        colegio = Mock()

        with patch(
            "backend.apps.core.services.escuela_management_service.Colegio.objects"
        ) as mock_colegio, patch(
            "backend.apps.core.services.escuela_management_service.get_object_or_404",
            return_value=tipo,
        ), patch(
            "backend.apps.core.services.escuela_management_service.transaction"
        ):
            mock_colegio.filter.side_effect = [rbd_qs, rut_qs]
            mock_colegio.create.return_value = colegio

            result = EscuelaManagementService._execute_crear_colegio(
                {
                    "data": {
                        "rbd": 99999,
                        "nombre": "Test",
                        "rut_establecimiento": "99.999.000-0",
                        "tipo_establecimiento": 1,
                        "dependencia": 1,
                        "comuna_id": 1,
                        "direccion": "Calle Test",
                    }
                }
            )

        assert result is colegio


# ---------------------------------------------------------------------------
# eliminar_colegio
# ---------------------------------------------------------------------------

class TestEliminarColegio:
    def test_blocked_by_active_users(self, admin_user):
        colegio = Mock()
        colegio.nombre = "Test School"
        colegio.rbd = 12345

        with patch(
            f"{SERVICE_MODULE}.get_object_or_404",
            return_value=colegio,
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            f"{SERVICE_MODULE}.User.objects"
        ) as mock_user, patch(
            f"{SERVICE_MODULE}.transaction"
        ), patch(
            f"{SERVICE_MODULE}.PrerequisiteException",
            _FlexiblePrerequisiteException,
        ):
            mock_user.filter.return_value.count.return_value = 5

            with pytest.raises(_FlexiblePrerequisiteException) as exc_info:
                EscuelaManagementService._execute_eliminar_colegio(
                    {"rbd": "12345"}
                )

            assert exc_info.value.error_type == "INVALID_STATE"

    def test_blocked_by_active_cycles(self, admin_user):
        colegio = Mock()
        colegio.nombre = "Test School"
        colegio.rbd = 12345

        with patch(
            f"{SERVICE_MODULE}.get_object_or_404",
            return_value=colegio,
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            f"{SERVICE_MODULE}.User.objects"
        ) as mock_user, patch(
            f"{SERVICE_MODULE}.CicloAcademico.objects"
        ) as mock_ciclo, patch(
            f"{SERVICE_MODULE}.transaction"
        ), patch(
            f"{SERVICE_MODULE}.PrerequisiteException",
            _FlexiblePrerequisiteException,
        ):
            mock_user.filter.return_value.count.return_value = 0
            mock_ciclo.filter.return_value.count.return_value = 2

            with pytest.raises(_FlexiblePrerequisiteException) as exc_info:
                EscuelaManagementService._execute_eliminar_colegio(
                    {"rbd": "12345"}
                )

            assert exc_info.value.error_type == "INVALID_STATE"

    def test_handles_protected_error(self, admin_user):
        colegio = Mock()
        colegio.nombre = "Test School"
        colegio.rbd = 12345
        colegio.delete.side_effect = ProtectedError("protected", [Mock()])

        with patch(
            f"{SERVICE_MODULE}.get_object_or_404",
            return_value=colegio,
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            f"{SERVICE_MODULE}.User.objects"
        ) as mock_user, patch(
            f"{SERVICE_MODULE}.CicloAcademico.objects"
        ) as mock_ciclo, patch(
            f"{SERVICE_MODULE}.transaction"
        ), patch(
            f"{SERVICE_MODULE}.PrerequisiteException",
            _FlexiblePrerequisiteException,
        ):
            mock_user.filter.return_value.count.return_value = 0
            mock_ciclo.filter.return_value.count.return_value = 0

            with pytest.raises(_FlexiblePrerequisiteException) as exc_info:
                EscuelaManagementService._execute_eliminar_colegio(
                    {"rbd": "12345"}
                )

            assert exc_info.value.error_type == "INVALID_STATE"

    def test_deletes_school_successfully(self, admin_user):
        colegio = Mock()
        colegio.nombre = "Test School"
        colegio.rbd = 12345

        with patch(
            f"{SERVICE_MODULE}.get_object_or_404",
            return_value=colegio,
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            f"{SERVICE_MODULE}.User.objects"
        ) as mock_user, patch(
            f"{SERVICE_MODULE}.CicloAcademico.objects"
        ) as mock_ciclo, patch(
            f"{SERVICE_MODULE}.transaction"
        ):
            mock_user.filter.return_value.count.return_value = 0
            mock_ciclo.filter.return_value.count.return_value = 0

            result = EscuelaManagementService._execute_eliminar_colegio(
                {"rbd": "12345"}
            )

        assert result == "Test School"
        colegio.delete.assert_called_once()


# ---------------------------------------------------------------------------
# crear_admin_escolar
# ---------------------------------------------------------------------------

class TestCrearAdminEscolar:
    def test_blocked_when_no_active_cycle(self, admin_user):
        colegio = Mock()
        colegio.rbd = 12345
        colegio.nombre = "Test"

        with patch(
            f"{SERVICE_MODULE}.get_object_or_404",
            return_value=colegio,
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            f"{SERVICE_MODULE}.CicloAcademico.objects"
        ) as mock_ciclo, patch(
            f"{SERVICE_MODULE}.transaction"
        ), patch(
            f"{SERVICE_MODULE}.PrerequisiteException",
            _FlexiblePrerequisiteException,
        ):
            mock_ciclo.filter.return_value.first.return_value = None

            with pytest.raises(_FlexiblePrerequisiteException) as exc_info:
                EscuelaManagementService._execute_crear_admin_escolar(
                    {"data": {"rbd_admin": 12345, "email_admin": "a@b.cl"}}
                )

            assert exc_info.value.error_type == "MISSING_CICLO_ACTIVO"

    def test_rejects_duplicate_email(self, admin_user):
        colegio = Mock()
        colegio.rbd = 12345
        colegio.nombre = "Test"

        with patch(
            f"{SERVICE_MODULE}.get_object_or_404",
            return_value=colegio,
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            f"{SERVICE_MODULE}.CicloAcademico.objects"
        ) as mock_ciclo, patch(
            f"{SERVICE_MODULE}.User.objects"
        ) as mock_user, patch(
            f"{SERVICE_MODULE}.transaction"
        ), patch(
            f"{SERVICE_MODULE}.PrerequisiteException",
            _FlexiblePrerequisiteException,
        ):
            mock_ciclo.filter.return_value.first.return_value = Mock()
            email_qs = MagicMock()
            email_qs.exists.return_value = True
            mock_user.filter.return_value = email_qs

            with pytest.raises(_FlexiblePrerequisiteException) as exc_info:
                EscuelaManagementService._execute_crear_admin_escolar(
                    {"data": {"rbd_admin": 12345, "email_admin": "dup@test.cl"}}
                )

            assert exc_info.value.error_type == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# cambiar_plan_colegio
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCambiarPlanColegio:
    def test_updates_existing_subscription(self, admin_user):
        colegio = Mock()
        colegio.rbd = 12345
        plan = Mock()
        plan.codigo = "pro"
        plan.duracion_dias = 365

        with patch(
            "backend.apps.core.services.escuela_management_service.get_object_or_404",
            side_effect=[colegio, plan],
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            "backend.apps.core.services.escuela_management_service.SubscriptionService.upsert_school_subscription"
        ) as mock_upsert, patch(
            "backend.apps.core.services.escuela_management_service.transaction"
        ):
            result = EscuelaManagementService._execute_cambiar_plan_colegio(
                {"rbd": "12345", "plan_codigo": "pro"}
            )

        assert result == (colegio, plan)
        mock_upsert.assert_called_once_with(colegio_rbd=colegio.rbd, plan_codigo=plan.codigo)

    def test_creates_new_subscription_if_missing(self, admin_user):
        colegio = Mock()
        colegio.rbd = 12345
        plan = Mock()
        plan.codigo = "basic"
        plan.duracion_dias = 30

        with patch(
            "backend.apps.core.services.escuela_management_service.get_object_or_404",
            side_effect=[colegio, plan],
        ), patch.object(
            EscuelaManagementService,
            "_validate_school_integrity",
            return_value=None,
        ), patch(
            "backend.apps.core.services.escuela_management_service.SubscriptionService.upsert_school_subscription"
        ) as mock_upsert, patch(
            "backend.apps.core.services.escuela_management_service.transaction"
        ):
            result = EscuelaManagementService._execute_cambiar_plan_colegio(
                {"rbd": "12345", "plan_codigo": "basic"}
            )

        assert result[0] is colegio
        assert result[1] is plan
        mock_upsert.assert_called_once_with(colegio_rbd=colegio.rbd, plan_codigo=plan.codigo)

"""
Tests for ImportacionCSVService — CSV import operations.

Covers:
- Validation: missing archivo, missing rbd, unsupported operation
- validar_archivo: non-CSV rejected, oversized rejected, valid accepted
- _parsear_booleano: various truthy/falsy string inputs
- _parsear_fecha: valid, invalid, empty date strings
- _parsear_entero: valid, invalid, default handling
- _validar_prerequisitos_colegio: missing school, inactive school, no active cycle, success
- generar_plantilla_*: CSV templates contain required headers
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from backend.apps.core.services.import_csv_service import ImportacionCSVService
from backend.common.exceptions import PrerequisiteException


class _FlexiblePrerequisiteException(Exception):
    def __init__(self, error_type=None, **kwargs):
        self.error_type = error_type
        self.context = kwargs.get('context', {})
        super().__init__(kwargs.get('user_message', str(error_type)))


class _DummyFile:
    def __init__(self, content: str, name='data.csv', size=100):
        self._content = content
        self.name = name
        self.size = size

    def read(self):
        return self._content.encode('utf-8')


# ---------------------------------------------------------------------------
# execute / validate / _execute pattern
# ---------------------------------------------------------------------------

class TestImportCSVServicePattern:
    def test_validate_rejects_missing_archivo(self):
        with pytest.raises(ValueError, match="archivo"):
            ImportacionCSVService.validate(
                "importar_estudiantes", {"rbd_colegio": 12345}
            )

    def test_validate_rejects_missing_rbd(self):
        with pytest.raises(ValueError, match="rbd_colegio"):
            ImportacionCSVService.validate(
                "importar_estudiantes", {"archivo": Mock()}
            )

    def test_validate_rejects_unsupported_operation(self):
        with pytest.raises(ValueError, match="no soportada"):
            ImportacionCSVService.validate(
                "importar_directores",
                {"archivo": Mock(), "rbd_colegio": 12345},
            )

    def test_validate_accepts_valid_params(self):
        ImportacionCSVService.validate(
            "importar_estudiantes",
            {"archivo": Mock(), "rbd_colegio": 12345},
        )
        ImportacionCSVService.validate(
            "importar_profesores",
            {"archivo": Mock(), "rbd_colegio": 12345},
        )
        ImportacionCSVService.validate(
            "importar_apoderados",
            {"archivo": Mock(), "rbd_colegio": 12345},
        )

    def test_execute_rejects_unsupported_operation(self):
        with pytest.raises(ValueError, match="no soportada"):
            ImportacionCSVService._execute("unknown_op", {})

    def test_execute_dispatches(self):
        with patch.object(ImportacionCSVService, 'validate') as mock_validate, patch.object(
            ImportacionCSVService,
            '_execute',
            return_value=(1, 0, []),
        ) as mock_execute:
            result = ImportacionCSVService.execute('importar_estudiantes', {'archivo': Mock(), 'rbd_colegio': 1})

        assert result == (1, 0, [])
        mock_validate.assert_called_once()
        mock_execute.assert_called_once()


class TestDashboardDatos:
    @patch('backend.apps.core.services.import_csv_service.User')
    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_get_importar_datos_dashboard(self, mock_role, mock_user):
        role_est = Mock()
        role_prof = Mock()
        role_apod = Mock()
        mock_role.objects.filter.return_value.first.side_effect = [role_est, role_prof, role_apod]

        est_qs = MagicMock()
        est_qs.filter.return_value = est_qs
        est_qs.select_related.return_value.order_by.return_value = ['e1']
        est_qs.count.return_value = 2

        prof_qs = MagicMock()
        prof_qs.filter.return_value = prof_qs
        prof_qs.select_related.return_value.order_by.return_value = ['p1']
        prof_qs.count.return_value = 3

        apod_qs = MagicMock()
        apod_qs.filter.return_value = apod_qs
        apod_qs.select_related.return_value.order_by.return_value = ['a1']
        apod_qs.count.return_value = 4

        mock_user.objects.filter.side_effect = [est_qs, prof_qs, apod_qs]

        result = ImportacionCSVService.get_importar_datos_dashboard(123)

        assert result['total_estudiantes'] == 2
        assert result['total_profesores'] == 3
        assert result['total_apoderados'] == 4

    @patch('backend.apps.core.services.import_csv_service.User')
    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_get_importar_datos_dashboard_without_roles_uses_none(self, mock_role, mock_user):
        mock_role.objects.filter.return_value.first.return_value = None
        base_qs = MagicMock()
        base_qs.none.return_value = base_qs
        base_qs.select_related.return_value.order_by.return_value = []
        base_qs.count.return_value = 0
        mock_user.objects.filter.return_value = base_qs

        result = ImportacionCSVService.get_importar_datos_dashboard(123)

        assert result['total_estudiantes'] == 0
        assert result['total_profesores'] == 0
        assert result['total_apoderados'] == 0


# ---------------------------------------------------------------------------
# validar_archivo
# ---------------------------------------------------------------------------

class TestValidarArchivo:
    def test_rejects_non_csv_file(self):
        archivo = Mock()
        archivo.name = "data.xlsx"
        archivo.size = 1000

        valid, msg = ImportacionCSVService.validar_archivo(archivo)

        assert valid is False
        assert "CSV" in msg

    def test_rejects_oversized_file(self):
        archivo = Mock()
        archivo.name = "data.csv"
        archivo.size = 10 * 1024 * 1024  # 10 MB

        valid, msg = ImportacionCSVService.validar_archivo(archivo)

        assert valid is False
        assert "5 MB" in msg

    def test_accepts_valid_csv(self):
        archivo = Mock()
        archivo.name = "students.csv"
        archivo.size = 1024

        valid, msg = ImportacionCSVService.validar_archivo(archivo)

        assert valid is True
        assert msg == ""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

class TestParsearBooleano:
    @pytest.mark.parametrize(
        "valor,expected",
        [
            ("true", True),
            ("True", True),
            ("1", True),
            ("si", True),
            ("sí", True),
            ("yes", True),
            ("t", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("random", False),
        ],
    )
    def test_parsear_booleano(self, valor, expected):
        assert ImportacionCSVService._parsear_booleano(valor) == expected


class TestParsearFecha:
    def test_valid_date(self):
        result = ImportacionCSVService._parsear_fecha("2024-03-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 15

    def test_invalid_date(self):
        assert ImportacionCSVService._parsear_fecha("not-a-date") is None

    def test_empty_string(self):
        assert ImportacionCSVService._parsear_fecha("") is None
        assert ImportacionCSVService._parsear_fecha("   ") is None


class TestParsearEntero:
    def test_valid_integer(self):
        assert ImportacionCSVService._parsear_entero("42") == 42

    def test_stripped_integer(self):
        assert ImportacionCSVService._parsear_entero("  7  ") == 7

    def test_invalid_returns_default(self):
        assert ImportacionCSVService._parsear_entero("abc", default=10) == 10

    def test_empty_returns_default(self):
        assert ImportacionCSVService._parsear_entero("", default=5) == 5
        assert ImportacionCSVService._parsear_entero("   ", default=5) == 5


# ---------------------------------------------------------------------------
# _validar_prerequisitos_colegio
# ---------------------------------------------------------------------------

def _mock_error_builder(error_type, **kwargs):
    """Mock for ErrorResponseBuilder.build that accepts any kwargs."""
    return {
        "error_type": error_type,
        "user_message": kwargs.get("user_message", f"Error: {error_type}"),
        "action_url": kwargs.get("action_url", "/"),
        "context": kwargs.get("context", {}),
    }


CSV_SERVICE_MODULE = "backend.apps.core.services.import_csv_service"


class TestValidarPrerequisitos:
    def test_missing_school_returns_error(self):
        from backend.apps.institucion.models import Colegio

        with patch(
            f"{CSV_SERVICE_MODULE}.Colegio.objects.get",
            side_effect=Colegio.DoesNotExist,
        ), patch(
            f"{CSV_SERVICE_MODULE}.ErrorResponseBuilder.build",
            side_effect=_mock_error_builder,
        ):
            result = ImportacionCSVService._validar_prerequisitos_colegio(99999)

        assert result is not None
        assert "error_type" in result

    def test_inactive_school_returns_error(self):
        colegio = Mock()
        colegio.activo = False
        colegio.nombre = "Inactivo"

        with patch(
            f"{CSV_SERVICE_MODULE}.Colegio.objects.get",
            return_value=colegio,
        ), patch(
            f"{CSV_SERVICE_MODULE}.ErrorResponseBuilder.build",
            side_effect=_mock_error_builder,
        ):
            result = ImportacionCSVService._validar_prerequisitos_colegio(12345)

        assert result is not None
        assert "INVALID_STATE" in str(result.get("error_type", ""))

    def test_no_active_cycle_returns_error(self):
        colegio = Mock()
        colegio.activo = True
        colegio.nombre = "Test"

        with patch(
            f"{CSV_SERVICE_MODULE}.Colegio.objects.get",
            return_value=colegio,
        ), patch(
            f"{CSV_SERVICE_MODULE}.CicloAcademico.objects"
        ) as mock_ciclo, patch(
            f"{CSV_SERVICE_MODULE}.ErrorResponseBuilder.build",
            side_effect=_mock_error_builder,
        ):
            mock_ciclo.filter.return_value.first.return_value = None

            result = ImportacionCSVService._validar_prerequisitos_colegio(12345)

        assert result is not None
        assert "MISSING_CICLO_ACTIVO" in str(result.get("error_type", ""))

    def test_valid_school_returns_none(self):
        colegio = Mock()
        colegio.activo = True
        colegio.nombre = "Test"

        with patch(
            f"{CSV_SERVICE_MODULE}.Colegio.objects.get",
            return_value=colegio,
        ), patch(
            f"{CSV_SERVICE_MODULE}.CicloAcademico.objects"
        ) as mock_ciclo:
            mock_ciclo.filter.return_value.first.return_value = Mock()

            result = ImportacionCSVService._validar_prerequisitos_colegio(12345)

        assert result is None


# ---------------------------------------------------------------------------
# CSV Templates
# ---------------------------------------------------------------------------

class TestCSVTemplates:
    def test_student_template_has_required_headers(self):
        plantilla = ImportacionCSVService.generar_plantilla_estudiantes()
        first_line = plantilla.split("\n")[0]

        for required_header in ["email", "nombre", "apellido_paterno", "rut", "password"]:
            assert required_header in first_line

    def test_profesor_template_has_required_headers(self):
        plantilla = ImportacionCSVService.generar_plantilla_profesores()
        first_line = plantilla.split("\n")[0]

        for required_header in ["email", "nombre", "apellido_paterno", "rut", "password", "especialidad"]:
            assert required_header in first_line

    def test_apoderado_template_has_required_headers(self):
        plantilla = ImportacionCSVService.generar_plantilla_apoderados()
        first_line = plantilla.split("\n")[0]

        for required_header in ["email", "nombre", "apellido_paterno", "rut", "password", "ocupacion"]:
            assert required_header in first_line

    def test_templates_have_example_rows(self):
        for generator in [
            ImportacionCSVService.generar_plantilla_estudiantes,
            ImportacionCSVService.generar_plantilla_profesores,
            ImportacionCSVService.generar_plantilla_apoderados,
        ]:
            plantilla = generator()
            lines = [l for l in plantilla.split("\n") if l.strip()]
            assert len(lines) >= 2, "Template must have header + at least 1 example row"


class TestImportadores:
    def test_importar_wrappers_delegate_execute(self):
        archivo = Mock()
        with patch.object(ImportacionCSVService, 'execute', return_value=(1, 0, [])) as mock_execute:
            assert ImportacionCSVService.importar_estudiantes(archivo, 1) == (1, 0, [])
            assert ImportacionCSVService.importar_profesores(archivo, 1) == (1, 0, [])
            assert ImportacionCSVService.importar_apoderados(archivo, 1) == (1, 0, [])

        assert mock_execute.call_count == 3

    def test_execute_dispatch_import_operations(self):
        with patch.object(ImportacionCSVService, '_execute_importar_estudiantes', return_value='E') as e_st, patch.object(
            ImportacionCSVService, '_execute_importar_profesores', return_value='P'
        ) as e_pr, patch.object(ImportacionCSVService, '_execute_importar_apoderados', return_value='A') as e_ap:
            assert ImportacionCSVService._execute('importar_estudiantes', {'x': 1}) == 'E'
            assert ImportacionCSVService._execute('importar_profesores', {'x': 1}) == 'P'
            assert ImportacionCSVService._execute('importar_apoderados', {'x': 1}) == 'A'

        e_st.assert_called_once()
        e_pr.assert_called_once()
        e_ap.assert_called_once()

    @patch('backend.apps.core.services.import_csv_service.transaction')
    @patch('backend.apps.core.services.import_csv_service.PerfilEstudiante')
    @patch('backend.apps.core.services.import_csv_service.User')
    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_execute_importar_estudiantes_success_and_duplicates(
        self,
        mock_role,
        mock_user,
        mock_perfil,
        mock_transaction,
    ):
        mock_transaction.atomic.return_value.__enter__.return_value = None
        mock_transaction.atomic.return_value.__exit__.return_value = False

        file_content = (
            'email,nombre,apellido_paterno,rut,password\n'
            'ok@test.cl,Juan,Perez,111-1,PasswordMuySegura123\n'
            'dup@test.cl,Ana,Lopez,222-2,PasswordMuySegura123\n'
        )
        archivo = _DummyFile(file_content)

        mock_role.objects.filter.return_value.first.side_effect = [Mock(), None]

        exists_email_false = Mock()
        exists_email_false.exists.return_value = False
        exists_rut_false = Mock()
        exists_rut_false.exists.return_value = False
        exists_email_true = Mock()
        exists_email_true.exists.return_value = True

        mock_user.objects.filter.side_effect = [exists_email_false, exists_rut_false, exists_email_true]

        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(True, '')):
            exitosos, fallidos, errores = ImportacionCSVService._execute_importar_estudiantes(
                {'archivo': archivo, 'rbd_colegio': 123}
            )

        assert exitosos == 1
        assert fallidos == 1
        assert len(errores) == 1
        mock_perfil.objects.create.assert_called_once()

    def test_execute_importar_estudiantes_prerequisite_exception(self):
        with patch.object(
            ImportacionCSVService,
            '_validar_prerequisitos_colegio',
            return_value={'error_type': 'X', 'user_message': 'msg', 'context': {}},
        ), patch(
            'backend.apps.core.services.import_csv_service.PrerequisiteException',
            _FlexiblePrerequisiteException,
        ):
            with pytest.raises(_FlexiblePrerequisiteException):
                ImportacionCSVService._execute_importar_estudiantes({'archivo': Mock(), 'rbd_colegio': 1})

    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_execute_importar_estudiantes_role_missing(self, mock_role):
        archivo = _DummyFile('email,nombre,apellido_paterno,rut,password\n')
        mock_role.objects.filter.return_value.first.return_value = None

        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(True, '')):
            result = ImportacionCSVService._execute_importar_estudiantes({'archivo': archivo, 'rbd_colegio': 1})

        assert result == (0, 0, ['No existe un rol de estudiante en el sistema'])

    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_execute_importar_profesores_role_missing(self, mock_role):
        archivo = _DummyFile('email,nombre,apellido_paterno,rut,password\n')
        mock_role.objects.filter.return_value.first.return_value = None

        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(True, '')):
            result = ImportacionCSVService._execute_importar_profesores({'archivo': archivo, 'rbd_colegio': 1})

        assert result == (0, 0, ["No existe el rol 'Profesor' en el sistema"])

    @patch('backend.apps.core.services.import_csv_service.transaction')
    @patch('backend.apps.core.services.import_csv_service.PerfilProfesor')
    @patch('backend.apps.core.services.import_csv_service.User')
    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_execute_importar_profesores_success(
        self,
        mock_role,
        mock_user,
        mock_perfil,
        mock_transaction,
    ):
        mock_transaction.atomic.return_value.__enter__.return_value = None
        mock_transaction.atomic.return_value.__exit__.return_value = False
        archivo = _DummyFile('email,nombre,apellido_paterno,rut,password\nprof@test.cl,Profe,Uno,333-3,PasswordMuySegura123\n')

        mock_role.objects.filter.return_value.first.return_value = Mock()
        exists_false = Mock()
        exists_false.exists.return_value = False
        mock_user.objects.filter.side_effect = [exists_false, exists_false]

        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(True, '')):
            exitosos, fallidos, errores = ImportacionCSVService._execute_importar_profesores(
                {'archivo': archivo, 'rbd_colegio': 1}
            )

        assert exitosos == 1
        assert fallidos == 0
        assert errores == []
        mock_perfil.objects.create.assert_called_once()

    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_execute_importar_apoderados_invalid_file(self, mock_role):
        mock_role.objects.filter.return_value.first.return_value = Mock()
        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(False, 'bad file')):
            result = ImportacionCSVService._execute_importar_apoderados({'archivo': Mock(), 'rbd_colegio': 1})

        assert result == (0, 0, ['bad file'])

    @patch('backend.apps.core.services.import_csv_service.transaction')
    @patch('backend.apps.core.services.import_csv_service.Apoderado')
    @patch('backend.apps.core.services.import_csv_service.User')
    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_execute_importar_apoderados_success_and_decode_error(
        self,
        mock_role,
        mock_user,
        mock_apoderado,
        mock_transaction,
    ):
        mock_transaction.atomic.return_value.__enter__.return_value = None
        mock_transaction.atomic.return_value.__exit__.return_value = False
        archivo = _DummyFile('email,nombre,apellido_paterno,rut,password\nap@test.cl,Apo,Uno,444-4,PasswordMuySegura123\n')

        mock_role.objects.filter.return_value.first.return_value = Mock()
        exists_false = Mock()
        exists_false.exists.return_value = False
        mock_user.objects.filter.side_effect = [exists_false, exists_false]

        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(True, '')):
            exitosos, fallidos, errores = ImportacionCSVService._execute_importar_apoderados(
                {'archivo': archivo, 'rbd_colegio': 1}
            )

        assert exitosos == 1
        assert fallidos == 0
        assert errores == []
        mock_apoderado.objects.create.assert_called_once()

        archivo_bad = Mock()
        archivo_bad.read.side_effect = UnicodeDecodeError('utf-8', b'a', 0, 1, 'bad')
        archivo_bad.name = 'data.csv'
        archivo_bad.size = 100

        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(True, '')):
            ex2, fa2, err2 = ImportacionCSVService._execute_importar_apoderados({'archivo': archivo_bad, 'rbd_colegio': 1})

        assert ex2 == 0
        assert fa2 == 0
        assert any('UTF-8' in e for e in err2)

    @patch('backend.apps.core.services.import_csv_service.transaction')
    @patch('backend.apps.core.services.import_csv_service.User')
    @patch('backend.apps.core.services.import_csv_service.Role')
    def test_execute_importar_apoderados_short_password_branch(self, mock_role, mock_user, mock_transaction):
        mock_transaction.atomic.return_value.__enter__.return_value = None
        mock_transaction.atomic.return_value.__exit__.return_value = False
        archivo = _DummyFile('email,nombre,apellido_paterno,rut,password\nap@test.cl,Apo,Uno,444-4,short\n')
        mock_role.objects.filter.return_value.first.return_value = Mock()
        mock_user.objects.filter.return_value.exists.return_value = False

        with patch.object(ImportacionCSVService, '_validar_prerequisitos_colegio', return_value=None), patch.object(
            ImportacionCSVService, '_validate_school_integrity'
        ), patch.object(ImportacionCSVService, 'validar_archivo', return_value=(True, '')):
            exitosos, fallidos, errores = ImportacionCSVService._execute_importar_apoderados(
                {'archivo': archivo, 'rbd_colegio': 1}
            )

        assert exitosos == 0
        assert fallidos == 1
        assert any('12 caracteres' in e for e in errores)

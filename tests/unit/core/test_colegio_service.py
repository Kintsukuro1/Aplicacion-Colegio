from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.colegio_service import ColegioService


pytestmark = pytest.mark.django_db

MODULE = 'backend.apps.core.services.colegio_service'


def _valid_data(**overrides):
    base = {
        'rut_establecimiento': '76.123.456-7',
        'nombre': 'Colegio Test',
        'comuna_id': 1,
        'tipo_establecimiento_id': 2,
        'dependencia_id': 3,
        'correo': 'colegio@test.cl',
        'direccion': 'Calle 123',
        'telefono': '123456789',
        'web': 'https://test.cl',
        'capacidad_maxima': 500,
        'fecha_fundacion': '2000-01-01',
    }
    base.update(overrides)
    return base


class TestColegioService:
    @pytest.mark.parametrize(
        'field',
        ['rut_establecimiento', 'nombre', 'comuna_id', 'tipo_establecimiento_id', 'dependencia_id'],
    )
    def test_validations_require_fields(self, field):
        data = _valid_data(**{field: None})
        with pytest.raises(ValueError, match=f'Campo requerido: {field}'):
            ColegioService.validations(data=data)

    def test_validations_reject_duplicate_email_without_rbd(self):
        query = Mock()
        query.exists.return_value = True
        with patch(f'{MODULE}.Colegio.objects.filter', return_value=query):
            with pytest.raises(ValueError, match='correo del colegio ya está en uso'):
                ColegioService.validations(data=_valid_data())

    def test_validations_reject_duplicate_email_with_rbd(self):
        query = Mock()
        excluded = Mock()
        excluded.exists.return_value = True
        query.exclude.return_value = excluded
        with patch(f'{MODULE}.Colegio.objects.filter', return_value=query):
            with pytest.raises(ValueError, match='correo del colegio ya está en uso'):
                ColegioService.validations(data=_valid_data(), rbd=123)

        query.exclude.assert_called_once_with(rbd=123)

    def test_validations_allow_empty_email(self):
        with patch(f'{MODULE}.Colegio.objects.filter') as mock_filter:
            ColegioService.validations(data=_valid_data(correo=''))
        mock_filter.assert_not_called()

    def test_create_delegates_to_escuela_management_service(self):
        user = Mock()
        colegio = Mock()
        data = _valid_data()
        with patch.object(ColegioService, 'validations') as mock_valid, patch(
            f'{MODULE}.EscuelaManagementService.crear_colegio',
            return_value=colegio,
        ) as mock_create:
            result = ColegioService.create(user=user, data=data)

        assert result is colegio
        mock_valid.assert_called_once_with(data=data)
        mock_create.assert_called_once_with(user, data)

    def test_update_rejects_duplicate_email_in_second_check(self):
        user = Mock()
        data = _valid_data(correo='nuevo@test.cl')
        colegio = Mock()
        correo_qs = Mock()
        correo_qs.exclude.return_value.exists.return_value = True

        with patch.object(ColegioService, 'validations'), patch(
            f'{MODULE}.IntegrityService.validate_colegio_update'
        ), patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.Colegio.objects.filter',
            return_value=correo_qs,
        ):
            with pytest.raises(ValueError, match='correo del colegio ya está en uso'):
                ColegioService.update(user=user, rbd=123, data=data)

    def test_update_success_sets_fields_and_saves(self):
        user = Mock()
        colegio = Mock()
        data = _valid_data(correo='nuevo@test.cl')
        correo_qs = Mock()
        correo_qs.exclude.return_value.exists.return_value = False

        with patch.object(ColegioService, 'validations') as mock_valid, patch(
            f'{MODULE}.IntegrityService.validate_colegio_update'
        ) as mock_integrity, patch(
            f'{MODULE}.Colegio.objects.get',
            return_value=colegio,
        ), patch(
            f'{MODULE}.Colegio.objects.filter',
            return_value=correo_qs,
        ):
            result = ColegioService.update(user=user, rbd=123, data=data)

        assert result is colegio
        mock_valid.assert_called_once_with(data=data, rbd=123)
        mock_integrity.assert_called_once_with(123)
        assert colegio.nombre == data['nombre']
        assert colegio.comuna_id == data['comuna_id']
        assert colegio.dependencia_id == data['dependencia_id']
        colegio.save.assert_called_once()

    def test_get_delegates_to_model(self):
        colegio = Mock()
        with patch(f'{MODULE}.Colegio.objects.get', return_value=colegio) as mock_get:
            result = ColegioService.get(rbd=123)
        assert result is colegio
        mock_get.assert_called_once_with(rbd=123)

    def test_update_basic_info_updates_and_saves(self):
        colegio = Mock()
        data = _valid_data(correo='basic@test.cl')
        with patch(f'{MODULE}.IntegrityService.validate_colegio_update') as mock_integrity, patch(
            f'{MODULE}.Colegio.objects.get',
            return_value=colegio,
        ):
            result = ColegioService.update_basic_info(user=Mock(), rbd=123, data=data)

        assert result is colegio
        mock_integrity.assert_called_once_with(123)
        assert colegio.correo == 'basic@test.cl'
        colegio.save.assert_called_once()

    def test_delete_rejects_when_active_users_exist(self):
        users_qs = Mock()
        users_qs.exists.return_value = True
        with patch(f'{MODULE}.IntegrityService.validate_colegio_deletion'), patch(
            f'{MODULE}.User.objects.filter',
            return_value=users_qs,
        ):
            with pytest.raises(ValueError, match='usuarios activos asociados'):
                ColegioService.delete(user=Mock(), rbd=123)

    def test_delete_success_delegates_to_escuela_management(self):
        user = Mock()
        users_qs = Mock()
        users_qs.exists.return_value = False
        with patch(f'{MODULE}.IntegrityService.validate_colegio_deletion') as mock_integrity, patch(
            f'{MODULE}.User.objects.filter',
            return_value=users_qs,
        ), patch(
            f'{MODULE}.EscuelaManagementService.eliminar_colegio',
            return_value=True,
        ) as mock_delete:
            result = ColegioService.delete(user=user, rbd=123)

        assert result is True
        mock_integrity.assert_called_once_with(123)
        mock_delete.assert_called_once_with(user, '123')

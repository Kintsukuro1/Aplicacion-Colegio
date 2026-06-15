from datetime import date
from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.ciclo_academico_service import CicloAcademicoService


pytestmark = pytest.mark.django_db

MODULE = 'backend.apps.core.services.ciclo_academico_service'


class TestCicloAcademicoService:
    def test_validations_require_nombre(self):
        with pytest.raises(ValueError, match='nombre'):
            CicloAcademicoService.validations(
                school_rbd=1,
                nombre='',
                fecha_inicio=date(2026, 3, 1),
                fecha_fin=date(2026, 12, 20),
            )

    def test_validations_require_dates(self):
        with pytest.raises(ValueError, match='fecha_inicio y fecha_fin'):
            CicloAcademicoService.validations(
                school_rbd=1,
                nombre='2026',
                fecha_inicio=None,
                fecha_fin=date(2026, 12, 20),
            )

    def test_validations_reject_invalid_date_range(self):
        with pytest.raises(ValueError, match='inicio no puede ser mayor'):
            CicloAcademicoService.validations(
                school_rbd=1,
                nombre='2026',
                fecha_inicio=date(2026, 12, 21),
                fecha_fin=date(2026, 12, 20),
            )

    def test_validations_reject_duplicate_name(self):
        colegio = Mock()
        ciclos_qs = Mock()
        ciclos_qs.exists.return_value = True

        with patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.CicloAcademico.objects.filter', return_value=ciclos_qs
        ):
            with pytest.raises(ValueError, match='Ya existe un ciclo académico'):
                CicloAcademicoService.validations(
                    school_rbd=1,
                    nombre='2026',
                    fecha_inicio=date(2026, 3, 1),
                    fecha_fin=date(2026, 12, 20),
                )

    def test_validations_exclude_current_cycle_when_updating(self):
        colegio = Mock()
        ciclos_qs = Mock()
        excluido_qs = Mock()
        excluido_qs.exists.return_value = False
        ciclos_qs.exclude.return_value = excluido_qs

        with patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.CicloAcademico.objects.filter', return_value=ciclos_qs
        ):
            CicloAcademicoService.validations(
                school_rbd=1,
                nombre='2026',
                fecha_inicio=date(2026, 3, 1),
                fecha_fin=date(2026, 12, 20),
                ciclo_id=9,
            )

        ciclos_qs.exclude.assert_called_once_with(id=9)

    def test_create_calls_integrity_validations_and_admin_service(self):
        user = Mock()
        ciclo = Mock()
        with patch.object(CicloAcademicoService, 'validations') as mock_validations, patch(
            f'{MODULE}.IntegrityService.validate_ciclo_creation'
        ) as mock_integrity, patch(
            f'{MODULE}.AdminSchoolService.create_academic_cycle',
            return_value=ciclo,
        ) as mock_create:
            result = CicloAcademicoService.create(
                user=user,
                school_rbd=1,
                nombre='2026',
                fecha_inicio=date(2026, 3, 1),
                fecha_fin=date(2026, 12, 20),
                descripcion='desc',
                activate=True,
            )

        assert result is ciclo
        mock_integrity.assert_called_once_with(1)
        mock_validations.assert_called_once()
        mock_create.assert_called_once()

    def test_activate_delegates_to_admin_service(self):
        user = Mock()
        with patch(
            f'{MODULE}.AdminSchoolService.activate_academic_cycle',
            return_value='ok',
        ) as mock_activate:
            result = CicloAcademicoService.activate(user=user, school_rbd=1, ciclo_id=3)

        assert result == 'ok'
        mock_activate.assert_called_once_with(user=user, school_rbd=1, ciclo_id=3)

    def test_update_rejects_duplicate_name_in_same_school(self):
        user = Mock()
        colegio = Mock()
        ciclo = Mock(id=10)
        dup_qs = Mock()
        dup_qs.exists.return_value = True

        with patch.object(CicloAcademicoService, 'validations'), patch(
            f'{MODULE}.IntegrityService.validate_ciclo_update'
        ), patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.CicloAcademico.objects.get',
            return_value=ciclo,
        ), patch(
            f'{MODULE}.CicloAcademico.objects.filter',
            return_value=dup_qs,
        ):
            with pytest.raises(ValueError, match='Ya existe un ciclo académico'):
                CicloAcademicoService.update(
                    user=user,
                    school_rbd=1,
                    ciclo_id=10,
                    nombre='2026',
                    fecha_inicio=date(2026, 3, 1),
                    fecha_fin=date(2026, 12, 20),
                    descripcion='d',
                )

    def test_update_success(self):
        user = Mock()
        colegio = Mock()
        ciclo = Mock(id=10)
        filtro_qs = Mock()
        excluido_qs = Mock()
        excluido_qs.exists.return_value = False
        filtro_qs.exclude.return_value = excluido_qs

        with patch.object(CicloAcademicoService, 'validations'), patch(
            f'{MODULE}.IntegrityService.validate_ciclo_update'
        ), patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.CicloAcademico.objects.get',
            return_value=ciclo,
        ), patch(
            f'{MODULE}.CicloAcademico.objects.filter',
            return_value=filtro_qs,
        ):
            result = CicloAcademicoService.update(
                user=user,
                school_rbd=1,
                ciclo_id=10,
                nombre='2026',
                fecha_inicio=date(2026, 3, 1),
                fecha_fin=date(2026, 12, 20),
                descripcion='desc',
            )

        assert result is ciclo
        assert ciclo.nombre == '2026'
        assert ciclo.descripcion == 'desc'
        assert ciclo.modificado_por is user
        ciclo.save.assert_called_once()

    def test_get_returns_cycle_for_school(self):
        colegio = Mock()
        ciclo = Mock()
        with patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.CicloAcademico.objects.get',
            return_value=ciclo,
        ) as mock_get:
            result = CicloAcademicoService.get(school_rbd=1, ciclo_id=7)

        assert result is ciclo
        mock_get.assert_called_once_with(id=7, colegio=colegio)

    def test_delete_rejects_active_cycle(self):
        colegio = Mock()
        ciclo = Mock(estado='ACTIVO')
        with patch(f'{MODULE}.IntegrityService.validate_ciclo_deletion'), patch(
            f'{MODULE}.Colegio.objects.get',
            return_value=colegio,
        ), patch(
            f'{MODULE}.CicloAcademico.objects.get',
            return_value=ciclo,
        ):
            with pytest.raises(ValueError, match='No se puede eliminar un ciclo activo'):
                CicloAcademicoService.delete(user=Mock(), school_rbd=1, ciclo_id=9)

    def test_delete_success(self):
        colegio = Mock()
        ciclo = Mock(estado='CERRADO')
        with patch(f'{MODULE}.IntegrityService.validate_ciclo_deletion'), patch(
            f'{MODULE}.Colegio.objects.get',
            return_value=colegio,
        ), patch(
            f'{MODULE}.CicloAcademico.objects.get',
            return_value=ciclo,
        ):
            result = CicloAcademicoService.delete(user=Mock(), school_rbd=1, ciclo_id=9)

        assert result is True
        ciclo.delete.assert_called_once()

    def test_close_delegates_to_admin_service(self):
        user = Mock()
        with patch(
            f'{MODULE}.AdminSchoolService.close_academic_cycle',
            return_value='closed',
        ) as mock_close:
            result = CicloAcademicoService.close(user=user, school_rbd=1, ciclo_id=8)

        assert result == 'closed'
        mock_close.assert_called_once_with(user=user, school_rbd=1, ciclo_id=8)

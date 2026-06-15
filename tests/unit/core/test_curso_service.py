from unittest.mock import Mock, patch

import pytest

from backend.apps.core.services.curso_service import CursoService


pytestmark = pytest.mark.django_db

MODULE = 'backend.apps.core.services.curso_service'


class TestCursoService:
    def test_validations_require_nombre(self):
        with pytest.raises(ValueError, match='nombre'):
            CursoService.validations(school_rbd=1, nombre='', nivel_id=2)

    def test_validations_reject_duplicate_active_course(self):
        colegio = Mock()
        nivel = Mock()
        cursos_qs = Mock()
        cursos_qs.exists.return_value = True

        with patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.NivelEducativo.objects.get',
            return_value=nivel,
        ), patch(
            f'{MODULE}.Curso.objects.filter',
            return_value=cursos_qs,
        ):
            with pytest.raises(ValueError, match='Ya existe un curso activo'):
                CursoService.validations(school_rbd=1, nombre='1A', nivel_id=3)

    def test_validations_success_and_exclude_current_course(self):
        colegio = Mock()
        nivel = Mock()
        cursos_qs = Mock()
        excluido_qs = Mock()
        excluido_qs.exists.return_value = False
        cursos_qs.exclude.return_value = excluido_qs

        with patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.NivelEducativo.objects.get',
            return_value=nivel,
        ), patch(
            f'{MODULE}.Curso.objects.filter',
            return_value=cursos_qs,
        ):
            result = CursoService.validations(
                school_rbd=1,
                nombre='1A',
                nivel_id=3,
                curso_id=99,
            )

        assert result == {'colegio': colegio, 'nivel': nivel}
        cursos_qs.exclude.assert_called_once_with(id_curso=99)

    def test_create_delegates_with_integrity(self):
        user = Mock()
        curso = Mock()
        with patch.object(CursoService, 'validations') as mock_valid, patch(
            f'{MODULE}.IntegrityService.validate_curso_creation'
        ) as mock_integrity, patch(
            f'{MODULE}.AdminSchoolService.create_course',
            return_value=curso,
        ) as mock_create:
            result = CursoService.create(user=user, school_rbd=1, nombre='1A', nivel_id=3)

        assert result is curso
        mock_integrity.assert_called_once_with(1)
        mock_valid.assert_called_once_with(school_rbd=1, nombre='1A', nivel_id=3)
        mock_create.assert_called_once_with(user=user, school_rbd=1, nombre='1A', nivel_id=3)

    def test_update_rejects_duplicate_name_in_current_cycle(self):
        user = Mock()
        colegio = Mock()
        curso = Mock(id_curso=10, ciclo_academico='C1')
        nivel = Mock()

        dup_qs = Mock()
        excluido_qs = Mock()
        excluido_qs.exists.return_value = True
        dup_qs.exclude.return_value = excluido_qs

        with patch.object(
            CursoService,
            'validations',
            return_value={'colegio': colegio, 'nivel': nivel},
        ), patch(f'{MODULE}.IntegrityService.validate_curso_update'), patch(
            f'{MODULE}.Curso.objects.get',
            return_value=curso,
        ), patch(
            f'{MODULE}.Curso.objects.filter',
            return_value=dup_qs,
        ):
            with pytest.raises(ValueError, match='Ya existe un curso con ese nombre'):
                CursoService.update(
                    user=user,
                    school_rbd=1,
                    curso_id=10,
                    nombre='1A',
                    nivel_id=3,
                )

    def test_update_success(self):
        user = Mock()
        colegio = Mock()
        curso = Mock(id_curso=10, ciclo_academico='C1')
        nivel = Mock()

        filtro_qs = Mock()
        excluido_qs = Mock()
        excluido_qs.exists.return_value = False
        filtro_qs.exclude.return_value = excluido_qs

        with patch.object(
            CursoService,
            'validations',
            return_value={'colegio': colegio, 'nivel': nivel},
        ), patch(f'{MODULE}.IntegrityService.validate_curso_update'), patch(
            f'{MODULE}.Curso.objects.get',
            return_value=curso,
        ), patch(
            f'{MODULE}.Curso.objects.filter',
            return_value=filtro_qs,
        ):
            result = CursoService.update(
                user=user,
                school_rbd=1,
                curso_id=10,
                nombre='1A',
                nivel_id=3,
            )

        assert result is curso
        assert curso.nombre == '1A'
        assert curso.nivel is nivel
        curso.save.assert_called_once_with(update_fields=['nombre', 'nivel'])

    def test_get_returns_course_scoped_by_school(self):
        colegio = Mock()
        curso = Mock()
        with patch(f'{MODULE}.Colegio.objects.get', return_value=colegio), patch(
            f'{MODULE}.Curso.objects.get',
            return_value=curso,
        ) as mock_get:
            result = CursoService.get(school_rbd=1, curso_id=22)

        assert result is curso
        mock_get.assert_called_once_with(id_curso=22, colegio=colegio)

    def test_delete_soft_deletes_course_and_classes(self):
        colegio = Mock()
        curso = Mock()
        clases_qs = Mock()

        with patch(f'{MODULE}.IntegrityService.validate_curso_deletion'), patch(
            f'{MODULE}.Colegio.objects.get',
            return_value=colegio,
        ), patch(
            f'{MODULE}.Curso.objects.get',
            return_value=curso,
        ), patch(
            f'{MODULE}.Clase.objects.filter',
            return_value=clases_qs,
        ), patch(f'{MODULE}.transaction.atomic'):
            result = CursoService.delete(user=Mock(), school_rbd=1, curso_id=3)

        assert result is curso
        assert curso.activo is False
        curso.save.assert_called_once_with(update_fields=['activo'])
        clases_qs.update.assert_called_once_with(activo=False)

    def test_assign_students_updates_missing_ciclo_actual_only(self):
        colegio = Mock()
        curso = Mock(ciclo_academico='CICLO-2026')

        usuarios_qs = Mock()
        usuarios_qs.values_list.return_value = [101, 202]

        perfil_sin_ciclo = Mock(ciclo_actual=None)
        perfil_con_ciclo = Mock(ciclo_actual='YA')

        with patch(
            f'{MODULE}.IntegrityService.validate_school_integrity_or_raise'
        ) as mock_integrity, patch(
            f'{MODULE}.Colegio.objects.get',
            return_value=colegio,
        ), patch(
            f'{MODULE}.Curso.objects.get',
            return_value=curso,
        ), patch(
            f'{MODULE}.User.objects.filter',
            return_value=usuarios_qs,
        ), patch(
            f'{MODULE}.PerfilEstudiante.objects.get_or_create',
            side_effect=[(perfil_sin_ciclo, True), (perfil_con_ciclo, False)],
        ) as mock_get_or_create, patch(f'{MODULE}.transaction.atomic'):
            result = CursoService.assign_students(
                user=Mock(),
                school_rbd=1,
                curso_id=8,
                estudiantes_ids=[101, 202],
            )

        assert result == 2
        mock_integrity.assert_called_once_with(
            school_id=1,
            action='ADMIN_ESCOLAR_ASSIGN_ESTUDIANTES_CURSO',
        )
        assert mock_get_or_create.call_count == 2
        assert perfil_sin_ciclo.ciclo_actual == 'CICLO-2026'
        perfil_sin_ciclo.save.assert_called_once_with(update_fields=['ciclo_actual'])
        perfil_con_ciclo.save.assert_not_called()

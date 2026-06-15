from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.core.exceptions import PermissionDenied

from backend.apps.academico.services.academic_view_service import AcademicViewService


pytestmark = pytest.mark.django_db


def _user(role='Alumno'):
    user = Mock()
    user.id = 10
    user.email = 'user@test.cl'
    user.is_active = True
    user.rbd_colegio = 123
    user.colegio = Mock()
    user.role = Mock(nombre=role)
    return user


class TestAcademicViewServiceBasics:
    def test_validate_and_dispatch(self):
        user = _user()
        with patch.object(AcademicViewService, 'validate') as mock_validate, patch.object(
            AcademicViewService,
            '_execute',
            return_value={'ok': True},
        ) as mock_execute:
            result = AcademicViewService.execute('get_student_profile', {'user': user})

        assert result == {'ok': True}
        mock_validate.assert_called_once()
        mock_execute.assert_called_once()

    def test_validate_rejects_invalid_inputs(self):
        with pytest.raises(ValueError):
            AcademicViewService.validate('get_student_profile', {})

        with pytest.raises(ValueError):
            AcademicViewService.validate('x', {'user': _user()})

    def test_execute_unsupported_operation(self):
        with pytest.raises(ValueError):
            AcademicViewService._execute('x', {'user': _user()})

    def test_role_validators(self):
        def _student_caps(_u, capability, school_id=None):
            return capability in {'CLASS_VIEW', 'GRADE_VIEW'}

        def _teacher_caps(_u, capability, school_id=None):
            return capability == 'TEACHER_VIEW'

        with patch('backend.apps.academico.services.academic_view_service.PolicyService.has_capability', side_effect=_student_caps):
            assert AcademicViewService.validate_student_role(_user('Alumno')) is True

        with patch('backend.apps.academico.services.academic_view_service.PolicyService.has_capability', return_value=False):
            assert AcademicViewService.validate_student_role(_user('Profesor')) is False

        with patch('backend.apps.academico.services.academic_view_service.PolicyService.has_capability', side_effect=_teacher_caps):
            assert AcademicViewService.validate_teacher_role(_user('Profesor')) is True


class TestAcademicViewValidation:
    @patch('backend.apps.academico.services.academic_view_service.ErrorResponseBuilder.build', return_value={'error': 'bad'})
    def test_validate_student_profile_inactive_user(self, _mock_build):
        user = _user()
        user.is_active = False

        result = AcademicViewService._validate_student_profile(user)

        assert result == {'error': 'bad'}

    @patch('backend.apps.academico.services.academic_view_service.ErrorResponseBuilder.build', return_value={'error': 'missing'})
    def test_validate_student_profile_missing_perfil(self, _mock_build):
        user = _user()
        with patch('backend.apps.accounts.models.PerfilEstudiante.objects.get', side_effect=Exception('missing')), patch(
            'backend.apps.accounts.models.PerfilEstudiante.DoesNotExist',
            Exception,
        ):
            result = AcademicViewService._validate_student_profile(user)

        assert result == {'error': 'missing'}

    @patch('backend.apps.academico.services.academic_view_service.ErrorResponseBuilder.build', return_value={'error': 'inactive'})
    def test_validate_student_profile_inactive_estado(self, _mock_build):
        user = _user()
        perfil = Mock(estado_academico='Retirado')

        with patch('backend.apps.accounts.models.PerfilEstudiante.objects.get', return_value=perfil):
            result = AcademicViewService._validate_student_profile(user)

        assert result == {'error': 'inactive'}


class TestStudentProfileAndGrades:
    @patch.object(AcademicViewService, '_validate_school_integrity_from_user')
    def test_get_student_profile_success_and_not_found(self, _mock_integrity):
        user = _user()
        perfil = Mock(curso_actual=Mock())

        with patch('backend.apps.accounts.models.PerfilEstudiante.objects.get', return_value=perfil):
            p, c = AcademicViewService._execute_get_student_profile({'user': user})
        assert p is perfil
        assert c is perfil.curso_actual

        with patch('backend.apps.accounts.models.PerfilEstudiante.objects.get', side_effect=Exception('nope')), patch(
            'backend.apps.accounts.models.PerfilEstudiante.DoesNotExist',
            Exception,
        ):
            p2, c2 = AcademicViewService._execute_get_student_profile({'user': user})
        assert p2 is None
        assert c2 is None

    @patch.object(AcademicViewService, '_validate_school_integrity_from_user')
    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.cursos.models.Clase')
    def test_calculate_grades_by_subject(self, mock_clase, mock_calificacion, _mock_integrity):
        user = _user()
        curso = Mock()

        clase = Mock()
        clase.asignatura.nombre = 'Matemática'
        clase.profesor.get_full_name.return_value = 'Profe Uno'
        mock_clase.objects.filter.return_value.select_related.return_value = [clase]

        cal1 = Mock()
        cal1.nota = 6.0
        cal1.evaluacion.nombre = 'Prueba 1'
        cal1.evaluacion.fecha_evaluacion = date(2026, 1, 10)
        cal1.evaluacion.ponderacion = 50

        cal2 = Mock()
        cal2.nota = 4.0
        cal2.evaluacion.nombre = 'Prueba 2'
        cal2.evaluacion.fecha_evaluacion = date(2026, 1, 20)
        cal2.evaluacion.ponderacion = 50

        qs = MagicMock()
        qs.select_related.return_value.order_by.return_value = qs
        qs.exists.return_value = True
        qs.__iter__.return_value = iter([cal1, cal2])
        mock_calificacion.objects.filter.return_value = qs

        result = AcademicViewService._execute_calculate_grades_by_subject({'user': user, 'curso_actual': curso})

        assert result['promedio_general'] == 5.0
        assert result['total_notas'] == 2
        assert result['sin_datos'] is False

    @patch.object(AcademicViewService, '_validate_school_integrity_from_user')
    def test_calculate_grades_by_subject_without_course(self, _mock_integrity):
        user = _user()

        result = AcademicViewService._execute_calculate_grades_by_subject({'user': user, 'curso_actual': None})

        assert result['sin_datos'] is True
        assert result['total_notas'] == 0


class TestAttendanceAndClasses:
    @patch.object(AcademicViewService, '_validate_school_integrity_from_user')
    @patch('backend.apps.academico.services.academic_view_service.PolicyService.has_capability', return_value=False)
    def test_calculate_attendance_statistics_permission_denied(self, _mock_policy, _mock_integrity):
        user = _user(role='Apoderado')

        with pytest.raises(PermissionDenied):
            AcademicViewService._execute_calculate_attendance_statistics({'user': user, 'mes_filtro': None})

    @patch.object(AcademicViewService, '_validate_school_integrity_from_user')
    @patch('backend.apps.academico.services.academic_view_service.PolicyService.has_capability', side_effect=lambda _u, c, school_id=None: c in {'CLASS_VIEW', 'GRADE_VIEW'})
    @patch('backend.apps.academico.models.Asistencia')
    @patch('backend.apps.accounts.models.PerfilEstudiante')
    def test_calculate_attendance_statistics_success(self, mock_perfil, mock_asistencia, _mock_policy, _mock_integrity):
        user = _user(role='Alumno')
        mock_perfil.objects.get.return_value.curso_actual = Mock()

        a1 = Mock()
        a1.fecha.strftime.side_effect = ['2026-01-01', '01/01/2026']
        a1.clase.asignatura.nombre = 'Lenguaje'
        a1.estado = 'P'
        a1.get_estado_display.return_value = 'Presente'
        a1.observaciones = ''

        a2 = Mock()
        a2.fecha.strftime.side_effect = ['2026-01-02', '02/01/2026']
        a2.clase.asignatura.nombre = 'Matemática'
        a2.estado = 'A'
        a2.get_estado_display.return_value = 'Ausente'
        a2.observaciones = 'Justificada'

        qs = MagicMock()
        qs.select_related.return_value.order_by.return_value = qs
        qs.__iter__.return_value = iter([a1, a2])
        qs.count.return_value = 2

        p_qs = Mock(); p_qs.count.return_value = 1
        a_qs = Mock(); a_qs.count.return_value = 1
        t_qs = Mock(); t_qs.count.return_value = 0
        j_qs = Mock(); j_qs.count.return_value = 0
        recent_qs = MagicMock(); recent_qs.order_by.return_value.__getitem__.return_value = [a1, a2]

        def filter_side_effect(**kwargs):
            if kwargs.get('estado') == 'P':
                return p_qs
            if kwargs.get('estado') == 'A':
                return a_qs
            if kwargs.get('estado') == 'T':
                return t_qs
            if kwargs.get('estado') == 'J':
                return j_qs
            if 'fecha__gte' in kwargs:
                return recent_qs
            return qs

        qs.filter.side_effect = filter_side_effect
        mock_asistencia.objects.filter.return_value = qs

        result = AcademicViewService._execute_calculate_attendance_statistics({'user': user, 'mes_filtro': '2026-01'})

        assert result['total_registros'] == 2
        assert result['presentes'] == 1
        assert result['ausentes'] == 1
        assert result['porcentaje_asistencia'] == 50.0
        assert len(result['registros_recientes']) == 2

    @patch.object(AcademicViewService, '_validate_school_integrity_from_user')
    @patch('backend.apps.cursos.models.BloqueHorario')
    @patch('backend.apps.cursos.models.Clase')
    def test_get_student_classes(self, mock_clase, mock_bloque, _mock_integrity):
        user = _user()
        curso = Mock()

        clase = Mock()
        clase.id = 3
        clase.asignatura.nombre = 'Historia'
        clase.asignatura.codigo = 'HIS'
        clase.asignatura.color = '#111111'
        clase.asignatura.horas_semanales = 4
        clase.horas_semanales = 4
        clase.profesor.get_full_name.return_value = 'Profe Historia'
        clase.profesor.email = 'profe@test.cl'

        bloque = Mock()
        bloque.get_dia_semana_display.return_value = 'Lunes'
        bloque.bloque_numero = 1
        bloque.hora_inicio.strftime.return_value = '08:00'
        bloque.hora_fin.strftime.return_value = '08:45'

        mock_clase.objects.filter.return_value.select_related.return_value = [clase]
        bqs = MagicMock()
        bqs.order_by.return_value = bqs
        bqs.count.return_value = 1
        bqs.__iter__.return_value = iter([bloque])
        mock_bloque.objects.filter.return_value = bqs

        result = AcademicViewService._execute_get_student_classes({'user': user, 'curso_actual': curso})

        assert result['total_clases'] == 1
        assert result['mis_clases'][0]['asignatura'] == 'Historia'

    @patch.object(AcademicViewService, '_validate_school_integrity_from_user')
    @patch('backend.apps.cursos.models.BloqueHorario')
    @patch('backend.apps.core.optimizations.get_clases_profesor_optimized')
    def test_get_teacher_classes(self, mock_opt, mock_bloque, _mock_integrity):
        user = _user(role='Profesor')

        clase = Mock()
        clase.id = 9
        clase.asignatura.nombre = 'Química'
        clase.asignatura.codigo = 'QUI'
        clase.asignatura.color = '#222222'
        clase.asignatura.horas_semanales = 5
        clase.curso.nombre = '2B'
        clase.curso.id_curso = 77
        clase.estudiantes.filter.return_value.count.return_value = 28
        mock_opt.return_value = [clase]

        bloque = Mock()
        bloque.get_dia_semana_display.return_value = 'Martes'
        bloque.bloque_numero = 2
        bloque.hora_inicio.strftime.return_value = '09:00'
        bloque.hora_fin.strftime.return_value = '09:45'

        bqs = MagicMock()
        bqs.order_by.return_value = bqs
        bqs.count.return_value = 1
        bqs.__iter__.return_value = iter([bloque])
        mock_bloque.objects.filter.return_value = bqs

        result = AcademicViewService._execute_get_teacher_classes({'user': user})

        assert result['total_clases'] == 1
        assert result['promedio_estudiantes'] == 28
        assert result['total_horas_semanales'] == 5
        assert result['total_cursos'] == 1

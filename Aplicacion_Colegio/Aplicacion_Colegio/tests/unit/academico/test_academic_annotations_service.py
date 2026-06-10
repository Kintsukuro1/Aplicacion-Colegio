from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest

from backend.apps.academico.services.academic_annotations_service import AcademicAnnotationsService


pytestmark = pytest.mark.django_db


class TestAcademicAnnotationsServiceBasics:
    def test_validate_rejects_invalid_inputs(self):
        with pytest.raises(ValueError):
            AcademicAnnotationsService.validate('', {})
        with pytest.raises(ValueError):
            AcademicAnnotationsService.validate('op', [])

    def test_execute_dispatch_and_unsupported(self):
        with patch.object(AcademicAnnotationsService, 'validate') as mock_validate, patch.object(
            AcademicAnnotationsService,
            '_execute',
            return_value='ok',
        ) as mock_exec:
            result = AcademicAnnotationsService.execute('x', {'a': 1})

        assert result == 'ok'
        mock_validate.assert_called_once()
        mock_exec.assert_called_once()

        with pytest.raises(ValueError):
            AcademicAnnotationsService._execute('op_inexistente', {})

    def test_validate_school_integrity_calls_integrity_service(self):
        with patch('backend.apps.academico.services.academic_annotations_service.IntegrityService.validate_school_integrity_or_raise') as mock_integrity:
            AcademicAnnotationsService._validate_school_integrity(123, 'ACTION')
        mock_integrity.assert_called_once_with(school_id=123, action='ACTION')


class TestAttendanceObservation:
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'not_found'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_add_attendance_observation_not_found(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)

        with patch('backend.apps.academico.models.Asistencia') as mock_asistencia:
            mock_asistencia.DoesNotExist = Exception
            mock_asistencia.objects.get.side_effect = Exception('not found')
            result = AcademicAnnotationsService.add_attendance_observation(user, colegio, 10, 'obs')

        assert result == {'error': 'not_found'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'invalid_class'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_add_attendance_observation_inactive_class(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        asistencia = Mock()
        asistencia.clase.activo = False
        asistencia.clase.id_clase = 7

        with patch('backend.apps.academico.models.Asistencia') as mock_asistencia:
            mock_asistencia.objects.get.return_value = asistencia
            result = AcademicAnnotationsService.add_attendance_observation(user, colegio, 10, 'obs')

        assert result == {'error': 'invalid_class'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'invalid_student'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_add_attendance_observation_inactive_student(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        asistencia = Mock()
        asistencia.clase.activo = True
        asistencia.estudiante.is_active = False
        asistencia.estudiante.id = 5

        with patch('backend.apps.academico.models.Asistencia') as mock_asistencia:
            mock_asistencia.objects.get.return_value = asistencia
            result = AcademicAnnotationsService.add_attendance_observation(user, colegio, 10, 'obs')

        assert result == {'error': 'invalid_student'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_add_attendance_observation_success(self, _mock_integrity, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        asistencia = Mock()
        asistencia.clase.activo = True
        asistencia.estudiante.is_active = True

        with patch('backend.apps.academico.models.Asistencia') as mock_asistencia:
            mock_asistencia.objects.get.return_value = asistencia
            result = AcademicAnnotationsService.add_attendance_observation(user, colegio, 10, 'nueva obs')

        assert result is None
        assert asistencia.observaciones == 'nueva obs'
        asistencia.save.assert_called_once()


class TestAnnotationsQueries:
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_student_academic_annotations_sorted(self, _mock_perm):
        user = Mock()
        estudiante = Mock()

        a1 = Mock()
        a1.fecha = date.today() - timedelta(days=1)
        a1.clase.asignatura.nombre = 'Lenguaje'
        a1.observaciones = 'Obs 1'
        a1.get_estado_display.return_value = 'Presente'

        a2 = Mock()
        a2.fecha = date.today()
        a2.clase.asignatura.nombre = 'Matemática'
        a2.observaciones = 'Obs 2'
        a2.get_estado_display.return_value = 'Ausente'

        qs = Mock()
        qs.exclude.return_value.exclude.return_value = [a1, a2]

        with patch('backend.apps.academico.models.Asistencia') as mock_asistencia:
            mock_asistencia.objects.filter.return_value = qs
            result = AcademicAnnotationsService.get_student_academic_annotations(user, estudiante)

        assert len(result) == 2
        assert result[0]['contenido'] == 'Obs 2'

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_class_academic_annotations_with_date_filter(self, _mock_perm):
        user = Mock()
        clase = Mock()

        a1 = Mock()
        a1.fecha = date.today()
        a1.estudiante.get_full_name.return_value = 'Estudiante Uno'
        a1.observaciones = 'Obs clase'
        a1.get_estado_display.return_value = 'Tarde'

        qs = Mock()
        qs.exclude.return_value.exclude.return_value.select_related.return_value = qs
        qs.filter.return_value = [a1]

        with patch('backend.apps.academico.models.Asistencia') as mock_asistencia:
            mock_asistencia.objects.filter.return_value = qs
            result = AcademicAnnotationsService.get_class_academic_annotations(user, clase, date.today())

        assert len(result) == 1
        assert result[0]['estudiante'] == 'Estudiante Uno'


class TestCreateAcademicNote:
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'inactive_student'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_create_note_inactive_student(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        estudiante = Mock(is_active=False, id=9)

        result = AcademicAnnotationsService.create_academic_note(user, colegio, estudiante, None, 'positiva', 'ok')

        assert result == {'error': 'inactive_student'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'inactive_class'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_create_note_inactive_class(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        estudiante = Mock(is_active=True, id=9, rbd_colegio=1)
        clase = Mock(activo=False, id_clase=2)

        result = AcademicAnnotationsService.create_academic_note(user, colegio, estudiante, clase, 'positiva', 'ok')

        assert result == {'error': 'inactive_class'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'invalid_relationship'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_create_note_invalid_student_school(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        estudiante = Mock(is_active=True, id=9, rbd_colegio=2)

        result = AcademicAnnotationsService.create_academic_note(user, colegio, estudiante, None, 'positiva', 'ok')

        assert result == {'error': 'invalid_relationship'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'invalid_class_school'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_create_note_invalid_class_school(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        estudiante = Mock(is_active=True, id=9, rbd_colegio=1)
        clase = Mock(activo=True, colegio_id=2, id_clase=4)

        result = AcademicAnnotationsService.create_academic_note(user, colegio, estudiante, clase, 'positiva', 'ok')

        assert result == {'error': 'invalid_class_school'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.ErrorResponseBuilder.build', return_value={'error': 'invalid_cycle'})
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_create_note_invalid_cycle(self, _mock_integrity, _mock_error, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        perfil = Mock(ciclo_actual_id=100)
        estudiante = Mock(is_active=True, id=9, rbd_colegio=1, perfil_estudiante=perfil)
        clase = Mock(activo=True, colegio_id=1, id_clase=4)
        clase.curso.ciclo_academico_id = 200

        result = AcademicAnnotationsService.create_academic_note(user, colegio, estudiante, clase, 'positiva', 'ok')

        assert result == {'error': 'invalid_cycle'}

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_create_note_success_created_and_append(self, _mock_integrity, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)
        estudiante = Mock(is_active=True, id=9, rbd_colegio=1, perfil_estudiante=None)
        clase = Mock(activo=True, colegio_id=1, id_clase=4)

        asistencia = Mock(observaciones='Anterior')

        with patch('backend.apps.academico.models.Asistencia') as mock_asistencia:
            mock_asistencia.objects.get_or_create.side_effect = [
                (Mock(), True),
                (asistencia, False),
            ]
            r1 = AcademicAnnotationsService.create_academic_note(user, colegio, estudiante, clase, 'positiva', 'primera', date.today())
            r2 = AcademicAnnotationsService.create_academic_note(user, colegio, estudiante, clase, 'negativa', 'segunda', date.today())

        assert r1 is None
        assert r2 is None
        asistencia.save.assert_called_once()


class TestSummaryAndEvaluationComment:
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    def test_get_academic_notes_summary(self, _mock_perm):
        user = Mock()
        estudiante = Mock()
        anotaciones = [
            {'tipo': 'asistencia', 'fecha': date.today()},
            {'tipo': 'asistencia', 'fecha': date.today() - timedelta(days=40)},
        ]

        with patch.object(AcademicAnnotationsService, 'get_student_academic_annotations', return_value=anotaciones):
            result = AcademicAnnotationsService.get_academic_notes_summary(user, estudiante)

        assert result['total_anotaciones'] == 2
        assert result['anotaciones_por_tipo']['asistencia'] == 2
        assert result['anotaciones_recientes'] == 1
        assert result['ultima_anotacion'] == anotaciones[0]

    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.services.academic_annotations_service.AcademicAnnotationsService._validate_school_integrity')
    def test_update_evaluation_comment(self, _mock_integrity, _mock_perm):
        user = Mock()
        colegio = Mock(rbd=1)

        with patch('backend.apps.academico.models.Calificacion') as mock_calificacion:
            mock_calificacion.objects.get.return_value = Mock()
            assert AcademicAnnotationsService.update_evaluation_comment(user, colegio, 1, 'ok') is True

            mock_calificacion.DoesNotExist = Exception
            mock_calificacion.objects.get.side_effect = Exception('missing')
            assert AcademicAnnotationsService.update_evaluation_comment(user, colegio, 2, 'ok') is False

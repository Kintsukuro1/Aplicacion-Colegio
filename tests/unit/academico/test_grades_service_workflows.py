from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.apps.academico.services.grades_service import GradesService


pytestmark = pytest.mark.django_db


def _user(role_name='Profesor'):
    return SimpleNamespace(
        id=1,
        is_authenticated=True,
        role=SimpleNamespace(nombre=role_name),
        email='profe@test.cl',
    )


@pytest.fixture(autouse=True)
def _allow_permissions(monkeypatch):
    monkeypatch.setattr(
        'backend.common.services.permission_service.PermissionService.has_permission',
        lambda *args, **kwargs: True,
    )


@pytest.fixture(autouse=True)
def _mock_escala(monkeypatch):
    monkeypatch.setattr(
        'backend.apps.institucion.models.ConfiguracionAcademica.get_escala_para_colegio',
        lambda *args, **kwargs: {
            'nota_minima': Decimal('1.0'),
            'nota_maxima': Decimal('7.0'),
            'nota_aprobacion': Decimal('4.0'),
            'nota_eximicion': Decimal('5.5'),
            'redondeo_decimales': 1
        }
    )


class _FakePrereq(Exception):
    def __init__(self):
        self.error_dict = {'message': 'faltan prerequisitos', 'action_url': '/accion'}


class TestGradesServiceWorkflows:
    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.academico.services.grades_service.GradesService._validate_school_integrity')
    def test_create_validation_get_update_delete_execute_helpers(self, _mock_integrity, mock_calificacion):
        data = {
            'colegio': Mock(rbd=123),
            'evaluacion': Mock(),
            'estudiante': Mock(),
            'nota': Decimal('5.5'),
            'registrado_por': Mock(),
        }
        mock_obj = Mock(
            colegio=data['colegio'],
            evaluacion=data['evaluacion'],
            estudiante=data['estudiante'],
            nota=data['nota'],
            registrado_por=data['registrado_por'],
            actualizado_por=data['registrado_por'],
        )
        mock_calificacion.objects.create.return_value = mock_obj
        mock_calificacion.objects.select_related.return_value.get.return_value = mock_obj

        created = GradesService.create(data)
        assert created is mock_obj

        updated = GradesService.update(1, {'nota': Decimal('6.0')})
        assert updated is mock_obj
        assert mock_obj.nota == Decimal('6.0')

        GradesService.delete(1)
        mock_obj.delete.assert_called_once()

        with pytest.raises(ValueError):
            GradesService.execute('validate', {'operation': 'x'})
        with pytest.raises(ValueError):
            GradesService.validate('', {})
        with pytest.raises(ValueError):
            GradesService._execute('no_existe', {})

    @patch('backend.apps.cursos.models.Clase')
    @patch('backend.apps.academico.services.grades_service.CommonValidations.validate_class_ownership', return_value=(True, ''))
    @patch('backend.apps.academico.services.grades_service.GradesService.create_evaluation')
    @patch('django.urls.reverse', return_value='/dashboard/')
    @patch('backend.apps.academico.services.resoluble_service.ResolubleService.create_or_update_activity')
    @patch('backend.apps.academico.services.grades_service.GradesService._notificar_revision_pendiente')
    def test_process_evaluation_action_create_success(self, mock_notify, mock_create_activity, _mock_reverse, mock_create_eval, _mock_owner, mock_clase):
        user = _user('Profesor')
        colegio = Mock()
        clase = Mock(id=11)
        mock_clase.objects.get.return_value = clase
        mock_create_eval.return_value = Mock()

        result = GradesService.process_evaluation_action(user, colegio, {
            'accion': 'crear_evaluacion',
            'clase_id': '11',
            'nombre': 'Prueba',
            'fecha_evaluacion': date.today(),
            'ponderacion': '40.0',
            'pregunta_1_enunciado': 'Pregunta 1',
            'pregunta_1_tipo': 'desarrollo',
            'pregunta_1_respuesta_texto': 'Respuesta',
        })

        assert result['success'] is True
        assert 'redirect_url' in result

    @patch('backend.apps.cursos.models.Clase')
    @patch('backend.apps.academico.services.grades_service.CommonValidations.validate_class_ownership', return_value=(False, 'sin permisos'))
    def test_process_evaluation_action_create_forbidden(self, _mock_owner, mock_clase):
        user = _user('Profesor')
        colegio = Mock()
        mock_clase.objects.get.return_value = Mock(id=2)

        result = GradesService.process_evaluation_action(user, colegio, {
            'accion': 'crear_evaluacion',
            'clase_id': '2',
            'pregunta_1_enunciado': 'Pregunta 1',
            'pregunta_1_tipo': 'desarrollo',
            'pregunta_1_respuesta_texto': 'Respuesta',
        })

        assert result == {'success': False, 'message': 'sin permisos'}

    @patch('backend.apps.academico.models.Evaluacion')
    @patch('backend.apps.cursos.models.Clase')
    @patch('backend.apps.academico.services.grades_service.CommonValidations.validate_class_ownership', return_value=(True, ''))
    @patch('backend.apps.academico.services.grades_service.GradesService.update_evaluation', return_value=True)
    @patch('django.urls.reverse', return_value='/dashboard/')
    @patch('backend.apps.academico.services.resoluble_service.ResolubleService.create_or_update_activity')
    @patch('backend.apps.academico.services.grades_service.GradesService._notificar_revision_pendiente')
    def test_process_evaluation_action_edit_success(self, mock_notify, mock_create_activity, _mock_reverse, _mock_update, _mock_owner, mock_clase, mock_eval):
        user = _user('Profesor')
        colegio = Mock()
        clase = Mock(id=12)
        mock_clase.objects.get.return_value = clase
        mock_eval.objects.select_related.return_value.prefetch_related.return_value.get.return_value = Mock(clase_id=12)

        result = GradesService.process_evaluation_action(user, colegio, {
            'accion': 'editar_evaluacion',
            'clase_id': '12',
            'id': '5',
            'nombre': 'Control',
            'fecha_evaluacion': date.today(),
            'ponderacion': '30.0',
            'pregunta_1_enunciado': 'Pregunta 1',
            'pregunta_1_tipo': 'desarrollo',
            'pregunta_1_respuesta_texto': 'Respuesta',
        })

        assert result['success'] is True

    @patch('backend.apps.cursos.models.Clase')
    @patch('backend.apps.academico.services.grades_service.CommonValidations.validate_class_ownership', return_value=(True, ''))
    @patch('backend.apps.academico.services.grades_service.GradesService.update_evaluation', return_value=False)
    def test_process_evaluation_action_edit_not_found(self, _mock_update, _mock_owner, mock_clase):
        user = _user('Profesor')
        colegio = Mock()
        mock_clase.objects.get.return_value = Mock(id=12)

        result = GradesService.process_evaluation_action(user, colegio, {
            'accion': 'editar_evaluacion',
            'clase_id': '12',
            'id': '5',
            'nombre': 'Control',
            'fecha_evaluacion': date.today(),
            'ponderacion': '30.0',
        })

        assert result['success'] is False

    @patch('backend.apps.academico.services.grades_service.CommonValidations.validate_class_ownership', return_value=(False, 'sin permisos'))
    @patch('backend.apps.academico.models.Evaluacion')
    def test_process_evaluation_action_delete_profesor_forbidden(self, mock_eval, _mock_owner):
        user = _user('Profesor')
        colegio = Mock()
        evaluacion = Mock()
        evaluacion.clase = Mock()
        mock_eval.objects.select_related.return_value.get.return_value = evaluacion

        result = GradesService.process_evaluation_action(user, colegio, {'accion': 'eliminar_evaluacion', 'id': '9'})

        assert result['success'] is False
        assert 'Error:' in result['message']

    @patch('backend.apps.academico.services.grades_service.CommonValidations.validate_class_ownership', return_value=(True, ''))
    @patch('backend.apps.academico.services.grades_service.GradesService.delete_evaluation', return_value=True)
    @patch('backend.apps.academico.models.Evaluacion')
    @patch('django.urls.reverse', return_value='/dashboard/')
    def test_process_evaluation_action_delete_success(self, _mock_reverse, _mock_eval_del, mock_eval, _mock_owner):
        user = _user('Profesor')
        colegio = Mock()
        evaluacion = Mock(clase_id=33)
        evaluacion.clase = Mock()
        mock_eval.objects.select_related.return_value.get.return_value = evaluacion

        result = GradesService.process_evaluation_action(user, colegio, {'accion': 'eliminar_evaluacion', 'id': '9'})

        assert result['success'] is True

    def test_process_evaluation_action_prerequisite_and_generic_errors(self):
        user = _user('Profesor')
        colegio = Mock()

        with patch('backend.apps.academico.services.grades_service.PrerequisiteException', _FakePrereq), \
             patch('backend.apps.cursos.models.Clase.objects.get', side_effect=_FakePrereq()):
            result = GradesService.process_evaluation_action(user, colegio, {'accion': 'crear_evaluacion', 'clase_id': '1'})
            assert result['success'] is False
            assert result['redirect_url'] == '/accion'

        with patch('backend.apps.cursos.models.Clase.objects.get', side_effect=Exception('boom')):
            result2 = GradesService.process_evaluation_action(user, colegio, {'accion': 'crear_evaluacion', 'clase_id': '1'})
            assert result2['success'] is False

    @patch('backend.apps.academico.services.grades_service.GradesService.register_grades_for_evaluation', return_value=2)
    @patch('backend.apps.academico.models.Evaluacion')
    @patch('django.urls.reverse', return_value='/dashboard/')
    def test_process_grades_registration_success(self, _mock_reverse, mock_eval, _mock_register):
        user = _user('Profesor')
        colegio = Mock()
        evaluacion = Mock(id_evaluacion=7)
        evaluacion.clase = Mock()
        mock_eval.objects.select_related.return_value.get.return_value = evaluacion

        result = GradesService.process_grades_registration(user, colegio, {
            'evaluacion_id': 7,
            'nota_1': '6.0',
            'nota_2': 'x',
            'nota_3': '9.0',
            'nota_4': '5.5',
        })

        assert result['success'] is False
        assert 'Error al registrar calificaciones' in result['message']

    @patch('backend.apps.academico.models.Evaluacion')
    def test_process_grades_registration_error(self, mock_eval):
        user = _user('Profesor')
        colegio = Mock()
        mock_eval.objects.select_related.return_value.get.side_effect = Exception('fail')

        result = GradesService.process_grades_registration(user, colegio, {'evaluacion_id': 7})

        assert result['success'] is False

    def test_get_student_classes_summary_success_and_exception(self):
        user = Mock()
        user.colegio = Mock()
        user.perfil_estudiante = Mock()
        curso = Mock(nombre='1A')
        user.perfil_estudiante.curso_actual = curso

        clase = Mock()
        clase.id = 5
        clase.asignatura.nombre = 'Lenguaje'
        clase.asignatura.color = '#000'
        clase.asignatura.horas_semanales = 5
        clase.profesor.get_full_name.return_value = 'Profesor X'

        with patch('backend.apps.cursos.models.Clase.objects.filter') as mock_filter:
            mock_filter.return_value.select_related.return_value.order_by.return_value = [clase]
            result = GradesService.get_student_classes_summary(user)

        assert result['total_clases'] == 1
        assert result['curso_actual'] == '1A'

        user_bad = Mock()
        user_bad.perfil_estudiante = Mock(curso_actual=curso)
        user_bad.colegio = Mock()
        with patch('backend.apps.cursos.models.Clase.objects.filter', side_effect=Exception('x')):
            result2 = GradesService.get_student_classes_summary(user_bad)
        assert 'error' in result2

    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.accounts.models.User')
    @patch('backend.apps.academico.models.Evaluacion')
    def test_build_gradebook_matrix_branches(self, mock_eval, mock_user_model, mock_calificacion):
        colegio = Mock(rbd=123)
        clase = Mock()
        clase.curso.ciclo_academico = Mock()

        ev1 = Mock(pk=201, nombre='E1', fecha_evaluacion=date.today())
        ev2 = Mock(pk=202, nombre='E2', fecha_evaluacion=date.today())
        mock_eval.objects.filter.return_value.order_by.return_value = [ev1, ev2]

        estudiante = Mock(pk=101)
        mock_user_model.objects.filter.return_value.select_related.return_value.order_by.return_value = [estudiante]

        calif_e1 = Mock(estudiante_id=101, evaluacion_id=201, nota=Decimal('5.0'))
        mock_calificacion.objects.filter.return_value = [calif_e1]

        result = GradesService.build_gradebook_matrix(colegio, clase)

        assert result['total_evaluaciones'] == 2
        assert result['total_estudiantes'] == 1
        assert result['promedio_general'] == 5.0
        assert len(result['promedios_evaluaciones']) == 2
        assert result['matriz_calificaciones'][0]['notas'] == [5.0, None]
        assert result['matriz_calificaciones'][0]['promedio'] == 5.0

    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.accounts.models.PerfilEstudiante')
    @patch('backend.apps.academico.services.grades_service.GradesService.calculate_student_final_grade')
    def test_get_student_grades_summary_success_and_errors(self, mock_final_grade, mock_perfil_model, mock_calificacion):
        user = Mock(id=55)
        perfil = Mock()
        curso = Mock(nombre='2B')
        perfil.curso_actual = curso
        mock_perfil_model.objects.get.return_value = perfil

        clase = Mock()
        clase.asignatura.nombre = 'Matemática'
        clase.profesor.get_full_name.return_value = 'Profe Y'
        curso.clases.filter.return_value.select_related.return_value = [clase]

        mock_final_grade.return_value = {'nota_final': 6.0, 'estado': 'Aprobado'}
        calif = Mock()
        calif.evaluacion.nombre = 'Prueba 1'
        calif.evaluacion.ponderacion = Decimal('50.0')
        calif.evaluacion.fecha_evaluacion = date.today()
        calif.nota = Decimal('6.0')
        mock_calificacion.objects.filter.return_value.select_related.return_value.order_by.return_value = [calif]

        result = GradesService.get_student_grades_summary(user)
        assert result['total_notas'] == 1
        assert result['curso_actual'] == '2B'
        assert result['promedio_general'] == 6.0

        does_not_exist = type('DoesNotExist', (Exception,), {})
        mock_perfil_model.DoesNotExist = does_not_exist
        mock_perfil_model.objects.get.side_effect = does_not_exist()
        result_missing = GradesService.get_student_grades_summary(user)
        assert result_missing['error'] == 'Student profile not found'

        mock_perfil_model.objects.get.side_effect = Exception('boom')
        result_error = GradesService.get_student_grades_summary(user)
        assert result_error['sin_datos'] is True

    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.accounts.models.User')
    @patch('backend.apps.academico.services.grades_service.GradesService._validate_clase_active_state', return_value=None)
    def test_get_students_with_grades_and_final_grade(self, _mock_validate, mock_user_model, mock_calificacion):
        user = _user('Profesor')
        colegio = Mock(rbd=123)
        evaluacion = Mock(id_evaluacion=77)
        evaluacion.clase.curso.ciclo_academico = Mock()

        estudiante = Mock(id=10)
        mock_user_model.objects.filter.return_value.select_related.return_value.order_by.return_value = [estudiante]

        calif = Mock()
        calif.estudiante.id = 10
        calif.nota = Decimal('6.0')
        calif.evaluacion.nombre = 'Prueba'
        calif.evaluacion.ponderacion = Decimal('50.0')
        evaluacion.calificaciones.all.return_value = [calif]
        mock_calificacion.objects.filter.return_value.select_related.return_value = [calif]

        rows = GradesService.get_students_with_grades(colegio, evaluacion)
        assert len(rows) == 1
        assert rows[0]['calificacion'] == Decimal('6.0')

        final_data = GradesService.calculate_student_final_grade(estudiante, evaluacion.clase)
        assert final_data['nota_final'] == 6.0
        assert final_data['estado'] == 'Aprobado'

    @patch('backend.apps.academico.services.grades_service.IntegrityService.validate_school_integrity_or_raise')
    def test_validation_and_integrity_default_branch(self, mock_validate_default):
        with pytest.raises(ValueError):
            GradesService.validations({'colegio': Mock()})
        with pytest.raises(ValueError):
            GradesService.validations({
                'colegio': Mock(),
                'evaluacion': Mock(),
                'estudiante': Mock(),
                'nota': Decimal('8.0'),
                'registrado_por': Mock(),
            })
        with pytest.raises(ValueError):
            GradesService.validate('ok', [])

        colegio = Mock(rbd=999)
        GradesService._validate_school_integrity(colegio, 'UNKNOWN_ACTION')
        mock_validate_default.assert_called_once_with(school_id=999, action='UNKNOWN_ACTION')

    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.accounts.models.PerfilEstudiante')
    @patch('backend.apps.academico.services.grades_service.GradesService.calculate_student_final_grade', return_value={'nota_final': None, 'estado': 'Sin evaluaciones'})
    def test_get_student_grades_summary_skips_subject_without_grade(self, _mock_grade, mock_perfil_model, _mock_calificacion):
        user = Mock(id=56)
        perfil = Mock()
        curso = Mock(nombre='3B')
        perfil.curso_actual = curso
        mock_perfil_model.objects.get.return_value = perfil
        curso.clases.filter.return_value.select_related.return_value = [Mock()]

        result = GradesService.get_student_grades_summary(user)
        assert result['total_notas'] == 0
        assert result['sin_datos'] is True

    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.accounts.models.User')
    @patch('backend.apps.academico.models.Evaluacion')
    def test_build_gradebook_matrix_sin_notas_branch(self, mock_eval, mock_user_model, mock_calificacion):
        colegio = Mock(rbd=123)
        clase = Mock()
        clase.curso.ciclo_academico = Mock()

        ev1 = Mock(pk=201, nombre='E1', fecha_evaluacion=date.today())
        mock_eval.objects.filter.return_value.order_by.return_value = [ev1]
        estudiante = Mock(pk=101)
        mock_user_model.objects.filter.return_value.select_related.return_value.order_by.return_value = [estudiante]

        mock_calificacion.objects.filter.return_value = []

        result = GradesService.build_gradebook_matrix(colegio, clase)
        assert result['matriz_calificaciones'][0]['estado'] == 'Sin Notas'
        assert result['promedio_general'] == 0

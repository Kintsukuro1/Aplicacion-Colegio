import datetime as dt

import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User
from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion
from backend.apps.cursos.models import Asignatura, Clase, ClaseEstudiante, Curso
from backend.apps.institucion.models import Colegio, NivelEducativo
from backend.common.services.policy_service import PolicyService


pytestmark = pytest.mark.django_db


def _mk_role(name):
    role, _ = Role.objects.get_or_create(nombre=name)
    return role


def _mk_user(email, role_name, school_id, rut):
    return User.objects.create_user(
        email=email,
        password='Test#123456',
        nombre='Nombre',
        apellido_paterno='Apellido',
        rut=rut,
        role=_mk_role(role_name),
        rbd_colegio=school_id,
        is_active=True,
    )


def _mk_school(rbd, name):
    return Colegio.objects.create(rbd=rbd, nombre=name, rut_establecimiento=f'{rbd}-K')


def _configure_capabilities(monkeypatch, capability_by_email):
    def _fake_has_capability(user, capability, school_id=None):
        allowed = capability_by_email.get(user.email, set())
        return capability in allowed

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(_fake_has_capability))


def _mk_class_graph(school, teacher):
    nivel = NivelEducativo.objects.create(nombre=f'Nivel {school.rbd}')
    curso = Curso.objects.create(colegio=school, nombre=f'{school.rbd}-A', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre=f'Asignatura {school.rbd}')
    return Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=teacher,
    )


def test_bulk_deactivate_students_works_for_student_edit(monkeypatch):
    school = _mk_school(8101, 'Colegio Bulk Students')
    admin = _mk_user('admin-bulk-students@test.cl', 'Administrador escolar', school.rbd, '50000001-1')
    student_one = _mk_user('student-bulk-1@test.cl', 'Estudiante', school.rbd, '50000002-2')
    student_two = _mk_user('student-bulk-2@test.cl', 'Estudiante', school.rbd, '50000003-3')

    _configure_capabilities(monkeypatch, {admin.email: {'STUDENT_EDIT'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.post(
        '/api/v1/estudiantes/bulk-deactivate/',
        {'ids': [student_one.id, student_two.id]},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 2
    assert payload['failed'] == 0

    student_one.refresh_from_db()
    student_two.refresh_from_db()
    assert student_one.is_active is False
    assert student_two.is_active is False


def test_bulk_deactivate_students_reports_invalid_ids(monkeypatch):
    school = _mk_school(8106, 'Colegio Bulk Students Invalid')
    admin = _mk_user('admin-bulk-students-invalid@test.cl', 'Administrador escolar', school.rbd, '50000101-1')
    student = _mk_user('student-bulk-invalid@test.cl', 'Estudiante', school.rbd, '50000102-2')

    _configure_capabilities(monkeypatch, {admin.email: {'STUDENT_EDIT'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.post(
        '/api/v1/estudiantes/bulk-deactivate/',
        {'ids': [student.id, 'abc']},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 1
    assert payload['failed'] == 1
    assert 'abc' in payload['failed_ids']


def test_bulk_update_attendance_state_updates_selected_rows(monkeypatch):
    school = _mk_school(8102, 'Colegio Bulk Attendance')
    teacher = _mk_user('teacher-bulk-att@test.cl', 'Profesor', school.rbd, '50000004-4')
    student = _mk_user('student-bulk-att@test.cl', 'Estudiante', school.rbd, '50000005-5')
    clase = _mk_class_graph(school, teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    row_one = Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date(2026, 3, 1),
        estado='A',
    )
    row_two = Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date(2026, 3, 2),
        estado='T',
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'CLASS_TAKE_ATTENDANCE'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/profesor/asistencias/bulk-update-state/',
        {'ids': [row_one.id_asistencia, row_two.id_asistencia], 'estado': 'P'},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 2
    assert payload['failed'] == 0

    row_one.refresh_from_db()
    row_two.refresh_from_db()
    assert row_one.estado == 'P'
    assert row_two.estado == 'P'


def test_bulk_update_attendance_state_reports_invalid_ids(monkeypatch):
    school = _mk_school(8107, 'Colegio Bulk Attendance Invalid')
    teacher = _mk_user('teacher-bulk-att-invalid@test.cl', 'Profesor', school.rbd, '50000103-3')
    student = _mk_user('student-bulk-att-invalid@test.cl', 'Estudiante', school.rbd, '50000104-4')
    clase = _mk_class_graph(school, teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    row = Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date(2026, 3, 3),
        estado='A',
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'CLASS_TAKE_ATTENDANCE'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/profesor/asistencias/bulk-update-state/',
        {'ids': [row.id_asistencia, 'abc'], 'estado': 'P'},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 1
    assert payload['failed'] == 1
    assert 'abc' in payload['failed_ids']


def test_bulk_toggle_evaluations_active_flag(monkeypatch):
    school = _mk_school(8103, 'Colegio Bulk Eval')
    teacher = _mk_user('teacher-bulk-eval@test.cl', 'Profesor', school.rbd, '50000006-6')
    clase = _mk_class_graph(school, teacher)

    eval_one = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval 1',
        fecha_evaluacion=dt.date(2026, 3, 5),
        activa=True,
    )
    eval_two = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval 2',
        fecha_evaluacion=dt.date(2026, 3, 6),
        activa=True,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_EDIT'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/profesor/evaluaciones/bulk-toggle-active/',
        {'ids': [eval_one.id_evaluacion, eval_two.id_evaluacion], 'activa': False},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 2
    assert payload['failed'] == 0

    eval_one.refresh_from_db()
    eval_two.refresh_from_db()
    assert eval_one.activa is False
    assert eval_two.activa is False


def test_bulk_toggle_evaluations_reports_invalid_ids(monkeypatch):
    school = _mk_school(8108, 'Colegio Bulk Eval Invalid')
    teacher = _mk_user('teacher-bulk-eval-invalid@test.cl', 'Profesor', school.rbd, '50000105-5')
    clase = _mk_class_graph(school, teacher)

    evaluation = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval Invalid',
        fecha_evaluacion=dt.date(2026, 3, 12),
        activa=True,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_EDIT'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/profesor/evaluaciones/bulk-toggle-active/',
        {'ids': [evaluation.id_evaluacion, 'abc'], 'activa': False},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 1
    assert payload['failed'] == 1
    assert 'abc' in payload['failed_ids']


def test_bulk_delete_grades_removes_rows(monkeypatch):
    school = _mk_school(8104, 'Colegio Bulk Grade')
    teacher = _mk_user('teacher-bulk-grade@test.cl', 'Profesor', school.rbd, '50000007-7')
    student = _mk_user('student-bulk-grade@test.cl', 'Estudiante', school.rbd, '50000008-8')
    clase = _mk_class_graph(school, teacher)

    evaluation = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval Grade',
        fecha_evaluacion=dt.date(2026, 3, 8),
        activa=True,
    )

    grade_one = Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluation,
        estudiante=student,
        nota=5.5,
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    student_two = _mk_user('student-bulk-grade-2@test.cl', 'Estudiante', school.rbd, '50000009-9')
    grade_two = Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluation,
        estudiante=student_two,
        nota=6.0,
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_DELETE'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/profesor/calificaciones/bulk-delete/',
        {'ids': [grade_one.id_calificacion, grade_two.id_calificacion]},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 2
    assert payload['failed'] == 0
    assert Calificacion.objects.filter(pk=grade_one.id_calificacion).exists() is False
    assert Calificacion.objects.filter(pk=grade_two.id_calificacion).exists() is False


def test_bulk_delete_grades_reports_invalid_ids(monkeypatch):
    school = _mk_school(8109, 'Colegio Bulk Grade Invalid')
    teacher = _mk_user('teacher-bulk-grade-invalid@test.cl', 'Profesor', school.rbd, '50000106-6')
    student = _mk_user('student-bulk-grade-invalid@test.cl', 'Estudiante', school.rbd, '50000107-7')
    clase = _mk_class_graph(school, teacher)

    evaluation = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval Grade Invalid',
        fecha_evaluacion=dt.date(2026, 3, 13),
        activa=True,
    )
    grade = Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluation,
        estudiante=student,
        nota=5.2,
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_DELETE'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/profesor/calificaciones/bulk-delete/',
        {'ids': [grade.id_calificacion, 'abc']},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] == 1
    assert payload['failed'] == 1
    assert 'abc' in payload['failed_ids']


def test_teacher_attendance_list_accepts_mobile_limit_query_param(monkeypatch):
    school = _mk_school(8111, 'Colegio Mobile Attendance Limit')
    teacher = _mk_user('teacher-mobile-att@test.cl', 'Profesor', school.rbd, '50000111-1')
    student = _mk_user('student-mobile-att@test.cl', 'Estudiante', school.rbd, '50000112-2')
    clase = _mk_class_graph(school, teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date(2026, 3, 14),
        estado='A',
    )
    Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date(2026, 3, 15),
        estado='P',
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'CLASS_VIEW_ATTENDANCE'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get('/api/v1/profesor/asistencias/?limit=1')

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 2
    assert len(payload['results']) == 1


def test_teacher_grades_list_accepts_mobile_limit_query_param(monkeypatch):
    school = _mk_school(8112, 'Colegio Mobile Grades Limit')
    teacher = _mk_user('teacher-mobile-grade@test.cl', 'Profesor', school.rbd, '50000113-3')
    student_one = _mk_user('student-mobile-grade-1@test.cl', 'Estudiante', school.rbd, '50000114-4')
    student_two = _mk_user('student-mobile-grade-2@test.cl', 'Estudiante', school.rbd, '50000115-5')
    clase = _mk_class_graph(school, teacher)

    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval mobile limit',
        fecha_evaluacion=dt.date(2026, 3, 16),
        activa=True,
    )

    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student_one,
        nota=5.5,
        registrado_por=teacher,
        actualizado_por=teacher,
    )
    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student_two,
        nota=6.0,
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_VIEW'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get('/api/v1/profesor/calificaciones/?limit=1')

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 2
    assert len(payload['results']) == 1


def test_teacher_attendance_list_compact_mode_returns_lightweight_rows(monkeypatch):
    school = _mk_school(8113, 'Colegio Mobile Attendance Compact')
    teacher = _mk_user('teacher-mobile-att-compact@test.cl', 'Profesor', school.rbd, '50000116-6')
    student = _mk_user('student-mobile-att-compact@test.cl', 'Estudiante', school.rbd, '50000117-7')
    clase = _mk_class_graph(school, teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date(2026, 3, 17),
        estado='P',
        tipo_asistencia='Presencial',
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'CLASS_VIEW_ATTENDANCE'}})

    client = APIClient()
    client.force_authenticate(user=teacher)

    compact_response = client.get('/api/v1/profesor/asistencias/?compact=1')
    assert compact_response.status_code == 200
    compact_row = compact_response.json()['results'][0]
    assert set(compact_row.keys()) == {'id_asistencia', 'fecha', 'estado'}

    regular_response = client.get('/api/v1/profesor/asistencias/')
    assert regular_response.status_code == 200
    regular_row = regular_response.json()['results'][0]
    assert 'tipo_asistencia' in regular_row
    assert 'estudiante' in regular_row


def test_teacher_grades_list_compact_mode_returns_lightweight_rows(monkeypatch):
    school = _mk_school(8114, 'Colegio Mobile Grades Compact')
    teacher = _mk_user('teacher-mobile-grade-compact@test.cl', 'Profesor', school.rbd, '50000118-8')
    student = _mk_user('student-mobile-grade-compact@test.cl', 'Estudiante', school.rbd, '50000119-9')
    clase = _mk_class_graph(school, teacher)

    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval compact',
        fecha_evaluacion=dt.date(2026, 3, 18),
        activa=True,
    )
    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student,
        nota=6.2,
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_VIEW'}})

    client = APIClient()
    client.force_authenticate(user=teacher)

    compact_response = client.get('/api/v1/profesor/calificaciones/?compact=1')
    assert compact_response.status_code == 200
    compact_row = compact_response.json()['results'][0]
    assert set(compact_row.keys()) == {'id_calificacion', 'evaluacion', 'estudiante', 'nota'}

    regular_response = client.get('/api/v1/profesor/calificaciones/')
    assert regular_response.status_code == 200
    regular_row = regular_response.json()['results'][0]
    assert 'colegio_id' in regular_row
    assert 'estudiante_nombre' in regular_row


def test_teacher_evaluations_list_accepts_mobile_limit_query_param(monkeypatch):
    school = _mk_school(8115, 'Colegio Mobile Evaluations Limit')
    teacher = _mk_user('teacher-mobile-eval@test.cl', 'Profesor', school.rbd, '50000120-0')
    clase = _mk_class_graph(school, teacher)

    Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval 1',
        fecha_evaluacion=dt.date(2026, 3, 19),
        activa=True,
    )
    Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval 2',
        fecha_evaluacion=dt.date(2026, 3, 20),
        activa=True,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_VIEW'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get('/api/v1/profesor/evaluaciones/?limit=1')

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 2
    assert len(payload['results']) == 1


def test_teacher_evaluations_list_compact_mode_returns_lightweight_rows(monkeypatch):
    school = _mk_school(8116, 'Colegio Mobile Evaluations Compact')
    teacher = _mk_user('teacher-mobile-eval-compact@test.cl', 'Profesor', school.rbd, '50000121-1')
    clase = _mk_class_graph(school, teacher)

    Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval compact',
        fecha_evaluacion=dt.date(2026, 3, 21),
        activa=False,
    )

    _configure_capabilities(monkeypatch, {teacher.email: {'GRADE_VIEW'}})

    client = APIClient()
    client.force_authenticate(user=teacher)

    compact_response = client.get('/api/v1/profesor/evaluaciones/?compact=1')
    assert compact_response.status_code == 200
    compact_row = compact_response.json()['results'][0]
    assert set(compact_row.keys()) == {'id_evaluacion', 'clase', 'fecha_evaluacion', 'activa'}

    regular_response = client.get('/api/v1/profesor/evaluaciones/')
    assert regular_response.status_code == 200
    regular_row = regular_response.json()['results'][0]
    assert 'nombre' in regular_row
    assert 'colegio_id' in regular_row
    assert 'tipo_evaluacion' in regular_row


def test_bulk_endpoints_forbid_without_capability(monkeypatch):
    school = _mk_school(8105, 'Colegio Bulk Forbidden')
    admin = _mk_user('admin-no-cap@test.cl', 'Administrador escolar', school.rbd, '50000010-0')
    student = _mk_user('student-no-cap@test.cl', 'Estudiante', school.rbd, '50000011-1')

    _configure_capabilities(monkeypatch, {admin.email: set()})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.post(
        '/api/v1/estudiantes/bulk-deactivate/',
        {'ids': [student.id]},
        format='json',
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    'list_path,bulk_path,view_caps',
    [
        ('/api/v1/estudiantes/', '/api/v1/estudiantes/bulk-deactivate/', {'STUDENT_VIEW'}),
        ('/api/v1/profesor/asistencias/', '/api/v1/profesor/asistencias/bulk-update-state/', {'CLASS_VIEW_ATTENDANCE'}),
        ('/api/v1/profesor/evaluaciones/', '/api/v1/profesor/evaluaciones/bulk-toggle-active/', {'GRADE_VIEW'}),
        ('/api/v1/profesor/calificaciones/', '/api/v1/profesor/calificaciones/bulk-delete/', {'GRADE_VIEW'}),
    ],
)
def test_read_only_user_can_list_but_cannot_run_bulk(monkeypatch, list_path, bulk_path, view_caps):
    school = _mk_school(8110, 'Colegio Bulk ReadOnly')
    admin_read_only = _mk_user(
        'admin-readonly@test.cl',
        'Administrador escolar',
        school.rbd,
        '50000012-2',
    )

    teacher = _mk_user('teacher-readonly-seed@test.cl', 'Profesor', school.rbd, '50000013-3')
    student = _mk_user('student-readonly-seed@test.cl', 'Estudiante', school.rbd, '50000014-4')
    clase = _mk_class_graph(school, teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    asistencia = Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date(2026, 3, 10),
        estado='A',
    )
    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Eval ReadOnly',
        fecha_evaluacion=dt.date(2026, 3, 11),
        activa=True,
    )
    calificacion = Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student,
        nota=5.0,
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    _configure_capabilities(monkeypatch, {admin_read_only.email: view_caps})

    client = APIClient()
    client.force_authenticate(user=admin_read_only)

    list_response = client.get(list_path)
    assert list_response.status_code == 200

    payload_by_bulk_path = {
        '/api/v1/estudiantes/bulk-deactivate/': {'ids': [student.id]},
        '/api/v1/profesor/asistencias/bulk-update-state/': {'ids': [asistencia.id_asistencia], 'estado': 'P'},
        '/api/v1/profesor/evaluaciones/bulk-toggle-active/': {'ids': [evaluacion.id_evaluacion], 'activa': False},
        '/api/v1/profesor/calificaciones/bulk-delete/': {'ids': [calificacion.id_calificacion]},
    }
    bulk_response = client.post(bulk_path, payload_by_bulk_path[bulk_path], format='json')
    assert bulk_response.status_code == 403

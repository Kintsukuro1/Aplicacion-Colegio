import datetime as dt

import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User
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


def test_teacher_classes_list_is_scoped_to_own_classes(monkeypatch):
    school = _mk_school(8001, 'Colegio Uno')
    nivel = NivelEducativo.objects.create(nombre='Basica API')

    curso = Curso.objects.create(colegio=school, nombre='5A', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Matematica')

    teacher_one = _mk_user('teacher1@test.cl', 'Profesor', school.rbd, '55555555-5')
    teacher_two = _mk_user('teacher2@test.cl', 'Profesor', school.rbd, '66666666-6')

    clase_one = Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=teacher_one,
    )
    Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=teacher_two,
    )

    _configure_capabilities(
        monkeypatch,
        {
            teacher_one.email: {'CLASS_VIEW'},
            teacher_two.email: {'CLASS_VIEW'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=teacher_one)
    response = client.get('/api/v1/profesor/clases/')

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 1
    assert payload['results'][0]['id'] == clase_one.id


def test_teacher_classes_list_accepts_mobile_limit_query_param(monkeypatch):
    school = _mk_school(8004, 'Colegio Clases Limit')
    nivel = NivelEducativo.objects.create(nombre='Media Limit')
    curso = Curso.objects.create(colegio=school, nombre='3A', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Lenguaje')
    teacher = _mk_user('teacher-limit-class@test.cl', 'Profesor', school.rbd, '57575757-5')

    Clase.objects.create(colegio=school, curso=curso, asignatura=asignatura, profesor=teacher)
    Clase.objects.create(colegio=school, curso=curso, asignatura=asignatura, profesor=teacher)

    _configure_capabilities(monkeypatch, {teacher.email: {'CLASS_VIEW'}})

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get('/api/v1/profesor/clases/?limit=1')

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 2
    assert len(payload['results']) == 1


def test_teacher_classes_list_compact_mode_returns_lightweight_rows(monkeypatch):
    school = _mk_school(8005, 'Colegio Clases Compact')
    nivel = NivelEducativo.objects.create(nombre='Media Compact')
    curso = Curso.objects.create(colegio=school, nombre='4A', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Ciencias')
    teacher = _mk_user('teacher-compact-class@test.cl', 'Profesor', school.rbd, '58585858-5')

    Clase.objects.create(colegio=school, curso=curso, asignatura=asignatura, profesor=teacher)

    _configure_capabilities(monkeypatch, {teacher.email: {'CLASS_VIEW'}})

    client = APIClient()
    client.force_authenticate(user=teacher)

    compact_response = client.get('/api/v1/profesor/clases/?compact=1')
    assert compact_response.status_code == 200
    compact_row = compact_response.json()['results'][0]
    assert set(compact_row.keys()) == {'id', 'curso_id', 'asignatura_id', 'activo'}

    regular_response = client.get('/api/v1/profesor/clases/')
    assert regular_response.status_code == 200
    regular_row = regular_response.json()['results'][0]
    assert 'curso_nombre' in regular_row
    assert 'asignatura_nombre' in regular_row
    assert 'total_estudiantes' in regular_row


def test_teacher_can_create_attendance_for_own_class(monkeypatch):
    school = _mk_school(8002, 'Colegio Dos')
    nivel = NivelEducativo.objects.create(nombre='Media API')

    curso = Curso.objects.create(colegio=school, nombre='2B', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Historia')

    teacher = _mk_user('teacher3@test.cl', 'Profesor', school.rbd, '77777777-7')
    student = _mk_user('student1@test.cl', 'Estudiante', school.rbd, '88888888-8')

    clase = Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=teacher,
    )
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    _configure_capabilities(
        monkeypatch,
        {
            teacher.email: {'CLASS_TAKE_ATTENDANCE', 'CLASS_VIEW_ATTENDANCE'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/profesor/asistencias/',
        {
            'clase': clase.id,
            'estudiante': student.id,
            'fecha': dt.date.today().isoformat(),
            'estado': 'P',
            'tipo_asistencia': 'Presencial',
        },
        format='json',
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['colegio_id'] == school.rbd
    assert payload['estudiante'] == student.id


def test_dashboard_summary_forbidden_without_capabilities(monkeypatch):
    user = _mk_user('user-no-dashboard@test.cl', 'Profesor', 9001, '99999999-9')
    _configure_capabilities(monkeypatch, {user.email: set()})

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get('/api/v1/dashboard/resumen/')

    assert response.status_code == 403


def test_dashboard_summary_self_scope_contract(monkeypatch):
    teacher = _mk_user('user-dashboard-self@test.cl', 'Profesor', 9002, '12121212-1')
    _configure_capabilities(
        monkeypatch,
        {
            teacher.email: {'DASHBOARD_VIEW_SELF'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get('/api/v1/dashboard/resumen/?scope=self')

    assert response.status_code == 200
    payload = response.json()
    assert payload['contract_version'] == '1.0.0'
    assert payload['scope'] == 'self'
    assert 'self' in payload['sections']
    assert payload['sections']['self'] is not None
    assert payload['sections']['school'] is None
    assert payload['sections']['analytics'] is None


def test_dashboard_summary_school_scope_contract(monkeypatch):
    admin = _mk_user('user-dashboard-school@test.cl', 'Administrador escolar', 9003, '13131313-1')
    _configure_capabilities(
        monkeypatch,
        {
            admin.email: {'DASHBOARD_VIEW_SCHOOL'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/dashboard/resumen/?scope=school')

    assert response.status_code == 200
    payload = response.json()
    assert payload['scope'] == 'school'
    assert payload['sections']['self'] is None
    assert payload['sections']['school'] is not None
    assert payload['sections']['analytics'] is None
    assert payload['sections']['school']['colegio_id'] == 9003

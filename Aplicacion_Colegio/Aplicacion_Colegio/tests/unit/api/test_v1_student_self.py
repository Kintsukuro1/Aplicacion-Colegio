import datetime as dt

import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import PerfilEstudiante, Role, User
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


def test_student_my_grades_is_scoped_to_authenticated_student(monkeypatch):
    school = _mk_school(9101, 'Colegio API 1')
    nivel = NivelEducativo.objects.create(nombre='Basica API Student')

    curso = Curso.objects.create(colegio=school, nombre='6A', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Lenguaje')
    teacher = _mk_user('teacher4@test.cl', 'Profesor', school.rbd, '11111111-9')
    student_one = _mk_user('student-a@test.cl', 'Estudiante', school.rbd, '22222222-9')
    student_two = _mk_user('student-b@test.cl', 'Estudiante', school.rbd, '33333333-9')

    clase = Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=teacher,
    )

    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Prueba 1',
        fecha_evaluacion=dt.date.today(),
    )

    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student_one,
        nota=6.5,
        registrado_por=teacher,
    )
    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student_two,
        nota=4.0,
        registrado_por=teacher,
    )

    _configure_capabilities(
        monkeypatch,
        {
            student_one.email: {'GRADE_VIEW'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=student_one)
    response = client.get('/api/v1/estudiante/mis-notas/')

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]['nota'] == '6.5'


def test_student_my_attendance_is_scoped_to_authenticated_student(monkeypatch):
    school = _mk_school(9102, 'Colegio API 2')
    nivel = NivelEducativo.objects.create(nombre='Media API Student')

    curso = Curso.objects.create(colegio=school, nombre='3B', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Ciencias')
    teacher = _mk_user('teacher5@test.cl', 'Profesor', school.rbd, '44444444-9')
    student_one = _mk_user('student-c@test.cl', 'Estudiante', school.rbd, '55555555-9')
    student_two = _mk_user('student-d@test.cl', 'Estudiante', school.rbd, '66666666-9')

    clase = Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=teacher,
    )
    ClaseEstudiante.objects.create(clase=clase, estudiante=student_one, activo=True)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student_two, activo=True)

    Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student_one,
        fecha=dt.date.today(),
        estado='P',
    )
    Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student_two,
        fecha=dt.date.today(),
        estado='A',
    )

    _configure_capabilities(
        monkeypatch,
        {
            student_one.email: {'CLASS_VIEW_ATTENDANCE'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=student_one)
    response = client.get('/api/v1/estudiante/mi-asistencia/')

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]['estado'] == 'P'


def test_student_my_profile_requires_dashboard_capability(monkeypatch):
    student = _mk_user('student-no-cap@test.cl', 'Estudiante', 9199, '77777777-9')
    PerfilEstudiante.objects.create(user=student, estado_academico='Activo')

    _configure_capabilities(monkeypatch, {student.email: set()})

    client = APIClient()
    client.force_authenticate(user=student)
    response = client.get('/api/v1/estudiante/mi-perfil/')

    assert response.status_code == 403

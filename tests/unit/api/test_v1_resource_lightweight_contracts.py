import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Apoderado, Role, User
from backend.apps.cursos.models import Asignatura, Curso
from backend.apps.institucion.models import CicloAcademico, Colegio, NivelEducativo
from backend.apps.matriculas.models import Matricula
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


def _mk_school(rbd):
    return Colegio.objects.create(rbd=rbd, rut_establecimiento=f'{rbd}-K', nombre=f'Colegio {rbd}')


def _allow_all_capabilities(monkeypatch):
    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda _u, _c, school_id=None: True))


def test_asignaturas_list_is_lightweight_and_detail_is_full(monkeypatch):
    _allow_all_capabilities(monkeypatch)
    school = _mk_school(7201)
    user = _mk_user('light-asig@test.cl', 'Administrador escolar', school.rbd, '72000001-1')
    asignatura = Asignatura.objects.create(colegio=school, nombre='Matematica', codigo='MAT', activa=True)

    client = APIClient()
    client.force_authenticate(user=user)

    list_resp = client.get('/api/v1/asignaturas/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/asignaturas/{asignatura.id_asignatura}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'codigo' in detail
    assert detail['nombre'] == 'Matematica'


def test_ciclos_list_is_lightweight_and_detail_is_full(monkeypatch):
    _allow_all_capabilities(monkeypatch)
    school = _mk_school(7202)
    user = _mk_user('light-ciclo@test.cl', 'Administrador escolar', school.rbd, '72000002-2')
    ciclo = CicloAcademico.objects.create(
        colegio=school,
        nombre='Ciclo 2026',
        fecha_inicio='2026-03-01',
        fecha_fin='2026-12-20',
        estado='ACTIVO',
        periodos_config={},
        creado_por=user,
        modificado_por=user,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    list_resp = client.get('/api/v1/ciclos-academicos/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/ciclos-academicos/{ciclo.id}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'fecha_inicio' in detail
    assert detail['nombre'] == 'Ciclo 2026'


def test_matriculas_list_is_lightweight_and_detail_is_full(monkeypatch):
    _allow_all_capabilities(monkeypatch)
    school = _mk_school(7203)
    admin = _mk_user('light-mat-admin@test.cl', 'Administrador escolar', school.rbd, '72000003-3')
    student = _mk_user('light-mat-student@test.cl', 'Estudiante', school.rbd, '72000004-4')

    nivel = NivelEducativo.objects.create(nombre='Nivel 7203')
    ciclo = CicloAcademico.objects.create(
        colegio=school,
        nombre='Ciclo 7203',
        fecha_inicio='2026-03-01',
        fecha_fin='2026-12-20',
        estado='ACTIVO',
        periodos_config={},
        creado_por=admin,
        modificado_por=admin,
    )
    curso = Curso.objects.create(colegio=school, nombre='6A', nivel=nivel, ciclo_academico=ciclo, activo=True)
    matricula = Matricula.objects.create(
        estudiante=student,
        colegio=school,
        curso=curso,
        ciclo_academico=ciclo,
        estado='ACTIVA',
    )

    client = APIClient()
    client.force_authenticate(user=admin)

    list_resp = client.get('/api/v1/matriculas/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/matriculas/{matricula.id}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'estudiante' in detail
    assert detail['estado'] == 'ACTIVA'


def test_apoderados_list_is_lightweight_and_detail_is_full(monkeypatch):
    _allow_all_capabilities(monkeypatch)
    school = _mk_school(7204)
    admin = _mk_user('light-apo-admin@test.cl', 'Administrador escolar', school.rbd, '72000005-5')
    guardian_user = _mk_user('light-apo-user@test.cl', 'Apoderado', school.rbd, '72000006-6')
    apoderado = Apoderado.objects.create(user=guardian_user, activo=True)

    client = APIClient()
    client.force_authenticate(user=admin)

    list_resp = client.get('/api/v1/apoderados/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/apoderados/{apoderado.id}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'email' in detail
    assert detail['email'] == guardian_user.email

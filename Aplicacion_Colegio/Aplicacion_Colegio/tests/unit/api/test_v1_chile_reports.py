import datetime as dt
import json

import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User
from backend.apps.academico.models import Asistencia
from backend.apps.cursos.models import Asignatura, Clase, Curso
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


def _mk_school(rbd, name):
    return Colegio.objects.create(rbd=rbd, nombre=name, rut_establecimiento=f'{rbd}-K')


def _configure_capabilities(monkeypatch, capability_by_email):
    def _fake_has_capability(user, capability, school_id=None):
        allowed = capability_by_email.get(user.email, set())
        return capability in allowed

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(_fake_has_capability))


def _mk_base_class(school, teacher):
    nivel = NivelEducativo.objects.create(nombre=f'Nivel {school.rbd}')
    curso = Curso.objects.create(colegio=school, nombre=f'Curso {school.rbd}', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre=f'Asignatura {school.rbd}')
    return Clase.objects.create(colegio=school, curso=curso, asignatura=asignatura, profesor=teacher)


def _mk_ciclo(school, admin_user):
    return CicloAcademico.objects.create(
        colegio=school,
        nombre=f'Ciclo {school.rbd}',
        fecha_inicio=dt.date(2026, 3, 1),
        fecha_fin=dt.date(2026, 12, 31),
        estado='ACTIVO',
        creado_por=admin_user,
        modificado_por=admin_user,
    )


def test_ministerial_monthly_report_requires_capability(monkeypatch):
    school = _mk_school(9101, 'Colegio Reportes')
    user = _mk_user('sin-cap-report@test.cl', 'Administrador escolar', school.rbd, '91919191-1')
    _configure_capabilities(monkeypatch, {user.email: set()})

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get('/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03')

    assert response.status_code == 403


def test_ministerial_monthly_report_returns_attendance_and_enrollment_summary(monkeypatch):
    school = _mk_school(9102, 'Colegio Resumen Mensual')
    admin = _mk_user('admin-report@test.cl', 'Administrador escolar', school.rbd, '92929292-2')
    teacher = _mk_user('teacher-report@test.cl', 'Profesor', school.rbd, '93939393-3')
    student = _mk_user('student-report@test.cl', 'Estudiante', school.rbd, '94949494-4')

    clase = _mk_base_class(school, teacher)
    ciclo = _mk_ciclo(school, admin)

    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha=dt.date(2026, 3, 10), estado='P')
    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha=dt.date(2026, 3, 11), estado='A')
    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha=dt.date(2026, 3, 12), estado='J')

    Matricula.objects.create(
        estudiante=student,
        colegio=school,
        curso=clase.curso,
        ciclo_academico=ciclo,
        estado='ACTIVA',
    )
    Matricula.objects.create(
        estudiante=teacher,
        colegio=school,
        curso=clase.curso,
        ciclo_academico=ciclo,
        estado='RETIRADA',
    )

    _configure_capabilities(monkeypatch, {admin.email: {'REPORT_VIEW_BASIC'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03')

    assert response.status_code == 200
    payload = response.json()
    assert payload['contract_version'] == '1.0.0'
    assert payload['month'] == '2026-03'
    assert payload['colegio_id'] == school.rbd
    assert payload['asistencia']['total_registros'] == 3
    assert payload['asistencia']['presentes'] == 1
    assert payload['asistencia']['ausentes'] == 1
    assert payload['asistencia']['justificadas'] == 1
    assert payload['asistencia']['tasa_presentismo'] == 33.33
    assert payload['matricula']['total'] == 2
    assert payload['matricula']['activas'] == 1
    assert payload['matricula']['retiradas'] == 1


def test_ministerial_monthly_report_rejects_invalid_month(monkeypatch):
    school = _mk_school(9103, 'Colegio Mes Invalido')
    admin = _mk_user('admin-invalid-month@test.cl', 'Administrador escolar', school.rbd, '95959595-5')
    _configure_capabilities(monkeypatch, {admin.email: {'REPORT_VIEW_BASIC'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-13')

    assert response.status_code == 400
    assert 'month' in response.json()


def test_ministerial_monthly_report_blocks_non_admin_cross_school_access(monkeypatch):
    school_a = _mk_school(9104, 'Colegio A')
    school_b = _mk_school(9105, 'Colegio B')
    admin_a = _mk_user('admin-a@test.cl', 'Administrador escolar', school_a.rbd, '96969696-6')

    _configure_capabilities(monkeypatch, {admin_a.email: {'REPORT_VIEW_BASIC'}})

    client = APIClient()
    client.force_authenticate(user=admin_a)
    response = client.get(f'/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03&colegio_id={school_b.rbd}')

    assert response.status_code == 403


def test_ministerial_monthly_report_allows_global_admin_cross_school_access(monkeypatch):
    school_a = _mk_school(9106, 'Colegio Global A')
    school_b = _mk_school(9107, 'Colegio Global B')
    super_admin = _mk_user('global-admin@test.cl', 'Admin', school_a.rbd, '97979797-7')
    teacher = _mk_user('teacher-global@test.cl', 'Profesor', school_b.rbd, '98989898-8')
    student = _mk_user('student-global@test.cl', 'Estudiante', school_b.rbd, '99999999-9')

    clase_b = _mk_base_class(school_b, teacher)
    Asistencia.objects.create(colegio=school_b, clase=clase_b, estudiante=student, fecha=dt.date(2026, 3, 18), estado='P')

    _configure_capabilities(monkeypatch, {super_admin.email: {'SYSTEM_ADMIN'}})

    client = APIClient()
    client.force_authenticate(user=super_admin)
    response = client.get(f'/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03&colegio_id={school_b.rbd}')

    assert response.status_code == 200
    payload = response.json()
    assert payload['colegio_id'] == school_b.rbd
    assert payload['asistencia']['total_registros'] == 1


def test_ministerial_monthly_report_csv_export_returns_attachment(monkeypatch):
    school = _mk_school(9108, 'Colegio Export CSV')
    admin = _mk_user('admin-csv@test.cl', 'Administrador escolar', school.rbd, '91919192-2')
    teacher = _mk_user('teacher-csv@test.cl', 'Profesor', school.rbd, '91919193-3')
    student = _mk_user('student-csv@test.cl', 'Estudiante', school.rbd, '91919194-4')
    clase = _mk_base_class(school, teacher)
    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha=dt.date(2026, 3, 19), estado='P')

    _configure_capabilities(monkeypatch, {admin.email: {'REPORT_VIEW_BASIC'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03&export=csv')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')
    assert '.csv' in response['Content-Disposition']
    csv_text = response.content.decode('utf-8')
    assert 'reporte,mes,colegio_id' in csv_text
    assert 'ministerial_monthly,2026-03' in csv_text


def test_ministerial_monthly_report_xlsx_export_returns_attachment(monkeypatch):
    school = _mk_school(9109, 'Colegio Export XLSX')
    admin = _mk_user('admin-xlsx@test.cl', 'Administrador escolar', school.rbd, '92929293-3')
    teacher = _mk_user('teacher-xlsx@test.cl', 'Profesor', school.rbd, '92929294-4')
    student = _mk_user('student-xlsx@test.cl', 'Estudiante', school.rbd, '92929295-5')
    clase = _mk_base_class(school, teacher)
    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha=dt.date(2026, 3, 20), estado='A')

    _configure_capabilities(monkeypatch, {admin.email: {'REPORT_VIEW_BASIC'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03&export=xlsx')

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert '.xlsx' in response['Content-Disposition']
    assert response.content.startswith(b'PK')


def test_ministerial_monthly_report_rejects_invalid_export_format(monkeypatch):
    school = _mk_school(9110, 'Colegio Export Invalido')
    admin = _mk_user('admin-export-invalid@test.cl', 'Administrador escolar', school.rbd, '93939393-6')
    _configure_capabilities(monkeypatch, {admin.email: {'REPORT_VIEW_BASIC'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03&export=pdf')

    assert response.status_code == 400
    assert 'format' in response.json()


def test_ministerial_monthly_report_sige_export_returns_attachment(monkeypatch):
    school = _mk_school(9111, 'Colegio Export SIGE')
    admin = _mk_user('admin-sige@test.cl', 'Administrador escolar', school.rbd, '94949494-7')
    teacher = _mk_user('teacher-sige@test.cl', 'Profesor', school.rbd, '94949495-8')
    student = _mk_user('student-sige@test.cl', 'Estudiante', school.rbd, '94949496-9')
    clase = _mk_base_class(school, teacher)
    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha=dt.date(2026, 3, 21), estado='P')

    _configure_capabilities(monkeypatch, {admin.email: {'REPORT_VIEW_BASIC'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/reportes/ministeriales/resumen-mensual/?month=2026-03&export=sige')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/json')
    assert '_sige.json' in response['Content-Disposition']

    payload = json.loads(response.content.decode('utf-8'))
    assert payload['adapter'] == 'sige_ministerial_monthly'
    assert payload['adapter_version'] == '1.0.0'
    assert payload['month'] == '2026-03'
    assert payload['colegio_id'] == school.rbd
    assert payload['attendance_summary']['total_records'] == 1

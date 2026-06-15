import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User
from backend.apps.comunicados.models import Comunicado
from backend.apps.core.models import AnotacionConvivencia, JustificativoInasistencia
from backend.apps.cursos.models import Curso
from backend.apps.institucion.models import CicloAcademico, Colegio, NivelEducativo
from backend.apps.matriculas.models import Cuota, EstadoCuenta, Matricula, Pago
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


def _mk_finance_context(school, admin_user, student):
    nivel = NivelEducativo.objects.create(nombre=f'Nivel {school.rbd}')
    ciclo = CicloAcademico.objects.create(
        colegio=school,
        nombre=f'Ciclo {school.rbd}',
        fecha_inicio='2026-03-01',
        fecha_fin='2026-12-20',
        estado='ACTIVO',
        periodos_config={},
        creado_por=admin_user,
        modificado_por=admin_user,
    )
    curso = Curso.objects.create(
        colegio=school,
        nombre='5A',
        nivel=nivel,
        ciclo_academico=ciclo,
        activo=True,
    )
    matricula = Matricula.objects.create(
        estudiante=student,
        colegio=school,
        curso=curso,
        ciclo_academico=ciclo,
        estado='ACTIVA',
    )
    cuota = Cuota.objects.create(
        matricula=matricula,
        numero_cuota=1,
        mes=3,
        anio=2026,
        monto_original=10000,
        monto_descuento=0,
        monto_final=10000,
        monto_pagado=0,
        fecha_vencimiento='2026-03-31',
        estado='PENDIENTE',
    )
    return cuota


def _allow_all_capabilities(monkeypatch):
    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda _u, _c, school_id=None: True))


def test_comunicados_list_is_lightweight_and_retrieve_is_detail(monkeypatch):
    _allow_all_capabilities(monkeypatch)

    school = _mk_school(7101)
    user = _mk_user('light-com@test.cl', 'Administrador escolar', school.rbd, '71000001-1')
    comunicado = Comunicado.objects.create(
        colegio=school,
        tipo='comunicado',
        titulo='Titulo corto',
        contenido='Contenido completo comunicado',
        destinatario='todos',
        publicado_por=user,
        activo=True,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    list_resp = client.get('/api/v1/comunicados/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/comunicados/{comunicado.id_comunicado}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'contenido' in detail
    assert detail['titulo'] == 'Titulo corto'


def test_justificativos_list_is_lightweight_and_retrieve_is_detail(monkeypatch):
    _allow_all_capabilities(monkeypatch)

    school = _mk_school(7102)
    user = _mk_user('light-jus@test.cl', 'Inspector convivencia escolar', school.rbd, '71000002-2')
    student = _mk_user('student-jus@test.cl', 'Estudiante', school.rbd, '71000003-3')
    justificativo = JustificativoInasistencia.objects.create(
        estudiante=student,
        colegio=school,
        fecha_ausencia='2026-03-02',
        motivo='Control',
        tipo='MEDICO',
        presentado_por=user,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    list_resp = client.get('/api/v1/justificativos/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/justificativos/{justificativo.id_justificativo}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'motivo' in detail
    assert detail['tipo'] == 'MEDICO'


def test_estado_cuenta_list_is_lightweight_and_retrieve_is_detail(monkeypatch):
    _allow_all_capabilities(monkeypatch)

    school = _mk_school(7103)
    user = _mk_user('light-fin@test.cl', 'Asesor financiero', school.rbd, '71000004-4')
    student = _mk_user('student-fin@test.cl', 'Estudiante', school.rbd, '71000005-5')
    estado = EstadoCuenta.objects.create(
        estudiante=student,
        colegio=school,
        mes=3,
        anio=2026,
        total_deuda=10000,
        total_pagado=0,
        saldo_pendiente=10000,
        estado='GENERADO',
    )

    client = APIClient()
    client.force_authenticate(user=user)

    list_resp = client.get('/api/v1/finanzas/estados-cuenta/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/finanzas/estados-cuenta/{estado.id}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'saldo_pendiente' in detail
    assert detail['estado'] == 'GENERADO'


def test_anotaciones_list_is_lightweight_and_retrieve_is_detail(monkeypatch):
    _allow_all_capabilities(monkeypatch)

    school = _mk_school(7104)
    inspector = _mk_user('light-anot@test.cl', 'Inspector convivencia escolar', school.rbd, '71000006-6')
    student = _mk_user('student-anot@test.cl', 'Estudiante', school.rbd, '71000007-7')
    anotacion = AnotacionConvivencia.objects.create(
        estudiante=student,
        colegio=school,
        tipo='NEUTRA',
        categoria='COMPORTAMIENTO',
        descripcion='Registro convivencia.',
        gravedad=1,
        registrado_por=inspector,
    )

    client = APIClient()
    client.force_authenticate(user=inspector)

    list_resp = client.get('/api/v1/convivencia/anotaciones/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/convivencia/anotaciones/{anotacion.id_anotacion}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'descripcion' in detail
    assert detail['tipo'] == 'NEUTRA'


def test_pagos_list_is_lightweight_and_retrieve_is_detail(monkeypatch):
    _allow_all_capabilities(monkeypatch)

    school = _mk_school(7105)
    finance_user = _mk_user('light-pago@test.cl', 'Asesor financiero', school.rbd, '71000008-8')
    student = _mk_user('student-pago@test.cl', 'Estudiante', school.rbd, '71000009-9')
    cuota = _mk_finance_context(school, finance_user, student)
    pago = Pago.objects.create(
        cuota=cuota,
        estudiante=student,
        monto=5000,
        metodo_pago='EFECTIVO',
        estado='APROBADO',
        procesado_por=finance_user,
    )

    client = APIClient()
    client.force_authenticate(user=finance_user)

    list_resp = client.get('/api/v1/finanzas/pagos/')
    assert list_resp.status_code == 200
    row = list_resp.json()['results'][0]
    assert set(row.keys()) == {'id', 'nombre', 'estado'}

    detail_resp = client.get(f'/api/v1/finanzas/pagos/{pago.id}/')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert 'metodo_pago' in detail
    assert detail['estado'] == 'APROBADO'

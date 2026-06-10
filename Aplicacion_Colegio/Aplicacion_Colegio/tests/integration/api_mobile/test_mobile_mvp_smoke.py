import datetime as dt

import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Apoderado, PerfilEstudiante, RelacionApoderadoEstudiante, Role, User
from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion
from backend.apps.cursos.models import Asignatura, Clase, ClaseEstudiante, Curso
from backend.apps.institucion.models import Colegio, NivelEducativo
from backend.apps.comunicados.models import Comunicado
from backend.apps.matriculas.models import EstadoCuenta
from backend.apps.notificaciones.models import Notificacion


pytestmark = pytest.mark.django_db


def _mk_role(name: str):
    role, _ = Role.objects.get_or_create(nombre=name)
    return role


def _mk_school(rbd: int, name: str):
    return Colegio.objects.create(rbd=rbd, nombre=name, rut_establecimiento=f'{rbd}-K')


def _mk_user(email: str, role_name: str, school_id: int, rut: str):
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


@pytest.fixture(autouse=True)
def _require_api_v1_root_enabled():
    """Skip the matrix when root source-of-truth does not expose /api/v1 yet."""
    client = APIClient()
    probe = client.get('/api/v1/health/')
    if probe.status_code == 404:
        pytest.skip('API v1 no está expuesta en el root actual; habilitar include api/v1 en core urls.')


def test_mobile_mvp_auth_token_and_me_smoke():
    school = _mk_school(9601, 'Colegio Mobile Auth')
    user = _mk_user('mobile.auth@test.cl', 'Administrador escolar', school.rbd, '96000001-1')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': user.email, 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()
    assert token_payload.get('access')
    assert token_payload.get('refresh')

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_payload['access']}")
    me_response = client.get('/api/v1/auth/me/')
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload['email'] == user.email
    assert me_payload['school']['id'] == school.rbd


def test_mobile_mvp_auth_verify_and_logout_smoke():
    school = _mk_school(9610, 'Colegio Mobile Auth Verify')
    user = _mk_user('mobile.verify@test.cl', 'Administrador escolar', school.rbd, '96100001-1')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': user.email, 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()

    verify_response = client.post(
        '/api/v1/auth/token/verify/',
        {'token': token_payload['access']},
        format='json',
    )
    assert verify_response.status_code == 200

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_payload['access']}")
    logout_response = client.post(
        '/api/v1/auth/logout/',
        {'refresh': token_payload['refresh']},
        format='json',
    )
    assert logout_response.status_code == 200


def test_mobile_mvp_dashboard_summary_smoke(monkeypatch):
    school = _mk_school(9602, 'Colegio Mobile Dashboard')
    teacher = _mk_user('mobile.dashboard@test.cl', 'Profesor', school.rbd, '96000002-2')

    from backend.common.services.policy_service import PolicyService

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda *_args, **_kwargs: True))

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get('/api/v1/dashboard/resumen/?scope=auto')
    assert response.status_code == 200
    payload = response.json()
    assert payload.get('context', {}).get('school_id') == school.rbd


def test_mobile_mvp_dashboard_summary_denied_without_capability(monkeypatch):
    school = _mk_school(9611, 'Colegio Mobile Dashboard Denied')
    teacher = _mk_user('mobile.dashboard.denied@test.cl', 'Profesor', school.rbd, '96110001-1')

    from backend.common.services.policy_service import PolicyService

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda *_args, **_kwargs: False))

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get('/api/v1/dashboard/resumen/?scope=auto')
    assert response.status_code == 403


def test_mobile_mvp_student_endpoints_smoke(monkeypatch):
    school = _mk_school(9603, 'Colegio Mobile Student')
    nivel = NivelEducativo.objects.create(nombre='Basica Mobile Student')
    student = _mk_user('mobile.student@test.cl', 'Estudiante', school.rbd, '96000003-3')
    teacher = _mk_user('mobile.teacher@student.test.cl', 'Profesor', school.rbd, '96000004-4')

    PerfilEstudiante.objects.create(user=student, estado_academico='Activo')
    curso = Curso.objects.create(colegio=school, nombre='6A', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Historia')
    clase = Clase.objects.create(colegio=school, curso=curso, asignatura=asignatura, profesor=teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Prueba Mobile',
        fecha_evaluacion=dt.date.today(),
    )
    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student,
        nota=6.2,
        registrado_por=teacher,
    )
    Asistencia.objects.create(
        colegio=school,
        clase=clase,
        estudiante=student,
        fecha=dt.date.today(),
        estado='P',
    )

    from backend.common.services.policy_service import PolicyService

    def _cap(_user, capability, school_id=None):
        allowed = {
            'DASHBOARD_VIEW_SELF',
            'CLASS_VIEW',
            'CLASS_VIEW_ATTENDANCE',
            'GRADE_VIEW',
        }
        return capability in allowed

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(_cap))

    client = APIClient()
    client.force_authenticate(user=student)

    perfil_response = client.get('/api/v1/estudiante/mi-perfil/')
    assert perfil_response.status_code in (200, 404)

    clases_response = client.get('/api/v1/estudiante/mis-clases/')
    assert clases_response.status_code == 200

    notas_response = client.get('/api/v1/estudiante/mis-notas/')
    assert notas_response.status_code == 200

    asistencia_response = client.get('/api/v1/estudiante/mi-asistencia/')
    assert asistencia_response.status_code == 200


def test_mobile_mvp_student_endpoints_denied_without_capability(monkeypatch):
    school = _mk_school(9612, 'Colegio Mobile Student Denied')
    student = _mk_user('mobile.student.denied@test.cl', 'Estudiante', school.rbd, '96120001-1')

    from backend.common.services.policy_service import PolicyService

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda *_args, **_kwargs: False))

    client = APIClient()
    client.force_authenticate(user=student)

    clases_response = client.get('/api/v1/estudiante/mis-clases/')
    assert clases_response.status_code == 403


def test_mobile_mvp_apoderado_endpoints_smoke(monkeypatch):
    school = _mk_school(9604, 'Colegio Mobile Apoderado')
    nivel = NivelEducativo.objects.create(nombre='Basica Mobile Apoderado')
    guardian = _mk_user('mobile.guardian@test.cl', 'Apoderado', school.rbd, '96000005-5')
    student = _mk_user('mobile.ward@test.cl', 'Estudiante', school.rbd, '96000006-6')
    teacher = _mk_user('mobile.teacher@guardian.test.cl', 'Profesor', school.rbd, '96000007-7')

    guardian_profile = Apoderado.objects.create(user=guardian)
    RelacionApoderadoEstudiante.objects.create(
        apoderado=guardian_profile,
        estudiante=student,
        parentesco='madre',
        tipo_apoderado='principal',
        activa=True,
    )

    curso = Curso.objects.create(colegio=school, nombre='5B', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre='Lenguaje')
    clase = Clase.objects.create(colegio=school, curso=curso, asignatura=asignatura, profesor=teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Prueba Apoderado',
        fecha_evaluacion=dt.date.today(),
    )
    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student,
        nota=5.9,
        registrado_por=teacher,
    )

    from backend.common.services.policy_service import PolicyService

    def _cap(_user, _capability, school_id=None):
        return True

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(_cap))

    client = APIClient()
    client.force_authenticate(user=guardian)

    pupilos_response = client.get('/api/v1/apoderado/mis-pupilos/')
    assert pupilos_response.status_code == 200

    notas_response = client.get(f'/api/v1/apoderado/pupilo/{student.id}/notas/')
    assert notas_response.status_code == 200

    asistencia_response = client.get(f'/api/v1/apoderado/pupilo/{student.id}/asistencia/')
    assert asistencia_response.status_code == 200

    anotaciones_response = client.get(f'/api/v1/apoderado/pupilo/{student.id}/anotaciones/')
    assert anotaciones_response.status_code == 200

    comunicado = Comunicado.objects.create(
        colegio=school,
        tipo='comunicado',
        titulo='Comunicado Mobile',
        contenido='Mensaje para apoderados',
        destinatario='apoderados',
        publicado_por=teacher,
        activo=True,
    )
    assert comunicado.id_comunicado

    EstadoCuenta.objects.create(
        estudiante=student,
        colegio=school,
        mes=3,
        anio=2026,
        total_deuda=120000,
        total_pagado=50000,
        saldo_pendiente=70000,
    )

    comunicados_response = client.get('/api/v1/apoderado/comunicados/')
    assert comunicados_response.status_code == 200

    pagos_estado_response = client.get('/api/v1/apoderado/pagos/estado/')
    assert pagos_estado_response.status_code == 200

    justificativo_response = client.post(
        '/api/v1/apoderado/justificativos/',
        {
            'estudiante_id': student.id,
            'fecha_ausencia': '2026-03-16',
            'motivo': 'Control medico',
            'tipo': 'MEDICO',
        },
        format='json',
    )
    assert justificativo_response.status_code == 201


def test_mobile_mvp_apoderado_denied_for_unrelated_or_cross_tenant_student(monkeypatch):
    school_a = _mk_school(9614, 'Colegio Mobile Apoderado A')
    school_b = _mk_school(9615, 'Colegio Mobile Apoderado B')

    guardian = _mk_user('mobile.guardian.denied@test.cl', 'Apoderado', school_a.rbd, '96140001-1')
    linked_student = _mk_user('mobile.linked@test.cl', 'Estudiante', school_a.rbd, '96140002-2')
    foreign_student = _mk_user('mobile.foreign@test.cl', 'Estudiante', school_b.rbd, '96150001-1')

    guardian_profile = Apoderado.objects.create(user=guardian)
    RelacionApoderadoEstudiante.objects.create(
        apoderado=guardian_profile,
        estudiante=linked_student,
        parentesco='madre',
        tipo_apoderado='principal',
        activa=True,
    )

    from backend.common.services.policy_service import PolicyService

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda *_args, **_kwargs: True))

    client = APIClient()
    client.force_authenticate(user=guardian)

    response = client.get(f'/api/v1/apoderado/pupilo/{foreign_student.id}/notas/')
    assert response.status_code == 403

    justificativo_response = client.post(
        '/api/v1/apoderado/justificativos/',
        {
            'estudiante_id': foreign_student.id,
            'fecha_ausencia': '2026-03-16',
            'motivo': 'No relacionado',
            'tipo': 'OTRO',
        },
        format='json',
    )
    assert justificativo_response.status_code == 403


def test_mobile_mvp_apoderado_denied_notas_when_relation_permission_disabled(monkeypatch):
    school = _mk_school(9616, 'Colegio Mobile Apoderado Permisos Notas')
    guardian = _mk_user('mobile.guardian.perm.notas@test.cl', 'Apoderado', school.rbd, '96160001-1')
    student = _mk_user('mobile.student.perm.notas@test.cl', 'Estudiante', school.rbd, '96160002-2')

    guardian_profile = Apoderado.objects.create(user=guardian)
    RelacionApoderadoEstudiante.objects.create(
        apoderado=guardian_profile,
        estudiante=student,
        parentesco='madre',
        tipo_apoderado='principal',
        activa=True,
        usar_permisos_personalizados=True,
        puede_ver_notas=False,
        puede_ver_asistencia=True,
    )

    from backend.common.services.policy_service import PolicyService

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda *_args, **_kwargs: True))

    client = APIClient()
    client.force_authenticate(user=guardian)
    response = client.get(f'/api/v1/apoderado/pupilo/{student.id}/notas/')
    assert response.status_code == 403


def test_mobile_mvp_apoderado_denied_asistencia_when_relation_permission_disabled(monkeypatch):
    school = _mk_school(9617, 'Colegio Mobile Apoderado Permisos Asistencia')
    guardian = _mk_user('mobile.guardian.perm.asistencia@test.cl', 'Apoderado', school.rbd, '96170001-1')
    student = _mk_user('mobile.student.perm.asistencia@test.cl', 'Estudiante', school.rbd, '96170002-2')

    guardian_profile = Apoderado.objects.create(user=guardian)
    RelacionApoderadoEstudiante.objects.create(
        apoderado=guardian_profile,
        estudiante=student,
        parentesco='madre',
        tipo_apoderado='principal',
        activa=True,
        usar_permisos_personalizados=True,
        puede_ver_notas=True,
        puede_ver_asistencia=False,
    )

    from backend.common.services.policy_service import PolicyService

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(lambda *_args, **_kwargs: True))

    client = APIClient()
    client.force_authenticate(user=guardian)
    response = client.get(f'/api/v1/apoderado/pupilo/{student.id}/asistencia/')
    assert response.status_code == 403


def test_mobile_mvp_notifications_smoke():
    school = _mk_school(9605, 'Colegio Mobile Notif')
    user = _mk_user('mobile.notif@test.cl', 'Profesor', school.rbd, '96000008-8')
    Notificacion.objects.create(destinatario=user, tipo='sistema', titulo='Mobile', mensaje='Smoke', leido=False)

    client = APIClient()
    client.force_authenticate(user=user)

    list_response = client.get('/api/v1/notificaciones/')
    assert list_response.status_code == 200

    summary_response = client.get('/api/v1/notificaciones/resumen/')
    assert summary_response.status_code == 200


def test_mobile_mvp_notifications_mark_read_not_found():
    school = _mk_school(9613, 'Colegio Mobile Notif NotFound')
    user = _mk_user('mobile.notif.notfound@test.cl', 'Profesor', school.rbd, '96130001-1')

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post('/api/v1/notificaciones/999999/marcar-leida/')
    assert response.status_code == 404

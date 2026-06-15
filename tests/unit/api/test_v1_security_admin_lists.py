import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User
from backend.apps.institucion.models import Colegio
from backend.apps.security.models import ActiveSession, PasswordHistory
from backend.apps.api import seguridad_views


pytestmark = pytest.mark.django_db


def _mk_user(email, role_name, school_id, rut):
    role, _ = Role.objects.get_or_create(nombre=role_name)
    return User.objects.create_user(
        email=email,
        password='Test#123456',
        nombre='Nombre',
        apellido_paterno='Apellido',
        rut=rut,
        role=role,
        rbd_colegio=school_id,
        is_active=True,
    )


def _mock_admin_monitoring(monkeypatch, *, is_global):
    monkeypatch.setattr(seguridad_views, '_is_admin', lambda user: True)
    monkeypatch.setattr(
        seguridad_views.SecurityMonitoringService,
        'validate_monitoring_access',
        staticmethod(lambda user: (True, is_global)),
    )


def test_active_sessions_list_is_school_scoped_for_non_global_admin(monkeypatch):
    Colegio.objects.create(rbd=801, nombre='Colegio 801')
    Colegio.objects.create(rbd=802, nombre='Colegio 802')

    admin = _mk_user('admin.scope@test.cl', 'Administrador escolar', 801, '10101010-2')
    user_a = _mk_user('a.scope@test.cl', 'Profesor', 801, '10101011-2')
    user_b = _mk_user('b.scope@test.cl', 'Profesor', 802, '10101012-2')

    ActiveSession.objects.create(user=user_a, token_jti='scope-jti-a', ip_address='10.0.0.1', is_active=True)
    ActiveSession.objects.create(user=user_b, token_jti='scope-jti-b', ip_address='10.0.0.2', is_active=True)

    _mock_admin_monitoring(monkeypatch, is_global=False)

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/seguridad/sesiones-activas/')

    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 1
    assert payload['sesiones'][0]['user_email'] == 'a.scope@test.cl'


def test_active_sessions_list_global_admin_sees_all(monkeypatch):
    Colegio.objects.create(rbd=803, nombre='Colegio 803')
    Colegio.objects.create(rbd=804, nombre='Colegio 804')

    admin = _mk_user('admin.global@test.cl', 'Administrador', 803, '11101010-2')
    user_a = _mk_user('a.global@test.cl', 'Profesor', 803, '11101011-2')
    user_b = _mk_user('b.global@test.cl', 'Profesor', 804, '11101012-2')

    ActiveSession.objects.create(user=user_a, token_jti='global-jti-a', ip_address='10.0.1.1', is_active=True)
    ActiveSession.objects.create(user=user_b, token_jti='global-jti-b', ip_address='10.0.1.2', is_active=True)

    _mock_admin_monitoring(monkeypatch, is_global=True)

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/seguridad/sesiones-activas/')

    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 2


def test_password_history_list_is_school_scoped_for_non_global_admin(monkeypatch):
    Colegio.objects.create(rbd=805, nombre='Colegio 805')
    Colegio.objects.create(rbd=806, nombre='Colegio 806')

    admin = _mk_user('admin.password@test.cl', 'Administrador escolar', 805, '12101010-2')
    user_a = _mk_user('a.password@test.cl', 'Profesor', 805, '12101011-2')
    user_b = _mk_user('b.password@test.cl', 'Profesor', 806, '12101012-2')

    PasswordHistory.objects.create(user=user_a, password_hash='hash-a')
    PasswordHistory.objects.create(user=user_b, password_hash='hash-b')

    _mock_admin_monitoring(monkeypatch, is_global=False)

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/seguridad/password-history/')

    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 1
    assert payload['entries'][0]['user_email'] == 'a.password@test.cl'

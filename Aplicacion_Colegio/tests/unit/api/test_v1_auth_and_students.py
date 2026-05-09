import pytest
from rest_framework.test import APIClient
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken

from backend.apps.api.auth import AuthTokenBurstThrottle, AuthTokenSustainedThrottle, ColegioTokenObtainPairView
from backend.apps.accounts.models import Role, User
from backend.apps.institucion.models import Colegio
from backend.apps.security.models import ActiveSession


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


def test_auth_me_requires_authentication():
    client = APIClient()
    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 401


def test_auth_me_returns_user_context():
    Colegio.objects.create(rbd=123, nombre='Colegio Demo')
    admin = _mk_user('admin1@test.cl', 'Administrador escolar', 123, '11111111-1')
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 200
    payload = response.json()
    assert payload['email'] == 'admin1@test.cl'
    assert payload['rbd_colegio'] == 123
    assert payload['user']['id'] == admin.id
    assert payload['user']['name'] == admin.get_full_name()
    assert payload['user']['email'] == 'admin1@test.cl'
    assert payload['school']['id'] == 123
    assert payload['school']['name'] == 'Colegio Demo'
    assert isinstance(payload['capabilities'], list)


def test_me_alias_returns_same_contract():
    Colegio.objects.create(rbd=321, nombre='Colegio Alias')
    admin = _mk_user('admin.alias@test.cl', 'Administrador escolar', 321, '12121212-1')

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/me/')

    assert response.status_code == 200
    payload = response.json()
    assert payload['email'] == 'admin.alias@test.cl'
    assert payload['user']['role'] == admin.role.nombre
    assert payload['school']['id'] == 321
    assert payload['school']['name'] == 'Colegio Alias'


def test_students_list_is_tenant_scoped_for_non_global_user():
    admin = _mk_user('admin2@test.cl', 'Administrador escolar', 123, '22222222-2')
    _mk_user('est1@test.cl', 'Estudiante', 123, '33333333-3')
    _mk_user('est2@test.cl', 'Estudiante', 456, '44444444-4')

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/estudiantes/')

    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 1
    assert data['results'][0]['id']
    assert data['results'][0]['nombre'] == 'Nombre Apellido'
    assert data['results'][0]['estado'] == 'ACTIVO'
    assert 'email' not in data['results'][0]


def test_students_list_accepts_mobile_limit_query_param():
    admin = _mk_user('admin-limit@test.cl', 'Administrador escolar', 124, '23232323-2')
    for idx in range(12):
        _mk_user(f'est-limit-{idx}@test.cl', 'Estudiante', 124, f'5345345{idx}-{idx}')

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/estudiantes/?limit=5')

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 12
    assert len(payload['results']) == 5


def test_students_list_limit_is_capped_to_max_page_size():
    admin = _mk_user('admin-limit-cap@test.cl', 'Administrador escolar', 125, '24242424-2')
    for idx in range(120):
        _mk_user(f'est-cap-{idx}@test.cl', 'Estudiante', 125, f'6446446{idx}-1')

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/v1/estudiantes/?limit=500')

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 120
    assert len(payload['results']) == 100


def test_jwt_verify_and_logout_endpoints_available():
    user = _mk_user('admin3@test.cl', 'Administrador escolar', 777, '55555555-5')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': 'admin3@test.cl', 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200

    tokens = token_response.json()
    verify_response = client.post('/api/v1/auth/token/verify/', {'token': tokens['access']}, format='json')
    assert verify_response.status_code == 200

    client.force_authenticate(user=user)
    logout_response = client.post('/api/v1/auth/logout/', {'refresh': tokens['refresh']}, format='json')
    assert logout_response.status_code == 200


def test_auth_token_preflight_allows_configured_react_origin():
    client = APIClient(
        HTTP_HOST='localhost',
        HTTP_ORIGIN='http://localhost:5175',
        HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type',
    )

    response = client.options('/api/v1/auth/token/')

    assert response.status_code == 200
    assert response['Access-Control-Allow-Origin'] == 'http://localhost:5175'


def test_logout_rejects_refresh_token_from_other_user():
    user_one = _mk_user('admin4@test.cl', 'Administrador escolar', 700, '66666666-6')
    user_two = _mk_user('admin5@test.cl', 'Administrador escolar', 700, '77777777-7')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': 'admin4@test.cl', 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200
    refresh_one = token_response.json()['refresh']

    client.force_authenticate(user=user_two)
    logout_response = client.post('/api/v1/auth/logout/', {'refresh': refresh_one}, format='json')

    assert logout_response.status_code == 403


def test_refresh_rotates_token_and_old_refresh_is_rejected():
    _mk_user('admin6@test.cl', 'Administrador escolar', 701, '88888888-8')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': 'admin6@test.cl', 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200

    old_refresh = token_response.json()['refresh']
    refresh_response = client.post('/api/v1/auth/token/refresh/', {'refresh': old_refresh}, format='json')
    assert refresh_response.status_code == 200

    rotated_refresh = refresh_response.json().get('refresh')
    assert rotated_refresh
    assert rotated_refresh != old_refresh

    stale_refresh_response = client.post('/api/v1/auth/token/refresh/', {'refresh': old_refresh}, format='json')
    assert stale_refresh_response.status_code in (400, 401)


def test_token_obtain_registers_active_session():
    user = _mk_user('admin10@test.cl', 'Administrador escolar', 705, '12121211-3')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': user.email, 'password': 'Test#123456'},
        format='json',
        HTTP_USER_AGENT='pytest-agent-login',
    )
    assert token_response.status_code == 200

    refresh = token_response.json()['refresh']
    refresh_jti = str(RefreshToken(refresh).get('jti'))

    session = ActiveSession.objects.get(user=user, token_jti=refresh_jti)
    assert session.is_active is True
    assert 'pytest-agent-login' in session.user_agent


def test_token_refresh_rotates_active_session_state():
    user = _mk_user('admin11@test.cl', 'Administrador escolar', 706, '13131311-3')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': user.email, 'password': 'Test#123456'},
        format='json',
        HTTP_USER_AGENT='pytest-agent-initial',
    )
    assert token_response.status_code == 200

    refresh = token_response.json()['refresh']
    old_jti = str(RefreshToken(refresh).get('jti'))
    assert ActiveSession.objects.filter(user=user, token_jti=old_jti, is_active=True).exists()

    refresh_response = client.post(
        '/api/v1/auth/token/refresh/',
        {'refresh': refresh},
        format='json',
        HTTP_USER_AGENT='pytest-agent-refresh',
    )
    assert refresh_response.status_code == 200

    rotated_refresh = refresh_response.json().get('refresh')
    assert rotated_refresh
    new_jti = str(RefreshToken(rotated_refresh).get('jti'))
    assert new_jti != old_jti

    assert ActiveSession.objects.filter(user=user, token_jti=old_jti, is_active=False).exists()
    assert ActiveSession.objects.filter(user=user, token_jti=new_jti, is_active=True).exists()


def test_logout_invalidates_refresh_token_for_next_refresh_attempt():
    user = _mk_user('admin9@test.cl', 'Administrador escolar', 704, '11112222-3')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': 'admin9@test.cl', 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200

    refresh = token_response.json()['refresh']
    client.force_authenticate(user=user)
    logout_response = client.post('/api/v1/auth/logout/', {'refresh': refresh}, format='json')
    assert logout_response.status_code == 200

    refresh_after_logout = client.post('/api/v1/auth/token/refresh/', {'refresh': refresh}, format='json')
    assert refresh_after_logout.status_code in (400, 401)


def test_logout_deactivates_active_session_for_refresh_token():
    user = _mk_user('admin12@test.cl', 'Administrador escolar', 707, '14141411-3')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': user.email, 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200

    refresh = token_response.json()['refresh']
    refresh_jti = str(RefreshToken(refresh).get('jti'))
    assert ActiveSession.objects.filter(user=user, token_jti=refresh_jti, is_active=True).exists()

    client.force_authenticate(user=user)
    logout_response = client.post('/api/v1/auth/logout/', {'refresh': refresh}, format='json')
    assert logout_response.status_code == 200

    assert ActiveSession.objects.filter(user=user, token_jti=refresh_jti, is_active=False).exists()


def test_token_endpoint_declares_auth_throttles():
    assert ColegioTokenObtainPairView.throttle_classes == [AuthTokenBurstThrottle, AuthTokenSustainedThrottle]


@patch('backend.apps.api.auth.AuthApiAuditService.audit_token_obtain')
def test_token_obtain_emits_audit_event(mock_audit_token_obtain):
    _mk_user('admin7@test.cl', 'Administrador escolar', 702, '99999999-9')

    client = APIClient()
    response = client.post(
        '/api/v1/auth/token/',
        {'email': 'admin7@test.cl', 'password': 'Test#123456'},
        format='json',
    )

    assert response.status_code == 200
    mock_audit_token_obtain.assert_called_once()


@patch('backend.apps.api.auth.AuthApiAuditService.audit_logout')
def test_logout_emits_audit_event(mock_audit_logout):
    user = _mk_user('admin8@test.cl', 'Administrador escolar', 703, '10101010-1')

    client = APIClient()
    token_response = client.post(
        '/api/v1/auth/token/',
        {'email': 'admin8@test.cl', 'password': 'Test#123456'},
        format='json',
    )
    assert token_response.status_code == 200

    client.force_authenticate(user=user)
    response = client.post('/api/v1/auth/logout/', {'refresh': token_response.json()['refresh']}, format='json')

    assert response.status_code == 200
    mock_audit_logout.assert_called_once()

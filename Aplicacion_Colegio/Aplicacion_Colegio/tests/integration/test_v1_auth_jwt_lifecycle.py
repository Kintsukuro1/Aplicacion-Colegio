import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User
from backend.apps.institucion.models import Colegio


pytestmark = pytest.mark.django_db


def _mk_role(name: str):
    role, _ = Role.objects.get_or_create(nombre=name)
    return role


def _mk_school(rbd: int) -> Colegio:
    return Colegio.objects.create(
        rbd=rbd,
        rut_establecimiento=f"{rbd}-K",
        nombre=f"Colegio {rbd}",
    )


def _mk_user(email: str, role_name: str, school_rbd: int, rut: str) -> User:
    return User.objects.create_user(
        email=email,
        password='Test#123456',
        nombre='Nombre',
        apellido_paterno='Apellido',
        rut=rut,
        role=_mk_role(role_name),
        rbd_colegio=school_rbd,
        is_active=True,
    )


def test_jwt_lifecycle_login_refresh_logout_and_refresh_rejected():
    school = _mk_school(5701)
    user = _mk_user('jwt.lifecycle@test.cl', 'Administrador escolar', school.rbd, '57000001-1')

    client = APIClient()

    login_response = client.post(
        '/api/v1/auth/token/',
        {'email': user.email, 'password': 'Test#123456'},
        format='json',
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    access = login_payload['access']
    refresh_one = login_payload['refresh']

    refresh_response = client.post(
        '/api/v1/auth/token/refresh/',
        {'refresh': refresh_one},
        format='json',
    )
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    access_rotated = refresh_payload['access']
    refresh_two = refresh_payload['refresh']
    assert refresh_two != refresh_one

    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_rotated}')
    me_response = client.get('/api/v1/me/')
    assert me_response.status_code == 200

    logout_response = client.post('/api/v1/auth/logout/', {'refresh': refresh_two}, format='json')
    assert logout_response.status_code == 200

    refresh_after_logout = client.post(
        '/api/v1/auth/token/refresh/',
        {'refresh': refresh_two},
        format='json',
    )
    assert refresh_after_logout.status_code in (400, 401)

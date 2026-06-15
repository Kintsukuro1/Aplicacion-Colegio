"""Functional auth tests aligned with current routes and auth flow."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from backend.apps.accounts.models import Role

User = get_user_model()


@pytest.fixture
def profesor_user(colegio):
    rol_profesor = Role.objects.create(nombre='Profesor')
    return User.objects.create_user(
        email='prof.auth@test.cl',
        password='AuthPass123!',
        nombre='Profe',
        apellido_paterno='Auth',
        rut='12345678-5',
        role=rol_profesor,
        rbd_colegio=colegio.rbd,
    )


@pytest.mark.django_db
class TestAuthenticationRoutes:
    def test_login_page_loads(self, client):
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200

    def test_staff_login_page_loads(self, client):
        response = client.get(reverse('accounts:login_staff'))
        assert response.status_code == 200

    def test_invalid_credentials_do_not_authenticate(self, client):
        response = client.post(
            reverse('accounts:login'),
            {'username': 'nadie@test.cl', 'password': 'wrong'},
        )
        assert response.status_code == 200
        assert response.wsgi_request.user.is_authenticated is False

    def test_logout_redirects_to_login(self, client, profesor_user):
        client.force_login(profesor_user)
        response = client.get(reverse('accounts:logout'))
        assert response.status_code == 302
        assert reverse('accounts:login') in response.url

    def test_dashboard_requires_authentication(self, client):
        response = client.get(reverse('dashboard'))
        assert response.status_code in [301, 302]

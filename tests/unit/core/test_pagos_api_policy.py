from unittest.mock import patch

import pytest
from django.test import RequestFactory

from backend.apps.accounts.models import Role, User
from backend.apps.core.views.asesor_financiero.pagos_api import listar_pagos


pytestmark = pytest.mark.django_db


def _create_user(email: str, role_name: str, rbd: int, rut: str):
    role, _ = Role.objects.get_or_create(nombre=role_name)
    return User.objects.create_user(
        email=email,
        password='Temp#123456',
        nombre='Nombre',
        apellido_paterno='Apellido',
        rut=rut,
        role=role,
        rbd_colegio=rbd,
        is_active=True,
    )


def test_listar_pagos_requires_finance_capability():
    user = _create_user('finanzas@test.cl', 'Asesor financiero', 123, '44444444-4')
    request = RequestFactory().get('/api/asesor-financiero/pagos/')
    request.user = user

    with patch('backend.apps.core.views.asesor_financiero.pagos_api.PolicyService.has_capability', return_value=False):
        response = listar_pagos(request)

    assert response.status_code == 403
    assert b'Permiso denegado' in response.content

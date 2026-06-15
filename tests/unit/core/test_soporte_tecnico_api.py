import json
from unittest.mock import Mock, patch

import pytest
from django.test import RequestFactory

from backend.apps.accounts.models import Role, User
from backend.apps.core.views.soporte_tecnico.api import reset_password


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


class TestSoporteTecnicoResetPassword:
    def test_reset_password_creates_pending_request_when_no_approval(self):
        requester = _create_user('soporte1@test.cl', 'Soporte técnico escolar', 123, '66666666-6')
        target = _create_user('target1@test.cl', 'Profesor', 123, '77777777-7')
        factory = RequestFactory()
        request = factory.post(
            f'/api/soporte/usuarios/{target.id}/reset_password/',
            data=json.dumps({}),
            content_type='application/json',
        )
        request.user = requester

        pending = Mock(id=42)
        with patch('backend.apps.core.views.soporte_tecnico.api.PolicyService.has_capability', return_value=True), patch(
            'backend.apps.core.views.soporte_tecnico.api.SensitiveActionService.create_request',
            return_value=pending,
        ):
            response = reset_password(request, target.id)

        assert response.status_code == 202
        payload = json.loads(response.content.decode('utf-8'))
        assert payload['requires_approval'] is True
        assert payload['request_id'] == 42

    def test_reset_password_executes_with_approval_request(self):
        approver = _create_user('soporte2@test.cl', 'Soporte técnico escolar', 123, '88888888-8')
        target = _create_user('target2@test.cl', 'Profesor', 123, '99999999-9')
        factory = RequestFactory()
        request = factory.post(
            f'/api/soporte/usuarios/{target.id}/reset_password/',
            data=json.dumps({'approval_request_id': 10, 'new_password': 'NuevaClave#2026'}),
            content_type='application/json',
        )
        request.user = approver

        request_obj = Mock(id=10)
        with patch('backend.apps.core.views.soporte_tecnico.api.PolicyService.has_capability', return_value=True), patch(
            'backend.apps.core.views.soporte_tecnico.api.SensitiveActionService.validate_and_approve_for_execution',
            return_value=request_obj,
        ), patch(
            'backend.apps.core.views.soporte_tecnico.api.SensitiveActionService.mark_request_executed'
        ) as mock_mark_executed:
            response = reset_password(request, target.id)

        target.refresh_from_db()
        assert response.status_code == 200
        assert target.check_password('NuevaClave#2026') is True
        mock_mark_executed.assert_called_once()

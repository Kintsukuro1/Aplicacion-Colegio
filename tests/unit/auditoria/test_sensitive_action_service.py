from unittest.mock import patch

import pytest

from backend.apps.accounts.models import Role, User
from backend.apps.auditoria.services.sensitive_action_service import SensitiveActionService
from backend.common.exceptions import PrerequisiteException


pytestmark = pytest.mark.django_db


def _create_user(email: str, role_name: str, rbd: int, rut: str):
    role, _ = Role.objects.get_or_create(nombre=role_name)
    return User.objects.create_user(
        email=email,
        password='Test#123456',
        nombre='Nombre',
        apellido_paterno='Apellido',
        rut=rut,
        role=role,
        rbd_colegio=rbd,
        is_active=True,
    )


class TestSensitiveActionService:
    @patch('backend.apps.auditoria.services.sensitive_action_service.AuditoriaEvento.registrar_evento')
    def test_create_request_generates_pending_record(self, _mock_audit):
        requester = _create_user('requester@test.cl', 'Administrador escolar', 123, '11111111-1')
        target = _create_user('target@test.cl', 'Profesor', 123, '22222222-2')

        request_obj = SensitiveActionService.create_request(
            action_type=SensitiveActionService.ACTION_ROLE_CHANGE,
            requested_by=requester,
            school_rbd=123,
            target_user=target,
            payload={'target_user_id': target.id, 'new_role_name': 'profesor'},
            justification='Cambio de rol de prueba',
        )

        assert request_obj.status == request_obj.STATUS_PENDING
        assert request_obj.requested_by_id == requester.id
        assert request_obj.target_user_id == target.id
        assert request_obj.payload['new_role_name'] == 'profesor'

    @patch('backend.apps.auditoria.services.sensitive_action_service.AuditoriaEvento.registrar_evento')
    def test_same_user_cannot_approve_own_request(self, _mock_audit):
        requester = _create_user('same@test.cl', 'Administrador escolar', 123, '33333333-3')
        request_obj = SensitiveActionService.create_request(
            action_type=SensitiveActionService.ACTION_PASSWORD_RESET,
            requested_by=requester,
            school_rbd=123,
            payload={'target_user_id': 99},
        )

        with pytest.raises(PrerequisiteException):
            SensitiveActionService.validate_and_approve_for_execution(
                request_id=request_obj.id,
                actor=requester,
                action_type=SensitiveActionService.ACTION_PASSWORD_RESET,
                school_rbd=123,
            )

    @patch('backend.apps.auditoria.services.sensitive_action_service.AuditoriaEvento.registrar_evento')
    def test_approve_and_execute_request(self, _mock_audit):
        requester = _create_user('req2@test.cl', 'Administrador escolar', 123, '44444444-4')
        approver = _create_user('app2@test.cl', 'Administrador escolar', 123, '55555555-5')

        request_obj = SensitiveActionService.create_request(
            action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
            requested_by=requester,
            school_rbd=123,
            payload={'tipo': 'asistencia', 'formato': 'pdf'},
        )

        approved = SensitiveActionService.validate_and_approve_for_execution(
            request_id=request_obj.id,
            actor=approver,
            action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
            school_rbd=123,
            expected_payload={'tipo': 'asistencia', 'formato': 'pdf'},
        )
        assert approved.status == approved.STATUS_APPROVED
        assert approved.approved_by_id == approver.id

        SensitiveActionService.mark_request_executed(
            approved,
            actor=approver,
            execution_result={'formato': 'pdf'},
        )
        approved.refresh_from_db()

        assert approved.status == approved.STATUS_EXECUTED
        assert approved.executed_by_id == approver.id
        assert approved.execution_result == {'formato': 'pdf'}

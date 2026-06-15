from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from backend.apps.auditoria.models import AuditoriaEvento, SensitiveActionRequest
from backend.common.exceptions import PrerequisiteException


class SensitiveActionService:
    """Servicio de doble control para acciones sensibles."""

    ACTION_ROLE_CHANGE = SensitiveActionRequest.ACTION_ROLE_CHANGE
    ACTION_PASSWORD_RESET = SensitiveActionRequest.ACTION_PASSWORD_RESET
    ACTION_SENSITIVE_EXPORT = SensitiveActionRequest.ACTION_SENSITIVE_EXPORT

    @staticmethod
    def create_request(
        *,
        action_type: str,
        requested_by,
        school_rbd: Optional[int | str],
        target_user=None,
        payload: Optional[Dict[str, Any]] = None,
        justification: str = '',
    ) -> SensitiveActionRequest:
        request_obj = SensitiveActionRequest.objects.create(
            action_type=action_type,
            status=SensitiveActionRequest.STATUS_PENDING,
            school_rbd=str(school_rbd) if school_rbd is not None else None,
            requested_by=requested_by,
            target_user=target_user,
            payload=payload or {},
            justification=justification or '',
        )
        SensitiveActionService._audit_event(
            user=requested_by,
            action=AuditoriaEvento.CREAR,
            level=AuditoriaEvento.NIVEL_WARNING,
            description=f'Solicitud sensible creada: {action_type}',
            metadata={
                'sensitive_request_id': request_obj.id,
                'action_type': action_type,
                'target_user_id': getattr(target_user, 'id', None),
            },
        )
        return request_obj

    @staticmethod
    @transaction.atomic
    def validate_and_approve_for_execution(
        *,
        request_id: int,
        actor,
        action_type: str,
        school_rbd: Optional[int | str] = None,
        target_user_id: Optional[int] = None,
        expected_payload: Optional[Dict[str, Any]] = None,
        approval_comment: str = '',
    ) -> SensitiveActionRequest:
        try:
            request_obj = SensitiveActionRequest.objects.select_for_update().get(id=request_id)
        except SensitiveActionRequest.DoesNotExist:
            raise PrerequisiteException(
                error_type='NOT_FOUND',
                context={'message': 'No se encontró la solicitud de doble control.'},
            )

        if request_obj.action_type != action_type:
            raise PrerequisiteException(
                error_type='PERMISSION_DENIED',
                context={'message': 'La solicitud no corresponde al tipo de acción sensible.'},
            )

        if school_rbd is not None and str(request_obj.school_rbd or '') != str(school_rbd):
            raise PrerequisiteException(
                error_type='PERMISSION_DENIED',
                context={'message': 'La solicitud no corresponde al colegio indicado.'},
            )

        if target_user_id is not None and request_obj.target_user_id not in (None, target_user_id):
            raise PrerequisiteException(
                error_type='PERMISSION_DENIED',
                context={'message': 'La solicitud no corresponde al usuario objetivo.'},
            )

        if request_obj.status in {
            SensitiveActionRequest.STATUS_EXECUTED,
            SensitiveActionRequest.STATUS_FAILED,
            SensitiveActionRequest.STATUS_REJECTED,
        }:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={'message': 'La solicitud ya fue cerrada y no puede reutilizarse.'},
            )

        if actor is None or request_obj.requested_by_id == getattr(actor, 'id', None):
            raise PrerequisiteException(
                error_type='PERMISSION_DENIED',
                context={'message': 'El aprobador debe ser distinto del solicitante.'},
            )

        if expected_payload:
            for key, expected_value in expected_payload.items():
                if request_obj.payload.get(key) != expected_value:
                    raise PrerequisiteException(
                        error_type='PERMISSION_DENIED',
                        context={'message': f'La solicitud no coincide con el payload esperado ({key}).'},
                    )

        if request_obj.status == SensitiveActionRequest.STATUS_PENDING:
            request_obj.status = SensitiveActionRequest.STATUS_APPROVED
            request_obj.approved_by = actor
            request_obj.approved_at = timezone.now()
            request_obj.approval_comment = approval_comment or request_obj.approval_comment
            request_obj.save(update_fields=['status', 'approved_by', 'approved_at', 'approval_comment'])
            SensitiveActionService._audit_event(
                user=actor,
                action=AuditoriaEvento.MODIFICAR,
                level=AuditoriaEvento.NIVEL_WARNING,
                description=f'Solicitud sensible aprobada: {request_obj.action_type}',
                metadata={'sensitive_request_id': request_obj.id},
            )

        return request_obj

    @staticmethod
    @transaction.atomic
    def mark_request_executed(
        request_obj: SensitiveActionRequest,
        *,
        actor,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> SensitiveActionRequest:
        request_obj.status = SensitiveActionRequest.STATUS_EXECUTED
        request_obj.executed_by = actor
        request_obj.executed_at = timezone.now()
        if execution_result is not None:
            request_obj.execution_result = execution_result
        request_obj.save(update_fields=['status', 'executed_by', 'executed_at', 'execution_result'])

        SensitiveActionService._audit_event(
            user=actor,
            action=AuditoriaEvento.MODIFICAR,
            level=AuditoriaEvento.NIVEL_INFO,
            description=f'Solicitud sensible ejecutada: {request_obj.action_type}',
            metadata={
                'sensitive_request_id': request_obj.id,
                'execution_result': execution_result or {},
            },
        )
        return request_obj

    @staticmethod
    @transaction.atomic
    def mark_request_failed(
        request_obj: SensitiveActionRequest,
        *,
        actor,
        error_message: str,
    ) -> SensitiveActionRequest:
        request_obj.status = SensitiveActionRequest.STATUS_FAILED
        request_obj.executed_by = actor
        request_obj.executed_at = timezone.now()
        request_obj.execution_result = {'error': error_message}
        request_obj.save(update_fields=['status', 'executed_by', 'executed_at', 'execution_result'])

        SensitiveActionService._audit_event(
            user=actor,
            action=AuditoriaEvento.MODIFICAR,
            level=AuditoriaEvento.NIVEL_CRITICAL,
            description=f'Solicitud sensible fallida: {request_obj.action_type}',
            metadata={
                'sensitive_request_id': request_obj.id,
                'error': error_message,
            },
        )
        return request_obj

    @staticmethod
    def _audit_event(
        *,
        user,
        action: str,
        level: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        AuditoriaEvento.registrar_evento(
            usuario=user,
            accion=action,
            tabla_afectada='auditoria_sensitive_action_request',
            descripcion=description,
            categoria=AuditoriaEvento.CATEGORIA_SEGURIDAD,
            nivel=level,
            metadata=metadata or {},
        )

from __future__ import annotations

from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from rest_framework.request import Request

from backend.apps.auditoria.models import AuditoriaEvento


class AuthApiAuditService:
    """Auditoria no bloqueante para eventos de autenticacion API v1."""

    @staticmethod
    def _client_ip(request: Request) -> Optional[str]:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def _base_metadata(request: Request) -> Dict[str, Any]:
        return {
            'path': request.path,
            'method': request.method,
            'user_agent': request.META.get('HTTP_USER_AGENT'),
        }

    @staticmethod
    def _resolve_user_by_id(user_id: Optional[int]):
        if not user_id:
            return None
        user_model = get_user_model()
        return user_model.objects.filter(id=user_id).select_related('role').first()

    @classmethod
    def _emit_event(
        cls,
        *,
        request: Request,
        action: str,
        level: str,
        description: str,
        user=None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        event_metadata = cls._base_metadata(request)
        if metadata:
            event_metadata.update(metadata)

        AuditoriaEvento.registrar_evento(
            usuario=user,
            accion=action,
            tabla_afectada='api_auth',
            descripcion=description,
            categoria=AuditoriaEvento.CATEGORIA_SEGURIDAD,
            nivel=level,
            ip_address=cls._client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata=event_metadata,
        )

    @classmethod
    def audit_token_obtain(cls, request: Request, status_code: int, user_id: Optional[int], login_identifier: Optional[str]) -> None:
        user = cls._resolve_user_by_id(user_id)
        is_success = status_code == 200
        cls._emit_event(
            request=request,
            action=AuditoriaEvento.VISUALIZAR,
            level=AuditoriaEvento.NIVEL_INFO if is_success else AuditoriaEvento.NIVEL_WARNING,
            description='API JWT token obtenido' if is_success else 'API JWT token rechazado',
            user=user,
            metadata={
                'event': 'jwt_token_obtain',
                'status_code': status_code,
                'login_identifier': login_identifier,
                'success': is_success,
            },
        )

    @classmethod
    def audit_token_refresh(cls, request: Request, status_code: int) -> None:
        is_success = status_code == 200
        cls._emit_event(
            request=request,
            action=AuditoriaEvento.VISUALIZAR,
            level=AuditoriaEvento.NIVEL_INFO if is_success else AuditoriaEvento.NIVEL_WARNING,
            description='API JWT refresh exitoso' if is_success else 'API JWT refresh rechazado',
            user=getattr(request, 'user', None) if getattr(request, 'user', None) and request.user.is_authenticated else None,
            metadata={
                'event': 'jwt_token_refresh',
                'status_code': status_code,
                'success': is_success,
            },
        )

    @classmethod
    def audit_token_verify(cls, request: Request, status_code: int) -> None:
        is_success = status_code == 200
        cls._emit_event(
            request=request,
            action=AuditoriaEvento.VISUALIZAR,
            level=AuditoriaEvento.NIVEL_INFO if is_success else AuditoriaEvento.NIVEL_WARNING,
            description='API JWT verify exitoso' if is_success else 'API JWT verify rechazado',
            user=getattr(request, 'user', None) if getattr(request, 'user', None) and request.user.is_authenticated else None,
            metadata={
                'event': 'jwt_token_verify',
                'status_code': status_code,
                'success': is_success,
            },
        )

    @classmethod
    def audit_logout(cls, request: Request, status_code: int, detail: str) -> None:
        is_success = status_code == 200
        cls._emit_event(
            request=request,
            action=AuditoriaEvento.MODIFICAR,
            level=AuditoriaEvento.NIVEL_INFO if is_success else AuditoriaEvento.NIVEL_WARNING,
            description='API logout exitoso' if is_success else 'API logout rechazado',
            user=getattr(request, 'user', None) if getattr(request, 'user', None) and request.user.is_authenticated else None,
            metadata={
                'event': 'jwt_logout',
                'status_code': status_code,
                'detail': detail,
                'success': is_success,
            },
        )

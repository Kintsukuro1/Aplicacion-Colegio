from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from backend.apps.api.services.auth_audit_service import AuthApiAuditService
from backend.apps.security.models import ActiveSession


def _sync_active_session_from_refresh(request, refresh_token_raw):
    """Registra o actualiza ActiveSession a partir de un refresh token valido."""
    if not refresh_token_raw:
        return None, None

    token = RefreshToken(refresh_token_raw)
    user_id = token.get('user_id')
    token_jti = token.get('jti')
    if not user_id or not token_jti:
        return user_id, token_jti

    user = get_user_model().objects.filter(id=user_id).first()
    if not user:
        return user_id, token_jti

    ActiveSession.register_session(user=user, token_jti=str(token_jti), request=request)
    return user_id, str(token_jti)


class ColegioTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extiende JWT con claims minimas de contexto para cliente movil."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rbd_colegio'] = getattr(user, 'rbd_colegio', None)
        token['role'] = getattr(getattr(user, 'role', None), 'nombre', None)
        return token


class AuthTokenBurstThrottle(AnonRateThrottle):
    scope = 'auth_token_burst'


class AuthTokenSustainedThrottle(AnonRateThrottle):
    scope = 'auth_token_sustained'


class ColegioTokenObtainPairView(TokenObtainPairView):
    serializer_class = ColegioTokenObtainPairSerializer
    throttle_classes = [AuthTokenBurstThrottle, AuthTokenSustainedThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        user_id = None
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.get('refresh') if isinstance(response.data, dict) else None
            if refresh_token:
                try:
                    user_id, _ = _sync_active_session_from_refresh(request, refresh_token)
                    user_id = int(user_id) if user_id is not None else None
                except (TokenError, TypeError, ValueError):
                    user_id = None

        try:
            AuthApiAuditService.audit_token_obtain(
                request=request,
                status_code=response.status_code,
                user_id=user_id,
                login_identifier=request.data.get('email') if hasattr(request, 'data') else None,
            )
        except Exception:
            # La auditoria nunca debe bloquear autenticacion.
            pass

        return response


class AuditedTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        previous_refresh = request.data.get('refresh') if hasattr(request, 'data') else None
        previous_user_id = None
        previous_token_jti = None
        if previous_refresh:
            try:
                previous_user_id, previous_token_jti = _sync_active_session_from_refresh(request, previous_refresh)
            except (TokenError, TypeError, ValueError):
                previous_user_id = None
                previous_token_jti = None

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK and isinstance(response.data, dict):
            rotated_refresh = response.data.get('refresh')
            if rotated_refresh:
                try:
                    _, rotated_token_jti = _sync_active_session_from_refresh(request, rotated_refresh)
                    if previous_user_id and previous_token_jti and rotated_token_jti and previous_token_jti != rotated_token_jti:
                        ActiveSession.objects.filter(
                            user_id=previous_user_id,
                            token_jti=str(previous_token_jti),
                            is_active=True,
                        ).update(is_active=False)
                except (TokenError, TypeError, ValueError):
                    pass

        try:
            AuthApiAuditService.audit_token_refresh(request=request, status_code=response.status_code)
        except Exception:
            pass
        return response


class AuditedTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        try:
            AuthApiAuditService.audit_token_verify(request=request, status_code=response.status_code)
        except Exception:
            pass
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            response = Response({'detail': 'Debe enviar el refresh token.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                AuthApiAuditService.audit_logout(request=request, status_code=response.status_code, detail='missing_refresh')
            except Exception:
                pass
            return response

        try:
            token = RefreshToken(refresh_token)
            token_user_id = token.get('user_id')
            token_jti = token.get('jti')
            if token_user_id != request.user.id:
                response = Response(
                    {'detail': 'Refresh token no pertenece al usuario autenticado.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
                try:
                    AuthApiAuditService.audit_logout(request=request, status_code=response.status_code, detail='refresh_not_owned')
                except Exception:
                    pass
                return response

            try:
                token.blacklist()
                if token_jti:
                    ActiveSession.objects.filter(
                        user=request.user,
                        token_jti=str(token_jti),
                        is_active=True,
                    ).update(is_active=False)
                response = Response({'detail': 'Sesion cerrada.'}, status=status.HTTP_200_OK)
                try:
                    AuthApiAuditService.audit_logout(request=request, status_code=response.status_code, detail='logout_ok_blacklisted')
                except Exception:
                    pass
                return response
            except AttributeError:
                # Blacklist es opcional; si no esta configurado, se mantiene respuesta exitosa.
                if token_jti:
                    ActiveSession.objects.filter(
                        user=request.user,
                        token_jti=str(token_jti),
                        is_active=True,
                    ).update(is_active=False)
                response = Response(
                    {'detail': 'Sesion cerrada. Blacklist de tokens no esta habilitado.'},
                    status=status.HTTP_200_OK,
                )
                try:
                    AuthApiAuditService.audit_logout(request=request, status_code=response.status_code, detail='logout_ok_no_blacklist')
                except Exception:
                    pass
                return response
        except TokenError:
            response = Response({'detail': 'Refresh token invalido.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                AuthApiAuditService.audit_logout(request=request, status_code=response.status_code, detail='invalid_refresh')
            except Exception:
                pass
            return response

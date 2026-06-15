"""
Endpoints de perfil personal (self-service) para todos los roles.

Endpoints:
  GET    /api/perfil/mi-perfil/         → Obtener perfil propio
  PATCH  /api/perfil/mi-perfil/         → Actualizar perfil propio
  POST   /api/perfil/cambiar-password/  → Cambiar contraseña

Todos requieren autenticación (IsAuthenticated). No requieren capabilities
adicionales porque cada usuario opera solo sobre sí mismo.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.api.services.self_profile_service import SelfProfileService


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def my_profile(request):
    """
    GET:   Retorna el perfil del usuario autenticado (formato por rol).
    PATCH: Actualiza campos permitidos del perfil propio.
    """
    if request.method == 'GET':
        payload = SelfProfileService.get_my_profile(user=request.user)
        return Response(payload, status=status.HTTP_200_OK)

    # PATCH
    payload = SelfProfileService.update_my_profile(
        user=request.user,
        data=request.data,
    )
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    POST: Cambia la contraseña del usuario autenticado.

    Body:
      - password_actual: Contraseña actual
      - password_nueva: Nueva contraseña (min. 6 caracteres)
      - password_confirmar: Confirmar nueva contraseña
    """
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
        or request.META.get('REMOTE_ADDR', '')

    payload = SelfProfileService.change_password(
        user=request.user,
        data=request.data,
        client_ip=client_ip,
    )
    return Response(payload, status=status.HTTP_200_OK)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from backend.apps.api.serializers import UserContextSerializer
from backend.apps.core.services.operational_metrics_service import OperationalMetricsService
from backend.common.services.policy_service import PolicyService


@api_view(['GET'])
@permission_classes([AllowAny])
def api_health(request):
    return Response({'status': 'ok', 'version': 'v1'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    role_name = getattr(getattr(request.user, 'role', None), 'nombre', None)
    school_payload = None
    if getattr(request.user, 'rbd_colegio', None):
        colegio = request.user.colegio
        school_payload = {
            'id': request.user.rbd_colegio,
            'name': getattr(colegio, 'nombre', None),
        }

    payload = {
        'id': request.user.id,
        'email': request.user.email,
        'full_name': request.user.get_full_name(),
        'role': role_name,
        'rbd_colegio': getattr(request.user, 'rbd_colegio', None),
        'capabilities': sorted(PolicyService.get_user_capabilities(request.user)),
        'user': {
            'id': request.user.id,
            'name': request.user.get_full_name(),
            'role': role_name,
            'email': request.user.email,
        },
        'school': school_payload,
    }
    return Response(UserContextSerializer(payload).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def operational_metrics(request):
    if not PolicyService.has_capability(request.user, 'SYSTEM_ADMIN'):
        return Response({'detail': 'No tiene permisos para ver metricas operativas.'}, status=403)

    payload = {
        'contract_version': '1.0.0',
        'metrics': OperationalMetricsService.snapshot(),
    }
    return Response(payload)

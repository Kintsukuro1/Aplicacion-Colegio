from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from backend.apps.api.services.onboarding_service import OnboardingService
from backend.apps.api.throttling import OnboardingRateThrottle
from rest_framework.decorators import throttle_classes


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OnboardingRateThrottle])
def onboarding_register(request):
    try:
        result = OnboardingService.create_school(request.data if isinstance(request.data, dict) else {})
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            'colegio_rbd': result.colegio_rbd,
            'colegio_slug': result.colegio_slug,
            'admin_email': result.admin_email,
            'subscription_status': result.subscription_status,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def onboarding_check_slug(request):
    slug = str(request.query_params.get('slug') or '').strip()
    available = OnboardingService.check_slug_available(slug)
    return Response({'slug': slug, 'available': available}, status=status.HTTP_200_OK)


from backend.apps.api.tasks import generate_demo_data_task

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def onboarding_generate_demo(request):
    colegio = getattr(request.user, 'colegio', None)
    if colegio is None:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    generate_demo_data_task.delay(colegio.id, request.user.id)
    return Response({'detail': 'Datos demo generándose en segundo plano.'}, status=status.HTTP_200_OK)

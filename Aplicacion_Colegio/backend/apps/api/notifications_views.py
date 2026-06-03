import json

from django.http import HttpResponseForbidden, StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.api.serializers import (
    DeviceRegistrationSerializer,
    DeviceSerializer,
    NotificationSerializer,
)
from backend.apps.api.services.notifications_service import NotificationsService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list(request):
    queryset = NotificationsService.list_for_user(request.user, request.query_params.get('limit'))
    serializer = NotificationSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_mark_read(request, notification_id: int):
    if not NotificationsService.mark_read(user=request.user, notification_id=notification_id):
        return Response({'detail': 'Notificacion no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'detail': 'Notificacion marcada como leida.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_summary(request):
    return Response(NotificationsService.summary_for_user(request.user), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_mark_all_read(request):
    updated = NotificationsService.mark_all_read(request.user)
    return Response({'updated': updated}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def device_register(request):
    serializer = DeviceRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    device, created = NotificationsService.upsert_device(
        user=request.user,
        token_fcm=serializer.validated_data['token_fcm'],
        plataforma=serializer.validated_data['plataforma'],
        nombre_dispositivo=serializer.validated_data.get('nombre_dispositivo', ''),
        modelo=serializer.validated_data.get('modelo', ''),
        version_app=serializer.validated_data.get('version_app', ''),
    )
    payload = DeviceSerializer(device).data
    return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def device_deactivate(request, device_id: int):
    if not NotificationsService.deactivate_device(user=request.user, device_id=device_id):
        return Response({'detail': 'Dispositivo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'detail': 'Dispositivo desactivado.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_sse_stream(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Auth requerida')

    last_id_raw = request.GET.get('last_id', '0')
    try:
        last_id = max(0, int(last_id_raw))
    except (TypeError, ValueError):
        last_id = 0

    def event_generator():
        try:
            for event_type, event_id, payload in NotificationsService.stream_events(
                user=request.user, last_id=last_id
            ):
                if event_type == 'notification':
                    data = NotificationSerializer(payload).data
                    yield f"id: {event_id}\n"
                    yield 'event: notification\n'
                    yield f"data: {json.dumps(data, ensure_ascii=True)}\n\n"
                    continue

                yield 'event: keepalive\n'
                yield 'data: {}\n\n'
        finally:
            from django.db import close_old_connections, connection

            close_old_connections()
            connection.close()

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

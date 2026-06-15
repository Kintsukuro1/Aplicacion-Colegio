import json

from django.http import HttpResponseForbidden, StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
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

import asyncio
from asgiref.sync import sync_to_async

async def notifications_sse_stream(request):
    # Authenticate manually (supporting session, token, and DRF force_authenticate)
    @sync_to_async
    def get_authenticated_user(req):
        from rest_framework.views import APIView
        try:
            drf_request = APIView().initialize_request(req)
            user = drf_request.user
            if user and user.is_authenticated:
                return user
        except Exception:
            pass
        return None

    user = await get_authenticated_user(request)
    if not user:
        from django.http import HttpResponse
        return HttpResponse('{"detail": "No autorizado"}', content_type='application/json', status=401)

    last_id_raw = request.GET.get('last_id', '0')
    try:
        last_id = max(0, int(last_id_raw))
    except (TypeError, ValueError):
        last_id = 0

    @sync_to_async
    def get_serialized_notifications(current_user, current_last_id):
        from django.db import close_old_connections
        close_old_connections()
        
        queryset = NotificationsService.queryset_for_user(current_user)
        notifications = list(queryset.filter(id__gt=current_last_id).order_by('id')[:100])
        
        serialized = []
        for notification in notifications:
            serialized.append({
                'id': notification.id,
                'data': NotificationSerializer(notification).data
            })
        return serialized

    @sync_to_async
    def close_db_connections():
        from django.db import close_old_connections, connection
        close_old_connections()
        connection.close()

    async def event_generator():
        nonlocal last_id
        timeout_at = asyncio.get_event_loop().time() + 55
        keepalive_every = 10
        last_keepalive = 0
        
        try:
            while asyncio.get_event_loop().time() < timeout_at:
                items = await get_serialized_notifications(user, last_id)
                
                if items:
                    for item in items:
                        last_id = item['id']
                        yield f"id: {item['id']}\n"
                        yield 'event: notification\n'
                        yield f"data: {json.dumps(item['data'], ensure_ascii=True)}\n\n"
                    continue
                
                now = asyncio.get_event_loop().time()
                if now - last_keepalive >= keepalive_every:
                    last_keepalive = now
                    yield "event: keepalive\n"
                    yield "data: {}\n\n"
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await close_db_connections()

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

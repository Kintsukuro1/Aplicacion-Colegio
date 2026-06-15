from __future__ import annotations

import time
from typing import Iterable

from django.db import close_old_connections, connection
from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.notificaciones.models import DispositivoMovil, Notificacion


class NotificationsService:
    @staticmethod
    def queryset_for_user(user) -> QuerySet[Notificacion]:
        queryset = Notificacion.objects.filter(destinatario=user)
        if getattr(user, 'rbd_colegio', None) is not None:
            queryset = queryset.filter(destinatario__rbd_colegio=user.rbd_colegio)
        return queryset

    @staticmethod
    def list_for_user(user, limit_raw: str | None) -> QuerySet[Notificacion]:
        try:
            limit = max(1, min(int(limit_raw or '50'), 200))
        except (TypeError, ValueError):
            limit = 50

        return NotificationsService.queryset_for_user(user).order_by('-fecha_creacion')[:limit]

    @staticmethod
    def mark_read(*, user, notification_id: int) -> bool:
        notification = NotificationsService.queryset_for_user(user).filter(id=notification_id).first()
        if not notification:
            return False

        if not notification.leido:
            notification.leido = True
            notification.fecha_lectura = timezone.now()
            notification.save(update_fields=['leido', 'fecha_lectura'])

        return True

    @staticmethod
    def summary_for_user(user) -> dict:
        queryset = NotificationsService.queryset_for_user(user)
        unread_count = queryset.filter(leido=False).count()
        latest = queryset.order_by('-fecha_creacion').values_list('fecha_creacion', flat=True).first()
        latest_iso = latest.isoformat() if latest else None
        return {
            'unread_count': unread_count,
            'latest_notification_at': latest_iso,
        }

    @staticmethod
    def mark_all_read(user) -> int:
        now = timezone.now()
        updated = NotificationsService.queryset_for_user(user).filter(leido=False).update(
            leido=True,
            fecha_lectura=now,
        )
        return updated

    @staticmethod
    def upsert_device(*, user, token_fcm: str, plataforma: str, nombre_dispositivo: str = '', modelo: str = '', version_app: str = ''):
        token = token_fcm.strip()
        defaults = {
            'plataforma': plataforma,
            'nombre_dispositivo': nombre_dispositivo,
            'modelo': modelo,
            'version_app': version_app,
            'activo': True,
        }

        return DispositivoMovil.objects.update_or_create(
            token_fcm=token,
            defaults={
                **defaults,
                'usuario': user,
            },
        )

    @staticmethod
    def deactivate_device(*, user, device_id: int) -> bool:
        device = DispositivoMovil.objects.filter(id=device_id, usuario=user).first()
        if not device:
            return False

        if device.activo:
            device.activo = False
            device.save(update_fields=['activo', 'ultima_actividad'])
        return True

    @staticmethod
    def stream_events(*, user, last_id: int) -> Iterable[str]:
        timeout_at = time.time() + 55
        keepalive_every = 10
        last_keepalive = 0

        try:
            while time.time() < timeout_at:
                close_old_connections()
                notifications = list(
                    NotificationsService.queryset_for_user(user)
                    .filter(id__gt=last_id)
                    .order_by('id')[:100]
                )
                if notifications:
                    for notification in notifications:
                        last_id = notification.id
                        yield ('notification', notification.id, notification)
                    connection.close()
                    continue

                now = time.time()
                if now - last_keepalive >= keepalive_every:
                    last_keepalive = now
                    yield ('keepalive', None, None)

                connection.close()
                time.sleep(1)
        finally:
            close_old_connections()
            connection.close()

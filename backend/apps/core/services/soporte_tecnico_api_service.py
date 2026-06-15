"""
Service para operaciones de Soporte Técnico vía API.
Centraliza el acceso ORM para tickets y reseteo de contraseñas.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SoporteTecnicoApiService:
    """Encapsula el acceso ORM del soporte técnico."""

    # ------------------------------------------------------------------
    # Tickets
    # ------------------------------------------------------------------

    @staticmethod
    def crear_ticket(*, rbd: int, user, titulo: str, descripcion: str,
                     categoria: str, prioridad: str):
        """Crea y retorna un TicketSoporte."""
        from backend.apps.core.models import TicketSoporte

        return TicketSoporte.objects.create(
            colegio_id=rbd,
            reportado_por=user,
            asignado_a=user,
            titulo=titulo,
            descripcion=descripcion,
            categoria=categoria,
            prioridad=prioridad,
            estado='ABIERTO',
        )

    @staticmethod
    def get_ticket_or_none(ticket_id, rbd: int):
        """Retorna TicketSoporte o None."""
        from backend.apps.core.models import TicketSoporte

        try:
            return TicketSoporte.objects.get(id_ticket=ticket_id, colegio_id=rbd)
        except TicketSoporte.DoesNotExist:
            return None

    @staticmethod
    def actualizar_ticket(ticket, *, nuevo_estado: str, resolucion: str = '',
                          resuelto_por=None, fecha_resolucion=None) -> None:
        """Actualiza estado y resolución del ticket."""
        ticket.estado = nuevo_estado
        fields = ['estado']

        if resolucion:
            ticket.resolucion = resolucion
            fields.append('resolucion')

        if nuevo_estado in ('RESUELTO', 'CERRADO'):
            if resuelto_por is not None:
                ticket.resuelto_por = resuelto_por
                fields.append('resuelto_por')
            if fecha_resolucion is not None:
                ticket.fecha_resolucion = fecha_resolucion
                fields.append('fecha_resolucion')

        ticket.save(update_fields=fields)

    # ------------------------------------------------------------------
    # Usuarios / contraseñas
    # ------------------------------------------------------------------

    @staticmethod
    def get_target_user_or_none(user_id, rbd: int):
        """Retorna User del colegio o None."""
        from backend.apps.accounts.models import User

        try:
            return User.objects.get(id=user_id, rbd_colegio=rbd)
        except User.DoesNotExist:
            return None

    @staticmethod
    def reset_user_password(user, new_password: str) -> None:
        """Cambia la contraseña del usuario y persiste."""
        user.set_password(new_password)
        user.save()

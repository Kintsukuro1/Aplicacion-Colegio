"""
Service para operaciones de Coordinador Académico vía API.
Centraliza el acceso ORM para planificaciones.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CoordinadorAcademicoApiService:
    """Encapsula las operaciones ORM del coordinador académico."""

    @staticmethod
    def get_planificacion_or_none(planificacion_id, rbd: int):
        """Retorna Planificacion filtrada por id y colegio, o None."""
        from backend.apps.academico.models import Planificacion

        try:
            return Planificacion.objects.get(id_planificacion=planificacion_id, colegio_id=rbd)
        except Planificacion.DoesNotExist:
            return None

    @staticmethod
    def actualizar_estado_planificacion(planificacion, *, nuevo_estado: str,
                                        observaciones: str, aprobado_por, fecha_aprobacion) -> None:
        """Actualiza estado, observaciones y aprobador de la planificación."""
        planificacion.estado = nuevo_estado
        planificacion.observaciones_coordinador = observaciones
        planificacion.aprobado_por = aprobado_por
        planificacion.fecha_aprobacion = fecha_aprobacion
        planificacion.save(update_fields=['estado', 'observaciones_coordinador', 'aprobado_por', 'fecha_aprobacion'])

    @staticmethod
    def list_planificaciones_pendientes(rbd: int, limit: int = 50) -> list[dict]:
        """Lista planificaciones pendientes de revisión para acciones rápidas."""
        from backend.apps.academico.models import Planificacion

        qs = (
            Planificacion.objects.filter(colegio_id=rbd, activa=True, estado='ENVIADA')
            .select_related('clase', 'enviada_por')
            .order_by('-fecha_envio', '-fecha_creacion')[:limit]
        )

        data = []
        for item in qs:
            enviada_por = item.enviada_por.get_full_name() if item.enviada_por else 'Sin profesor'
            data.append(
                {
                    'id': item.id_planificacion,
                    'titulo': item.titulo,
                    'clase': str(item.clase) if item.clase else 'Sin clase',
                    'enviada_por': enviada_por,
                    'fecha_inicio': str(item.fecha_inicio) if item.fecha_inicio else None,
                    'fecha_fin': str(item.fecha_fin) if item.fecha_fin else None,
                }
            )

        return data

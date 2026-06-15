"""
Service para operaciones del Estudiante vía API.
Centraliza el acceso ORM para entregas de tareas.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class EstudianteApiService:
    """Encapsula operaciones ORM del estudiante para mantener las vistas limpias."""

    @staticmethod
    def get_tarea_activa_or_none(tarea_id):
        """Retorna la tarea activa o None."""
        from backend.apps.academico.models import Tarea

        return Tarea.objects.filter(id_tarea=tarea_id, activa=True).first()

    @staticmethod
    def get_entrega_existente(tarea, estudiante):
        """Retorna EntregaTarea existente para tarea+estudiante, o None."""
        from backend.apps.academico.models import EntregaTarea

        return EntregaTarea.objects.filter(tarea=tarea, estudiante=estudiante).first()

    @staticmethod
    def actualizar_entrega(entrega, *, archivo, comentario: str, fecha_entrega) -> None:
        """Actualiza los campos de una entrega existente y la guarda."""
        entrega.archivo = archivo
        entrega.comentarios_estudiante = comentario
        entrega.fecha_entrega = fecha_entrega
        if entrega.estado in ['pendiente', 'devuelta']:
            entrega.estado = 'pendiente'
        entrega.save()

    @staticmethod
    def crear_entrega(*, tarea, estudiante, archivo, comentario: str) -> None:
        """Crea una nueva EntregaTarea."""
        from backend.apps.academico.models import EntregaTarea

        EntregaTarea.objects.create(
            tarea=tarea,
            estudiante=estudiante,
            archivo=archivo,
            comentarios_estudiante=comentario,
            estado='pendiente',
        )

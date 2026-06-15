"""Servicio para entregas de tareas de estudiantes."""

from django.utils import timezone


class TareaEntregaService:
    @staticmethod
    def upsert_entrega(*, tarea, estudiante, archivo, comentario: str = ''):
        from backend.apps.academico.models import EntregaTarea

        entrega, created = EntregaTarea.objects.get_or_create(
            tarea=tarea,
            estudiante=estudiante,
            defaults={
                'archivo': archivo,
                'comentario_estudiante': comentario,
                'estado': 'tarde' if tarea.esta_vencida() else 'entregada',
            },
        )

        if created:
            return entrega, True

        entrega.archivo = archivo
        entrega.comentario_estudiante = comentario
        entrega.fecha_entrega = timezone.now()
        entrega.estado = 'tarde' if tarea.esta_vencida() else 'entregada'
        entrega.save()
        return entrega, False

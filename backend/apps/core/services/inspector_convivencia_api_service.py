"""
Service para operaciones del Inspector de Convivencia vía API.
Centraliza el acceso ORM para anotaciones, justificativos y atrasos.
"""
from __future__ import annotations

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


class InspectorConvivenciaApiService:
    """Encapsula el acceso ORM del inspector de convivencia."""

    # ------------------------------------------------------------------
    # Estudiantes
    # ------------------------------------------------------------------

    @staticmethod
    def list_estudiantes(rbd: int) -> list[dict]:
        """Lista estudiantes activos del colegio."""
        from backend.apps.accounts.models import User

        qs = User.objects.filter(
            rbd_colegio=rbd,
            role__nombre__in=['Alumno', 'Estudiante'],
            is_active=True,
        ).values('id', 'nombre', 'apellido_paterno', 'apellido_materno', 'rut').order_by('apellido_paterno', 'nombre')

        return [
            {
                'id': e['id'],
                'nombre': (
                    f"{e['nombre']} {e['apellido_paterno']} {e.get('apellido_materno') or ''}"
                ).strip(),
                'rut': e['rut'] or '',
            }
            for e in qs
        ]

    @staticmethod
    def get_estudiante_or_none(estudiante_id, rbd: int):
        """Retorna User estudiante del colegio o None."""
        from backend.apps.accounts.models import User

        try:
            return User.objects.get(id=estudiante_id, rbd_colegio=rbd)
        except User.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Anotaciones
    # ------------------------------------------------------------------

    @staticmethod
    def crear_anotacion(*, estudiante, rbd: int, tipo: str, categoria: str,
                        descripcion: str, gravedad: int, registrado_por):
        """Crea y retorna una AnotacionConvivencia."""
        from backend.apps.core.models import AnotacionConvivencia

        return AnotacionConvivencia.objects.create(
            estudiante=estudiante,
            colegio_id=rbd,
            tipo=tipo,
            categoria=categoria,
            descripcion=descripcion,
            gravedad=gravedad,
            registrado_por=registrado_por,
        )

    # ------------------------------------------------------------------
    # Justificativos
    # ------------------------------------------------------------------

    @staticmethod
    def list_justificativos_pendientes(rbd: int, limit: int = 50) -> list[dict]:
        """Lista justificativos pendientes para revisión rápida del inspector."""
        from backend.apps.core.models import JustificativoInasistencia

        qs = (
            JustificativoInasistencia.objects.filter(colegio_id=rbd, estado='PENDIENTE')
            .select_related('estudiante', 'presentado_por')
            .order_by('-fecha_ausencia')[:limit]
        )

        data = []
        for item in qs:
            estudiante_nombre = item.estudiante.get_full_name() if item.estudiante else 'Sin estudiante'
            presentado_por = item.presentado_por.get_full_name() if item.presentado_por else 'Sin apoderado'
            data.append(
                {
                    'id': item.id_justificativo,
                    'estudiante': estudiante_nombre,
                    'presentado_por': presentado_por,
                    'fecha_ausencia': str(item.fecha_ausencia),
                    'tipo': item.tipo,
                    'motivo': item.motivo,
                }
            )

        return data

    @staticmethod
    def get_justificativo_or_none(justificativo_id, rbd: int):
        """Retorna JustificativoInasistencia o None."""
        from backend.apps.core.models import JustificativoInasistencia

        try:
            return JustificativoInasistencia.objects.get(id_justificativo=justificativo_id, colegio_id=rbd)
        except JustificativoInasistencia.DoesNotExist:
            return None

    @staticmethod
    def actualizar_justificativo(justificativo, *, nuevo_estado: str, revisado_por,
                                 observaciones: str) -> None:
        """Cambia estado de un justificativo y persiste."""
        justificativo.estado = nuevo_estado
        justificativo.revisado_por = revisado_por
        justificativo.fecha_revision = timezone.now()
        justificativo.observaciones_revision = observaciones
        justificativo.save(update_fields=['estado', 'revisado_por', 'fecha_revision', 'observaciones_revision'])

    # ------------------------------------------------------------------
    # Atrasos
    # ------------------------------------------------------------------

    @staticmethod
    def get_clase_or_none(clase_id, rbd: int):
        """Retorna Clase del colegio o None."""
        from backend.apps.cursos.models import Clase

        try:
            return Clase.objects.get(id=clase_id, curso__colegio_id=rbd)
        except Clase.DoesNotExist:
            return None

    @staticmethod
    def registrar_atraso(*, rbd: int, clase, estudiante, fecha: str, observaciones: str):
        """Crea o actualiza un registro de asistencia con estado 'T' (Tardanza)."""
        from backend.apps.academico.models import Asistencia

        # Control defensivo de duplicados: consultar estado anterior
        try:
            asistencia_previa = Asistencia.objects.get(
                colegio_id=rbd,
                clase=clase,
                estudiante=estudiante,
                fecha=fecha
            )
            estado_anterior = asistencia_previa.estado
        except Asistencia.DoesNotExist:
            estado_anterior = None

        asistencia, _ = Asistencia.objects.update_or_create(
            colegio_id=rbd,
            clase=clase,
            estudiante=estudiante,
            fecha=fecha,
            defaults={
                'estado': 'T',
                'tipo_asistencia': 'Presencial',
                'observaciones': observaciones,
            },
        )

        # Disparar notificación si pasa a estar con atraso
        if estado_anterior != 'T':
            from backend.apps.notificaciones.services.attendance_notifications import AttendanceNotificationService
            import logging
            logger = logging.getLogger(__name__)
            try:
                # Convertir fecha a date object si es string, para consistencia
                from datetime import datetime, date
                fecha_obj = fecha
                if isinstance(fecha, str):
                    try:
                        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
                    except ValueError:
                        pass

                AttendanceNotificationService.notify_lateness(
                    estudiante=estudiante,
                    clase=clase,
                    fecha=fecha_obj,
                    observaciones=observaciones
                )
            except Exception as e:
                logger.error(f"Error al enviar notificacion de atraso: {e}", exc_info=True)

        return asistencia

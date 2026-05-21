import logging
from django.db import transaction
from backend.apps.notificaciones.models import Notificacion
from backend.apps.accounts.models import RelacionApoderadoEstudiante

logger = logging.getLogger(__name__)

class AttendanceNotificationService:
    """
    Servicio de dominio para enviar alertas inmediatas de inasistencia y atrasos
    a los apoderados activos de los estudiantes, respetando el multi-tenant y
    las preferencias de permisos de cada relación.
    """

    @staticmethod
    def notify_absence(estudiante, clase, fecha, registrada_por=None):
        """
        Notifica a los apoderados de un estudiante sobre una inasistencia (ausencia).
        """
        # Asegurarse de que el estudiante y la clase pertenezcan al mismo colegio para multi-tenancy
        colegio_id = estudiante.rbd_colegio
        if clase.curso.colegio_id != colegio_id:
            logger.warning(
                f"Multi-tenant violation attempt: Estudiante colegio {colegio_id} "
                f"no coincide con clase colegio {clase.curso.colegio_id}"
            )
            return []

        # Buscar relaciones de apoderado activas dentro del mismo colegio
        relaciones = RelacionApoderadoEstudiante.objects.filter(
            estudiante=estudiante,
            activa=True,
            apoderado__user__rbd_colegio=colegio_id
        ).select_related('apoderado__user')

        notificaciones = []
        with transaction.atomic():
            for relacion in relaciones:
                apoderado = relacion.apoderado
                if not apoderado.activo or not apoderado.user.is_active:
                    continue

                # Validar permisos efectivos
                permisos = relacion.get_permisos_efectivos()
                if not permisos.get('ver_asistencia', True):
                    logger.info(
                        f"Apoderado {apoderado.user.id} no tiene permiso 'ver_asistencia' "
                        f"para el estudiante {estudiante.id}"
                    )
                    continue

                titulo = f"Alerta de Inasistencia: {estudiante.get_full_name()}"
                mensaje = (
                    f"Estimado(a) apoderado, le informamos que se ha registrado la inasistencia "
                    f"de su pupilo(a) {estudiante.get_full_name()} en la clase de "
                    f"{clase.asignatura.nombre} el {fecha}."
                )

                # Construir enlace a la vista de asistencia en el portal del apoderado
                enlace = f"/apoderado/estudiante/{estudiante.id}/asistencia"

                notificacion = Notificacion.objects.create(
                    destinatario=apoderado.user,
                    tipo='asistencia',
                    titulo=titulo,
                    mensaje=mensaje,
                    enlace=enlace,
                    prioridad='alta'
                )
                notificaciones.append(notificacion)
                logger.info(f"Notificación de inasistencia creada para {apoderado.user.email}")

        return notificaciones

    @staticmethod
    def notify_lateness(estudiante, clase, fecha, registrada_por=None, observaciones=""):
        """
        Notifica a los apoderados de un estudiante sobre un atraso (tardanza).
        """
        colegio_id = estudiante.rbd_colegio
        if clase.curso.colegio_id != colegio_id:
            logger.warning(
                f"Multi-tenant violation attempt: Estudiante colegio {colegio_id} "
                f"no coincide con clase colegio {clase.curso.colegio_id}"
            )
            return []

        relaciones = RelacionApoderadoEstudiante.objects.filter(
            estudiante=estudiante,
            activa=True,
            apoderado__user__rbd_colegio=colegio_id
        ).select_related('apoderado__user')

        notificaciones = []
        with transaction.atomic():
            for relacion in relaciones:
                apoderado = relacion.apoderado
                if not apoderado.activo or not apoderado.user.is_active:
                    continue

                permisos = relacion.get_permisos_efectivos()
                if not permisos.get('ver_asistencia', True):
                    logger.info(
                        f"Apoderado {apoderado.user.id} no tiene permiso 'ver_asistencia' "
                        f"para el estudiante {estudiante.id}"
                    )
                    continue

                titulo = f"Alerta de Atraso: {estudiante.get_full_name()}"
                obs_text = f" Observaciones: {observaciones}" if observaciones else ""
                mensaje = (
                    f"Estimado(a) apoderado, le informamos que se ha registrado un atraso "
                    f"de su pupilo(a) {estudiante.get_full_name()} en la clase de "
                    f"{clase.asignatura.nombre} el {fecha}.{obs_text}"
                )

                enlace = f"/apoderado/estudiante/{estudiante.id}/asistencia"

                notificacion = Notificacion.objects.create(
                    destinatario=apoderado.user,
                    tipo='asistencia',
                    titulo=titulo,
                    mensaje=mensaje,
                    enlace=enlace,
                    prioridad='alta'
                )
                notificaciones.append(notificacion)
                logger.info(f"Notificación de atraso creada para {apoderado.user.email}")

        return notificaciones

import logging
from datetime import timedelta
from django.db.models import Avg, Count, Q
from django.utils import timezone

from backend.apps.notificaciones.models import Notificacion
from backend.apps.academico.models import Calificacion, Asistencia, Tarea, EntregaTarea
from backend.apps.cursos.models import Clase
from backend.apps.accounts.models import RelacionApoderadoEstudiante, PerfilEstudiante
from backend.apps.matriculas.models import Matricula

logger = logging.getLogger(__name__)

class AcademicAlertsService:
    """
    Servicio para evaluar y generar alertas académicas automáticas de forma
    deduplicada y respetando las reglas de multi-tenancy.
    """

    @staticmethod
    def evaluate_student_alerts(
        student,
        curso_actual=None,
        relaciones=None,
        promedio_general=None,
        porcentaje_asistencia=None,
        pending_count=None,
        ausencias_mes=None
    ):
        """
        Evalúa el estado académico del estudiante y genera las notificaciones
        adecuadas para el estudiante y sus apoderados.
        """
        colegio_id = getattr(student, 'rbd_colegio', None)
        if not colegio_id:
            return

        # 1. Resolver curso actual
        if curso_actual is None:
            matricula_activa = Matricula.objects.filter(
                estudiante=student,
                estado='ACTIVA',
                curso__isnull=False,
            ).select_related('curso').order_by('-fecha_matricula', '-pk').first()
            curso_actual = matricula_activa.curso if matricula_activa else None

            if not curso_actual:
                perfil = getattr(student, 'perfil_estudiante', None)
                if not perfil:
                    perfil = PerfilEstudiante.objects.filter(user=student).first()
                curso_actual = perfil.curso_actual if perfil else None

        # 2. Obtener apoderados del estudiante
        if relaciones is None:
            relaciones = list(RelacionApoderadoEstudiante.objects.filter(
                estudiante=student,
                activa=True,
                apoderado__user__rbd_colegio=colegio_id
            ).select_related('apoderado__user'))
        elif not isinstance(relaciones, list):
            relaciones = list(relaciones)

        # -------------------------------------------------------------
        # PRECARGA DE NOTIFICACIONES NO LEÍDAS (Bulk check in memory)
        # -------------------------------------------------------------
        destinatarios_ids = [student.id] + [
            rel.apoderado.user.id
            for rel in relaciones
            if rel.apoderado.activo and rel.apoderado.user.is_active
        ]
        unread_notifications = list(Notificacion.objects.filter(
            destinatario_id__in=destinatarios_ids,
            leido=False
        ))

        # -------------------------------------------------------------
        # EVALUACIÓN 1: Riesgo Académico Alto
        # (Asistencia < 85% Y Promedio < 5.0)
        # -------------------------------------------------------------
        if promedio_general is None:
            promedio = Calificacion.objects.filter(
                estudiante=student,
                evaluacion__activa=True
            ).aggregate(promedio=Avg('nota'))['promedio']
            promedio_general = float(promedio) if promedio else None
        else:
            promedio_general = float(promedio_general)

        if porcentaje_asistencia is None:
            asistencias = Asistencia.objects.filter(estudiante=student)
            total_asistencias = asistencias.count()
            porcentaje_asistencia = 100.0
            if total_asistencias > 0:
                presentes = asistencias.filter(estado='P').count()
                porcentaje_asistencia = (presentes / total_asistencias) * 100.0
        else:
            porcentaje_asistencia = float(porcentaje_asistencia)

        title_riesgo_student = "⚠ Riesgo Académico Alto"
        title_riesgo_parent = f"⚠ Riesgo Académico Alto: {student.get_full_name()}"

        if promedio_general is not None and promedio_general < 5.0 and porcentaje_asistencia < 85.0:
            # Alerta para el alumno
            msg_student = f"Tu promedio general es {promedio_general:.1f} y tu asistencia es {porcentaje_asistencia:.0f}%."
            AcademicAlertsService.check_and_create_or_update_alert(
                destinatario=student,
                tipo='alerta',
                titulo=title_riesgo_student,
                mensaje=msg_student,
                enlace='/dashboard/?pagina=inicio',
                prioridad='alta',
                unread_notifications=unread_notifications
            )
            # Alerta para los apoderados
            msg_parent = f"Su pupilo(a) {student.get_full_name()} se encuentra en riesgo académico alto. Promedio: {promedio_general:.1f}, Asistencia: {porcentaje_asistencia:.0f}%."
            for rel in relaciones:
                if rel.apoderado.activo and rel.apoderado.user.is_active:
                    AcademicAlertsService.check_and_create_or_update_alert(
                        destinatario=rel.apoderado.user,
                        tipo='alerta',
                        titulo=title_riesgo_parent,
                        mensaje=msg_parent,
                        enlace=f"/dashboard/?pagina=inicio&estudiante_id={student.id}",
                        prioridad='alta',
                        unread_notifications=unread_notifications
                    )
        else:
            # Resolver alerta si existía y ya no aplica
            AcademicAlertsService.resolve_alert(student, title_riesgo_student, unread_notifications)
            for rel in relaciones:
                AcademicAlertsService.resolve_alert(rel.apoderado.user, title_riesgo_parent, unread_notifications)

        # -------------------------------------------------------------
        # EVALUACIÓN 2: Tareas Pendientes
        # -------------------------------------------------------------
        if pending_count is None:
            pending_count = 0
            if curso_actual:
                clases = Clase.objects.filter(curso=curso_actual, activo=True)
                tareas_qs = Tarea.objects.filter(
                    clase__in=clases,
                    es_publica=True,
                    activa=True
                )
                entregas = EntregaTarea.objects.filter(
                    tarea__in=tareas_qs,
                    estudiante=student
                ).values_list('tarea_id', flat=True)
                pending_count = tareas_qs.exclude(id_tarea__in=entregas).count()

        title_tareas = "Tareas pendientes"

        if pending_count > 0:
            msg_tareas = f"Tienes {pending_count} tareas pendientes por entregar."
            AcademicAlertsService.check_and_create_or_update_alert(
                destinatario=student,
                tipo='tarea_nueva',
                titulo=title_tareas,
                mensaje=msg_tareas,
                enlace='/dashboard/?pagina=mis_tareas',
                prioridad='normal',
                unread_notifications=unread_notifications
            )
        else:
            AcademicAlertsService.resolve_alert(student, title_tareas, unread_notifications)

        # -------------------------------------------------------------
        # EVALUACIÓN 3: Ausencias del Mes
        # (Acumulación de 4 o más ausencias en el mes actual)
        # -------------------------------------------------------------
        if ausencias_mes is None:
            hoy = timezone.now().date()
            ausencias_mes = Asistencia.objects.filter(
                estudiante=student,
                estado='A',
                fecha__year=hoy.year,
                fecha__month=hoy.month
            ).count()

        title_ausencias = f"Ausencias del mes: {student.get_full_name()}"

        if ausencias_mes >= 4:
            msg_ausencias = f"Su hijo(a) {student.get_full_name()} acumula {ausencias_mes} ausencias durante este mes."
            for rel in relaciones:
                if rel.apoderado.activo and rel.apoderado.user.is_active:
                    # Validar si tiene permiso de ver asistencia antes de alertar
                    permisos = rel.get_permisos_efectivos()
                    if permisos.get('ver_asistencia', True):
                        AcademicAlertsService.check_and_create_or_update_alert(
                            destinatario=rel.apoderado.user,
                            tipo='asistencia',
                            titulo=title_ausencias,
                            mensaje=msg_ausencias,
                            enlace=f"/dashboard/?pagina=inicio&estudiante_id={student.id}",
                            prioridad='alta',
                            unread_notifications=unread_notifications
                        )
        else:
            for rel in relaciones:
                AcademicAlertsService.resolve_alert(rel.apoderado.user, title_ausencias, unread_notifications)

    @staticmethod
    def check_and_create_or_update_alert(destinatario, tipo, titulo, mensaje, enlace, prioridad, unread_notifications=None):
        """
        Helper para guardar una alerta de forma deduplicada.
        """
        hace_7_dias = timezone.now() - timedelta(days=7)

        # Buscar si existe una notificación no leída idéntica
        unread_alert = None
        if unread_notifications is not None:
            unread_alert = next((
                n for n in unread_notifications
                if n.destinatario_id == destinatario.id and n.titulo == titulo
            ), None)
        else:
            unread_alert = Notificacion.objects.filter(
                destinatario=destinatario,
                titulo=titulo,
                leido=False
            ).first()

        if unread_alert:
            if unread_alert.mensaje != mensaje:
                unread_alert.mensaje = mensaje
                unread_alert.fecha_creacion = timezone.now()
                unread_alert.save()
            return unread_alert

        # Verificar si existe una ya leída en los últimos 7 días
        recent_read_alert = Notificacion.objects.filter(
            destinatario=destinatario,
            titulo=titulo,
            leido=True,
            fecha_creacion__gte=hace_7_dias
        ).exists()

        if not recent_read_alert:
            return Notificacion.objects.create(
                destinatario=destinatario,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                enlace=enlace,
                prioridad=prioridad
            )
        return None

    @staticmethod
    def resolve_alert(destinatario, titulo, unread_notifications=None):
        """
        Marca las alertas no leídas vigentes como leídas cuando la condición
        deja de cumplirse.
        """
        if unread_notifications is not None:
            has_unread = any(
                n.destinatario_id == destinatario.id and n.titulo == titulo
                for n in unread_notifications
            )
            if not has_unread:
                return

        Notificacion.objects.filter(
            destinatario=destinatario,
            titulo=titulo,
            leido=False
        ).update(leido=True, fecha_lectura=timezone.now())

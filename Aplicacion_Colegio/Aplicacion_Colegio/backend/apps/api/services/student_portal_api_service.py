from __future__ import annotations

from django.utils import timezone

from backend.apps.accounts.models import PerfilEstudiante
from backend.apps.academico.models import Asistencia, Calificacion, EntregaTarea, Tarea
from backend.apps.api.resources_serializers import (
    StudentAttendanceSerializer,
    StudentEnrollmentSerializer,
    StudentGradeSerializer,
    StudentSelfSerializer,
)
from backend.apps.cursos.models import Clase, ClaseEstudiante
from backend.apps.core.services.dashboard_context_service import DashboardContextService
from backend.common.services.policy_service import PolicyService


class StudentPortalApiService:
    """Logica de dominio para endpoints de autoservicio de estudiante."""

    @staticmethod
    def has_capability(*, user, capability: str) -> bool:
        return PolicyService.has_capability(
            user,
            capability,
            school_id=getattr(user, 'rbd_colegio', None),
        )

    @staticmethod
    def is_global_admin(user) -> bool:
        return PolicyService.has_capability(user, 'SYSTEM_ADMIN')

    @classmethod
    def serialize_profile(cls, *, user) -> dict:
        return StudentSelfSerializer(user).data

    @classmethod
    def serialize_my_classes(cls, *, user) -> list:
        queryset = ClaseEstudiante.objects.select_related(
            'clase__curso',
            'clase__asignatura',
            'clase__profesor',
        ).filter(estudiante_id=user.id, activo=True)

        if not cls.is_global_admin(user):
            queryset = queryset.filter(clase__colegio_id=user.rbd_colegio)

        return StudentEnrollmentSerializer(queryset.order_by('-fecha_matricula'), many=True).data

    @classmethod
    def serialize_my_grades(cls, *, user, clase_id=None, evaluacion_id=None) -> list:
        queryset = Calificacion.objects.select_related(
            'evaluacion',
            'evaluacion__clase',
            'evaluacion__clase__curso',
            'evaluacion__clase__asignatura',
        ).filter(estudiante_id=user.id)

        if not cls.is_global_admin(user):
            queryset = queryset.filter(colegio_id=user.rbd_colegio)

        if clase_id:
            queryset = queryset.filter(evaluacion__clase_id=clase_id)

        if evaluacion_id:
            queryset = queryset.filter(evaluacion_id=evaluacion_id)

        return StudentGradeSerializer(queryset.order_by('-fecha_creacion', '-id_calificacion'), many=True).data

    @classmethod
    def serialize_my_attendance(cls, *, user, clase_id=None, fecha_desde=None, fecha_hasta=None) -> list:
        queryset = Asistencia.objects.select_related(
            'clase__curso',
            'clase__asignatura',
        ).filter(estudiante_id=user.id)

        if not cls.is_global_admin(user):
            queryset = queryset.filter(colegio_id=user.rbd_colegio)

        if clase_id:
            queryset = queryset.filter(clase_id=clase_id)

        if fecha_desde:
            queryset = queryset.filter(fecha__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha__lte=fecha_hasta)

        return StudentAttendanceSerializer(queryset.order_by('-fecha', '-id_asistencia'), many=True).data

    @staticmethod
    def _get_estado_entrega(tarea, entrega):
        if entrega:
            if entrega.calificacion is not None or entrega.estado == 'revisada' or entrega.retroalimentacion:
                return 'corregida', '✅', 'Corregida'

            if entrega.estado == 'tarde' or entrega.fue_entregada_tarde():
                return 'atrasada', '⏰', 'Entregada tarde'

            return 'entregada', '📤', 'Entregada'

        if tarea.esta_vencida():
            return 'atrasada', '⏰', 'Atrasada'
        return 'pendiente', '📝', 'Pendiente'

    @staticmethod
    def _get_estado_tiempo(tarea):
        now = timezone.now()
        if not tarea.fecha_entrega:
            return 'normal'

        delta = tarea.fecha_entrega - now
        if delta.total_seconds() < 0:
            return 'vencida'
        if delta.days <= 1:
            return 'urgente'
        if delta.days <= 3:
            return 'proximo'
        return 'normal'

    @classmethod
    def _resolve_student_course(cls, *, user):
        perfil = PerfilEstudiante.objects.filter(user=user).select_related('curso_actual').first()
        curso_actual = DashboardContextService._resolve_estudiante_curso_actual(user)
        return perfil, curso_actual

    @classmethod
    def serialize_my_tasks(cls, *, user) -> list:
        _, curso_actual = cls._resolve_student_course(user=user)
        if not curso_actual:
            return []

        clases = Clase.objects.filter(
            curso=curso_actual,
            colegio_id=user.rbd_colegio,
            activo=True,
        )

        tareas_qs = (
            Tarea.objects.filter(
                clase__in=clases,
                es_publica=True,
                activa=True,
                colegio_id=user.rbd_colegio,
            )
            .select_related('clase__curso', 'clase__asignatura')
            .order_by('fecha_entrega')
        )

        entregas = EntregaTarea.objects.filter(tarea__in=tareas_qs, estudiante_id=user.id)
        entregas_por_tarea = {entrega.tarea_id: entrega for entrega in entregas}

        data = []
        for tarea in tareas_qs:
            entrega = entregas_por_tarea.get(tarea.id_tarea)
            estado, icono_estado, texto_estado = cls._get_estado_entrega(tarea, entrega)

            fecha_entrega = tarea.fecha_entrega
            fecha_entrega_local = timezone.localtime(fecha_entrega) if fecha_entrega else None

            data.append(
                {
                    'id_tarea': tarea.id_tarea,
                    'titulo': tarea.titulo,
                    'instrucciones': tarea.instrucciones,
                    'clase_id': tarea.clase_id,
                    'curso_nombre': tarea.clase.curso.nombre if tarea.clase and tarea.clase.curso else None,
                    'asignatura_nombre': tarea.clase.asignatura.nombre if tarea.clase and tarea.clase.asignatura else None,
                    'fecha_entrega': fecha_entrega.isoformat() if fecha_entrega else None,
                    'fecha_entrega_date': fecha_entrega.date().isoformat() if fecha_entrega else None,
                    'fecha_entrega_time': fecha_entrega_local.strftime('%H:%M') if fecha_entrega_local else None,
                    'fecha_entrega_full': fecha_entrega_local.strftime('%d/%m/%Y %H:%M') if fecha_entrega_local else 'Sin fecha',
                    'estado': estado,
                    'icono_estado': icono_estado,
                    'texto_estado': texto_estado,
                    'estado_tiempo': cls._get_estado_tiempo(tarea),
                    'dias_restantes': tarea.dias_restantes(),
                    'archivo_instrucciones': tarea.archivo_instrucciones.url if tarea.archivo_instrucciones else None,
                    'calificacion': float(entrega.calificacion) if entrega and entrega.calificacion is not None else None,
                    'entrega': (
                        {
                            'id_entrega': entrega.id_entrega,
                            'estado': entrega.estado,
                            'fecha_entrega': timezone.localtime(entrega.fecha_entrega).isoformat() if entrega.fecha_entrega else None,
                            'comentario_estudiante': entrega.comentario_estudiante or '',
                            'retroalimentacion': entrega.retroalimentacion or '',
                            'archivo': entrega.archivo.url if entrega.archivo else None,
                            'fue_tarde': entrega.fue_entregada_tarde(),
                        }
                        if entrega
                        else None
                    ),
                }
            )

        return data

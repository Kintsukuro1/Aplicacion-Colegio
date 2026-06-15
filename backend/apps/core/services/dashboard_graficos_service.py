"""
Dashboard Graficos Service - Lógica de negocio para estadísticas y gráficos del dashboard.

Extraído de backend/apps/core/views/dashboard_graficos.py para separar responsabilidades.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import Avg, QuerySet
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from backend.apps.accounts.models import PerfilEstudiante, User
from backend.apps.academico.models import Asistencia, Calificacion, EntregaTarea, Evaluacion, Tarea
from backend.apps.cursos.models import Clase, Curso
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService


@dataclass(frozen=True)
class MonthRange:
    start: date
    end_exclusive: date
    label: str


class DashboardGraficosService:
    """Servicio para lógica de gráficos y estadísticas del dashboard."""

    @staticmethod
    def execute(operation: str, params: dict):
        DashboardGraficosService.validate(operation, params)
        return DashboardGraficosService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: dict) -> None:
        if operation in [
            'get_datos_asistencia',
            'get_datos_calificaciones',
            'get_datos_rendimiento',
            'get_datos_estadisticas',
        ]:
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('rol') is None:
                raise ValueError('Parámetro requerido: rol')
            if params.get('escuela_rbd') is None:
                raise ValueError('Parámetro requerido: escuela_rbd')
            return
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: dict):
        if operation == 'get_datos_asistencia':
            return DashboardGraficosService._execute_get_datos_asistencia(params)
        if operation == 'get_datos_calificaciones':
            return DashboardGraficosService._execute_get_datos_calificaciones(params)
        if operation == 'get_datos_rendimiento':
            return DashboardGraficosService._execute_get_datos_rendimiento(params)
        if operation == 'get_datos_estadisticas':
            return DashboardGraficosService._execute_get_datos_estadisticas(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _validate_school_integrity(escuela_rbd: int, action: str) -> None:
        IntegrityService.validate_school_integrity_or_raise(
            school_id=escuela_rbd,
            action=action,
        )

    @staticmethod
    def _add_months(d: date, months: int) -> date:
        """Suma meses sin dependencias externas."""
        year = d.year + (d.month - 1 + months) // 12
        month = (d.month - 1 + months) % 12 + 1
        return date(year, month, 1)

    @staticmethod
    def _last_n_month_ranges(n: int) -> list[MonthRange]:
        hoy = timezone.localdate()
        first_this_month = hoy.replace(day=1)
        first = DashboardGraficosService._add_months(first_this_month, -(n - 1))

        labels_es = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
        }

        ranges: list[MonthRange] = []
        for i in range(n):
            start = DashboardGraficosService._add_months(first, i)
            end_exclusive = DashboardGraficosService._add_months(start, 1)
            ranges.append(MonthRange(
                start=start,
                end_exclusive=end_exclusive,
                label=labels_es.get(start.month, str(start.month))
            ))
        return ranges

    @staticmethod
    def _get_student_course(user: User) -> Optional[Curso]:
        perfil = PerfilEstudiante.objects.filter(user=user).first()
        return perfil.curso_actual if perfil else None

    @staticmethod
    def _get_clases_estudiante(user: User, escuela_rbd: int) -> QuerySet[Clase]:
        curso = DashboardGraficosService._get_student_course(user)
        if not curso:
            return Clase.objects.none()
        return Clase.objects.filter(colegio_id=escuela_rbd, curso=curso, activo=True)

    @staticmethod
    @PermissionService.require_permission_any([('ACADEMICO', 'VIEW_ATTENDANCE'), ('ACADEMICO', 'VIEW_OWN_ATTENDANCE')])
    def get_datos_asistencia(user: User, rol: str, escuela_rbd: int) -> dict:
        return DashboardGraficosService.execute('get_datos_asistencia', {
            'user': user,
            'rol': rol,
            'escuela_rbd': escuela_rbd,
        })

    @staticmethod
    def _execute_get_datos_asistencia(params: dict) -> dict:
        """Obtiene datos de asistencia mensual para gráficos."""
        user = params['user']
        rol = params['rol']
        escuela_rbd = params['escuela_rbd']
        has_student_management_scope = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=escuela_rbd)
        has_admin_role_context = rol in ['admin', 'admin_escolar']

        DashboardGraficosService._validate_school_integrity(escuela_rbd, 'GRAFICOS_DATOS_ASISTENCIA')

        labels: list[str] = []
        datos: list[float] = []
        for m in DashboardGraficosService._last_n_month_ranges(6):
            labels.append(m.label)

            qs = Asistencia.objects.filter(
                colegio_id=escuela_rbd,
                fecha__gte=m.start,
                fecha__lt=m.end_exclusive,
            )
            if rol == 'estudiante':
                qs = qs.filter(estudiante=user)
            elif rol == 'profesor':
                clases_ids = list(
                    Clase.objects.filter(colegio_id=escuela_rbd, profesor=user, activo=True).values_list('id', flat=True)
                )
                qs = qs.filter(clase_id__in=clases_ids)
            elif has_student_management_scope or has_admin_role_context:
                pass
            else:
                qs = Asistencia.objects.none()

            total = qs.count()
            presente = qs.exclude(estado='A').count()
            porcentaje = round((presente / total) * 100, 1) if total else 0.0
            datos.append(porcentaje)

        return {'labels': labels, 'data': datos, 'title': 'Asistencia Mensual (%)'}

    @staticmethod
    @PermissionService.require_permission_any([('ACADEMICO', 'VIEW_GRADES'), ('ACADEMICO', 'VIEW_OWN_GRADES')])
    def get_datos_calificaciones(user: User, rol: str, escuela_rbd: int) -> dict:
        return DashboardGraficosService.execute('get_datos_calificaciones', {
            'user': user,
            'rol': rol,
            'escuela_rbd': escuela_rbd,
        })

    @staticmethod
    def _execute_get_datos_calificaciones(params: dict) -> dict:
        """Obtiene datos de calificaciones promedio por asignatura."""
        user = params['user']
        rol = params['rol']
        escuela_rbd = params['escuela_rbd']
        has_student_management_scope = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=escuela_rbd)
        has_admin_role_context = rol in ['admin', 'admin_escolar']

        DashboardGraficosService._validate_school_integrity(escuela_rbd, 'GRAFICOS_DATOS_CALIFICACIONES')

        labels: list[str] = []
        datos: list[float] = []

        try:
            base = Calificacion.objects.filter(colegio_id=escuela_rbd)

            if rol == 'estudiante':
                base = base.filter(estudiante=user)
            elif rol == 'profesor':
                clases_ids = Clase.objects.filter(
                    colegio_id=escuela_rbd,
                    profesor=user,
                    activo=True,
                ).values_list('id', flat=True)
                base = base.filter(evaluacion__clase_id__in=clases_ids)
            elif has_student_management_scope or has_admin_role_context:
                pass
            else:
                base = Calificacion.objects.none()

            rows = (
                base.values('evaluacion__clase__asignatura__nombre')
                .annotate(promedio=Avg('nota'))
                .order_by('-promedio')[:8]
            )

            for item in rows:
                asignatura = item.get('evaluacion__clase__asignatura__nombre') or 'Sin asignatura'
                promedio = item.get('promedio')
                promedio_num = float(promedio) if promedio is not None else 0.0
                labels.append(asignatura[:15])
                datos.append(round(promedio_num, 1))

            if not labels:
                labels = ['Sin datos']
                datos = [0.0]
        except Exception:
            labels = ['Sin datos']
            datos = [0.0]

        return {'labels': labels, 'data': datos, 'title': 'Promedio por Asignatura'}

    @staticmethod
    @PermissionService.require_permission_any([('ACADEMICO', 'VIEW_GRADES'), ('ACADEMICO', 'VIEW_OWN_GRADES')])
    def get_datos_rendimiento(user: User, rol: str, escuela_rbd: int) -> dict:
        return DashboardGraficosService.execute('get_datos_rendimiento', {
            'user': user,
            'rol': rol,
            'escuela_rbd': escuela_rbd,
        })

    @staticmethod
    def _execute_get_datos_rendimiento(params: dict) -> dict:
        """Obtiene distribución de notas por rangos."""
        user = params['user']
        rol = params['rol']
        escuela_rbd = params['escuela_rbd']
        has_student_management_scope = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=escuela_rbd)
        has_admin_role_context = rol in ['admin', 'admin_escolar']

        DashboardGraficosService._validate_school_integrity(escuela_rbd, 'GRAFICOS_DATOS_RENDIMIENTO')

        labels = ['Insuficiente\n(1.0-3.9)', 'Suficiente\n(4.0-4.9)', 'Bueno\n(5.0-5.9)', 'Excelente\n(6.0-7.0)']
        datos = [0, 0, 0, 0]

        base = Calificacion.objects.filter(colegio_id=escuela_rbd)
        if rol == 'estudiante':
            base = base.filter(estudiante=user)
        elif rol == 'profesor':
            clases_ids = Clase.objects.filter(
                colegio_id=escuela_rbd,
                profesor=user,
                activo=True,
            ).values_list('id', flat=True)
            base = base.filter(evaluacion__clase_id__in=clases_ids)
        elif has_student_management_scope or has_admin_role_context:
            pass
        else:
            base = Calificacion.objects.none()

        datos[0] = base.filter(nota__lt=Decimal('4.0')).count()
        datos[1] = base.filter(nota__gte=Decimal('4.0'), nota__lt=Decimal('5.0')).count()
        datos[2] = base.filter(nota__gte=Decimal('5.0'), nota__lt=Decimal('6.0')).count()
        datos[3] = base.filter(nota__gte=Decimal('6.0')).count()

        return {'labels': labels, 'data': datos, 'title': 'Distribución de Notas'}

    @staticmethod
    def get_datos_estadisticas(user: User, rol: str, escuela_rbd: int) -> dict:
        return DashboardGraficosService.execute('get_datos_estadisticas', {
            'user': user,
            'rol': rol,
            'escuela_rbd': escuela_rbd,
        })

    @staticmethod
    def _execute_get_datos_estadisticas(params: dict) -> dict:
        """Obtiene estadísticas generales según rol - sin decorador, validación manual"""
        user = params['user']
        rol = params['rol']
        escuela_rbd = params['escuela_rbd']

        DashboardGraficosService._validate_school_integrity(escuela_rbd, 'GRAFICOS_DATOS_ESTADISTICAS')

        has_student_scope = (
            PolicyService.has_capability(user, 'CLASS_VIEW', school_id=escuela_rbd)
            and PolicyService.has_capability(user, 'GRADE_VIEW', school_id=escuela_rbd)
            and not PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=escuela_rbd)
        )
        has_student_management_scope = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=escuela_rbd)
        has_admin_role_context = rol in ['admin', 'admin_escolar']

        if not has_student_scope and not has_student_management_scope:
            raise PermissionDenied("No tiene permisos para acceder a estadísticas de estudiantes")
        
        try:
            if rol == 'estudiante':
                promedio = Calificacion.objects.filter(
                    colegio_id=escuela_rbd, estudiante=user
                ).aggregate(p=Avg('nota'))['p']

                asist_qs = Asistencia.objects.filter(colegio_id=escuela_rbd, estudiante=user)
                total = asist_qs.count()
                presente = asist_qs.exclude(estado='A').count()
                asistencia_porcentaje = round((presente / total) * 100, 1) if total else 0.0

                clases = DashboardGraficosService._get_clases_estudiante(user, escuela_rbd)
                clases_ids = list(clases.values_list('id', flat=True))

                ahora = timezone.now()
                tareas_qs = Tarea.objects.filter(
                    colegio_id=escuela_rbd,
                    clase_id__in=clases_ids,
                    activa=True,
                    fecha_entrega__gte=ahora,
                )
                tareas_ids = list(tareas_qs.values_list('pk', flat=True))
                entregadas_ids = set(
                    EntregaTarea.objects.filter(estudiante=user, tarea_id__in=tareas_ids).values_list('tarea_id', flat=True)
                )
                tareas_pendientes = max(len(tareas_ids) - len(entregadas_ids), 0)

                hoy = timezone.localdate()
                proximo = hoy + timedelta(days=7)
                evaluaciones_proximas = Evaluacion.objects.filter(
                    colegio_id=escuela_rbd,
                    clase_id__in=clases_ids,
                    fecha_evaluacion__gte=hoy,
                    fecha_evaluacion__lte=proximo,
                    activa=True,
                ).count()

                return {
                    'promedio_general': round(float(promedio), 1) if promedio is not None else 0.0,
                    'asistencia_porcentaje': asistencia_porcentaje,
                    'tareas_pendientes': tareas_pendientes,
                    'evaluaciones_proximas': evaluaciones_proximas,
                }

            if rol == 'profesor':
                clases_ids = list(
                    Clase.objects.filter(colegio_id=escuela_rbd, profesor=user, activo=True).values_list('id', flat=True)
                )

                total_clases = len(clases_ids)
                total_estudiantes = (
                    User.objects.filter(asistencias__clase_id__in=clases_ids)
                    .distinct()
                    .count()
                    if clases_ids
                    else 0
                )

                promedio = Calificacion.objects.filter(
                    colegio_id=escuela_rbd, evaluacion__clase_id__in=clases_ids
                ).aggregate(p=Avg('nota'))['p']

                asist_qs = Asistencia.objects.filter(colegio_id=escuela_rbd, clase_id__in=clases_ids)
                total = asist_qs.count()
                presente = asist_qs.exclude(estado='A').count()
                asistencia_promedio = round((presente / total) * 100, 1) if total else 0.0

                return {
                    'total_clases': total_clases,
                    'total_estudiantes': total_estudiantes,
                    'promedio_clases': round(float(promedio), 1) if promedio is not None else 0.0,
                    'asistencia_promedio': asistencia_promedio,
                }

            if has_student_management_scope and has_admin_role_context:
                total_estudiantes = User.objects.filter(
                    rbd_colegio=escuela_rbd,
                    perfil_estudiante__isnull=False,
                ).count()
                total_profesores = User.objects.filter(
                    rbd_colegio=escuela_rbd,
                    perfil_profesor__isnull=False,
                ).count()
                total_cursos = Curso.objects.filter(colegio_id=escuela_rbd, activo=True).count()

                promedio = Calificacion.objects.filter(colegio_id=escuela_rbd).aggregate(p=Avg('nota'))['p']
                return {
                    'total_estudiantes': total_estudiantes,
                    'total_profesores': total_profesores,
                    'total_cursos': total_cursos,
                    'promedio_general': round(float(promedio), 1) if promedio is not None else 0.0,
                }

            return {'error': 'Rol no soportado'}
        except Exception:
            return {'error': 'No se pudieron cargar las estadísticas'}
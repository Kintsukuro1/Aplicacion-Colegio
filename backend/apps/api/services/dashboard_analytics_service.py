"""
Dashboard Analytics Service
============================

Servicio de métricas ejecutivas avanzadas para el dashboard.
Provee datos para gráficos (tendencias, distribuciones) y alertas.
"""
from __future__ import annotations

from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Avg, Count, Q
from django.conf import settings
from django.core.cache import cache

from backend.apps.accounts.models import User
from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion, RegistroClase
from backend.apps.cursos.models import Clase, ClaseEstudiante, Curso
from backend.apps.subscriptions.utils import (
    get_subscription_status_message,
    get_usage_warnings,
)
from backend.common.services.tenant_cache_service import TenantCacheService


class DashboardAnalyticsService:
    """Genera métricas ejecutivas con datos para gráficos y alertas."""

    @classmethod
    def get_executive_payload(cls, *, user, school_id, scope='auto'):
        """
        Punto de entrada principal. Retorna payload ejecutivo con:
        - kpis: métricas numéricas clave
        - charts: datos para gráficos frontend
        - alerts: alertas activas
        - subscription_alert: estado de suscripción
        - usage_warnings: advertencias de límites
        """
        cache_key = TenantCacheService.build_key(
            'dashboard_executive',
            tenant_id=school_id,
            scope=scope,
            user_id=user.id if scope == 'self' else None,
        )
        cached = cache.get(cache_key)
        if cached:
            return cached

        today = date.today()
        payload = {
            'scope': scope,
            'generated_at': today.isoformat(),
        }

        if scope in ('school', 'analytics', 'auto', 'global'):
            payload['kpis'] = cls._build_kpis(school_id=school_id, today=today)
            payload['charts'] = cls._build_charts(school_id=school_id, today=today)
            payload['alerts'] = cls._build_alerts(school_id=school_id, today=today)
            payload['recent_activity'] = cls._build_recent_activity(school_id=school_id)
        else:
            payload['kpis'] = {}
            payload['charts'] = {}
            payload['alerts'] = []
            payload['recent_activity'] = []

        # Subscription info
        payload.update(cls._build_subscription_info(school_id=school_id))

        cache_timeout = getattr(settings, 'CACHE_TIMEOUT_SHORT', 60) * 2
        cache.set(cache_key, payload, timeout=cache_timeout)
        return payload

    @classmethod
    def _build_charts(cls, *, school_id, today):
        """Construye datos para los gráficos del dashboard."""
        charts = {}

        # 1. Tendencia de asistencia últimos 30 días
        charts['attendance_trend_30d'] = cls._attendance_trend(
            school_id=school_id,
            today=today,
            days=30,
        )

        # 2. Distribución de notas
        charts['grade_distribution'] = cls._grade_distribution(
            school_id=school_id,
        )

        # 3. Asistencia por curso (top 10)
        charts['attendance_by_course'] = cls._attendance_by_course(
            school_id=school_id,
            today=today,
        )

        return charts

    @classmethod
    def _build_kpis(cls, *, school_id, today):
        """Construye KPIs ejecutivos simples y estables."""
        student_qs = ClaseEstudiante.objects.filter(activo=True)
        teacher_qs = User.objects.filter(role__nombre__iexact='Profesor')
        attendance_today = Asistencia.objects.filter(fecha=today)
        grades_qs = Calificacion.objects.all()
        evaluations_qs = Evaluacion.objects.filter(activa=True)
        classes_qs = Clase.objects.filter(activo=True)

        if school_id is not None:
            student_qs = student_qs.filter(clase__colegio_id=school_id)
            teacher_qs = teacher_qs.filter(rbd_colegio=school_id)
            attendance_today = attendance_today.filter(colegio_id=school_id)
            grades_qs = grades_qs.filter(colegio_id=school_id)
            evaluations_qs = evaluations_qs.filter(colegio_id=school_id)
            classes_qs = classes_qs.filter(colegio_id=school_id)

        total_students = student_qs.values('estudiante_id').distinct().count()
        total_teachers = teacher_qs.count()

        attendance_total = attendance_today.count()
        attendance_present = attendance_today.filter(estado='P').count()
        attendance_rate_today = round((attendance_present / attendance_total) * 100, 1) if attendance_total else 0

        nota_aprobacion = 4.0
        try:
            from backend.apps.institucion.models import Colegio
            from backend.common.utils.grade_scale import get_escala

            colegio = Colegio.objects.get(rbd=school_id)
            escala = get_escala(colegio)
            nota_aprobacion = float(escala['nota_aprobacion'])
        except Exception:
            pass

        grades_below_threshold = grades_qs.filter(nota__lt=nota_aprobacion).values('estudiante_id').distinct().count()

        upcoming_evaluations = evaluations_qs.filter(
            activa=True,
            fecha_evaluacion__gte=today,
            fecha_evaluacion__lte=today + timedelta(days=7),
        ).count()

        active_classes = classes_qs.count()

        return {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'attendance_today_total': attendance_total,
            'attendance_today_present': attendance_present,
            'attendance_rate_today': attendance_rate_today,
            'grades_below_threshold': grades_below_threshold,
            'upcoming_evaluations': upcoming_evaluations,
            'active_classes': active_classes,
        }

    @classmethod
    def _build_recent_activity(cls, *, school_id, limit=8):
        """Une las acciones recientes más visibles del colegio en una sola lista."""
        activities = []

        evaluations_qs = Evaluacion.objects.all()
        class_logs_qs = RegistroClase.objects.all()
        grades_qs = Calificacion.objects.all()
        attendance_qs = Asistencia.objects.all()
        if school_id is not None:
            evaluations_qs = evaluations_qs.filter(colegio_id=school_id)
            class_logs_qs = class_logs_qs.filter(colegio_id=school_id)
            grades_qs = grades_qs.filter(colegio_id=school_id)
            attendance_qs = attendance_qs.filter(colegio_id=school_id)

        evaluations = (
            evaluations_qs
            .select_related('clase__curso', 'clase__asignatura')
            .order_by('-fecha_creacion')[:4]
        )
        for evaluacion in evaluations:
            activities.append(
                {
                    'type': 'evaluacion',
                    'icon': '📝',
                    'title': 'Evaluación creada',
                    'subject': evaluacion.clase.asignatura.nombre if evaluacion.clase and evaluacion.clase.asignatura else '',
                    'course': evaluacion.clase.curso.nombre if evaluacion.clase and evaluacion.clase.curso else '',
                    'detail': evaluacion.nombre,
                    'timestamp': evaluacion.fecha_creacion.isoformat() if evaluacion.fecha_creacion else None,
                }
            )

        class_logs = (
            class_logs_qs
            .select_related('clase__curso', 'clase__asignatura', 'profesor')
            .order_by('-fecha_creacion')[:4]
        )
        for registro in class_logs:
            activities.append(
                {
                    'type': 'clase',
                    'icon': '🏫',
                    'title': 'Registro de clase',
                    'subject': registro.clase.asignatura.nombre if registro.clase and registro.clase.asignatura else '',
                    'course': registro.clase.curso.nombre if registro.clase and registro.clase.curso else '',
                    'detail': f'Bloque {registro.numero_clase} por {registro.profesor.get_full_name() or registro.profesor.email}',
                    'timestamp': registro.fecha_creacion.isoformat() if registro.fecha_creacion else None,
                }
            )

        grades = (
            grades_qs
            .select_related('evaluacion__clase__curso', 'evaluacion__clase__asignatura', 'estudiante', 'registrado_por')
            .order_by('-fecha_creacion')[:4]
        )
        for calificacion in grades:
            activities.append(
                {
                    'type': 'calificacion',
                    'icon': '⭐',
                    'title': 'Calificación registrada',
                    'subject': calificacion.evaluacion.clase.asignatura.nombre if calificacion.evaluacion and calificacion.evaluacion.clase and calificacion.evaluacion.clase.asignatura else '',
                    'course': calificacion.evaluacion.clase.curso.nombre if calificacion.evaluacion and calificacion.evaluacion.clase and calificacion.evaluacion.clase.curso else '',
                    'detail': f"{calificacion.estudiante.get_full_name()}: {calificacion.nota}",
                    'timestamp': calificacion.fecha_creacion.isoformat() if calificacion.fecha_creacion else None,
                }
            )

        attendance = (
            attendance_qs
            .select_related('clase__curso', 'clase__asignatura', 'estudiante')
            .order_by('-fecha_creacion')[:4]
        )
        for asistencia in attendance:
            activities.append(
                {
                    'type': 'asistencia',
                    'icon': '✅',
                    'title': 'Asistencia tomada',
                    'subject': asistencia.clase.asignatura.nombre if asistencia.clase and asistencia.clase.asignatura else '',
                    'course': asistencia.clase.curso.nombre if asistencia.clase and asistencia.clase.curso else '',
                    'detail': f"{asistencia.estudiante.get_full_name()} · {asistencia.get_estado_display()}",
                    'timestamp': asistencia.fecha_creacion.isoformat() if asistencia.fecha_creacion else None,
                }
            )

        activities.sort(key=lambda item: item.get('timestamp') or '', reverse=True)
        return activities[:limit]

    @classmethod
    def _attendance_trend(cls, *, school_id, today, days=30):
        """
        Calcula tasa de asistencia diaria para los últimos N días.
        Retorna lista de {date, present, absent, total, rate}.
        """
        start_date = today - timedelta(days=days - 1)
        base_qs = Asistencia.objects.all()
        if school_id is not None:
            base_qs = base_qs.filter(colegio_id=school_id)

        # Agrupar por fecha
        daily = (
            base_qs
            .filter(fecha__gte=start_date, fecha__lte=today)
            .values('fecha')
            .annotate(
                total=Count('id_asistencia'),
                present=Count('id_asistencia', filter=Q(estado='P')),
            )
            .order_by('fecha')
        )

        # Crear mapa de fecha → datos
        daily_map = {
            row['fecha']: {
                'total': row['total'],
                'present': row['present'],
            }
            for row in daily
        }

        result = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            info = daily_map.get(d, {'total': 0, 'present': 0})
            total = info['total']
            present = info['present']
            rate = round((present / total) * 100, 1) if total > 0 else 0
            result.append({
                'date': d.isoformat(),
                'present': present,
                'absent': total - present,
                'total': total,
                'rate': rate,
            })

        return result

    @classmethod
    def _grade_distribution(cls, *, school_id):
        """
        Distribución de notas por rango (1-2, 2-3, ..., 6-7).
        Retorna lista de {range, count, color}.
        """
        base_qs = Calificacion.objects.all()
        if school_id is not None:
            base_qs = base_qs.filter(colegio_id=school_id)

        # Obtener escala del colegio
        nota_aprobacion = 4.0
        try:
            from backend.apps.institucion.models import Colegio
            from backend.common.utils.grade_scale import get_escala
            colegio = Colegio.objects.get(rbd=school_id)
            escala = get_escala(colegio)
            nota_aprobacion = float(escala['nota_aprobacion'])
        except Exception:
            pass

        ranges = [
            ('1.0-2.0', 1.0, 2.0),
            ('2.0-3.0', 2.0, 3.0),
            ('3.0-4.0', 3.0, 4.0),
            ('4.0-5.0', 4.0, 5.0),
            ('5.0-6.0', 5.0, 6.0),
            ('6.0-7.0', 6.0, 7.01),
        ]

        colors = ['#f43f5e', '#f97316', '#f59e0b', '#84cc16', '#10b981', '#6366f1']

        result = []
        for i, (label, low, high) in enumerate(ranges):
            count = base_qs.filter(nota__gte=low, nota__lt=high).count()
            result.append({
                'range': label,
                'label': label,
                'count': count,
                'color': colors[i],
                'below_approval': high <= nota_aprobacion,
            })

        return result

    @classmethod
    def _attendance_by_course(cls, *, school_id, today, limit=10):
        """
        Tasa de asistencia promedio por curso en el mes actual.
        Retorna lista de {course, rate, total, present}.
        """
        primer_dia_mes = today.replace(day=1)
        base_qs = Asistencia.objects.filter(
            fecha__gte=primer_dia_mes,
            fecha__lte=today,
        )
        if school_id is not None:
            base_qs = base_qs.filter(colegio_id=school_id)

        # Obtener asistencia por clase → curso
        by_clase = (
            base_qs
            .values('clase_id', 'clase__curso__nombre')
            .annotate(
                total=Count('id_asistencia'),
                present=Count('id_asistencia', filter=Q(estado='P')),
            )
            .order_by('-total')[:limit * 2]  # Get extra to merge by curso
        )

        # Agrupar por nombre de curso
        curso_data = defaultdict(lambda: {'total': 0, 'present': 0})
        for row in by_clase:
            curso_nombre = row['clase__curso__nombre'] or 'Sin Curso'
            curso_data[curso_nombre]['total'] += row['total']
            curso_data[curso_nombre]['present'] += row['present']

        result = []
        for curso, info in sorted(curso_data.items(), key=lambda x: -x[1]['total']):
            rate = round((info['present'] / info['total']) * 100, 1) if info['total'] > 0 else 0
            result.append({
                'course': curso,
                'rate': rate,
                'total': info['total'],
                'present': info['present'],
            })
            if len(result) >= limit:
                break

        return result

    @classmethod
    def _build_alerts(cls, *, school_id, today):
        """Genera alertas basadas en métricas actuales."""
        alerts = []

        # Asistencia baja hoy
        att_today = Asistencia.objects.filter(fecha=today)
        if school_id is not None:
            att_today = att_today.filter(colegio_id=school_id)
        total = att_today.count()
        if total > 0:
            present = att_today.filter(estado='P').count()
            rate = round((present / total) * 100, 1)
            if rate < 70:
                alerts.append({
                    'type': 'danger',
                    'icon': '📉',
                    'message': f'Asistencia crítica hoy: {rate}% ({present}/{total} presentes).',
                })
            elif rate < 85:
                alerts.append({
                    'type': 'warning',
                    'icon': '⚠️',
                    'message': f'Asistencia moderada hoy: {rate}% ({present}/{total} presentes).',
                })

        # Evaluaciones próximas
        next_3 = today + timedelta(days=3)
        eval_qs = Evaluacion.objects.filter(
            activa=True,
            fecha_evaluacion__gte=today,
            fecha_evaluacion__lte=next_3,
        )
        if school_id is not None:
            eval_qs = eval_qs.filter(colegio_id=school_id)
        eval_count = eval_qs.count()
        if eval_count > 0:
            alerts.append({
                'type': 'info',
                'icon': '📝',
                'message': f'{eval_count} evaluación(es) programada(s) en los próximos 3 días.',
            })

        # Notas bajo aprobación
        nota_aprobacion = 4.0
        try:
            from backend.apps.institucion.models import Colegio
            from backend.common.utils.grade_scale import get_escala
            colegio = Colegio.objects.get(rbd=school_id)
            escala = get_escala(colegio)
            nota_aprobacion = float(escala['nota_aprobacion'])
        except Exception:
            pass

        grade_qs = Calificacion.objects.filter(nota__lt=nota_aprobacion)
        if school_id is not None:
            grade_qs = grade_qs.filter(colegio_id=school_id)
        below_count = grade_qs.values('estudiante_id').distinct().count()

        if below_count > 10:
            alerts.append({
                'type': 'warning',
                'icon': '📊',
                'message': f'{below_count} estudiantes con notas bajo {nota_aprobacion}.',
            })

        return alerts

    @classmethod
    def _build_subscription_info(cls, *, school_id):
        """Obtiene información de suscripción y advertencias de uso."""
        result = {
            'subscription_alert': None,
            'usage_warnings': [],
        }

        if school_id is None:
            return result

        try:
            from backend.apps.subscriptions.models import Subscription
            sub = Subscription.objects.select_related('plan').get(
                colegio__rbd=school_id
            )
            result['subscription_alert'] = get_subscription_status_message(sub)
            result['usage_warnings'] = get_usage_warnings(sub)
        except Exception:
            pass

        return result

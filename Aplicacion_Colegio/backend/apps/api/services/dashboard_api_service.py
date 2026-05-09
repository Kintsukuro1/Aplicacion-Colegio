from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from backend.apps.accounts.models import User
from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion
from backend.apps.api.contracts import (
    DASHBOARD_ALLOWED_SCOPES,
    DASHBOARD_CONTRACT_VERSION,
    DASHBOARD_SCOPE_AUTO,
)
from backend.apps.cursos.models import Clase, ClaseEstudiante, Curso
from backend.common.services.policy_service import PolicyService
from backend.common.services.tenant_cache_service import TenantCacheService


class DashboardApiService:
    """Construye payloads de dashboard para la capa API."""

    @staticmethod
    def _is_global_admin(user) -> bool:
        return PolicyService.has_capability(user, 'SYSTEM_ADMIN')

    @staticmethod
    def _has_capability(user, capability: str) -> bool:
        return PolicyService.has_capability(
            user,
            capability,
            school_id=getattr(user, 'rbd_colegio', None),
        )

    @classmethod
    def _is_teacher_user(cls, user) -> bool:
        role_name = getattr(getattr(user, 'role', None), 'nombre', '') or ''
        return role_name.strip().lower() == 'profesor'

    @classmethod
    def _require_dashboard_capability(cls, user) -> bool:
        required = {
            'DASHBOARD_VIEW_SELF',
            'DASHBOARD_VIEW_SCHOOL',
            'DASHBOARD_VIEW_ANALYTICS',
        }
        return any(cls._has_capability(user, cap) for cap in required)

    @classmethod
    def _dashboard_scopes_for_user(cls, user):
        if cls._is_global_admin(user):
            return {'self', 'school', 'analytics', 'global'}

        scopes = set()
        if cls._has_capability(user, 'DASHBOARD_VIEW_SELF'):
            scopes.add('self')
        if cls._has_capability(user, 'DASHBOARD_VIEW_SCHOOL'):
            scopes.add('school')
        if cls._has_capability(user, 'DASHBOARD_VIEW_ANALYTICS'):
            scopes.add('analytics')
        return scopes

    @classmethod
    def _resolve_dashboard_scope(cls, *, requested_scope: str, allowed_scopes):
        requested = (requested_scope or DASHBOARD_SCOPE_AUTO).strip().lower()
        if requested == DASHBOARD_SCOPE_AUTO:
            for candidate in ('analytics', 'school', 'self'):
                if candidate in allowed_scopes:
                    return candidate
            return None
        if requested not in DASHBOARD_ALLOWED_SCOPES:
            raise ValidationError({'scope': 'Valor invalido. Use self, school, analytics o auto.'})
        if requested not in allowed_scopes:
            return None
        return requested

    @classmethod
    def _base_dashboard_context(cls, user, *, scope, school_id):
        role_name = getattr(getattr(user, 'role', None), 'nombre', None)
        return {
            'contract_version': DASHBOARD_CONTRACT_VERSION,
            'scope': scope,
            'generated_at': date.today().isoformat(),
            'context': {
                'user_id': user.id,
                'role': role_name,
                'school_id': school_id,
                'colegio_id': school_id,
                'is_global_admin': cls._is_global_admin(user),
            },
        }

    @classmethod
    def _build_self_section(cls, user, *, today):
        """Construye la sección 'self' del dashboard con métricas por rol."""
        role_name = getattr(getattr(user, 'role', None), 'nombre', '') or ''
        role_key = role_name.strip().lower()
        school_id = getattr(user, 'rbd_colegio', None)

        base = {'today': today.isoformat(), 'role': role_name}

        if role_key == 'profesor':
            base.update(cls._build_teacher_self(user, today=today, school_id=school_id))
        elif role_key in {'estudiante', 'alumno'}:
            base.update(cls._build_student_self(user, today=today, school_id=school_id))
        elif role_key == 'apoderado':
            base.update(cls._build_apoderado_self(user, today=today, school_id=school_id))
        elif role_key in {'administrador escolar', 'admin_escolar'}:
            base.update(cls._build_admin_escolar_self(user, today=today, school_id=school_id))
        elif role_key in {'administrador general', 'admin_general', 'super admin'}:
            base.update(cls._build_admin_general_self(user, today=today, school_id=school_id))
        else:
            base.update({'my_classes': 0, 'my_attendance_today': 0, 'my_evaluations': 0})

        return base

    # ── Estudiante ──────────────────────────────────────────

    @classmethod
    def _build_student_self(cls, user, *, today, school_id):
        from django.db.models import Avg
        from backend.apps.accounts.models import PerfilEstudiante
        from backend.apps.academico.models import Tarea, EntregaTarea
        from backend.common.utils.grade_scale import get_escala

        data = {
            'mis_clases': ClaseEstudiante.objects.filter(estudiante_id=user.id, activo=True).count(),
            'promedio_general': None,
            'porcentaje_asistencia': 100.0,
            'tareas_pendientes': 0,
            'proximas_evaluaciones': [],
            'nota_aprobacion': None,
        }

        # Promedio general
        avg = Calificacion.objects.filter(
            estudiante_id=user.id, colegio_id=school_id
        ).aggregate(avg=Avg('nota'))['avg']
        if avg is not None:
            data['promedio_general'] = round(float(avg), 1)

        # Escala del colegio
        try:
            from backend.apps.institucion.models import Colegio
            colegio = Colegio.objects.get(rbd=school_id)
            escala = get_escala(colegio)
            data['nota_aprobacion'] = float(escala['nota_aprobacion'])
        except Exception:
            data['nota_aprobacion'] = 4.0

        # Porcentaje de asistencia
        att_total = Asistencia.objects.filter(
            estudiante_id=user.id, colegio_id=school_id
        ).count()
        if att_total > 0:
            att_present = Asistencia.objects.filter(
                estudiante_id=user.id, colegio_id=school_id, estado='P'
            ).count()
            data['porcentaje_asistencia'] = round((att_present / att_total) * 100, 1)

        # Tareas pendientes
        try:
            perfil = PerfilEstudiante.objects.get(user=user)
            curso_actual = perfil.curso_actual
            if curso_actual:
                tareas_del_curso = Tarea.objects.filter(
                    clase__curso=curso_actual, activa=True, es_publica=True
                ).values_list('id_tarea', flat=True)
                entregadas = set(
                    EntregaTarea.objects.filter(
                        estudiante=user, tarea_id__in=tareas_del_curso
                    ).values_list('tarea_id', flat=True)
                )
                data['tareas_pendientes'] = len(set(tareas_del_curso) - entregadas)
        except PerfilEstudiante.DoesNotExist:
            pass

        # Próximas evaluaciones (7 días)
        next_7 = today + timedelta(days=7)
        upcoming = Evaluacion.objects.filter(
            clase__in=ClaseEstudiante.objects.filter(
                estudiante_id=user.id, activo=True
            ).values_list('clase_id', flat=True),
            activa=True,
            fecha_evaluacion__gte=today,
            fecha_evaluacion__lte=next_7,
        ).select_related('clase__asignatura').order_by('fecha_evaluacion')[:5]
        data['proximas_evaluaciones'] = [
            {
                'nombre': ev.nombre,
                'asignatura': ev.clase.asignatura.nombre if ev.clase and ev.clase.asignatura else '',
                'fecha': ev.fecha_evaluacion.isoformat() if ev.fecha_evaluacion else None,
                'tipo': ev.tipo_evaluacion or '',
            }
            for ev in upcoming
        ]

        return data

    # ── Profesor ────────────────────────────────────────────

    @classmethod
    def _build_teacher_self(cls, user, *, today, school_id):
        from django.db.models import Avg, Count
        from backend.apps.academico.models import Tarea, EntregaTarea

        teacher_classes = Clase.objects.filter(
            profesor_id=user.id, colegio_id=school_id, activo=True
        )
        teacher_class_ids = list(teacher_classes.values_list('id', flat=True))

        # Clases hoy (por bloques)
        from backend.apps.cursos.models import BloqueHorario
        dia_semana = today.weekday() + 1
        clases_hoy = BloqueHorario.objects.filter(
            clase_id__in=teacher_class_ids,
            dia_semana=dia_semana,
            activo=True,
        ).select_related('clase__asignatura', 'clase__curso').order_by('hora_inicio')
        clases_hoy_list = [
            {
                'asignatura': b.clase.asignatura.nombre if b.clase.asignatura else '',
                'curso': b.clase.curso.nombre if b.clase.curso else '',
                'hora_inicio': b.hora_inicio.strftime('%H:%M'),
                'hora_fin': b.hora_fin.strftime('%H:%M'),
                'bloque': b.bloque_numero,
            }
            for b in clases_hoy
        ]

        # Evaluaciones activas
        eval_count = Evaluacion.objects.filter(
            clase_id__in=teacher_class_ids, activa=True
        ).count()

        # Promedio general de notas del profesor
        avg = Calificacion.objects.filter(
            evaluacion__clase_id__in=teacher_class_ids
        ).aggregate(avg=Avg('nota'))['avg']
        promedio_general = round(float(avg), 1) if avg is not None else None

        # Tareas por revisar
        tareas_sin_revisar = 0
        try:
            tareas_activas = Tarea.objects.filter(
                clase_id__in=teacher_class_ids, activa=True
            ).values_list('id_tarea', flat=True)
            tareas_sin_revisar = EntregaTarea.objects.filter(
                tarea_id__in=tareas_activas,
                calificacion__isnull=True,
            ).count()
        except Exception:
            pass

        # Total estudiantes distintos
        total_estudiantes = ClaseEstudiante.objects.filter(
            clase_id__in=teacher_class_ids, activo=True
        ).values('estudiante_id').distinct().count()

        # Asistencia pendiente hoy
        clases_sin_asistencia_hoy = teacher_classes.exclude(
            asistencias__fecha=today
        ).count()

        return {
            'mis_clases': len(teacher_class_ids),
            'clases_hoy': clases_hoy_list,
            'total_clases_hoy': len(clases_hoy_list),
            'mis_evaluaciones': eval_count,
            'promedio_general': promedio_general,
            'tareas_por_revisar': tareas_sin_revisar,
            'total_estudiantes': total_estudiantes,
            'asistencia_pendiente_hoy': clases_sin_asistencia_hoy,
        }

    # ── Apoderado ───────────────────────────────────────────

    @classmethod
    def _build_apoderado_self(cls, user, *, today, school_id):
        from django.db.models import Avg
        from backend.apps.accounts.models import Apoderado, RelacionApoderadoEstudiante
        from backend.apps.matriculas.models import EstadoCuenta
        from backend.apps.comunicados.models import Comunicado, ConfirmacionLectura

        data = {
            'pupilos': [],
            'pagos_pendientes': 0,
            'total_deuda': 0,
            'comunicados_sin_leer': 0,
        }

        try:
            apoderado = Apoderado.objects.get(user=user)
        except Apoderado.DoesNotExist:
            return data

        # Pupilos con métricas
        relaciones = RelacionApoderadoEstudiante.objects.filter(
            apoderado=apoderado, activa=True
        ).select_related('estudiante')

        for rel in relaciones:
            est = rel.estudiante
            avg = Calificacion.objects.filter(
                estudiante_id=est.id, colegio_id=school_id
            ).aggregate(avg=Avg('nota'))['avg']

            att_total = Asistencia.objects.filter(
                estudiante_id=est.id, colegio_id=school_id
            ).count()
            att_pct = 100.0
            if att_total > 0:
                att_present = Asistencia.objects.filter(
                    estudiante_id=est.id, colegio_id=school_id, estado='P'
                ).count()
                att_pct = round((att_present / att_total) * 100, 1)

            data['pupilos'].append({
                'id': est.id,
                'nombre': est.get_full_name(),
                'promedio': round(float(avg), 1) if avg else None,
                'porcentaje_asistencia': att_pct,
                'parentesco': rel.parentesco,
            })

        # Pagos pendientes
        cuentas_pendientes = EstadoCuenta.objects.filter(
            estudiante_id__in=[r.estudiante_id for r in relaciones],
            colegio_id=school_id,
            estado__in=['GENERADO', 'ENVIADO'],
        )
        data['pagos_pendientes'] = cuentas_pendientes.count()
        data['total_deuda'] = float(
            sum(c.saldo_pendiente for c in cuentas_pendientes)
        )

        # Comunicados sin leer
        comunicados_enviados = Comunicado.objects.filter(
            colegio_id=school_id,
            estado='ENVIADO',
        ).values_list('id', flat=True)
        leidos = set(
            ConfirmacionLectura.objects.filter(
                usuario=user,
                comunicado_id__in=comunicados_enviados,
            ).values_list('comunicado_id', flat=True)
        )
        data['comunicados_sin_leer'] = len(set(comunicados_enviados) - leidos)

        return data

    # ── Administrador Escolar ───────────────────────────────

    @classmethod
    def _build_admin_escolar_self(cls, user, *, today, school_id):
        from django.db.models import Avg, Sum
        from backend.apps.matriculas.models import Matricula, EstadoCuenta

        # Matrícula total
        matriculas_activas = Matricula.objects.filter(
            colegio_id=school_id, estado='ACTIVA'
        ).count()

        # Estudiantes activos
        student_qs = User.objects.filter(
            Q(role__nombre__iexact='Estudiante') | Q(role__nombre__iexact='Alumno'),
            rbd_colegio=school_id, is_active=True,
        )
        total_estudiantes = student_qs.count()

        # Profesores activos
        total_profesores = User.objects.filter(
            role__nombre__iexact='Profesor',
            rbd_colegio=school_id, is_active=True,
        ).count()

        # Cursos activos
        total_cursos = Curso.objects.filter(
            colegio_id=school_id, activo=True
        ).count()

        # Asistencia promedio del mes
        primer_dia_mes = today.replace(day=1)
        att_mes = Asistencia.objects.filter(
            colegio_id=school_id,
            fecha__gte=primer_dia_mes,
            fecha__lte=today,
        )
        att_total = att_mes.count()
        att_pct = 0.0
        if att_total > 0:
            att_present = att_mes.filter(estado='P').count()
            att_pct = round((att_present / att_total) * 100, 1)

        # Morosidad
        cuentas_pendientes = EstadoCuenta.objects.filter(
            colegio_id=school_id,
            estado__in=['GENERADO', 'ENVIADO'],
        )
        total_morosidad = float(
            cuentas_pendientes.aggregate(total=Sum('saldo_pendiente'))['total'] or 0
        )
        alumnos_morosos = cuentas_pendientes.values('estudiante_id').distinct().count()

        # Evaluaciones próximos 7 días
        next_7 = today + timedelta(days=7)
        evaluaciones_proximas = Evaluacion.objects.filter(
            colegio_id=school_id,
            activa=True,
            fecha_evaluacion__gte=today,
            fecha_evaluacion__lte=next_7,
        ).count()

        return {
            'matriculas_activas': matriculas_activas,
            'total_estudiantes': total_estudiantes,
            'total_profesores': total_profesores,
            'total_cursos': total_cursos,
            'asistencia_promedio_mes': att_pct,
            'total_morosidad': total_morosidad,
            'alumnos_morosos': alumnos_morosos,
            'evaluaciones_proximas': evaluaciones_proximas,
        }

    # ── Administrador General ───────────────────────────────

    @classmethod
    def _build_admin_general_self(cls, user, *, today, school_id):
        return cls._build_admin_general_global_self(today=today)

    @staticmethod
    def _build_admin_general_global_self(*, today):
        from django.db.models import Sum
        from backend.apps.matriculas.models import Matricula, EstadoCuenta

        primer_dia_mes = today.replace(day=1)
        att_mes = Asistencia.objects.filter(fecha__gte=primer_dia_mes, fecha__lte=today)
        att_total = att_mes.count()
        att_pct = 0.0
        if att_total > 0:
            att_present = att_mes.filter(estado='P').count()
            att_pct = round((att_present / att_total) * 100, 1)

        cuentas_pendientes = EstadoCuenta.objects.filter(estado__in=['GENERADO', 'ENVIADO'])
        next_7 = today + timedelta(days=7)

        data = {
            'matriculas_activas': Matricula.objects.filter(estado='ACTIVA').count(),
            'total_estudiantes': User.objects.filter(
                Q(role__nombre__iexact='Estudiante') | Q(role__nombre__iexact='Alumno'),
                is_active=True,
            ).count(),
            'total_profesores': User.objects.filter(role__nombre__iexact='Profesor', is_active=True).count(),
            'total_cursos': Curso.objects.filter(activo=True).count(),
            'asistencia_promedio_mes': att_pct,
            'total_morosidad': float(cuentas_pendientes.aggregate(total=Sum('saldo_pendiente'))['total'] or 0),
            'alumnos_morosos': cuentas_pendientes.values('estudiante_id').distinct().count(),
            'evaluaciones_proximas': Evaluacion.objects.filter(
                activa=True,
                fecha_evaluacion__gte=today,
                fecha_evaluacion__lte=next_7,
            ).count(),
        }

        try:
            from backend.apps.subscriptions.models import Subscription
            data['suscripciones_activas'] = Subscription.objects.filter(status='active').count()
            data['suscripciones_vencidas'] = Subscription.objects.filter(status='expired').count()
        except Exception:
            data['suscripciones_activas'] = 0
            data['suscripciones_vencidas'] = 0

        return data

    @classmethod
    def _build_admin_general_school_self(cls, user, *, today, school_id):
        """Admin general ve datos del colegio más métricas globales."""
        # Reutilizar admin escolar como base
        data = cls._build_admin_escolar_self(user, today=today, school_id=school_id)

        # Agregar métricas globales
        try:
            from backend.apps.subscriptions.models import Subscription
            sub = Subscription.objects.select_related('plan').filter(
                colegio_id=school_id, status='active'
            ).first()
            if sub:
                data['plan_actual'] = sub.plan.nombre if sub.plan else None
                data['estado_suscripcion'] = sub.status
            else:
                data['plan_actual'] = None
                data['estado_suscripcion'] = None
        except Exception:
            data['plan_actual'] = None
            data['estado_suscripcion'] = None

        return data

    @staticmethod
    def _build_school_section(*, today, school_id=None):
        student_qs = User.objects.filter(Q(role__nombre__iexact='Estudiante') | Q(role__nombre__iexact='Alumno'))
        teacher_qs = User.objects.filter(role__nombre__iexact='Profesor')
        course_qs = Curso.objects.filter(activo=True)
        class_qs = Clase.objects.filter(activo=True)
        attendance_qs = Asistencia.objects
        eval_qs = Evaluacion.objects.filter(activa=True)

        if school_id is not None:
            student_qs = student_qs.filter(rbd_colegio=school_id)
            teacher_qs = teacher_qs.filter(rbd_colegio=school_id)
            course_qs = course_qs.filter(colegio_id=school_id)
            class_qs = class_qs.filter(colegio_id=school_id)
            attendance_qs = attendance_qs.filter(colegio_id=school_id)
            eval_qs = eval_qs.filter(colegio_id=school_id)

        return {
            'today': today.isoformat(),
            'school_id': school_id,
            'colegio_id': school_id,
            'students': student_qs.count(),
            'teachers': teacher_qs.count(),
            'courses_active': course_qs.count(),
            'classes_active': class_qs.count(),
            'attendance_today': attendance_qs.filter(fecha=today).count(),
            'evaluations_upcoming': eval_qs.filter(fecha_evaluacion__gte=today).count(),
        }

    @staticmethod
    def _build_analytics_section(*, today, school_id=None):
        attendance_qs = Asistencia.objects
        eval_qs = Evaluacion.objects.filter(activa=True)
        grades_qs = Calificacion.objects
        if school_id is not None:
            attendance_qs = attendance_qs.filter(colegio_id=school_id)
            eval_qs = eval_qs.filter(colegio_id=school_id)
            grades_qs = grades_qs.filter(colegio_id=school_id)

        attendance_today_total = attendance_qs.filter(fecha=today).count()
        attendance_today_present = attendance_qs.filter(fecha=today, estado='P').count()
        attendance_rate = 0.0
        if attendance_today_total:
            attendance_rate = round((attendance_today_present * 100.0) / attendance_today_total, 2)

        # Obtener umbral de aprobación del colegio
        nota_aprobacion = 4.0
        if school_id is not None:
            from backend.apps.institucion.models import Colegio
            try:
                from backend.common.utils.grade_scale import get_escala
                colegio = Colegio.objects.get(rbd=school_id)
                escala = get_escala(colegio)
                nota_aprobacion = float(escala['nota_aprobacion'])
            except Exception:
                pass

        next_7_days = today + timedelta(days=7)
        return {
            'today': today.isoformat(),
            'school_id': school_id,
            'colegio_id': school_id,
            'attendance_today_total': attendance_today_total,
            'attendance_today_present': attendance_today_present,
            'attendance_rate_today': attendance_rate,
            'evaluations_next_7_days': eval_qs.filter(
                fecha_evaluacion__gte=today,
                fecha_evaluacion__lte=next_7_days,
            ).count(),
            'grades_below_approval': grades_qs.filter(nota__lt=nota_aprobacion).count(),
            'nota_aprobacion': nota_aprobacion,
        }

    @classmethod
    def build_dashboard_payload(cls, *, user, query_params):
        if not cls._require_dashboard_capability(user) and not cls._is_global_admin(user):
            raise PermissionDenied('No tiene permisos para ver dashboard.')

        today = date.today()
        allowed_scopes = cls._dashboard_scopes_for_user(user)
        scope = cls._resolve_dashboard_scope(
            requested_scope=query_params.get('scope'),
            allowed_scopes=allowed_scopes,
        )
        if scope is None:
            raise PermissionDenied('No tiene permisos para el scope solicitado.')

        school_id = query_params.get('colegio_id') or getattr(user, 'rbd_colegio', None)

        if school_id is not None:
            try:
                school_id = int(school_id)
            except (TypeError, ValueError):
                raise ValidationError({'colegio_id': 'Debe ser un entero valido.'})

        if not cls._is_global_admin(user) and school_id is None:
            raise ValidationError({'colegio_id': 'Usuario sin colegio asignado.'})

        if scope == 'global' and not cls._is_global_admin(user):
            raise PermissionDenied('Scope global no permitido.')

        if scope != 'global' and school_id is None and scope in {'school', 'analytics'} and not cls._is_global_admin(user):
            raise ValidationError({'colegio_id': 'Scope school/analytics requiere colegio_id.'})

        effective_school_id = None if scope == 'global' else school_id

        cache_key = TenantCacheService.build_key(
            'dashboard_summary',
            tenant_id=effective_school_id,
            scope=scope,
            user_id=user.id if scope == 'self' else None,
        )
        cached_payload = cache.get(cache_key)
        if cached_payload:
            return cached_payload

        payload = cls._base_dashboard_context(user, scope=scope, school_id=effective_school_id)
        payload['available_scopes'] = sorted(allowed_scopes)

        sections = {
            'self': None,
            'school': None,
            'analytics': None,
        }

        if scope == 'self':
            sections['self'] = cls._build_self_section(user, today=today)
        elif scope == 'school':
            sections['school'] = cls._build_school_section(today=today, school_id=effective_school_id)
        elif scope == 'analytics':
            sections['analytics'] = cls._build_analytics_section(today=today, school_id=effective_school_id)
        elif scope == 'global':
            sections['school'] = cls._build_school_section(today=today, school_id=None)
            sections['analytics'] = cls._build_analytics_section(today=today, school_id=None)

        payload['sections'] = sections
        cache.set(cache_key, payload, timeout=getattr(settings, 'CACHE_TIMEOUT_SHORT', 60))
        return payload

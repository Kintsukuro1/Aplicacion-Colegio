"""
Views y Serializers para funcionalidades Semana 5-6.

1. Confirmación de comunicados desde API
2. Reportes de tendencias para el profesor
3. Calendario escolar académico (CRUD + consulta pública)
"""
import logging
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.accounts.models import User
from backend.apps.api.base import CapabilityModelViewSet
from backend.apps.api.permissions import HasCapability
from backend.apps.comunicados.models import (
    Comunicado,
    ConfirmacionLectura,
    EstadisticaComunicado,
)
from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion
from backend.apps.cursos.models import Clase, ClaseEstudiante
from backend.apps.institucion.models import EventoCalendario
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.common.services.policy_service import PolicyService

logger = logging.getLogger('api')


def _is_global_admin(user):
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN')


def _school_id(request):
    return resolve_request_rbd(request)


# ═══════════════════════════════════════════════
# 1. CONFIRMACIÓN DE COMUNICADOS
# ═══════════════════════════════════════════════

class ConfirmacionSerializer(serializers.Serializer):
    """Body para confirmar un comunicado."""
    observaciones = serializers.CharField(required=False, allow_blank=True, default='')


class ConfirmacionLecturaReadSerializer(serializers.ModelSerializer):
    """Lectura de confirmación."""
    comunicado_titulo = serializers.CharField(source='comunicado.titulo', read_only=True)
    comunicado_tipo = serializers.CharField(source='comunicado.tipo', read_only=True)

    class Meta:
        model = ConfirmacionLectura
        fields = [
            'id_confirmacion', 'comunicado', 'comunicado_titulo', 'comunicado_tipo',
            'leido', 'fecha_lectura', 'confirmado', 'fecha_confirmacion',
            'observaciones',
        ]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirmar_comunicado(request, comunicado_id):
    """
    POST /api/comunicados/<id>/confirmar/
    Marca un comunicado como leído y/o confirmado (para citaciones).

    Body (opcional):
      - observaciones: texto libre
    """
    user = request.user
    school_id = getattr(user, 'rbd_colegio', None)

    try:
        comunicado = Comunicado.objects.get(
            id_comunicado=comunicado_id,
            activo=True,
        )
        if not _is_global_admin(user) and comunicado.colegio_id != school_id:
            raise PermissionDenied('No tiene acceso a este comunicado.')
    except Comunicado.DoesNotExist:
        raise ValidationError({'comunicado_id': 'Comunicado no encontrado.'})

    ser = ConfirmacionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    confirmacion, created = ConfirmacionLectura.objects.get_or_create(
        comunicado=comunicado,
        usuario=user,
        defaults={'observaciones': ser.validated_data.get('observaciones', '')},
    )

    now = timezone.now()

    # Marcar como leído
    if not confirmacion.leido:
        confirmacion.leido = True
        confirmacion.fecha_lectura = now

    # Si se requiere confirmación (citaciones, eventos), confirmar
    if comunicado.requiere_confirmacion and not confirmacion.confirmado:
        confirmacion.confirmado = True
        confirmacion.fecha_confirmacion = now

    if ser.validated_data.get('observaciones'):
        confirmacion.observaciones = ser.validated_data['observaciones']

    confirmacion.save()

    logger.info(
        f"Comunicado confirmado — comunicado={comunicado_id} user={user.email} "
        f"leido={confirmacion.leido} confirmado={confirmacion.confirmado}"
    )

    return Response({
        'leido': confirmacion.leido,
        'confirmado': confirmacion.confirmado,
        'fecha_lectura': confirmacion.fecha_lectura.isoformat() if confirmacion.fecha_lectura else None,
        'fecha_confirmacion': confirmacion.fecha_confirmacion.isoformat() if confirmacion.fecha_confirmacion else None,
        'requiere_confirmacion': comunicado.requiere_confirmacion,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_comunicados(request):
    """
    GET /api/comunicados/mis-comunicados/
    Lista los comunicados dirigidos al usuario con su estado de lectura/confirmación.
    Filtros opcionales: ?tipo=urgente&leido=false&confirmado=false
    """
    user = request.user
    school_id = getattr(user, 'rbd_colegio', None)
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()

    # Comunicados del colegio activos
    qs = Comunicado.objects.filter(colegio_id=school_id, activo=True)

    # Filtrar por destinatario según rol
    role_dest_map = {
        'profesor': 'profesores',
        'estudiante': 'estudiantes',
        'alumno': 'estudiantes',
        'apoderado': 'apoderados',
    }
    dest_filter = role_dest_map.get(role_name)
    if dest_filter:
        qs = qs.filter(Q(destinatario='todos') | Q(destinatario=dest_filter))
    else:
        # Admin ve todos
        qs = qs

    # Filtros opcionales
    tipo = request.query_params.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    qs = qs.order_by('-es_prioritario', '-fecha_publicacion')

    # Obtener estados de lectura del usuario
    confirmaciones = {
        c.comunicado_id: c
        for c in ConfirmacionLectura.objects.filter(
            usuario=user, comunicado__in=qs
        )
    }

    # Filtro de leido/confirmado
    filtro_leido = request.query_params.get('leido')
    filtro_confirmado = request.query_params.get('confirmado')

    results = []
    for com in qs[:50]:
        conf = confirmaciones.get(com.id_comunicado)
        leido = conf.leido if conf else False
        confirmado = conf.confirmado if conf else False

        # Aplicar filtros
        if filtro_leido == 'true' and not leido:
            continue
        if filtro_leido == 'false' and leido:
            continue
        if filtro_confirmado == 'true' and not confirmado:
            continue
        if filtro_confirmado == 'false' and confirmado:
            continue

        results.append({
            'id': com.id_comunicado,
            'tipo': com.tipo,
            'titulo': com.titulo,
            'contenido': com.contenido[:300],
            'es_prioritario': com.es_prioritario,
            'es_destacado': com.es_destacado,
            'requiere_confirmacion': com.requiere_confirmacion,
            'fecha_publicacion': com.fecha_publicacion.isoformat() if com.fecha_publicacion else None,
            'fecha_evento': com.fecha_evento.isoformat() if com.fecha_evento else None,
            'lugar_evento': com.lugar_evento,
            'leido': leido,
            'confirmado': confirmado,
            'fecha_lectura': conf.fecha_lectura.isoformat() if conf and conf.fecha_lectura else None,
        })

    return Response({
        'total': len(results),
        'comunicados': results,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comunicado_estadisticas(request, comunicado_id):
    """
    GET /api/comunicados/<id>/estadisticas/
    Retorna estadísticas de alcance y lectura (solo admin/publicador).
    """
    user = request.user
    school_id = getattr(user, 'rbd_colegio', None)

    try:
        comunicado = Comunicado.objects.get(id_comunicado=comunicado_id)
        if not _is_global_admin(user) and comunicado.colegio_id != school_id:
            raise PermissionDenied('No tiene acceso.')
    except Comunicado.DoesNotExist:
        raise ValidationError({'comunicado_id': 'No encontrado.'})

    # Calcular o recuperar estadísticas
    stats, _ = EstadisticaComunicado.objects.get_or_create(comunicado=comunicado)
    stats.calcular_estadisticas()

    return Response({
        'comunicado_id': comunicado.id_comunicado,
        'titulo': comunicado.titulo,
        'total_destinatarios': stats.total_destinatarios,
        'total_leidos': stats.total_leidos,
        'porcentaje_lectura': float(stats.porcentaje_lectura),
        'total_confirmados': stats.total_confirmados,
        'porcentaje_confirmacion': float(stats.porcentaje_confirmacion),
        'desglose': {
            'profesores': {'destinatarios': stats.destinatarios_profesores, 'leidos': stats.leidos_profesores},
            'estudiantes': {'destinatarios': stats.destinatarios_estudiantes, 'leidos': stats.leidos_estudiantes},
            'apoderados': {'destinatarios': stats.destinatarios_apoderados, 'leidos': stats.leidos_apoderados},
        },
        'tiempo_promedio_lectura_horas': float(stats.tiempo_promedio_lectura_horas),
    })


# ═══════════════════════════════════════════════
# 2. REPORTES DE TENDENCIAS PARA PROFESOR
# ═══════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_trends_report(request):
    """
    GET /api/profesor/tendencias/
    Retorna tendencias de rendimiento de los estudiantes del profesor.

    Query params:
      - clase_id (optional): filtrar por clase específica
      - periodo (optional): 'mes', 'semestre', 'anual' (default: 'semestre')
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()

    if role_name != 'profesor' and not _is_global_admin(user):
        raise PermissionDenied('Solo profesores pueden ver tendencias.')

    school_id = getattr(user, 'rbd_colegio', None)
    today = date.today()

    # Obtener clases del profesor
    teacher_classes = Clase.objects.filter(
        profesor_id=user.id, colegio_id=school_id, activo=True,
    )

    clase_id = request.query_params.get('clase_id')
    if clase_id:
        teacher_classes = teacher_classes.filter(id=clase_id)

    teacher_class_ids = list(teacher_classes.values_list('id', flat=True))

    if not teacher_class_ids:
        return Response({
            'tendencias_por_clase': [],
            'tendencia_general': None,
            'asistencia_mensual': [],
        })

    periodo = request.query_params.get('periodo', 'semestre')
    if periodo == 'mes':
        fecha_desde = today.replace(day=1)
    elif periodo == 'anual':
        fecha_desde = today.replace(month=1, day=1)
    else:  # semestre
        fecha_desde = today.replace(month=1 if today.month <= 6 else 7, day=1)

    # ── Tendencias por clase ──
    tendencias_por_clase = []
    for clase in teacher_classes.select_related('asignatura', 'curso'):
        # Promedio de notas del período
        notas = Calificacion.objects.filter(
            evaluacion__clase=clase,
            fecha_creacion__gte=fecha_desde,
        )
        avg_actual = notas.aggregate(avg=Avg('nota'))['avg']

        # Promedio anterior (para comparación)
        delta = today - fecha_desde
        fecha_anterior_desde = fecha_desde - delta
        notas_anteriores = Calificacion.objects.filter(
            evaluacion__clase=clase,
            fecha_creacion__gte=fecha_anterior_desde,
            fecha_creacion__lt=fecha_desde,
        )
        avg_anterior = notas_anteriores.aggregate(avg=Avg('nota'))['avg']

        # Distribución de notas
        from backend.common.utils.grade_scale import get_escala
        try:
            from backend.apps.institucion.models import Colegio
            colegio = Colegio.objects.get(rbd=school_id)
            escala = get_escala(colegio)
            nota_aprobacion = float(escala['nota_aprobacion'])
        except Exception:
            nota_aprobacion = 4.0

        total_notas = notas.count()
        aprobados = notas.filter(nota__gte=nota_aprobacion).count()
        reprobados = total_notas - aprobados

        # Asistencia del período
        att_total = Asistencia.objects.filter(
            clase=clase, fecha__gte=fecha_desde,
        ).count()
        att_present = Asistencia.objects.filter(
            clase=clase, fecha__gte=fecha_desde, estado='P',
        ).count()
        att_pct = round((att_present / att_total) * 100, 1) if att_total else 0.0

        # Evaluaciones realizadas vs pendientes
        evals_total = Evaluacion.objects.filter(clase=clase, activa=True).count()
        evals_futuras = Evaluacion.objects.filter(
            clase=clase, activa=True, fecha_evaluacion__gt=today,
        ).count()

        tendencia = None
        if avg_actual and avg_anterior:
            diff = float(avg_actual) - float(avg_anterior)
            if diff > 0.2:
                tendencia = 'subiendo'
            elif diff < -0.2:
                tendencia = 'bajando'
            else:
                tendencia = 'estable'

        tendencias_por_clase.append({
            'clase_id': clase.id,
            'asignatura': clase.asignatura.nombre if clase.asignatura else '',
            'curso': clase.curso.nombre if clase.curso else '',
            'promedio_actual': round(float(avg_actual), 1) if avg_actual else None,
            'promedio_anterior': round(float(avg_anterior), 1) if avg_anterior else None,
            'tendencia': tendencia,
            'total_notas': total_notas,
            'aprobados': aprobados,
            'reprobados': reprobados,
            'porcentaje_aprobacion': round((aprobados / total_notas) * 100, 1) if total_notas else 0.0,
            'porcentaje_asistencia': att_pct,
            'evaluaciones_total': evals_total,
            'evaluaciones_pendientes': evals_futuras,
        })

    # ── Tendencia general ──
    all_avg = Calificacion.objects.filter(
        evaluacion__clase_id__in=teacher_class_ids,
        fecha_creacion__gte=fecha_desde,
    ).aggregate(avg=Avg('nota'))['avg']

    all_att_total = Asistencia.objects.filter(
        clase_id__in=teacher_class_ids, fecha__gte=fecha_desde,
    ).count()
    all_att_present = Asistencia.objects.filter(
        clase_id__in=teacher_class_ids, fecha__gte=fecha_desde, estado='P',
    ).count()
    att_general = round((all_att_present / all_att_total) * 100, 1) if all_att_total else 0.0

    # ── Asistencia mensual (últimos 6 meses) ──
    asistencia_mensual = []
    for i in range(5, -1, -1):
        mes_ref = today.replace(day=1) - timedelta(days=i * 30)
        mes_inicio = mes_ref.replace(day=1)
        if mes_inicio.month == 12:
            mes_fin = mes_inicio.replace(year=mes_inicio.year + 1, month=1)
        else:
            mes_fin = mes_inicio.replace(month=mes_inicio.month + 1)

        att_m_total = Asistencia.objects.filter(
            clase_id__in=teacher_class_ids,
            fecha__gte=mes_inicio, fecha__lt=mes_fin,
        ).count()
        att_m_present = Asistencia.objects.filter(
            clase_id__in=teacher_class_ids,
            fecha__gte=mes_inicio, fecha__lt=mes_fin,
            estado='P',
        ).count()

        asistencia_mensual.append({
            'mes': mes_inicio.strftime('%Y-%m'),
            'porcentaje': round((att_m_present / att_m_total) * 100, 1) if att_m_total else 0.0,
            'total_registros': att_m_total,
        })

    return Response({
        'periodo': periodo,
        'fecha_desde': fecha_desde.isoformat(),
        'tendencias_por_clase': tendencias_por_clase,
        'tendencia_general': {
            'promedio_general': round(float(all_avg), 1) if all_avg else None,
            'porcentaje_asistencia': att_general,
            'total_clases': len(teacher_class_ids),
        },
        'asistencia_mensual': asistencia_mensual,
    })


# ═══════════════════════════════════════════════
# 3. CALENDARIO ESCOLAR ACADÉMICO
# ═══════════════════════════════════════════════

class EventoCalendarioSerializer(serializers.ModelSerializer):
    """Serializer completo de evento."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    es_multidia = serializers.BooleanField(read_only=True)

    class Meta:
        model = EventoCalendario
        fields = [
            'id_evento', 'colegio_id', 'ciclo_academico_id',
            'titulo', 'descripcion', 'tipo', 'tipo_display',
            'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin',
            'todo_el_dia', 'lugar', 'visibilidad',
            'es_feriado_nacional', 'color', 'activo',
            'creado_por', 'creado_por_nombre', 'es_multidia',
            'fecha_creacion',
        ]
        read_only_fields = ['id_evento', 'creado_por', 'colegio_id', 'fecha_creacion']


class EventoCalendarioListSerializer(serializers.ModelSerializer):
    """Lista compacta para vista de calendario."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = EventoCalendario
        fields = [
            'id_evento', 'titulo', 'tipo', 'tipo_display',
            'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin',
            'todo_el_dia', 'color', 'es_feriado_nacional',
            'visibilidad',
        ]


class EventoCalendarioViewSet(CapabilityModelViewSet):
    """
    CRUD de eventos del calendario escolar.
    Admin: lectura + escritura.
    Otros roles: solo lectura filtrada por visibilidad.
    """
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'ANNOUNCEMENT_VIEW',
        'retrieve': 'ANNOUNCEMENT_VIEW',
        'create': 'ANNOUNCEMENT_CREATE',
        'update': 'ANNOUNCEMENT_EDIT',
        'partial_update': 'ANNOUNCEMENT_EDIT',
        'destroy': 'ANNOUNCEMENT_DELETE',
    }

    def get_queryset(self):
        user = self.request.user
        school_id = _school_id(self.request)
        role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()

        base_qs = EventoCalendario.objects.filter(activo=True)

        if _is_global_admin(user):
            qs = base_qs
        else:
            qs = base_qs.filter(colegio_id=school_id)

            # Filtrar por visibilidad según rol
            vis_map = {
                'profesor': 'profesores',
                'estudiante': 'estudiantes',
                'alumno': 'estudiantes',
                'apoderado': 'apoderados',
            }
            vis_filter = vis_map.get(role_name, 'administrativos')
            qs = qs.filter(Q(visibilidad='todos') | Q(visibilidad=vis_filter))

        # Filtros de query params
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)

        mes = self.request.query_params.get('mes')
        anio = self.request.query_params.get('anio')
        if anio:
            try:
                anio_int = int(anio)
                if mes:
                    mes_int = int(mes)
                    qs = qs.filter(
                        Q(fecha_inicio__year=anio_int, fecha_inicio__month=mes_int) |
                        Q(fecha_fin__year=anio_int, fecha_fin__month=mes_int)
                    )
                else:
                    qs = qs.filter(
                        Q(fecha_inicio__year=anio_int) | Q(fecha_fin__year=anio_int)
                    )
            except (TypeError, ValueError):
                pass

        fecha_desde = self.request.query_params.get('desde')
        fecha_hasta = self.request.query_params.get('hasta')
        if fecha_desde:
            qs = qs.filter(fecha_inicio__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_inicio__lte=fecha_hasta)

        return qs.order_by('fecha_inicio', 'hora_inicio')

    def get_serializer_class(self):
        if self.action == 'list':
            return EventoCalendarioListSerializer
        return EventoCalendarioSerializer

    def _ensure_manage_permission(self):
        role_name = getattr(getattr(self.request.user, 'role', None), 'nombre', '').strip().lower()
        if role_name == 'profesor':
            raise PermissionDenied('El rol profesor solo tiene permisos de lectura para el calendario.')

    def perform_create(self, serializer):
        self._ensure_manage_permission()
        serializer.save(
            colegio_id=_school_id(self.request),
            creado_por=self.request.user,
        )

    def perform_update(self, serializer):
        self._ensure_manage_permission()
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        self._ensure_manage_permission()
        instance.activo = False
        instance.save(update_fields=['activo'])

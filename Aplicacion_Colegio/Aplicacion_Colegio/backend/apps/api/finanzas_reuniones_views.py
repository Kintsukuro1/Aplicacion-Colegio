"""
Views para funcionalidades Semana 9-10.

L. Dashboard Financiero Consolidado (Admin Escolar)
N. Solicitud de Reunión Apoderado→Profesor
K. Gestión Completa de Ciclo Académico (transiciones, cierre, estadísticas)
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.accounts.models import Apoderado, RelacionApoderadoEstudiante, User
from backend.apps.api.base import CapabilityModelViewSet
from backend.apps.api.permissions import HasCapability
from backend.apps.cursos.models import Clase
from backend.apps.institucion.models import CicloAcademico, Colegio
from backend.apps.matriculas.models import Beca, Cuota, EstadoCuenta, Matricula, Pago
from backend.common.services.policy_service import PolicyService

logger = logging.getLogger('api')


def _is_global_admin(user):
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN')


def _school_id(user):
    return getattr(user, 'rbd_colegio', None)


def _can_manage_school(user):
    return _is_global_admin(user) or PolicyService.has_capability(user, 'SYSTEM_CONFIGURE')


# ═══════════════════════════════════════════════
# L. DASHBOARD FINANCIERO CONSOLIDADO
# ═══════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_dashboard(request):
    """
    GET /api/finanzas/dashboard/
    Panel financiero consolidado para admin escolar.

    Query params:
      - anio (optional): año (default: actual)
      - mes (optional): mes 1-12
    """
    user = request.user
    if not (_is_global_admin(user) or PolicyService.has_capability(user, 'FINANCE_VIEW')):
        raise PermissionDenied('Solo administradores pueden acceder al dashboard financiero.')

    school_id = _school_id(user)
    anio = int(request.query_params.get('anio', date.today().year))
    mes = request.query_params.get('mes')

    # ── Cuotas del período ──
    cuotas_qs = Cuota.objects.filter(
        matricula__colegio_id=school_id,
        anio=anio,
    )
    if mes:
        cuotas_qs = cuotas_qs.filter(mes=int(mes))

    cuotas_agg = cuotas_qs.aggregate(
        total_emitido=Sum('monto_final'),
        total_pagado=Sum('monto_pagado'),
        total_cuotas=Count('id'),
    )

    total_emitido = cuotas_agg['total_emitido'] or Decimal('0')
    total_pagado = cuotas_agg['total_pagado'] or Decimal('0')
    total_pendiente = total_emitido - total_pagado

    # ── Morosidad ──
    hoy = date.today()
    cuotas_vencidas = cuotas_qs.filter(
        estado__in=['PENDIENTE', 'VENCIDA', 'PAGADA_PARCIAL'],
        fecha_vencimiento__lt=hoy,
    )
    morosos_count = cuotas_vencidas.values('matricula__estudiante').distinct().count()
    monto_moroso = cuotas_vencidas.aggregate(
        total=Sum(F('monto_final') - F('monto_pagado'))
    )['total'] or Decimal('0')

    # ── Distribución por estado ──
    estados = cuotas_qs.values('estado').annotate(
        cantidad=Count('id'),
        monto=Sum('monto_final'),
    ).order_by('estado')

    # ── Recaudación mensual (últimos 6 meses) ──
    recaudacion_mensual = []
    for i in range(5, -1, -1):
        mes_ref = hoy.replace(day=1) - timedelta(days=i * 30)
        m_inicio = mes_ref.replace(day=1)
        if m_inicio.month == 12:
            m_fin = m_inicio.replace(year=m_inicio.year + 1, month=1)
        else:
            m_fin = m_inicio.replace(month=m_inicio.month + 1)

        pagos_mes = Pago.objects.filter(
            cuota__matricula__colegio_id=school_id,
            estado='APROBADO',
            fecha_pago__gte=m_inicio,
            fecha_pago__lt=m_fin,
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        recaudacion_mensual.append({
            'mes': m_inicio.strftime('%Y-%m'),
            'recaudado': float(pagos_mes),
        })

    # ── Becas vigentes ──
    becas_count = Beca.objects.filter(
        matricula__colegio_id=school_id,
        estado__in=['VIGENTE', 'APROBADA'],
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy,
    ).count()
    becas_por_tipo = Beca.objects.filter(
        matricula__colegio_id=school_id,
        estado__in=['VIGENTE', 'APROBADA'],
    ).values('tipo').annotate(total=Count('id'))

    # ── Pagos recientes ──
    pagos_recientes = Pago.objects.filter(
        cuota__matricula__colegio_id=school_id,
    ).select_related(
        'estudiante', 'cuota'
    ).order_by('-fecha_pago')[:10]

    # ── Tasa de cobranza ──
    tasa = round(float(total_pagado / total_emitido) * 100, 1) if total_emitido else 0.0

    return Response({
        'anio': anio,
        'mes_filtro': int(mes) if mes else None,
        'resumen': {
            'total_emitido': float(total_emitido),
            'total_pagado': float(total_pagado),
            'total_pendiente': float(total_pendiente),
            'tasa_cobranza': tasa,
        },
        'morosidad': {
            'familias_morosas': morosos_count,
            'monto_vencido': float(monto_moroso),
        },
        'cuotas_por_estado': [
            {'estado': e['estado'], 'cantidad': e['cantidad'], 'monto': float(e['monto'] or 0)}
            for e in estados
        ],
        'recaudacion_mensual': recaudacion_mensual,
        'becas': {
            'vigentes': becas_count,
            'por_tipo': [
                {'tipo': b['tipo'], 'total': b['total']}
                for b in becas_por_tipo
            ],
        },
        'pagos_recientes': [
            {
                'id': p.id,
                'estudiante': p.estudiante.get_full_name(),
                'monto': float(p.monto),
                'metodo': p.metodo_pago,
                'estado': p.estado,
                'fecha': p.fecha_pago.isoformat(),
            }
            for p in pagos_recientes
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_morosos_report(request):
    """
    GET /api/finanzas/morosos/
    Lista detallada de familias morosas con monto y cuotas vencidas.
    """
    user = request.user
    if not (_is_global_admin(user) or PolicyService.has_capability(user, 'FINANCE_VIEW')):
        raise PermissionDenied('Sin permisos financieros.')

    school_id = _school_id(user)
    hoy = date.today()

    cuotas_vencidas = Cuota.objects.filter(
        matricula__colegio_id=school_id,
        estado__in=['PENDIENTE', 'VENCIDA', 'PAGADA_PARCIAL'],
        fecha_vencimiento__lt=hoy,
    ).select_related(
        'matricula__estudiante'
    ).order_by('matricula__estudiante__apellido_paterno', 'anio', 'mes')

    morosos = {}
    for cuota in cuotas_vencidas:
        est = cuota.matricula.estudiante
        key = est.id
        if key not in morosos:
            morosos[key] = {
                'estudiante_id': est.id,
                'nombre': est.get_full_name(),
                'email': est.email,
                'cuotas_vencidas': 0,
                'monto_total_adeudado': Decimal('0'),
                'cuotas_detalle': [],
            }
        saldo = cuota.saldo_pendiente()
        morosos[key]['cuotas_vencidas'] += 1
        morosos[key]['monto_total_adeudado'] += saldo
        morosos[key]['cuotas_detalle'].append({
            'mes': cuota.mes,
            'anio': cuota.anio,
            'monto_final': float(cuota.monto_final),
            'monto_pagado': float(cuota.monto_pagado),
            'saldo': float(saldo),
            'fecha_vencimiento': cuota.fecha_vencimiento.isoformat(),
        })

    result = sorted(morosos.values(), key=lambda x: x['monto_total_adeudado'], reverse=True)
    for r in result:
        r['monto_total_adeudado'] = float(r['monto_total_adeudado'])

    return Response({
        'total_morosos': len(result),
        'morosos': result,
    })


# ═══════════════════════════════════════════════
# N. SOLICITUD DE REUNIÓN APODERADO → PROFESOR
# ═══════════════════════════════════════════════

# El modelo no existe aún, lo creamos como modelo Django en institucion/models.py
# desde aquí importamos

from backend.apps.institucion.models import SolicitudReunion


class SolicitudReunionSerializer(serializers.ModelSerializer):
    """Serializer de solicitud de reunión."""
    apoderado_nombre = serializers.SerializerMethodField()
    profesor_nombre = serializers.CharField(source='profesor.get_full_name', read_only=True)
    estudiante_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = SolicitudReunion
        fields = [
            'id', 'colegio_id', 'apoderado', 'apoderado_nombre',
            'profesor', 'profesor_nombre', 'estudiante', 'estudiante_nombre',
            'motivo', 'tipo', 'fecha_propuesta', 'hora_propuesta',
            'fecha_confirmada', 'hora_confirmada', 'duracion_minutos',
            'modalidad', 'lugar', 'enlace_virtual',
            'estado', 'estado_display',
            'observaciones_apoderado', 'respuesta_profesor',
            'fecha_creacion',
        ]
        read_only_fields = [
            'id', 'colegio_id', 'apoderado', 'estado',
            'fecha_confirmada', 'hora_confirmada',
            'respuesta_profesor', 'fecha_creacion',
        ]

    @staticmethod
    def get_apoderado_nombre(obj):
        return obj.apoderado.user.get_full_name() if obj.apoderado and obj.apoderado.user else ''

    @staticmethod
    def get_estudiante_nombre(obj):
        return obj.estudiante.get_full_name() if obj.estudiante else ''


class SolicitudReunionListSerializer(serializers.ModelSerializer):
    """Lista compacta de solicitudes."""
    apoderado_nombre = serializers.SerializerMethodField()
    profesor_nombre = serializers.CharField(source='profesor.get_full_name', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = SolicitudReunion
        fields = [
            'id', 'apoderado_nombre', 'profesor_nombre',
            'motivo', 'tipo', 'estado', 'estado_display',
            'fecha_propuesta', 'hora_propuesta', 'modalidad',
            'fecha_creacion',
        ]

    @staticmethod
    def get_apoderado_nombre(obj):
        return obj.apoderado.user.get_full_name() if obj.apoderado and obj.apoderado.user else ''


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def solicitar_reunion(request):
    """
    POST /api/reuniones/solicitar/
    Apoderado solicita reunión con un profesor.

    Body:
    {
        "profesor_id": 5,
        "estudiante_id": 12,  (opcional)
        "motivo": "Rendimiento en matemáticas",
        "tipo": "academica",
        "fecha_propuesta": "2026-04-15",
        "hora_propuesta": "10:00",
        "modalidad": "presencial",
        "observaciones_apoderado": "Prefiero en la mañana"
    }
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()
    data = request.data
    school_id = _school_id(user)

    if role_name not in {'apoderado', 'profesor'} and not _can_manage_school(user):
        raise PermissionDenied('No tiene permisos para crear reuniones.')

    # Resolver apoderado de la solicitud
    apoderado = None
    if role_name == 'apoderado':
        try:
            apoderado = Apoderado.objects.get(user=user)
        except Apoderado.DoesNotExist:
            raise PermissionDenied('Solo apoderados registrados pueden solicitar reuniones.')
    else:
        apoderado_id = data.get('apoderado_id')
        apoderado_email = (data.get('apoderado_email') or '').strip().lower()

        if not apoderado_id and not apoderado_email:
            raise ValidationError({'apoderado': 'Debe indicar apoderado_id o apoderado_email.'})

        qs_apoderado = Apoderado.objects.select_related('user')
        if apoderado_id:
            qs_apoderado = qs_apoderado.filter(id=apoderado_id)
        else:
            qs_apoderado = qs_apoderado.filter(user__email__iexact=apoderado_email)

        apoderado = qs_apoderado.first()
        if not apoderado:
            raise ValidationError({'apoderado': 'Apoderado no encontrado.'})

        if apoderado.user.rbd_colegio != school_id:
            raise ValidationError({'apoderado': 'El apoderado no pertenece a su colegio.'})

    # Resolver profesor según rol
    if role_name == 'profesor':
        # Un profesor solo puede crear reuniones para sí mismo.
        profesor = user
    else:
        profesor_id = data.get('profesor_id')
        profesor_email = (data.get('profesor_email') or '').strip().lower()
        if not profesor_id and not profesor_email:
            raise ValidationError({'profesor': 'Debe indicar profesor_id o profesor_email.'})

        qs_profesor = User.objects.filter(
            role__nombre__iexact='Profesor',
            rbd_colegio=school_id,
        )
        if profesor_id:
            qs_profesor = qs_profesor.filter(id=profesor_id)
        else:
            qs_profesor = qs_profesor.filter(email__iexact=profesor_email)

        profesor = qs_profesor.first()
        if not profesor:
            raise ValidationError({'profesor': 'Profesor no encontrado en su colegio.'})

    # Verificar estudiante si se proporciona
    estudiante = None
    estudiante_id = data.get('estudiante_id')
    if estudiante_id:
        rel = RelacionApoderadoEstudiante.objects.filter(
            apoderado=apoderado,
            estudiante_id=estudiante_id,
            activa=True,
        ).first()
        if not rel:
            raise ValidationError({'estudiante_id': 'El estudiante no esta vinculado activamente al apoderado.'})
        estudiante = rel.estudiante

    solicitud = SolicitudReunion.objects.create(
        colegio_id=apoderado.user.rbd_colegio,
        apoderado=apoderado,
        profesor=profesor,
        estudiante=estudiante,
        motivo=data.get('motivo', ''),
        tipo=data.get('tipo', 'general'),
        fecha_propuesta=data.get('fecha_propuesta'),
        hora_propuesta=data.get('hora_propuesta'),
        modalidad=data.get('modalidad', 'presencial'),
        observaciones_apoderado=data.get('observaciones_apoderado', ''),
    )

    logger.info(
        f'Solicitud de reunión creada — id={solicitud.id} '
        f'creador={user.email} rol={role_name} apoderado={apoderado.user.email} profesor={profesor.email}'
    )

    return Response(
        SolicitudReunionSerializer(solicitud).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reuniones_apoderados_pupilos(request):
    """
    GET /api/reuniones/apoderados-pupilos/
    Catalogo para formulario de creacion de reuniones (profesor/admin escolar).
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()

    if role_name not in {'profesor'} and not _can_manage_school(user):
        raise PermissionDenied('Sin permisos para consultar catalogo de reuniones.')

    school_id = _school_id(user)

    relaciones = (
        RelacionApoderadoEstudiante.objects.select_related('apoderado__user', 'estudiante')
        .filter(
            apoderado__user__rbd_colegio=school_id,
            apoderado__activo=True,
            activa=True,
            estudiante__is_active=True,
        )
        .order_by('apoderado__user__apellido_paterno', 'apoderado__user__nombre', 'estudiante__id')
    )

    apoderados_map = {}
    for rel in relaciones:
        apoderado = rel.apoderado
        apoderado_user = getattr(apoderado, 'user', None)
        estudiante = rel.estudiante
        if not apoderado_user or not estudiante:
            continue

        key = apoderado.id
        if key not in apoderados_map:
            apoderados_map[key] = {
                'apoderado_id': apoderado.id,
                'apoderado_nombre': apoderado_user.get_full_name(),
                'apoderado_email': apoderado_user.email,
                'pupilos': [],
            }

        apoderados_map[key]['pupilos'].append({
            'id': estudiante.id,
            'nombre': estudiante.get_full_name(),
        })

    return Response({
        'total_apoderados': len(apoderados_map),
        'apoderados': list(apoderados_map.values()),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_reuniones(request):
    """
    GET /api/reuniones/mis-reuniones/
    Lista solicitudes de reunión del usuario (apoderado o profesor).

    Filtros: ?estado=pendiente&tipo=academica
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()
    school_id = _school_id(user)

    if role_name == 'apoderado':
        try:
            apoderado = Apoderado.objects.get(user=user)
            qs = SolicitudReunion.objects.filter(apoderado=apoderado)
        except Apoderado.DoesNotExist:
            return Response({'reuniones': [], 'total': 0})
    elif role_name == 'profesor':
        qs = SolicitudReunion.objects.filter(profesor=user)
    elif _can_manage_school(user):
        qs = SolicitudReunion.objects.filter(colegio_id=school_id)
    else:
        raise PermissionDenied('Rol no soportado.')

    # Filtros
    estado = request.query_params.get('estado')
    if estado:
        qs = qs.filter(estado=estado)
    tipo = request.query_params.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    qs = qs.select_related(
        'apoderado__user', 'profesor', 'estudiante'
    ).order_by('-fecha_creacion')

    return Response({
        'total': qs.count(),
        'reuniones': SolicitudReunionListSerializer(qs[:50], many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def responder_reunion(request, reunion_id):
    """
    POST /api/reuniones/<id>/responder/
    Profesor acepta, propone nueva fecha o rechaza.

    Body:
    {
        "accion": "aceptar" | "proponer_fecha" | "rechazar",
        "fecha_confirmada": "2026-04-16",  (si propone fecha)
        "hora_confirmada": "11:00",
        "respuesta_profesor": "Confirmo la reunión"
    }
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()

    if role_name != 'profesor' and not _can_manage_school(user):
        raise PermissionDenied('Solo profesores pueden responder solicitudes.')

    if role_name == 'profesor':
        try:
            solicitud = SolicitudReunion.objects.get(id=reunion_id, profesor=user)
        except SolicitudReunion.DoesNotExist:
            raise ValidationError({'reunion_id': 'Solicitud no encontrada.'})
    else:
        try:
            solicitud = SolicitudReunion.objects.get(id=reunion_id, colegio_id=_school_id(user))
        except SolicitudReunion.DoesNotExist:
            raise ValidationError({'reunion_id': 'Solicitud no encontrada para este colegio.'})

    accion = request.data.get('accion', '').lower()
    respuesta = request.data.get('respuesta_profesor', '')

    if accion == 'aceptar':
        solicitud.estado = 'confirmada'
        solicitud.fecha_confirmada = solicitud.fecha_propuesta
        solicitud.hora_confirmada = solicitud.hora_propuesta
        solicitud.respuesta_profesor = respuesta or 'Reunión confirmada.'
    elif accion == 'proponer_fecha':
        solicitud.estado = 'reprogramada'
        solicitud.fecha_confirmada = request.data.get('fecha_confirmada')
        solicitud.hora_confirmada = request.data.get('hora_confirmada')
        solicitud.respuesta_profesor = respuesta or 'Propongo nueva fecha.'
    elif accion == 'rechazar':
        solicitud.estado = 'rechazada'
        solicitud.respuesta_profesor = respuesta or 'No es posible realizar la reunión.'
    else:
        raise ValidationError({'accion': 'Debe ser: aceptar, proponer_fecha o rechazar.'})

    solicitud.save()

    logger.info(f'Reunión {reunion_id} — acción={accion} profesor={user.email}')

    return Response(SolicitudReunionSerializer(solicitud).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancelar_reunion(request, reunion_id):
    """
    POST /api/reuniones/<id>/cancelar/
    Permite cancelar reuniones en estado pendiente/confirmada/reprogramada.
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()

    if role_name == 'profesor':
        qs = SolicitudReunion.objects.filter(id=reunion_id, profesor=user)
    elif _can_manage_school(user):
        qs = SolicitudReunion.objects.filter(id=reunion_id, colegio_id=_school_id(user))
    else:
        raise PermissionDenied('Sin permisos para cancelar reuniones.')

    solicitud = qs.first()
    if not solicitud:
        raise ValidationError({'reunion_id': 'Solicitud no encontrada.'})

    if solicitud.estado not in {'pendiente', 'confirmada', 'reprogramada'}:
        raise ValidationError({'estado': f'No se puede cancelar en estado {solicitud.estado}.'})

    motivo = request.data.get('motivo', '').strip()
    solicitud.estado = 'cancelada'
    if motivo:
        solicitud.respuesta_profesor = motivo
    solicitud.save(update_fields=['estado', 'respuesta_profesor', 'fecha_actualizacion'])

    logger.info(f'Reunión {reunion_id} cancelada por {user.email}')
    return Response(SolicitudReunionSerializer(solicitud).data)


# ═══════════════════════════════════════════════
# K. GESTIÓN COMPLETA DE CICLO ACADÉMICO
# ═══════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ciclo_transition(request, ciclo_id):
    """
    POST /api/ciclos-academicos/<id>/transicion/
    Ejecuta transición de estado validando reglas de negocio.

    Body: {"nuevo_estado": "ACTIVO" | "EVALUACION" | "FINALIZADO" | "CERRADO"}
    """
    user = request.user
    if not (_is_global_admin(user) or PolicyService.has_capability(user, 'SYSTEM_CONFIGURE')):
        raise PermissionDenied('Sin permisos para gestionar ciclos.')

    school_id = _school_id(user)
    nuevo_estado = request.data.get('nuevo_estado', '').upper()

    try:
        ciclo = CicloAcademico.objects.get(id=ciclo_id)
        if not _is_global_admin(user) and ciclo.colegio_id != school_id:
            raise PermissionDenied('No puede gestionar ciclos de otro colegio.')
    except CicloAcademico.DoesNotExist:
        raise ValidationError({'ciclo_id': 'Ciclo académico no encontrado.'})

    # Validar transición
    transiciones_validas = CicloAcademico.TRANSICIONES_VALIDAS.get(ciclo.estado, [])
    if nuevo_estado not in transiciones_validas:
        raise ValidationError({
            'nuevo_estado': f'Transición inválida: {ciclo.estado} → {nuevo_estado}. '
                            f'Transiciones permitidas: {transiciones_validas}'
        })

    # Validaciones de negocio según transición
    warnings = []

    if nuevo_estado == 'ACTIVO':
        # Desactivar ciclo activo anterior del mismo colegio
        otros_activos = CicloAcademico.objects.filter(
            colegio_id=ciclo.colegio_id, estado='ACTIVO'
        ).exclude(pk=ciclo.pk)
        if otros_activos.exists():
            otros_activos.update(estado='FINALIZADO', modificado_por=user)
            warnings.append(f'{otros_activos.count()} ciclo(s) anterior(es) finalizados automáticamente.')

    elif nuevo_estado == 'FINALIZADO':
        # Verificar que no haya evaluaciones pendientes
        from backend.apps.academico.models import Evaluacion
        evals_pendientes = Evaluacion.objects.filter(
            clase__curso__ciclo_academico=ciclo,
            activa=True,
            fecha_evaluacion__gt=date.today(),
        ).count()
        if evals_pendientes:
            warnings.append(f'{evals_pendientes} evaluaciones futuras pendientes.')

    elif nuevo_estado == 'CERRADO':
        # Verificar que no haya cuotas pendientes
        cuotas_pendientes = Cuota.objects.filter(
            matricula__ciclo_academico=ciclo,
            estado__in=['PENDIENTE', 'VENCIDA', 'PAGADA_PARCIAL'],
        ).count()
        if cuotas_pendientes:
            warnings.append(f'{cuotas_pendientes} cuotas sin pagar completo.')

    # Ejecutar transición
    estado_anterior = ciclo.estado
    ciclo.estado = nuevo_estado
    ciclo.modificado_por = user
    ciclo.save(update_fields=['estado', 'modificado_por', 'fecha_modificacion'])

    logger.info(
        f'Ciclo {ciclo.id} transición {estado_anterior} → {nuevo_estado} '
        f'by {user.email}'
    )

    return Response({
        'ciclo_id': ciclo.id,
        'nombre': ciclo.nombre,
        'estado_anterior': estado_anterior,
        'estado_actual': nuevo_estado,
        'warnings': warnings,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ciclo_statistics(request, ciclo_id):
    """
    GET /api/ciclos-academicos/<id>/estadisticas/
    Estadísticas consolidadas de un ciclo académico.
    """
    user = request.user
    if not (_is_global_admin(user) or PolicyService.has_capability(user, 'SYSTEM_CONFIGURE')):
        raise PermissionDenied('Sin permisos.')

    school_id = _school_id(user)

    try:
        ciclo = CicloAcademico.objects.get(id=ciclo_id)
        if not _is_global_admin(user) and ciclo.colegio_id != school_id:
            raise PermissionDenied('No puede ver ciclos de otro colegio.')
    except CicloAcademico.DoesNotExist:
        raise ValidationError({'ciclo_id': 'No encontrado.'})

    # Matrículas
    matriculas = Matricula.objects.filter(ciclo_academico=ciclo, colegio_id=ciclo.colegio_id)
    matriculas_total = matriculas.count()
    matriculas_por_estado = matriculas.values('estado').annotate(total=Count('id'))

    # Cursos y clases
    from backend.apps.cursos.models import Curso
    cursos = Curso.objects.filter(ciclo_academico=ciclo).count()
    clases = Clase.objects.filter(curso__ciclo_academico=ciclo, activo=True).count()

    # Rendimiento académico
    from backend.apps.academico.models import Calificacion
    notas = Calificacion.objects.filter(
        evaluacion__clase__curso__ciclo_academico=ciclo,
    )
    promedio_general = notas.aggregate(avg=Avg('nota'))['avg']

    # Asistencia
    from backend.apps.academico.models import Asistencia
    att_total = Asistencia.objects.filter(
        clase__curso__ciclo_academico=ciclo,
    ).count()
    att_presente = Asistencia.objects.filter(
        clase__curso__ciclo_academico=ciclo, estado='P',
    ).count()
    att_pct = round((att_presente / att_total) * 100, 1) if att_total else 0.0

    # Financiero
    cuotas_ciclo = Cuota.objects.filter(matricula__ciclo_academico=ciclo)
    fin_agg = cuotas_ciclo.aggregate(
        emitido=Sum('monto_final'),
        cobrado=Sum('monto_pagado'),
    )

    return Response({
        'ciclo': {
            'id': ciclo.id,
            'nombre': ciclo.nombre,
            'estado': ciclo.estado,
            'fecha_inicio': ciclo.fecha_inicio.isoformat(),
            'fecha_fin': ciclo.fecha_fin.isoformat(),
        },
        'matriculas': {
            'total': matriculas_total,
            'por_estado': [
                {'estado': m['estado'], 'total': m['total']}
                for m in matriculas_por_estado
            ],
        },
        'academico': {
            'cursos': cursos,
            'clases': clases,
            'promedio_general': round(float(promedio_general), 1) if promedio_general else None,
            'porcentaje_asistencia': att_pct,
        },
        'financiero': {
            'total_emitido': float(fin_agg['emitido'] or 0),
            'total_cobrado': float(fin_agg['cobrado'] or 0),
            'tasa_cobranza': round(
                float((fin_agg['cobrado'] or 0) / fin_agg['emitido']) * 100, 1
            ) if fin_agg['emitido'] else 0.0,
        },
    })

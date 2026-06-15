"""
API endpoints para el Administrador General.
CRUD de usuarios, planes, suscripciones y configuración del sistema.
"""
import json
import logging
import csv
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Q, Count, Sum

from backend.apps.accounts.models import Role, User
from backend.apps.auditoria.models import ConfiguracionAuditoria, AuditoriaEvento
from backend.apps.institucion.models import Colegio
from backend.apps.subscriptions.models import Plan, Subscription
from backend.common.services.policy_service import PolicyService

logger = logging.getLogger(__name__)


def _require_system_admin(user):
    """Return True if user is system admin, False otherwise."""
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN') is True


def _json_error(msg, status=400):
    return JsonResponse({'success': False, 'error': msg}, status=status)


# ───────────────────────────────────────────
# USUARIOS
# ───────────────────────────────────────────

@login_required
@require_POST
def crear_usuario(request):
    """Crear un usuario del sistema."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    email = data.get('email', '').strip()
    nombre = data.get('nombre', '').strip()
    apellido_paterno = data.get('apellido_paterno', '').strip()
    apellido_materno = data.get('apellido_materno', '').strip()
    rut = data.get('rut', '').strip() or None
    rol_id = data.get('rol_id')
    colegio_rbd = data.get('colegio_rbd') or None
    password = data.get('password', '').strip()

    if not email or not nombre or not apellido_paterno:
        return _json_error('Campos obligatorios: email, nombre, apellido_paterno')

    if User.objects.filter(email=email).exists():
        return _json_error(f'Ya existe un usuario con email {email}')

    if rut and User.objects.filter(rut=rut).exists():
        return _json_error(f'Ya existe un usuario con RUT {rut}')

    role = None
    if rol_id:
        try:
            role = Role.objects.get(id=int(rol_id))
        except (Role.DoesNotExist, ValueError):
            return _json_error('Rol no encontrado')

    user = User(
        email=email,
        nombre=nombre,
        apellido_paterno=apellido_paterno,
        apellido_materno=apellido_materno or '',
        rut=rut,
        role=role,
        rbd_colegio=int(colegio_rbd) if colegio_rbd else None,
        is_active=True,
    )
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()

    return JsonResponse({
        'success': True,
        'message': f'Usuario {user.get_full_name()} creado exitosamente',
        'user_id': user.id,
    })


@login_required
@require_POST
def toggle_estado_usuario(request, user_id):
    """Activar o desactivar un usuario."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return _json_error('Usuario no encontrado', 404)

    if user.id == request.user.id:
        return _json_error('No puedes desactivar tu propia cuenta')

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])

    estado = 'activado' if user.is_active else 'desactivado'
    return JsonResponse({
        'success': True,
        'message': f'Usuario {user.get_full_name()} {estado}',
        'is_active': user.is_active,
    })


@login_required
@require_POST
def editar_usuario(request, user_id):
    """Editar datos de un usuario."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return _json_error('Usuario no encontrado', 404)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    fields_to_update = []

    if data.get('nombre'):
        user.nombre = data['nombre'].strip()
        fields_to_update.append('nombre')
    if data.get('apellido_paterno'):
        user.apellido_paterno = data['apellido_paterno'].strip()
        fields_to_update.append('apellido_paterno')
    if 'apellido_materno' in data:
        user.apellido_materno = data['apellido_materno'].strip()
        fields_to_update.append('apellido_materno')

    if data.get('rol_id'):
        try:
            user.role = Role.objects.get(id=int(data['rol_id']))
            fields_to_update.append('role')
        except (Role.DoesNotExist, ValueError):
            return _json_error('Rol no encontrado')

    if 'colegio_rbd' in data:
        user.rbd_colegio = int(data['colegio_rbd']) if data['colegio_rbd'] else None
        fields_to_update.append('rbd_colegio')

    if fields_to_update:
        user.save(update_fields=fields_to_update)

    return JsonResponse({
        'success': True,
        'message': f'Usuario {user.get_full_name()} actualizado',
    })


# ───────────────────────────────────────────
# PLANES
# ───────────────────────────────────────────

@login_required
@require_POST
def crear_plan(request):
    """Crear un nuevo plan de suscripción."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    nombre = data.get('nombre', '').strip()
    codigo = data.get('codigo', '').strip()

    if not nombre or not codigo:
        return _json_error('Nombre y código son obligatorios')

    if Plan.objects.filter(codigo=codigo).exists():
        return _json_error(f'Ya existe un plan con código {codigo}')

    plan = Plan.objects.create(
        nombre=nombre,
        codigo=codigo,
        descripcion=data.get('descripcion', ''),
        precio_mensual=data.get('precio_mensual', 0),
        duracion_dias=data.get('duracion_dias') or None,
        is_trial=data.get('is_trial', False),
        is_unlimited=data.get('is_unlimited', False),
    )

    return JsonResponse({
        'success': True,
        'message': f'Plan "{plan.nombre}" creado exitosamente',
        'plan_id': plan.id,
    })


@login_required
@require_POST
def editar_plan(request, plan_id):
    """Editar un plan existente."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        plan = Plan.objects.get(id=plan_id)
    except Plan.DoesNotExist:
        return _json_error('Plan no encontrado', 404)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    if data.get('nombre'):
        plan.nombre = data['nombre'].strip()
    if data.get('descripcion') is not None:
        plan.descripcion = data['descripcion']
    if data.get('precio_mensual') is not None:
        plan.precio_mensual = data['precio_mensual']

    plan.save()

    return JsonResponse({
        'success': True,
        'message': f'Plan "{plan.nombre}" actualizado',
    })


# ───────────────────────────────────────────
# SUSCRIPCIONES
# ───────────────────────────────────────────

@login_required
@require_POST
def crear_suscripcion(request):
    """Crear una nueva suscripción para un colegio."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    colegio_rbd = data.get('colegio_rbd')
    plan_id = data.get('plan_id')

    if not colegio_rbd or not plan_id:
        return _json_error('colegio_rbd y plan_id son obligatorios')

    try:
        colegio = Colegio.objects.get(rbd=int(colegio_rbd))
    except Colegio.DoesNotExist:
        return _json_error('Colegio no encontrado')

    try:
        plan = Plan.objects.get(id=int(plan_id))
    except Plan.DoesNotExist:
        return _json_error('Plan no encontrado')

    if Subscription.objects.filter(colegio=colegio).exists():
        return _json_error(f'{colegio.nombre} ya tiene una suscripción activa')

    sub = Subscription.objects.create(
        colegio=colegio,
        plan=plan,
        auto_renovar=data.get('auto_renovar', True),
    )

    return JsonResponse({
        'success': True,
        'message': f'Suscripción creada para {colegio.nombre}',
        'subscription_id': sub.id,
    })


@login_required
@require_POST
def toggle_estado_suscripcion(request, subscription_id):
    """Suspender o reactivar una suscripción."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        sub = Subscription.objects.select_related('colegio', 'plan').get(id=subscription_id)
    except Subscription.DoesNotExist:
        return _json_error('Suscripción no encontrada', 404)

    if sub.status == Subscription.STATUS_ACTIVE:
        sub.suspender('Suspendida por administrador del sistema')
        return JsonResponse({
            'success': True,
            'message': f'Suscripción de {sub.colegio.nombre} suspendida',
            'status': sub.status,
        })
    elif sub.status == Subscription.STATUS_SUSPENDED:
        sub.reactivar()
        return JsonResponse({
            'success': True,
            'message': f'Suscripción de {sub.colegio.nombre} reactivada',
            'status': sub.status,
        })
    else:
        return _json_error(f'No se puede cambiar el estado de una suscripción {sub.get_status_display()}')


# ───────────────────────────────────────────
# CONFIGURACIÓN DE AUDITORÍA
# ───────────────────────────────────────────

@login_required
@require_POST
def guardar_configuracion_auditoria(request):
    """Guardar la configuración global de auditoría."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    config = ConfiguracionAuditoria.get_config(None)
    # Si es un objeto en memoria (colegio_rbd='__global__' sin PK), crear en DB
    if not config.pk:
        config.colegio_rbd = '__global__'

    bool_fields = [
        'auditar_academico', 'auditar_asistencia', 'auditar_comunicacion',
        'auditar_estudiantes', 'auditar_usuarios', 'auditar_seguridad',
        'capturar_ip', 'capturar_user_agent', 'auditar_visualizaciones',
    ]
    for field in bool_fields:
        if field in data:
            setattr(config, field, bool(data[field]))

    if 'dias_retencion' in data:
        try:
            dias = int(data['dias_retencion'])
            config.dias_retencion = max(30, min(3650, dias))
        except (ValueError, TypeError):
            pass

    if 'hosts_permitidos' in data:
        config.hosts_permitidos = str(data['hosts_permitidos'] or '').strip()

    config.save()

    return JsonResponse({
        'success': True,
        'message': 'Configuración de auditoría guardada exitosamente',
    })


@login_required
def exportar_auditoria_csv(request):
    """Export system audit logs to CSV based on active filters."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    busqueda = request.GET.get('busqueda', '').strip()
    accion = request.GET.get('accion', '').strip()
    nivel = request.GET.get('nivel', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()

    qs = AuditoriaEvento.objects.all().order_by('-fecha_hora')

    if busqueda:
        qs = qs.filter(
            Q(usuario_nombre__icontains=busqueda) |
            Q(usuario_email__icontains=busqueda) |
            Q(ip_address__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(tabla_afectada__icontains=busqueda)
        )
    if accion:
        qs = qs.filter(accion=accion)
    if nivel:
        qs = qs.filter(nivel=nivel)
    if categoria:
        qs = qs.filter(categoria=categoria)
    if fecha_inicio:
        try:
            qs = qs.filter(fecha_hora__date__gte=datetime.strptime(fecha_inicio, '%Y-%m-%d').date())
        except ValueError:
            pass
    if fecha_fin:
        try:
            qs = qs.filter(fecha_hora__date__lte=datetime.strptime(fecha_fin, '%Y-%m-%d').date())
        except ValueError:
            pass

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"auditoria_sistema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Write BOM for UTF-8 compatibility with Excel
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Fecha y Hora', 'Usuario', 'Email', 'Rol', 'RBD Colegio',
        'Acción', 'Categoría', 'Nivel', 'Tabla Afectada', 'Dirección IP', 'Descripción'
    ])

    for e in qs[:5000]:
        writer.writerow([
            e.id,
            e.fecha_hora.strftime('%d/%m/%Y %H:%M:%S') if e.fecha_hora else '',
            e.usuario_nombre or 'Sistema',
            e.usuario_email or '',
            e.usuario_rol or '',
            e.colegio_rbd or '',
            e.get_accion_display(),
            e.get_categoria_display(),
            e.get_nivel_display(),
            e.tabla_afectada,
            e.ip_address or '',
            e.descripcion
        ])

    return response


@login_required
def exportar_estadisticas_globales_csv(request):
    """Export global platform usage statistics consolidate to CSV."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    colegio_rbd_raw = request.GET.get('colegio_rbd', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()

    rbd_filter = None
    if colegio_rbd_raw:
        try:
            rbd_filter = int(colegio_rbd_raw)
        except (TypeError, ValueError):
            rbd_filter = None

    colegios_qs = Colegio.objects.all_schools()
    users_qs = User.objects.all_schools()

    if rbd_filter is not None:
        colegios_qs = colegios_qs.filter(rbd=rbd_filter)
        users_qs = users_qs.filter(rbd_colegio=rbd_filter)

    if fecha_inicio:
        try:
            inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            users_qs = users_qs.filter(fecha_creacion__gte=inicio)
        except ValueError:
            pass

    if fecha_fin:
        try:
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            users_qs = users_qs.filter(fecha_creacion__lte=fin)
        except ValueError:
            pass

    total_escuelas = colegios_qs.count()
    total_usuarios = users_qs.count()
    total_profesores = users_qs.filter(role__nombre__iexact='profesor').count()
    total_estudiantes = users_qs.filter(role__nombre__iexact='estudiante').count()
    total_apoderados = users_qs.filter(role__nombre__iexact='apoderado').count()

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"estadisticas_globales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.write('\ufeff')
    writer = csv.writer(response)

    writer.writerow(['REPORTE DE ESTADÍSTICAS GLOBALES DEL SISTEMA'])
    writer.writerow(['Fecha de generación', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
    writer.writerow([])

    writer.writerow(['MÉTRICAS GENERALES'])
    writer.writerow(['Concepto', 'Total'])
    writer.writerow(['Escuelas / Colegios', total_escuelas])
    writer.writerow(['Usuarios Totales', total_usuarios])
    writer.writerow(['Profesores', total_profesores])
    writer.writerow(['Estudiantes', total_estudiantes])
    writer.writerow(['Apoderados', total_apoderados])
    writer.writerow([])

    writer.writerow(['DISTRIBUCIÓN DE USUARIOS POR ROL'])
    writer.writerow(['Rol', 'Cantidad'])
    roles_stats = users_qs.values('role__nombre').annotate(count=Count('id')).order_by('-count')
    for item in roles_stats:
        writer.writerow([item['role__nombre'] or 'Sin Rol', item['count']])
    writer.writerow([])

    writer.writerow(['COLEGIOS CON MAYOR CANTIDAD DE USUARIOS'])
    writer.writerow(['Colegio', 'RBD', 'Total Usuarios'])
    users_by_school = users_qs.filter(rbd_colegio__isnull=False).values('rbd_colegio').annotate(count=Count('id')).order_by('-count')
    colegios_map = {c.rbd: c.nombre for c in Colegio.objects.all()}
    for item in users_by_school:
        writer.writerow([
            colegios_map.get(item['rbd_colegio'], f"RBD {item['rbd_colegio']}"),
            item['rbd_colegio'],
            item['count']
        ])

    return response


@login_required
def exportar_reportes_financieros_csv(request):
    """Export global financial MRR/subscription logs to CSV."""
    if not _require_system_admin(request.user):
        return _json_error('Permisos insuficientes', 403)

    plan_id = request.GET.get('plan_id', '').strip()
    status = request.GET.get('status', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()

    subs = Subscription.objects.select_related('colegio', 'plan').all()

    if plan_id:
        subs = subs.filter(plan_id=plan_id)
    if status:
        subs = subs.filter(status=status)
    if fecha_inicio:
        try:
            inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            subs = subs.filter(fecha_inicio__gte=inicio)
        except ValueError:
            pass
    if fecha_fin:
        try:
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            subs = subs.filter(fecha_inicio__lte=fin)
        except ValueError:
            pass

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"reportes_financieros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.write('\ufeff')
    writer = csv.writer(response)

    writer.writerow(['REPORTE DE SUSCRIPCIONES Y FINANZAS SAAS'])
    writer.writerow(['Fecha de generación', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
    writer.writerow([])

    writer.writerow(['ID Suscripción', 'Colegio', 'RBD', 'Plan', 'Precio Mensual', 'Estado', 'Fecha Inicio', 'Fecha Fin', 'Auto-Renovar'])
    for sub in subs:
        writer.writerow([
            sub.id,
            sub.colegio.nombre,
            sub.colegio.rbd,
            sub.plan.nombre,
            int(sub.plan.precio_mensual),
            sub.get_status_display(),
            sub.fecha_inicio.strftime('%d/%m/%Y') if sub.fecha_inicio else '',
            sub.fecha_fin.strftime('%d/%m/%Y') if sub.fecha_fin else 'Sin vencimiento',
            'Sí' if sub.auto_renovar else 'No'
        ])

    return response

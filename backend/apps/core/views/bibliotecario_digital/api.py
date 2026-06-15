"""
API endpoints para Bibliotecario Digital.
- Crear / publicar recursos digitales
- Gestionar préstamos de recursos (crear, registrar devolución)
"""
import json
import logging
from datetime import date, timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.bibliotecario_api_service import BibliotecarioApiService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


def _get_rbd(request):
    return resolve_request_rbd(request)


@jwt_or_session_auth_required
@require_http_methods(['GET'])
def listar_recursos(request):
    """Lista recursos del colegio para selectores de préstamo."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRARY_VIEW', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = BibliotecarioApiService.list_recursos(rbd)
        return JsonResponse({'success': True, 'recursos': data})
    except Exception:
        logger.exception('Error listando recursos')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['GET'])
def listar_usuarios(request):
    """Lista usuarios del colegio para préstamos."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRARY_MANAGE_LOANS', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = BibliotecarioApiService.list_usuarios(rbd)
        return JsonResponse({'success': True, 'usuarios': data})
    except Exception:
        logger.exception('Error listando usuarios')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['GET'])
def listar_prestamos(request):
    """Lista préstamos activos para devolución rápida."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRARY_MANAGE_LOANS', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = BibliotecarioApiService.list_prestamos_activos(rbd)
        return JsonResponse({'success': True, 'prestamos': data})
    except Exception:
        logger.exception('Error listando préstamos')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def crear_recurso(request):
    """Crea un nuevo recurso digital en el catálogo."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRARY_CREATE', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para crear recursos'}, status=403)

    try:
        body = json.loads(request.body)
        titulo = (body.get('titulo') or '').strip()
        descripcion = (body.get('descripcion') or '').strip()
        tipo = body.get('tipo', 'DOCUMENTO')
        url_externa = (body.get('url_externa') or '').strip()
        publicado = bool(body.get('publicado', False))
        es_plan_lector = bool(body.get('es_plan_lector', False))

        if not titulo:
            return JsonResponse({'success': False, 'error': 'El título es obligatorio'}, status=400)

        tipos_validos = {'LIBRO', 'VIDEO', 'DOCUMENTO', 'ENLACE', 'SOFTWARE', 'MATERIAL_CRA'}
        if tipo not in tipos_validos:
            tipo = 'DOCUMENTO'

        recurso = BibliotecarioApiService.crear_recurso(
            rbd=rbd,
            user=request.user,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo,
            url_externa=url_externa,
            publicado=publicado,
            es_plan_lector=es_plan_lector,
        )

        return JsonResponse({
            'success': True,
            'message': 'Recurso creado correctamente',
            'id': recurso.id_recurso,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error creando recurso')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def toggle_publicar_recurso(request, recurso_id):
    """Activa/desactiva la publicación de un recurso."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRARY_EDIT', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para editar recursos'}, status=403)

    try:
        recurso = BibliotecarioApiService.get_recurso_or_none(recurso_id, rbd)
    except Exception:
        recurso = None
    if not recurso:
        return JsonResponse({'success': False, 'error': 'Recurso no encontrado'}, status=404)

    nuevo_publicado = BibliotecarioApiService.toggle_publicar(recurso)
    estado = 'publicado' if nuevo_publicado else 'despublicado'
    return JsonResponse({
        'success': True,
        'message': f'Recurso {estado} correctamente',
        'publicado': nuevo_publicado,
    })


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def crear_prestamo(request):
    """Registra un nuevo préstamo de recurso."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRARY_MANAGE_LOANS', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para gestionar préstamos'}, status=403)

    try:
        body = json.loads(request.body)
        recurso_id = body.get('recurso_id')
        usuario_id = body.get('usuario_id')
        dias = int(body.get('dias_prestamo', 14))
        fecha_devolucion = body.get('fecha_devolucion_esperada') or str(date.today() + timedelta(days=dias))

        if not recurso_id:
            return JsonResponse({'success': False, 'error': 'Debe seleccionar un recurso'}, status=400)
        if not usuario_id:
            return JsonResponse({'success': False, 'error': 'Debe seleccionar un usuario'}, status=400)

        recurso = BibliotecarioApiService.get_recurso_or_none(recurso_id, rbd)
        if not recurso:
            return JsonResponse({'success': False, 'error': 'Recurso no encontrado'}, status=404)

        usuario = BibliotecarioApiService.get_usuario_or_none(usuario_id, rbd)
        if not usuario:
            return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=404)

        prestamo = BibliotecarioApiService.crear_prestamo(
            recurso=recurso,
            usuario=usuario,
            rbd=rbd,
            fecha_devolucion=fecha_devolucion,
        )

        return JsonResponse({
            'success': True,
            'message': 'Préstamo registrado correctamente',
            'id': prestamo.id_prestamo,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception('Error creando préstamo')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@require_http_methods(['POST'])
def registrar_devolucion(request, prestamo_id):
    """Registra la devolución de un recurso prestado."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRARY_MANAGE_LOANS', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para gestionar préstamos'}, status=403)

    try:
        prestamo = BibliotecarioApiService.get_prestamo_or_none(prestamo_id, rbd)
    except Exception:
        prestamo = None
    if not prestamo:
        return JsonResponse({'success': False, 'error': 'Préstamo no encontrado'}, status=404)

    if prestamo.estado == 'DEVUELTO':
        return JsonResponse({'success': False, 'error': 'Este préstamo ya fue devuelto'}, status=400)

    BibliotecarioApiService.registrar_devolucion(prestamo)

    return JsonResponse({
        'success': True,
        'message': 'Devolución registrada correctamente',
    })

import csv
import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from backend.apps.academico.services.libro_clases_service import LibroClasesService
from backend.apps.academico.services.superintendencia_reports_service import SuperintendenciaReportsService
from backend.apps.auditoria.models import AuditoriaEvento
from backend.common.services.policy_service import PolicyService

logger = logging.getLogger(__name__)


def _get_rbd(request):
    return getattr(request.user, 'rbd_colegio', None)


def _parse_fecha(value):
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').date()


def _serialize_registro(registro):
    return {
        'id_registro': registro.id_registro,
        'colegio_id': registro.colegio_id,
        'clase_id': registro.clase_id,
        'curso': registro.clase.curso.nombre if registro.clase and registro.clase.curso else '',
        'asignatura': registro.clase.asignatura.nombre if registro.clase and registro.clase.asignatura else '',
        'profesor_id': registro.profesor_id,
        'fecha': registro.fecha.isoformat(),
        'numero_clase': registro.numero_clase,
        'contenido_tratado': registro.contenido_tratado,
        'tarea_asignada': registro.tarea_asignada or '',
        'observaciones': registro.observaciones or '',
        'firmado': registro.firmado,
        'fecha_firma': registro.fecha_firma.isoformat() if registro.fecha_firma else None,
        'hash_contenido': registro.hash_contenido,
    }


@login_required
@require_http_methods(['GET'])
def listar_registros_profesor(request):
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRO_CLASE_VIEW', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        clase_id = request.GET.get('clase_id')
        fecha = _parse_fecha(request.GET.get('fecha'))
        registros = LibroClasesService.list_registros(
            colegio_id=rbd,
            clase_id=int(clase_id) if clase_id else None,
            fecha=fecha,
            profesor_id=request.user.id,
        )
        return JsonResponse({'success': True, 'registros': [_serialize_registro(r) for r in registros]})
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Parámetros inválidos'}, status=400)
    except Exception:
        logger.exception('Error listando registros del libro de clases')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@login_required
@require_http_methods(['GET'])
def obtener_registro_profesor(request, registro_id):
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRO_CLASE_VIEW', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        registro = LibroClasesService.get_registro(
            colegio_id=rbd,
            registro_id=registro_id,
            profesor_id=request.user.id,
        )
        return JsonResponse({'success': True, 'registro': _serialize_registro(registro)})
    except Exception:
        logger.exception('Error obteniendo registro del libro de clases')
        return JsonResponse({'success': False, 'error': 'Registro no encontrado'}, status=404)


@login_required
@require_http_methods(['POST'])
def guardar_registro_profesor(request):
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRO_CLASE_EDIT', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para editar libro de clases'}, status=403)

    try:
        body = json.loads(request.body)
        clase_id = int(body.get('clase_id'))
        fecha = _parse_fecha(body.get('fecha'))
        numero_clase = int(body.get('numero_clase', 1))
        contenido_tratado = (body.get('contenido_tratado') or '').strip()
        tarea_asignada = (body.get('tarea_asignada') or '').strip()
        observaciones = (body.get('observaciones') or '').strip()

        if fecha is None or not contenido_tratado:
            return JsonResponse(
                {'success': False, 'error': 'Debe informar fecha y contenido tratado'},
                status=400,
            )

        registro, created = LibroClasesService.upsert_registro_profesor(
            user=request.user,
            colegio_id=rbd,
            clase_id=clase_id,
            fecha=fecha,
            numero_clase=numero_clase,
            contenido_tratado=contenido_tratado,
            tarea_asignada=tarea_asignada,
            observaciones=observaciones,
        )

        AuditoriaEvento.registrar_evento(
            usuario=request.user,
            accion=AuditoriaEvento.CREAR if created else AuditoriaEvento.MODIFICAR,
            tabla_afectada='registro_clase',
            descripcion=f"{'Creación' if created else 'Actualización'} de registro de clase por el docente",
            categoria=AuditoriaEvento.CATEGORIA_ACADEMICO,
            content_object=registro,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            nivel=AuditoriaEvento.NIVEL_INFO,
            metadata={
                'registro_id': registro.id_registro,
                'clase_id': registro.clase_id,
                'fecha': registro.fecha.isoformat(),
                'numero_clase': registro.numero_clase,
            }
        )

        return JsonResponse(
            {
                'success': True,
                'created': created,
                'registro': _serialize_registro(registro),
            }
        )
    except ValidationError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except ObjectDoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception:
        logger.exception('Error guardando registro del libro de clases')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@login_required
@require_http_methods(['POST'])
def firmar_registro_profesor(request, registro_id):
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRO_CLASE_FIRMAR', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para firmar'}, status=403)

    try:
        registro = LibroClasesService.firmar_registro_profesor(
            user=request.user,
            colegio_id=rbd,
            registro_id=registro_id,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:255],
        )

        AuditoriaEvento.registrar_evento(
            usuario=request.user,
            accion=AuditoriaEvento.MODIFICAR,
            tabla_afectada='registro_clase',
            descripcion="Firma digital del registro de clase por el docente",
            categoria=AuditoriaEvento.CATEGORIA_SEGURIDAD,
            content_object=registro,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            nivel=AuditoriaEvento.NIVEL_INFO,
            metadata={
                'registro_id': registro.id_registro,
                'clase_id': registro.clase_id,
                'fecha': registro.fecha.isoformat(),
                'numero_clase': registro.numero_clase,
                'hash_contenido': registro.hash_contenido,
            }
        )

        return JsonResponse({'success': True, 'registro': _serialize_registro(registro)})
    except ValidationError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception:
        logger.exception('Error firmando registro del libro de clases')
        return JsonResponse({'success': False, 'error': 'Registro no encontrado'}, status=404)


@login_required
@require_http_methods(['GET'])
def listar_registros_rbd(request):
    """Vista de lectura para Coordinador/Admin sobre registros del establecimiento."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'LIBRO_CLASE_VIEW_RBD', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)

    try:
        clase_id = request.GET.get('clase_id')
        fecha = _parse_fecha(request.GET.get('fecha'))
        profesor_id = request.GET.get('profesor_id')
        registros = LibroClasesService.list_registros(
            colegio_id=rbd,
            clase_id=int(clase_id) if clase_id else None,
            fecha=fecha,
            profesor_id=int(profesor_id) if profesor_id else None,
        )
        return JsonResponse({'success': True, 'registros': [_serialize_registro(r) for r in registros]})
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Parámetros inválidos'}, status=400)
    except Exception:
        logger.exception('Error listando registros del establecimiento')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@login_required
@require_http_methods(['GET'])
def exportar_reporte_superintendencia(request):
    """Exporta reporte mensual Decreto 67 para Superintendencia (json/csv/xlsx/pdf)."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'REPORT_EXPORT_SUPERINTENDENCIA', school_id=rbd):
        AuditoriaEvento.registrar_evento(
            usuario=request.user,
            accion=AuditoriaEvento.EXPORTAR,
            tabla_afectada='reporte_superintendencia',
            descripcion='Intento no autorizado de exportar reporte normativo',
            categoria=AuditoriaEvento.CATEGORIA_SEGURIDAD,
            nivel=AuditoriaEvento.NIVEL_WARNING,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            metadata={
                'format': (request.GET.get('format') or 'json').lower(),
                'month': request.GET.get('month'),
                'result': 'denied',
            },
        )
        return JsonResponse({'success': False, 'error': 'Sin permisos para exportar reportes normativos'}, status=403)

    try:
        raw_month = request.GET.get('month')
        export_format = (request.GET.get('format') or 'json').lower()

        year, month = SuperintendenciaReportsService.resolve_month(raw_month)
        payload = SuperintendenciaReportsService.build_monthly_payload(
            school_id=rbd,
            year=year,
            month=month,
        )

        if export_format == 'json':
            AuditoriaEvento.registrar_evento(
                usuario=request.user,
                accion=AuditoriaEvento.EXPORTAR,
                tabla_afectada='reporte_superintendencia',
                descripcion='Exportacion de reporte normativo (json)',
                categoria=AuditoriaEvento.CATEGORIA_ACADEMICO,
                nivel=AuditoriaEvento.NIVEL_INFO,
                ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
                user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
                metadata={
                    'format': 'json',
                    'month': payload['month'],
                    'result': 'success',
                },
            )
            return JsonResponse({'success': True, 'data': payload})

        artifact = SuperintendenciaReportsService.export_payload(payload, export_format)
        AuditoriaEvento.registrar_evento(
            usuario=request.user,
            accion=AuditoriaEvento.EXPORTAR,
            tabla_afectada='reporte_superintendencia',
            descripcion=f'Exportacion de reporte normativo ({export_format})',
            categoria=AuditoriaEvento.CATEGORIA_ACADEMICO,
            nivel=AuditoriaEvento.NIVEL_INFO,
            ip_address=(request.META.get('REMOTE_ADDR') or '')[:45],
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            metadata={
                'format': export_format,
                'month': payload['month'],
                'filename': artifact.filename,
                'result': 'success',
            },
        )
        response = HttpResponse(artifact.content, content_type=artifact.content_type)
        response['Content-Disposition'] = f'attachment; filename="{artifact.filename}"'
        return response
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception:
        logger.exception('Error exportando reporte de Superintendencia')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@login_required
@require_http_methods(['GET'])
def listar_auditoria_reporte_superintendencia(request):
    """Lista eventos de auditoria del reporte Superintendencia para el colegio activo."""
    rbd = _get_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Sin colegio asignado'}, status=400)

    if not PolicyService.has_capability(request.user, 'REPORT_EXPORT_SUPERINTENDENCIA', school_id=rbd):
        return JsonResponse({'success': False, 'error': 'Sin permisos para consultar auditoria normativa'}, status=403)

    try:
        month = request.GET.get('month')
        export_format = (request.GET.get('format') or '').lower().strip()
        result = (request.GET.get('result') or '').lower().strip()
        fecha_desde = (request.GET.get('fecha_desde') or '').strip()
        fecha_hasta = (request.GET.get('fecha_hasta') or '').strip()
        usuario = (request.GET.get('usuario') or '').strip()
        sort_by = (request.GET.get('sort_by') or 'fecha').lower().strip()
        sort_dir = (request.GET.get('sort_dir') or 'desc').lower().strip()
        limit_raw = request.GET.get('limit')
        page_raw = request.GET.get('page') or '1'
        page_size_raw = request.GET.get('page_size') or '20'
        download = (request.GET.get('download') or '').lower().strip()

        sort_map = {
            'fecha': 'fecha_hora',
            'usuario': 'usuario_nombre',
            'resultado': 'metadata__result',
        }
        if sort_by not in sort_map:
            return JsonResponse({'success': False, 'error': 'Parametro sort_by invalido'}, status=400)
        if sort_dir not in {'asc', 'desc'}:
            return JsonResponse({'success': False, 'error': 'Parametro sort_dir invalido'}, status=400)

        page = max(1, int(page_raw))
        page_size = max(1, min(int(page_size_raw), 100))

        # Backward compatibility: if limit is provided, keep previous behavior (single page constrained by limit).
        if limit_raw is not None:
            page = 1
            page_size = max(1, min(int(limit_raw), 200))

        qs = AuditoriaEvento.objects.filter(
            tabla_afectada='reporte_superintendencia',
            colegio_rbd=str(rbd),
        )

        if month:
            qs = qs.filter(metadata__month=month)
        if export_format:
            qs = qs.filter(metadata__format=export_format)
        if result:
            qs = qs.filter(metadata__result=result)
        if fecha_desde:
            fecha_desde_date = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            qs = qs.filter(fecha_hora__date__gte=fecha_desde_date)
        if fecha_hasta:
            fecha_hasta_date = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            qs = qs.filter(fecha_hora__date__lte=fecha_hasta_date)
        if usuario:
            if usuario.isdigit():
                qs = qs.filter(usuario_id=int(usuario))
            else:
                qs = qs.filter(Q(usuario_nombre__icontains=usuario) | Q(usuario_email__icontains=usuario))

        sort_field = sort_map[sort_by]
        if sort_dir == 'asc':
            qs = qs.order_by(sort_field, 'id')
        else:
            qs = qs.order_by(f'-{sort_field}', '-id')

        if download == 'csv':
            eventos_csv = qs[:5000]
            filename = f"auditoria_superintendencia_{rbd}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)
            writer.writerow(
                [
                    'id',
                    'fecha_hora',
                    'usuario_id',
                    'usuario_nombre',
                    'accion',
                    'categoria',
                    'nivel',
                    'format',
                    'month',
                    'result',
                    'filename',
                    'descripcion',
                ]
            )
            for evento in eventos_csv:
                metadata = evento.metadata or {}
                writer.writerow(
                    [
                        evento.id,
                        evento.fecha_hora.isoformat(),
                        evento.usuario_id,
                        evento.usuario_nombre,
                        evento.accion,
                        evento.categoria,
                        evento.nivel,
                        metadata.get('format'),
                        metadata.get('month'),
                        metadata.get('result'),
                        metadata.get('filename'),
                        evento.descripcion,
                    ]
                )
            return response

        total_count = qs.count()
        offset = (page - 1) * page_size
        eventos = qs[offset:offset + page_size]
        payload = []
        for evento in eventos:
            metadata = evento.metadata or {}
            payload.append(
                {
                    'id': evento.id,
                    'fecha_hora': evento.fecha_hora.isoformat(),
                    'usuario_id': evento.usuario_id,
                    'usuario_nombre': evento.usuario_nombre,
                    'accion': evento.accion,
                    'categoria': evento.categoria,
                    'nivel': evento.nivel,
                    'descripcion': evento.descripcion,
                    'format': metadata.get('format'),
                    'month': metadata.get('month'),
                    'result': metadata.get('result'),
                    'filename': metadata.get('filename'),
                }
            )

        total_pages = (total_count + page_size - 1) // page_size if total_count else 0
        return JsonResponse(
            {
                'success': True,
                'eventos': payload,
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': page < total_pages,
                'has_prev': page > 1,
                'total_pages': total_pages,
                'sort_by': sort_by,
                'sort_dir': sort_dir,
            }
        )
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Parametro de paginacion invalido'}, status=400)
    except Exception:
        logger.exception('Error listando auditoria de reporte Superintendencia')
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)

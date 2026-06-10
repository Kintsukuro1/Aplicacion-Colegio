"""
API endpoints para gestión de becas - Asesor Financiero
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.financial_documents_service import FinancialDocumentsService
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.apps.matriculas.models import Beca, Matricula
from backend.common.services import PermissionService
from backend.common.utils.auth_helpers import normalizar_rol
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'VIEW_SCHOLARSHIPS')
def estadisticas_becas(request):
    """
    Retorna estadísticas generales de becas
    """
    
    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Usuario sin colegio asignado'}, status=400)
    
    try:
        # Obtener ciclo academico activo/más reciente con matriculas activas
        ciclo_actual_id = ORMAccessService.filter(
            Matricula,
            colegio_id=rbd,
            estado="ACTIVA",
            ciclo_academico__isnull=False,
        ).values_list("ciclo_academico_id", flat=True).order_by(
            "-ciclo_academico__fecha_inicio", "-ciclo_academico_id"
        ).first()

        if not ciclo_actual_id:
            return JsonResponse({
                'success': True,
                'pendientes': 0,
                'activas': 0,
                'rechazadas': 0,
                'monto_total': 0
            })
        
        # Filtrar becas del año actual del colegio
        becas = ORMAccessService.filter(
            Beca,
            matricula__colegio_id=rbd,
            matricula__ciclo_academico_id=ciclo_actual_id,
        )
        
        # Contar por estado
        pendientes = becas.filter(estado__in=['SOLICITADA', 'EN_REVISION']).count()
        activas = becas.filter(estado__in=['APROBADA', 'VIGENTE']).count()
        rechazadas = becas.filter(estado='RECHAZADA').count()
        
        # Calcular monto total de becas activas
        # El monto depende de las cuotas que tienen beca aplicada
        # Calculamos el ahorro total estimado para becas activas
        from backend.apps.matriculas.models import Cuota
        becas_activas = becas.filter(estado__in=['APROBADA', 'VIGENTE']).select_related('matricula')
        becas_por_matricula = {
            beca.matricula_id: beca.porcentaje_descuento for beca in becas_activas if beca.matricula_id
        }

        monto_total = 0
        if becas_por_matricula:
            cuotas = ORMAccessService.filter(
                Cuota,
                matricula_id__in=becas_por_matricula.keys(),
                estado__in=['PENDIENTE', 'PAGADA', 'PAGADA_PARCIAL'],
            ).values('matricula_id', 'monto_original')

            for cuota in cuotas:
                porcentaje = Decimal(str(becas_por_matricula.get(cuota['matricula_id']) or 0))
                monto_original = Decimal(str(cuota.get('monto_original') or 0))
                monto_total += monto_original * (porcentaje / Decimal('100'))
        
        return JsonResponse({
            'success': True,
            'pendientes': pendientes,
            'activas': activas,
            'rechazadas': rechazadas,
            'monto_total': float(monto_total)
        })
        
    except Exception:
        logger.exception("Error al obtener estadísticas de becas")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'VIEW_SCHOLARSHIPS')
def listar_becas(request):
    """
    Lista becas según el estado/tab solicitado
    """

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Usuario sin colegio asignado'}, status=400)
    
    try:
        estado_filtro = request.GET.get('estado', 'pendientes')
        
        # Obtener ciclo academico activo/más reciente con matriculas activas
        ciclo_actual_id = ORMAccessService.filter(
            Matricula,
            colegio_id=rbd,
            estado="ACTIVA",
            ciclo_academico__isnull=False,
        ).values_list("ciclo_academico_id", flat=True).order_by(
            "-ciclo_academico__fecha_inicio", "-ciclo_academico_id"
        ).first()

        if not ciclo_actual_id:
            return JsonResponse({
                'success': True,
                'becas': [],
                'total': 0
            })
        
        becas = ORMAccessService.filter(
            Beca,
            matricula__colegio_id=rbd,
            matricula__ciclo_academico_id=ciclo_actual_id,
        ).select_related('estudiante', 'aprobada_por')

        if estado_filtro == 'pendientes':
            becas = becas.filter(estado__in=['SOLICITADA', 'EN_REVISION'])
        elif estado_filtro == 'activas':
            becas = becas.filter(estado__in=['APROBADA', 'VIGENTE'])
        elif estado_filtro == 'historial':
            becas = becas.filter(estado__in=['RECHAZADA', 'VENCIDA', 'CANCELADA'])

        becas = becas.order_by('-fecha_creacion')

        becas_list = []
        for beca in becas:
            estudiante = beca.estudiante
            nombre_completo = estudiante.get_full_name() if estudiante else 'Sin nombre'

            becas_list.append({
                'id': beca.id,
                'estudiante_nombre': nombre_completo,
                'estudiante_rut': getattr(estudiante, 'rut', None) or 'Sin RUT',
                'tipo_beca': beca.get_tipo_display(),
                'porcentaje': float(beca.porcentaje_descuento),
                'estado': beca.get_estado_display(),
                'fecha_solicitud': beca.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                'solicitada_por': 'Sistema',
                'fecha_inicio': beca.fecha_inicio.strftime('%d/%m/%Y'),
                'fecha_fin': beca.fecha_fin.strftime('%d/%m/%Y'),
                'motivo_solicitud': beca.motivo[:100] + '...' if len(beca.motivo) > 100 else beca.motivo,
                'aprobada_por': beca.aprobada_por.get_full_name() if beca.aprobada_por else None,
                'fecha_aprobacion': beca.fecha_aprobacion.strftime('%d/%m/%Y %H:%M') if beca.fecha_aprobacion else None,
            })
        
        return JsonResponse({
            'success': True,
            'becas': becas_list,
            'total': len(becas_list)
        })
        
    except Exception:
        logger.exception("Error al listar becas")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@PermissionService.require_permission('ACADEMICO', 'VIEW_STUDENTS')
def buscar_estudiantes_beca(request):
    """
    Busca estudiantes con matrícula activa para asignar beca
    """

    
    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Usuario sin colegio asignado'}, status=400)
    
    try:
        busqueda = request.GET.get('q', '').strip()
        
        if len(busqueda) < 3:
            return JsonResponse({'success': True, 'estudiantes': []})
        
        # Obtener ciclo academico activo/más reciente con matriculas activas
        ciclo_actual_id = ORMAccessService.filter(
            Matricula,
            colegio_id=rbd,
            estado="ACTIVA",
            ciclo_academico__isnull=False,
        ).values_list("ciclo_academico_id", flat=True).order_by(
            "-ciclo_academico__fecha_inicio", "-ciclo_academico_id"
        ).first()

        if not ciclo_actual_id:
            return JsonResponse({'success': True, 'estudiantes': []})
        
        # Buscar matrículas activas del año actual
        matriculas = ORMAccessService.filter(
            Matricula,
            colegio_id=rbd,
            ciclo_academico_id=ciclo_actual_id,
            estado='ACTIVA'
        ).select_related('estudiante', 'curso')
        
        # Filtrar por nombre o RUT
        matriculas = matriculas.filter(
            Q(estudiante__nombre__icontains=busqueda) |
            Q(estudiante__apellido_paterno__icontains=busqueda) |
            Q(estudiante__apellido_materno__icontains=busqueda) |
            Q(estudiante__rut__icontains=busqueda)
        )[:10]
        
        estudiantes_list = []
        for matricula in matriculas:
            est = matricula.estudiante
            nombre_completo = est.get_full_name()
            curso_nombre = str(matricula.curso) if matricula.curso else 'Sin curso'
            
            estudiantes_list.append({
                'matricula_id': matricula.id,
                'nombre': nombre_completo,
                'rut': est.rut,
                'curso': curso_nombre
            })
        
        return JsonResponse({
            'success': True,
            'estudiantes': estudiantes_list
        })
        
    except Exception:
        logger.exception("Error al buscar estudiantes para beca")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@require_http_methods(["POST"])
@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'PROCESS_SCHOLARSHIPS')
def crear_beca(request):
    """
    Crea una nueva beca con validaciones de seguridad mejoradas (Fase 4)
    """
    from backend.common.validations import CommonValidations
    from backend.common.utils.permissions import validar_permiso_usuario, validar_acceso_colegio
    import json

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Usuario sin colegio asignado'}, status=400)

    try:
        data = json.loads(request.body)

        # Preparar datos para validación
        beca_data = {
            'estudiante_id': data.get('matricula_id'),  # Usamos matricula_id como estudiante_id
            'tipo_beca': data.get('tipo_beca'),
            'monto': data.get('monto_beca', 0),  # Monto opcional
            'porcentaje': data.get('porcentaje_descuento'),
            'motivo': data.get('motivo_solicitud'),
            'fecha_inicio': data.get('fecha_inicio'),
            'fecha_fin': data.get('fecha_fin'),
            'descripcion': data.get('observaciones'),
        }

        # Validar datos de beca
        is_valid, error_msg = CommonValidations.validate_beca_data(beca_data, 'create')
        if not is_valid:
            return JsonResponse({'success': False, 'error': error_msg}, status=400)

        # Obtener matrícula y validar acceso
        matricula = ORMAccessService.filter(
            Matricula,
            id=data['matricula_id']
        ).select_related('estudiante', 'colegio').get()

        # Validar que la matrícula pertenece al colegio del usuario
        if not validar_acceso_colegio(request.user, matricula.colegio.rbd):
            return JsonResponse({
                'success': False,
                'error': 'No tiene acceso a esta matrícula'
            }, status=403)

        # Validar que la matrícula esté activa
        if matricula.estado != 'ACTIVA':
            return JsonResponse({
                'success': False,
                'error': 'La matrícula debe estar activa'
            }, status=400)

        # Verificar duplicados - no permitir becas activas para la misma matrícula y tipo
        beca_existente = ORMAccessService.filter(
            Beca,
            matricula=matricula,
            tipo=data['tipo_beca'],
            estado__in=['SOLICITADA', 'EN_REVISION', 'APROBADA', 'VIGENTE']
        ).exists()

        if beca_existente:
            return JsonResponse({
                'success': False,
                'error': 'Ya existe una beca activa del mismo tipo para este estudiante'
            }, status=400)

        # Validar fechas adicionales
        fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()

        # Validar que las fechas estén dentro del año escolar
        if matricula.anio_escolar:
            if fecha_inicio.year != matricula.anio_escolar or fecha_fin.year != matricula.anio_escolar:
                return JsonResponse({
                    'success': False,
                    'error': 'Las fechas de la beca deben estar dentro del año escolar de la matrícula'
                }, status=400)

        beca = FinancialDocumentsService.create_beca(
            user=request.user,
            matricula=matricula,
            data=data,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )

        return JsonResponse({
            'success': True,
            'message': 'Beca creada exitosamente',
            'beca_id': beca.id
        })

    except Matricula.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Matrícula no encontrada o no tiene acceso'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        }, status=400)
    except Exception as e:
        # Log del error para debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creando beca: {str(e)}", exc_info=True)

        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)

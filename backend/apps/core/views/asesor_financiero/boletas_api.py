"""
API endpoints para gestión de boletas - Asesor Financiero
"""
import json
import logging
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.financial_documents_service import FinancialDocumentsService
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.apps.matriculas.models import Boleta
from backend.common.services import PermissionService
from backend.common.utils.auth_helpers import normalizar_rol
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'VIEW_INVOICES')
def estadisticas_boletas(request):
    """
    Retorna estadísticas de boletas emitidas
    """
    
    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Usuario sin colegio asignado'}, status=400)
    
    try:
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        
        # Filtrar boletas por estudiantes del colegio
        # El modelo Boleta tiene FK a estudiante, no a colegio directamente
        from backend.apps.accounts.models import User
        from backend.apps.matriculas.models import Matricula
        
        # Obtener IDs de estudiantes del colegio
        estudiantes_ids = ORMAccessService.filter(
            Matricula,
            colegio_id=rbd,
            estado='ACTIVA'
        ).values_list('estudiante_id', flat=True).distinct()
        
        # Filtrar boletas de estudiantes del colegio
        boletas = ORMAccessService.filter(Boleta, estudiante_id__in=estudiantes_ids)
        
        # Boletas de hoy
        boletas_hoy = boletas.filter(fecha_emision__date=hoy).count()
        
        # Boletas del mes actual
        boletas_mes = boletas.filter(fecha_emision__date__gte=inicio_mes).count()
        
        # Monto total del mes
        monto_total = boletas.filter(
            fecha_emision__date__gte=inicio_mes
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'boletas_hoy': boletas_hoy,
            'boletas_mes': boletas_mes,
            'monto_total_mes': float(monto_total)
        })
        
    except Exception:
        logger.exception("Error al obtener estadísticas de boletas")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'VIEW_INVOICES')
def listar_boletas(request):
    """
    Lista boletas recientes con filtros
    """

    
    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Usuario sin colegio asignado'}, status=400)
    
    try:
        from backend.apps.matriculas.models import Matricula
        
        # Obtener parámetros de búsqueda
        busqueda = request.GET.get('busqueda', '').strip()
        mes = request.GET.get('mes', '')
        anio = request.GET.get('anio', '')
        
        # Obtener IDs de estudiantes del colegio
        estudiantes_ids = ORMAccessService.filter(
            Matricula,
            colegio_id=rbd,
            estado='ACTIVA'
        ).values_list('estudiante_id', flat=True).distinct()
        
        # Filtrar boletas de estudiantes del colegio
        boletas = ORMAccessService.filter(
            Boleta,
            estudiante_id__in=estudiantes_ids
        ).select_related('estudiante', 'pago')
        
        # Aplicar búsqueda por número de boleta o nombre de estudiante
        if busqueda:
            boletas = boletas.filter(
                Q(numero_boleta__icontains=busqueda) |
                Q(estudiante__nombre__icontains=busqueda) |
                Q(estudiante__apellido_paterno__icontains=busqueda) |
                Q(estudiante__apellido_materno__icontains=busqueda) |
                Q(estudiante__rut__icontains=busqueda)
            )
        
        # Filtrar por mes/año
        if mes and anio:
            try:
                boletas = boletas.filter(
                    fecha_emision__month=int(mes),
                    fecha_emision__year=int(anio)
                )
            except ValueError:
                pass
        elif anio:
            try:
                boletas = boletas.filter(fecha_emision__year=int(anio))
            except ValueError:
                pass
        
        # Ordenar por fecha descendente y limitar a 50
        boletas = boletas.order_by('-fecha_emision')[:50]
        
        # Preparar lista de boletas
        boletas_list = []
        for boleta in boletas:
            estudiante = boleta.estudiante
            nombre_receptor = estudiante.get_full_name()
            rut_receptor = estudiante.rut if hasattr(estudiante, 'rut') and estudiante.rut else 'Sin RUT'
            
            # El modelo migrado no tiene tipo_boleta, usamos 'Boleta' por defecto
            tipo_boleta = 'Boleta'
            
            boleta_data = {
                'id': boleta.id,
                'numero_boleta': boleta.numero_boleta,
                'tipo_boleta': tipo_boleta,
                'nombre_receptor': nombre_receptor,
                'rut_receptor': rut_receptor,
                'monto_total': float(boleta.monto_total),
                'fecha_emision': boleta.fecha_emision.strftime('%Y-%m-%d %H:%M'),
                'fecha_emision_formatted': boleta.fecha_emision.strftime('%d/%m/%Y %H:%M'),
                'estado': boleta.estado,
                'estado_display': boleta.get_estado_display() if hasattr(boleta, 'get_estado_display') else boleta.estado,
                'detalle': boleta.detalle if hasattr(boleta, 'detalle') else '',
                'pdf_url': boleta.archivo_pdf.url if hasattr(boleta, 'archivo_pdf') and boleta.archivo_pdf else None
            }
            boletas_list.append(boleta_data)
        
        return JsonResponse({
            'success': True,
            'boletas': boletas_list,
            'total': len(boletas_list)
        })
        
    except Exception:
        logger.exception("Error al listar boletas")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'}, status=500)


@require_http_methods(["POST"])
@jwt_or_session_auth_required
@PermissionService.require_permission('FINANCIERO', 'PROCESS_INVOICES')
def crear_boleta(request):
    """
    Crea una nueva boleta con validaciones de seguridad mejoradas (Fase 4)
    """
    from backend.common.validations import CommonValidations
    from backend.common.utils.permissions import validar_permiso_usuario, validar_acceso_colegio

    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({'success': False, 'error': 'Usuario sin colegio asignado'}, status=400)

    try:
        data = json.loads(request.body)

        # Preparar datos para validación
        boleta_data = {
            'estudiante_id': data.get('estudiante_id'),
            'cuota_id': data.get('cuota_id'),
            'monto_total': data.get('monto_total'),
            'fecha_emision': data.get('fecha_emision'),
            'detalle': data.get('detalle'),
        }

        # Validar datos de boleta
        is_valid, error_msg = CommonValidations.validate_boleta_data(boleta_data, 'create')
        if not is_valid:
            return JsonResponse({'success': False, 'error': error_msg}, status=400)

        # Obtener estudiante y validar acceso
        from backend.apps.accounts.models import User
        estudiante = ORMAccessService.get(User, id=data['estudiante_id'])

        # Validar que el estudiante pertenece al colegio del usuario
        if not validar_acceso_colegio(request.user, estudiante.rbd_colegio):
            return JsonResponse({
                'success': False,
                'error': 'No tiene acceso a este estudiante'
            }, status=403)

        # Validar que el estudiante tenga matrícula activa
        from backend.apps.matriculas.models import Matricula
        matricula_activa = ORMAccessService.filter(
            Matricula,
            estudiante=estudiante,
            estado='ACTIVA'
        ).exists()

        if not matricula_activa:
            return JsonResponse({
                'success': False,
                'error': 'El estudiante debe tener una matrícula activa'
            }, status=400)

        # Obtener pago asociado (requerido para crear boleta)
        from backend.apps.matriculas.models import Pago
        pago = ORMAccessService.get(Pago, id=data.get('pago_id')) if data.get('pago_id') else None

        if pago is None:
            return JsonResponse({
                'success': False,
                'error': 'Debe indicar pago_id válido para generar boleta'
            }, status=400)

        # Validar consistencia del pago
        if pago.estudiante != estudiante:
            return JsonResponse({
                'success': False,
                'error': 'El pago no pertenece al estudiante especificado'
            }, status=400)
        if pago.cuota.matricula.colegio_id != rbd:
            return JsonResponse({
                'success': False,
                'error': 'El pago no pertenece al colegio del usuario'
            }, status=403)

        # Generar número de boleta único
        numero_boleta = generar_numero_boleta(rbd)

        monto_total = Decimal(str(data['monto_total']))
        if pago.monto != monto_total:
            return JsonResponse({
                'success': False,
                'error': 'El monto del pago no coincide con el monto_total enviado'
            }, status=400)

        boleta = FinancialDocumentsService.create_boleta(
            user=request.user,
            estudiante=estudiante,
            pago=pago,
            numero_boleta=numero_boleta,
            monto_total=monto_total,
            detalle=data.get('detalle', ''),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )

        return JsonResponse({
            'success': True,
            'message': 'Boleta creada exitosamente',
            'boleta_id': boleta.id,
            'numero_boleta': numero_boleta
        })

    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Estudiante no encontrado'
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
        logger.error(f"Error creando boleta: {str(e)}", exc_info=True)

        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


def generar_numero_boleta(rbd_colegio):
    """
    Genera un número de boleta único para el colegio
    Formato: RBD + AÑO + SECUENCIAL (ej: 1234520240001)
    """
    from django.db.models import Max

    anio_actual = timezone.now().year

    # Obtener el último número de boleta del colegio en el año actual
    ultimo_numero = ORMAccessService.filter(
        Boleta,
        estudiante__rbd_colegio=rbd_colegio,
        numero_boleta__startswith=f"{rbd_colegio}{anio_actual}"
    ).aggregate(max_num=Max('numero_boleta'))['max_num']

    if ultimo_numero:
        # Extraer la parte secuencial (últimos 4 dígitos)
        secuencial = int(ultimo_numero[-4:]) + 1
    else:
        secuencial = 1

    # Formatear número de boleta
    numero_boleta = f"{rbd_colegio}{anio_actual}{secuencial:04d}"

    return numero_boleta

from __future__ import annotations

import csv
import hashlib
import io
import hmac

from django.conf import settings
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from backend.apps.api.tasks import process_payment_webhook_task
from backend.common.services.policy_service import PolicyService

from backend.apps.institucion.models import Colegio
from backend.apps.subscriptions.models import Plan
from backend.apps.subscriptions.services.payment_service import PaymentService


@api_view(['GET'])
@permission_classes([AllowAny])
def plans_list(request):
    plans = []
    for plan in PaymentService.list_active_plans():
        plans.append(
            {
                'codigo': plan.codigo,
                'nombre': plan.nombre,
                'descripcion': plan.descripcion,
                'precio_mensual': str(plan.precio_mensual),
                'destacado': plan.destacado,
                'is_trial': plan.is_trial,
                'is_unlimited': plan.is_unlimited,
                'limites': {
                    'estudiantes': plan.get_limite_display('max_estudiantes'),
                    'profesores': plan.get_limite_display('max_profesores'),
                    'cursos': plan.get_limite_display('max_cursos'),
                    'mensajes_mes': plan.get_limite_display('max_mensajes_mes'),
                    'evaluaciones_mes': plan.get_limite_display('max_evaluaciones_mes'),
                    'almacenamiento_mb': plan.get_limite_display('max_almacenamiento_mb'),
                },
                'features': {
                    'attendance': plan.has_attendance,
                    'grades': plan.has_grades,
                    'messaging': plan.has_messaging,
                    'reports': plan.has_reports,
                    'advanced_reports': plan.has_advanced_reports,
                    'attachments': plan.has_file_attachments,
                    'api_access': plan.has_api_access,
                    'priority_support': plan.has_priority_support,
                    'branding': plan.has_custom_branding,
                },
            }
        )
    return Response({'plans': plans}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_providers(request):
    providers = list(PaymentService.list_payment_providers())
    return Response({'providers': providers}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout(request):
    plan_codigo = str(request.data.get('plan_codigo') or '').strip()
    provider = str(request.data.get('provider') or '').strip() or None
    colegio_rbd = request.data.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    if not plan_codigo:
        return Response({'detail': 'plan_codigo es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
    if colegio_rbd is None:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        colegio = Colegio.objects.get(rbd=colegio_rbd)
        plan = Plan.objects.get(codigo=plan_codigo, activo=True)
        result = PaymentService.create_checkout(colegio=colegio, plan=plan, user=request.user, provider=provider)
    except Colegio.DoesNotExist:
        return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(
        {
            'payment_id': result.payment_id,
            'external_id': result.external_id,
            'provider': result.provider,
            'status': result.status,
            'checkout_url': result.checkout_url,
            'instructions': result.instructions,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    colegio_rbd = request.query_params.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    is_admin = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
    if colegio_rbd is None and not is_admin:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    payments = PaymentService.history_for_school(school_id=colegio_rbd)
    history = []
    for payment in payments:
        history.append(
            {
                'id': payment.id,
                'external_id': payment.external_id,
                'plan': payment.subscription.plan.nombre if payment.subscription and payment.subscription.plan else '',
                'monto': str(payment.monto),
                'moneda': payment.moneda,
                'status': payment.status,
                'gateway': payment.gateway,
                'fecha_pago': payment.fecha_pago.isoformat() if payment.fecha_pago else None,
                'fecha_creacion': payment.fecha_creacion.isoformat() if payment.fecha_creacion else None,
            }
        )

    return Response({'payments': history}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transfer_notices(request):
    colegio_rbd = request.query_params.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    is_admin = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
    if colegio_rbd is None and not is_admin:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    status_filter = str(request.query_params.get('status') or '').strip().lower() or None
    gateway_filter = str(request.query_params.get('gateway') or '').strip().lower() or None
    since_filter = str(request.query_params.get('since') or '').strip() or None
    until_filter = str(request.query_params.get('until') or '').strip() or None

    school_id_to_pass = None
    if colegio_rbd is not None:
        try:
            colegio = Colegio.objects.get(rbd=colegio_rbd)
            school_id_to_pass = colegio.rbd
        except Colegio.DoesNotExist:
            return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    payments = PaymentService.list_transfer_notices(
        school_id=school_id_to_pass,
        status_filter=status_filter,
        gateway_filter=gateway_filter,
        since_filter=since_filter,
        until_filter=until_filter,
    )
    notices = []
    for payment in payments:
        notice = (payment.metadata_json or {}).get('bank_transfer_notice', {})
        notices.append(
            {
                'payment_id': payment.id,
                'external_id': payment.external_id,
                'plan': payment.subscription.plan.nombre if payment.subscription and payment.subscription.plan else '',
                'gateway': payment.gateway,
                'status': payment.status,
                'monto': str(payment.monto),
                'moneda': payment.moneda,
                'fecha_creacion': payment.fecha_creacion.isoformat() if payment.fecha_creacion else None,
                'notice': notice,
            }
        )

    return Response({'notices': notices}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transfer_notices_export(request):
    colegio_rbd = request.query_params.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    is_admin = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
    if colegio_rbd is None and not is_admin:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    status_filter = str(request.query_params.get('status') or '').strip().lower() or None
    gateway_filter = str(request.query_params.get('gateway') or '').strip().lower() or None
    since_filter = str(request.query_params.get('since') or '').strip() or None
    until_filter = str(request.query_params.get('until') or '').strip() or None

    school_id_to_pass = None
    filename_suffix = "todos"
    if colegio_rbd is not None:
        try:
            colegio = Colegio.objects.get(rbd=colegio_rbd)
            school_id_to_pass = colegio.rbd
            filename_suffix = str(colegio.rbd)
        except Colegio.DoesNotExist:
            return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    payments = PaymentService.list_transfer_notices(
        school_id=school_id_to_pass,
        status_filter=status_filter,
        gateway_filter=gateway_filter,
        since_filter=since_filter,
        until_filter=until_filter,
    )
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow([
        'payment_id',
        'external_id',
        'plan',
        'gateway',
        'status',
        'monto',
        'moneda',
        'reference',
        'bank_name',
        'account_holder',
        'notes',
        'fecha_creacion',
        'received_at',
    ])

    for payment in payments:
        notice = (payment.metadata_json or {}).get('bank_transfer_notice', {})
        writer.writerow([
            payment.id,
            payment.external_id,
            payment.subscription.plan.nombre if payment.subscription and payment.subscription.plan else '',
            payment.gateway,
            payment.status,
            str(payment.monto),
            payment.moneda,
            notice.get('reference', ''),
            notice.get('bank_name', ''),
            notice.get('account_holder', ''),
            notice.get('notes', ''),
            payment.fecha_creacion.isoformat() if payment.fecha_creacion else '',
            notice.get('received_at', ''),
        ])

    response = HttpResponse(stream.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="transferencias_{filename_suffix}.csv"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_transfer_notice(request):
    payment_id = request.data.get('payment_id')
    if not payment_id:
        return Response({'detail': 'payment_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

    colegio_rbd = request.data.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    if colegio_rbd is None:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        colegio = Colegio.objects.get(rbd=colegio_rbd)
        payment = colegio.subscription.payments.select_related('subscription__plan').get(id=payment_id)
    except Colegio.DoesNotExist:
        return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response({'detail': 'Pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        updated_payment = PaymentService.approve_transfer_payment(payment=payment, user=request.user)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(
        {
            'detail': 'Transferencia conciliada y aprobada.',
            'payment_id': updated_payment.id,
            'status': updated_payment.status,
            'gateway': updated_payment.gateway,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notify_transfer(request):
    payment_id = request.data.get('payment_id')
    if not payment_id:
        return Response({'detail': 'payment_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

    colegio_rbd = request.data.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    if colegio_rbd is None:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        colegio = Colegio.objects.get(rbd=colegio_rbd)
        payment = colegio.subscription.payments.get(id=payment_id)
    except Colegio.DoesNotExist:
        return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response({'detail': 'Pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    updated_payment = PaymentService.register_transfer_notice(payment=payment, payload=request.data, user=request.user)
    return Response(
        {
            'detail': 'Aviso de transferencia registrado.',
            'payment_id': updated_payment.id,
            'gateway': updated_payment.gateway,
            'metadata': updated_payment.metadata_json,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_subscription(request):
    """Upgrade a un plan superior.
    
    POST /api/v1/subscriptions/upgrade/
    {
        "plan_codigo": "premium",
        "colegio_rbd": 123  # opcional, usa rbd_colegio del usuario si no se proporciona
    }
    """
    plan_codigo = str(request.data.get('plan_codigo') or '').strip()
    colegio_rbd = request.data.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    
    if not plan_codigo:
        return Response({'detail': 'plan_codigo es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
    if colegio_rbd is None:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        colegio = Colegio.objects.get(rbd=colegio_rbd)
        plan = Plan.objects.get(codigo=plan_codigo, activo=True)
        subscription = colegio.subscription
        subscription.upgrade_to(plan)
    except Colegio.DoesNotExist:
        return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

    return Response(
        {
            'detail': f'Suscripción actualizada a {plan.nombre}.',
            'plan_nombre': plan.nombre,
            'plan_codigo': plan.codigo,
            'fecha_inicio': subscription.fecha_inicio.isoformat(),
            'fecha_fin': subscription.fecha_fin.isoformat() if subscription.fecha_fin else None,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancelar la suscripción actual.
    
    POST /api/v1/subscriptions/cancel/
    """
    colegio_rbd = request.data.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    if colegio_rbd is None:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        colegio = Colegio.objects.get(rbd=colegio_rbd)
        subscription = colegio.subscription
        if subscription.cancelar():
            return Response(
                {
                    'detail': 'Suscripción cancelada.',
                    'plan_nombre': subscription.plan.nombre,
                    'status': subscription.get_status_display(),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {'detail': 'No se puede cancelar un plan ilimitado.'},
                status=status.HTTP_409_CONFLICT,
            )
    except Colegio.DoesNotExist:
        return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def renew_subscription(request):
    """Renovar la suscripción actual por X días.
    
    POST /api/v1/subscriptions/renew/
    {
        "dias": 30
    }
    """
    colegio_rbd = request.data.get('colegio_rbd') or getattr(request.user, 'rbd_colegio', None)
    dias = request.data.get('dias', 30)
    
    if colegio_rbd is None:
        return Response({'detail': 'No se pudo resolver el colegio.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        colegio = Colegio.objects.get(rbd=colegio_rbd)
        subscription = colegio.subscription
        subscription.renovar(dias=dias)
        
        return Response(
            {
                'detail': f'Suscripción renovada por {dias} días.',
                'plan_nombre': subscription.plan.nombre,
                'fecha_fin': subscription.fecha_fin.isoformat() if subscription.fecha_fin else None,
                'status': subscription.get_status_display(),
            },
            status=status.HTTP_200_OK,
        )
    except Colegio.DoesNotExist:
        return Response({'detail': 'Colegio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def payment_webhook(request):
    expected_token = getattr(settings, 'PAYMENT_WEBHOOK_TOKEN', '')
    expected_secret = getattr(settings, 'PAYMENT_WEBHOOK_SECRET', '')

    if expected_secret:
        provided_signature = request.headers.get('X-Webhook-Signature') or request.query_params.get('signature')
        if not _is_valid_webhook_signature(request.body, provided_signature, expected_secret):
            return Response({'detail': 'Firma de webhook invalida.'}, status=status.HTTP_403_FORBIDDEN)
    elif expected_token:
        provided_token = request.headers.get('X-Webhook-Token') or request.query_params.get('token')
        if provided_token != expected_token:
            return Response({'detail': 'Firma de webhook invalida.'}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if isinstance(request.data, dict) else {}
    
    # Process webhook asynchronously to prevent gateway timeouts
    process_payment_webhook_task.delay(payload)

    event_type = PaymentService._normalize_webhook_event(payload)

    return Response(
        {
            'detail': 'Webhook encolado para procesamiento.',
            'event_type': event_type,
        },
        status=status.HTTP_200_OK,
    )


def _is_valid_webhook_signature(body: bytes, provided_signature: str | None, expected_secret: str) -> bool:
    if not provided_signature:
        return False

    normalized_signature = str(provided_signature).strip()
    if normalized_signature.lower().startswith('sha256='):
        normalized_signature = normalized_signature.split('=', 1)[1].strip()

    expected_signature = hmac.new(
        expected_secret.encode('utf-8'),
        body or b'',
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(normalized_signature, expected_signature)

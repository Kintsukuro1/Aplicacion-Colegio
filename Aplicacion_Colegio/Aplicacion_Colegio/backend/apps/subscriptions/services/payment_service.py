"""Servicio de pagos para suscripciones."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from backend.apps.institucion.models import Colegio
from backend.apps.subscriptions.models import Payment, Plan, Subscription


@dataclass(frozen=True)
class CheckoutResult:
    payment_id: int
    external_id: str
    checkout_url: str
    provider: str
    status: str
    instructions: Optional[Dict[str, Any]] = None


class PaymentService:
    """Operaciones de dominio para pagos y checkout."""

    DEFAULT_PROVIDER = 'bank_transfer'
    SUPPORTED_PROVIDERS = {
        'bank_transfer',
        'bank_transfer_bancoestado',
        'webpay',
        'mercadopago',
    }

    @staticmethod
    def list_active_plans() -> Iterable[Plan]:
        return Plan.objects.filter(activo=True).order_by('orden_visualizacion', 'precio_mensual')

    @staticmethod
    def create_checkout(*, colegio: Colegio, plan: Plan, user=None, provider: Optional[str] = None) -> CheckoutResult:
        provider = PaymentService._normalize_provider(provider)
        subscription = Subscription.objects.select_related('plan', 'colegio').get(colegio=colegio)
        if subscription.is_active() and subscription.plan_id == plan.id:
            raise ValueError('El colegio ya tiene este plan activo.')

        external_id = uuid.uuid4().hex
        payment = Payment.objects.create(
            subscription=subscription,
            external_id=external_id,
            monto=PaymentService._plan_amount(plan),
            moneda='CLP',
            status=Payment.STATUS_PENDING,
            gateway=provider,
            metadata_json={
                'plan_codigo': plan.codigo,
                'plan_nombre': plan.nombre,
                'colegio_rbd': colegio.rbd,
                'requested_by': getattr(user, 'id', None),
                'payment_provider': provider,
            },
        )

        checkout_url = PaymentService._build_checkout_url(payment=payment, plan=plan, colegio=colegio, provider=provider)
        return CheckoutResult(
            payment_id=payment.id,
            external_id=payment.external_id,
            checkout_url=checkout_url,
            provider=payment.gateway,
            status=payment.status,
            instructions=PaymentService._provider_instructions(payment=payment, colegio=colegio, plan=plan, provider=provider),
        )

    @staticmethod
    def list_payment_providers() -> Iterable[Dict[str, Any]]:
        return (
            {
                'codigo': 'bank_transfer_bancoestado',
                'nombre': 'Transferencia BancoEstado',
                'tipo': 'bank_transfer',
                'descripcion': 'Transferencia bancaria directa para colegios en Chile.',
                'active': True,
            },
            {
                'codigo': 'webpay',
                'nombre': 'Webpay (Transbank)',
                'tipo': 'card',
                'descripcion': 'Tarjeta de débito/crédito con flujo local chileno.',
                'active': True,
            },
            {
                'codigo': 'mercadopago',
                'nombre': 'MercadoPago',
                'tipo': 'wallet',
                'descripcion': 'Wallet y medios locales LATAM.',
                'active': False,
            },
        )

    @staticmethod
    def process_webhook(payload: Dict[str, Any]) -> Optional[Payment]:
        payload = payload or {}
        external_id = PaymentService._extract_external_id(payload)
        if external_id is None:
            raise ValueError('Webhook sin external_id/external_reference.')

        payment = Payment.objects.select_related('subscription__plan', 'subscription__colegio').filter(
            external_id=str(external_id)
        ).first()
        if payment is None:
            raise ValueError('Pago no encontrado.')

        status = PaymentService._normalize_status(payload)
        event_type = PaymentService._normalize_webhook_event(payload)

        if PaymentService._is_duplicate_webhook(payment=payment, payload=payload, status=status):
            PaymentService._store_webhook_payload(payment=payment, payload=payload, event_type=event_type)
            return payment

        if status == Payment.STATUS_APPROVED:
            PaymentService._apply_approved_payment(payment=payment, payload=payload)
        elif status == Payment.STATUS_REJECTED:
            payment.mark_rejected()
            PaymentService._store_webhook_payload(payment=payment, payload=payload, event_type=event_type)
        else:
            PaymentService._store_webhook_payload(payment=payment, payload=payload, event_type=event_type)

        return payment

    @staticmethod
    def history_for_school(*, school_id: Optional[int] = None):
        qs = Payment.objects.select_related('subscription__plan', 'subscription__colegio')
        if school_id is not None:
            qs = qs.filter(subscription__colegio_id=school_id)
        return qs.order_by('-fecha_creacion')

    @staticmethod
    def list_transfer_notices(*, school_id: Optional[int] = None, status_filter: Optional[str] = None, gateway_filter: Optional[str] = None, since_filter: Optional[str] = None, until_filter: Optional[str] = None):
        qs = Payment.objects.select_related('subscription__plan', 'subscription__colegio').filter(
            gateway__in=['bank_transfer', 'bank_transfer_bancoestado'],
        )
        if school_id is not None:
            qs = qs.filter(subscription__colegio_id=school_id)
        payments = qs.order_by('-fecha_creacion')
        notice_payments = [payment for payment in payments if (payment.metadata_json or {}).get('bank_transfer_notice')]

        if status_filter:
            notice_payments = [payment for payment in notice_payments if payment.status == status_filter]

        if gateway_filter:
            notice_payments = [payment for payment in notice_payments if payment.gateway == gateway_filter]

        if since_filter:
            notice_payments = [payment for payment in notice_payments if (payment.fecha_creacion and payment.fecha_creacion.date().isoformat() >= since_filter)]

        if until_filter:
            notice_payments = [payment for payment in notice_payments if (payment.fecha_creacion and payment.fecha_creacion.date().isoformat() <= until_filter)]

        return notice_payments

    @staticmethod
    def register_transfer_notice(*, payment: Payment, payload: Dict[str, Any], user=None) -> Payment:
        metadata = dict(payment.metadata_json or {})
        metadata['bank_transfer_notice'] = {
            'received_at': timezone.now().isoformat(),
            'reported_by': getattr(user, 'id', None),
            'reference': str(payload.get('reference') or payload.get('transfer_reference') or '').strip(),
            'bank_name': str(payload.get('bank_name') or '').strip(),
            'account_holder': str(payload.get('account_holder') or '').strip(),
            'amount': str(payload.get('amount') or payment.monto),
            'notes': str(payload.get('notes') or '').strip(),
        }
        metadata['payment_provider'] = payment.gateway
        payment.metadata_json = metadata
        payment.save(update_fields=['metadata_json', 'fecha_actualizacion'])
        return payment

    @staticmethod
    def approve_transfer_payment(*, payment: Payment, user=None) -> Payment:
        plan = PaymentService._resolve_target_plan(payment)
        if plan is None:
            raise ValueError('No se pudo resolver el plan objetivo del pago.')

        with transaction.atomic():
            payment = Payment.objects.select_related('subscription__colegio').select_for_update().get(pk=payment.pk)
            metadata = dict(payment.metadata_json or {})
            metadata['transfer_review'] = {
                'approved_at': timezone.now().isoformat(),
                'reviewed_by': getattr(user, 'id', None),
            }
            payment.metadata_json = metadata
            payment.save(update_fields=['metadata_json', 'fecha_actualizacion'])

            paid_at = timezone.now()
            payment.mark_approved(paid_at=paid_at)

            subscription = payment.subscription
            if plan.is_unlimited:
                subscription.plan = plan
                subscription.fecha_inicio = paid_at.date()
                subscription.fecha_fin = None
                subscription.fecha_ultimo_pago = paid_at.date()
                subscription.proximo_pago = None
                subscription.status = Subscription.STATUS_ACTIVE
            else:
                dias = plan.duracion_dias or 30
                subscription.plan = plan
                subscription.fecha_inicio = paid_at.date()
                subscription.fecha_fin = paid_at.date() + timedelta(days=dias)
                subscription.fecha_ultimo_pago = paid_at.date()
                subscription.proximo_pago = subscription.fecha_fin
                subscription.status = Subscription.STATUS_ACTIVE

            subscription.save(
                update_fields=['plan', 'fecha_inicio', 'fecha_fin', 'fecha_ultimo_pago', 'proximo_pago', 'status', 'fecha_modificacion']
            )

        return payment

    @staticmethod
    def _apply_approved_payment(*, payment: Payment, payload: Dict[str, Any]) -> None:
        subscription = payment.subscription
        plan = PaymentService._resolve_target_plan(payment) or subscription.plan
        paid_at = PaymentService._parse_paid_at(payload) or timezone.now()

        with transaction.atomic():
            PaymentService._store_webhook_payload(payment=payment, payload=payload, event_type='payment.approved', save=False)
            payment.mark_approved(paid_at=paid_at)

            if plan.is_unlimited:
                subscription.plan = plan
                subscription.fecha_inicio = paid_at.date()
                subscription.fecha_fin = None
                subscription.fecha_ultimo_pago = paid_at.date()
                subscription.proximo_pago = None
                subscription.status = Subscription.STATUS_ACTIVE
                subscription.save(
                    update_fields=['plan', 'fecha_inicio', 'fecha_fin', 'fecha_ultimo_pago', 'proximo_pago', 'status', 'fecha_modificacion']
                )
                return

            dias = plan.duracion_dias or 30
            subscription.plan = plan
            subscription.fecha_inicio = paid_at.date()
            subscription.fecha_fin = paid_at.date() + timedelta(days=dias)
            subscription.fecha_ultimo_pago = paid_at.date()
            subscription.proximo_pago = subscription.fecha_fin
            subscription.status = Subscription.STATUS_ACTIVE
            subscription.save(
                update_fields=['plan', 'fecha_inicio', 'fecha_fin', 'fecha_ultimo_pago', 'proximo_pago', 'status', 'fecha_modificacion']
            )

    @staticmethod
    def _store_webhook_payload(*, payment: Payment, payload: Dict[str, Any], event_type: str, save: bool = True) -> None:
        metadata = dict(payment.metadata_json or {})
        metadata['webhook_payload'] = payload
        metadata['webhook_event_type'] = event_type
        metadata['webhook_payment_reference'] = PaymentService._extract_external_id(payload)
        metadata['webhook_received_at'] = timezone.now().isoformat()
        payment.metadata_json = metadata
        if save:
            payment.save(update_fields=['metadata_json', 'fecha_actualizacion'])

    @staticmethod
    def _is_duplicate_webhook(*, payment: Payment, payload: Dict[str, Any], status: str) -> bool:
        metadata = payment.metadata_json or {}
        last_payload = metadata.get('webhook_payload') or {}
        return (
            payment.status == status
            and isinstance(last_payload, dict)
            and last_payload.get('id') == payload.get('id')
            and last_payload.get('status') == payload.get('status')
        )

    @staticmethod
    def _normalize_status(payload: Dict[str, Any]) -> str:
        raw_status = (
            payload.get('status')
            or payload.get('payment_status')
            or payload.get('collection_status')
            or payload.get('data', {}).get('status')
            or ''
        )
        normalized = str(raw_status).strip().lower()
        if normalized in {'approved', 'paid', 'paid_out'}:
            return Payment.STATUS_APPROVED
        if normalized in {'rejected', 'cancelled', 'canceled', 'failed'}:
            return Payment.STATUS_REJECTED
        return Payment.STATUS_PENDING

    @staticmethod
    def _normalize_webhook_event(payload: Dict[str, Any]) -> str:
        raw_event = (
            payload.get('action')
            or payload.get('topic')
            or payload.get('type')
            or payload.get('event_type')
            or ''
        )
        normalized = str(raw_event).strip().lower()
        if normalized:
            return normalized

        normalized_status = PaymentService._normalize_status(payload)
        if normalized_status == Payment.STATUS_APPROVED:
            return 'payment.approved'
        if normalized_status == Payment.STATUS_REJECTED:
            return 'payment.rejected'
        return 'payment.pending'

    @staticmethod
    def _extract_external_id(payload: Dict[str, Any]) -> Optional[str]:
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        candidate_values = [
            payload.get('external_reference'),
            payload.get('external_id'),
            payload.get('id'),
            data.get('id'),
            data.get('external_reference'),
            data.get('external_id'),
            payload.get('resource'),
            data.get('resource'),
        ]

        for candidate in candidate_values:
            if candidate is None:
                continue
            value = str(candidate).strip()
            if not value:
                continue
            if '/v1/payments/' in value:
                value = value.rsplit('/', 1)[-1]
            return value
        return None

    @staticmethod
    def _parse_paid_at(payload: Dict[str, Any]):
        paid_at = payload.get('date_approved') or payload.get('paid_at') or payload.get('date_created')
        if not paid_at:
            return None
        try:
            return datetime.fromisoformat(str(paid_at).replace('Z', '+00:00'))
        except Exception:
            return None

    @staticmethod
    def _plan_amount(plan: Plan) -> Decimal:
        return Decimal(plan.precio_mensual or 0)

    @staticmethod
    def _build_checkout_url(*, payment: Payment, plan: Plan, colegio: Colegio, provider: Optional[str] = None) -> str:
        provider_code = PaymentService._normalize_provider(provider or payment.gateway)
        if provider_code == 'webpay':
            return PaymentService._webpay_checkout_url(payment=payment, plan=plan, colegio=colegio)
        frontend_url = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
        if frontend_url:
            return (
                f"{frontend_url}/pagos/historial?external_id={payment.external_id}"
                f"&plan={plan.codigo}&colegio={colegio.rbd}&provider={provider_code}"
            )
        return f"/pagos/historial?external_id={payment.external_id}&plan={plan.codigo}&colegio={colegio.rbd}&provider={provider_code}"

    @staticmethod
    def _normalize_provider(provider: Optional[str]) -> str:
        candidate = str(provider or PaymentService.DEFAULT_PROVIDER).strip().lower()
        if candidate in PaymentService.SUPPORTED_PROVIDERS:
            return candidate
        return PaymentService.DEFAULT_PROVIDER

    @staticmethod
    def _provider_instructions(*, payment: Payment, colegio: Colegio, plan: Plan, provider: str) -> Optional[Dict[str, Any]]:
        if provider not in {'bank_transfer', 'bank_transfer_bancoestado'}:
            if provider != 'webpay':
                return None

            return {
                'provider': provider,
                'gateway': 'webpay',
                'checkout_url': PaymentService._webpay_checkout_url(payment=payment, plan=plan, colegio=colegio),
                'instructions': [
                    'Serás redirigido al formulario de pago Webpay de Transbank.',
                    'Completa la tarjeta de débito o crédito y luego vuelve al panel.',
                    'Si el pago no se acredita, el estado quedará pendiente hasta el webhook o conciliación.',
                ],
                'amount': str(payment.monto),
                'currency': payment.moneda,
                'plan_codigo': plan.codigo,
                'colegio_rbd': colegio.rbd,
            }

        account_holder = getattr(settings, 'PAYMENT_BANK_ACCOUNT_HOLDER', 'Aplicacion Colegio SpA')
        bank_name = getattr(settings, 'PAYMENT_BANK_NAME', 'BancoEstado')
        account_type = getattr(settings, 'PAYMENT_BANK_ACCOUNT_TYPE', 'Cuenta Corriente')
        account_number = getattr(settings, 'PAYMENT_BANK_ACCOUNT_NUMBER', '')
        account_rut = getattr(settings, 'PAYMENT_BANK_ACCOUNT_RUT', '')
        email = getattr(settings, 'PAYMENT_BANK_CONTACT_EMAIL', '')

        reference = f"COLEGIO-{colegio.rbd}-PAGO-{payment.external_id[:8]}"

        return {
            'provider': provider,
            'bank_name': bank_name,
            'account_holder': account_holder,
            'account_type': account_type,
            'account_number': account_number,
            'account_rut': account_rut,
            'contact_email': email,
            'reference': reference,
            'instructions': [
                'Realiza la transferencia por el monto exacto del plan.',
                f'Indica la referencia {reference} en el glosa o comentario.',
                'Adjunta el comprobante desde el panel de pagos para validar el abono.',
            ],
            'amount': str(payment.monto),
            'currency': payment.moneda,
            'plan_codigo': plan.codigo,
            'colegio_rbd': colegio.rbd,
        }

    @staticmethod
    def _resolve_target_plan(payment: Payment) -> Optional[Plan]:
        metadata = payment.metadata_json or {}
        plan_codigo = metadata.get('plan_codigo')
        if not plan_codigo:
            return payment.subscription.plan if payment.subscription_id else None
        return Plan.objects.filter(codigo=plan_codigo, activo=True).first()

    @staticmethod
    def _webpay_checkout_url(*, payment: Payment, plan: Plan, colegio: Colegio) -> str:
        configured_url = getattr(settings, 'WEBPAY_CHECKOUT_URL', '').strip()
        if configured_url:
            return configured_url

        frontend_url = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
        checkout_path = (
            f"/pagos/webpay?payment={payment.external_id}"
            f"&plan={plan.codigo}&colegio={colegio.rbd}"
        )
        if frontend_url:
            return f"{frontend_url}{checkout_path}"
        return checkout_path
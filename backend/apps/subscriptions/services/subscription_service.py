"""Servicio de suscripciones con invariantes de negocio."""

from datetime import timedelta
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.institucion.models import Colegio
from backend.apps.subscriptions.models import Plan, Subscription


class SubscriptionService:
    """Operaciones de dominio para suscripciones por colegio."""

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        SubscriptionService.validate(operation, params)
        return SubscriptionService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        if operation == 'upsert_school_subscription':
            if params.get('colegio_rbd') is None:
                raise ValueError('Parámetro requerido: colegio_rbd')
            if not params.get('plan_codigo'):
                raise ValueError('Parámetro requerido: plan_codigo')
            return

        if operation == 'change_status':
            if params.get('colegio_rbd') is None:
                raise ValueError('Parámetro requerido: colegio_rbd')
            if not params.get('new_status'):
                raise ValueError('Parámetro requerido: new_status')
            return

        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        if operation == 'upsert_school_subscription':
            return SubscriptionService._execute_upsert_school_subscription(params)
        if operation == 'change_status':
            return SubscriptionService._execute_change_status(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def upsert_school_subscription(colegio_rbd: int, plan_codigo: str) -> Subscription:
        return SubscriptionService.execute('upsert_school_subscription', {
            'colegio_rbd': colegio_rbd,
            'plan_codigo': plan_codigo,
        })

    @staticmethod
    def _execute_upsert_school_subscription(params: Dict[str, Any]) -> Subscription:
        colegio_rbd = int(params['colegio_rbd'])
        plan_codigo = str(params['plan_codigo']).strip()

        IntegrityService.validate_school_integrity_or_raise(
            school_id=colegio_rbd,
            action='SUBSCRIPTION_UPSERT',
        )

        colegio = Colegio.objects.get(rbd=colegio_rbd)
        plan = Plan.objects.get(codigo=plan_codigo)

        fecha_inicio = timezone.now().date()
        fecha_fin = None
        if not plan.is_unlimited:
            dias = plan.duracion_dias if plan.duracion_dias else 30
            fecha_fin = fecha_inicio + timedelta(days=dias)

        with transaction.atomic():
            subscription, _ = Subscription.objects.update_or_create(
                colegio=colegio,
                defaults={
                    'plan': plan,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'status': Subscription.STATUS_ACTIVE,
                }
            )

        return subscription

    @staticmethod
    def change_status(colegio_rbd: int, new_status: str) -> Subscription:
        return SubscriptionService.execute('change_status', {
            'colegio_rbd': colegio_rbd,
            'new_status': new_status,
        })

    @staticmethod
    def _execute_change_status(params: Dict[str, Any]) -> Subscription:
        colegio_rbd = int(params['colegio_rbd'])
        new_status = str(params['new_status']).strip().lower()

        valid_status = {
            Subscription.STATUS_ACTIVE,
            Subscription.STATUS_EXPIRED,
            Subscription.STATUS_CANCELLED,
            Subscription.STATUS_SUSPENDED,
        }
        if new_status not in valid_status:
            raise ValueError('Estado de suscripción inválido')

        IntegrityService.validate_school_integrity_or_raise(
            school_id=colegio_rbd,
            action='SUBSCRIPTION_CHANGE_STATUS',
        )

        subscription = Subscription.objects.select_related('colegio').get(colegio_id=colegio_rbd)
        subscription.status = new_status
        subscription.save(update_fields=['status'])
        return subscription

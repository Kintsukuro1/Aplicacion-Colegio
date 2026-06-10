"""
Tests para MercadoPago webhook handling.
Valida que el webhook endpoint procesa pagos correctamente.
"""

from decimal import Decimal
import hashlib
import hmac
import json

import pytest
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.test import override_settings

from backend.apps.accounts.models import User, Role
from backend.apps.institucion.models import Colegio
from backend.apps.subscriptions.models import Payment, Plan, Subscription


@pytest.mark.django_db
class TestPaymentWebhook(APITestCase):
    """Valida que el webhook de MercadoPago procesa pagos correctamente."""

    def setUp(self):
        # Ensure admin role and colegio exist for tests
        self.rol_admin, _ = Role.objects.get_or_create(nombre="Admin")
        self.colegio, _ = Colegio.objects.get_or_create(
            rbd=99001,
            defaults={
                "rut_establecimiento": "99001-K",
                "nombre": "Colegio Test Webhook",
            },
        )

        self.plan = Plan.objects.create(
            nombre='Test Plan',
            codigo='test_plan',
            precio_mensual=Decimal('30000'),
            duracion_dias=30,
            activo=True,
        )

        self.subscription = Subscription.objects.create(
            colegio=self.colegio,
            plan=self.plan,
        )

        self.user = User.objects.create_user(
            email='admin@test.cl',
            password='test123',
            rbd_colegio=self.colegio.rbd,
            is_active=True,
        )

    def _create_payment(self, external_id):
        return Payment.objects.create(
            subscription=self.subscription,
            external_id=external_id,
            monto=Decimal('30000'),
            moneda='CLP',
            status=Payment.STATUS_PENDING,
            gateway='mercadopago',
            metadata_json={'plan_codigo': self.plan.codigo},
        )

    def _signed_payload(self, payload, secret):
        raw_body = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        signature = hmac.new(secret.encode('utf-8'), raw_body.encode('utf-8'), hashlib.sha256).hexdigest()
        return raw_body, signature

    def test_webhook_marks_payment_approved(self):
        payment = self._create_payment('test-payment-001')
        payload = {
            'id': 'test-payment-001',
            'status': 'approved',
            'date_approved': '2025-01-15T10:30:00Z',
            'external_reference': 'test-payment-001',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['payment_id'] == payment.id
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_APPROVED
        assert payment.fecha_pago is not None

    def test_webhook_marks_payment_rejected(self):
        payment = self._create_payment('test-payment-002')
        payload = {
            'id': 'test-payment-002',
            'status': 'rejected',
            'external_reference': 'test-payment-002',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_REJECTED

    def test_webhook_updates_subscription_on_approved(self):
        self._create_payment('test-payment-003')
        payload = {
            'id': 'test-payment-003',
            'status': 'approved',
            'date_approved': '2025-01-15T10:30:00Z',
            'external_reference': 'test-payment-003',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        self.subscription.refresh_from_db()
        assert self.subscription.status == Subscription.STATUS_ACTIVE
        assert self.subscription.plan.codigo == self.plan.codigo
        assert self.subscription.fecha_fin is not None

    def test_webhook_with_invalid_external_id(self):
        payload = {
            'id': 'nonexistent-payment',
            'status': 'approved',
            'date_approved': '2025-01-15T10:30:00Z',
            'external_reference': 'nonexistent-payment',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_webhook_with_missing_external_id(self):
        payload = {
            'status': 'approved',
            'date_approved': '2025-01-15T10:30:00Z',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_webhook_normalizes_status_formats(self):
        payment = self._create_payment('test-payment-004')
        payload = {
            'id': 'test-payment-004',
            'status': 'paid',
            'date_approved': '2025-01-15T10:30:00Z',
            'external_reference': 'test-payment-004',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_APPROVED

    def test_webhook_stores_full_payload(self):
        payment = self._create_payment('test-payment-005')
        payload = {
            'id': 'test-payment-005',
            'status': 'approved',
            'date_approved': '2025-01-15T10:30:00Z',
            'external_reference': 'test-payment-005',
            'extra_field': 'extra_value',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert 'webhook_payload' in payment.metadata_json
        assert payment.metadata_json['webhook_payload']['extra_field'] == 'extra_value'

    @override_settings(PAYMENT_WEBHOOK_TOKEN='expected-token')
    def test_webhook_rejects_invalid_token(self):
        payment = self._create_payment('test-payment-006')
        payload = {
            'id': 'test-payment-006',
            'status': 'approved',
            'external_reference': 'test-payment-006',
        }

        response = APIClient().post('/api/v1/payments/webhook/', payload, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_PENDING

    @override_settings(PAYMENT_WEBHOOK_TOKEN='expected-token')
    def test_webhook_accepts_valid_token(self):
        payment = self._create_payment('test-payment-007')
        payload = {
            'id': 'test-payment-007',
            'status': 'approved',
            'external_reference': 'test-payment-007',
        }

        client = APIClient()
        response = client.post(
            '/api/v1/payments/webhook/',
            payload,
            format='json',
            HTTP_X_WEBHOOK_TOKEN='expected-token',
        )

        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_APPROVED

    @override_settings(PAYMENT_WEBHOOK_SECRET='webhook-secret')
    def test_webhook_rejects_invalid_signature(self):
        payment = self._create_payment('test-payment-008')
        payload = {
            'id': 'test-payment-008',
            'status': 'approved',
            'external_reference': 'test-payment-008',
        }
        raw_body, _ = self._signed_payload(payload, 'webhook-secret')

        response = APIClient().generic(
            'POST',
            '/api/v1/payments/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE='invalid-signature',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_PENDING

    @override_settings(PAYMENT_WEBHOOK_SECRET='webhook-secret')
    def test_webhook_accepts_valid_signature(self):
        payment = self._create_payment('test-payment-009')
        payload = {
            'id': 'test-payment-009',
            'status': 'approved',
            'external_reference': 'test-payment-009',
        }
        raw_body, signature = self._signed_payload(payload, 'webhook-secret')

        response = APIClient().generic(
            'POST',
            '/api/v1/payments/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=f'sha256={signature}',
        )

        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_APPROVED

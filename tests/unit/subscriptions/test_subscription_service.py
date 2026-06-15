from datetime import date
from unittest.mock import Mock, patch

import pytest

from backend.apps.subscriptions.services.subscription_service import SubscriptionService


def test_validate_guards():
    with pytest.raises(ValueError):
        SubscriptionService.validate('upsert_school_subscription', {'colegio_rbd': 1})
    with pytest.raises(ValueError):
        SubscriptionService.validate('change_status', {'colegio_rbd': 1})
    with pytest.raises(ValueError):
        SubscriptionService.validate('unknown', {})


@patch('backend.apps.subscriptions.services.subscription_service.IntegrityService.validate_school_integrity_or_raise')
@patch('backend.apps.subscriptions.services.subscription_service.transaction.atomic')
@patch('backend.apps.subscriptions.services.subscription_service.Subscription')
@patch('backend.apps.subscriptions.services.subscription_service.Plan')
@patch('backend.apps.subscriptions.services.subscription_service.Colegio')
@patch('backend.apps.subscriptions.services.subscription_service.timezone')
def test_upsert_school_subscription_unlimited(mock_tz, mock_colegio, mock_plan, mock_subscription, mock_atomic, _mock_integrity):
    mock_tz.now.return_value.date.return_value = date(2026, 2, 27)
    mock_colegio.objects.get.return_value = Mock()
    plan = Mock(is_unlimited=True, duracion_dias=None)
    mock_plan.objects.get.return_value = plan
    created = Mock()
    mock_subscription.objects.update_or_create.return_value = (created, True)

    result = SubscriptionService._execute_upsert_school_subscription({'colegio_rbd': 10, 'plan_codigo': 'free'})

    assert result is created
    defaults = mock_subscription.objects.update_or_create.call_args.kwargs['defaults']
    assert defaults['fecha_fin'] is None
    assert defaults['status'] == mock_subscription.STATUS_ACTIVE
    mock_atomic.assert_called_once()


@patch('backend.apps.subscriptions.services.subscription_service.IntegrityService.validate_school_integrity_or_raise')
@patch('backend.apps.subscriptions.services.subscription_service.transaction.atomic')
@patch('backend.apps.subscriptions.services.subscription_service.Subscription')
@patch('backend.apps.subscriptions.services.subscription_service.Plan')
@patch('backend.apps.subscriptions.services.subscription_service.Colegio')
@patch('backend.apps.subscriptions.services.subscription_service.timezone')
def test_upsert_school_subscription_limited(mock_tz, mock_colegio, mock_plan, mock_subscription, _mock_atomic, _mock_integrity):
    today = date(2026, 2, 27)
    mock_tz.now.return_value.date.return_value = today
    mock_colegio.objects.get.return_value = Mock()
    mock_plan.objects.get.return_value = Mock(is_unlimited=False, duracion_dias=10)
    mock_subscription.objects.update_or_create.return_value = (Mock(), False)

    SubscriptionService._execute_upsert_school_subscription({'colegio_rbd': 10, 'plan_codigo': 'basic'})
    defaults = mock_subscription.objects.update_or_create.call_args.kwargs['defaults']
    assert defaults['fecha_fin'] == date(2026, 3, 9)


@patch('backend.apps.subscriptions.services.subscription_service.IntegrityService.validate_school_integrity_or_raise')
@patch('backend.apps.subscriptions.services.subscription_service.Subscription')
def test_change_status_paths(mock_subscription, _mock_integrity):
    mock_subscription.STATUS_ACTIVE = 'active'
    mock_subscription.STATUS_EXPIRED = 'expired'
    mock_subscription.STATUS_CANCELLED = 'cancelled'
    mock_subscription.STATUS_SUSPENDED = 'suspended'

    with pytest.raises(ValueError):
        SubscriptionService._execute_change_status({'colegio_rbd': 1, 'new_status': 'weird'})

    sub = Mock()
    mock_subscription.objects.select_related.return_value.get.return_value = sub

    result = SubscriptionService._execute_change_status({'colegio_rbd': 1, 'new_status': 'SUSPENDED'})
    assert result is sub
    assert sub.status == 'suspended'
    sub.save.assert_called_once_with(update_fields=['status'])

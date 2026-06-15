from celery import shared_task
from backend.apps.institucion.models import Colegio
from backend.apps.accounts.models import User
from backend.apps.api.services.onboarding_service import OnboardingService
from backend.apps.subscriptions.services.payment_service import PaymentService

@shared_task
def generate_demo_data_task(colegio_id, admin_user_id):
    """
    Celery task to generate demo data asynchronously.
    We pass IDs instead of ORM objects to avoid serialization issues.
    """
    try:
        colegio = Colegio.objects.get(pk=colegio_id)
        admin_user = User.objects.get(pk=admin_user_id)
        OnboardingService.generate_demo_data(colegio=colegio, admin_user=admin_user)
        return f"Demo data generated successfully for colegio {colegio.rbd}"
    except Exception as e:
        return f"Error generating demo data: {str(e)}"

@shared_task
def process_payment_webhook_task(payload: dict):
    """
    Celery task to process payment webhooks asynchronously.
    """
    try:
        PaymentService.process_webhook(payload)
        return "Webhook processed successfully."
    except Exception as e:
        return f"Error processing webhook: {str(e)}"

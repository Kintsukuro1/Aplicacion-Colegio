import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import User
from backend.apps.institucion.models import Colegio, ConfiguracionAcademica, CicloAcademico
from backend.apps.subscriptions.models import Subscription


pytestmark = pytest.mark.django_db


def test_onboarding_register_creates_school_admin_configuration_cycle_and_trial_subscription():
    client = APIClient()

    check_before = client.get('/api/v1/onboarding/check-slug/', {'slug': 'colegio-san-jose'})
    assert check_before.status_code == 200
    assert check_before.json()['available'] is True

    payload = {
        'rbd': 91001,
        'school_name': 'Colegio San Jose',
        'school_rut': '91001000-1',
        'school_email': 'contacto@sanjose.cl',
        'school_phone': '+56 2 2345 6789',
        'school_address': 'Av. Principal 123',
        'slug': 'colegio-san-jose',
        'color_primario': '#0f766e',
        'admin_name': 'Maria',
        'admin_last_name': 'Perez',
        'admin_email': 'admin@sanjose.cl',
        'admin_password': 'Admin#123456',
        'school_year': 2026,
        'regimen_evaluacion': 'SEMESTRAL',
        'nota_aprobacion': 4.0,
        'generate_demo_data': False,
    }

    response = client.post('/api/v1/onboarding/register/', payload, format='json')
    assert response.status_code == 201

    data = response.json()
    assert data['colegio_rbd'] == 91001
    assert data['colegio_slug'] == 'colegio-san-jose'
    assert data['admin_email'] == 'admin@sanjose.cl'
    assert data['subscription_status'] == 'active'

    colegio = Colegio.objects.get(rbd=91001)
    assert colegio.slug == 'colegio-san-jose'
    assert colegio.color_primario == '#0f766e'

    admin = User.objects.get(email='admin@sanjose.cl')
    assert admin.rbd_colegio == 91001
    assert admin.is_staff is True

    config = ConfiguracionAcademica.objects.get(colegio=colegio)
    assert config.anio_escolar_activo == 2026
    assert config.regimen_evaluacion == 'SEMESTRAL'
    assert float(config.nota_aprobacion) == 4.0

    ciclo = CicloAcademico.objects.get(colegio=colegio)
    assert ciclo.estado == 'ACTIVO'
    assert ciclo.fecha_inicio.year == 2026

    subscription = Subscription.objects.get(colegio=colegio)
    assert subscription.status == Subscription.STATUS_ACTIVE
    assert subscription.plan.codigo == 'trial'

    check_after = client.get('/api/v1/onboarding/check-slug/', {'slug': 'colegio-san-jose'})
    assert check_after.status_code == 200
    assert check_after.json()['available'] is False

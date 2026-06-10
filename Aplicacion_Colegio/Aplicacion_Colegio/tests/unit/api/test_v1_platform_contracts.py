import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User


pytestmark = pytest.mark.django_db


def _mk_user(email, role_name, school_id, rut):
    role, _ = Role.objects.get_or_create(nombre=role_name)
    return User.objects.create_user(
        email=email,
        password='Test#123456',
        nombre='Nombre',
        apellido_paterno='Apellido',
        rut=rut,
        role=role,
        rbd_colegio=school_id,
        is_active=True,
    )


def _build_png_upload(name='image.png', size=(2200, 1200), color=(120, 80, 60)):
    stream = io.BytesIO()
    image = Image.new('RGB', size, color)
    image.save(stream, format='PNG')
    stream.seek(0)
    return SimpleUploadedFile(name, stream.getvalue(), content_type='image/png')


def test_accept_header_version_1_0_is_supported():
    client = APIClient()
    response = client.get('/api/v1/health/', HTTP_ACCEPT='application/json; version=1.0')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_accept_header_unknown_version_returns_not_acceptable():
    client = APIClient()
    response = client.get('/api/v1/health/', HTTP_ACCEPT='application/json; version=2.0')

    assert response.status_code == 406


def test_query_param_version_1_0_is_supported():
    client = APIClient()
    response = client.get('/api/v1/health/?version=1.0')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_query_param_unknown_version_returns_not_acceptable():
    client = APIClient()
    response = client.get('/api/v1/health/?version=2.0')

    assert response.status_code == 406


def test_query_param_version_takes_priority_over_accept_header_version():
    client = APIClient()
    response = client.get('/api/v1/health/?version=1.0', HTTP_ACCEPT='application/json; version=2.0')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


@override_settings(
    API_DEPRECATION_MAP={
        '1.0': {
            'enabled': True,
            'sunset': 'Tue, 31 Dec 2026 23:59:59 GMT',
            'doc_url': 'https://example.local/docs/api/v1-deprecation',
            'message': 'API v1 sera retirada, migra a v2.',
        }
    }
)
def test_v1_deprecation_headers_are_added_when_enabled():
    client = APIClient()
    response = client.get('/api/v1/health/')

    assert response.status_code == 200
    assert response['Deprecation'] == 'true'
    assert response['Sunset'] == 'Tue, 31 Dec 2026 23:59:59 GMT'
    assert 'deprecation' in response['Link']
    assert response['X-API-Deprecation-Message'] == 'API v1 sera retirada, migra a v2.'


@override_settings(MEDIA_ROOT='c:/Proyectos/Aplicacion_Colegio/Aplicacion_Colegio/media_test_tmp')
def test_upload_image_endpoint_validates_and_compresses_for_authenticated_user():
    user = _mk_user('upload-user@test.cl', 'Profesor', 1001, '90909090-1')

    client = APIClient()
    client.force_authenticate(user=user)

    upload = _build_png_upload()
    response = client.post('/api/v1/uploads/image/', {'file': upload}, format='multipart')

    assert response.status_code == 201
    payload = response.json()
    assert payload['path'].startswith('uploads/api/')
    assert payload['content_type'] in {'image/jpeg', 'image/png'}
    assert payload['width'] <= 1920
    assert payload['height'] <= 1920
    assert payload['size'] > 0


def test_upload_image_endpoint_rejects_unauthenticated_requests():
    client = APIClient()
    upload = _build_png_upload()

    response = client.post('/api/v1/uploads/image/', {'file': upload}, format='multipart')

    assert response.status_code == 401


def test_service_worker_is_served_from_root_with_allowed_scope_header():
    client = APIClient()

    response = client.get('/service-worker.js?v=20260306')

    assert response.status_code == 200
    assert response['Service-Worker-Allowed'] == '/'
    assert response['Cache-Control'] == 'no-cache'
    assert response['Content-Type'].startswith('application/javascript')

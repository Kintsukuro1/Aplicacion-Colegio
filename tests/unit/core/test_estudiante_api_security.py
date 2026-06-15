from unittest.mock import Mock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, override_settings

from backend.apps.accounts.models import Role, User
from backend.apps.core.views.estudiante.api import entregar_tarea


pytestmark = pytest.mark.django_db


def _create_user(email: str, role_name: str, rbd: int, rut: str):
    role, _ = Role.objects.get_or_create(nombre=role_name)
    return User.objects.create_user(
        email=email,
        password='Temp#123456',
        nombre='Nombre',
        apellido_paterno='Apellido',
        rut=rut,
        role=role,
        rbd_colegio=rbd,
        is_active=True,
    )


def _capability_map(user, capability, school_id=None):
    if capability == 'CLASS_VIEW':
        return True
    if capability in {'CLASS_EDIT', 'CLASS_TAKE_ATTENDANCE'}:
        return False
    return False


@override_settings(
    ALLOWED_UPLOAD_EXTENSIONS={'.pdf'},
    ALLOWED_MIME_TYPES={'application/pdf'},
    MAX_UPLOAD_SIZE=1024,
)
def test_entregar_tarea_rejects_invalid_extension_before_service_calls():
    user = _create_user('estudiante-ext@test.cl', 'Estudiante', 123, '11111111-1')
    factory = RequestFactory()
    archivo = SimpleUploadedFile('tarea.exe', b'x', content_type='application/octet-stream')
    request = factory.post('/api/v1/estudiante/tareas/entregar/', data={'tarea_id': '10', 'archivo': archivo})
    request.user = user

    with patch('backend.apps.core.views.estudiante.api.PolicyService.has_capability', side_effect=_capability_map), patch(
        'backend.apps.core.views.estudiante.api.EstudianteApiService.get_tarea_activa_or_none'
    ) as mock_get_tarea:
        response = entregar_tarea(request)

    assert response.status_code == 400
    assert b'Tipo de archivo no permitido' in response.content
    mock_get_tarea.assert_not_called()


@override_settings(
    ALLOWED_UPLOAD_EXTENSIONS={'.pdf'},
    ALLOWED_MIME_TYPES={'application/pdf'},
    MAX_UPLOAD_SIZE=1024,
)
def test_entregar_tarea_rejects_file_over_max_size():
    user = _create_user('estudiante-size@test.cl', 'Estudiante', 123, '22222222-2')
    factory = RequestFactory()
    archivo = SimpleUploadedFile('tarea.pdf', b'x' * 2048, content_type='application/pdf')
    request = factory.post('/api/v1/estudiante/tareas/entregar/', data={'tarea_id': '10', 'archivo': archivo})
    request.user = user

    with patch('backend.apps.core.views.estudiante.api.PolicyService.has_capability', side_effect=_capability_map):
        response = entregar_tarea(request)

    assert response.status_code == 400
    assert b'tamano maximo permitido' in response.content


@override_settings(
    ALLOWED_UPLOAD_EXTENSIONS={'.pdf'},
    ALLOWED_MIME_TYPES={'application/pdf'},
    MAX_UPLOAD_SIZE=1024 * 1024,
)
def test_entregar_tarea_accepts_valid_file_and_creates_submission():
    user = _create_user('estudiante-ok@test.cl', 'Estudiante', 123, '33333333-3')
    factory = RequestFactory()
    archivo = SimpleUploadedFile('tarea.pdf', b'documento', content_type='application/pdf')
    request = factory.post('/api/v1/estudiante/tareas/entregar/', data={'tarea_id': '10', 'archivo': archivo})
    request.user = user

    fake_tarea = Mock()
    with patch('backend.apps.core.views.estudiante.api.PolicyService.has_capability', side_effect=_capability_map), patch(
        'backend.apps.core.views.estudiante.api.EstudianteApiService.get_tarea_activa_or_none',
        return_value=fake_tarea,
    ), patch(
        'backend.apps.core.views.estudiante.api.EstudianteApiService.get_entrega_existente',
        return_value=None,
    ), patch('backend.apps.core.views.estudiante.api.EstudianteApiService.crear_entrega') as mock_crear:
        response = entregar_tarea(request)

    assert response.status_code == 200
    assert b'Tarea entregada exitosamente' in response.content
    mock_crear.assert_called_once()

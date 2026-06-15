import pytest
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ('method', 'url'),
    [
        ('get', '/api/v1/coordinador/planificaciones/'),
        ('post', '/api/v1/soporte/tickets/crear/'),
        ('post', '/api/v1/soporte/tickets/1/actualizar/'),
        ('post', '/api/v1/soporte/usuarios/1/reset-password/'),
        ('get', '/api/v1/asesor-financiero/pagos/'),
        ('post', '/api/v1/estudiante/tareas/entregar/'),
        ('get', '/api/v1/inspector/estudiantes/'),
        ('get', '/api/v1/inspector/justificativos/'),
        ('post', '/api/v1/inspector/anotaciones/crear/'),
        ('post', '/api/v1/inspector/asistencia/registrar_atraso/'),
        ('post', '/api/v1/inspector/atrasos/registrar/'),
        ('post', '/api/v1/inspector/justificativos/1/revisar/'),
        ('get', '/api/v1/psicologo/estudiantes/'),
        ('post', '/api/v1/psicologo/entrevistas/crear/'),
        ('post', '/api/v1/psicologo/derivaciones/crear/'),
        ('post', '/api/v1/psicologo/derivaciones/1/actualizar/'),
        ('get', '/api/v1/bibliotecario/recursos/'),
        ('get', '/api/v1/bibliotecario/usuarios/'),
        ('get', '/api/v1/bibliotecario/prestamos/'),
        ('post', '/api/v1/bibliotecario/recursos/crear/'),
        ('post', '/api/v1/bibliotecario/prestamos/crear/'),
        ('post', '/api/v1/bibliotecario/prestamos/1/devolucion/'),
    ],
)
def test_legacy_role_aliases_are_registered_under_v1_and_require_auth(method, url):
    client = APIClient()
    response = getattr(client, method)(url, {}, format='json')

    assert response.status_code == 401

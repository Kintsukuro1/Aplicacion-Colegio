import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Role, User
from backend.apps.notificaciones.models import DispositivoMovil, Notificacion


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


def test_notifications_list_is_scoped_to_authenticated_user():
    user = _mk_user('notif-user@test.cl', 'Profesor', 1201, '11111111-2')
    other = _mk_user('notif-other@test.cl', 'Profesor', 1201, '22222222-2')

    Notificacion.objects.create(destinatario=user, tipo='sistema', titulo='A', mensaje='A')
    Notificacion.objects.create(destinatario=other, tipo='sistema', titulo='B', mensaje='B')

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get('/api/v1/notificaciones/')
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]['titulo'] == 'A'


def test_notifications_mark_read_updates_state():
    user = _mk_user('notif-read@test.cl', 'Profesor', 1202, '33333333-2')
    notification = Notificacion.objects.create(
        destinatario=user,
        tipo='sistema',
        titulo='Pendiente',
        mensaje='M',
        leido=False,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f'/api/v1/notificaciones/{notification.id}/marcar-leida/', {}, format='json')
    assert response.status_code == 200

    notification.refresh_from_db()
    assert notification.leido is True
    assert notification.fecha_lectura is not None


def test_notifications_summary_returns_unread_count():
    user = _mk_user('notif-summary@test.cl', 'Profesor', 1204, '55555555-2')
    Notificacion.objects.create(destinatario=user, tipo='sistema', titulo='U1', mensaje='A', leido=False)
    Notificacion.objects.create(destinatario=user, tipo='sistema', titulo='U2', mensaje='B', leido=True)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get('/api/v1/notificaciones/resumen/')
    assert response.status_code == 200
    payload = response.json()
    assert payload['unread_count'] == 1
    assert payload['latest_notification_at'] is not None


def test_notifications_mark_all_read_marks_only_current_user_rows():
    user = _mk_user('notif-mark-all@test.cl', 'Profesor', 1205, '66666666-2')
    other = _mk_user('notif-mark-all-other@test.cl', 'Profesor', 1205, '77777777-2')

    own_unread = Notificacion.objects.create(destinatario=user, tipo='sistema', titulo='Own', mensaje='A', leido=False)
    other_unread = Notificacion.objects.create(destinatario=other, tipo='sistema', titulo='Other', mensaje='B', leido=False)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post('/api/v1/notificaciones/marcar-todas-leidas/', {}, format='json')
    assert response.status_code == 200
    assert response.json()['updated'] == 1

    own_unread.refresh_from_db()
    other_unread.refresh_from_db()
    assert own_unread.leido is True
    assert other_unread.leido is False


def test_register_and_deactivate_device():
    user = _mk_user('notif-device@test.cl', 'Profesor', 1203, '44444444-2')

    client = APIClient()
    client.force_authenticate(user=user)

    register_response = client.post(
        '/api/v1/notificaciones/dispositivos/registrar/',
        {
            'token_fcm': 'token-demo-123',
            'plataforma': 'android',
            'nombre_dispositivo': 'Pixel',
        },
        format='json',
    )
    assert register_response.status_code in (200, 201)

    device_id = register_response.json()['id']
    assert DispositivoMovil.objects.filter(id=device_id, usuario=user, activo=True).exists()

    deactivate_response = client.post(
        f'/api/v1/notificaciones/dispositivos/{device_id}/desactivar/',
        {},
        format='json',
    )
    assert deactivate_response.status_code == 200

    assert DispositivoMovil.objects.filter(id=device_id, usuario=user, activo=False).exists()


def test_notifications_sse_endpoint_requires_auth():
    client = APIClient()
    response = client.get('/api/v1/notificaciones/stream/')
    assert response.status_code == 401

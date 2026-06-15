from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.management import call_command
from django.utils import timezone

from backend.apps.accounts.models import Role, User
from backend.apps.academico.models import Calificacion, EntregaTarea, Evaluacion, Tarea
from backend.apps.cursos.models import Asignatura, Clase, ClaseEstudiante, Curso
from backend.apps.institucion.models import Colegio, NivelEducativo
from backend.apps.mensajeria.models import Conversacion, Mensaje
from backend.apps.notificaciones.consumers import NotificacionesConsumer
from backend.apps.notificaciones.models import Notificacion


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


@pytest.fixture(autouse=True)
def _patch_dispatch(request):
    if request.node.get_closest_marker('websocket_realtime'):
        yield
        return
    with patch('backend.apps.notificaciones.signals.NotificationDispatchService.dispatch_channels'):
        yield


def _mk_school_graph(suffix='1'):
    school = Colegio.objects.create(
        rbd=1400 + int(suffix),
        rut_establecimiento=f'1400{suffix}-K',
        nombre=f'Colegio Test {suffix}',
    )
    nivel = NivelEducativo.objects.create(nombre=f'Nivel {suffix}')
    curso = Curso.objects.create(colegio=school, nombre=f'1A-{suffix}', nivel=nivel)
    asignatura = Asignatura.objects.create(colegio=school, nombre=f'Matematica {suffix}')
    profesor = _mk_user(f'profesor{suffix}@test.cl', 'Profesor', school.rbd, f'4000000{suffix}-1')
    estudiante = _mk_user(f'estudiante{suffix}@test.cl', 'Estudiante', school.rbd, f'5000000{suffix}-2')
    clase = Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=profesor,
    )
    ClaseEstudiante.objects.create(clase=clase, estudiante=estudiante, activo=True)
    return school, clase, profesor, estudiante


@patch('backend.apps.notificaciones.signals.NotificationDispatchService.dispatch_channels')
def test_notificacion_post_save_dispatches_channels(mock_dispatch):
    user = _mk_user('notif-signal@test.cl', 'Profesor', 1301, '55555555-2')

    notification = Notificacion.objects.create(
        destinatario=user,
        tipo='sistema',
        titulo='Signal test',
        mensaje='Dispatch',
    )

    mock_dispatch.assert_called_once_with(notification)


def test_tarea_signal_creates_student_and_teacher_notifications():
    school, clase, profesor, estudiante = _mk_school_graph('2')

    Tarea.objects.create(
        colegio=school,
        clase=clase,
        titulo='Tarea Signal',
        instrucciones='Resolver ejercicios',
        fecha_entrega=timezone.now() + timezone.timedelta(days=1),
        creada_por=profesor,
        activa=True,
    )

    assert Notificacion.objects.filter(destinatario=estudiante, tipo='tarea_nueva').exists()
    assert Notificacion.objects.filter(destinatario=profesor, tipo='tarea_nueva').exists()


def test_evaluacion_calificacion_and_entrega_signals_create_notifications():
    school, clase, profesor, estudiante = _mk_school_graph('3')

    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Prueba Signal',
        fecha_evaluacion=timezone.localdate(),
        activa=True,
    )

    assert Notificacion.objects.filter(destinatario=estudiante, tipo='evaluacion').exists()
    assert Notificacion.objects.filter(destinatario=profesor, tipo='evaluacion').exists()

    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=estudiante,
        nota=6.0,
        registrado_por=profesor,
    )
    assert Notificacion.objects.filter(destinatario=estudiante, tipo='calificacion').exists()

    tarea = Tarea.objects.create(
        colegio=school,
        clase=clase,
        titulo='Tarea Entrega Signal',
        instrucciones='Subir trabajo',
        fecha_entrega=timezone.now() + timezone.timedelta(days=1),
        creada_por=profesor,
        activa=True,
    )
    EntregaTarea.objects.create(
        tarea=tarea,
        estudiante=estudiante,
        comentario_estudiante='Adjunto tarea',
    )
    assert Notificacion.objects.filter(destinatario=profesor, tipo='tarea_entregada').exists()


def test_mensaje_signal_notifies_receiver_only():
    _school, clase, profesor, estudiante = _mk_school_graph('4')
    conversacion = Conversacion.objects.create(
        clase=clase,
        participante1=profesor,
        participante2=estudiante,
    )

    Mensaje.objects.create(
        conversacion=conversacion,
        emisor=profesor,
        receptor=estudiante,
        contenido='Mensaje para estudiante',
    )
    Mensaje.objects.create(
        conversacion=conversacion,
        emisor=estudiante,
        receptor=profesor,
        contenido='Mensaje para profesor',
    )

    assert Notificacion.objects.filter(destinatario=estudiante, tipo='mensaje_nuevo').count() == 1
    assert Notificacion.objects.filter(destinatario=profesor, tipo='mensaje_nuevo').count() == 1


def test_daily_command_creates_and_deduplicates_teacher_alerts():
    school, clase, profesor, _estudiante = _mk_school_graph('5')

    Tarea.objects.create(
        colegio=school,
        clase=clase,
        titulo='Tarea de hoy',
        instrucciones='Resolver guia',
        fecha_entrega=timezone.make_aware(
            timezone.datetime.combine(timezone.localdate(), timezone.datetime.min.time())
        ),
        creada_por=profesor,
        activa=True,
    )
    Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Prueba de hoy',
        fecha_evaluacion=timezone.localdate(),
        activa=True,
    )

    call_command('notify_profesores_eventos_hoy', verbosity=0)
    primera = Notificacion.objects.filter(destinatario=profesor, tipo='alerta').count()

    call_command('notify_profesores_eventos_hoy', verbosity=0)
    segunda = Notificacion.objects.filter(destinatario=profesor, tipo='alerta').count()

    assert primera == 2
    assert segunda == 2


@pytest.mark.websocket_realtime
def test_websocket_consumer_receives_notification_created_event():
    user = _mk_user('ws-consumer@test.cl', 'Estudiante', 1302, '55555556-3')

    async def _run():
        communicator = WebsocketCommunicator(NotificacionesConsumer.as_asgi(), '/ws/notificaciones/')
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected is True

        await sync_to_async(Notificacion.objects.create)(
            destinatario=user,
            tipo='sistema',
            titulo='WS Test',
            mensaje='Notificacion realtime',
        )

        payload = await communicator.receive_json_from(timeout=5)
        assert payload['event'] == 'notification.created'
        assert payload['notification']['tipo'] == 'sistema'
        assert payload['notification']['titulo'] == 'WS Test'

        await communicator.disconnect()

    async_to_sync(_run)()

import pytest
from rest_framework.test import APIClient

from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion, RegistroClase, Tarea, MaterialClase
from backend.apps.accounts.models import Apoderado, PerfilEstudiante, PerfilProfesor, RelacionApoderadoEstudiante, User
from backend.apps.cursos.models import Asignatura, Clase, Curso, BloqueHorario
from backend.apps.institucion.models import Colegio
from backend.apps.matriculas.models import Matricula


pytestmark = pytest.mark.django_db


def _register_school(client: APIClient) -> Colegio:
    payload = {
        'rbd': 92001,
        'school_name': 'Colegio Demo Automatico',
        'school_rut': '92001000-1',
        'school_email': 'contacto@demoautomatico.cl',
        'slug': 'colegio-demo-automatico',
        'admin_name': 'Ana',
        'admin_last_name': 'Lopez',
        'admin_email': 'admin@demoautomatico.cl',
        'admin_password': 'Admin#123456',
        'school_year': 2026,
        'regimen_evaluacion': 'SEMESTRAL',
        'generate_demo_data': False,
    }

    response = client.post('/api/v1/onboarding/register/', payload, format='json')
    assert response.status_code == 201
    return Colegio.objects.get(rbd=92001)


def test_onboarding_generate_demo_creates_real_data_and_is_idempotent():
    client = APIClient()
    colegio = _register_school(client)
    admin = User.objects.get(email='admin@demoautomatico.cl')
    client.force_authenticate(user=admin)

    first_response = client.post('/api/v1/onboarding/generate-demo/', format='json')
    assert first_response.status_code == 200
    assert first_response.json()['detail'] == 'Datos demo generados.'

    expected_counts = {
        'cursos': Curso.objects.filter(colegio=colegio).count(),
        'asignaturas': Asignatura.objects.filter(colegio=colegio).count(),
        'clases': Clase.objects.filter(colegio=colegio).count(),
        'profesores': PerfilProfesor.objects.filter(user__rbd_colegio=colegio.rbd).count(),
        'apoderados': Apoderado.objects.filter(user__rbd_colegio=colegio.rbd).count(),
        'estudiantes': PerfilEstudiante.objects.filter(user__rbd_colegio=colegio.rbd).count(),
        'relaciones_apoderado_estudiante': RelacionApoderadoEstudiante.objects.filter(apoderado__user__rbd_colegio=colegio.rbd).count(),
        'matriculas': Matricula.objects.filter(colegio=colegio).count(),
        'evaluaciones': Evaluacion.objects.filter(colegio=colegio).count(),
        'calificaciones': Calificacion.objects.filter(colegio=colegio).count(),
        'registros': RegistroClase.objects.filter(colegio=colegio).count(),
        'asistencias': Asistencia.objects.filter(colegio=colegio).count(),
        'tareas': Tarea.objects.filter(colegio=colegio).count(),
        'materiales': MaterialClase.objects.filter(colegio=colegio).count(),
        'bloques': BloqueHorario.objects.filter(colegio=colegio).count(),
    }

    assert expected_counts == {
        'cursos': 2,
        'asignaturas': 2,
        'clases': 4,
        'profesores': 2,
        'apoderados': 3,
        'estudiantes': 6,
        'relaciones_apoderado_estudiante': 6,
        'matriculas': 6,
        'evaluaciones': 4,
        'calificaciones': 24,
        'registros': 4,
        'asistencias': 24,
        'tareas': 4,
        'materiales': 4,
        'bloques': 4,
    }

    first_student_profile = PerfilEstudiante.objects.get(user__email='alumna.valentina.colegio-demo-automatico@demo.local')
    assert first_student_profile.apoderado_nombre == 'Paula Perez Mora'
    assert first_student_profile.apoderado_email == 'apoderado.perez.colegio-demo-automatico@demo.local'
    assert first_student_profile.apoderado_telefono == '+56 9 1111 1111'

    second_response = client.post('/api/v1/onboarding/generate-demo/', format='json')
    assert second_response.status_code == 200

    repeated_counts = {
        'cursos': Curso.objects.filter(colegio=colegio).count(),
        'asignaturas': Asignatura.objects.filter(colegio=colegio).count(),
        'clases': Clase.objects.filter(colegio=colegio).count(),
        'profesores': PerfilProfesor.objects.filter(user__rbd_colegio=colegio.rbd).count(),
        'apoderados': Apoderado.objects.filter(user__rbd_colegio=colegio.rbd).count(),
        'estudiantes': PerfilEstudiante.objects.filter(user__rbd_colegio=colegio.rbd).count(),
        'relaciones_apoderado_estudiante': RelacionApoderadoEstudiante.objects.filter(apoderado__user__rbd_colegio=colegio.rbd).count(),
        'matriculas': Matricula.objects.filter(colegio=colegio).count(),
        'evaluaciones': Evaluacion.objects.filter(colegio=colegio).count(),
        'calificaciones': Calificacion.objects.filter(colegio=colegio).count(),
        'registros': RegistroClase.objects.filter(colegio=colegio).count(),
        'asistencias': Asistencia.objects.filter(colegio=colegio).count(),
        'tareas': Tarea.objects.filter(colegio=colegio).count(),
        'materiales': MaterialClase.objects.filter(colegio=colegio).count(),
        'bloques': BloqueHorario.objects.filter(colegio=colegio).count(),
    }

    assert repeated_counts == expected_counts
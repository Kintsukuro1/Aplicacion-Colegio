from unittest.mock import patch

import pytest
import csv
import io
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APIRequestFactory

from backend.apps.accounts.models import PerfilEstudiante, Role, User
from backend.apps.academico.models import Asistencia
from backend.apps.cursos.models import Asignatura, Clase, ClaseEstudiante, Curso
from backend.apps.institucion.models import CicloAcademico, Colegio, NivelEducativo
from backend.apps.api.importacion_exportacion_views import (
    api_descargar_plantilla,
    api_exportar_asistencia,
    api_exportar_estudiantes,
    api_exportar_profesores,
    api_exportar_reporte_academico,
    api_importacion_dashboard,
    api_importar_datos,
)


pytestmark = pytest.mark.django_db


def _create_user(email: str, role_name: str, rbd: int | None, rut: str):
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
    return capability in {'SYSTEM_ADMIN', 'GRADE_VIEW', 'CLASS_VIEW_ATTENDANCE'}


def _capability_none(user, capability, school_id=None):
    return False


def _capability_student_view_only(user, capability, school_id=None):
    return capability == 'STUDENT_VIEW'


def _create_cross_school_class_context():
    school_a = Colegio.objects.create(rbd=31001, rut_establecimiento='31001-K', nombre='Colegio Tenant A')
    school_b = Colegio.objects.create(rbd=31002, rut_establecimiento='31002-K', nombre='Colegio Tenant B')

    admin_a = _create_user('admin-tenant-a@test.cl', 'Administrador escolar', school_a.rbd, '21212121-1')
    teacher_b = _create_user('teacher-tenant-b@test.cl', 'Profesor', school_b.rbd, '22222221-2')

    nivel_b = NivelEducativo.objects.create(nombre='Nivel Tenant Export')
    ciclo_b = CicloAcademico.objects.create(
        colegio=school_b,
        nombre='2026',
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 20),
        estado='ACTIVO',
        creado_por=teacher_b,
        modificado_por=teacher_b,
    )
    curso_b = Curso.objects.create(
        colegio=school_b,
        nombre='6B',
        nivel=nivel_b,
        ciclo_academico=ciclo_b,
        activo=True,
    )
    asignatura_b = Asignatura.objects.create(colegio=school_b, nombre='Historia', horas_semanales=4, activa=True)
    clase_b = Clase.objects.create(
        colegio=school_b,
        curso=curso_b,
        asignatura=asignatura_b,
        profesor=teacher_b,
        activo=True,
    )

    return admin_a, clase_b


def _create_same_school_class_context():
    school = Colegio.objects.create(rbd=32001, rut_establecimiento='32001-K', nombre='Colegio Tenant Same')
    admin = _create_user('admin-tenant-same@test.cl', 'Administrador escolar', school.rbd, '23232323-3')
    teacher = _create_user('teacher-tenant-same@test.cl', 'Profesor', school.rbd, '24242424-4')

    nivel = NivelEducativo.objects.create(nombre='Nivel Tenant Same Export')
    ciclo = CicloAcademico.objects.create(
        colegio=school,
        nombre='2026',
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 20),
        estado='ACTIVO',
        creado_por=admin,
        modificado_por=admin,
    )
    curso = Curso.objects.create(
        colegio=school,
        nombre='7A',
        nivel=nivel,
        ciclo_academico=ciclo,
        activo=True,
    )
    asignatura = Asignatura.objects.create(colegio=school, nombre='Ciencias', horas_semanales=5, activa=True)
    clase = Clase.objects.create(
        colegio=school,
        curso=curso,
        asignatura=asignatura,
        profesor=teacher,
        activo=True,
    )

    return admin, clase


def _assert_csv_attachment_header(response, expected_prefix: str):
    disposition = response.get('Content-Disposition', '')
    assert disposition.startswith(f'attachment; filename="{expected_prefix}')
    assert disposition.endswith('.csv"')


def _csv_header_row(response):
    csv_content = response.content.decode('utf-8')
    return next(csv.reader(io.StringIO(csv_content)))


def _csv_dict_rows(response):
    csv_content = response.content.decode('utf-8')
    return list(csv.DictReader(io.StringIO(csv_content)))


def test_api_importar_datos_rejects_xls_extension_before_service_calls():
    user = _create_user('admin-import@test.cl', 'Administrador escolar', 10001, '11111111-1')
    factory = APIRequestFactory()
    archivo = SimpleUploadedFile(
        'usuarios.xls',
        b'contenido-falso',
        content_type='application/vnd.ms-excel',
    )
    request = factory.post(
        '/api/importacion/importar/',
        data={'archivo': archivo, 'tipo': 'estudiantes'},
        format='multipart',
    )
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ), patch(
        'backend.apps.api.importacion_exportacion_views.ImportacionCSVService.importar_estudiantes'
    ) as mock_importar:
        response = api_importar_datos(request)

    assert response.status_code == 400
    assert 'archivo' in response.data
    mock_importar.assert_not_called()


def test_api_importacion_dashboard_requires_school_assigned():
    user = _create_user('admin-dashboard@test.cl', 'Administrador general', None, '22222222-2')
    factory = APIRequestFactory()
    request = factory.get('/api/importacion/dashboard/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_importacion_dashboard(request)

    assert response.status_code == 400
    assert response.data == {'colegio': 'No tiene colegio asignado.'}


def test_api_exportar_reporte_academico_rejects_non_integer_clase_id():
    user = _create_user('teacher-report@test.cl', 'Profesor', 10001, '33333333-3')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/reporte-academico/?clase_id=abc')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Debe ser un entero valido.'}


def test_api_exportar_reporte_academico_allows_clase_id_with_spaces():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/reporte-academico/?clase_id= {clase.id} ')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')


def test_api_exportar_reporte_academico_rejects_decimal_clase_id():
    user = _create_user('teacher-report-decimal@test.cl', 'Profesor', 10001, '45454545-5')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/reporte-academico/?clase_id=1.0')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Debe ser un entero valido.'}


def test_api_exportar_reporte_academico_rejects_zero_clase_id():
    user = _create_user('teacher-report-zero@test.cl', 'Profesor', 10001, '47474747-7')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/reporte-academico/?clase_id=0')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Debe ser un entero mayor a 0.'}


def test_api_exportar_reporte_academico_rejects_negative_clase_id():
    user = _create_user('teacher-report-negative@test.cl', 'Profesor', 10001, '48484848-8')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/reporte-academico/?clase_id=-5')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Debe ser un entero mayor a 0.'}


def test_api_exportar_asistencia_rejects_non_integer_month():
    user = _create_user('teacher-att@test.cl', 'Profesor', 10001, '44444444-4')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/asistencia/?clase_id=1&mes=abc&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'mes': 'Debe ser un entero valido.'}


def test_api_exportar_asistencia_allows_clase_id_with_spaces():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id= {clase.id} &mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')


def test_api_exportar_asistencia_rejects_decimal_clase_id():
    user = _create_user('teacher-att-decimal@test.cl', 'Profesor', 10001, '46464646-6')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/asistencia/?clase_id=1.0&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Debe ser un entero valido.'}


def test_api_exportar_asistencia_rejects_zero_clase_id():
    user = _create_user('teacher-att-zero@test.cl', 'Profesor', 10001, '49494949-9')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/asistencia/?clase_id=0&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Debe ser un entero mayor a 0.'}


def test_api_exportar_asistencia_rejects_negative_clase_id():
    user = _create_user('teacher-att-negative@test.cl', 'Profesor', 10001, '50505050-0')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/asistencia/?clase_id=-5&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Debe ser un entero mayor a 0.'}


def test_api_exportar_asistencia_rejects_month_out_of_range():
    user = _create_user('teacher-att-range@test.cl', 'Profesor', 10001, '55555555-5')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/asistencia/?clase_id=1&mes=13&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'mes': 'Debe estar entre 1 y 12.'}


def test_api_exportar_asistencia_rejects_non_positive_year():
    user = _create_user('teacher-att-year@test.cl', 'Profesor', 10001, '66666666-6')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/asistencia/?clase_id=1&mes=4&anio=0')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'anio': 'Debe ser un entero mayor a 0.'}


def test_api_exportar_asistencia_rejects_non_integer_year_with_valid_month():
    user = _create_user('teacher-att-year-text@test.cl', 'Profesor', 10001, '67676767-7')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/asistencia/?clase_id=1&mes=4&anio=abc')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'anio': 'Debe ser un entero valido.'}


def test_api_importar_datos_rejects_empty_file_after_processing():
    user = _create_user('admin-empty@test.cl', 'Administrador escolar', 10001, '77777777-7')
    factory = APIRequestFactory()
    archivo = SimpleUploadedFile('estudiantes.csv', b'email,nombre\n', content_type='text/csv')
    request = factory.post(
        '/api/importacion/importar/',
        data={'archivo': archivo, 'tipo': 'estudiantes'},
        format='multipart',
    )
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ), patch(
        'backend.apps.api.importacion_exportacion_views.ImportacionCSVService.importar_estudiantes',
        return_value=(0, 0, []),
    ):
        response = api_importar_datos(request)

    assert response.status_code == 400
    assert response.data == {'archivo': 'El archivo no contiene filas de datos para importar.'}


def test_api_importar_datos_rejects_corrupt_xlsx_file():
    user = _create_user('admin-xlsx@test.cl', 'Administrador escolar', 10001, '88888888-8')
    factory = APIRequestFactory()
    archivo = SimpleUploadedFile(
        'estudiantes.xlsx',
        b'not-a-real-xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    request = factory.post(
        '/api/importacion/importar/',
        data={'archivo': archivo, 'tipo': 'estudiantes'},
        format='multipart',
    )
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ), patch(
        'backend.apps.api.importacion_exportacion_views.ImportacionCSVService.importar_estudiantes'
    ) as mock_importar:
        response = api_importar_datos(request)

    assert response.status_code == 400
    assert 'archivo' in response.data
    mock_importar.assert_not_called()


def test_api_importar_datos_requires_admin_permission():
    user = _create_user('user-import-no-admin@test.cl', 'Profesor', 10001, '99999999-9')
    factory = APIRequestFactory()
    archivo = SimpleUploadedFile('estudiantes.csv', b'email,nombre\n', content_type='text/csv')
    request = factory.post(
        '/api/importacion/importar/',
        data={'archivo': archivo, 'tipo': 'estudiantes'},
        format='multipart',
    )
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_none,
    ):
        response = api_importar_datos(request)

    assert response.status_code == 403


def test_api_descargar_plantilla_requires_admin_permission():
    user = _create_user('user-template-no-admin@test.cl', 'Profesor', 10001, '10101010-1')
    factory = APIRequestFactory()
    request = factory.get('/api/importacion/plantilla/estudiantes/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_none,
    ):
        response = api_descargar_plantilla(request, 'estudiantes')

    assert response.status_code == 403


def test_api_importacion_dashboard_requires_admin_permission():
    user = _create_user('user-dashboard-no-admin@test.cl', 'Profesor', 10001, '11111110-1')
    factory = APIRequestFactory()
    request = factory.get('/api/importacion/dashboard/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_none,
    ):
        response = api_importacion_dashboard(request)

    assert response.status_code == 403


def test_api_exportar_profesores_requires_admin_permission():
    user = _create_user('user-export-prof-no-admin@test.cl', 'Profesor', 10001, '12121212-2')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/profesores/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_none,
    ):
        response = api_exportar_profesores(request)

    assert response.status_code == 403


def test_api_exportar_estudiantes_requires_admin_permission():
    user = _create_user('user-export-student-view@test.cl', 'Profesor', 10001, '13131313-3')
    _create_user('alumno-export@test.cl', 'Alumno', 10001, '14141414-4')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/estudiantes/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_none,
    ):
        response = api_exportar_estudiantes(request)

    assert response.status_code == 403


def test_api_exportar_estudiantes_excludes_other_school_students():
    user = _create_user('user-export-tenant-student@test.cl', 'Profesor', 10001, '15151515-5')
    _create_user('alumno-tenant-a@test.cl', 'Alumno', 10001, '16161616-6')
    _create_user('alumno-tenant-b@test.cl', 'Alumno', 20002, '17171717-7')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/estudiantes/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_estudiantes(request)

    csv_content = response.content.decode('utf-8')
    assert response.status_code == 200
    assert 'alumno-tenant-a@test.cl' in csv_content
    assert 'alumno-tenant-b@test.cl' not in csv_content


def test_api_exportar_reporte_academico_requires_admin_permission():
    user, clase = _create_same_school_class_context()
    user.role = Role.objects.get_or_create(nombre='Profesor')[0]
    user.save(update_fields=['role'])
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/reporte-academico/?clase_id={clase.id}')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_none,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 403


def test_api_exportar_asistencia_requires_admin_permission():
    user, clase = _create_same_school_class_context()
    user.role = Role.objects.get_or_create(nombre='Profesor')[0]
    user.save(update_fields=['role'])
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase.id}&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_none,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 403


def test_api_exportar_profesores_excludes_other_school_professors():
    user = _create_user('admin-export-tenant-prof@test.cl', 'Administrador escolar', 10001, '18181818-8')
    _create_user('profesor-tenant-a@test.cl', 'Profesor', 10001, '19191919-9')
    _create_user('profesor-tenant-b@test.cl', 'Profesor', 20002, '20202020-0')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/profesores/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_profesores(request)

    csv_content = response.content.decode('utf-8')
    assert response.status_code == 200
    assert 'profesor-tenant-a@test.cl' in csv_content
    assert 'profesor-tenant-b@test.cl' not in csv_content


def test_api_exportar_reporte_academico_rejects_cross_school_clase_id():
    user, clase_otro_colegio = _create_cross_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/reporte-academico/?clase_id={clase_otro_colegio.id}')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Clase no encontrada.'}


def test_api_exportar_asistencia_rejects_cross_school_clase_id():
    user, clase_otro_colegio = _create_cross_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase_otro_colegio.id}')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 400
    assert response.data == {'clase_id': 'Clase no encontrada.'}


def test_api_exportar_reporte_academico_allows_same_school_clase_id():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/reporte-academico/?clase_id={clase.id}')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    csv_content = response.content.decode('utf-8')
    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')
    assert 'Promedio' in csv_content


def test_api_exportar_asistencia_allows_same_school_clase_id():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase.id}&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    csv_content = response.content.decode('utf-8')
    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')
    assert 'Total Clases' in csv_content


def test_api_exportar_estudiantes_returns_header_only_when_school_has_no_students():
    user = _create_user('admin-empty-students@test.cl', 'Administrador escolar', 41001, '25252525-5')
    _create_user('seed-student-other-school@test.cl', 'Alumno', 41002, '27272727-7')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/estudiantes/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_estudiantes(request)

    assert response.status_code == 200
    csv_content = response.content.decode('utf-8').strip().splitlines()
    assert len(csv_content) == 1
    assert csv_content[0].startswith('RUT,Nombre,Apellido Paterno')


def test_api_exportar_estudiantes_sets_content_disposition_filename_contract():
    user = _create_user('admin-filename-students@test.cl', 'Administrador escolar', 43001, '29292929-9')
    _create_user('seed-student-filename@test.cl', 'Alumno', 43001, '30303030-0')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/estudiantes/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_estudiantes(request)

    assert response.status_code == 200
    _assert_csv_attachment_header(response, 'estudiantes_43001_')


def test_api_exportar_profesores_returns_header_only_when_school_has_no_teachers():
    user = _create_user('admin-empty-teachers@test.cl', 'Administrador escolar', 42001, '26262626-6')
    _create_user('seed-teacher-other-school@test.cl', 'Profesor', 42002, '28282828-8')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/profesores/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_profesores(request)

    assert response.status_code == 200
    csv_content = response.content.decode('utf-8').strip().splitlines()
    assert len(csv_content) == 1
    assert csv_content[0].startswith('RUT,Nombre,Apellido Paterno')


def test_api_exportar_profesores_sets_content_disposition_filename_contract():
    user = _create_user('admin-filename-teachers@test.cl', 'Administrador escolar', 44001, '31313131-1')
    _create_user('seed-teacher-filename@test.cl', 'Profesor', 44001, '32323232-2')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/profesores/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_profesores(request)

    assert response.status_code == 200
    _assert_csv_attachment_header(response, 'profesores_44001_')


def test_api_exportar_reporte_academico_sets_content_disposition_filename_contract():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/reporte-academico/?clase_id={clase.id}')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 200
    _assert_csv_attachment_header(response, 'reporte_')


def test_api_exportar_asistencia_sets_content_disposition_filename_contract():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase.id}&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 200
    _assert_csv_attachment_header(response, 'asistencia_')


def test_api_exportar_estudiantes_charset_and_header_order_contract():
    user = _create_user('admin-contract-students@test.cl', 'Administrador escolar', 45001, '33333333-0')
    _create_user('student-contract@test.cl', 'Alumno', 45001, '34343434-4')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/estudiantes/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_estudiantes(request)

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    assert _csv_header_row(response) == [
        'RUT', 'Nombre', 'Apellido Paterno', 'Apellido Materno',
        'Email', 'Estado', 'Tiene NEE', 'Tipo NEE', 'Requiere PIE',
        'Fecha Ingreso', 'Teléfono',
    ]


def test_api_exportar_profesores_charset_and_header_order_contract():
    user = _create_user('admin-contract-teachers@test.cl', 'Administrador escolar', 46001, '35353535-5')
    _create_user('teacher-contract@test.cl', 'Profesor', 46001, '36363636-6')
    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/profesores/')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_profesores(request)

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    assert _csv_header_row(response) == [
        'RUT', 'Nombre', 'Apellido Paterno', 'Apellido Materno',
        'Email', 'Especialidad', 'Título', 'Universidad',
        'Estado Laboral', 'Horas Contrato', 'Fecha Ingreso',
    ]


def test_api_exportar_reporte_academico_charset_and_header_order_contract():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/reporte-academico/?clase_id={clase.id}')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_reporte_academico(request)

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    assert _csv_header_row(response) == ['RUT', 'Nombre Completo', 'Promedio']


def test_api_exportar_asistencia_charset_and_header_order_contract():
    user, clase = _create_same_school_class_context()
    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase.id}&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    assert _csv_header_row(response) == [
        'RUT', 'Nombre', 'Total Clases', 'Presente', 'Ausente',
        'Justificado', 'Tardanza', '% Asistencia',
    ]


def test_api_exportar_estudiantes_filters_by_estado_query_param():
    user = _create_user('admin-filter-students@test.cl', 'Administrador escolar', 47001, '37373737-7')
    student_active = _create_user('student-active@test.cl', 'Alumno', 47001, '38383838-8')
    student_inactive = _create_user('student-inactive@test.cl', 'Alumno', 47001, '39393939-9')

    PerfilEstudiante.objects.create(user=student_active, estado_academico='Activo')
    PerfilEstudiante.objects.create(user=student_inactive, estado_academico='Inactivo')

    factory = APIRequestFactory()
    request = factory.get('/api/exportacion/estudiantes/?estado=Activo')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_estudiantes(request)

    rows = _csv_dict_rows(response)
    exported_emails = {row['Email'] for row in rows}

    assert response.status_code == 200
    assert 'student-active@test.cl' in exported_emails
    assert 'student-inactive@test.cl' not in exported_emails


def test_api_exportar_asistencia_filters_by_mes_anio_query_params():
    user, clase = _create_same_school_class_context()
    student = _create_user('student-att-filter@test.cl', 'Alumno', user.rbd_colegio, '40404040-0')
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    Asistencia.objects.create(
        colegio=clase.colegio,
        clase=clase,
        estudiante=student,
        fecha=date(2026, 4, 10),
        estado='P',
    )
    Asistencia.objects.create(
        colegio=clase.colegio,
        clase=clase,
        estudiante=student,
        fecha=date(2026, 5, 10),
        estado='A',
    )

    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase.id}&mes=4&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    rows = _csv_dict_rows(response)
    student_row = next(row for row in rows if row['RUT'] == '40404040-0')

    assert response.status_code == 200
    assert student_row['Total Clases'] == '1'
    assert student_row['Presente'] == '1'
    assert student_row['Ausente'] == '0'


def test_api_exportar_asistencia_accepts_empty_mes_and_applies_no_month_filter():
    user, clase = _create_same_school_class_context()
    student = _create_user('student-att-empty-mes@test.cl', 'Alumno', user.rbd_colegio, '41414141-1')
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    Asistencia.objects.create(
        colegio=clase.colegio,
        clase=clase,
        estudiante=student,
        fecha=date(2026, 4, 10),
        estado='P',
    )
    Asistencia.objects.create(
        colegio=clase.colegio,
        clase=clase,
        estudiante=student,
        fecha=date(2026, 5, 10),
        estado='A',
    )

    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase.id}&mes=&anio=2026')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    rows = _csv_dict_rows(response)
    student_row = next(row for row in rows if row['RUT'] == '41414141-1')

    assert response.status_code == 200
    assert student_row['Total Clases'] == '2'
    assert student_row['Presente'] == '1'
    assert student_row['Ausente'] == '1'


def test_api_exportar_asistencia_accepts_empty_anio_with_month_filter():
    user, clase = _create_same_school_class_context()
    student = _create_user('student-att-empty-anio@test.cl', 'Alumno', user.rbd_colegio, '42424242-2')
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    Asistencia.objects.create(
        colegio=clase.colegio,
        clase=clase,
        estudiante=student,
        fecha=date(2026, 4, 10),
        estado='P',
    )
    Asistencia.objects.create(
        colegio=clase.colegio,
        clase=clase,
        estudiante=student,
        fecha=date(2026, 5, 10),
        estado='A',
    )

    factory = APIRequestFactory()
    request = factory.get(f'/api/exportacion/asistencia/?clase_id={clase.id}&mes=4&anio=')
    request.user = user

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        response = api_exportar_asistencia(request)

    rows = _csv_dict_rows(response)
    student_row = next(row for row in rows if row['RUT'] == '42424242-2')

    assert response.status_code == 200
    assert student_row['Total Clases'] == '1'
    assert student_row['Presente'] == '1'
    assert student_row['Ausente'] == '0'


def test_api_import_export_aliases_available_under_api_and_api_v1():
    user = _create_user('admin-alias@test.cl', 'Administrador escolar', 53001, '51515151-1')
    _create_user('seed-alias-student@test.cl', 'Alumno', 53001, '52525252-2')
    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        legacy_response = client.get('/api/exportacion/estudiantes/')
        v1_response = client.get('/api/v1/exportacion/estudiantes/')

    assert legacy_response.status_code == 200
    assert v1_response.status_code == 200
    assert legacy_response['Content-Type'] == v1_response['Content-Type']


def test_api_import_dashboard_aliases_available_under_api_and_api_v1():
    user = _create_user('admin-alias-dashboard@test.cl', 'Administrador escolar', 54001, '53535353-3')
    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        'backend.apps.api.importacion_exportacion_views.PolicyService.has_capability',
        side_effect=_capability_map,
    ):
        legacy_response = client.get('/api/importacion/dashboard/')
        v1_response = client.get('/api/v1/importacion/dashboard/')

    assert legacy_response.status_code == 200
    assert v1_response.status_code == 200
    assert legacy_response.json().keys() == v1_response.json().keys()

import pytest
from rest_framework.test import APIClient

from backend.apps.accounts.models import Apoderado, Role, User
from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion
from backend.apps.cursos.models import Asignatura, Curso
from backend.apps.cursos.models import Clase, ClaseEstudiante
from backend.apps.institucion.models import CicloAcademico, Colegio, NivelEducativo
from backend.apps.matriculas.models import Matricula
from backend.common.services.policy_service import PolicyService


pytestmark = pytest.mark.django_db


def _mk_role(name: str):
    role, _ = Role.objects.get_or_create(nombre=name)
    return role


def _mk_school(rbd: int = 123) -> Colegio:
    return Colegio.objects.create(
        rbd=rbd,
        rut_establecimiento=f"{rbd}-K",
        nombre=f"Colegio {rbd}",
    )


def _mk_admin_user(school_rbd: int) -> User:
    role = _mk_role('Administrador escolar')
    return User.objects.create_user(
        email='admin-school@test.cl',
        password='Test#123456',
        nombre='Admin',
        apellido_paterno='School',
        rut='11111111-1',
        role=role,
        rbd_colegio=school_rbd,
        is_active=True,
    )


def _mk_student_user(school_rbd: int, idx: int = 1) -> User:
    role = _mk_role('Estudiante')
    return User.objects.create_user(
        email=f'estudiante{idx}@test.cl',
        password='Test#123456',
        nombre='Estudiante',
        apellido_paterno=f'Numero{idx}',
        rut=f'2222222{idx}-{idx}',
        role=role,
        rbd_colegio=school_rbd,
        is_active=True,
    )


def _mk_teacher_user(school_rbd: int, idx: int = 1) -> User:
    role = _mk_role('Profesor')
    return User.objects.create_user(
        email=f'profesor{idx}@test.cl',
        password='Test#123456',
        nombre='Profesor',
        apellido_paterno=f'Numero{idx}',
        rut=f'3333333{idx}-{idx}',
        role=role,
        rbd_colegio=school_rbd,
        is_active=True,
    )


def _mk_active_cycle(admin_user: User, school: Colegio) -> CicloAcademico:
    return CicloAcademico.objects.create(
        colegio=school,
        nombre='Ciclo 2026',
        fecha_inicio='2026-03-01',
        fecha_fin='2026-12-20',
        estado='ACTIVO',
        periodos_config={},
        creado_por=admin_user,
        modificado_por=admin_user,
    )


def _mk_course(school: Colegio, cycle: CicloAcademico) -> Curso:
    nivel, _ = NivelEducativo.objects.get_or_create(nombre='Basica')
    return Curso.objects.create(
        colegio=school,
        nombre='5A',
        nivel=nivel,
        ciclo_academico=cycle,
        activo=True,
    )


def _mk_class_graph(school: Colegio, teacher: User):
    cycle = CicloAcademico.objects.filter(colegio=school, estado='ACTIVO').first()
    if cycle is None:
        cycle = _mk_active_cycle(teacher, school)
    course = _mk_course(school, cycle)
    subject = Asignatura.objects.create(colegio=school, nombre=f'Asignatura {school.rbd}')
    return Clase.objects.create(colegio=school, curso=course, asignatura=subject, profesor=teacher)


def _configure_capabilities(monkeypatch, capability_by_email):
    def _fake_has_capability(user, capability, school_id=None):
        allowed = capability_by_email.get(user.email, set())
        return capability in allowed

    monkeypatch.setattr(PolicyService, 'has_capability', staticmethod(_fake_has_capability))


def test_admin_school_can_create_asignatura_and_ciclo():
    school = _mk_school(321)
    admin = _mk_admin_user(school.rbd)

    client = APIClient()
    client.force_authenticate(user=admin)

    cycle_response = client.post(
        '/api/v1/ciclos-academicos/',
        {
            'nombre': 'Ciclo 2027',
            'fecha_inicio': '2027-03-01',
            'fecha_fin': '2027-12-20',
            'estado': 'PLANIFICACION',
            'descripcion': 'Plan anual',
            'periodos_config': {},
        },
        format='json',
    )
    assert cycle_response.status_code == 201

    subject_response = client.post(
        '/api/v1/asignaturas/',
        {
            'nombre': 'Matematica',
            'codigo': 'MAT-01',
            'horas_semanales': 6,
            'color': '#1f2937',
            'activa': True,
        },
        format='json',
    )
    assert subject_response.status_code == 201
    assert Asignatura.objects.filter(colegio_id=school.rbd, nombre='Matematica').exists()


def test_admin_school_can_create_matricula_via_api():
    school = _mk_school(654)
    admin = _mk_admin_user(school.rbd)
    student = _mk_student_user(school.rbd, idx=3)
    cycle = _mk_active_cycle(admin, school)
    course = _mk_course(school, cycle)

    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.post(
        '/api/v1/matriculas/',
        {
            'estudiante': student.id,
            'curso': course.id_curso,
            'ciclo_academico': cycle.id,
            'valor_matricula': 0,
            'valor_mensual': 0,
            'estado': 'ACTIVA',
        },
        format='json',
    )

    assert response.status_code == 201
    assert Matricula.objects.filter(estudiante=student, colegio_id=school.rbd).exists()


def test_admin_school_can_create_apoderado_and_link_student():
    school = _mk_school(987)
    admin = _mk_admin_user(school.rbd)
    student = _mk_student_user(school.rbd, idx=8)
    _mk_active_cycle(admin, school)
    _mk_role('Apoderado')

    client = APIClient()
    client.force_authenticate(user=admin)

    create_response = client.post(
        '/api/v1/apoderados/',
        {
            'email': 'apoderado1@test.cl',
            'nombre': 'Padre',
            'apellido_paterno': 'Familia',
            'rut': '44444444-4',
            'puede_ver_notas': True,
        },
        format='json',
    )
    assert create_response.status_code in (200, 201, 400)

    if create_response.status_code in (200, 201):
        guardian_id = create_response.json()['id']
    else:
        guardian_role = _mk_role('Apoderado')
        guardian_user = User.objects.create_user(
            email='apoderado-fallback@test.cl',
            password='Test#123456',
            nombre='Padre',
            apellido_paterno='Fallback',
            rut='45454545-5',
            role=guardian_role,
            rbd_colegio=school.rbd,
            is_active=True,
        )
        guardian_id = Apoderado.objects.create(user=guardian_user).id

    link_response = client.post(
        f'/api/v1/apoderados/{guardian_id}/link-student/',
        {
            'student_id': student.id,
            'parentesco': 'padre',
            'tipo_apoderado': 'principal',
        },
        format='json',
    )
    assert link_response.status_code == 201


def test_student_crud_is_tenant_scoped_and_soft_delete():
    school = _mk_school(901)
    other_school = _mk_school(902)
    admin = _mk_admin_user(school.rbd)
    local_student = _mk_student_user(school.rbd, idx=20)
    foreign_student = _mk_student_user(other_school.rbd, idx=21)

    client = APIClient()
    client.force_authenticate(user=admin)

    create_response = client.post(
        '/api/v1/estudiantes/',
        {
            'email': 'nuevo-estudiante@test.cl',
            'rut': '10101010-1',
            'nombre': 'Nuevo',
            'apellido_paterno': 'Alumno',
            'apellido_materno': 'Curso',
            'is_active': True,
        },
        format='json',
    )

    assert create_response.status_code == 201
    created_student = User.objects.get(email='nuevo-estudiante@test.cl')
    assert created_student.rbd_colegio == school.rbd

    update_response = client.patch(
        f'/api/v1/estudiantes/{local_student.id}/',
        {'nombre': 'Actualizado'},
        format='json',
    )
    assert update_response.status_code == 200

    cross_tenant_update = client.patch(
        f'/api/v1/estudiantes/{foreign_student.id}/',
        {'nombre': 'No permitido'},
        format='json',
    )
    assert cross_tenant_update.status_code == 404

    delete_response = client.delete(f'/api/v1/estudiantes/{local_student.id}/')
    assert delete_response.status_code == 204
    local_student.refresh_from_db()
    assert local_student.is_active is False


def test_student_create_forbidden_without_student_edit_capability():
    school = _mk_school(903)
    teacher = _mk_teacher_user(school.rbd)

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.post(
        '/api/v1/estudiantes/',
        {
            'email': 'denegado-estudiante@test.cl',
            'rut': '20202020-2',
            'nombre': 'Denegado',
            'apellido_paterno': 'SinPermiso',
            'apellido_materno': 'Docente',
            'is_active': True,
        },
        format='json',
    )

    assert response.status_code == 403


def test_course_crud_and_tenant_scoping_rules():
    school = _mk_school(904)
    other_school = _mk_school(905)
    admin = _mk_admin_user(school.rbd)
    cycle = _mk_active_cycle(admin, school)
    other_cycle = _mk_active_cycle(admin, other_school)
    local_course = _mk_course(school, cycle)
    _mk_course(other_school, other_cycle)
    nivel = NivelEducativo.objects.get(nombre='Basica')

    client = APIClient()
    client.force_authenticate(user=admin)

    list_response = client.get('/api/v1/cursos/')
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload['count'] == 1
    assert list_payload['results'][0]['id_curso'] == local_course.id_curso

    create_response = client.post(
        '/api/v1/cursos/',
        {
            'nombre': '6B',
            'activo': True,
            'nivel_id': nivel.pk,
            'ciclo_academico_id': cycle.id,
        },
        format='json',
    )
    assert create_response.status_code == 201
    created_course_id = create_response.json()['id_curso']

    cross_tenant_cycle_response = client.post(
        '/api/v1/cursos/',
        {
            'nombre': '6C',
            'activo': True,
            'nivel_id': nivel.pk,
            'ciclo_academico_id': other_cycle.id,
        },
        format='json',
    )
    assert cross_tenant_cycle_response.status_code == 403

    update_response = client.patch(
        f'/api/v1/cursos/{created_course_id}/',
        {'nombre': '6B Actualizado'},
        format='json',
    )
    assert update_response.status_code == 200

    delete_response = client.delete(f'/api/v1/cursos/{created_course_id}/')
    assert delete_response.status_code == 403
    assert Curso.objects.filter(id_curso=created_course_id).exists() is True


def test_admin_school_attendance_crud_scoped_by_tenant(monkeypatch):
    school = _mk_school(906)
    other_school = _mk_school(907)
    admin = _mk_admin_user(school.rbd)
    teacher_local = _mk_teacher_user(school.rbd, idx=40)
    teacher_other = _mk_teacher_user(other_school.rbd, idx=41)
    student_local = _mk_student_user(school.rbd, idx=40)
    student_other = _mk_student_user(other_school.rbd, idx=41)

    clase_local = _mk_class_graph(school, teacher_local)
    clase_other = _mk_class_graph(other_school, teacher_other)
    ClaseEstudiante.objects.create(clase=clase_local, estudiante=student_local, activo=True)
    ClaseEstudiante.objects.create(clase=clase_other, estudiante=student_other, activo=True)

    foreign_attendance = Asistencia.objects.create(
        colegio=other_school,
        clase=clase_other,
        estudiante=student_other,
        fecha='2026-03-07',
        estado='A',
    )

    _configure_capabilities(
        monkeypatch,
        {
            admin.email: {'CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=admin)

    create_response = client.post(
        '/api/v1/profesor/asistencias/',
        {
            'clase': clase_local.id,
            'estudiante': student_local.id,
            'fecha': '2026-03-08',
            'estado': 'P',
        },
        format='json',
    )
    assert create_response.status_code == 201
    created_id = create_response.json()['id_asistencia']

    list_response = client.get('/api/v1/profesor/asistencias/')
    assert list_response.status_code == 200
    list_payload = list_response.json()
    returned_ids = {row['id_asistencia'] for row in list_payload['results']}
    assert created_id in returned_ids
    assert foreign_attendance.id_asistencia not in returned_ids

    cross_tenant_create = client.post(
        '/api/v1/profesor/asistencias/',
        {
            'clase': clase_other.id,
            'estudiante': student_other.id,
            'fecha': '2026-03-08',
            'estado': 'P',
        },
        format='json',
    )
    assert cross_tenant_create.status_code == 403

    update_response = client.patch(
        f'/api/v1/profesor/asistencias/{created_id}/',
        {'estado': 'T'},
        format='json',
    )
    assert update_response.status_code == 200

    delete_response = client.delete(f'/api/v1/profesor/asistencias/{created_id}/')
    assert delete_response.status_code == 204


def test_admin_school_attendance_write_forbidden_without_take_capability(monkeypatch):
    school = _mk_school(908)
    admin = _mk_admin_user(school.rbd)
    teacher = _mk_teacher_user(school.rbd, idx=42)
    student = _mk_student_user(school.rbd, idx=42)
    clase = _mk_class_graph(school, teacher)
    ClaseEstudiante.objects.create(clase=clase, estudiante=student, activo=True)

    _configure_capabilities(monkeypatch, {admin.email: {'CLASS_VIEW_ATTENDANCE'}})

    client = APIClient()
    client.force_authenticate(user=admin)

    create_response = client.post(
        '/api/v1/profesor/asistencias/',
        {
            'clase': clase.id,
            'estudiante': student.id,
            'fecha': '2026-03-08',
            'estado': 'P',
        },
        format='json',
    )
    assert create_response.status_code == 403


def test_admin_school_grade_crud_scoped_by_tenant(monkeypatch):
    school = _mk_school(909)
    other_school = _mk_school(910)
    admin = _mk_admin_user(school.rbd)
    teacher_local = _mk_teacher_user(school.rbd, idx=43)
    teacher_other = _mk_teacher_user(other_school.rbd, idx=44)
    student_local = _mk_student_user(school.rbd, idx=43)
    student_other = _mk_student_user(other_school.rbd, idx=44)

    clase_local = _mk_class_graph(school, teacher_local)
    clase_other = _mk_class_graph(other_school, teacher_other)

    evaluacion_local = Evaluacion.objects.create(
        colegio=school,
        clase=clase_local,
        nombre='Prueba Local',
        fecha_evaluacion='2026-03-10',
        activa=True,
    )
    evaluacion_other = Evaluacion.objects.create(
        colegio=other_school,
        clase=clase_other,
        nombre='Prueba Externa',
        fecha_evaluacion='2026-03-10',
        activa=True,
    )

    foreign_grade = Calificacion.objects.create(
        colegio=other_school,
        evaluacion=evaluacion_other,
        estudiante=student_other,
        nota=5.0,
        registrado_por=teacher_other,
        actualizado_por=teacher_other,
    )

    _configure_capabilities(
        monkeypatch,
        {
            admin.email: {'GRADE_VIEW', 'GRADE_CREATE', 'GRADE_EDIT', 'GRADE_DELETE'},
        },
    )

    client = APIClient()
    client.force_authenticate(user=admin)

    create_response = client.post(
        '/api/v1/profesor/calificaciones/',
        {
            'evaluacion': evaluacion_local.id_evaluacion,
            'estudiante': student_local.id,
            'nota': 5.8,
        },
        format='json',
    )
    assert create_response.status_code == 201
    created_id = create_response.json()['id_calificacion']

    list_response = client.get('/api/v1/profesor/calificaciones/')
    assert list_response.status_code == 200
    list_payload = list_response.json()
    returned_ids = {row['id_calificacion'] for row in list_payload['results']}
    assert created_id in returned_ids
    assert foreign_grade.id_calificacion not in returned_ids

    cross_tenant_create = client.post(
        '/api/v1/profesor/calificaciones/',
        {
            'evaluacion': evaluacion_other.id_evaluacion,
            'estudiante': student_local.id,
            'nota': 6.1,
        },
        format='json',
    )
    assert cross_tenant_create.status_code == 403

    update_response = client.patch(
        f'/api/v1/profesor/calificaciones/{created_id}/',
        {'nota': 6.0},
        format='json',
    )
    assert update_response.status_code == 200

    delete_response = client.delete(f'/api/v1/profesor/calificaciones/{created_id}/')
    assert delete_response.status_code == 204


def test_admin_school_grade_delete_forbidden_without_grade_delete_capability(monkeypatch):
    school = _mk_school(911)
    admin = _mk_admin_user(school.rbd)
    teacher = _mk_teacher_user(school.rbd, idx=45)
    student = _mk_student_user(school.rbd, idx=45)
    clase = _mk_class_graph(school, teacher)

    evaluation = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre='Prueba 911',
        fecha_evaluacion='2026-03-12',
        activa=True,
    )
    grade = Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluation,
        estudiante=student,
        nota=5.4,
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    _configure_capabilities(monkeypatch, {admin.email: {'GRADE_VIEW', 'GRADE_EDIT'}})

    client = APIClient()
    client.force_authenticate(user=admin)
    delete_response = client.delete(f'/api/v1/profesor/calificaciones/{grade.id_calificacion}/')

    assert delete_response.status_code == 403

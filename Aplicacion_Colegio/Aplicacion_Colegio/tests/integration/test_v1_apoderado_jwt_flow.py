import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from backend.apps.accounts.models import Apoderado, RelacionApoderadoEstudiante, Role, User
from backend.apps.comunicados.models import Comunicado
from backend.apps.core.models import JustificativoInasistencia
from backend.apps.cursos.models import Curso
from backend.apps.institucion.models import Colegio
from backend.apps.institucion.models import CicloAcademico, NivelEducativo
from backend.apps.matriculas.models import Matricula


pytestmark = pytest.mark.django_db


def _mk_role(name: str):
    role, _ = Role.objects.get_or_create(nombre=name)
    return role


def _mk_school(rbd: int) -> Colegio:
    return Colegio.objects.create(
        rbd=rbd,
        rut_establecimiento=f"{rbd}-K",
        nombre=f"Colegio {rbd}",
    )


def _mk_user(email: str, role_name: str, school_rbd: int, rut: str) -> User:
    return User.objects.create_user(
        email=email,
        password="Test#123456",
        nombre="Nombre",
        apellido_paterno="Apellido",
        rut=rut,
        role=_mk_role(role_name),
        rbd_colegio=school_rbd,
        is_active=True,
    )


def _build_jwt_client(email: str, password: str = "Test#123456") -> APIClient:
    client = APIClient()
    token_response = client.post(
        "/api/v1/auth/token/",
        {"email": email, "password": password},
        format="json",
    )
    assert token_response.status_code == 200
    access = token_response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _mk_guardian_relation(guardian: User, student: User):
    guardian_profile = Apoderado.objects.create(user=guardian)
    return RelacionApoderadoEstudiante.objects.create(
        apoderado=guardian_profile,
        estudiante=student,
        parentesco="madre",
        tipo_apoderado="principal",
        activa=True,
    )


def _mk_student_course_context(school: Colegio, teacher: User, student: User):
    nivel = NivelEducativo.objects.create(nombre=f"Nivel {school.rbd}")
    ciclo = CicloAcademico.objects.create(
        colegio=school,
        nombre=f"Ciclo {school.rbd}",
        fecha_inicio="2026-03-01",
        fecha_fin="2026-12-20",
        estado="ACTIVO",
        periodos_config={},
        creado_por=teacher,
        modificado_por=teacher,
    )
    curso = Curso.objects.create(
        colegio=school,
        nombre="6A",
        nivel=nivel,
        ciclo_academico=ciclo,
        activo=True,
    )
    Matricula.objects.create(
        estudiante=student,
        colegio=school,
        curso=curso,
        ciclo_academico=ciclo,
        estado="ACTIVA",
    )
    return curso


def test_apoderado_mis_pupilos_with_real_jwt_token_returns_guardian_students():
    school = _mk_school(5601)
    guardian = _mk_user("guardian.jwt@test.cl", "Apoderado", school.rbd, "56000001-1")
    student = _mk_user("student.jwt@test.cl", "Estudiante", school.rbd, "56000002-2")

    _mk_guardian_relation(guardian, student)

    client = _build_jwt_client(guardian.email)
    response = client.get("/api/v1/apoderado/mis-pupilos/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == student.id


def test_apoderado_endpoint_with_real_jwt_rejects_non_guardian_user():
    school = _mk_school(5602)
    teacher = _mk_user("teacher.jwt@test.cl", "Profesor", school.rbd, "56000003-3")

    client = _build_jwt_client(teacher.email)
    response = client.get("/api/v1/apoderado/mis-pupilos/")

    assert response.status_code == 403
    assert "perfil de apoderado" in response.json()["detail"].lower()


def test_apoderado_comunicados_with_real_jwt_returns_only_related_school_rows():
    school = _mk_school(5603)
    other_school = _mk_school(5604)

    guardian = _mk_user("guardian.comunicados@test.cl", "Apoderado", school.rbd, "56000004-4")
    student = _mk_user("student.comunicados@test.cl", "Estudiante", school.rbd, "56000005-5")
    teacher = _mk_user("teacher.comunicados@test.cl", "Profesor", school.rbd, "56000006-6")
    outsider_teacher = _mk_user("teacher.outside@test.cl", "Profesor", other_school.rbd, "56000007-7")

    _mk_guardian_relation(guardian, student)
    _mk_student_course_context(school, teacher, student)

    visible = Comunicado.objects.create(
        colegio=school,
        tipo="comunicado",
        titulo="Comunicado para apoderados",
        contenido="Contenido visible",
        destinatario="apoderados",
        publicado_por=teacher,
        activo=True,
    )
    hidden = Comunicado.objects.create(
        colegio=other_school,
        tipo="comunicado",
        titulo="Comunicado otro colegio",
        contenido="Contenido no visible",
        destinatario="apoderados",
        publicado_por=outsider_teacher,
        activo=True,
    )

    client = _build_jwt_client(guardian.email)
    response = client.get("/api/v1/apoderado/comunicados/")

    assert response.status_code == 200
    ids = {row["id_comunicado"] for row in response.json()}
    assert visible.id_comunicado in ids
    assert hidden.id_comunicado not in ids


def test_apoderado_justificativos_with_real_jwt_accepts_multipart_file():
    school = _mk_school(5605)
    guardian = _mk_user("guardian.justificativo@test.cl", "Apoderado", school.rbd, "56000008-8")
    student = _mk_user("student.justificativo@test.cl", "Estudiante", school.rbd, "56000009-9")

    _mk_guardian_relation(guardian, student)

    client = _build_jwt_client(guardian.email)
    document = SimpleUploadedFile("respaldo.jpg", b"fake-image-content", content_type="image/jpeg")
    response = client.post(
        "/api/v1/apoderado/justificativos/",
        {
            "estudiante_id": str(student.id),
            "fecha_ausencia": "2026-05-20",
            "motivo": "Control medico",
            "tipo": "MEDICO",
            "foto": document,
        },
        format="multipart",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["estado"] == "PENDIENTE"

    created = JustificativoInasistencia.objects.get(id_justificativo=payload["id_justificativo"])
    assert created.estudiante_id == student.id
    assert created.presentado_por_id == guardian.id
    assert created.documento_adjunto.name

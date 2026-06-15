from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion
from backend.apps.accounts.models import Apoderado, RelacionApoderadoEstudiante, Role, User
from backend.apps.comunicados.models import Comunicado
from backend.apps.core.models import AnotacionConvivencia, JustificativoInasistencia
from backend.apps.cursos.models import Asignatura, Clase, Curso
from backend.apps.institucion.models import CicloAcademico, Colegio, NivelEducativo
from backend.apps.matriculas.models import EstadoCuenta, Matricula


pytestmark = pytest.mark.django_db


def _mk_role(name: str):
    role, _ = Role.objects.get_or_create(nombre=name)
    return role


def _mk_user(email: str, role_name: str, school_id: int, rut: str) -> User:
    return User.objects.create_user(
        email=email,
        password="Test#123456",
        nombre="Nombre",
        apellido_paterno="Apellido",
        rut=rut,
        role=_mk_role(role_name),
        rbd_colegio=school_id,
        is_active=True,
    )


def _mk_school(rbd: int) -> Colegio:
    return Colegio.objects.create(
        rbd=rbd,
        rut_establecimiento=f"{rbd}-K",
        nombre=f"Colegio {rbd}",
    )


def _mk_guardian_relation(guardian_user: User, student: User, parentesco: str = "madre"):
    guardian_profile = Apoderado.objects.create(user=guardian_user)
    return RelacionApoderadoEstudiante.objects.create(
        apoderado=guardian_profile,
        estudiante=student,
        parentesco=parentesco,
        tipo_apoderado="principal",
        activa=True,
    )


def _mk_class_context(school: Colegio, teacher: User):
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
    asignatura = Asignatura.objects.create(colegio=school, nombre="Matematica")
    clase = Clase.objects.create(colegio=school, curso=curso, asignatura=asignatura, profesor=teacher, activo=True)
    return ciclo, curso, clase


def test_apoderado_mis_pupilos_returns_summary_payload():
    school = _mk_school(5001)
    guardian = _mk_user("apoderado1@test.cl", "Apoderado", school.rbd, "10000001-1")
    student = _mk_user("student1@test.cl", "Estudiante", school.rbd, "10000002-2")
    teacher = _mk_user("teacher1@test.cl", "Profesor", school.rbd, "10000003-3")

    _mk_guardian_relation(guardian, student)
    ciclo, curso, clase = _mk_class_context(school, teacher)

    Matricula.objects.create(
        estudiante=student,
        colegio=school,
        curso=curso,
        ciclo_academico=ciclo,
        estado="ACTIVA",
    )

    evaluacion = Evaluacion.objects.create(
        colegio=school,
        clase=clase,
        nombre="Prueba 1",
        fecha_evaluacion="2026-04-10",
        ponderacion=Decimal("50.00"),
    )
    Calificacion.objects.create(
        colegio=school,
        evaluacion=evaluacion,
        estudiante=student,
        nota=Decimal("6.0"),
        registrado_por=teacher,
        actualizado_por=teacher,
    )

    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha="2026-04-10", estado="P")
    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha="2026-04-11", estado="A")
    JustificativoInasistencia.objects.create(
        estudiante=student,
        colegio=school,
        fecha_ausencia="2026-04-08",
        motivo="Control medico",
        tipo="MEDICO",
        estado="PENDIENTE",
        presentado_por=guardian,
    )

    client = APIClient()
    client.force_authenticate(user=guardian)
    response = client.get("/api/v1/apoderado/mis-pupilos/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == student.id
    assert payload[0]["curso"] == "6A"
    assert payload[0]["promedio_notas"] == 6.0
    assert payload[0]["asistencia_porcentaje"] == 50.0
    assert payload[0]["justificativos_pendientes"] == 1


def test_apoderado_pupilo_notas_forbidden_for_unrelated_student():
    school = _mk_school(5002)
    guardian = _mk_user("apoderado2@test.cl", "Apoderado", school.rbd, "20000001-1")
    student_related = _mk_user("student-related@test.cl", "Estudiante", school.rbd, "20000002-2")
    student_other = _mk_user("student-other@test.cl", "Estudiante", school.rbd, "20000003-3")
    _mk_guardian_relation(guardian, student_related)

    client = APIClient()
    client.force_authenticate(user=guardian)
    response = client.get(f"/api/v1/apoderado/pupilo/{student_other.id}/notas/")

    assert response.status_code == 403


def test_apoderado_pupilo_asistencia_and_anotaciones_contract():
    school = _mk_school(5003)
    guardian = _mk_user("apoderado3@test.cl", "Apoderado", school.rbd, "30000001-1")
    student = _mk_user("student3@test.cl", "Estudiante", school.rbd, "30000002-2")
    teacher = _mk_user("teacher3@test.cl", "Profesor", school.rbd, "30000003-3")
    _mk_guardian_relation(guardian, student)
    _, _, clase = _mk_class_context(school, teacher)

    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha="2026-04-01", estado="P")
    Asistencia.objects.create(colegio=school, clase=clase, estudiante=student, fecha="2026-04-02", estado="T")
    AnotacionConvivencia.objects.create(
        estudiante=student,
        colegio=school,
        tipo="NEUTRA",
        categoria="COMPORTAMIENTO",
        descripcion="Participacion regular.",
        gravedad=1,
        registrado_por=teacher,
    )

    client = APIClient()
    client.force_authenticate(user=guardian)

    asistencia_response = client.get(f"/api/v1/apoderado/pupilo/{student.id}/asistencia/")
    assert asistencia_response.status_code == 200
    asistencia_payload = asistencia_response.json()
    assert asistencia_payload["resumen"]["total"] == 2
    assert len(asistencia_payload["resultados"]) == 2

    anot_response = client.get(f"/api/v1/apoderado/pupilo/{student.id}/anotaciones/")
    assert anot_response.status_code == 200
    anot_payload = anot_response.json()
    assert anot_payload["total"] == 1
    assert anot_payload["resultados"][0]["descripcion"] == "Participacion regular."


def test_apoderado_justificativo_accepts_multipart_photo():
    school = _mk_school(5004)
    guardian = _mk_user("apoderado4@test.cl", "Apoderado", school.rbd, "40000001-1")
    student = _mk_user("student4@test.cl", "Estudiante", school.rbd, "40000002-2")
    _mk_guardian_relation(guardian, student)

    client = APIClient()
    client.force_authenticate(user=guardian)

    foto = SimpleUploadedFile("justificativo.jpg", b"binary-image-content", content_type="image/jpeg")
    response = client.post(
        "/api/v1/apoderado/justificativos/",
        {
            "estudiante_id": str(student.id),
            "fecha_ausencia": "2026-05-10",
            "motivo": "Consulta medica",
            "tipo": "MEDICO",
            "foto": foto,
        },
        format="multipart",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["estado"] == "PENDIENTE"
    assert JustificativoInasistencia.objects.filter(estudiante=student, presentado_por=guardian).exists()


def test_apoderado_comunicados_and_pagos_estado_contracts():
    school = _mk_school(5005)
    other_school = _mk_school(5006)
    guardian = _mk_user("apoderado5@test.cl", "Apoderado", school.rbd, "50000001-1")
    student = _mk_user("student5@test.cl", "Estudiante", school.rbd, "50000002-2")
    teacher = _mk_user("teacher5@test.cl", "Profesor", school.rbd, "50000003-3")
    outsider_teacher = _mk_user("teacher6@test.cl", "Profesor", other_school.rbd, "50000004-4")
    _mk_guardian_relation(guardian, student)

    ciclo, curso, _ = _mk_class_context(school, teacher)
    Matricula.objects.create(estudiante=student, colegio=school, curso=curso, ciclo_academico=ciclo, estado="ACTIVA")

    com_a = Comunicado.objects.create(
        colegio=school,
        tipo="comunicado",
        titulo="Comunicado Apoderados",
        contenido="Info general",
        destinatario="apoderados",
        publicado_por=teacher,
        activo=True,
    )
    com_b = Comunicado.objects.create(
        colegio=school,
        tipo="citacion",
        titulo="Citacion Curso",
        contenido="Reunion curso",
        destinatario="curso_especifico",
        publicado_por=teacher,
        activo=True,
    )
    com_b.cursos_destinatarios.add(curso)

    Comunicado.objects.create(
        colegio=other_school,
        tipo="comunicado",
        titulo="Otro colegio",
        contenido="No debe verse",
        destinatario="apoderados",
        publicado_por=outsider_teacher,
        activo=True,
    )

    EstadoCuenta.objects.create(
        estudiante=student,
        colegio=school,
        mes=5,
        anio=2026,
        total_deuda=Decimal("100000"),
        total_pagado=Decimal("40000"),
        saldo_pendiente=Decimal("60000"),
        estado="GENERADO",
    )

    client = APIClient()
    client.force_authenticate(user=guardian)

    comunicados_response = client.get("/api/v1/apoderado/comunicados/")
    assert comunicados_response.status_code == 200
    comunicados_payload = comunicados_response.json()
    ids = {item["id_comunicado"] for item in comunicados_payload}
    assert com_a.id_comunicado in ids
    assert com_b.id_comunicado in ids

    pagos_response = client.get("/api/v1/apoderado/pagos/estado/")
    assert pagos_response.status_code == 200
    pagos_payload = pagos_response.json()
    assert pagos_payload["resumen"]["total_deuda"] == 100000.0
    assert pagos_payload["resumen"]["saldo_pendiente"] == 60000.0
    assert pagos_payload["pupilos"][0]["student_id"] == student.id


def test_apoderado_endpoints_reject_user_without_guardian_profile():
    school = _mk_school(5007)
    teacher = _mk_user("teacher-no-guardian@test.cl", "Profesor", school.rbd, "70000001-1")

    client = APIClient()
    client.force_authenticate(user=teacher)
    response = client.get("/api/v1/apoderado/mis-pupilos/")

    assert response.status_code == 403
    assert "perfil de apoderado" in response.json()["detail"].lower()


def test_apoderado_justificativo_without_photo_is_allowed():
    school = _mk_school(5008)
    guardian = _mk_user("apoderado-no-photo@test.cl", "Apoderado", school.rbd, "80000001-1")
    student = _mk_user("student-no-photo@test.cl", "Estudiante", school.rbd, "80000002-2")
    _mk_guardian_relation(guardian, student)

    client = APIClient()
    client.force_authenticate(user=guardian)
    response = client.post(
        "/api/v1/apoderado/justificativos/",
        {
            "estudiante_id": str(student.id),
            "fecha_ausencia": "2026-05-15",
            "motivo": "Tramite familiar",
            "tipo": "FAMILIAR",
        },
        format="multipart",
    )

    assert response.status_code == 201
    created = JustificativoInasistencia.objects.get(id_justificativo=response.json()["id_justificativo"])
    assert created.documento_adjunto.name in (None, "")


def test_apoderado_comunicados_filters_course_specific_by_active_enrollment():
    school = _mk_school(5009)
    guardian = _mk_user("apoderado-course-filter@test.cl", "Apoderado", school.rbd, "90000001-1")
    student = _mk_user("student-course-filter@test.cl", "Estudiante", school.rbd, "90000002-2")
    teacher = _mk_user("teacher-course-filter@test.cl", "Profesor", school.rbd, "90000003-3")
    _mk_guardian_relation(guardian, student)

    ciclo, curso_relacionado, _ = _mk_class_context(school, teacher)
    nivel_alt = NivelEducativo.objects.create(nombre="Nivel Alterno")
    curso_no_relacionado = Curso.objects.create(
        colegio=school,
        nombre="7B",
        nivel=nivel_alt,
        ciclo_academico=ciclo,
        activo=True,
    )

    Matricula.objects.create(
        estudiante=student,
        colegio=school,
        curso=curso_relacionado,
        ciclo_academico=ciclo,
        estado="ACTIVA",
    )

    comunicado_visible = Comunicado.objects.create(
        colegio=school,
        tipo="citacion",
        titulo="Visible curso",
        contenido="Debe aparecer",
        destinatario="curso_especifico",
        publicado_por=teacher,
        activo=True,
    )
    comunicado_visible.cursos_destinatarios.add(curso_relacionado)

    comunicado_no_visible = Comunicado.objects.create(
        colegio=school,
        tipo="citacion",
        titulo="No visible curso",
        contenido="No debe aparecer",
        destinatario="curso_especifico",
        publicado_por=teacher,
        activo=True,
    )
    comunicado_no_visible.cursos_destinatarios.add(curso_no_relacionado)

    client = APIClient()
    client.force_authenticate(user=guardian)
    response = client.get("/api/v1/apoderado/comunicados/")

    assert response.status_code == 200
    ids = {item["id_comunicado"] for item in response.json()}
    assert comunicado_visible.id_comunicado in ids
    assert comunicado_no_visible.id_comunicado not in ids

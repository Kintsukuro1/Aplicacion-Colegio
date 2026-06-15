from datetime import date

import pytest

from backend.apps.academico.services.attendance_service import AttendanceService
from backend.apps.accounts.models import PerfilProfesor, Role, User
from backend.apps.core.services.ciclo_academico_service import CicloAcademicoService
from backend.apps.core.services.clase_service import ClaseService
from backend.apps.core.services.curso_service import CursoService
from backend.apps.cursos.models import Asignatura, Curso
from backend.apps.institucion.models import (
    CicloAcademico,
    Colegio,
    Comuna,
    DependenciaAdministrativa,
    NivelEducativo,
    Region,
    TipoEstablecimiento,
)
from backend.apps.matriculas.services import MatriculaService


pytestmark = pytest.mark.django_db


def _create_school_bundle(*, rbd: int, suffix: str):
    region = Region.objects.create(nombre=f"Región {suffix}")
    comuna = Comuna.objects.create(nombre=f"Comuna {suffix}", region=region)
    tipo = TipoEstablecimiento.objects.create(nombre=f"Tipo {suffix}")
    dependencia = DependenciaAdministrativa.objects.create(nombre=f"Dependencia {suffix}")
    nivel = NivelEducativo.objects.create(nombre=f"Nivel {suffix}", activo=True)

    colegio = Colegio.objects.create(
        rbd=rbd,
        rut_establecimiento=f"{rbd}-K",
        nombre=f"Colegio {suffix}",
        direccion=f"Dirección {suffix}",
        comuna=comuna,
        tipo_establecimiento=tipo,
        dependencia=dependencia,
    )

    return {
        'colegio': colegio,
        'nivel': nivel,
    }


def _create_user(*, email: str, nombre: str, apellido: str, role_name: str, rbd: int, is_active: bool = True):
    role, _ = Role.objects.get_or_create(nombre=role_name)
    return User.objects.create(
        email=email,
        rut=None,
        nombre=nombre,
        apellido_paterno=apellido,
        role=role,
        rbd_colegio=rbd,
        is_active=is_active,
    )


def _create_ready_school_context(*, rbd: int, suffix: str):
    data = _create_school_bundle(rbd=rbd, suffix=suffix)
    colegio = data['colegio']

    admin = _create_user(
        email=f'admin_{suffix.lower()}@test.cl',
        nombre='Admin',
        apellido='School',
        role_name='Administrador escolar',
        rbd=colegio.rbd,
    )
    ciclo = CicloAcademico.objects.create(
        colegio=colegio,
        nombre=f'2026-{suffix}',
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 31),
        estado='ACTIVO',
        creado_por=admin,
        modificado_por=admin,
    )

    curso = Curso.objects.create(
        colegio=colegio,
        nombre=f'Curso {suffix}',
        nivel=data['nivel'],
        ciclo_academico=ciclo,
        activo=True,
    )

    asignatura = Asignatura.objects.create(
        colegio=colegio,
        nombre=f'Asignatura {suffix}',
        horas_semanales=5,
        activa=True,
    )

    profesor = _create_user(
        email=f'profesor_{suffix.lower()}@test.cl',
        nombre='Profesor',
        apellido='Activo',
        role_name='Profesor',
        rbd=colegio.rbd,
        is_active=True,
    )
    # PerfilProfesor is required by integrity check (_count_broken_relationships)
    PerfilProfesor.objects.create(user=profesor)

    estudiante = _create_user(
        email=f'estudiante_{suffix.lower()}@test.cl',
        nombre='Estudiante',
        apellido='Activo',
        role_name='Alumno',
        rbd=colegio.rbd,
        is_active=True,
    )

    return {
        'colegio': colegio,
        'admin': admin,
        'ciclo': ciclo,
        'curso': curso,
        'asignatura': asignatura,
        'profesor': profesor,
        'estudiante': estudiante,
        'nivel': data['nivel'],
    }


def test_minimo_crear_ciclo_academico():
    data = _create_school_bundle(rbd=91001, suffix='M1')
    colegio = data['colegio']

    admin = _create_user(
        email='admin_m1@test.cl',
        nombre='Admin',
        apellido='M1',
        role_name='Administrador escolar',
        rbd=colegio.rbd,
    )

    ciclo = CicloAcademicoService.create(
        user=admin,
        school_rbd=colegio.rbd,
        nombre='2026',
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 31),
        descripcion='Ciclo mínimo obligatorio',
        activate=True,
    )

    assert ciclo.id is not None
    assert ciclo.colegio_id == colegio.rbd


def test_minimo_crear_curso():
    data = _create_school_bundle(rbd=91011, suffix='M2')
    colegio = data['colegio']

    admin = _create_user(
        email='admin_m2@test.cl',
        nombre='Admin',
        apellido='M2',
        role_name='Administrador escolar',
        rbd=colegio.rbd,
    )
    CicloAcademico.objects.create(
        colegio=colegio,
        nombre='2026-M2',
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 31),
        estado='ACTIVO',
        creado_por=admin,
        modificado_por=admin,
    )

    curso = CursoService.create(
        user=admin,
        school_rbd=colegio.rbd,
        nombre='1° Básico A',
        nivel_id=data['nivel'].id_nivel,
    )

    assert curso.id_curso is not None
    assert curso.colegio_id == colegio.rbd


def test_minimo_crear_clase():
    ctx = _create_ready_school_context(rbd=91021, suffix='M3')

    clase = ClaseService.create(
        school_rbd=ctx['colegio'].rbd,
        curso_id=ctx['curso'].id_curso,
        asignatura_id=ctx['asignatura'].id_asignatura,
        profesor_id=ctx['profesor'].id,
    )

    assert clase.id is not None
    assert clase.colegio_id == ctx['colegio'].rbd


def test_minimo_matricular_estudiante():
    ctx = _create_ready_school_context(rbd=91031, suffix='M4')

    matricula = MatriculaService.create(
        actor=ctx['admin'],
        estudiante_id=ctx['estudiante'].id,
        colegio_rbd=ctx['colegio'].rbd,
        curso_id=ctx['curso'].id_curso,
        ciclo_academico_id=ctx['ciclo'].id,
        valor_matricula=1000,
        valor_mensual=2000,
    )

    assert matricula.id is not None
    assert matricula.estudiante_id == ctx['estudiante'].id
    assert matricula.colegio_id == ctx['colegio'].rbd


def test_minimo_registrar_asistencia():
    ctx = _create_ready_school_context(rbd=91041, suffix='M5')
    clase = ClaseService.create(
        school_rbd=ctx['colegio'].rbd,
        curso_id=ctx['curso'].id_curso,
        asignatura_id=ctx['asignatura'].id_asignatura,
        profesor_id=ctx['profesor'].id,
    )

    asistencia = AttendanceService.create({
        'colegio': ctx['colegio'],
        'clase': clase,
        'estudiante': ctx['estudiante'],
        'fecha': date(2026, 4, 1),
        'estado': AttendanceService.PRESENTE,
        'tipo_asistencia': 'Presencial',
    })

    assert asistencia.id_asistencia is not None
    assert asistencia.colegio_id == ctx['colegio'].rbd
    assert asistencia.estudiante_id == ctx['estudiante'].id
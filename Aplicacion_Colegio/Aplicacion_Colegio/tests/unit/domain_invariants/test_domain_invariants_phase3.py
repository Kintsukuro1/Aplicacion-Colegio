"""Fase 3 - Tests de invariantes de dominio (bloque inicial)."""

from datetime import date

import pytest

from backend.apps.accounts.models import Role, User
from backend.apps.core.services.ciclo_academico_service import CicloAcademicoService
from backend.apps.core.services.clase_service import ClaseService
from backend.apps.core.services.curso_service import CursoService
from backend.apps.institucion.models import (
    CicloAcademico,
    Colegio,
    Comuna,
    DependenciaAdministrativa,
    NivelEducativo,
    Region,
    TipoEstablecimiento,
)
from backend.apps.cursos.models import Asignatura, Curso
from backend.apps.matriculas.models import Matricula
from backend.apps.matriculas.services import MatriculaService
from backend.common.exceptions import PrerequisiteException


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


def _create_active_cycle(*, colegio, admin_user, nombre: str = '2026'):
    return CicloAcademico.objects.create(
        colegio=colegio,
        nombre=nombre,
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 31),
        estado='ACTIVO',
        creado_por=admin_user,
        modificado_por=admin_user,
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
    ciclo = _create_active_cycle(colegio=colegio, admin_user=admin, nombre=f'2026-{suffix}')

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


def test_no_permitir_crear_curso_sin_ciclo_activo():
    data = _create_school_bundle(rbd=90001, suffix='T1')
    colegio = data['colegio']
    nivel = data['nivel']
    admin = _create_user(
        email='admin_t1@test.cl',
        nombre='Admin',
        apellido='Uno',
        role_name='Administrador escolar',
        rbd=colegio.rbd,
    )

    with pytest.raises(PrerequisiteException) as exc_info:
        CursoService.create(
            user=admin,
            school_rbd=colegio.rbd,
            nombre='1° Básico A',
            nivel_id=nivel.id_nivel,
        )

    assert exc_info.value.error_type == 'MISSING_CICLO_ACTIVO'


def test_no_permitir_matricula_cross_school():
    school_a = _create_school_bundle(rbd=90011, suffix='A')
    school_b = _create_school_bundle(rbd=90012, suffix='B')

    admin_b = _create_user(
        email='admin_b@test.cl',
        nombre='Admin',
        apellido='B',
        role_name='Administrador escolar',
        rbd=school_b['colegio'].rbd,
    )
    _create_active_cycle(colegio=school_b['colegio'], admin_user=admin_b, nombre='2026-B')

    curso_b = Curso.objects.create(
        colegio=school_b['colegio'],
        nombre='2° Básico B',
        nivel=school_b['nivel'],
        ciclo_academico=CicloAcademico.objects.get(colegio=school_b['colegio'], estado='ACTIVO'),
        activo=True,
    )

    estudiante_a = _create_user(
        email='estudiante_a@test.cl',
        nombre='Estudiante',
        apellido='A',
        role_name='Alumno',
        rbd=school_a['colegio'].rbd,
    )

    with pytest.raises(PrerequisiteException) as exc_info:
        MatriculaService.create(
            actor=admin_b,
            estudiante_id=estudiante_a.id,
            colegio_rbd=school_b['colegio'].rbd,
            curso_id=curso_b.id_curso,
            ciclo_academico_id=curso_b.ciclo_academico_id,
            valor_matricula=1000,
            valor_mensual=2000,
        )

    assert exc_info.value.error_type == 'INVALID_RELATIONSHIP'


def test_no_permitir_clase_sin_profesor_valido():
    data = _create_school_bundle(rbd=90021, suffix='T3')
    colegio = data['colegio']

    admin = _create_user(
        email='admin_t3@test.cl',
        nombre='Admin',
        apellido='Tres',
        role_name='Administrador escolar',
        rbd=colegio.rbd,
    )
    ciclo = _create_active_cycle(colegio=colegio, admin_user=admin, nombre='2026-T3')

    curso = Curso.objects.create(
        colegio=colegio,
        nombre='3° Básico A',
        nivel=data['nivel'],
        ciclo_academico=ciclo,
        activo=True,
    )
    asignatura = Asignatura.objects.create(
        colegio=colegio,
        nombre='Lenguaje',
        horas_semanales=6,
        activa=True,
    )

    profesor_inactivo = _create_user(
        email='profesor_inactivo@test.cl',
        nombre='Profesor',
        apellido='Inactivo',
        role_name='Profesor',
        rbd=colegio.rbd,
        is_active=False,
    )

    with pytest.raises(User.DoesNotExist):
        ClaseService.create(
            school_rbd=colegio.rbd,
            curso_id=curso.id_curso,
            asignatura_id=asignatura.id_asignatura,
            profesor_id=profesor_inactivo.id,
        )


def test_no_permitir_operaciones_sin_setup_completo():
    data = _create_school_bundle(rbd=90031, suffix='T4')
    colegio = data['colegio']

    with pytest.raises(PrerequisiteException) as exc_info:
        ClaseService.create(
            school_rbd=colegio.rbd,
            curso_id=999999,
            asignatura_id=999999,
            profesor_id=999999,
        )

    assert exc_info.value.error_type == 'DATA_INCONSISTENCY'


def test_no_permitir_doble_matricula_activa_mismo_ciclo():
    ctx = _create_ready_school_context(rbd=90041, suffix='T5')

    MatriculaService.create(
        actor=ctx['admin'],
        estudiante_id=ctx['estudiante'].id,
        colegio_rbd=ctx['colegio'].rbd,
        curso_id=ctx['curso'].id_curso,
        ciclo_academico_id=ctx['ciclo'].id,
    )

    curso_2 = Curso.objects.create(
        colegio=ctx['colegio'],
        nombre='Curso T5-B',
        nivel=ctx['nivel'],
        ciclo_academico=ctx['ciclo'],
        activo=True,
    )

    with pytest.raises(PrerequisiteException) as exc_info:
        MatriculaService.create(
            actor=ctx['admin'],
            estudiante_id=ctx['estudiante'].id,
            colegio_rbd=ctx['colegio'].rbd,
            curso_id=curso_2.id_curso,
            ciclo_academico_id=ctx['ciclo'].id,
        )

    assert exc_info.value.error_type == 'DUPLICATE_ACTIVE_MATRICULA'


def test_no_permitir_eliminar_matricula_activa():
    ctx = _create_ready_school_context(rbd=90051, suffix='T6')

    matricula = MatriculaService.create(
        actor=ctx['admin'],
        estudiante_id=ctx['estudiante'].id,
        colegio_rbd=ctx['colegio'].rbd,
        curso_id=ctx['curso'].id_curso,
        ciclo_academico_id=ctx['ciclo'].id,
    )

    with pytest.raises(PrerequisiteException) as exc_info:
        MatriculaService.delete(actor=ctx['admin'], matricula_id=matricula.id)

    assert exc_info.value.error_type == 'INVALID_STATE'


def test_permitir_eliminar_matricula_no_activa():
    ctx = _create_ready_school_context(rbd=90061, suffix='T7')

    matricula = MatriculaService.create(
        actor=ctx['admin'],
        estudiante_id=ctx['estudiante'].id,
        colegio_rbd=ctx['colegio'].rbd,
        curso_id=ctx['curso'].id_curso,
        ciclo_academico_id=ctx['ciclo'].id,
    )
    MatriculaService.change_status(actor=ctx['admin'], matricula_id=matricula.id, new_status='FINALIZADA')
    MatriculaService.delete(actor=ctx['admin'], matricula_id=matricula.id)

    assert not Matricula.objects.filter(id=matricula.id).exists()


def test_no_permitir_reactivar_matricula_si_ya_hay_otra_activa():
    ctx = _create_ready_school_context(rbd=90071, suffix='T8')

    matricula_activa = MatriculaService.create(
        actor=ctx['admin'],
        estudiante_id=ctx['estudiante'].id,
        colegio_rbd=ctx['colegio'].rbd,
        curso_id=ctx['curso'].id_curso,
        ciclo_academico_id=ctx['ciclo'].id,
    )

    curso_2 = Curso.objects.create(
        colegio=ctx['colegio'],
        nombre='Curso T8-B',
        nivel=ctx['nivel'],
        ciclo_academico=ctx['ciclo'],
        activo=True,
    )
    matricula_finalizada = Matricula.objects.create(
        estudiante=ctx['estudiante'],
        colegio=ctx['colegio'],
        curso=curso_2,
        ciclo_academico=ctx['ciclo'],
        estado='FINALIZADA',
    )

    with pytest.raises(PrerequisiteException) as exc_info:
        MatriculaService.change_status(
            actor=ctx['admin'],
            matricula_id=matricula_finalizada.id,
            new_status='ACTIVA',
        )

    assert Matricula.objects.filter(id=matricula_activa.id, estado='ACTIVA').exists()
    assert exc_info.value.error_type == 'DUPLICATE_ACTIVE_MATRICULA'


def test_no_permitir_clase_con_curso_inactivo():
    ctx = _create_ready_school_context(rbd=90081, suffix='T9')
    ctx['curso'].activo = False
    ctx['curso'].save(update_fields=['activo'])

    with pytest.raises(Curso.DoesNotExist):
        ClaseService.create(
            school_rbd=ctx['colegio'].rbd,
            curso_id=ctx['curso'].id_curso,
            asignatura_id=ctx['asignatura'].id_asignatura,
            profesor_id=ctx['profesor'].id,
        )


def test_no_permitir_clase_con_asignatura_inactiva():
    ctx = _create_ready_school_context(rbd=90091, suffix='T10')
    ctx['asignatura'].activa = False
    ctx['asignatura'].save(update_fields=['activa'])

    with pytest.raises(Asignatura.DoesNotExist):
        ClaseService.create(
            school_rbd=ctx['colegio'].rbd,
            curso_id=ctx['curso'].id_curso,
            asignatura_id=ctx['asignatura'].id_asignatura,
            profesor_id=ctx['profesor'].id,
        )


def test_no_permitir_eliminar_ciclo_activo_desde_servicio():
    ctx = _create_ready_school_context(rbd=90101, suffix='T11')

    with pytest.raises(ValueError, match='ciclo activo'):
        CicloAcademicoService.delete(
            user=ctx['admin'],
            school_rbd=ctx['colegio'].rbd,
            ciclo_id=ctx['ciclo'].id,
        )


def test_activar_ciclo_desactiva_ciclo_activo_previo():
    ctx = _create_ready_school_context(rbd=90111, suffix='T12')
    ciclo_plan = CicloAcademico.objects.create(
        colegio=ctx['colegio'],
        nombre='2027-T12',
        fecha_inicio=date(2027, 3, 1),
        fecha_fin=date(2027, 12, 31),
        estado='PLANIFICACION',
        creado_por=ctx['admin'],
        modificado_por=ctx['admin'],
    )

    CicloAcademicoService.activate(
        user=ctx['admin'],
        school_rbd=ctx['colegio'].rbd,
        ciclo_id=ciclo_plan.id,
    )

    ctx['ciclo'].refresh_from_db()
    ciclo_plan.refresh_from_db()

    assert ctx['ciclo'].estado == 'PLANIFICACION'
    assert ciclo_plan.estado == 'ACTIVO'

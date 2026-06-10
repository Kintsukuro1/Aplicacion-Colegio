"""Functional validations for dashboard data wiring (fase7, schema-aligned)."""

import pytest
from datetime import date, timedelta

from backend.apps.accounts.models import PerfilEstudiante, Role, User
from backend.apps.cursos.models import Asignatura, Clase, Curso
from backend.apps.institucion.models import (
    CicloAcademico,
    Colegio,
    Comuna,
    DependenciaAdministrativa,
    NivelEducativo,
    Region,
    TipoEstablecimiento,
)
from backend.apps.matriculas.models import Matricula


@pytest.fixture
def base_school_data(db):
    role_profesor = Role.objects.create(nombre='Profesor')
    role_estudiante = Role.objects.create(nombre='Alumno')
    role_admin = Role.objects.create(nombre='Administrador Escolar')

    region = Region.objects.create(nombre='Region F7')
    comuna = Comuna.objects.create(nombre='Comuna F7', region=region)
    tipo = TipoEstablecimiento.objects.create(nombre='Tipo F7')
    dependencia = DependenciaAdministrativa.objects.create(nombre='Dependencia F7')

    colegio = Colegio.objects.create(
        rbd=55667,
        rut_establecimiento='76000777-3',
        nombre='Colegio Fase7',
        direccion='Direccion F7',
        comuna=comuna,
        tipo_establecimiento=tipo,
        dependencia=dependencia,
    )

    admin = User.objects.create_user(
        email='admin.f7@test.cl',
        password='AdminF7Pass123!',
        nombre='Admin',
        apellido_paterno='F7',
        rut='12121212-1',
        role=role_admin,
        rbd_colegio=colegio.rbd,
    )

    ciclo = CicloAcademico.objects.create(
        colegio=colegio,
        nombre='2026',
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=365),
        estado='ACTIVO',
        creado_por=admin,
        modificado_por=admin,
    )

    nivel = NivelEducativo.objects.create(nombre='Básica F7')
    curso = Curso.objects.create(
        nombre='1° Básico A',
        colegio=colegio,
        ciclo_academico=ciclo,
        nivel=nivel,
        activo=True,
    )

    asignatura = Asignatura.objects.create(nombre='Matemáticas F7', colegio=colegio)

    return {
        'colegio': colegio,
        'admin': admin,
        'ciclo': ciclo,
        'curso': curso,
        'asignatura': asignatura,
        'role_profesor': role_profesor,
        'role_estudiante': role_estudiante,
    }


@pytest.mark.django_db
class TestDashboardFase7Validation:
    def test_clase_creation_without_legacy_nombre_field(self, base_school_data):
        data = base_school_data
        profesor = User.objects.create_user(
            email='prof.f7@test.cl',
            password='ProfF7Pass123!',
            nombre='Profe',
            apellido_paterno='F7',
            rut='13131313-2',
            role=data['role_profesor'],
            rbd_colegio=data['colegio'].rbd,
        )

        clase = Clase.objects.create(
            colegio=data['colegio'],
            curso=data['curso'],
            asignatura=data['asignatura'],
            profesor=profesor,
            activo=True,
        )

        assert clase.id is not None
        assert clase.profesor == profesor

    def test_perfil_estudiante_uses_ciclo_actual_and_matricula_for_curso_actual(self, base_school_data):
        data = base_school_data
        estudiante = User.objects.create_user(
            email='estu.f7@test.cl',
            password='EstuF7Pass123!',
            nombre='Estu',
            apellido_paterno='F7',
            rut='14141414-3',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd,
        )

        perfil = PerfilEstudiante.objects.create(
            user=estudiante,
            ciclo_actual=data['ciclo'],
            estado_academico='Activo',
        )

        Matricula.objects.create(
            estudiante=estudiante,
            colegio=data['colegio'],
            curso=data['curso'],
            ciclo_academico=data['ciclo'],
            estado='ACTIVA',
        )

        assert perfil.ciclo_actual == data['ciclo']
        assert perfil.curso_actual == data['curso']

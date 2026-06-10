"""Tests defensivos del contrato público MatriculaService en matrículas."""

from datetime import date
from unittest.mock import patch

from tests.common.test_base import BaseTestCase
from backend.common.exceptions import PrerequisiteException
from backend.apps.accounts.models import PerfilEstudiante
from backend.apps.accounts.models import User
from backend.apps.institucion.models import (
    CicloAcademico,
    NivelEducativo,
    Colegio,
    Region,
    Comuna,
    TipoEstablecimiento,
    DependenciaAdministrativa,
)
from backend.apps.cursos.models import Curso
from backend.apps.matriculas.models import Matricula
from backend.apps.matriculas.services import MatriculaService
from backend.apps.matriculas.services.matriculas_service import MatriculasService


class TestMatriculaDefensiveValidations(BaseTestCase):
    """Cobertura mínima de validaciones defensivas del contrato público."""

    def setUp(self):
        super().setUp()
        region = Region.objects.get_or_create(nombre='Región Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(nombre='Santiago', defaults={'region': region})[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Liceo')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]
        self.colegio = Colegio.objects.get_or_create(
            rbd=12345,
            defaults={
                'rut_establecimiento': '12345678-9',
                'nombre': 'Colegio Test',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia,
            },
        )[0]

        self.admin_user = self.crear_usuario_admin()

        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 20),
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        self.ciclo_cerrado = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 20),
            estado='CERRADO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        self.nivel = NivelEducativo.objects.get_or_create(nombre='Enseñanza Media')[0]
        self.curso = Curso.objects.create(
            colegio=self.colegio,
            nivel=self.nivel,
            nombre='Primero A',
            ciclo_academico=self.ciclo_activo,
            activo=True,
        )

    def test_validate_student_profile_success(self):
        estudiante, perfil = self.crear_usuario_estudiante(email='juan@test.cl')
        perfil.ciclo_actual = self.ciclo_activo
        perfil.save()

        MatriculasService._validate_student_profile(estudiante)

    def test_validate_student_profile_missing_raises(self):
        estudiante = self.crear_usuario_profesor(email='sinperfil@test.cl')
        with self.assertRaises(PrerequisiteException):
            MatriculasService._validate_student_profile(estudiante)

    def test_validate_colegio_has_active_ciclo_success(self):
        ciclo = MatriculasService._validate_colegio_has_active_ciclo(self.colegio.rbd)
        self.assertIsNotNone(ciclo)
        self.assertEqual(ciclo.estado, 'ACTIVO')

    def test_validate_colegio_not_found_raises(self):
        with self.assertRaises(PrerequisiteException):
            MatriculasService._validate_colegio_has_active_ciclo(99999)

    def test_validate_colegio_no_active_ciclo_raises(self):
        self.ciclo_activo.estado = 'CERRADO'
        self.ciclo_activo.save()
        with self.assertRaises(PrerequisiteException):
            MatriculasService._validate_colegio_has_active_ciclo(self.colegio.rbd)

    @patch.object(MatriculasService, '_validate_school_integrity', return_value=None)
    def test_get_active_matricula_without_profile_raises(self, _):
        estudiante = User.objects.create_user(
            email='sinperfil2@test.cl',
            password='test123',
            nombre='Sin',
            apellido_paterno='Perfil',
            role=self.rol_estudiante,
            rbd_colegio=self.colegio.rbd,
        )
        with self.assertRaises(PrerequisiteException):
            MatriculaService.get_active_matricula_for_user(estudiante, self.colegio.rbd)

    @patch.object(MatriculasService, '_validate_school_integrity', return_value=None)
    def test_get_active_matricula_without_active_ciclo_raises(self, _):
        estudiante, perfil = self.crear_usuario_estudiante(email='juan2@test.cl')
        perfil.ciclo_actual = self.ciclo_activo
        perfil.save()

        self.ciclo_activo.estado = 'CERRADO'
        self.ciclo_activo.save()

        with self.assertRaises(PrerequisiteException):
            MatriculaService.get_active_matricula_for_user(estudiante, self.colegio.rbd)

    @patch.object(MatriculasService, '_validate_school_integrity', return_value=None)
    def test_get_active_matricula_success(self, _):
        estudiante, perfil = self.crear_usuario_estudiante(email='juan3@test.cl')
        perfil.ciclo_actual = self.ciclo_activo
        perfil.save()

        matricula_obj = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            estado='ACTIVA',
        )

        matricula = MatriculaService.get_active_matricula_for_user(estudiante, self.colegio.rbd)
        self.assertIsNotNone(matricula)
        self.assertEqual(matricula.pk, matricula_obj.pk)

    @patch.object(MatriculasService, '_validate_school_integrity', return_value=None)
    def test_get_estado_cuenta_validates_profile(self, _):
        estudiante = User.objects.create_user(
            email='sinperfil3@test.cl',
            password='test123',
            nombre='Sin',
            apellido_paterno='Perfil',
            role=self.rol_estudiante,
            rbd_colegio=self.colegio.rbd,
        )
        result = MatriculaService.get_estado_cuenta_data(estudiante, None)
        self.assertIn('error', result)

    @patch.object(MatriculasService, '_validate_school_integrity', return_value=None)
    def test_get_estado_cuenta_validates_ciclo(self, _):
        estudiante, perfil = self.crear_usuario_estudiante(email='juan4@test.cl')
        perfil.ciclo_actual = self.ciclo_activo
        perfil.save()

        self.ciclo_activo.estado = 'CERRADO'
        self.ciclo_activo.save()

        result = MatriculaService.get_estado_cuenta_data(estudiante, None)
        self.assertIn('error', result)

    @patch.object(MatriculasService, '_validate_school_integrity', return_value=None)
    def test_get_pagos_filters_by_active_ciclo(self, _):
        estudiante, perfil = self.crear_usuario_estudiante(email='juan5@test.cl')
        estudiante.rbd_colegio = self.colegio.rbd
        estudiante.save()
        perfil.ciclo_actual = self.ciclo_activo
        perfil.save()

        Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            estado='ACTIVA',
        )

        result = MatriculaService.get_pagos_data(estudiante, None)
        self.assertNotIn('error', result)
        self.assertIn('pagos', result)

    @patch.object(MatriculasService, '_validate_school_integrity', return_value=None)
    def test_get_pagos_validates_profile(self, _):
        estudiante = User.objects.create_user(
            email='sinperfil4@test.cl',
            password='test123',
            nombre='Sin',
            apellido_paterno='Perfil',
            role=self.rol_estudiante,
            rbd_colegio=self.colegio.rbd,
        )
        result = MatriculaService.get_pagos_data(estudiante, None)
        self.assertIn('error', result)

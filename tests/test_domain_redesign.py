"""
Tests de baseline para el rediseño de dominio.

Objetivo:
- Verificar reglas críticas vigentes en modelos actuales.
- Mantener compatibilidad con esquema real del proyecto.
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from backend.apps.accounts.models import User
from backend.apps.cursos.models import Curso
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


class DomainBaseMixin:
    def create_colegio(self, rbd=12345, nombre="Colegio Test"):
        region = Region.objects.create(nombre=f"Región {rbd}")
        comuna = Comuna.objects.create(nombre=f"Comuna {rbd}", region=region)
        tipo = TipoEstablecimiento.objects.create(nombre=f"Municipal {rbd}")
        dependencia = DependenciaAdministrativa.objects.create(nombre=f"DAEM {rbd}")

        return Colegio.objects.create(
            rbd=rbd,
            rut_establecimiento=f"76{rbd:06d}-K",
            nombre=nombre,
            comuna=comuna,
            tipo_establecimiento=tipo,
            dependencia=dependencia,
        )

    def create_user(self, email, nombre="Nombre", apellido="Apellido", **extra):
        return User.objects.create_user(
            email=email,
            password="test123",
            nombre=nombre,
            apellido_paterno=apellido,
            **extra,
        )


class CicloAcademicoTestCase(DomainBaseMixin, TestCase):
    def setUp(self):
        self.colegio = self.create_colegio(rbd=12345)
        self.admin_user = self.create_user("admin@test.com", nombre="Admin", apellido="Sistema")

    def test_creacion_ciclo_academico_valido(self):
        ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre="2024-2025",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        self.assertEqual(ciclo.estado, "PLANIFICACION")
        self.assertFalse(ciclo.esta_activo())

    def test_ciclo_fechas_invalidas(self):
        ciclo = CicloAcademico(
            colegio=self.colegio,
            nombre="2024-2025",
            fecha_inicio=date(2024, 12, 31),
            fecha_fin=date(2024, 3, 1),
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        with self.assertRaises(ValidationError):
            ciclo.full_clean()

    def test_ciclo_solapado(self):
        CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre="2024-2025",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        solapado = CicloAcademico(
            colegio=self.colegio,
            nombre="2025-A",
            fecha_inicio=date(2024, 6, 1),
            fecha_fin=date(2025, 2, 28),
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        with self.assertRaises(ValidationError):
            solapado.full_clean()

    def test_transicion_estado(self):
        ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre="2024-2025",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        self.assertTrue(ciclo.puede_transitar_a("ACTIVO"))
        self.assertFalse(ciclo.puede_transitar_a("CERRADO"))

        ciclo.transitar_estado("ACTIVO", self.admin_user)
        ciclo.refresh_from_db()
        self.assertEqual(ciclo.estado, "ACTIVO")


class MatriculaRulesTestCase(DomainBaseMixin, TestCase):
    def setUp(self):
        self.colegio = self.create_colegio(rbd=99999, nombre="Colegio Integración")
        self.admin_user = self.create_user("admin.integracion@test.com", nombre="Admin", apellido="Integración")
        self.estudiante = self.create_user(
            "estudiante@test.com",
            nombre="Estudiante",
            apellido="Prueba",
            rbd_colegio=self.colegio.rbd,
        )

        self.ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre="2024-2025",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            estado="ACTIVO",
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        nivel = NivelEducativo.objects.create(nombre=f"Básica {self.colegio.rbd}")
        self.curso = Curso.objects.create(
            colegio=self.colegio,
            nombre="1° Básico A",
            nivel=nivel,
            ciclo_academico=self.ciclo,
            activo=True,
        )

    def test_flujo_basico_matricula_valida(self):
        matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado="ACTIVA",
            fecha_inicio=self.ciclo.fecha_inicio,
            valor_matricula=0,
            valor_mensual=0,
        )

        self.assertEqual(matricula.estado, "ACTIVA")
        self.assertEqual(matricula.colegio_id, self.colegio.rbd)

    def test_no_permite_doble_matricula_activa_mismo_ciclo(self):
        Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado="ACTIVA",
            fecha_inicio=self.ciclo.fecha_inicio,
            valor_matricula=0,
            valor_mensual=0,
        )

        with self.assertRaises(Exception):
            Matricula.objects.create(
                estudiante=self.estudiante,
                colegio=self.colegio,
                curso=self.curso,
                ciclo_academico=self.ciclo,
                estado="ACTIVA",
                fecha_inicio=self.ciclo.fecha_inicio,
                valor_matricula=0,
                valor_mensual=0,
            )

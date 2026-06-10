"""Tests unitarios del contrato público MatriculaService en dominio matrículas."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from tests.common.test_base import BaseTestCase
from backend.apps.matriculas.services import MatriculaService
from backend.apps.matriculas.services.matriculas_service import MatriculasService
from backend.apps.matriculas.models import Matricula, Cuota, Pago
from backend.apps.accounts.models import Apoderado, RelacionApoderadoEstudiante
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


class TestMatriculaServicePermissions(BaseTestCase):
    """Smoke tests de acceso para el contrato público de matrículas."""

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

        self.super_admin = self.crear_usuario_super_admin()
        self.admin_escolar = self.crear_usuario_admin()
        self.asesor = self.crear_usuario_asesor()
        self.estudiante, _ = self.crear_usuario_estudiante()
        self.apoderado = self.crear_usuario_apoderado()

        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2026',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            estado='ACTIVO',
            creado_por=self.admin_escolar,
            modificado_por=self.admin_escolar,
        )

    def test_admin_can_view_enrollment_data(self):
        """Admin puede invocar la operación sin error de permisos."""
        with patch.object(MatriculasService, '_validate_student_profile', return_value=None), \
               patch.object(MatriculasService, '_validate_colegio_has_active_ciclo', return_value=self.ciclo_activo), \
             patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_active_matricula_for_user(self.admin_escolar, self.colegio.rbd)
            self.assertIsNone(result)

    def test_asesor_can_view_financial_data(self):
        """Asesor retorna respuesta estructurada (sin excepción inesperada)."""
        result = MatriculaService.get_estado_cuenta_data(self.asesor)
        self.assertIsInstance(result, dict)

    def test_student_can_view_own_financial_data(self):
        """Estudiante puede consultar su estado de cuenta."""
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save()
        result = MatriculaService.get_estado_cuenta_data(self.estudiante)
        self.assertIsInstance(result, dict)

    def test_apoderado_can_view_financial_data(self):
        """Apoderado puede consultar datos financieros."""
        self.apoderado.rbd_colegio = self.colegio.rbd
        self.apoderado.save()
        result = MatriculaService.get_estado_cuenta_data(self.apoderado)
        self.assertIsInstance(result, dict)

    def test_apoderado_can_view_enrollments(self):
        """Apoderado puede invocar consulta de matrículas."""
        self.apoderado.rbd_colegio = self.colegio.rbd
        self.apoderado.save()

        with patch.object(MatriculasService, '_validate_student_profile', return_value=None), \
               patch.object(MatriculasService, '_validate_colegio_has_active_ciclo', return_value=self.ciclo_activo), \
             patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_active_matricula_for_user(self.apoderado, self.colegio.rbd)
            self.assertIsNone(result)

    def test_student_can_view_enrollments(self):
        """Estudiante puede invocar consulta de matrículas."""
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save()

        with patch.object(MatriculasService, '_validate_student_profile', return_value=None), \
               patch.object(MatriculasService, '_validate_colegio_has_active_ciclo', return_value=self.ciclo_activo), \
             patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_active_matricula_for_user(self.estudiante, self.colegio.rbd)
            self.assertIsNone(result)


class TestMatriculaServiceBusinessLogic(BaseTestCase):
    """Lógica de negocio sobre el contrato público y respuestas defensivas."""

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
        self.estudiante, _ = self.crear_usuario_estudiante()
        self.apoderado = self.crear_usuario_apoderado()

        self.ciclo_academico = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre="Año 2024",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

    def test_get_active_matricula_for_user_no_enrollment(self):
        """Sin matrícula activa retorna None."""
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save()

        with patch.object(MatriculasService, '_validate_colegio_has_active_ciclo', return_value=self.ciclo_academico), \
             patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_active_matricula_for_user(self.estudiante, self.colegio.rbd)
        self.assertIsNone(result)

    def test_get_apoderado_estudiantes_no_apoderado_profile(self):
        """get_apoderado_estudiantes should return None when user has no apoderado profile"""
        apoderado, estudiantes = MatriculaService.get_apoderado_estudiantes(self.apoderado)
        self.assertIsNone(apoderado)
        self.assertEqual(estudiantes, [])

    def test_apoderado_puede_ver_estudiante_no_relation(self):
        """Sin relación activa, no puede ver estudiante."""
        # Create apoderado profile
        apoderado_profile = Apoderado.objects.create(
            user=self.apoderado,
            telefono="+56912345678"
        )

        result = MatriculaService.apoderado_puede_ver_estudiante(apoderado_profile, self.estudiante)
        self.assertFalse(result)

    def test_get_estado_cuenta_data_no_enrollment(self):
        """Sin matrícula activa retorna error estructurado."""
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save()

        with patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_estado_cuenta_data(self.estudiante)
        self.assertIn('error', result)
        self.assertIn('matrícula activa', result['error'].lower())

    def test_get_pagos_data_no_enrollment(self):
        """Sin pagos retorna estructura válida y total 0."""
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save()

        with patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_pagos_data(self.estudiante)
        self.assertIn('pagos', result)
        self.assertIn('total_pagado', result)
        self.assertEqual(result['total_pagado'], 0)
        self.assertEqual(len(result['pagos']), 0)


class TestMatriculaServiceIntegration(BaseTestCase):
    """Integración mínima del contrato público con modelos reales."""

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
        self.estudiante, _ = self.crear_usuario_estudiante()
        self.apoderado = self.crear_usuario_apoderado()

        self.ciclo_academico = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre="Año 2024",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user,
        )

        nivel = NivelEducativo.objects.get_or_create(nombre='Básica')[0]
        self.curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_academico,
            nombre="1° Básico A",
            nivel=nivel,
            activo=True,
        )

        # Create matricula
        self.matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_academico,
            curso=self.curso,
            estado='ACTIVA',
        )

        # Create cuotas
        self.cuota1 = Cuota.objects.create(
            matricula=self.matricula,
            numero_cuota=1,
            anio=2024,
            mes=3,
            monto_original=Decimal('50000.00'),
            monto_descuento=Decimal('5000.00'),
            monto_final=Decimal('45000.00'),
            fecha_vencimiento=date(2024, 3, 15),
            estado='PENDIENTE'
        )

        self.cuota2 = Cuota.objects.create(
            matricula=self.matricula,
            numero_cuota=2,
            anio=2024,
            mes=4,
            monto_original=Decimal('50000.00'),
            monto_descuento=Decimal('0.00'),
            monto_final=Decimal('50000.00'),
            fecha_vencimiento=date(2024, 4, 15),
            estado='PAGADA',
            monto_pagado=Decimal('50000.00')
        )

        # Create pago
        self.pago = Pago.objects.create(
            estudiante=self.estudiante,
            cuota=self.cuota2,
            monto=Decimal('50000.00'),
            fecha_pago=timezone.make_aware(datetime(2024, 4, 15, 0, 0)),
            metodo_pago='TRANSFERENCIA',
            estado='APROBADO'
        )

    def test_get_active_matricula_for_user_with_enrollment(self):
        """Retorna matrícula activa en ciclo actual."""
        with patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_active_matricula_for_user(self.estudiante, self.colegio.rbd)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.matricula.id)
        self.assertEqual(result.estado, 'ACTIVA')

    def test_get_estado_cuenta_data_with_data(self):
        """Estado de cuenta calcula totales correctamente."""
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save()

        with patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_estado_cuenta_data(self.estudiante)

        self.assertNotIn('error', result)
        self.assertEqual(result['matricula'].id, self.matricula.id)
        self.assertEqual(result['totales']['total_arancel'], Decimal('100000.00'))  # 50000 + 50000
        self.assertEqual(result['totales']['total_descuentos'], Decimal('5000.00'))  # 5000 + 0
        self.assertEqual(result['totales']['total_a_pagar'], Decimal('95000.00'))  # 45000 + 50000
        self.assertEqual(result['totales']['total_pagado'], Decimal('50000.00'))  # Only cuota2 is paid
        self.assertEqual(result['totales']['saldo_pendiente'], Decimal('45000.00'))  # 95000 - 50000

    def test_get_pagos_data_with_data(self):
        """Historial de pagos retorna pagos del ciclo activo."""
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save()

        with patch.object(MatriculasService, '_validate_school_integrity', return_value=None):
            result = MatriculaService.get_pagos_data(self.estudiante)

        self.assertNotIn('error', result)
        self.assertEqual(result['pagos'].count(), 1)
        self.assertEqual(result['pagos'].first().id, self.pago.id)
        self.assertEqual(result['total_pagado'], Decimal('50000.00'))

    def test_apoderado_integration_with_relation(self):
        """Relación apoderado-estudiante habilita visibilidad."""
        # Create apoderado profile
        apoderado_profile = Apoderado.objects.create(
            user=self.apoderado,
            telefono="+56912345678"
        )

        # Create relation
        relacion = RelacionApoderadoEstudiante.objects.create(
            apoderado=apoderado_profile,
            estudiante=self.estudiante,
            parentesco="PADRE",
            prioridad_contacto=1,
            activa=True
        )

        apoderado_result, estudiantes = MatriculaService.get_apoderado_estudiantes(self.apoderado)
        self.assertIsNotNone(apoderado_result)
        self.assertEqual(len(estudiantes), 1)
        self.assertEqual(estudiantes[0].id, self.estudiante.id)

        puede_ver = MatriculaService.apoderado_puede_ver_estudiante(apoderado_profile, self.estudiante)
        self.assertTrue(puede_ver)

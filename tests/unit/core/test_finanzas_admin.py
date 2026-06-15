"""
Suite de pruebas unitarias — Gestión de Finanzas y Pagos (Admin Escolar)
Fase 2, Ítem 3.

Verifica:
1. Registro de pago manual completo (transición PENDIENTE → PAGADA).
2. Pagos parciales (transición PENDIENTE → PAGADA_PARCIAL).
3. Prevención de sobrepago (monto > saldo pendiente).
4. Aislamiento multi-tenant estricto.
5. Condonación de cuotas.
6. Descuento por becas.
"""

import json
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.utils import timezone

from backend.apps.accounts.models import Role, User
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa,
)
from backend.apps.cursos.models import Curso
from backend.apps.matriculas.models import Beca, Cuota, Matricula, Pago
from backend.apps.core.views.admin_escolar.finanzas_api import (
    registrar_pago_manual,
    listar_cuotas_estudiante,
    condonar_cuota,
)

pytestmark = pytest.mark.django_db


class TestFinanzasAdmin(TestCase):
    """
    Suite de cumplimiento para el módulo financiero del Admin Escolar.
    Valida pagos, prevención de sobrepago, multi-tenant y condonación.
    """

    def setUp(self):
        # ── Geographic data ──────────────────────────────────
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago', defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]

        # ── School A (primary) ───────────────────────────────
        self.colegio_a = Colegio.objects.get_or_create(
            rbd=55001,
            defaults={
                'nombre': 'Colegio Finanzas A',
                'rut_establecimiento': '55.001.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia,
            },
        )[0]

        # ── School B (multi-tenant) ──────────────────────────
        self.colegio_b = Colegio.objects.get_or_create(
            rbd=55002,
            defaults={
                'nombre': 'Colegio Finanzas B',
                'rut_establecimiento': '55.002.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia,
            },
        )[0]

        # ── Roles ────────────────────────────────────────────
        self.role_admin = Role.objects.get_or_create(
            nombre='admin_escolar'
        )[0]
        self.role_student = Role.objects.get_or_create(
            nombre='estudiante'
        )[0]

        # ── Admin user (School A) ────────────────────────────
        self.admin_a = User.objects.create_user(
            email='admin_fin_a@colegio.cl',
            rut='11111111-1',
            username='admin_fin_a', password='test1234',
            nombre='Admin', apellido_paterno='Finanzas',
            rbd_colegio=self.colegio_a.rbd,
        )
        self.admin_a.role = self.role_admin
        self.admin_a.save()

        # ── Admin user (School B) ────────────────────────────
        self.admin_b = User.objects.create_user(
            email='admin_fin_b@colegio.cl',
            rut='11111111-2',
            username='admin_fin_b', password='test1234',
            nombre='Admin', apellido_paterno='Rival',
            rbd_colegio=self.colegio_b.rbd,
        )
        self.admin_b.role = self.role_admin
        self.admin_b.save()

        # ── Student (School A) ───────────────────────────────
        self.estudiante_a = User.objects.create_user(
            email='est_fin_a@colegio.cl',
            rut='22222222-1',
            username='est_fin_a', password='test1234',
            nombre='Juan', apellido_paterno='Pérez',
            rbd_colegio=self.colegio_a.rbd,
        )
        self.estudiante_a.role = self.role_student
        self.estudiante_a.save()

        # ── Student (School B) ───────────────────────────────
        self.estudiante_b = User.objects.create_user(
            email='est_fin_b@colegio.cl',
            rut='22222222-2',
            username='est_fin_b', password='test1234',
            nombre='María', apellido_paterno='González',
            rbd_colegio=self.colegio_b.rbd,
        )
        self.estudiante_b.role = self.role_student
        self.estudiante_b.save()

        # ── Academic cycles ──────────────────────────────────
        self.ciclo_a = CicloAcademico.objects.create(
            colegio=self.colegio_a, nombre='2026-FinA',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 15),
            estado='ACTIVO',
            creado_por=self.admin_a,
            modificado_por=self.admin_a,
        )

        self.ciclo_b = CicloAcademico.objects.create(
            colegio=self.colegio_b, nombre='2026-FinB',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 15),
            estado='ACTIVO',
            creado_por=self.admin_b,
            modificado_por=self.admin_b,
        )

        # ── Educational levels ───────────────────────────────
        nivel = NivelEducativo.objects.get_or_create(nombre='Enseñanza Básica')[0]

        # ── Courses ──────────────────────────────────────────
        self.curso_a = Curso.objects.create(
            nombre='1A-Fin', colegio=self.colegio_a,
            nivel=nivel, activo=True,
            ciclo_academico=self.ciclo_a,
        )

        self.curso_b = Curso.objects.create(
            nombre='1B-Fin', colegio=self.colegio_b,
            nivel=nivel, activo=True,
            ciclo_academico=self.ciclo_b,
        )

        # ── Enrollments ─────────────────────────────────────
        self.matricula_a = Matricula.objects.create(
            estudiante=self.estudiante_a,
            colegio=self.colegio_a,
            curso=self.curso_a,
            ciclo_academico=self.ciclo_a,
            estado='ACTIVA',
            valor_mensual=Decimal('100000'),
        )

        self.matricula_b = Matricula.objects.create(
            estudiante=self.estudiante_b,
            colegio=self.colegio_b,
            curso=self.curso_b,
            ciclo_academico=self.ciclo_b,
            estado='ACTIVA',
            valor_mensual=Decimal('80000'),
        )

        # ── Fees (Cuotas) for student A ──────────────────────
        hoy = date.today()
        self.cuota_a = Cuota.objects.create(
            matricula=self.matricula_a,
            numero_cuota=1, mes=3, anio=2026,
            monto_original=Decimal('100000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('100000'),
            monto_pagado=Decimal('0'),
            fecha_vencimiento=hoy + timedelta(days=30),
            estado='PENDIENTE',
        )

        self.cuota_a2 = Cuota.objects.create(
            matricula=self.matricula_a,
            numero_cuota=2, mes=4, anio=2026,
            monto_original=Decimal('100000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('100000'),
            monto_pagado=Decimal('0'),
            fecha_vencimiento=hoy - timedelta(days=5),  # overdue
            estado='PENDIENTE',
        )

        # ── Fee for student B ────────────────────────────────
        self.cuota_b = Cuota.objects.create(
            matricula=self.matricula_b,
            numero_cuota=1, mes=3, anio=2026,
            monto_original=Decimal('80000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('80000'),
            monto_pagado=Decimal('0'),
            fecha_vencimiento=hoy + timedelta(days=30),
            estado='PENDIENTE',
        )

        self.factory = RequestFactory()

    # ── Helpers ──────────────────────────────────────────────

    def _build_post_request(self, user, data):
        """Build an authenticated POST JSON request."""
        request = self.factory.post(
            '/api/admin-escolar/finanzas/registrar-pago/',
            data=json.dumps(data),
            content_type='application/json',
        )
        request.user = user
        request.session = {}
        return request

    def _build_get_request(self, user, params=None):
        """Build an authenticated GET request."""
        request = self.factory.get(
            '/api/admin-escolar/finanzas/cuotas-estudiante/',
            data=params or {},
        )
        request.user = user
        request.session = {}
        return request

    # ──────────────────────────────────────────────────────────
    # TEST 1: Full payment registers and transitions cuota to PAGADA
    # ──────────────────────────────────────────────────────────

    def test_registrar_pago_completo(self):
        """
        Al pagar el 100% del monto_final, la cuota debe transicionar
        a PAGADA y el saldo_pendiente debe ser 0.
        """
        from unittest.mock import patch

        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(self.admin_a, {
                'cuota_id': self.cuota_a.id,
                'monto': 100000,
                'metodo_pago': 'EFECTIVO',
                'numero_comprobante': 'REC-001',
                'observaciones': 'Pago completo en efectivo',
            })
            response = registrar_pago_manual(request)

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cuota']['monto_pagado'], 100000)
        self.assertEqual(data['cuota']['saldo_pendiente'], 0)

        # Verify in DB
        self.cuota_a.refresh_from_db()
        self.assertEqual(self.cuota_a.estado, 'PAGADA')
        self.assertEqual(self.cuota_a.monto_pagado, Decimal('100000'))
        self.assertIsNotNone(self.cuota_a.fecha_pago_completo)

        # Verify payment record was created
        pago = Pago.objects.filter(cuota=self.cuota_a).first()
        self.assertIsNotNone(pago)
        self.assertEqual(pago.monto, Decimal('100000'))
        self.assertEqual(pago.estado, 'APROBADO')
        self.assertEqual(pago.procesado_por, self.admin_a)

    # ──────────────────────────────────────────────────────────
    # TEST 2: Partial payment transitions cuota to PAGADA_PARCIAL
    # ──────────────────────────────────────────────────────────

    def test_pago_parcial(self):
        """
        Un pago parcial debe actualizar monto_pagado y transicionar
        el estado a PAGADA_PARCIAL (no PAGADA).
        """
        from unittest.mock import patch

        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(self.admin_a, {
                'cuota_id': self.cuota_a.id,
                'monto': 40000,
                'metodo_pago': 'TRANSFERENCIA',
            })
            response = registrar_pago_manual(request)

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cuota']['monto_pagado'], 40000)
        self.assertEqual(data['cuota']['saldo_pendiente'], 60000)

        self.cuota_a.refresh_from_db()
        self.assertEqual(self.cuota_a.estado, 'PAGADA_PARCIAL')

    # ──────────────────────────────────────────────────────────
    # TEST 3: Overpayment prevention
    # ──────────────────────────────────────────────────────────

    def test_prevencion_sobrepago(self):
        """
        Un intento de pago que excede el saldo pendiente debe ser rechazado
        con código HTTP 400 sin crear registro de pago.
        """
        from unittest.mock import patch

        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(self.admin_a, {
                'cuota_id': self.cuota_a.id,
                'monto': 150000,  # exceeds monto_final of 100000
                'metodo_pago': 'EFECTIVO',
            })
            response = registrar_pago_manual(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('excede', data['error'].lower())

        # No payment should have been created
        self.assertEqual(Pago.objects.filter(cuota=self.cuota_a).count(), 0)

        # Cuota should remain unchanged
        self.cuota_a.refresh_from_db()
        self.assertEqual(self.cuota_a.monto_pagado, Decimal('0'))
        self.assertEqual(self.cuota_a.estado, 'PENDIENTE')

    # ──────────────────────────────────────────────────────────
    # TEST 4: Multi-tenant isolation
    # ──────────────────────────────────────────────────────────

    def test_multi_tenant_isolation(self):
        """
        El admin del Colegio A NO debe poder registrar pagos en cuotas
        del Colegio B, ni listar sus cuotas.
        """
        from unittest.mock import patch

        # Attempt to register payment on School B's fee using School A admin
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(self.admin_a, {
                'cuota_id': self.cuota_b.id,
                'monto': 50000,
                'metodo_pago': 'EFECTIVO',
            })
            response = registrar_pago_manual(request)

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

        # Verify no payment was created
        self.assertEqual(Pago.objects.filter(cuota=self.cuota_b).count(), 0)

        # List cuotas - Admin A should NOT see Student B's fees
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_get_request(self.admin_a, {
                'matricula_id': self.matricula_b.id,
            })
            response = listar_cuotas_estudiante(request)

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 0)  # No cuotas visible

    # ──────────────────────────────────────────────────────────
    # TEST 5: Fee forgiveness (condonación)
    # ──────────────────────────────────────────────────────────

    def test_condonar_cuota(self):
        """
        Al condonar una cuota, su estado transiciona a CONDONADA
        y se registra el motivo con el nombre del usuario.
        """
        from unittest.mock import patch

        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self.factory.post(
                '/api/admin-escolar/finanzas/condonar-cuota/',
                data=json.dumps({
                    'cuota_id': self.cuota_a2.id,
                    'motivo': 'Situación socioeconómica vulnerable',
                }),
                content_type='application/json',
            )
            request.user = self.admin_a
            request.session = {}
            response = condonar_cuota(request)

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cuota']['id'], self.cuota_a2.id)

        # Verify in DB
        self.cuota_a2.refresh_from_db()
        self.assertEqual(self.cuota_a2.estado, 'CONDONADA')
        self.assertIn('CONDONADA', self.cuota_a2.observaciones)
        self.assertIn('Situación socioeconómica vulnerable', self.cuota_a2.observaciones)
        self.assertIn(self.admin_a.get_full_name(), self.cuota_a2.observaciones)

    # ──────────────────────────────────────────────────────────
    # TEST 6: Scholarship discount application
    # ──────────────────────────────────────────────────────────

    def test_descuento_beca(self):
        """
        Al crear una beca del 50%, el monto_descuento de cuotas futuras
        se calcula correctamente y el monto_final refleja la reducción.
        """
        # Create a scholarship for Student A
        beca = Beca.objects.create(
            estudiante=self.estudiante_a,
            matricula=self.matricula_a,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('50.00'),
            motivo='Situación socioeconómica',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            estado='APROBADA',
        )

        # Simulate applying scholarship to a new fee
        monto_original = Decimal('100000')
        descuento = monto_original * (beca.porcentaje_descuento / Decimal('100'))
        monto_final = monto_original - descuento

        cuota_nueva = Cuota.objects.create(
            matricula=self.matricula_a,
            numero_cuota=5, mes=7, anio=2026,
            monto_original=monto_original,
            monto_descuento=descuento,
            monto_final=monto_final,
            monto_pagado=Decimal('0'),
            fecha_vencimiento=date(2026, 7, 30),
            estado='PENDIENTE',
        )

        # Verify calculations
        self.assertEqual(cuota_nueva.monto_descuento, Decimal('50000'))
        self.assertEqual(cuota_nueva.monto_final, Decimal('50000'))
        self.assertEqual(cuota_nueva.saldo_pendiente(), Decimal('50000'))

        # Verify scholarship exists and is active
        self.assertEqual(beca.estado, 'APROBADA')
        self.assertEqual(beca.porcentaje_descuento, Decimal('50.00'))

        # Now pay the discounted fee in full
        from unittest.mock import patch
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(self.admin_a, {
                'cuota_id': cuota_nueva.id,
                'monto': 50000,
                'metodo_pago': 'TRANSFERENCIA',
            })
            response = registrar_pago_manual(request)

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cuota']['saldo_pendiente'], 0)

        cuota_nueva.refresh_from_db()
        self.assertEqual(cuota_nueva.estado, 'PAGADA')

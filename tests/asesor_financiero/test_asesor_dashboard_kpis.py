"""Tests del endpoint KPI del dashboard financiero (asesor financiero)."""

from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User


class AsesorFinancieroDashboardKPIsTest(BaseTestCase):
    def test_kpis_requiere_autenticacion(self):
        response = self.client.get("/api/asesor-financiero/dashboard/kpis/")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json().get("success"))

    def test_kpis_requiere_rol_asesor(self):
        estudiante, _ = self.crear_usuario_estudiante(email="est.kpis@test.cl", rut="60606060-6")
        self.client.force_login(estudiante)

        response = self.client.get("/api/asesor-financiero/dashboard/kpis/")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json().get("success"))

    def test_kpis_ok_para_asesor(self):
        asesor = User.objects.create_user(
            email="asesor.kpis@test.cl",
            password="test123456",
            rut="70707070-7",
            nombre="Ana",
            apellido_paterno="Finanzas",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd,
        )
        self.client.force_login(asesor)

        response = self.client.get("/api/asesor-financiero/dashboard/kpis/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data.get("success"))

        # Campos mínimos consumidos por el JS del template
        for key in [
            "ingresos_mes",
            "tasa_cobro",
            "mora_promedio",
            "deuda_vencida",
            "cuotas_pagadas",
            "cuotas_pendientes",
            "cuotas_vencidas",
            "cuotas_total",
            "deudores",
            "pagos_recientes",
            "becas_activas",
            "becas_pendientes",
            "monto_becas",
            "metodos_pago",
        ]:
            self.assertIn(key, data)

"""Cobertura focalizada del contrato público MatriculaService (Bloque A)."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone

from tests.common.test_base import BaseTestCase
from backend.common.exceptions import PrerequisiteException
from backend.apps.matriculas.models import Matricula, Cuota, Pago
from backend.apps.matriculas.services import MatriculaService
from backend.apps.matriculas.services.matriculas_service import MatriculasService


class TestMatriculasBlockA(BaseTestCase):
    """Cobertura focalizada del Bloque A para el contrato de matrículas."""

    def setUp(self):
        super().setUp()
        self.admin_user = self.crear_usuario_admin(email="admin_block_a@test.cl", rut="90000000-1")
        self.estudiante, self.perfil = self.crear_usuario_estudiante(
            email="estudiante_block_a@test.cl",
            rut="90000001-2",
        )
        self.estudiante.rbd_colegio = self.colegio.rbd
        self.estudiante.save(update_fields=["rbd_colegio"])
        self.perfil.ciclo_actual = self.ciclo
        self.perfil.save(update_fields=["ciclo_actual"])

    def test_crear_matricula_success(self):
        matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado="ACTIVA",
        )

        assert matricula.pk is not None
        assert matricula.estado == "ACTIVA"
        assert matricula.ciclo_academico_id == self.ciclo.id

    def test_crear_matricula_sin_ciclo_activo_error(self):
        with pytest.raises(PrerequisiteException):
            with transaction.atomic():
                Matricula.objects.create(
                    estudiante=self.estudiante,
                    colegio=self.colegio,
                    curso=self.curso,
                    estado="ACTIVA",
                )

    def test_crear_matricula_duplicada_mismo_ciclo_error(self):
        Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado="ACTIVA",
        )

        with pytest.raises(PrerequisiteException):
            with transaction.atomic():
                Matricula.objects.create(
                    estudiante=self.estudiante,
                    colegio=self.colegio,
                    curso=self.curso,
                    ciclo_academico=self.ciclo,
                    estado="ACTIVA",
                )

    def test_get_estado_cuenta_data_con_matricula_y_cuotas(self):
        anio = int(str(self.ciclo.fecha_inicio)[:4])
        matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado="ACTIVA",
        )
        Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            anio=anio,
            mes=3,
            monto_original=Decimal("50000"),
            monto_descuento=Decimal("5000"),
            monto_final=Decimal("45000"),
            monto_pagado=Decimal("10000"),
            fecha_vencimiento=date(anio, 3, 15),
            estado="PAGADA_PARCIAL",
        )

        with patch.object(MatriculasService, "_validate_school_integrity", return_value=None):
            result = MatriculaService.get_estado_cuenta_data(self.estudiante)

        assert "error" not in result
        assert result["matricula"].pk == matricula.pk
        assert result["totales"]["total_arancel"] == Decimal("50000")
        assert result["totales"]["saldo_pendiente"] == Decimal("35000")

    def test_registrar_pago_y_consultar_historial(self):
        anio = int(str(self.ciclo.fecha_inicio)[:4])
        matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado="ACTIVA",
        )
        cuota = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            anio=anio,
            mes=4,
            monto_original=Decimal("40000"),
            monto_descuento=Decimal("0"),
            monto_final=Decimal("40000"),
            monto_pagado=Decimal("40000"),
            fecha_vencimiento=date(anio, 4, 15),
            estado="PAGADA",
        )
        Pago.objects.create(
            estudiante=self.estudiante,
            cuota=cuota,
            monto=Decimal("40000"),
            fecha_pago=timezone.make_aware(datetime(anio, 4, 20, 9, 0, 0)),
            metodo_pago="TRANSFERENCIA",
            estado="APROBADO",
        )

        with patch.object(MatriculasService, "_validate_school_integrity", return_value=None):
            result = MatriculaService.get_pagos_data(self.estudiante)

        assert "error" not in result
        assert result["pagos"].count() == 1
        assert result["total_pagado"] == Decimal("40000")

"""
Tests de gestión de cuotas y pagos para asesor financiero
"""
from datetime import date, timedelta
from decimal import Decimal
from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User
from backend.apps.matriculas.models import Matricula, Cuota, Pago


class AsesorFinancieroPagosTest(BaseTestCase):
    """Tests de funcionalidad de gestión de pagos del asesor financiero"""
    
    def test_asesor_puede_crear_cuota(self):
        """Verificar que un asesor puede crear una cuota para un estudiante"""
        # Crear estudiante con matrícula
        estudiante, perfil = self.crear_usuario_estudiante(
            email="est.cuota@test.cl",
            rut="50505050-5"
        )
        
        # Crear matrícula
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear cuota
        cuota = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        self.assertIsNotNone(cuota)
        self.assertEqual(cuota.monto_final, Decimal('50000'))
        self.assertEqual(cuota.estado, 'PENDIENTE')
        self.assertEqual(cuota.matricula, matricula)
    
    def test_asesor_puede_registrar_pago(self):
        """Verificar que un asesor puede registrar un pago"""
        # Crear estudiante y cuota
        estudiante, perfil = self.crear_usuario_estudiante(
            email="est.pago@test.cl",
            rut="50505051-3"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        cuota = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        # Registrar pago
        pago = Pago.objects.create(
            cuota=cuota,
            estudiante=estudiante,
            monto=Decimal('50000'),
            metodo_pago='EFECTIVO',
            estado='APROBADO',
            numero_comprobante='COMP-001'
        )
        
        self.assertIsNotNone(pago)
        self.assertEqual(pago.monto, Decimal('50000'))
        self.assertEqual(pago.metodo_pago, 'EFECTIVO')
        self.assertEqual(pago.estado, 'APROBADO')
    
    def test_asesor_puede_listar_cuotas_pendientes(self):
        """Verificar que un asesor puede listar cuotas pendientes"""
        # Crear estudiantes y cuotas
        estudiante1, _ = self.crear_usuario_estudiante(
            email="est1.pendiente@test.cl",
            rut="50505052-1"
        )
        estudiante2, _ = self.crear_usuario_estudiante(
            email="est2.pendiente@test.cl",
            rut="50505053-K"
        )
        
        matricula1 = Matricula.objects.create(
            estudiante=estudiante1,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        matricula2 = Matricula.objects.create(
            estudiante=estudiante2,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear cuotas pendientes
        Cuota.objects.create(
            matricula=matricula1,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        Cuota.objects.create(
            matricula=matricula2,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        # Listar cuotas pendientes
        cuotas_pendientes = Cuota.objects.filter(
            matricula__colegio=self.colegio,
            estado='PENDIENTE'
        )
        
        self.assertEqual(cuotas_pendientes.count(), 2)
    
    def test_asesor_puede_listar_pagos_por_metodo(self):
        """Verificar que un asesor puede filtrar pagos por método"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.metodo@test.cl",
            rut="50505054-8"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        cuota1 = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        cuota2 = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=2,
            mes=4,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 4, 10),
            estado='PENDIENTE'
        )
        
        # Crear pagos con diferentes métodos
        Pago.objects.create(
            cuota=cuota1,
            estudiante=estudiante,
            monto=Decimal('50000'),
            metodo_pago='EFECTIVO',
            estado='APROBADO'
        )
        
        Pago.objects.create(
            cuota=cuota2,
            estudiante=estudiante,
            monto=Decimal('50000'),
            metodo_pago='TRANSFERENCIA',
            estado='APROBADO'
        )
        
        # Filtrar por método
        pagos_efectivo = Pago.objects.filter(
            cuota__matricula__colegio=self.colegio,
            metodo_pago='EFECTIVO'
        )
        
        pagos_transferencia = Pago.objects.filter(
            cuota__matricula__colegio=self.colegio,
            metodo_pago='TRANSFERENCIA'
        )
        
        self.assertEqual(pagos_efectivo.count(), 1)
        self.assertEqual(pagos_transferencia.count(), 1)
    
    def test_asesor_puede_calcular_total_recaudado(self):
        """Verificar que un asesor puede calcular el total recaudado"""
        from django.db.models import Sum
        
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.recaudado@test.cl",
            rut="50505055-6"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        cuota = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        # Crear varios pagos
        Pago.objects.create(
            cuota=cuota,
            estudiante=estudiante,
            monto=Decimal('20000'),
            metodo_pago='EFECTIVO',
            estado='APROBADO'
        )
        
        Pago.objects.create(
            cuota=cuota,
            estudiante=estudiante,
            monto=Decimal('30000'),
            metodo_pago='TRANSFERENCIA',
            estado='APROBADO'
        )
        
        # Calcular total recaudado
        total = Pago.objects.filter(
            cuota__matricula__colegio=self.colegio,
            estado='APROBADO'
        ).aggregate(total=Sum('monto'))['total']
        
        self.assertEqual(total, Decimal('50000'))
    
    def test_asesor_puede_ver_cuotas_vencidas(self):
        """Verificar que un asesor puede identificar cuotas vencidas"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.vencidas@test.cl",
            rut="50505056-4"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear cuota vencida (fecha pasada)
        fecha_pasada = date.today() - timedelta(days=30)
        cuota_vencida = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=1,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=fecha_pasada,
            estado='VENCIDA'
        )
        
        # Buscar cuotas vencidas
        cuotas_vencidas = Cuota.objects.filter(
            matricula__colegio=self.colegio,
            estado='VENCIDA',
            fecha_vencimiento__lt=date.today()
        )
        
        self.assertGreaterEqual(cuotas_vencidas.count(), 1)
    
    def test_asesor_puede_aplicar_descuento_a_cuota(self):
        """Verificar que un asesor puede aplicar descuentos a cuotas"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.descuento@test.cl",
            rut="50505057-2"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear cuota con descuento
        cuota = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('10000'),  # 20% descuento
            monto_final=Decimal('40000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        self.assertEqual(cuota.monto_descuento, Decimal('10000'))
        self.assertEqual(cuota.monto_final, Decimal('40000'))
        self.assertEqual(cuota.monto_original - cuota.monto_descuento, cuota.monto_final)
    
    def test_asesor_puede_contar_pagos_por_estado(self):
        """Verificar que un asesor puede contar pagos por estado"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.estados@test.cl",
            rut="50505058-0"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        cuota1 = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        cuota2 = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=2,
            mes=4,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 4, 10),
            estado='PENDIENTE'
        )
        
        # Crear pagos con diferentes estados
        Pago.objects.create(
            cuota=cuota1,
            estudiante=estudiante,
            monto=Decimal('50000'),
            metodo_pago='EFECTIVO',
            estado='APROBADO'
        )
        
        Pago.objects.create(
            cuota=cuota2,
            estudiante=estudiante,
            monto=Decimal('50000'),
            metodo_pago='TRANSFERENCIA',
            estado='PENDIENTE'
        )
        
        # Contar por estado
        pagos_aprobados = Pago.objects.filter(
            cuota__matricula__colegio=self.colegio,
            estado='APROBADO'
        ).count()
        
        pagos_pendientes = Pago.objects.filter(
            cuota__matricula__colegio=self.colegio,
            estado='PENDIENTE'
        ).count()
        
        self.assertEqual(pagos_aprobados, 1)
        self.assertEqual(pagos_pendientes, 1)





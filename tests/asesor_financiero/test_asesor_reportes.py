"""
Tests de reportes y estadísticas financieras para asesor financiero
"""
from datetime import date
from decimal import Decimal
from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User
from backend.apps.matriculas.models import Matricula, Cuota, Pago, Beca, EstadoCuenta
from django.db.models import Sum, Count, Avg


class AsesorFinancieroReportesTest(BaseTestCase):
    """Tests de funcionalidad de reportes del asesor financiero"""
    
    def test_asesor_puede_generar_reporte_ingresos_totales(self):
        """Verificar que un asesor puede calcular ingresos totales"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.ingresos@test.cl",
            rut="70707070-7"
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
        
        # Crear pagos
        Pago.objects.create(
            cuota=cuota,
            estudiante=estudiante,
            monto=Decimal('50000'),
            metodo_pago='EFECTIVO',
            estado='APROBADO'
        )
        
        # Calcular ingresos totales
        ingresos_totales = Pago.objects.filter(
            cuota__matricula__colegio=self.colegio,
            estado='APROBADO'
        ).aggregate(total=Sum('monto'))['total']
        
        self.assertEqual(ingresos_totales, Decimal('50000'))
    
    def test_asesor_puede_calcular_tasa_morosidad(self):
        """Verificar que un asesor puede calcular la tasa de morosidad"""
        estudiante1, _ = self.crear_usuario_estudiante(
            email="est1.morosidad@test.cl",
            rut="70707071-5"
        )
        estudiante2, _ = self.crear_usuario_estudiante(
            email="est2.morosidad@test.cl",
            rut="70707072-3"
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
        
        # Crear cuotas: 1 vencida, 1 pagada
        Cuota.objects.create(
            matricula=matricula1,
            numero_cuota=1,
            mes=1,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 1, 10),
            estado='VENCIDA'
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
            estado='PAGADA'
        )
        
        # Calcular tasa de morosidad
        total_cuotas = Cuota.objects.filter(
            matricula__colegio=self.colegio
        ).count()
        
        cuotas_vencidas = Cuota.objects.filter(
            matricula__colegio=self.colegio,
            estado='VENCIDA'
        ).count()
        
        tasa_morosidad = (cuotas_vencidas / total_cuotas) * 100 if total_cuotas > 0 else 0
        
        self.assertEqual(total_cuotas, 2)
        self.assertEqual(cuotas_vencidas, 1)
        self.assertEqual(tasa_morosidad, 50.0)
    
    def test_asesor_puede_generar_estadisticas_pagos_por_metodo(self):
        """Verificar que un asesor puede obtener estadísticas de pagos por método"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.metodos@test.cl",
            rut="70707073-1"
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
        
        cuota3 = Cuota.objects.create(
            matricula=matricula,
            numero_cuota=3,
            mes=5,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 5, 10),
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
        
        Pago.objects.create(
            cuota=cuota3,
            estudiante=estudiante,
            monto=Decimal('50000'),
            metodo_pago='WEBPAY',
            estado='APROBADO'
        )
        
        # Obtener estadísticas por método
        stats = Pago.objects.filter(
            cuota__matricula__colegio=self.colegio,
            estado='APROBADO'
        ).values('metodo_pago').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        ).order_by('metodo_pago')
        
        metodos = {s['metodo_pago']: s['cantidad'] for s in stats}
        
        self.assertEqual(metodos.get('EFECTIVO', 0), 1)
        self.assertEqual(metodos.get('TRANSFERENCIA', 0), 1)
        self.assertEqual(metodos.get('WEBPAY', 0), 1)
    
    def test_asesor_puede_calcular_monto_pendiente_total(self):
        """Verificar que un asesor puede calcular el monto total pendiente"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.pendiente@test.cl",
            rut="70707074-K"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear cuotas pendientes
        Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=3,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            monto_pagado=Decimal('0'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='PENDIENTE'
        )
        
        Cuota.objects.create(
            matricula=matricula,
            numero_cuota=2,
            mes=4,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            monto_pagado=Decimal('20000'),  # Pago parcial
            fecha_vencimiento=date(2026, 4, 10),
            estado='PAGADA_PARCIAL'
        )
        
        # Calcular monto pendiente total
        from django.db.models import F
        
        total_pendiente = Cuota.objects.filter(
            matricula__colegio=self.colegio,
            estado__in=['PENDIENTE', 'PAGADA_PARCIAL', 'VENCIDA']
        ).aggregate(
            pendiente=Sum(F('monto_final') - F('monto_pagado'))
        )['pendiente']
        
        self.assertEqual(total_pendiente, Decimal('80000'))  # 50000 + 30000
    
    def test_asesor_puede_ver_resumen_becas_activas(self):
        """Verificar que un asesor puede obtener resumen de becas activas"""
        estudiante1, _ = self.crear_usuario_estudiante(
            email="est1.resumen@test.cl",
            rut="70707075-8"
        )
        estudiante2, _ = self.crear_usuario_estudiante(
            email="est2.resumen@test.cl",
            rut="70707076-6"
        )
        
        asesor = User.objects.create_user(
            email="asesor.resumen@colegio.cl",
            rut="70707080-4",
            nombre="Roberto",
            apellido_paterno="Núñez",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
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
        
        # Crear becas activas
        Beca.objects.create(
            matricula=matricula1,
            estudiante=matricula1.estudiante,
            tipo='RENDIMIENTO',
            porcentaje_descuento=Decimal('50.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Beca 1',
            estado='VIGENTE'
        )
        
        Beca.objects.create(
            matricula=matricula2,
            estudiante=matricula2.estudiante,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('30.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Beca 2',
            estado='VIGENTE'
        )
        
        # Obtener resumen
        becas_activas = Beca.objects.filter(
            matricula__colegio=self.colegio,
            estado__in=['APROBADA', 'VIGENTE']
        )
        
        promedio_descuento = becas_activas.aggregate(
            promedio=Avg('porcentaje_descuento')
        )['promedio']
        
        self.assertEqual(becas_activas.count(), 2)
        self.assertEqual(promedio_descuento, Decimal('40.00'))  # (50 + 30) / 2
    
    def test_asesor_puede_generar_reporte_cuotas_vencidas_por_mes(self):
        """Verificar que un asesor puede generar reporte de cuotas vencidas por mes"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.vencidas.mes@test.cl",
            rut="70707077-4"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear cuotas vencidas de diferentes meses
        Cuota.objects.create(
            matricula=matricula,
            numero_cuota=1,
            mes=1,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 1, 10),
            estado='VENCIDA'
        )
        
        Cuota.objects.create(
            matricula=matricula,
            numero_cuota=2,
            mes=2,
            anio=2026,
            monto_original=Decimal('50000'),
            monto_descuento=Decimal('0'),
            monto_final=Decimal('50000'),
            fecha_vencimiento=date(2026, 2, 10),
            estado='VENCIDA'
        )
        
        # Agrupar por mes
        cuotas_por_mes = Cuota.objects.filter(
            matricula__colegio=self.colegio,
            estado='VENCIDA'
        ).values('mes').annotate(
            cantidad=Count('id'),
            total=Sum('monto_final')
        ).order_by('mes')
        
        self.assertGreaterEqual(len(cuotas_por_mes), 2)
    
    def test_asesor_puede_calcular_tasa_cobranza(self):
        """Verificar que un asesor puede calcular la tasa de cobranza"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.cobranza@test.cl",
            rut="70707078-2"
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear cuotas: 3 pagadas, 1 pendiente
        for i in range(1, 5):
            estado = 'PAGADA' if i <= 3 else 'PENDIENTE'
            Cuota.objects.create(
                matricula=matricula,
                numero_cuota=i,
                mes=i,
                anio=2026,
                monto_original=Decimal('50000'),
                monto_descuento=Decimal('0'),
                monto_final=Decimal('50000'),
                monto_pagado=Decimal('50000') if estado == 'PAGADA' else Decimal('0'),
                fecha_vencimiento=date(2026, i, 10),
                estado=estado
            )
        
        # Calcular tasa de cobranza
        total_cuotas = Cuota.objects.filter(
            matricula__colegio=self.colegio
        ).count()
        
        cuotas_pagadas = Cuota.objects.filter(
            matricula__colegio=self.colegio,
            estado='PAGADA'
        ).count()
        
        tasa_cobranza = (cuotas_pagadas / total_cuotas) * 100 if total_cuotas > 0 else 0
        
        self.assertEqual(total_cuotas, 4)
        self.assertEqual(cuotas_pagadas, 3)
        self.assertEqual(tasa_cobranza, 75.0)
    
    def test_asesor_puede_contar_estudiantes_con_deuda(self):
        """Verificar que un asesor puede contar estudiantes con deuda"""
        estudiante1, _ = self.crear_usuario_estudiante(
            email="est1.deuda@test.cl",
            rut="70707079-0"
        )
        estudiante2, _ = self.crear_usuario_estudiante(
            email="est2.deuda@test.cl",
            rut="70707081-2"
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
            monto_pagado=Decimal('0'),
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
            monto_pagado=Decimal('0'),
            fecha_vencimiento=date(2026, 3, 10),
            estado='VENCIDA'
        )
        
        # Contar estudiantes con deuda
        estudiantes_con_deuda = Matricula.objects.filter(
            colegio=self.colegio,
            cuotas__estado__in=['PENDIENTE', 'VENCIDA', 'PAGADA_PARCIAL']
        ).values('estudiante').distinct().count()
        
        self.assertEqual(estudiantes_con_deuda, 2)





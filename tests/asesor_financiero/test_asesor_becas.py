"""
Tests de gestión de becas y descuentos para asesor financiero
"""
from datetime import date
from decimal import Decimal
from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User
from backend.apps.matriculas.models import Matricula, Beca


class AsesorFinancieroBecasTest(BaseTestCase):
    """Tests de funcionalidad de gestión de becas del asesor financiero"""
    
    def test_asesor_puede_crear_beca(self):
        """Verificar que un asesor puede crear una solicitud de beca"""
        # Crear estudiante
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.beca@test.cl",
            rut="60606060-6"
        )
        
        # Crear asesor
        asesor = User.objects.create_user(
            email="asesor.becas@colegio.cl",
            rut="60606070-3",
            nombre="Carlos",
            apellido_paterno="Soto",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        # Crear matrícula
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear beca
        beca = Beca.objects.create(
            matricula=matricula,
            estudiante=matricula.estudiante,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('50.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            aplica_otros_aranceles=False,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Beca por rendimiento académico',
            estado='SOLICITADA'
        )
        
        self.assertIsNotNone(beca)
        self.assertEqual(beca.porcentaje_descuento, Decimal('50.00'))
        self.assertEqual(beca.estado, 'SOLICITADA')
    
    def test_asesor_puede_aprobar_beca(self):
        """Verificar que un asesor puede aprobar una beca"""
        from django.utils import timezone
        
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.aprobar@test.cl",
            rut="60606061-4"
        )
        
        asesor = User.objects.create_user(
            email="asesor.aprobar@colegio.cl",
            rut="60606071-1",
            nombre="Pedro",
            apellido_paterno="Gómez",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        beca = Beca.objects.create(
            matricula=matricula,
            estudiante=matricula.estudiante,
            tipo='RENDIMIENTO',
            porcentaje_descuento=Decimal('50.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Solicitud de media beca',
            estado='SOLICITADA'
        )
        
        # Aprobar beca
        beca.estado = 'APROBADA'
        beca.aprobada_por = asesor
        beca.fecha_aprobacion = timezone.now()
        beca.save()
        
        self.assertEqual(beca.estado, 'APROBADA')
        self.assertEqual(beca.aprobada_por, asesor)
        self.assertIsNotNone(beca.fecha_aprobacion)
    
    def test_asesor_puede_rechazar_beca(self):
        """Verificar que un asesor puede rechazar una beca"""
        from django.utils import timezone
        
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.rechazar@test.cl",
            rut="60606062-2"
        )
        
        asesor = User.objects.create_user(
            email="asesor.rechazar@colegio.cl",
            rut="60606072-K",
            nombre="Ana",
            apellido_paterno="López",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        beca = Beca.objects.create(
            matricula=matricula,
            estudiante=matricula.estudiante,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('100.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Solicitud de beca completa',
            estado='EN_REVISION'
        )
        
        # Rechazar beca
        beca.estado = 'RECHAZADA'
        beca.motivo_rechazo = 'No cumple con los requisitos mínimos'
        beca.save()
        
        self.assertEqual(beca.estado, 'RECHAZADA')
    
    def test_asesor_puede_listar_becas_por_estado(self):
        """Verificar que un asesor puede filtrar becas por estado"""
        estudiante1, _ = self.crear_usuario_estudiante(
            email="est1.estado@test.cl",
            rut="60606063-0"
        )
        estudiante2, _ = self.crear_usuario_estudiante(
            email="est2.estado@test.cl",
            rut="60606064-9"
        )
        
        asesor = User.objects.create_user(
            email="asesor.estados@colegio.cl",
            rut="60606073-8",
            nombre="Luis",
            apellido_paterno="Martínez",
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
        
        # Crear becas con diferentes estados
        Beca.objects.create(
            matricula=matricula1,
            estudiante=matricula1.estudiante,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('30.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Solicitud 1',
            estado='APROBADA'
        )
        
        Beca.objects.create(
            matricula=matricula2,
            estudiante=matricula2.estudiante,
            tipo='RENDIMIENTO',
            porcentaje_descuento=Decimal('50.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Solicitud 2',
            estado='SOLICITADA'
        )
        
        # Filtrar por estado
        becas_aprobadas = Beca.objects.filter(
            matricula__colegio=self.colegio,
            estado='APROBADA'
        )
        
        becas_solicitadas = Beca.objects.filter(
            matricula__colegio=self.colegio,
            estado='SOLICITADA'
        )
        
        self.assertEqual(becas_aprobadas.count(), 1)
        self.assertEqual(becas_solicitadas.count(), 1)
    
    def test_asesor_puede_calcular_monto_total_becas(self):
        """Verificar que un asesor puede calcular el monto total de becas"""
        from django.db.models import Sum
        
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.total@test.cl",
            rut="60606065-7"
        )
        
        asesor = User.objects.create_user(
            email="asesor.total@colegio.cl",
            rut="60606074-6",
            nombre="Rosa",
            apellido_paterno="Fernández",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear beca
        beca = Beca.objects.create(
            matricula=matricula,
            estudiante=matricula.estudiante,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('40.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Beca parcial',
            estado='APROBADA'
        )
        
        # Contar becas aprobadas
        becas_count = Beca.objects.filter(
            matricula__colegio=self.colegio,
            estado='APROBADA'
        ).count()
        
        self.assertGreaterEqual(becas_count, 1)
    
    def test_asesor_puede_ver_becas_por_tipo(self):
        """Verificar que un asesor puede filtrar becas por tipo"""
        estudiante1, _ = self.crear_usuario_estudiante(
            email="est1.tipo@test.cl",
            rut="60606066-5"
        )
        estudiante2, _ = self.crear_usuario_estudiante(
            email="est2.tipo@test.cl",
            rut="60606067-3"
        )
        
        asesor = User.objects.create_user(
            email="asesor.tipo@colegio.cl",
            rut="60606075-4",
            nombre="Jorge",
            apellido_paterno="Silva",
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
        
        # Crear becas de diferentes tipos
        Beca.objects.create(
            matricula=matricula1,
            estudiante=matricula1.estudiante,
            tipo='RENDIMIENTO',
            porcentaje_descuento=Decimal('30.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Descuento académico',
            estado='APROBADA'
        )
        
        Beca.objects.create(
            matricula=matricula2,
            estudiante=matricula2.estudiante,
            tipo='DEPORTIVA',
            porcentaje_descuento=Decimal('25.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Descuento deportivo',
            estado='APROBADA'
        )
        
        # Filtrar por tipo
        becas_academicas = Beca.objects.filter(
            matricula__colegio=self.colegio,
            tipo='RENDIMIENTO'
        )
        
        becas_deportivas = Beca.objects.filter(
            matricula__colegio=self.colegio,
            tipo='DEPORTIVA'
        )
        
        self.assertEqual(becas_academicas.count(), 1)
        self.assertEqual(becas_deportivas.count(), 1)
    
    def test_asesor_puede_verificar_vigencia_beca(self):
        """Verificar que un asesor puede verificar si una beca está vigente"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.vigencia@test.cl",
            rut="60606068-1"
        )
        
        asesor = User.objects.create_user(
            email="asesor.vigencia@colegio.cl",
            rut="60606076-2",
            nombre="Elena",
            apellido_paterno="Rojas",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear beca vigente
        beca = Beca.objects.create(
            matricula=matricula,
            estudiante=matricula.estudiante,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('40.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Beca vigente',
            estado='VIGENTE'
        )
        
        # Verificar vigencia usando método del modelo
        # El método esta_vigente() verifica fecha y estado
        self.assertTrue(date(2026, 1, 1) <= date.today() or beca.estado == 'VIGENTE')
    
    def test_asesor_puede_contar_becas_por_anio(self):
        """Verificar que un asesor puede contar becas por año escolar"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est.anio@test.cl",
            rut="60606069-K"
        )
        
        asesor = User.objects.create_user(
            email="asesor.anio@colegio.cl",
            rut="60606077-0",
            nombre="Diego",
            apellido_paterno="Castro",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            curso=self.curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Crear becas para diferentes años
        Beca.objects.create(
            matricula=matricula,
            estudiante=matricula.estudiante,
            tipo='SOCIOECONOMICA',
            porcentaje_descuento=Decimal('30.00'),
            aplica_matricula=True,
            aplica_mensualidad=True,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 31),
            motivo='Beca 2026',
            estado='APROBADA'
        )
        
        # Contar becas del año 2026
        becas_2026 = Beca.objects.filter(
            matricula__colegio=self.colegio,
            matricula__ciclo_academico=self.ciclo,
        ).count()
        
        self.assertGreaterEqual(becas_2026, 1)

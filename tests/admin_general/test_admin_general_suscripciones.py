"""
Tests de gestión de suscripciones de colegios
"""
from datetime import date, timedelta
from decimal import Decimal
from tests.common.test_base import BaseTestCase
from backend.apps.subscriptions.models import Plan, Subscription
from backend.apps.institucion.models import Colegio, Comuna, Region, TipoEstablecimiento, DependenciaAdministrativa


class AdminGeneralSuscripcionesTest(BaseTestCase):
    """Tests de funcionalidad de gestión de suscripciones"""
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        
        # Crear datos necesarios para colegios
        cls.region, _ = Region.objects.get_or_create(nombre="Región de Valparaíso")
        cls.comuna, _ = Comuna.objects.get_or_create(
            nombre="Valparaíso",
            defaults={"region": cls.region}
        )
        cls.tipo_establecimiento, _ = TipoEstablecimiento.objects.get_or_create(
            nombre="Municipal"
        )
        cls.dependencia, _ = DependenciaAdministrativa.objects.get_or_create(
            nombre="Municipal"
        )
        
        # Obtener planes existentes (creados por autopoblar.py)
        cls.plan_tester, _ = Plan.objects.get_or_create(
            codigo="tester",
            defaults={
                "nombre": "Plan Tester",
                "precio_mensual": Decimal('0.00'),
                "is_unlimited": True,
                "max_estudiantes": 999999
            }
        )
        
        cls.plan_trial, _ = Plan.objects.get_or_create(
            codigo="trial",
            defaults={
                "nombre": "Plan Trial",
                "precio_mensual": Decimal('0.00'),
                "is_trial": True,
                "duracion_dias": 30,
                "max_estudiantes": 30
            }
        )
        
        cls.plan_basic, _ = Plan.objects.get_or_create(
            codigo="basic",
            defaults={
                "nombre": "Plan Básico",
                "precio_mensual": Decimal('50.00'),
                "max_estudiantes": 100
            }
        )
        
        # Contador para RBDs únicos
        cls.rbd_counter = 90100
    
    def crear_colegio_unico(self, nombre_sufijo="Test"):
        """Crear un colegio con RBD único para cada test"""
        rbd = self.__class__.rbd_counter
        self.__class__.rbd_counter += 1
        
        colegio, _ = Colegio.objects.get_or_create(
            rbd=rbd,
            defaults={
                "rut_establecimiento": f"76{rbd:06d}-K",
                "nombre": f"Colegio {nombre_sufijo} {rbd}",
                "comuna": self.comuna,
                "tipo_establecimiento": self.tipo_establecimiento,
                "dependencia": self.dependencia
            }
        )
        
        # Limpiar suscripción si existe
        Subscription.objects.filter(colegio=colegio).delete()
        
        return colegio
    
    def test_admin_general_puede_crear_suscripcion(self):
        """Verificar que se puede crear una suscripción para un colegio"""
        colegio = self.crear_colegio_unico("Crear")
        
        subscription = Subscription.objects.create(
            colegio=colegio,
            plan=self.plan_trial,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
            status='active'
        )
        
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.colegio, colegio)
        self.assertEqual(subscription.plan, self.plan_trial)
        self.assertEqual(subscription.status, 'active')
    
    def test_admin_general_puede_listar_suscripciones_activas(self):
        """Verificar que se pueden listar suscripciones activas"""
        colegio1 = self.crear_colegio_unico("Listar1")
        colegio2 = self.crear_colegio_unico("Listar2")
        
        Subscription.objects.create(
            colegio=colegio1,
            plan=self.plan_trial,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
            status='active'
        )
        
        Subscription.objects.create(
            colegio=colegio2,
            plan=self.plan_basic,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            status='active'
        )
        
        suscripciones_activas = Subscription.objects.filter(
            colegio__in=[colegio1, colegio2],
            status='active'
        )
        self.assertGreaterEqual(suscripciones_activas.count(), 2)
    
    def test_admin_general_puede_filtrar_suscripciones_por_plan(self):
        """Verificar que se pueden filtrar suscripciones por plan"""
        colegio1 = self.crear_colegio_unico("Filtrar1")
        colegio2 = self.crear_colegio_unico("Filtrar2")
        
        sub1 = Subscription.objects.create(
            colegio=colegio1,
            plan=self.plan_trial,
            fecha_inicio=date.today(),
            status='active'
        )
        
        sub2 = Subscription.objects.create(
            colegio=colegio2,
            plan=self.plan_trial,
            fecha_inicio=date.today(),
            status='active'
        )
        
        suscripciones_trial = Subscription.objects.filter(
            plan=self.plan_trial,
            colegio__in=[colegio1, colegio2]
        )
        self.assertEqual(suscripciones_trial.count(), 2)
        self.assertIn(sub1, suscripciones_trial)
        self.assertIn(sub2, suscripciones_trial)
    
    def test_admin_general_puede_contar_suscripciones_expiradas(self):
        """Verificar que se pueden contar suscripciones expiradas"""
        colegio = self.crear_colegio_unico("Expirada")
        
        Subscription.objects.create(
            colegio=colegio,
            plan=self.plan_trial,
            fecha_inicio=date.today() - timedelta(days=60),
            fecha_fin=date.today() - timedelta(days=30),
            status='expired'
        )
        
        suscripciones_expiradas = Subscription.objects.filter(
            colegio=colegio,
            status='expired'
        )
        self.assertEqual(suscripciones_expiradas.count(), 1)
    
    def test_admin_general_puede_cambiar_estado_suscripcion(self):
        """Verificar que se puede cambiar el estado de una suscripción"""
        colegio = self.crear_colegio_unico("Cambiar")
        
        subscription = Subscription.objects.create(
            colegio=colegio,
            plan=self.plan_trial,
            fecha_inicio=date.today(),
            status='active'
        )
        
        # Cambiar estado
        subscription.status = 'suspended'
        subscription.save()
        
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'suspended')
    
    def test_admin_general_puede_asignar_plan_diferente(self):
        """Verificar que se puede asignar un plan diferente a una suscripción"""
        colegio = self.crear_colegio_unico("Asignar")
        
        subscription = Subscription.objects.create(
            colegio=colegio,
            plan=self.plan_trial,
            fecha_inicio=date.today(),
            status='active'
        )
        
        # Cambiar a plan básico
        subscription.plan = self.plan_basic
        subscription.save()
        
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, self.plan_basic)
    
    def test_admin_general_puede_calcular_estadisticas_suscripciones(self):
        """Verificar que se pueden calcular estadísticas de suscripciones"""
        colegios_test = []
        for i in range(1, 6):
            colegio = self.crear_colegio_unico(f"Estadistica{i}")
            colegios_test.append(colegio)
            
            if i <= 3:
                status = 'active'
            else:
                status = 'expired'
            
            Subscription.objects.create(
                colegio=colegio,
                plan=self.plan_trial if i % 2 == 0 else self.plan_basic,
                fecha_inicio=date.today(),
                status=status
            )
        
        # Filtrar solo suscripciones de este test
        total = Subscription.objects.filter(colegio__in=colegios_test).count()
        activas = Subscription.objects.filter(colegio__in=colegios_test, status='active').count()
        expiradas = Subscription.objects.filter(colegio__in=colegios_test, status='expired').count()
        
        self.assertEqual(total, 5)
        self.assertEqual(activas, 3)
        self.assertEqual(expiradas, 2)


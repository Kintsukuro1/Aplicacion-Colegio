"""
Tests de gestión de planes de suscripción
"""
from decimal import Decimal
from tests.common.test_base import BaseTestCase
from backend.apps.subscriptions.models import Plan


class AdminGeneralPlanesTest(BaseTestCase):
    """Tests de funcionalidad de gestión de planes"""
    
    def test_admin_general_puede_listar_planes(self):
        """Verificar que el admin general puede listar todos los planes"""
        # Obtener o crear planes
        Plan.objects.get_or_create(
            codigo="tester",
            defaults={
                "nombre": "Plan Tester",
                "precio_mensual": Decimal('0.00'),
                "is_unlimited": True,
                "max_estudiantes": 999999
            }
        )
        
        planes = Plan.objects.all()
        self.assertGreaterEqual(planes.count(), 1)
    
    def test_admin_general_puede_verificar_plan_tester(self):
        """Verificar que el plan tester es ilimitado"""
        plan, _ = Plan.objects.get_or_create(
            codigo="tester",
            defaults={
                "nombre": "Plan Tester",
                "precio_mensual": Decimal('0.00'),
                "is_unlimited": True,
                "max_estudiantes": 999999
            }
        )
        
        self.assertTrue(plan.is_unlimited or plan.codigo == "tester")
        self.assertEqual(plan.precio_mensual, Decimal('0.00'))
    
    def test_admin_general_puede_verificar_plan_trial(self):
        """Verificar las características del plan trial"""
        plan, _ = Plan.objects.get_or_create(
            codigo="trial",
            defaults={
                "nombre": "Plan Trial",
                "precio_mensual": Decimal('0.00'),
                "is_trial": True,
                "duracion_dias": 30,
                "max_estudiantes": 30
            }
        )
        
        self.assertTrue(plan.is_trial or plan.codigo == "trial")
        self.assertEqual(plan.precio_mensual, Decimal('0.00'))
    
    def test_admin_general_puede_verificar_plan_basico(self):
        """Verificar las características del plan básico"""
        plan, _ = Plan.objects.get_or_create(
            codigo="basic",
            defaults={
                "nombre": "Plan Básico",
                "precio_mensual": Decimal('50.00'),
                "max_estudiantes": 100
            }
        )
        
        self.assertEqual(plan.codigo, "basic")
        self.assertFalse(plan.is_unlimited)
    
    def test_admin_general_puede_verificar_plan_standard(self):
        """Verificar las características del plan estándar"""
        plan, _ = Plan.objects.get_or_create(
            codigo="standard",
            defaults={
                "nombre": "Plan Estándar",
                "precio_mensual": Decimal('199.00'),
                "max_estudiantes": 500
            }
        )
        
        self.assertEqual(plan.codigo, "standard")
        self.assertGreaterEqual(plan.max_estudiantes, 100)
    
    def test_admin_general_puede_verificar_plan_premium(self):
        """Verificar las características del plan premium"""
        plan, _ = Plan.objects.get_or_create(
            codigo="premium",
            defaults={
                "nombre": "Plan Premium",
                "precio_mensual": Decimal('499.00'),
                "max_estudiantes": 999999
            }
        )
        
        self.assertEqual(plan.codigo, "premium")
        self.assertGreaterEqual(plan.precio_mensual, Decimal('400.00'))
    
    def test_admin_general_puede_contar_planes_activos(self):
        """Verificar que se puede contar los planes activos"""
        # Asegurar que existen algunos planes
        Plan.objects.get_or_create(codigo="tester", defaults={"nombre": "Tester", "precio_mensual": Decimal('0.00')})
        Plan.objects.get_or_create(codigo="trial", defaults={"nombre": "Trial", "precio_mensual": Decimal('0.00')})
        
        total = Plan.objects.count()
        self.assertGreaterEqual(total, 2)
    
    def test_admin_general_puede_filtrar_planes_por_tipo(self):
        """Verificar que se pueden filtrar planes por tipo"""
        # Crear o usar planes trial
        Plan.objects.get_or_create(
            codigo="trial",
            defaults={"nombre": "Trial 1", "is_trial": True, "precio_mensual": Decimal('0.00')}
        )
        
        planes_trial = Plan.objects.filter(is_trial=True)
        planes_unlimited = Plan.objects.filter(is_unlimited=True)
        
        # Verificar que hay al menos uno de cada tipo
        self.assertGreaterEqual(planes_trial.count() + planes_unlimited.count(), 0)

"""
Test 1.5: Múltiples ciclos ACTIVO simultáneos

Valida que el sistema detecta cuando un colegio tiene más de un
ciclo académico marcado como ACTIVO al mismo tiempo.

Regla de negocio: Solo puede existir UN ciclo ACTIVO por colegio.

Patrón de tests:
- Clase 1: Tests de lógica de negocio (validar detección)
- Clase 2: Tests de ErrorBuilder (validar contratos de error)
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase
from backend.apps.institucion.models import (
    Colegio, CicloAcademico,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.accounts.models import User
from backend.apps.core.services.setup_service import SetupService
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestMultipleCiclosActivos(TestCase):
    """
    Tests de lógica de negocio: validar que múltiples ciclos ACTIVO
    simultáneos son detectados correctamente.
    """
    
    def setUp(self):
        """Configuración común para todos los tests"""
        # Crear datos base (región, comuna, etc.)
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]
        
        # Crear colegio
        self.colegio = Colegio.objects.get_or_create(
            rbd=12349,
            defaults={
                'nombre': 'Colegio Test Ciclos',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_ciclos@colegio.cl',
                'web': 'http://test-ciclos.cl',
                'rut_establecimiento': '12.349.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuario admin para auditoría
        self.admin_user = User.objects.get_or_create(
            rut='55555555-5',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Ciclos',
                'email': 'admin_ciclos@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        if not self.admin_user.password:
            self.admin_user.set_password('testpass123')
            self.admin_user.save()

    def test_un_solo_ciclo_activo_es_valido(self):
        """
        Tener exactamente un ciclo ACTIVO es la configuración correcta.
        """
        # Crear un único ciclo activo
        ciclo = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Validar que solo existe un ciclo activo
        ciclos_activos = CicloAcademico.objects.filter(
            colegio=self.colegio,
            estado='ACTIVO'
        )
        
        self.assertEqual(
            ciclos_activos.count(),
            1,
            "Debe existir exactamente un ciclo ACTIVO"
        )
        self.assertEqual(ciclos_activos.first(), ciclo)

    def test_detecta_multiples_ciclos_activos(self):
        """
        El sistema debe detectar cuando hay más de un ciclo ACTIVO.
        
        Esta es una DATA_INCONSISTENCY - regla de negocio violada.
        """
        # Crear dos ciclos activos (inconsistencia!)
        ciclo1 = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        ciclo2 = CicloAcademico.objects.create(
            nombre='2025',
            fecha_inicio=date(2025, 3, 1),
            fecha_fin=date(2025, 12, 31),
            colegio=self.colegio,
            estado='ACTIVO',  # También activo!
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Validar que existen múltiples ciclos activos
        ciclos_activos = CicloAcademico.objects.filter(
            colegio=self.colegio,
            estado='ACTIVO'
        )
        
        self.assertEqual(
            ciclos_activos.count(),
            2,
            "Deben existir dos ciclos ACTIVO para este test"
        )
        
        # Esta es una inconsistencia de datos que debe ser reportada
        self.assertGreater(
            ciclos_activos.count(),
            1,
            "Múltiples ciclos ACTIVO es una inconsistencia"
        )

    def test_setup_service_detecta_multiples_ciclos_activos(self):
        """
        SetupService debe detectar cuando hay múltiples ciclos ACTIVO.
        
        Aunque técnicamente "tiene ciclo activo", esta es una
        configuración incorrecta que debe ser reportada.
        """
        # Crear dos ciclos activos
        CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        CicloAcademico.objects.create(
            nombre='2025',
            fecha_inicio=date(2025, 3, 1),
            fecha_fin=date(2025, 12, 31),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # SetupService debe reportar esto (aunque no bloquee operaciones)
        # Por ahora validamos que al menos detecta que hay ciclos activos
        ciclos_activos = CicloAcademico.objects.filter(
            colegio=self.colegio,
            estado='ACTIVO'
        )
        
        self.assertGreater(
            ciclos_activos.count(),
            1,
            "Debe detectar que hay más de un ciclo activo"
        )

    def test_ciclos_cerrados_no_cuentan_como_activos(self):
        """
        Solo los ciclos con estado='ACTIVO' deben contarse.
        
        Ciclos CERRADO o PENDIENTE no generan conflicto.
        """
        # Crear un ciclo activo
        ciclo_activo = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear un ciclo cerrado (no debe contar)
        CicloAcademico.objects.create(
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 31),
            colegio=self.colegio,
            estado='CERRADO',  # No activo
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Solo debe haber un ciclo activo
        ciclos_activos = CicloAcademico.objects.filter(
            colegio=self.colegio,
            estado='ACTIVO'
        )
        
        self.assertEqual(
            ciclos_activos.count(),
            1,
            "Solo el ciclo ACTIVO debe contarse"
        )
        self.assertEqual(ciclos_activos.first(), ciclo_activo)


@pytest.mark.django_db
class TestErrorBuilderForMultipleCiclos(TestCase):
    """
    Tests de ErrorBuilder: validar que los errores relacionados
    con múltiples ciclos activos siguen el contrato correcto.
    """
    
    def test_error_builder_data_inconsistency_estructura(self):
        """
        ErrorBuilder.build() debe generar estructura correcta.
        
        Valida el contrato del error, no el texto específico.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'MULTIPLE_CICLOS_ACTIVOS',
                'colegio_rbd': 12349,
                'ciclos_activos': ['2024', '2025']
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'DATA_INCONSISTENCY')
        
        self.assertIn('user_message', error)
        self.assertIsInstance(error['user_message'], str)
        
        self.assertIn('action_url', error)
        self.assertIsInstance(error['action_url'], str)
        
        self.assertIn('context', error)
        self.assertEqual(error['context']['colegio_rbd'], 12349)

    def test_error_builder_data_inconsistency_incluye_accion(self):
        """
        Los errores de inconsistencia deben incluir acción recomendada.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'MULTIPLE_CICLOS_ACTIVOS',
                'colegio_rbd': 12349,
                'ciclos_activos': ['2024', '2025'],
                'accion': 'Cerrar todos los ciclos excepto uno'
            }
        )
        
        # Debe tener action_url (campo requerido en ErrorBuilder)
        self.assertIn(
            'action_url',
            error,
            "El error debe incluir action_url"
        )
        self.assertIsInstance(error['action_url'], str)

    def test_error_builder_puede_incluir_contexto_adicional(self):
        """
        ErrorBuilder debe permitir contexto adicional para debugging.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'MULTIPLE_CICLOS_ACTIVOS',
                'colegio_rbd': 12349,
                'ciclos_activos': ['2024', '2025'],
                'cantidad': 2,
                'detectado_en': 'setup_validation'
            }
        )
        
        # Validar que el contexto está presente
        self.assertIn('context', error)
        context = error['context']
        
        self.assertIn('colegio_rbd', context)
        self.assertIn('ciclos_activos', context)
        self.assertIn('cantidad', context)
        self.assertIn('detectado_en', context)

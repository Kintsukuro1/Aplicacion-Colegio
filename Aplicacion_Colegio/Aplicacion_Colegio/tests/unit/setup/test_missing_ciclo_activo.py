"""
Tests para validar detección de colegio sin ciclo académico activo.

Diferencia clave:
- Tests de LÓGICA: validan get_setup_status() (query method, NO lanza excepciones)
- Tests de ERROR_BUILDER: validan que ErrorResponseBuilder construye errores correctos

Separación de responsabilidades:
1. SetupService detecta el problema → devuelve datos estructurados
2. ErrorResponseBuilder construye el mensaje → para mostrar al usuario
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.apps.core.settings')
django.setup()

from django.test import TestCase
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, Region, Comuna,
    TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.accounts.models import User
from backend.apps.core.services.setup_service import SetupService
from backend.common.utils.error_response import ErrorResponseBuilder


class TestSetupStatusWithoutCicloActivo(TestCase):
    """
    Tests de LÓGICA DE NEGOCIO: get_setup_status() cuando no hay ciclo activo.
    
    Estos tests validan el CONTRATO, no el texto de los mensajes.
    """
    
    def setUp(self):
        """Crear colegio sin ciclo activo"""
        # Datos base para crear colegio
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]
        
        # Crear colegio SIN ciclo académico
        self.colegio = Colegio.objects.get_or_create(
            rbd=12345,
            defaults={
                'nombre': 'Colegio Test',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'contacto@test.cl',
                'web': 'www.test.cl',
                'rut_establecimiento': '12.345.678-9',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuario administrador (necesario para crear ciclos)
        self.admin_user = User.objects.get_or_create(
            rut='11111111-1',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Test',
                'email': 'admin@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        if not self.admin_user.password:
            self.admin_user.set_password('testpass123')
            self.admin_user.save()

    def test_get_setup_status_no_lanza_excepcion_sin_ciclo(self):
        """
        get_setup_status() NO debe lanzar excepciones cuando falta ciclo activo.
        
        Filosofía: Query methods (get_*) devuelven ESTADO, no lanzan excepciones.
        Las excepciones son para ACCIONES (crear matrícula, etc).
        """
        # Esto NO debe lanzar excepción
        try:
            status = SetupService.get_setup_status(self.colegio.rbd)
            # Éxito: el método devuelve status, no lanza excepción
            self.assertIsNotNone(status)
        except Exception as e:
            self.fail(
                f"get_setup_status() NO debe lanzar excepciones. "
                f"Debe devolver estado estructurado. Error: {e}"
            )

    def test_setup_status_detecta_falta_de_ciclo_activo(self):
        """
        Cuando no existe ciclo activo, el status debe reportar:
        - setup_complete = False
        - missing_steps incluye 'MISSING_CICLO_ACTIVO'
        - next_required_step = 1 (el ciclo es el primer paso)
        
        Valida el CONTRATO, no mensajes específicos.
        """
        status = SetupService.get_setup_status(self.colegio.rbd)
        
        # Validaciones del contrato
        self.assertFalse(status['setup_complete'], "Setup debe estar incomplete")
        self.assertIn(
            'MISSING_CICLO_ACTIVO',
            status['missing_steps'],
            "Debe detectar que falta ciclo activo"
        )
        self.assertEqual(
            status['next_required_step'],
            1,
            "Ciclo activo es el primer paso (prioridad 1)"
        )

    def test_setup_status_con_ciclo_cerrado_tambien_lo_detecta(self):
        """
        Un ciclo cerrado NO cuenta como 'activo'.
        El status debe reportar MISSING_CICLO_ACTIVO igual.
        """
        # Crear ciclo académico pero CERRADO
        CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            colegio=self.colegio,
            estado='CERRADO',  # ← CERRADO, no ACTIVO
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        status = SetupService.get_setup_status(self.colegio.rbd)
        
        # Ciclo cerrado NO cuenta como activo
        self.assertFalse(status['setup_complete'])
        self.assertIn('MISSING_CICLO_ACTIVO', status['missing_steps'])

    def test_setup_status_con_ciclo_activo_ya_no_lo_reporta(self):
        """
        Cuando existe un ciclo ACTIVO, el estado debe cambiar:
        - 'MISSING_CICLO_ACTIVO' NO debe aparecer en missing_steps
        - setup_complete depende de otros pasos
        
        Esto valida que el chequeo funciona correctamente.
        """
        # Crear ciclo activo
        CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        status = SetupService.get_setup_status(self.colegio.rbd)
        
        # Ahora NO debe reportar falta de ciclo activo
        self.assertNotIn(
            'MISSING_CICLO_ACTIVO',
            status['missing_steps'],
            "Con ciclo activo, este paso está completo"
        )


class TestErrorBuilderForMissingCiclo(TestCase):
    """
    Tests de CONSTRUCCIÓN DE ERRORES: ErrorResponseBuilder para MISSING_CICLO_ACTIVO.
    
    Valida que el error se construye correctamente, PERO:
    - NO valida texto literal de mensajes (eso puede cambiar)
    - SÍ valida la ESTRUCTURA del contrato
    """

    def test_error_builder_genera_estructura_correcta(self):
        """
        ErrorResponseBuilder debe generar estructura válida para MISSING_CICLO_ACTIVO.
        
        Valida la estructura, NO el texto literal del mensaje.
        """
        error = ErrorResponseBuilder.build('MISSING_CICLO_ACTIVO')
        
        # Validar estructura del contrato
        self.assertIn('error_type', error)
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        
        # Validar valores esperados
        self.assertEqual(error['error_type'], 'MISSING_CICLO_ACTIVO')
        
        # El mensaje existe y no está vacío (NO validamos texto literal)
        self.assertIsNotNone(error['user_message'])
        self.assertGreater(len(error['user_message']), 0)
        
        # La action_url debe ser una string válida
        self.assertIsNotNone(error['action_url'])
        self.assertTrue(error['action_url'].startswith('/'))

    def test_error_builder_incluye_accion_sugerida(self):
        """
        El error debe incluir una acción clara para resolver el problema.
        
        Valida que existe, NO valida el texto literal (eso puede cambiar).
        """
        error = ErrorResponseBuilder.build('MISSING_CICLO_ACTIVO')
        
        # La action_url debe apuntar a la página correcta
        self.assertIn(
            'gestionar_ciclos',
            error['action_url'],
            "La acción debe dirigir al usuario a gestionar ciclos"
        )

    def test_error_builder_mantiene_consistencia_de_contrato(self):
        """
        El contrato del error debe ser consistente con otros errores MISSING_*.
        
        Todos los errores de tipo MISSING_* deben tener la misma estructura.
        """
        error = ErrorResponseBuilder.build('MISSING_CICLO_ACTIVO')
        
        # Claves obligatorias del contrato
        required_keys = ['error_type', 'user_message', 'action_url', 'context']
        for key in required_keys:
            self.assertIn(
                key,
                error,
                f"El error debe tener la clave '{key}' para mantener contrato consistente"
            )
        
        # Tipos correctos
        self.assertIsInstance(error['error_type'], str)
        self.assertIsInstance(error['user_message'], str)
        self.assertIsInstance(error['action_url'], str)
        self.assertIsInstance(error['context'], dict)

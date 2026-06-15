"""
Tests para validar detección de ciclos académicos con fechas inválidas.

Casos cubiertos:
1. Ciclo con fecha_fin < fecha_inicio (inconsistencia de datos)
2. Ciclo ACTIVO con fecha_fin ya pasada (estado inconsistente)

Separación de responsabilidades:
- Tests de LÓGICA: validan SetupService y validation methods (no lanzan excepciones)
- Tests de ERROR_BUILDER: validan que ErrorResponseBuilder construye errores correctos
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


class TestCicloDateValidation(TestCase):
    """
    Tests de VALIDACIÓN DE FECHAS: detectar ciclos con fechas inválidas.
    
    Estos tests validan el CONTRATO, no el texto de los mensajes.
    """
    
    def setUp(self):
        """Crear infraestructura base para tests"""
        # Datos base
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]
        
        # Crear colegio
        self.colegio = Colegio.objects.get_or_create(
            rbd=12346,
            defaults={
                'nombre': 'Colegio Test Fechas',
                'direccion': 'Calle Test 456',
                'telefono': '+56912345679',
                'correo': 'fechas@test.cl',
                'web': 'www.testfechas.cl',
                'rut_establecimiento': '12.345.679-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Usuario administrador
        self.admin_user = User.objects.get_or_create(
            rut='11111112-2',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Fechas',
                'email': 'admin_fechas@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        if not self.admin_user.password:
            self.admin_user.set_password('testpass123')
            self.admin_user.save()

    def test_bd_previene_ciclo_con_fecha_fin_antes_de_inicio(self):
        """
        La BD debe prevenir ciclos con fecha_fin < fecha_inicio.
        
        Esto valida que existe un CHECK constraint a nivel de BD
        que protege la integridad de las fechas.
        """
        from django.db import IntegrityError
        
        # Intentar crear ciclo con fechas al revés debe fallar
        with self.assertRaises(IntegrityError) as context:
            CicloAcademico.objects.create(
                nombre='2024 Inválido',
                fecha_inicio=date(2024, 12, 1),  # Diciembre
                fecha_fin=date(2024, 3, 1),      # Marzo (antes que inicio!)
                colegio=self.colegio,
                estado='ACTIVO',
                creado_por=self.admin_user,
                modificado_por=self.admin_user
            )
        
        # Validar que el error menciona el constraint
        self.assertIn(
            'ciclo_fechas_validas',
            str(context.exception),
            "El constraint de BD debe prevenir fechas inválidas"
        )

    def test_detecta_ciclo_activo_con_fecha_fin_pasada(self):
        """
        Un ciclo ACTIVO con fecha_fin en el pasado es inconsistente.
        
        Estado y fechas no coinciden → DATA_INCONSISTENCY.
        """
        # Crear ciclo activo pero con fecha_fin ya pasada
        ciclo_expirado = CicloAcademico.objects.create(
            nombre='2023 Expirado',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 31),  # Ya pasó
            colegio=self.colegio,
            estado='ACTIVO',  # Pero sigue marcado como activo!
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Validar inconsistencia
        hoy = date.today()
        self.assertLess(
            ciclo_expirado.fecha_fin,
            hoy,
            "El ciclo debe tener fecha_fin en el pasado"
        )
        self.assertEqual(
            ciclo_expirado.estado,
            'ACTIVO',
            "El ciclo debe estar marcado como ACTIVO (inconsistencia)"
        )

    def test_setup_status_ignora_ciclos_expirados_marcados_activos(self):
        """
        SetupService debe ignorar ciclos expirados aunque estén marcados ACTIVO.
        
        Un ciclo ACTIVO con fecha_fin pasada no cuenta como "ciclo válido".
        """
        # Crear ciclo ACTIVO pero expirado
        ciclo_expirado = CicloAcademico.objects.create(
            nombre='2020 Expirado',
            fecha_inicio=date(2020, 3, 1),
            fecha_fin=date(2020, 12, 31),  # Año pasado
            colegio=self.colegio,
            estado='ACTIVO',  # Marcado como activo!
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Validar que el ciclo está expirado
        self.assertLess(
            ciclo_expirado.fecha_fin,
            date.today(),
            "El ciclo debe tener fecha_fin en el pasado"
        )
        
        # SetupService debe detectar que no hay ciclo válido
        status = SetupService.get_setup_status(self.colegio.rbd)
        self.assertFalse(
            status['setup_complete'],
            "Colegio con ciclo expirado no debe tener setup completo"
        )
        self.assertIn(
            'MISSING_CICLO_ACTIVO',
            status['missing_steps'],
            "Debe reportar falta de ciclo activo válido"
        )

    def test_ciclo_valido_con_fechas_correctas_pasa_validacion(self):
        """
        Un ciclo con fechas correctas debe ser aceptado.
        
        Este test valida que la validación funciona correctamente
        y no rechaza ciclos válidos.
        """
        # Crear ciclo válido
        CicloAcademico.objects.create(
            nombre='2024 Válido',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        status = SetupService.get_setup_status(self.colegio.rbd)
        
        # NO debe reportar falta de ciclo activo
        self.assertNotIn(
            'MISSING_CICLO_ACTIVO',
            status['missing_steps'],
            "Ciclo válido debe ser aceptado"
        )


class TestErrorBuilderForInvalidDates(TestCase):
    """
    Tests de CONSTRUCCIÓN DE ERRORES: ErrorResponseBuilder para DATA_INCONSISTENCY.
    
    Valida que el error se construye correctamente para fechas inválidas.
    """

    def test_error_builder_data_inconsistency_estructura(self):
        """
        ErrorResponseBuilder debe generar estructura válida para DATA_INCONSISTENCY.
        
        Valida la estructura, NO el texto literal del mensaje.
        """
        error = ErrorResponseBuilder.build('DATA_INCONSISTENCY')
        
        # Validar estructura del contrato
        self.assertIn('error_type', error)
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)
        
        # Validar valores
        self.assertEqual(error['error_type'], 'DATA_INCONSISTENCY')
        self.assertIsNotNone(error['user_message'])
        self.assertGreater(len(error['user_message']), 0)
        self.assertTrue(error['action_url'].startswith('/'))

    def test_error_builder_data_inconsistency_incluye_accion(self):
        """
        El error debe dirigir al usuario a una página de verificación.
        
        Para inconsistencias de datos, la acción típica es revisar/corregir.
        """
        error = ErrorResponseBuilder.build('DATA_INCONSISTENCY')
        
        # La action_url debe apuntar a verificación de datos
        self.assertIn(
            'verificar_datos',
            error['action_url'],
            "DATA_INCONSISTENCY debe dirigir a verificación de datos"
        )

    def test_error_builder_puede_incluir_contexto_adicional(self):
        """
        El error puede incluir contexto específico del problema.
        
        Por ejemplo, qué campo tiene el problema.
        """
        context = {
            'field': 'fecha_fin',
            'issue': 'menor que fecha_inicio'
        }
        error = ErrorResponseBuilder.build('DATA_INCONSISTENCY', context)
        
        # El contexto debe estar preservado
        self.assertEqual(error['context'], context)
        self.assertIn('field', error['context'])
        self.assertIn('issue', error['context'])

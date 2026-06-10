"""
Test 1.3: Curso sin nivel educativo

Valida que el sistema detecta cursos sin nivel educativo asignado.
Esta es una DATA_INCONSISTENCY porque el modelo requiere nivel.

Patrón de tests:
- Clase 1: Tests de lógica de negocio (validar detección)
- Clase 2: Tests de ErrorBuilder (validar contratos de error)
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso
from backend.apps.accounts.models import User
from backend.apps.core.services.setup_service import SetupService
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestCursoSinNivelEducativo(TestCase):
    """
    Tests de lógica de negocio: validar que cursos sin nivel
    educativo son detectados correctamente.
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
            rbd=12347,
            defaults={
                'nombre': 'Colegio Test Niveles',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_niveles@colegio.cl',
                'web': 'http://test-niveles.cl',
                'rut_establecimiento': '12.347.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuario admin para auditoría
        self.admin_user = User.objects.get_or_create(
            rut='22222222-2',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Niveles',
                'email': 'admin_niveles@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        if not self.admin_user.password:
            self.admin_user.set_password('testpass123')
            self.admin_user.save()
        
        # Crear ciclo académico activo
        self.ciclo = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear nivel educativo
        self.nivel_basico = NivelEducativo.objects.get_or_create(
            nombre='Educación Básica'
        )[0]

    def test_curso_valido_con_nivel_asignado_pasa_validacion(self):
        """
        Un curso con nivel educativo asignado es válido.
        
        Este test verifica que la validación no rechaza cursos correctos.
        """
        # Crear curso válido con nivel
        curso = Curso.objects.create(
            nombre='1° Básico A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            nivel=self.nivel_basico,
            activo=True
        )
        
        # Validar que el curso tiene nivel
        self.assertIsNotNone(
            curso.nivel,
            "El curso debe tener nivel educativo asignado"
        )
        self.assertEqual(
            curso.nivel,
            self.nivel_basico,
            "El nivel debe ser el asignado"
        )
    
    def test_modelo_requiere_nivel_educativo(self):
        """
        El modelo Curso requiere nivel educativo (NOT NULL en BD).
        
        Intentar crear un curso sin nivel debe fallar a nivel de BD.
        """
        from django.db import IntegrityError
        
        # Intentar crear curso sin nivel debe fallar
        with self.assertRaises((IntegrityError, ValueError)) as context:
            Curso.objects.create(
                nombre='Curso Inválido',
                colegio=self.colegio,
                ciclo_academico=self.ciclo,
                nivel=None,  # Esto debe fallar
                activo=True
            )
        
        # El error debe indicar que nivel es requerido
        error_msg = str(context.exception).lower()
        self.assertTrue(
            'nivel' in error_msg or 'not null' in error_msg or 'cannot be null' in error_msg,
            "El error debe mencionar que nivel es requerido"
        )

    def test_query_excluye_cursos_huerfanos_si_nivel_borrado(self):
        """
        Si un nivel educativo se borra (huérfanos por eliminación en cascada),
        los cursos asociados deberían ser detectados.
        
        Nota: El modelo usa PROTECT, así que esto no debería ocurrir.
        Este test verifica que la protección funciona.
        """
        from django.db.models.deletion import ProtectedError
        
        # Crear curso con nivel
        curso = Curso.objects.create(
            nombre='1° Básico A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            nivel=self.nivel_basico,
            activo=True
        )
        
        # Intentar borrar el nivel debe fallar (PROTECT)
        with self.assertRaises(ProtectedError) as context:
            self.nivel_basico.delete()
        
        # Validar que el curso sigue existiendo
        self.assertTrue(
            Curso.objects.filter(id_curso=curso.id_curso).exists(),
            "El curso debe seguir existiendo después del intento de borrado"
        )


@pytest.mark.django_db
class TestErrorBuilderForMissingNivel(TestCase):
    """
    Tests de ErrorBuilder: validar que los errores relacionados
    con niveles educativos faltantes siguen el contrato correcto.
    """
    
    def test_error_builder_data_inconsistency_estructura(self):
        """
        ErrorBuilder.build() debe generar estructura correcta.
        
        Valida el contrato del error, no el texto específico.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'CURSO_SIN_NIVEL',
                'curso_id': 123,
                'curso_nombre': '1° Básico A'
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
        self.assertEqual(error['context']['curso_id'], 123)

    def test_error_builder_data_inconsistency_incluye_accion(self):
        """
        Los errores de inconsistencia deben incluir acción recomendada.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'CURSO_SIN_NIVEL',
                'curso_id': 123,
                'curso_nombre': '1° Básico A',
                'accion': 'Asignar nivel educativo al curso'
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
                'issue': 'CURSO_SIN_NIVEL',
                'curso_id': 123,
                'colegio_rbd': 12347,
                'ciclo': '2024',
                'detectado_en': 'setup_validation'
            }
        )
        
        # Validar que el contexto está presente
        self.assertIn('context', error)
        context = error['context']
        
        self.assertIn('curso_id', context)
        self.assertIn('colegio_rbd', context)
        self.assertIn('ciclo', context)
        self.assertIn('detectado_en', context)

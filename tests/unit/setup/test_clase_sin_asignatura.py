"""
Test 1.4: Clase sin asignatura vinculada

Valida que el sistema detecta clases sin asignatura asignada.
Esta es una DATA_INCONSISTENCY porque el modelo requiere asignatura.

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
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.accounts.models import User
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestClaseSinAsignatura(TestCase):
    """
    Tests de lógica de negocio: validar que clases sin asignatura
    son detectadas correctamente.
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
            rbd=12348,
            defaults={
                'nombre': 'Colegio Test Clases',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_clases@colegio.cl',
                'web': 'http://test-clases.cl',
                'rut_establecimiento': '12.348.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuario admin para auditoría
        self.admin_user = User.objects.get_or_create(
            rut='33333333-3',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Clases',
                'email': 'admin_clases@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        if not self.admin_user.password:
            self.admin_user.set_password('testpass123')
            self.admin_user.save()
        
        # Crear profesor
        self.profesor = User.objects.get_or_create(
            rut='44444444-4',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Test',
                'email': 'profesor@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        if not self.profesor.password:
            self.profesor.set_password('testpass123')
            self.profesor.save()
        
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
        
        # Crear nivel educativo y curso
        self.nivel_basico = NivelEducativo.objects.get_or_create(
            nombre='Educación Básica'
        )[0]
        
        self.curso = Curso.objects.create(
            nombre='1° Básico A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            nivel=self.nivel_basico,
            activo=True
        )
        
        # Crear asignatura
        self.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            colegio=self.colegio,
            horas_semanales=5,
            activa=True
        )

    def test_clase_valida_con_asignatura_pasa_validacion(self):
        """
        Una clase con asignatura asignada es válida.
        
        Este test verifica que la validación no rechaza clases correctas.
        """
        # Crear clase válida con asignatura
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )
        
        # Validar que la clase tiene asignatura
        self.assertIsNotNone(
            clase.asignatura,
            "La clase debe tener asignatura asignada"
        )
        self.assertEqual(
            clase.asignatura,
            self.asignatura,
            "La asignatura debe ser la asignada"
        )

    def test_modelo_requiere_asignatura(self):
        """
        El modelo Clase requiere asignatura (NOT NULL en BD).
        
        Intentar crear una clase sin asignatura debe fallar a nivel de BD.
        """
        from django.db import IntegrityError
        from django.core.exceptions import ObjectDoesNotExist
        
        # Intentar crear clase sin asignatura debe fallar
        with self.assertRaises((IntegrityError, ValueError, ObjectDoesNotExist)) as context:
            Clase.objects.create(
                colegio=self.colegio,
                curso=self.curso,
                asignatura=None,  # Esto debe fallar
                profesor=self.profesor,
                activo=True
            )
        
        # El error debe indicar que asignatura es requerida
        error_msg = str(context.exception).lower()
        self.assertTrue(
            'asignatura' in error_msg or 'not null' in error_msg or 'cannot be null' in error_msg,
            "El error debe mencionar que asignatura es requerida"
        )

    def test_query_excluye_clases_huerfanas_si_asignatura_borrada(self):
        """
        Si una asignatura se borra (CASCADE), las clases asociadas
        también deberían borrarse automáticamente.
        
        Este test verifica que CASCADE funciona correctamente.
        """
        # Crear clase con asignatura
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )
        
        clase_id = clase.id
        
        # Borrar la asignatura (CASCADE debe eliminar la clase)
        self.asignatura.delete()
        
        # Validar que la clase ya no existe
        self.assertFalse(
            Clase.objects.filter(id=clase_id).exists(),
            "La clase debe ser eliminada cuando se borra su asignatura (CASCADE)"
        )


@pytest.mark.django_db
class TestErrorBuilderForMissingAsignatura(TestCase):
    """
    Tests de ErrorBuilder: validar que los errores relacionados
    con asignaturas faltantes siguen el contrato correcto.
    """
    
    def test_error_builder_data_inconsistency_estructura(self):
        """
        ErrorBuilder.build() debe generar estructura correcta.
        
        Valida el contrato del error, no el texto específico.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'CLASE_SIN_ASIGNATURA',
                'clase_id': 123,
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
        self.assertEqual(error['context']['clase_id'], 123)

    def test_error_builder_data_inconsistency_incluye_accion(self):
        """
        Los errores de inconsistencia deben incluir acción recomendada.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'CLASE_SIN_ASIGNATURA',
                'clase_id': 123,
                'curso_nombre': '1° Básico A',
                'accion': 'Asignar asignatura a la clase'
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
                'issue': 'CLASE_SIN_ASIGNATURA',
                'clase_id': 123,
                'colegio_rbd': 12348,
                'ciclo': '2024',
                'detectado_en': 'clase_validation'
            }
        )
        
        # Validar que el contexto está presente
        self.assertIn('context', error)
        context = error['context']
        
        self.assertIn('clase_id', context)
        self.assertIn('colegio_rbd', context)
        self.assertIn('ciclo', context)
        self.assertIn('detectado_en', context)

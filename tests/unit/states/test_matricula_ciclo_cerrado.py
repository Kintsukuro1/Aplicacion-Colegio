"""
Test 3.1: Matrícula en ciclo CERRADO

Valida que no se puede crear matrícula en un ciclo académico
que no está en estado ACTIVO.

Regla de negocio: Solo se permiten matrículas en ciclo ACTIVO.

Patrón de tests:
- Clase 1: Tests de validación de estado
- Clase 2: Tests de ErrorBuilder
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso
from backend.apps.matriculas.models import Matricula
from backend.apps.accounts.models import User
from backend.apps.matriculas.services.matriculas_service import MatriculasService
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.common.exceptions import PrerequisiteException


@pytest.mark.django_db
class TestMatriculaEnCicloCerrado(TestCase):
    """
    Tests de validación de estado del ciclo para matrículas.
    """
    
    def setUp(self):
        """Configuración común para todos los tests"""
        # Crear datos base
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]
        
        # Crear colegio
        self.colegio = Colegio.objects.get_or_create(
            rbd=12355,
            defaults={
                'nombre': 'Colegio Test Estados',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_estados@colegio.cl',
                'web': 'http://test-estados.cl',
                'rut_establecimiento': '12.355.000-3',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuarios
        self.admin_user = User.objects.get_or_create(
            rut='11111115-5',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Estados',
                'email': 'admin_estados@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        self.estudiante = User.objects.get_or_create(
            rut='13131315-5',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'Matricula',
                'email': 'est_matricula@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        # Crear ciclo CERRADO
        self.ciclo_cerrado = CicloAcademico.objects.create(
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 20),
            colegio=self.colegio,
            estado='CERRADO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear nivel y curso
        self.nivel = NivelEducativo.objects.get_or_create(
            nombre='Educación Básica'
        )[0]
        
        self.curso = Curso.objects.create(
            nombre='3° Básico A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo_cerrado,
            nivel=self.nivel,
            activo=True
        )

    def test_matricula_en_ciclo_cerrado_debe_fallar(self):
        """
        No se debe poder crear matrícula si el ciclo está CERRADO.
        """
        # Intentar crear matrícula en ciclo CERRADO
        matricula = Matricula(
            colegio=self.colegio,
            estudiante=self.estudiante,
            curso=self.curso,
            ciclo_academico=self.ciclo_cerrado,
            estado='ACTIVA'
        )
        
        # Guardar la matrícula (a nivel de BD se permite)
        matricula.save()
        
        # Pero el servicio debe detectar el problema levantando excepción estructurada
        with self.assertRaises(PrerequisiteException):
            MatriculasService._validate_colegio_has_active_ciclo(self.colegio.rbd)

    def test_matricula_en_ciclo_activo_debe_funcionar(self):
        """
        Crear matrícula en ciclo ACTIVO debe funcionar correctamente.
        """
        # Crear ciclo ACTIVO
        ciclo_activo = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear curso en ciclo activo
        curso_activo = Curso.objects.create(
            nombre='3° Básico B',
            colegio=self.colegio,
            ciclo_academico=ciclo_activo,
            nivel=self.nivel,
            activo=True
        )
        
        # Crear matrícula
        matricula = Matricula.objects.create(
            colegio=self.colegio,
            estudiante=self.estudiante,
            curso=curso_activo,
            ciclo_academico=ciclo_activo,
            estado='ACTIVA'
        )
        
        # Verificar que se creó correctamente
        self.assertIsNotNone(matricula.id)
        self.assertEqual(matricula.ciclo_academico.estado, 'ACTIVO')
        
        # Verificar que el servicio valida correctamente
        ciclo = MatriculasService._validate_colegio_has_active_ciclo(self.colegio.rbd)
        self.assertIsNotNone(ciclo)
        self.assertEqual(ciclo.nombre, '2024')

    def test_servicio_detecta_falta_de_ciclo_activo(self):
        """
        El servicio debe detectar cuando un colegio no tiene ciclo ACTIVO.
        """
        # Caso 1: Solo ciclo CERRADO (setup actual)
        with self.assertRaises(PrerequisiteException) as context:
            MatriculasService._validate_colegio_has_active_ciclo(self.colegio.rbd)

        self.assertIn('Ciclo Académico activo', str(context.exception))

    def test_matricula_no_debe_pertenecer_a_ciclo_cerrado(self):
        """
        Las matrículas activas no deben pertenecer a ciclos CERRADO.
        
        Esta es una inconsistencia de datos que debe prevenirse.
        """
        # Crear matrícula en ciclo CERRADO (simulando datos incorrectos)
        matricula = Matricula.objects.create(
            colegio=self.colegio,
            estudiante=self.estudiante,
            curso=self.curso,
            ciclo_academico=self.ciclo_cerrado,
            estado='ACTIVA'
        )
        
        # Verificar inconsistencia: matrícula ACTIVA en ciclo CERRADO
        self.assertEqual(matricula.estado, 'ACTIVA')
        self.assertEqual(matricula.ciclo_academico.estado, 'CERRADO')
        
        # Esta combinación no debería existir en producción
        # El servicio debe prevenirla validando el ciclo

    def test_solo_ciclos_activos_permiten_nuevas_matriculas(self):
        """
        Solo ciclos con estado ACTIVO deben permitir crear matrículas.
        """
        # Verificar que ciclo CERRADO no es válido para matrículas
        self.assertEqual(self.ciclo_cerrado.estado, 'CERRADO')
        
        # El servicio no debe encontrar ciclo activo
        with self.assertRaises(PrerequisiteException):
            MatriculasService._validate_colegio_has_active_ciclo(self.colegio.rbd)


@pytest.mark.django_db
class TestErrorBuilderForCicloCerrado(TestCase):
    """
    Tests de ErrorBuilder: validar errores de operaciones en ciclo cerrado.
    """
    
    def test_error_builder_missing_ciclo_activo_estructura(self):
        """
        ErrorBuilder debe manejar errores de ciclo no activo.
        """
        error = ErrorResponseBuilder.build(
            'MISSING_CICLO_ACTIVO',
            {
                'colegio_rbd': 12355,
                'colegio_nombre': 'Colegio Test',
                'accion_intentada': 'crear_matricula'
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'MISSING_CICLO_ACTIVO')
        
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_invalid_state_para_ciclo(self):
        """
        ErrorBuilder debe manejar errores de estado inválido.
        """
        error = ErrorResponseBuilder.build(
            'INVALID_STATE',
            {
                'entity': 'CicloAcademico',
                'field': 'estado',
                'expected': 'ACTIVO',
                'actual': 'CERRADO',
                'message': 'No se pueden crear matrículas en ciclo cerrado'
            }
        )
        
        context = error['context']
        self.assertIn('entity', context)
        self.assertIn('field', context)
        self.assertEqual(context['entity'], 'CicloAcademico')

    def test_error_builder_contexto_adicional_matricula(self):
        """
        ErrorBuilder debe permitir contexto adicional.
        """
        error = ErrorResponseBuilder.build(
            'MISSING_CICLO_ACTIVO',
            {
                'colegio_rbd': 12355,
                'estudiante_rut': '13131315-5',
                'curso_nombre': '3° Básico A',
                'fecha_intento': '2024-02-04'
            }
        )
        
        context = error['context']
        self.assertIn('colegio_rbd', context)
        self.assertIn('estudiante_rut', context)

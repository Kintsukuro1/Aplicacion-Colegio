"""
Test 2.1: Matrícula con curso eliminado (PROTECT)

Valida que el sistema protege contra eliminación de cursos
que tienen matrículas asociadas.

Regla: No se puede borrar un curso si tiene matrículas activas.

Patrón de tests:
- Clase 1: Tests de protección de integridad referencial
- Clase 2: Tests de ErrorBuilder
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase
from django.db.models.deletion import ProtectedError
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso
from backend.apps.matriculas.models import Matricula
from backend.apps.accounts.models import User
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestMatriculaProteccionCurso(TestCase):
    """
    Tests de integridad referencial: validar que PROTECT
    impide borrar cursos con matrículas.
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
            rbd=12350,
            defaults={
                'nombre': 'Colegio Test Matrículas',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_matriculas@colegio.cl',
                'web': 'http://test-matriculas.cl',
                'rut_establecimiento': '12.350.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuario admin
        self.admin_user = User.objects.get_or_create(
            rut='66666666-6',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Matrículas',
                'email': 'admin_mat@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        if not self.admin_user.password:
            self.admin_user.set_password('testpass123')
            self.admin_user.save()
        
        # Crear estudiante
        self.estudiante = User.objects.get_or_create(
            rut='77777777-7',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'Test',
                'email': 'estudiante@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        # Crear ciclo académico
        self.ciclo = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear nivel y curso
        self.nivel = NivelEducativo.objects.get_or_create(
            nombre='Educación Básica'
        )[0]
        
        self.curso = Curso.objects.create(
            nombre='1° Básico A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            nivel=self.nivel,
            activo=True
        )

    def test_protect_impide_borrar_curso_con_matriculas(self):
        """
        PROTECT debe impedir borrar un curso que tiene matrículas.
        
        Esta es la protección correcta de integridad referencial.
        """
        # Crear matrícula vinculada al curso
        matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Intentar borrar el curso debe fallar
        with self.assertRaises(ProtectedError) as context:
            self.curso.delete()
        
        # Validar que el curso sigue existiendo
        self.assertTrue(
            Curso.objects.filter(id_curso=self.curso.id_curso).exists(),
            "El curso debe seguir existiendo (PROTECT)"
        )
        
        # Validar que la matrícula sigue existiendo
        self.assertTrue(
            Matricula.objects.filter(id=matricula.id).exists(),
            "La matrícula debe seguir existiendo"
        )

    def test_puede_borrar_curso_sin_matriculas(self):
        """
        Un curso sin matrículas SÍ puede ser borrado.
        """
        curso_id = self.curso.id_curso
        
        # Borrar curso sin matrículas debe funcionar
        self.curso.delete()
        
        # Validar que el curso fue eliminado
        self.assertFalse(
            Curso.objects.filter(id_curso=curso_id).exists(),
            "El curso debe haber sido eliminado"
        )

    def test_matricula_huerfana_tras_eliminar_curso_es_imposible(self):
        """
        No deben existir matrículas huérfanas (sin curso).
        
        PROTECT garantiza que esto nunca ocurra.
        """
        # Crear matrícula
        Matricula.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            curso=self.curso,
            ciclo_academico=self.ciclo,
            estado='ACTIVA'
        )
        
        # Intentar borrar curso debe fallar
        with self.assertRaises(ProtectedError):
            self.curso.delete()
        
        # Validar que NO existen matrículas huérfanas
        matriculas_huerfanas = Matricula.objects.filter(
            colegio=self.colegio,
            curso__isnull=True
        ).exclude(
            curso=self.curso  # Excluir las que tienen curso válido
        )
        
        self.assertEqual(
            matriculas_huerfanas.count(),
            0,
            "No deben existir matrículas sin curso (huérfanas)"
        )

    def test_query_detecta_matriculas_vinculadas(self):
        """
        Se puede consultar cuántas matrículas tiene un curso.
        
        Útil para validar antes de intentar borrar.
        """
        # Crear 3 matrículas en el mismo curso
        for i in range(3):
            estudiante = User.objects.create(
                rut=f'8888888{i}-{i}',
                nombre=f'Estudiante{i}',
                apellido_paterno='Test',
                email=f'est{i}@test.cl',
                rbd_colegio=self.colegio.rbd
            )
            
            Matricula.objects.create(
                estudiante=estudiante,
                colegio=self.colegio,
                curso=self.curso,
                ciclo_academico=self.ciclo,
                estado='ACTIVA'
            )
        
        # Consultar matrículas del curso
        count = self.curso.matriculas.count()
        
        self.assertEqual(
            count,
            3,
            "El curso debe tener 3 matrículas"
        )
        
        # No se puede borrar
        with self.assertRaises(ProtectedError):
            self.curso.delete()


@pytest.mark.django_db
class TestErrorBuilderForProtectedRelations(TestCase):
    """
    Tests de ErrorBuilder: validar errores de relaciones protegidas.
    """
    
    def test_error_builder_protected_relation_estructura(self):
        """
        ErrorBuilder debe manejar errores de relaciones protegidas.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'PROTECTED_RELATION',
                'entity': 'Curso',
                'entity_id': 123,
                'related_count': 5,
                'related_entity': 'Matricula'
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'DATA_INCONSISTENCY')
        
        self.assertIn('user_message', error)
        self.assertIsInstance(error['user_message'], str)
        
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_relaciones(self):
        """
        El error debe incluir información sobre las relaciones.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'PROTECTED_RELATION',
                'entity': 'Curso',
                'entity_id': 123,
                'related_count': 5,
                'related_entity': 'Matricula',
                'accion': 'Reasignar o eliminar matrículas antes de borrar curso'
            }
        )
        
        context = error['context']
        self.assertIn('entity', context)
        self.assertIn('related_count', context)
        self.assertEqual(context['related_count'], 5)

    def test_error_builder_contexto_adicional(self):
        """
        ErrorBuilder debe permitir contexto adicional.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'PROTECTED_RELATION',
                'entity': 'Curso',
                'entity_id': 123,
                'colegio_rbd': 12350,
                'ciclo': '2024'
            }
        )
        
        context = error['context']
        self.assertIn('entity_id', context)
        self.assertIn('colegio_rbd', context)

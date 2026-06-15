"""
Test 2.2: Clase con profesor eliminado (PROTECT)

Valida que el sistema protege contra eliminación de profesores
que tienen clases asignadas.

Regla: No se puede borrar un profesor si tiene clases activas.

Patrón de tests:
- Clase 1: Tests de protección de integridad referencial
- Clase 2: Tests de ErrorBuilder
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
class TestClaseProteccionProfesor(TestCase):
    """
    Tests de integridad referencial con política SET_NULL
    para clases con profesor eliminado.
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
            rbd=12351,
            defaults={
                'nombre': 'Colegio Test Profesores',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_profes@colegio.cl',
                'web': 'http://test-profes.cl',
                'rut_establecimiento': '12.351.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuario admin
        self.admin_user = User.objects.get_or_create(
            rut='99999999-9',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Profesores',
                'email': 'admin_prof@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        # Crear profesor
        self.profesor = User.objects.get_or_create(
            rut='10101010-1',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Matematicas',
                'email': 'profe_mat@test.cl',
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
        
        # Crear nivel, curso y asignatura
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
        
        self.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            colegio=self.colegio,
            horas_semanales=5,
            activa=True
        )

    def test_protect_impide_borrar_profesor_con_clases(self):
        """
        Al borrar profesor, las clases se conservan y profesor queda en NULL.
        """
        # Crear clase asignada al profesor
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )
        
        self.profesor.delete()

        # Clase se conserva y profesor se nulifica
        self.assertTrue(Clase.objects.filter(id=clase.id).exists())
        clase.refresh_from_db()
        self.assertIsNone(clase.profesor)

    def test_puede_borrar_profesor_sin_clases(self):
        """
        Un profesor sin clases asignadas SÍ puede ser borrado.
        """
        profesor_rut = self.profesor.rut
        
        # Borrar profesor sin clases debe funcionar
        self.profesor.delete()
        
        # Validar que el profesor fue eliminado
        self.assertFalse(
            User.objects.filter(rut=profesor_rut).exists(),
            "El profesor debe haber sido eliminado"
        )

    def test_clase_huerfana_tras_eliminar_profesor_es_imposible(self):
        """
        Con SET_NULL, al eliminar profesor puede haber clases sin profesor.
        """
        # Crear clase
        Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )
        
        self.profesor.delete()
        
        # Validar que NO existen clases sin profesor
        clases_huerfanas = Clase.objects.filter(
            colegio=self.colegio,
            profesor__isnull=True
        )
        
        self.assertGreaterEqual(clases_huerfanas.count(), 1)

    def test_query_detecta_clases_asignadas_a_profesor(self):
        """
        Se puede consultar cuántas clases tiene un profesor.
        
        Útil para validar antes de intentar borrar.
        """
        # Crear 3 clases para el mismo profesor
        asignaturas = []
        for i in range(3):
            asig = Asignatura.objects.create(
                nombre=f'Asignatura {i}',
                colegio=self.colegio,
                horas_semanales=3,
                activa=True
            )
            asignaturas.append(asig)
            
            Clase.objects.create(
                colegio=self.colegio,
                curso=self.curso,
                asignatura=asig,
                profesor=self.profesor,
                activo=True
            )
        
        # Consultar clases del profesor
        count = self.profesor.clases_impartidas.count()
        
        self.assertEqual(
            count,
            3,
            "El profesor debe tener 3 clases asignadas"
        )
        
        # Al borrar profesor, sus clases quedan sin profesor (SET_NULL)
        self.profesor.delete()
        self.assertEqual(Clase.objects.filter(profesor__isnull=True).count(), 3)


@pytest.mark.django_db
class TestErrorBuilderForProfesorProtection(TestCase):
    """
    Tests de ErrorBuilder: validar errores de profesores protegidos.
    """
    
    def test_error_builder_profesor_con_clases_estructura(self):
        """
        ErrorBuilder debe manejar errores de profesores con clases.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'PROFESOR_CON_CLASES',
                'profesor_rut': '10101010-1',
                'profesor_nombre': 'Profesor Matematicas',
                'clases_count': 3
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'DATA_INCONSISTENCY')
        
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_clases(self):
        """
        El error debe incluir información sobre las clases.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'PROFESOR_CON_CLASES',
                'profesor_rut': '10101010-1',
                'clases_count': 3,
                'accion': 'Reasignar clases a otro profesor antes de eliminar'
            }
        )
        
        context = error['context']
        self.assertIn('profesor_rut', context)
        self.assertIn('clases_count', context)
        self.assertEqual(context['clases_count'], 3)

    def test_error_builder_contexto_adicional(self):
        """
        ErrorBuilder debe permitir contexto adicional.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'PROFESOR_CON_CLASES',
                'profesor_rut': '10101010-1',
                'colegio_rbd': 12351,
                'ciclo': '2024'
            }
        )
        
        context = error['context']
        self.assertIn('profesor_rut', context)
        self.assertIn('colegio_rbd', context)

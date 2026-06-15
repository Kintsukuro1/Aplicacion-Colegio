"""
Test 2.3: Evaluación sin clase padre (CASCADE)

Valida que cuando se borra una clase, las evaluaciones
asociadas también se borran automáticamente (CASCADE).

Regla: Las evaluaciones dependen de su clase padre.

Patrón de tests:
- Clase 1: Tests de limpieza automática (CASCADE)
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
from backend.apps.academico.models import Evaluacion
from backend.apps.accounts.models import User
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestEvaluacionCascadeClase(TestCase):
    """
    Tests de CASCADE: validar que borrar clase elimina evaluaciones.
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
            rbd=12352,
            defaults={
                'nombre': 'Colegio Test Evaluaciones',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_eval@colegio.cl',
                'web': 'http://test-eval.cl',
                'rut_establecimiento': '12.352.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuarios
        self.admin_user = User.objects.get_or_create(
            rut='11111112-2',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Eval',
                'email': 'admin_eval@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        self.profesor = User.objects.get_or_create(
            rut='12121212-1',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Ciencias',
                'email': 'profe_cie@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        # Crear ciclo, nivel, curso, asignatura
        self.ciclo = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
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
            nombre='Ciencias Naturales',
            colegio=self.colegio,
            horas_semanales=4,
            activa=True
        )
        
        self.clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )

    def test_cascade_borra_evaluaciones_al_borrar_clase(self):
        """
        CASCADE debe borrar evaluaciones cuando se borra la clase.
        
        Esta es la limpieza automática correcta.
        """
        # Crear evaluación vinculada a la clase
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre='Prueba 1',
            fecha_evaluacion=date.today(),
            ponderacion=100.0,
            tipo_evaluacion='sumativa'
        )
        
        evaluacion_id = evaluacion.id_evaluacion
        
        # Borrar la clase
        self.clase.delete()
        
        # Validar que la clase fue eliminada
        self.assertFalse(
            Clase.objects.filter(id=self.clase.id).exists(),
            "La clase debe haber sido eliminada"
        )
        
        # Validar que la evaluación también fue eliminada (CASCADE)
        self.assertFalse(
            Evaluacion.objects.filter(id_evaluacion=evaluacion_id).exists(),
            "La evaluación debe haber sido eliminada automáticamente (CASCADE)"
        )

    def test_clase_sin_evaluaciones_puede_borrarse(self):
        """
        Una clase sin evaluaciones SÍ puede ser borrada.
        """
        clase_id = self.clase.id
        
        # Borrar clase sin evaluaciones debe funcionar
        self.clase.delete()
        
        # Validar que la clase fue eliminada
        self.assertFalse(
            Clase.objects.filter(id=clase_id).exists(),
            "La clase debe haber sido eliminada"
        )

    def test_evaluaciones_huerfanas_no_deben_existir(self):
        """
        No deben existir evaluaciones sin clase padre.
        
        CASCADE garantiza que esto nunca ocurra.
        """
        # Crear evaluaciones
        for i in range(3):
            Evaluacion.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                nombre=f'Prueba {i+1}',
                fecha_evaluacion=date.today(),
                ponderacion=100.0,
                tipo_evaluacion='sumativa'
            )
        
        # Borrar clase (CASCADE debe eliminar evaluaciones)
        self.clase.delete()
        
        # Validar que NO existen evaluaciones huérfanas
        evaluaciones_huerfanas = Evaluacion.objects.filter(
            colegio=self.colegio,
            clase__isnull=True
        )
        
        self.assertEqual(
            evaluaciones_huerfanas.count(),
            0,
            "No deben existir evaluaciones sin clase (huérfanas)"
        )

    def test_cascade_borra_multiples_evaluaciones(self):
        """
        CASCADE debe borrar todas las evaluaciones de una clase.
        """
        # Crear 5 evaluaciones para la misma clase
        evaluacion_ids = []
        for i in range(5):
            eval = Evaluacion.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                nombre=f'Evaluación {i+1}',
                fecha_evaluacion=date.today() + timedelta(days=i*7),
                ponderacion=20.0,
                tipo_evaluacion='sumativa'
            )
            evaluacion_ids.append(eval.id_evaluacion)
        
        # Verificar que existen 5 evaluaciones
        self.assertEqual(
            Evaluacion.objects.filter(clase=self.clase).count(),
            5,
            "Debe haber 5 evaluaciones antes de borrar"
        )
        
        # Borrar la clase
        self.clase.delete()
        
        # Validar que NINGUNA evaluación existe
        for eval_id in evaluacion_ids:
            self.assertFalse(
                Evaluacion.objects.filter(id_evaluacion=eval_id).exists(),
                f"Evaluación {eval_id} debe haber sido eliminada"
            )


@pytest.mark.django_db
class TestErrorBuilderForOrphanedEvaluations(TestCase):
    """
    Tests de ErrorBuilder: validar errores de evaluaciones huérfanas.
    """
    
    def test_error_builder_evaluacion_huerfana_estructura(self):
        """
        ErrorBuilder debe manejar errores de evaluaciones huérfanas.
        
        Nota: Esto NO debería ocurrir por CASCADE, pero el error
        debe estar definido por si acaso.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'EVALUACION_HUERFANA',
                'evaluacion_id': 123,
                'evaluacion_nombre': 'Prueba 1',
                'clase_esperada': None
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'DATA_INCONSISTENCY')
        
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_evaluacion(self):
        """
        El error debe incluir información sobre la evaluación.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'EVALUACION_HUERFANA',
                'evaluacion_id': 123,
                'evaluacion_nombre': 'Prueba 1',
                'accion': 'Asignar clase o eliminar evaluación'
            }
        )
        
        context = error['context']
        self.assertIn('evaluacion_id', context)
        self.assertIn('evaluacion_nombre', context)

    def test_error_builder_contexto_adicional(self):
        """
        ErrorBuilder debe permitir contexto adicional.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'EVALUACION_HUERFANA',
                'evaluacion_id': 123,
                'colegio_rbd': 12352,
                'fecha_deteccion': '2024-02-04'
            }
        )
        
        context = error['context']
        self.assertIn('evaluacion_id', context)
        self.assertIn('colegio_rbd', context)

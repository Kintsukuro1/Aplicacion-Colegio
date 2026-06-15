"""
Test 2.4: Calificación sin estudiante (CASCADE)

Valida que cuando se borra un estudiante, las calificaciones
asociadas también se borran automáticamente (CASCADE).

Regla: Las calificaciones dependen del estudiante.

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
from backend.apps.academico.models import Evaluacion, Calificacion
from backend.apps.accounts.models import User
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestCalificacionCascadeEstudiante(TestCase):
    """
    Tests de CASCADE: validar que borrar estudiante elimina calificaciones.
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
            rbd=12353,
            defaults={
                'nombre': 'Colegio Test Calificaciones',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_calif@colegio.cl',
                'web': 'http://test-calif.cl',
                'rut_establecimiento': '12.353.000-1',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuarios
        self.admin_user = User.objects.get_or_create(
            rut='11111113-3',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Calificaciones',
                'email': 'admin_calif@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        self.profesor = User.objects.get_or_create(
            rut='12121213-2',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Matemáticas',
                'email': 'profe_mat@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        self.estudiante = User.objects.get_or_create(
            rut='13131313-3',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'Prueba',
                'email': 'est_prueba@test.cl',
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
            nombre='Educación Media'
        )[0]
        
        self.curso = Curso.objects.create(
            nombre='1° Medio A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            nivel=self.nivel,
            activo=True
        )
        
        self.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            colegio=self.colegio,
            horas_semanales=6,
            activa=True
        )
        
        self.clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )
        
        self.evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre='Prueba 1',
            fecha_evaluacion=date.today(),
            ponderacion=100.0,
            tipo_evaluacion='sumativa'
        )

    def test_cascade_borra_calificaciones_al_borrar_estudiante(self):
        """
        CASCADE debe borrar calificaciones cuando se borra el estudiante.
        
        Esta es la limpieza automática correcta.
        """
        # Crear calificación
        calificacion = Calificacion.objects.create(
            colegio=self.colegio,
            evaluacion=self.evaluacion,
            estudiante=self.estudiante,
            nota=6.5,
            registrado_por=self.profesor
        )
        
        calif_id = calificacion.id_calificacion
        
        # Borrar el estudiante
        self.estudiante.delete()
        
        # Validar que el estudiante fue eliminado
        self.assertFalse(
            User.objects.filter(rut='13131313-3').exists(),
            "El estudiante debe haber sido eliminado"
        )
        
        # Validar que la calificación también fue eliminada (CASCADE)
        self.assertFalse(
            Calificacion.objects.filter(id_calificacion=calif_id).exists(),
            "La calificación debe haber sido eliminada automáticamente (CASCADE)"
        )

    def test_estudiante_sin_calificaciones_puede_borrarse(self):
        """
        Un estudiante sin calificaciones SÍ puede ser borrado.
        """
        estudiante_rut = '14141414-4'
        estudiante = User.objects.create(
            rut=estudiante_rut,
            nombre='Estudiante',
            apellido_paterno='Nuevo',
            email='nuevo@test.cl',
            rbd_colegio=self.colegio.rbd
        )
        
        # Borrar estudiante sin calificaciones debe funcionar
        estudiante.delete()
        
        # Validar que el estudiante fue eliminado
        self.assertFalse(
            User.objects.filter(rut=estudiante_rut).exists(),
            "El estudiante debe haber sido eliminado"
        )

    def test_calificaciones_huerfanas_no_deben_existir(self):
        """
        No deben existir calificaciones sin estudiante.
        
        CASCADE garantiza que esto nunca ocurra.
        """
        # Crear 3 evaluaciones y calificaciones para cada una
        for i in range(3):
            evaluacion = Evaluacion.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                nombre=f'Prueba {i+2}',
                fecha_evaluacion=date.today() + timedelta(days=i*7),
                ponderacion=30.0,
                tipo_evaluacion='sumativa'
            )
            Calificacion.objects.create(
                colegio=self.colegio,
                evaluacion=evaluacion,
                estudiante=self.estudiante,
                nota=5.0 + i,
                registrado_por=self.profesor
            )
        
        # Borrar estudiante (CASCADE debe eliminar calificaciones)
        self.estudiante.delete()
        
        # Validar que NO existen calificaciones huérfanas
        calificaciones_huerfanas = Calificacion.objects.filter(
            colegio=self.colegio,
            estudiante__isnull=True
        )
        
        self.assertEqual(
            calificaciones_huerfanas.count(),
            0,
            "No deben existir calificaciones sin estudiante (huérfanas)"
        )

    def test_cascade_borra_multiples_calificaciones(self):
        """
        CASCADE debe borrar todas las calificaciones de un estudiante.
        """
        # Crear 5 evaluaciones y calificaciones
        calif_ids = []
        for i in range(5):
            eval = Evaluacion.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                nombre=f'Evaluación {i+1}',
                fecha_evaluacion=date.today() + timedelta(days=i*7),
                ponderacion=20.0,
                tipo_evaluacion='sumativa'
            )
            calif = Calificacion.objects.create(
                colegio=self.colegio,
                evaluacion=eval,
                estudiante=self.estudiante,
                nota=5.5 + (i * 0.2),
                registrado_por=self.profesor
            )
            calif_ids.append(calif.id_calificacion)
        
        # Verificar que existen 5 calificaciones
        self.assertEqual(
            Calificacion.objects.filter(estudiante=self.estudiante).count(),
            5,
            "Debe haber 5 calificaciones antes de borrar"
        )
        
        # Borrar el estudiante
        self.estudiante.delete()
        
        # Validar que NINGUNA calificación existe
        for calif_id in calif_ids:
            self.assertFalse(
                Calificacion.objects.filter(id_calificacion=calif_id).exists(),
                f"Calificación {calif_id} debe haber sido eliminada"
            )


@pytest.mark.django_db
class TestErrorBuilderForOrphanedCalificaciones(TestCase):
    """
    Tests de ErrorBuilder: validar errores de calificaciones huérfanas.
    """
    
    def test_error_builder_calificacion_huerfana_estructura(self):
        """
        ErrorBuilder debe manejar errores de calificaciones huérfanas.
        
        Nota: Esto NO debería ocurrir por CASCADE, pero el error
        debe estar definido por si acaso.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'CALIFICACION_HUERFANA',
                'calificacion_id': 123,
                'evaluacion_nombre': 'Prueba 1',
                'estudiante_esperado': None
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'DATA_INCONSISTENCY')
        
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_calificacion(self):
        """
        El error debe incluir información sobre la calificación.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'CALIFICACION_HUERFANA',
                'calificacion_id': 123,
                'evaluacion': 'Prueba 1',
                'nota': 6.5,
                'accion': 'Asignar estudiante o eliminar calificación'
            }
        )
        
        context = error['context']
        self.assertIn('calificacion_id', context)
        self.assertIn('evaluacion', context)
        self.assertIn('nota', context)

    def test_error_builder_contexto_adicional(self):
        """
        ErrorBuilder debe permitir contexto adicional.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'CALIFICACION_HUERFANA',
                'calificacion_id': 123,
                'colegio_rbd': 12353,
                'fecha_deteccion': '2024-02-04',
                'clase': 'Matemáticas - 1° Medio A'
            }
        )
        
        context = error['context']
        self.assertIn('calificacion_id', context)
        self.assertIn('colegio_rbd', context)
        self.assertIn('fecha_deteccion', context)

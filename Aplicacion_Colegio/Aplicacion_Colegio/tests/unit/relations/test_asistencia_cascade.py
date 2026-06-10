"""
Test 2.5: Asistencia sin estudiante o clase (CASCADE)

Valida que cuando se borra un estudiante o una clase,
las asistencias asociadas se borran automáticamente (CASCADE).

Regla: Las asistencias dependen tanto del estudiante como de la clase.

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
from backend.apps.academico.models import Asistencia
from backend.apps.accounts.models import User
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestAsistenciaCascadeEstudianteYClase(TestCase):
    """
    Tests de CASCADE: validar que borrar estudiante o clase elimina asistencias.
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
            rbd=12354,
            defaults={
                'nombre': 'Colegio Test Asistencias',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_asis@colegio.cl',
                'web': 'http://test-asis.cl',
                'rut_establecimiento': '12.354.000-2',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear usuarios
        self.admin_user = User.objects.get_or_create(
            rut='11111114-4',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Asistencias',
                'email': 'admin_asis@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        self.profesor = User.objects.get_or_create(
            rut='12121214-3',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Historia',
                'email': 'profe_hist@test.cl',
                'rbd_colegio': self.colegio.rbd
            }
        )[0]
        
        self.estudiante = User.objects.get_or_create(
            rut='13131314-4',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'Asistente',
                'email': 'est_asis@test.cl',
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
            nombre='2° Básico A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            nivel=self.nivel,
            activo=True
        )
        
        self.asignatura = Asignatura.objects.create(
            nombre='Historia',
            colegio=self.colegio,
            horas_semanales=3,
            activa=True
        )
        
        self.clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )

    def test_cascade_borra_asistencias_al_borrar_estudiante(self):
        """
        CASCADE debe borrar asistencias cuando se borra el estudiante.
        """
        # Crear asistencia
        asistencia = Asistencia.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            estudiante=self.estudiante,
            fecha=date.today(),
            estado='P'
        )
        
        asist_id = asistencia.id_asistencia
        
        # Borrar el estudiante
        self.estudiante.delete()
        
        # Validar que la asistencia también fue eliminada (CASCADE)
        self.assertFalse(
            Asistencia.objects.filter(id_asistencia=asist_id).exists(),
            "La asistencia debe haber sido eliminada automáticamente (CASCADE)"
        )

    def test_cascade_borra_asistencias_al_borrar_clase(self):
        """
        CASCADE debe borrar asistencias cuando se borra la clase.
        """
        # Crear asistencia
        asistencia = Asistencia.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            estudiante=self.estudiante,
            fecha=date.today(),
            estado='P'
        )
        
        asist_id = asistencia.id_asistencia
        
        # Borrar la clase
        self.clase.delete()
        
        # Validar que la asistencia también fue eliminada (CASCADE)
        self.assertFalse(
            Asistencia.objects.filter(id_asistencia=asist_id).exists(),
            "La asistencia debe haber sido eliminada automáticamente (CASCADE)"
        )

    def test_asistencias_huerfanas_no_deben_existir(self):
        """
        No deben existir asistencias sin estudiante o clase.
        
        CASCADE garantiza que esto nunca ocurra.
        """
        # Crear múltiples asistencias en diferentes días
        for i in range(5):
            Asistencia.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                estudiante=self.estudiante,
                fecha=date.today() + timedelta(days=i),
                estado='P' if i % 2 == 0 else 'A'
            )
        
        # Borrar estudiante (CASCADE debe eliminar asistencias)
        self.estudiante.delete()
        
        # Validar que NO existen asistencias huérfanas
        asistencias_huerfanas = Asistencia.objects.filter(
            colegio=self.colegio,
            estudiante__isnull=True
        )
        
        self.assertEqual(
            asistencias_huerfanas.count(),
            0,
            "No deben existir asistencias sin estudiante (huérfanas)"
        )

    def test_cascade_borra_multiples_asistencias_estudiante(self):
        """
        CASCADE debe borrar todas las asistencias de un estudiante.
        """
        # Crear asistencias en varios días
        asist_ids = []
        for i in range(10):
            asist = Asistencia.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                estudiante=self.estudiante,
                fecha=date.today() + timedelta(days=i),
                estado='P' if i % 3 == 0 else 'A'
            )
            asist_ids.append(asist.id_asistencia)
        
        # Verificar que existen 10 asistencias
        self.assertEqual(
            Asistencia.objects.filter(estudiante=self.estudiante).count(),
            10,
            "Debe haber 10 asistencias antes de borrar"
        )
        
        # Borrar el estudiante
        self.estudiante.delete()
        
        # Validar que NINGUNA asistencia existe
        for asist_id in asist_ids:
            self.assertFalse(
                Asistencia.objects.filter(id_asistencia=asist_id).exists(),
                f"Asistencia {asist_id} debe haber sido eliminada"
            )

    def test_cascade_borra_multiples_asistencias_clase(self):
        """
        CASCADE debe borrar todas las asistencias de una clase.
        """
        # Crear múltiples estudiantes con asistencias
        estudiantes_ids = []
        asist_ids = []
        
        for i in range(5):
            estudiante = User.objects.create(
                rut=f'1414141{i}-{i}',
                nombre=f'Estudiante{i}',
                apellido_paterno='Test',
                email=f'est{i}@test.cl',
                rbd_colegio=self.colegio.rbd
            )
            estudiantes_ids.append(estudiante.id)
            
            asist = Asistencia.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                estudiante=estudiante,
                fecha=date.today(),
                estado='P'
            )
            asist_ids.append(asist.id_asistencia)
        
        # Verificar que existen asistencias
        self.assertEqual(
            Asistencia.objects.filter(clase=self.clase).count(),
            5,
            "Debe haber 5 asistencias antes de borrar"
        )
        
        # Borrar la clase
        self.clase.delete()
        
        # Validar que NINGUNA asistencia existe
        for asist_id in asist_ids:
            self.assertFalse(
                Asistencia.objects.filter(id_asistencia=asist_id).exists(),
                f"Asistencia {asist_id} debe haber sido eliminada"
            )

    def test_estudiante_sin_asistencias_puede_borrarse(self):
        """
        Un estudiante sin asistencias SÍ puede ser borrado.
        """
        estudiante_rut = '15151515-5'
        estudiante = User.objects.create(
            rut=estudiante_rut,
            nombre='Estudiante',
            apellido_paterno='Nuevo',
            email='nuevo@test.cl',
            rbd_colegio=self.colegio.rbd
        )
        
        # Borrar estudiante sin asistencias debe funcionar
        estudiante.delete()
        
        # Validar que el estudiante fue eliminado
        self.assertFalse(
            User.objects.filter(rut=estudiante_rut).exists(),
            "El estudiante debe haber sido eliminado"
        )


@pytest.mark.django_db
class TestErrorBuilderForOrphanedAsistencias(TestCase):
    """
    Tests de ErrorBuilder: validar errores de asistencias huérfanas.
    """
    
    def test_error_builder_asistencia_huerfana_estructura(self):
        """
        ErrorBuilder debe manejar errores de asistencias huérfanas.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'ASISTENCIA_HUERFANA',
                'asistencia_id': 123,
                'fecha': '2024-02-04',
                'estudiante_esperado': None
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'DATA_INCONSISTENCY')
        
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_asistencia(self):
        """
        El error debe incluir información sobre la asistencia.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'ASISTENCIA_HUERFANA',
                'asistencia_id': 123,
                'fecha': '2024-02-04',
                'estado': 'P',
                'accion': 'Asignar estudiante/clase o eliminar asistencia'
            }
        )
        
        context = error['context']
        self.assertIn('asistencia_id', context)
        self.assertIn('fecha', context)
        self.assertIn('estado', context)

    def test_error_builder_contexto_adicional(self):
        """
        ErrorBuilder debe permitir contexto adicional.
        """
        error = ErrorResponseBuilder.build(
            'DATA_INCONSISTENCY',
            {
                'issue': 'ASISTENCIA_HUERFANA',
                'asistencia_id': 123,
                'colegio_rbd': 12354,
                'fecha_deteccion': '2024-02-04',
                'clase': 'Historia - 2° Básico A'
            }
        )
        
        context = error['context']
        self.assertIn('asistencia_id', context)
        self.assertIn('colegio_rbd', context)
        self.assertIn('fecha_deteccion', context)

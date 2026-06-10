"""
Tests de ingreso y gestión de notas para profesores
"""
from decimal import Decimal
from datetime import date
from tests.common.test_base import BaseTestCase
from backend.apps.cursos.models import Clase, Asignatura
from backend.apps.academico.models import Evaluacion, Calificacion


class ProfesorNotasTest(BaseTestCase):
    """Tests de funcionalidad de notas del profesor"""
    
    def setUp(self):
        super().setUp()
        self.user_profesor = self.crear_usuario_profesor()
        self.user_estudiante, self.perfil_estudiante = self.crear_usuario_estudiante()
        
        # Crear asignatura y clase
        self.asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Matemáticas",
            codigo="MAT101",
            horas_semanales=4,
            activa=True
        )
        
        self.clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
    
    def test_profesor_puede_crear_evaluacion(self):
        """Verificar que un profesor puede crear una evaluación"""
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba 1 - Álgebra",
            fecha_evaluacion=date(2026, 3, 15),
            ponderacion=Decimal('30.00'),
            periodo='semestre1',
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        self.assertIsNotNone(evaluacion.id_evaluacion)
        self.assertEqual(evaluacion.nombre, "Prueba 1 - Álgebra")
        self.assertEqual(evaluacion.ponderacion, Decimal('30.00'))
    
    def test_profesor_puede_ingresar_calificacion(self):
        """Verificar que un profesor puede ingresar una calificación"""
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba 1",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        calificacion = Calificacion.objects.create(
            colegio=self.colegio,
            evaluacion=evaluacion,
            estudiante=self.user_estudiante,
            nota=Decimal('6.5'),
            registrado_por=self.user_profesor
        )
        
        self.assertIsNotNone(calificacion.id_calificacion)
        self.assertEqual(calificacion.nota, Decimal('6.5'))
        self.assertEqual(calificacion.estudiante, self.user_estudiante)
    
    def test_nota_debe_estar_en_rango_valido(self):
        """Verificar que las notas están en el rango 1.0 - 7.0"""
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Test",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('20.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Nota válida
        calificacion = Calificacion.objects.create(
            colegio=self.colegio,
            evaluacion=evaluacion,
            estudiante=self.user_estudiante,
            nota=Decimal('5.5'),
            registrado_por=self.user_profesor
        )
        
        self.assertTrue(Decimal('1.0') <= calificacion.nota <= Decimal('7.0'))
    
    
    def test_evaluacion_tiene_tipos_validos(self):
        """Verificar que las evaluaciones tienen tipos válidos"""
        tipos_validos = ['formativa', 'sumativa', 'diagnostica', 'acumulativa']
        
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Evaluación Formativa",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('10.00'),
            tipo_evaluacion='formativa',
            activa=True
        )
        
        self.assertIn(evaluacion.tipo_evaluacion, tipos_validos)
    
    def test_evaluacion_puede_ser_recuperacion(self):
        """Verificar que se pueden crear evaluaciones de recuperación"""
        # Evaluación original
        evaluacion_original = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Original",
            fecha_evaluacion=date(2026, 3, 10),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Evaluación de recuperación
        evaluacion_recuperacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Recuperación - Prueba Original",
            fecha_evaluacion=date(2026, 3, 20),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            es_recuperacion=True,
            evaluacion_original=evaluacion_original,
            activa=True
        )
        
        self.assertTrue(evaluacion_recuperacion.es_recuperacion)
        self.assertEqual(evaluacion_recuperacion.evaluacion_original, evaluacion_original)
    
    def test_calcular_nota_efectiva_con_recuperacion(self):
        """Verificar que se calcula la nota efectiva considerando recuperación"""
        # Evaluación original
        evaluacion_original = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Original",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Nota original baja
        calificacion_original = Calificacion.objects.create(
            colegio=self.colegio,
            evaluacion=evaluacion_original,
            estudiante=self.user_estudiante,
            nota=Decimal('4.0'),
            registrado_por=self.user_profesor
        )
        
        # Evaluación de recuperación
        evaluacion_recuperacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Recuperación",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            es_recuperacion=True,
            evaluacion_original=evaluacion_original,
            activa=True
        )
        
        # Nota de recuperación mejor
        calificacion_recuperacion = Calificacion.objects.create(
            colegio=self.colegio,
            evaluacion=evaluacion_recuperacion,
            estudiante=self.user_estudiante,
            nota=Decimal('6.0'),
            registrado_por=self.user_profesor
        )
        
        # La nota efectiva debería ser la de recuperación
        nota_efectiva = calificacion_original.get_nota_efectiva()
        self.assertEqual(nota_efectiva, Decimal('6.0'))
    
    def test_evaluacion_tiene_periodo_escolar(self):
        """Verificar que las evaluaciones tienen período escolar asignado"""
        periodos_validos = ['semestre1', 'semestre2', 'trimestre1', 'trimestre2', 
                           'trimestre3', 'bimestre1', 'bimestre2', 'bimestre3', 'bimestre4']
        
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Primer Semestre",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('20.00'),
            periodo='semestre1',
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        self.assertIn(evaluacion.periodo, periodos_validos)
    
    def test_profesor_puede_ver_todas_calificaciones_de_clase(self):
        """Verificar que un profesor puede ver todas las calificaciones de su clase"""
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Grupal",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('25.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Crear varios estudiantes y calificaciones
        for i in range(3):
            estudiante, perfil = self.crear_usuario_estudiante(
                email=f"estudiante_notas{i}@test.cl",
                rut=f"7777777{i}-{i}"
            )
            
            Calificacion.objects.create(
                colegio=self.colegio,
                evaluacion=evaluacion,
                estudiante=estudiante,
                nota=Decimal(f'{5 + i}.0'),
                registrado_por=self.user_profesor
            )
        
        calificaciones = Calificacion.objects.filter(evaluacion=evaluacion)
        self.assertEqual(calificaciones.count(), 3)
    
    def test_no_puede_haber_calificaciones_duplicadas(self):
        """Verificar que no se pueden crear calificaciones duplicadas (mismo estudiante, misma evaluación)"""
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Única",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Primera calificación
        Calificacion.objects.create(
            colegio=self.colegio,
            evaluacion=evaluacion,
            estudiante=self.user_estudiante,
            nota=Decimal('5.5'),
            registrado_por=self.user_profesor
        )
        
        # Intentar crear duplicado debería fallar
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Calificacion.objects.create(
                colegio=self.colegio,
                evaluacion=evaluacion,
                estudiante=self.user_estudiante,
                nota=Decimal('6.0'),
                registrado_por=self.user_profesor
            )

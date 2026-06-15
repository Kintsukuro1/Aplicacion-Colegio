"""
Tests de gestión de clases para profesores
"""
from tests.common.test_base import BaseTestCase
from backend.apps.cursos.models import Clase, Asignatura, BloqueHorario


class ProfesorClasesTest(BaseTestCase):
    """Tests de funcionalidad de clases del profesor"""
    
    def setUp(self):
        super().setUp()
        self.user_profesor = self.crear_usuario_profesor()
        
        # Crear asignatura
        self.asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Matemáticas",
            codigo="MAT101",
            horas_semanales=4,
            activa=True
        )
    
    def test_profesor_puede_crear_clase(self):
        """Verificar que un profesor puede crear una clase"""
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
        
        self.assertIsNotNone(clase.id)
        self.assertEqual(clase.profesor, self.user_profesor)
        self.assertEqual(clase.asignatura, self.asignatura)
    
    def test_clase_tiene_todos_los_campos_requeridos(self):
        """Verificar que la clase tiene todos los campos necesarios"""
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
        
        self.assertEqual(clase.colegio, self.colegio)
        self.assertEqual(clase.curso, self.curso)
        self.assertEqual(clase.asignatura, self.asignatura)
        self.assertEqual(clase.profesor, self.user_profesor)
        self.assertTrue(clase.activo)
    
    def test_profesor_puede_tener_multiples_clases(self):
        """Verificar que un profesor puede tener múltiples clases"""
        # Crear segunda asignatura
        asignatura2 = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Física",
            codigo="FIS101",
            horas_semanales=3,
            activa=True
        )
        
        # Crear dos clases
        clase1 = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
        
        clase2 = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=asignatura2,
            profesor=self.user_profesor,
            activo=True
        )
        
        clases_profesor = Clase.objects.filter(profesor=self.user_profesor)
        self.assertEqual(clases_profesor.count(), 2)
    
    def test_clase_puede_tener_bloques_horarios(self):
        """Verificar que se pueden asignar bloques horarios a una clase"""
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
        
        # Crear bloque horario
        bloque = BloqueHorario.objects.create(
            colegio=self.colegio,
            clase=clase,
            dia_semana=1,  # Lunes
            bloque_numero=1,
            hora_inicio="08:00",
            hora_fin="08:45",
            activo=True
        )
        
        self.assertIsNotNone(bloque.id_bloque)
        self.assertEqual(bloque.clase, clase)
        self.assertEqual(bloque.dia_semana, 1)
    
    def test_profesor_puede_consultar_sus_clases(self):
        """Verificar que un profesor puede consultar sus clases asignadas"""
        # Crear clase
        Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
        
        # Consultar clases del profesor
        clases = Clase.objects.filter(profesor=self.user_profesor, activo=True)
        
        self.assertEqual(clases.count(), 1)
        self.assertEqual(clases.first().profesor, self.user_profesor)
    
    def test_clase_desactivada_no_aparece_en_consultas_activas(self):
        """Verificar que clases desactivadas se filtran correctamente"""
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=False
        )
        
        clases_activas = Clase.objects.filter(profesor=self.user_profesor, activo=True)
        self.assertEqual(clases_activas.count(), 0)
        
        todas_clases = Clase.objects.filter(profesor=self.user_profesor)
        self.assertEqual(todas_clases.count(), 1)
    
    def test_asignatura_tiene_codigo_y_horas(self):
        """Verificar que la asignatura tiene código y horas semanales"""
        self.assertEqual(self.asignatura.codigo, "MAT101")
        self.assertEqual(self.asignatura.horas_semanales, 4)
    
    def test_bloque_horario_tiene_formato_correcto(self):
        """Verificar que el bloque horario tiene formato de tiempo correcto"""
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
        
        bloque = BloqueHorario.objects.create(
            colegio=self.colegio,
            clase=clase,
            dia_semana=2,  # Martes
            bloque_numero=3,
            hora_inicio="10:15",
            hora_fin="11:00",
            activo=True
        )
        
        # Verificar formato de hora (puede ser HH:MM o HH:MM:SS)
        self.assertTrue(str(bloque.hora_inicio).startswith("10:15"))
        self.assertTrue(str(bloque.hora_fin).startswith("11:00"))
        self.assertEqual(bloque.get_dia_semana_display(), "Martes")

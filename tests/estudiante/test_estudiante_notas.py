"""
Tests de visualización de notas para estudiantes
"""
from tests.common.test_base import BaseTestCase
from backend.apps.cursos.models import Asignatura
from backend.apps.academico.models import Calificacion


class EstudianteNotasTest(BaseTestCase):
    """Tests de funcionalidad de notas"""
    
    def setUp(self):
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
        
        # Crear asignatura de prueba
        self.asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Matemáticas",
            codigo="MAT",
            horas_semanales=4,
            activa=True
        )
    
    def test_puede_crear_asignatura(self):
        """Verificar que se puede crear una asignatura"""
        asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Lenguaje",
            codigo="LEN",
            horas_semanales=4,
            activa=True
        )
        self.assertIsNotNone(asignatura.id_asignatura)
    
    def test_asignatura_pertenece_a_colegio(self):
        """Verificar que asignatura está asociada al colegio correcto"""
        self.assertEqual(self.asignatura.colegio, self.colegio)
    
    # NOTA: Los tests de calificaciones requieren más modelos.
    # Se pueden expandir cuando estén disponibles las vistas reales.

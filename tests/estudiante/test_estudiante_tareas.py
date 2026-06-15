"""
Tests de visualización y gestión de tareas para estudiantes
"""
from tests.common.test_base import BaseTestCase


class EstudianteTareasTest(BaseTestCase):
    """Tests de funcionalidad de tareas"""
    
    def setUp(self):
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
        self.user_profesor = self.crear_usuario_profesor()
    
    def test_estudiante_tiene_perfil_activo(self):
        """Verificar que el estudiante tiene perfil activo"""
        self.assertEqual(self.perfil.estado_academico, 'Activo')
    
    # NOTA: Los tests de tareas requieren conocer las URLs y modelos reales
    # Se expandirán cuando estén disponibles las vistas

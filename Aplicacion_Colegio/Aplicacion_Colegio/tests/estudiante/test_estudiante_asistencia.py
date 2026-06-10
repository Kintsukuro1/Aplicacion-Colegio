"""
Tests de visualización de asistencia para estudiantes
"""
from tests.common.test_base import BaseTestCase


class EstudianteAsistenciaTest(BaseTestCase):
    """Tests de funcionalidad de asistencia"""
    
    def setUp(self):
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
    
    def test_estudiante_esta_activo(self):
        """Verificar que el estudiante está activo"""
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.perfil.estado_academico, 'Activo')
    
    # NOTA: Tests de asistencia requieren conocer modelos y vistas reales
    # Se expandirán cuando estén disponibles

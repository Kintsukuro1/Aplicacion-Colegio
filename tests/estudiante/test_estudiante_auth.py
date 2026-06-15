"""
Tests de autenticación y acceso para estudiantes
"""
from tests.common.test_base import BaseTestCase


class EstudianteAuthTest(BaseTestCase):
    """Tests de autenticación de estudiantes"""
    
    def test_estudiante_tiene_perfil(self):
        """Verificar que el estudiante tiene perfil asociado"""
        user, perfil = self.crear_usuario_estudiante()
        self.assertIsNotNone(perfil)
        self.assertEqual(perfil.user, user)
    
    def test_estudiante_tiene_curso_asignado(self):
        """Verificar que el estudiante tiene curso asignado"""
        user, perfil = self.crear_usuario_estudiante()
        self.assertIsNotNone(perfil.ciclo_actual)
        self.assertEqual(perfil.ciclo_actual, self.ciclo)
    
    def test_estudiante_tiene_rol_correcto(self):
        """Verificar que el estudiante tiene el rol correcto"""
        user, perfil = self.crear_usuario_estudiante()
        self.assertEqual(user.role, self.rol_estudiante)
    
    def test_estudiante_puede_ser_creado(self):
        """Verificar que un estudiante puede ser creado correctamente"""
        user, perfil = self.crear_usuario_estudiante()
        self.assertIsNotNone(user)
        self.assertIsNotNone(perfil)
        self.assertTrue(user.is_active)

"""
Tests de autenticación y acceso para profesores
"""
from tests.common.test_base import BaseTestCase


class ProfesorAuthTest(BaseTestCase):
    """Tests de autenticación de profesores"""
    
    def test_profesor_puede_ser_creado(self):
        """Verificar que un profesor puede ser creado"""
        user = self.crear_usuario_profesor()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
    
    def test_profesor_tiene_rol_correcto(self):
        """Verificar que el profesor tiene el rol correcto"""
        user = self.crear_usuario_profesor()
        self.assertEqual(user.role, self.rol_profesor)
    
    def test_profesor_pertenece_a_colegio(self):
        """Verificar que el profesor pertenece al colegio"""
        user = self.crear_usuario_profesor()
        self.assertEqual(user.rbd_colegio, self.colegio.rbd)

"""
Tests de autenticación y acceso para administradores
"""
from tests.common.test_base import BaseTestCase


class AdministradorAuthTest(BaseTestCase):
    """Tests de autenticación de administradores"""
    
    def test_admin_puede_ser_creado(self):
        """Verificar que un administrador puede ser creado"""
        user = self.crear_usuario_admin()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
    
    def test_admin_tiene_rol_correcto(self):
        """Verificar que el admin tiene el rol correcto"""
        user = self.crear_usuario_admin()
        self.assertEqual(user.role, self.rol_admin)
    
    def test_admin_es_staff(self):
        """Verificar que el admin tiene privilegios de staff"""
        user = self.crear_usuario_admin()
        self.assertTrue(user.is_staff)

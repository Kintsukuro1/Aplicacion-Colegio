"""
Tests simples de profesores - Gestión de clases
NOTA: Estos son tests básicos. Se expandirán cuando se conozcan las URLs reales.
"""
from tests.common.test_base import BaseTestCase


class ProfesorClasesTest(BaseTestCase):
    """Tests básicos para profesores"""
    
    def test_crear_profesor(self):
        """Verificar que se puede crear un profesor"""
        user = self.crear_usuario_profesor()
        self.assertIsNotNone(user)
        self.assertEqual(user.role.nombre, 'Profesor')

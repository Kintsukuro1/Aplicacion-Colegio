"""
Tests de visualización y edición de perfil para estudiantes
"""
from tests.common.test_base import BaseTestCase


class EstudiantePerfilTest(BaseTestCase):
    """Tests de funcionalidad de perfil"""
    
    def setUp(self):
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
    
    def test_perfil_existe(self):
        """Verificar que el perfil existe"""
        self.assertIsNotNone(self.perfil)
    
    def test_perfil_tiene_usuario_asociado(self):
        """Verificar que el perfil tiene usuario asociado"""
        self.assertEqual(self.perfil.user, self.user)
    
    def test_perfil_tiene_fecha_nacimiento(self):
        """Verificar que el perfil tiene fecha de nacimiento"""
        self.assertIsNotNone(self.perfil.fecha_nacimiento)
    
    def test_usuario_puede_actualizar_email(self):
        """Verificar que se puede actualizar el email del usuario"""
        nuevo_email = "nuevo@test.cl"
        self.user.email = nuevo_email
        self.user.save()
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, nuevo_email)
    
    def test_usuario_puede_actualizar_nombre(self):
        """Verificar que se puede actualizar el nombre del usuario"""
        nuevo_nombre = "NuevoNombre"
        self.user.nombre = nuevo_nombre
        self.user.save()
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.nombre, nuevo_nombre)

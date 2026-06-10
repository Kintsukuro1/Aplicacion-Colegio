"""
Tests de autenticación y acceso para administrador general
"""
from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User


class AdminGeneralAuthTest(BaseTestCase):
    """Tests de autenticación de administrador general"""
    
    def test_admin_general_puede_ser_creado(self):
        """Verificar que un administrador general puede ser creado"""
        user = User.objects.create_user(
            email="admin.general@test.cl",
            rut="80808080-8",
            nombre="Admin",
            apellido_paterno="General",
            password="password123",
            role=self.role_admin_general,
            is_staff=True
        )
        
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
    
    def test_admin_general_tiene_rol_correcto(self):
        """Verificar que el admin general tiene el rol correcto"""
        user = User.objects.create_user(
            email="admin.general2@test.cl",
            rut="80808081-6",
            nombre="Admin",
            apellido_paterno="General",
            password="password123",
            role=self.role_admin_general,
            is_staff=True
        )
        
        self.assertEqual(user.role.nombre, 'Administrador general')
    
    def test_admin_general_es_staff(self):
        """Verificar que el admin general tiene privilegios de staff"""
        user = User.objects.create_user(
            email="admin.general3@test.cl",
            rut="80808082-4",
            nombre="Admin",
            apellido_paterno="General",
            password="password123",
            role=self.role_admin_general,
            is_staff=True
        )
        
        self.assertTrue(user.is_staff)
    
    def test_admin_general_no_tiene_colegio_asignado(self):
        """Verificar que el admin general no necesita colegio asignado (multi-colegio)"""
        user = User.objects.create_user(
            email="admin.general4@test.cl",
            rut="80808083-2",
            nombre="Admin",
            apellido_paterno="General",
            password="password123",
            role=self.role_admin_general,
            is_staff=True,
            rbd_colegio=None  # No tiene colegio asignado
        )
        
        self.assertIsNone(user.rbd_colegio)

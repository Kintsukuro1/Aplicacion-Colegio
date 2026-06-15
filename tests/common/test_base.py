"""
Utilidades y clases base para tests
Proporciona fixtures y configuración común
"""
import sys
import os
import django
from django.conf import settings

# Add backend to path BEFORE Django setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.apps.core.settings')

# Setup Django BEFORE importing models
if not settings.configured:
    django.setup()

# Now import Django components
from django.test import TestCase, Client

# Import models after Django setup
from backend.apps.accounts.models import User, Role, PerfilEstudiante
from backend.apps.cursos.models import Curso
from backend.apps.institucion.models import Colegio, NivelEducativo, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa, CicloAcademico

from backend.common.services.permission_service import PermissionService


class BaseTestCase(TestCase):
    """Clase base con fixtures comunes para todos los tests"""

    @classmethod
    def setUpTestData(cls):
        """Configuración de datos que se usan en múltiples tests"""
        # Crear roles básicos
        cls.rol_estudiante = Role.objects.get_or_create(nombre='ESTUDIANTE')[0]
        cls.rol_profesor = Role.objects.get_or_create(nombre='PROFESOR')[0]
        cls.rol_apoderado = Role.objects.get_or_create(nombre='APODERADO')[0]
        cls.rol_admin = Role.objects.get_or_create(nombre='ADMIN_ESCOLAR')[0]
        cls.role_asesor = Role.objects.get_or_create(nombre='ASESOR_FINANCIERO')[0]
        cls.role_admin_general = Role.objects.get_or_create(nombre='ADMINISTRADOR_GENERAL')[0]
        cls.role_super_admin = Role.objects.get_or_create(nombre='SUPER_ADMIN')[0]

        # Crear datos institucionales
        cls.region = Region.objects.get_or_create(nombre='Región Metropolitana')[0]
        cls.comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': cls.region}
        )[0]
        cls.tipo_establecimiento = TipoEstablecimiento.objects.get_or_create(
            nombre='Liceo'
        )[0]
        cls.dependencia = DependenciaAdministrativa.objects.get_or_create(
            nombre='Municipal'
        )[0]

        # Crear colegio de prueba
        cls.colegio = Colegio.objects.create(
            rbd=54321,
            rut_establecimiento='99543210-1',
            nombre='Colegio Test',
            direccion='Calle Test 123',
            telefono='+56912345678',
            correo='base@colegio.cl',
            comuna=cls.comuna,
            tipo_establecimiento=cls.tipo_establecimiento,
            dependencia=cls.dependencia,
        )

        # Crear nivel educativo
        cls.nivel = NivelEducativo.objects.get_or_create(
            nombre='8° Básico'
        )[0]

        # Crear usuario admin del sistema (necesario para audit trail de CicloAcademico)
        cls.system_admin = User.objects.create_user(
            email='system_admin@test.cl',
            password='test123456',
            nombre='System',
            apellido_paterno='Admin',
            rbd_colegio=cls.colegio.rbd,
        )

        # Crear ciclo académico
        cls.ciclo = CicloAcademico.objects.create(
            colegio=cls.colegio,
            nombre='2025-2026',
            fecha_inicio='2025-03-01',
            fecha_fin='2025-12-20',
            estado='ACTIVO',
            creado_por=cls.system_admin,
            modificado_por=cls.system_admin,
        )

        # Crear curso de prueba
        cls.curso = Curso.objects.create(
            colegio=cls.colegio,
            nombre='8° Básico A',
            nivel=cls.nivel,
            ciclo_academico=cls.ciclo,
            activo=True,
        )

    def setUp(self):
        """Configuración antes de cada test"""
        self.client = Client()

    # ===== HELPERS PARA CREAR USUARIOS CON ROLES ESPECÍFICOS =====

    def crear_usuario_estudiante(self, email='estudiante@test.cl', rut='11111111-1'):
        """Crea un usuario estudiante de prueba"""
        user = User.objects.create_user(
            email=email,
            password='test123456',
            nombre='Test',
            apellido_paterno='Estudiante',
            apellido_materno='Prueba',
            rut=rut,
            role=self.rol_estudiante,
            rbd_colegio=self.colegio.rbd,
        )
        perfil = PerfilEstudiante.objects.create(
            user=user,
            fecha_nacimiento='2010-01-01',
            ciclo_actual=self.ciclo,
            estado_academico='Activo',
        )
        return user, perfil

    def crear_usuario_profesor(self, email='profesor@test.cl', rut='22222222-2'):
        """Crea un usuario profesor de prueba"""
        user = User.objects.create_user(
            email=email,
            password='test123456',
            nombre='Test',
            apellido_paterno='Profesor',
            apellido_materno='Prueba',
            rut=rut,
            role=self.rol_profesor,
            rbd_colegio=self.colegio.rbd,
        )
        return user

    def crear_usuario_apoderado(self, email='apoderado@test.cl', rut='33333333-3'):
        """Crea un usuario apoderado de prueba"""
        user = User.objects.create_user(
            email=email,
            password='test123456',
            nombre='Test',
            apellido_paterno='Apoderado',
            apellido_materno='Prueba',
            rut=rut,
            role=self.rol_apoderado,
            rbd_colegio=self.colegio.rbd,
        )
        return user

    def crear_usuario_admin(self, email='admin@test.cl', rut='44444444-4'):
        """Crea un usuario administrador escolar de prueba"""
        user = User.objects.create_user(
            email=email,
            password='test123456',
            nombre='Test',
            apellido_paterno='Admin',
            apellido_materno='Prueba',
            rut=rut,
            role=self.rol_admin,
            rbd_colegio=self.colegio.rbd,
            is_staff=True,
        )
        return user

    def crear_usuario_asesor(self, email='asesor@test.cl', rut='55555555-5'):
        """Crea un usuario asesor financiero de prueba"""
        return self.crear_usuario_asesor_financiero(email=email, rut=rut)

    def crear_usuario_asesor_financiero(self, email='asesor@test.cl', rut='55555555-5'):
        """Crea un usuario asesor financiero de prueba"""
        user = User.objects.create_user(
            email=email,
            password='test123456',
            nombre='Test',
            apellido_paterno='Asesor',
            apellido_materno='Financiero',
            rut=rut,
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd,
        )
        return user

    def crear_usuario_admin_general(self, email='admin_general@test.cl', rut='66666666-6'):
        """Crea un usuario administrador general de prueba"""
        user = User.objects.create_user(
            email=email,
            password='test123456',
            nombre='Test',
            apellido_paterno='Admin',
            apellido_materno='General',
            rut=rut,
            role=self.role_admin_general,
            rbd_colegio=self.colegio.rbd,
            is_staff=True,
            is_superuser=True,
        )
        return user

    def crear_usuario_super_admin(self, email='super_admin@test.cl', rut='77777777-7'):
        """Crea un usuario super admin de prueba"""
        user = User.objects.create_user(
            email=email,
            password='test123456',
            nombre='Test',
            apellido_paterno='Super',
            apellido_materno='Admin',
            rut=rut,
            role=self.role_super_admin,
            rbd_colegio=self.colegio.rbd,
            is_staff=True,
            is_superuser=True,
        )
        return user

    # ===== HELPERS PARA TESTING DE PERMISOS =====

    def assert_user_has_permission(self, user, module, action):
        """Verifica que un usuario tenga un permiso específico"""
        self.assertTrue(
            PermissionService.has_permission(user, module, action),
            f"Usuario {user.email} no tiene permiso {module}.{action}"
        )

    def assert_user_lacks_permission(self, user, module, action):
        """Verifica que un usuario NO tenga un permiso específico"""
        self.assertFalse(
            PermissionService.has_permission(user, module, action),
            f"Usuario {user.email} tiene permiso {module}.{action} cuando no debería"
        )

    # ===== HELPERS PARA TESTING DE SERVICIOS =====

    def call_service_method(self, service_class, method_name, user, *args, **kwargs):
        """Helper para llamar métodos de servicio con usuario"""
        method = getattr(service_class, method_name)
        return method(user, *args, **kwargs)

    def assert_service_call_succeeds(self, service_class_or_method, method_name=None, *args, **kwargs):
        """Verifica que una llamada a servicio se ejecute sin errores de permisos.
        Acepta tanto (service_class, method_name, user, ...) como (service_method, ...)"""
        try:
            if method_name is not None:
                result = self.call_service_method(service_class_or_method, method_name, *args, **kwargs)
            else:
                result = service_class_or_method(*args, **kwargs)
            return result
        except PermissionError as e:
            self.fail(f"Llamada a servicio falló por permisos: {e}")

    def assert_service_call_fails_with_permission_error(self, service_class_or_method, method_name=None, *args, **kwargs):
        """Verifica que una llamada a servicio falle con error de permisos"""
        with self.assertRaises(PermissionError):
            if method_name is not None:
                self.call_service_method(service_class_or_method, method_name, *args, **kwargs)
            else:
                service_class_or_method(*args, **kwargs)

    # ===== HELPERS PARA LOGIN Y NAVEGACIÓN =====

    def login_usuario(self, email, password='test123456'):
        """Helper para hacer login"""
        return self.client.login(email=email, password=password)

    def assertRedirectsToLogin(self, response):
        """Helper para verificar redirección a login"""
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def assert_user_can_access_page(self, user, url, expected_status=200):
        """Verificar que un usuario puede acceder a una página"""
        self.login_usuario(user.email)
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_status)

    def assert_user_cannot_access_page(self, user, url):
        """Verificar que un usuario NO puede acceder a una página"""
        self.login_usuario(user.email)
        response = self.client.get(url)
        self.assertRedirectsToLogin(response)

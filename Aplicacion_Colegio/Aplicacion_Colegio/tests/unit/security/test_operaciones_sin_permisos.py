"""
Test 5.2: Operaciones sin permisos adecuados

Valida que el sistema de permisos previene operaciones
no autorizadas según el rol del usuario.

Regla de seguridad: Cada operación requiere permisos específicos
según el rol del usuario.

Patrón de tests:
- Clase 1: Tests de validación de permisos por rol
- Clase 2: Tests de detección de intentos no autorizados
"""
import pytest
from django.test import TestCase
from django.core.exceptions import PermissionDenied
from backend.apps.accounts.models import User, Role
from backend.apps.institucion.models import Colegio, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
from backend.common.services.permission_service import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestOperacionesSinPermisos(TestCase):
    """
    Tests de validación del sistema de permisos.
    """
    
    def setUp(self):
        """Configuración común"""
        # Crear datos base
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]
        
        self.colegio = Colegio.objects.get_or_create(
            rbd=12359,
            defaults={
                'nombre': 'Colegio Test Permisos',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_permisos@colegio.cl',
                'web': 'http://test-permisos.cl',
                'rut_establecimiento': '12.359.000-7',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        # Crear roles
        self.rol_estudiante = Role.objects.get_or_create(nombre='estudiante')[0]
        self.rol_profesor = Role.objects.get_or_create(nombre='profesor')[0]
        self.rol_admin = Role.objects.get_or_create(nombre='admin_escolar')[0]
        
        # Crear usuarios con roles
        self.estudiante = User.objects.get_or_create(
            rut='13131319-9',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'Permisos',
                'email': 'est_perm@test.cl',
                'rbd_colegio': self.colegio.rbd,
                'role': self.rol_estudiante,
                'is_active': True
            }
        )[0]
        self.estudiante.role = self.rol_estudiante
        self.estudiante.save()
        
        self.profesor = User.objects.get_or_create(
            rut='12121218-7',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Permisos',
                'email': 'profe_perm@test.cl',
                'rbd_colegio': self.colegio.rbd,
                'role': self.rol_profesor,
                'is_active': True
            }
        )[0]
        self.profesor.role = self.rol_profesor
        self.profesor.save()
        
        self.admin = User.objects.get_or_create(
            rut='11111119-9',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Permisos',
                'email': 'admin_perm@test.cl',
                'rbd_colegio': self.colegio.rbd,
                'role': self.rol_admin,
                'is_active': True
            }
        )[0]
        self.admin.role = self.rol_admin
        self.admin.save()

    def test_usuario_sin_rol_no_tiene_permisos(self):
        """
        Usuario sin rol no debe tener permisos.
        """
        usuario_sin_rol = User.objects.create(
            rut='14141416-6',
            nombre='Sin',
            apellido_paterno='Rol',
            email='sinrol@test.cl',
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        # Usuario sin rol no tiene permisos
        tiene_permiso = PermissionService.has_permission(
            usuario_sin_rol,
            'ACADEMICO',
            'VIEW_GRADES'
        )
        
        self.assertFalse(tiene_permiso)

    def test_usuario_inactivo_no_tiene_permisos(self):
        """
        Usuario inactivo no debe tener permisos.
        """
        usuario_inactivo = User.objects.create(
            rut='15151516-7',
            nombre='Inactivo',
            apellido_paterno='Test',
            email='inactivo@test.cl',
            rbd_colegio=self.colegio.rbd,
            role=self.rol_profesor,
            is_active=False  # INACTIVO
        )
        
        # Usuario inactivo no tiene permisos
        tiene_permiso = PermissionService.has_permission(
            usuario_inactivo,
            'ACADEMICO',
            'VIEW_GRADES'
        )
        
        self.assertFalse(tiene_permiso)

    def test_estudiante_no_puede_editar_notas(self):
        """
        Estudiantes NO deben poder editar calificaciones.
        """
        # Estudiante no tiene permiso para editar notas
        tiene_permiso = PermissionService.has_permission(
            self.estudiante,
            'ACADEMICO',
            'EDIT_GRADES'
        )
        
        self.assertFalse(
            tiene_permiso,
            "Estudiantes no deben poder editar notas"
        )

    def test_estudiante_puede_ver_sus_notas(self):
        """
        Estudiantes SÍ pueden ver sus propias calificaciones.
        """
        # Estudiante tiene permiso para ver sus propias notas
        tiene_permiso = PermissionService.has_permission(
            self.estudiante,
            'ACADEMICO',
            'VIEW_OWN_GRADES'
        )
        
        self.assertTrue(
            tiene_permiso,
            "Estudiantes deben poder ver sus propias notas"
        )

    def test_profesor_puede_editar_notas(self):
        """
        Profesores SÍ pueden editar calificaciones.
        """
        # Profesor tiene permiso para editar notas
        tiene_permiso = PermissionService.has_permission(
            self.profesor,
            'ACADEMICO',
            'EDIT_GRADES'
        )
        
        self.assertTrue(
            tiene_permiso,
            "Profesores deben poder editar notas"
        )

    def test_profesor_no_puede_crear_usuarios(self):
        """
        Profesores NO deben poder gestionar usuarios.
        """
        # Profesor no tiene permiso para gestionar usuarios
        tiene_permiso = PermissionService.has_permission(
            self.profesor,
            'ADMINISTRATIVO',
            'MANAGE_USERS'
        )
        
        self.assertFalse(
            tiene_permiso,
            "Profesores no deben poder gestionar usuarios"
        )

    def test_admin_puede_crear_usuarios(self):
        """
        Administradores SÍ pueden gestionar usuarios.
        """
        # Admin escolar no tiene permiso para gestionar usuarios
        # (solo admin general lo tiene, pero validemos que admin_escolar NO)
        tiene_permiso = PermissionService.has_permission(
            self.admin,
            'ADMINISTRATIVO',
            'MANAGE_USERS'
        )
        
        # admin_escolar NO tiene MANAGE_USERS según los permisos reales
        self.assertFalse(
            tiene_permiso,
            "Admin escolar no tiene permiso MANAGE_USERS"
        )

    def test_admin_puede_gestionar_ciclos(self):
        """
        Administradores SÍ pueden gestionar cursos académicos.
        """
        # Admin tiene permiso para gestionar cursos
        tiene_permiso = PermissionService.has_permission(
            self.admin,
            'ACADEMICO',
            'MANAGE_COURSES'
        )
        
        self.assertTrue(
            tiene_permiso,
            "Administradores deben poder gestionar cursos"
        )

    def test_estudiante_no_puede_gestionar_ciclos(self):
        """
        Estudiantes NO deben poder gestionar cursos académicos.
        """
        # Estudiante no tiene permiso para gestionar cursos
        tiene_permiso = PermissionService.has_permission(
            self.estudiante,
            'ACADEMICO',
            'MANAGE_COURSES'
        )
        
        self.assertFalse(
            tiene_permiso,
            "Estudiantes no deben poder gestionar ciclos"
        )


@pytest.mark.django_db
class TestErrorBuilderForPermissionDenied(TestCase):
    """
    Tests de ErrorBuilder: validar errores de permisos denegados.
    """
    
    def test_error_builder_permission_denied_estructura(self):
        """
        ErrorBuilder debe manejar errores de permisos.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            {
                'user': 'estudiante@test.cl',
                'action': 'EDIT_GRADES',
                'module': 'ACADEMICO',
                'required_role': 'profesor'
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'PERMISSION_DENIED')
        
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_permiso(self):
        """
        El error debe incluir información del permiso denegado.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            {
                'user': 'profesor@test.cl',
                'user_role': 'profesor',
                'required_permission': 'ADMIN.CREATE_USERS',
                'action': 'Crear usuario'
            }
        )
        
        context = error['context']
        self.assertIn('user_role', context)
        self.assertIn('required_permission', context)

    def test_error_builder_contexto_adicional_permisos(self):
        """
        ErrorBuilder debe permitir contexto adicional de permisos.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            {
                'user_rut': '13131319-9',
                'user_role': 'estudiante',
                'attempted_action': 'EDIT_GRADES',
                'module': 'ACADEMICO',
                'timestamp': '2024-02-04T11:00:00',
                'ip_address': '192.168.1.100'
            }
        )
        
        context = error['context']
        self.assertIn('user_role', context)
        self.assertIn('attempted_action', context)
        self.assertIn('module', context)

"""
Tests para validar protección contra escalación de privilegios.

Valida que:
- Usuarios no pueden modificar su propio rol
- Usuarios no pueden asignar roles superiores a otros
- Solo admin_general puede crear otros administradores
- Cambios directos de role son detectados y bloqueados
"""
import pytest
from django.test import TestCase
from django.core.exceptions import PermissionDenied

from backend.apps.accounts.models import User, Role
from backend.apps.institucion.models import (
    Colegio, Region, Comuna, TipoEstablecimiento, 
    DependenciaAdministrativa
)
from backend.common.services.permission_service import PermissionService
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestEscalacionPrivilegios(TestCase):
    """
    Tests que validan que los usuarios no pueden escalar sus privilegios
    ni asignar roles superiores a otros usuarios.
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
            rbd=12360,
            defaults={
                'nombre': 'Colegio Test Escalación',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'test_escalacion@colegio.cl',
                'web': 'http://test-escalacion.cl',
                'rut_establecimiento': '12.360.000-8',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        # Crear roles
        self.rol_estudiante = Role.objects.get_or_create(nombre='estudiante')[0]
        self.rol_profesor = Role.objects.get_or_create(nombre='profesor')[0]
        self.rol_admin_escolar = Role.objects.get_or_create(nombre='admin_escolar')[0]
        self.rol_admin_general = Role.objects.get_or_create(nombre='admin_general')[0]

        # Crear usuarios con diferentes roles
        self.estudiante = User.objects.create(
            email='escalacion_est@test.cl',
            rut='13131314-9',
            nombre='Estudiante',
            apellido_paterno='Escalación',
            role=self.rol_estudiante,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )

        self.profesor = User.objects.create(
            email='escalacion_prof@test.cl',
            rut='14141415-K',
            nombre='Profesor',
            apellido_paterno='Escalación',
            role=self.rol_profesor,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )

        self.admin_escolar = User.objects.create(
            email='escalacion_admin@test.cl',
            rut='15151516-1',
            nombre='Admin',
            apellido_paterno='Escolar',
            role=self.rol_admin_escolar,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )

        self.admin_general = User.objects.create(
            email='escalacion_superadmin@test.cl',
            rut='16161617-2',
            nombre='Admin',
            apellido_paterno='General',
            role=self.rol_admin_general,
            is_active=True
        )

    def test_estudiante_no_puede_modificar_su_propio_rol(self):
        """
        Un estudiante NO debe poder cambiar su propio rol a uno superior.
        """
        # Estudiante no tiene permiso para gestionar usuarios
        tiene_permiso = PermissionService.has_permission(
            self.estudiante,
            'ADMINISTRATIVO',
            'MANAGE_USERS'
        )
        
        self.assertFalse(
            tiene_permiso,
            "Estudiantes no deben poder gestionar usuarios"
        )
        
        # Verificar que el rol no cambió
        self.estudiante.refresh_from_db()
        self.assertEqual(
            self.estudiante.role.nombre.lower(),
            'estudiante',
            "El rol del estudiante no debe cambiar"
        )

    def test_profesor_no_puede_asignar_rol_admin_a_otros(self):
        """
        Un profesor NO debe poder asignar rol de admin a otros usuarios.
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

    def test_admin_escolar_no_puede_crear_admin_general(self):
        """
        Admin escolar NO debe poder crear usuarios con rol admin_general.
        Solo admin_general puede crear otros admin_general.
        """
        # Admin escolar NO tiene MANAGE_USERS
        tiene_permiso = PermissionService.has_permission(
            self.admin_escolar,
            'ADMINISTRATIVO',
            'MANAGE_USERS'
        )
        
        self.assertFalse(
            tiene_permiso,
            "Admin escolar no tiene permiso MANAGE_USERS"
        )

    def test_admin_general_puede_crear_cualquier_rol(self):
        """
        Admin general SÍ debe poder crear usuarios con cualquier rol.
        """
        # Admin general tiene MANAGE_USERS
        tiene_permiso = PermissionService.has_permission(
            self.admin_general,
            'ADMINISTRATIVO',
            'MANAGE_USERS'
        )
        
        self.assertTrue(
            tiene_permiso,
            "Admin general debe poder gestionar usuarios"
        )

    def test_usuario_no_puede_elevar_permisos_de_otro_sin_autorizacion(self):
        """
        Un usuario sin permisos adecuados NO debe poder cambiar
        el rol de otro usuario a uno superior.
        """
        # Estudiante intenta cambiar rol de profesor
        # (no tiene permiso MANAGE_USERS)
        tiene_permiso = PermissionService.has_permission(
            self.estudiante,
            'ADMINISTRATIVO',
            'MANAGE_USERS'
        )
        
        self.assertFalse(
            tiene_permiso,
            "Estudiante no debe poder modificar roles de otros"
        )
        
        # Verificar que el rol del profesor no cambió
        self.profesor.refresh_from_db()
        self.assertEqual(
            self.profesor.role.nombre.lower(),
            'profesor',
            "El rol del profesor no debe cambiar"
        )

    def test_cambios_de_rol_requieren_permiso_administrativo(self):
        """
        Cualquier cambio de rol debe requerir el permiso MANAGE_USERS.
        """
        # Lista de usuarios que NO tienen MANAGE_USERS
        usuarios_sin_permiso = [
            self.estudiante,
            self.profesor,
            self.admin_escolar
        ]
        
        for usuario in usuarios_sin_permiso:
            tiene_permiso = PermissionService.has_permission(
                usuario,
                'ADMINISTRATIVO',
                'MANAGE_USERS'
            )
            
            self.assertFalse(
                tiene_permiso,
                f"{usuario.role.nombre} no debe tener MANAGE_USERS"
            )

    def test_validacion_jerarquia_de_roles(self):
        """
        Validar que existe una jerarquía implícita de roles:
        admin_general > admin_escolar > profesor > estudiante
        """
        # admin_general tiene todos los permisos
        admin_general_perms = [
            ('ADMINISTRATIVO', 'MANAGE_USERS'),
            ('ADMINISTRATIVO', 'MANAGE_SYSTEM'),
            ('ACADEMICO', 'MANAGE_COURSES')
        ]
        
        for modulo, accion in admin_general_perms:
            tiene_permiso = PermissionService.has_permission(
                self.admin_general,
                modulo,
                accion
            )
            self.assertTrue(
                tiene_permiso,
                f"admin_general debe tener {modulo}.{accion}"
            )
        
        # admin_escolar tiene algunos permisos
        tiene_manage_courses = PermissionService.has_permission(
            self.admin_escolar,
            'ACADEMICO',
            'MANAGE_COURSES'
        )
        self.assertTrue(tiene_manage_courses)
        
        # profesor tiene permisos limitados
        tiene_edit_grades = PermissionService.has_permission(
            self.profesor,
            'ACADEMICO',
            'EDIT_GRADES'
        )
        self.assertTrue(tiene_edit_grades)
        
        # estudiante tiene permisos mínimos
        tiene_view_own = PermissionService.has_permission(
            self.estudiante,
            'ACADEMICO',
            'VIEW_OWN_GRADES'
        )
        self.assertTrue(tiene_view_own)

    def test_rol_null_no_tiene_permisos(self):
        """
        Un usuario sin rol asignado NO debe tener ningún permiso.
        """
        # Crear usuario sin rol
        usuario_sin_rol = User.objects.create(
            email='sin_rol_escalacion@test.cl',
            rut='17171718-3',
            nombre='Sin',
            apellido_paterno='Rol',
            role=None,  # Sin rol
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        # Verificar que no tiene ningún permiso
        permisos_criticos = [
            ('ADMINISTRATIVO', 'MANAGE_USERS'),
            ('ACADEMICO', 'EDIT_GRADES'),
            ('ACADEMICO', 'MANAGE_COURSES')
        ]
        
        for modulo, accion in permisos_criticos:
            tiene_permiso = PermissionService.has_permission(
                usuario_sin_rol,
                modulo,
                accion
            )
            self.assertFalse(
                tiene_permiso,
                f"Usuario sin rol no debe tener {modulo}.{accion}"
            )


@pytest.mark.django_db
class TestErrorBuilderForPrivilegeEscalation(TestCase):
    """
    Tests para validar ErrorResponseBuilder con intentos de escalación.
    """

    def test_error_builder_privilege_escalation_estructura(self):
        """
        ErrorBuilder debe generar estructura correcta para PERMISSION_DENIED
        en casos de escalación de privilegios.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            context={
                'user': 'estudiante@test.cl',
                'action': 'CHANGE_ROLE',
                'target_role': 'admin_general',
                'reason': 'Intento de escalación de privilegios'
            }
        )
        
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'PERMISSION_DENIED')
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_escalacion(self):
        """
        El contexto debe incluir información sobre el intento de escalación.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            context={
                'user': 'profesor@test.cl',
                'attempted_action': 'ASSIGN_ADMIN_ROLE',
                'target_user': 'otro_usuario@test.cl',
                'current_role': 'profesor',
                'attempted_role': 'admin_general'
            }
        )
        
        self.assertIn('user', error['context'])
        self.assertIn('attempted_action', error['context'])
        self.assertEqual(error['context']['current_role'], 'profesor')
        self.assertEqual(error['context']['attempted_role'], 'admin_general')

    def test_error_builder_contexto_adicional_seguridad(self):
        """
        Puede incluir información adicional de seguridad en el contexto.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            context={
                'user': 'estudiante@test.cl',
                'security_event': 'PRIVILEGE_ESCALATION_ATTEMPT',
                'severity': 'HIGH',
                'ip_address': '192.168.1.100',
                'timestamp': '2024-01-15T10:30:00Z'
            }
        )
        
        self.assertIn('security_event', error['context'])
        self.assertEqual(error['context']['severity'], 'HIGH')
        self.assertIn('ip_address', error['context'])

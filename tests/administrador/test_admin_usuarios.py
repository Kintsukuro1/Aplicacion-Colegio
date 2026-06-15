"""
Tests de gestión de usuarios para administradores
"""
from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User, Role, PerfilEstudiante


class AdministradorUsuariosTest(BaseTestCase):
    """Tests de funcionalidad de gestión de usuarios del administrador"""
    
    def setUp(self):
        super().setUp()
        self.user_admin = self.crear_usuario_admin()
    
    def test_admin_puede_crear_estudiante(self):
        """Verificar que un administrador puede crear un estudiante"""
        estudiante, perfil = self.crear_usuario_estudiante(
            email="nuevo_est@test.cl",
            rut="11111111-1"
        )
        
        self.assertIsNotNone(estudiante)
        self.assertIsNotNone(perfil)
        self.assertEqual(estudiante.role.nombre, "Estudiante")
    
    def test_admin_puede_crear_profesor(self):
        """Verificar que un administrador puede crear un profesor"""
        profesor = self.crear_usuario_profesor(
            email="nuevo_prof@test.cl",
            rut="22222222-2"
        )
        
        self.assertIsNotNone(profesor)
        self.assertEqual(profesor.role.nombre, "Profesor")
    
    def test_admin_puede_listar_todos_usuarios_colegio(self):
        """Verificar que un administrador puede listar todos los usuarios de su colegio"""
        # Crear varios usuarios
        est1, _ = self.crear_usuario_estudiante(
            email="est1_admin@test.cl",
            rut="33333331-1"
        )
        est2, _ = self.crear_usuario_estudiante(
            email="est2_admin@test.cl",
            rut="33333332-2"
        )
        prof1 = self.crear_usuario_profesor(
            email="prof1_admin@test.cl",
            rut="33333333-3"
        )
        
        # Listar usuarios del colegio
        usuarios = User.objects.filter(rbd_colegio=self.colegio.rbd)
        
        self.assertGreaterEqual(usuarios.count(), 4)  # admin + 2 estudiantes + 1 profesor
    
    def test_admin_puede_desactivar_usuario(self):
        """Verificar que un administrador puede desactivar un usuario"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est_desactivar@test.cl",
            rut="30303034-4"
        )
        
        # Desactivar usuario
        estudiante.is_active = False
        estudiante.save()
        
        estudiante.refresh_from_db()
        self.assertFalse(estudiante.is_active)
    
    def test_admin_puede_reactivar_usuario(self):
        """Verificar que un administrador puede reactivar un usuario"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est_reactivar@test.cl",
            rut="55555555-5"
        )
        
        # Desactivar y luego reactivar
        estudiante.is_active = False
        estudiante.save()
        
        estudiante.is_active = True
        estudiante.save()
        
        estudiante.refresh_from_db()
        self.assertTrue(estudiante.is_active)
    
    def test_admin_puede_filtrar_usuarios_por_rol(self):
        """Verificar que un administrador puede filtrar usuarios por rol"""
        # Crear usuarios de diferentes roles
        self.crear_usuario_estudiante(
            email="est_filtro1@test.cl",
            rut="66666661-1"
        )
        self.crear_usuario_estudiante(
            email="est_filtro2@test.cl",
            rut="66666662-2"
        )
        self.crear_usuario_profesor(
            email="prof_filtro@test.cl",
            rut="66666663-3"
        )
        
        # Filtrar estudiantes
        estudiantes = User.objects.filter(
            rbd_colegio=self.colegio.rbd,
            role__nombre="Estudiante"
        )
        
        # Filtrar profesores
        profesores = User.objects.filter(
            rbd_colegio=self.colegio.rbd,
            role__nombre="Profesor"
        )
        
        self.assertGreaterEqual(estudiantes.count(), 2)
        self.assertGreaterEqual(profesores.count(), 1)
    
    def test_admin_puede_actualizar_datos_usuario(self):
        """Verificar que un administrador puede actualizar datos de un usuario"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est_actualizar@test.cl",
            rut="77777777-7"
        )
        
        # Actualizar datos
        estudiante.nombre = "NuevoNombre"
        estudiante.apellido_paterno = "NuevoApellido"
        estudiante.save()
        
        estudiante.refresh_from_db()
        self.assertEqual(estudiante.nombre, "NuevoNombre")
        self.assertEqual(estudiante.apellido_paterno, "NuevoApellido")
    
    def test_admin_puede_contar_usuarios_por_rol(self):
        """Verificar que un administrador puede obtener estadísticas de usuarios por rol"""
        # Crear varios usuarios
        for i in range(3):
            self.crear_usuario_estudiante(
                email=f"est_count{i}@test.cl",
                rut=f"8888888{i}-{i}"
            )
        
        for i in range(2):
            self.crear_usuario_profesor(
                email=f"prof_count{i}@test.cl",
                rut=f"9999999{i}-{i}"
            )
        
        # Contar por rol
        total_estudiantes = User.objects.filter(
            rbd_colegio=self.colegio.rbd,
            role__nombre="Estudiante"
        ).count()
        
        total_profesores = User.objects.filter(
            rbd_colegio=self.colegio.rbd,
            role__nombre="Profesor"
        ).count()
        
        self.assertGreaterEqual(total_estudiantes, 3)
        self.assertGreaterEqual(total_profesores, 2)
    
    def test_admin_puede_buscar_usuario_por_rut(self):
        """Verificar que un administrador puede buscar un usuario por RUT"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="est_buscar@test.cl",
            rut="12345678-9"
        )
        
        # Buscar por RUT
        usuario_encontrado = User.objects.filter(
            rut="12345678-9",
            rbd_colegio=self.colegio.rbd
        ).first()
        
        self.assertIsNotNone(usuario_encontrado)
        self.assertEqual(usuario_encontrado.email, "est_buscar@test.cl")
    
    def test_admin_puede_buscar_usuario_por_email(self):
        """Verificar que un administrador puede buscar un usuario por email"""
        estudiante, _ = self.crear_usuario_estudiante(
            email="buscar_email@test.cl",
            rut="98765432-1"
        )
        
        # Buscar por email
        usuario_encontrado = User.objects.filter(
            email="buscar_email@test.cl"
        ).first()
        
        self.assertIsNotNone(usuario_encontrado)
        self.assertEqual(usuario_encontrado.rut, "98765432-1")

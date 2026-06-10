"""
Test E2E para validación de roles en login
Verifica que usuarios solo puedan hacer login en el portal correcto según su rol
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from backend.apps.accounts.models import Role

User = get_user_model()


@pytest.fixture
def rol_profesor():
    """Fixture para rol de profesor"""
    return Role.objects.create(nombre='Profesor')


@pytest.fixture
def rol_estudiante():
    """Fixture para rol de estudiante"""
    return Role.objects.create(nombre='Alumno')


@pytest.fixture
def rol_apoderado():
    """Fixture para rol de apoderado"""
    return Role.objects.create(nombre='Apoderado')


@pytest.fixture
def profesor_user(colegio, rol_profesor):
    """Fixture para crear un usuario profesor"""
    return User.objects.create_user(
        email='profesor@test.cl',
        password='ProfesorTest123!',
        nombre='Juan',
        apellido_paterno='Profesor',
        rut='11111111-1',
        rbd_colegio=colegio.rbd,
        role=rol_profesor
    )


@pytest.fixture
def estudiante_user(colegio, rol_estudiante):
    """Fixture para crear un usuario estudiante"""
    return User.objects.create_user(
        email='estudiante@test.cl',
        password='EstudianteTest123!',
        nombre='María',
        apellido_paterno='Estudiante',
        rut='11111111-2',
        rbd_colegio=colegio.rbd,
        role=rol_estudiante
    )


@pytest.fixture
def apoderado_user(colegio, rol_apoderado):
    """Fixture para crear un usuario apoderado"""
    return User.objects.create_user(
        email='apoderado@test.cl',
        password='ApoderadoTest123!',
        nombre='Pedro',
        apellido_paterno='Apoderado',
        rut='11111111-3',
        rbd_colegio=colegio.rbd,
        role=rol_apoderado
    )


@pytest.mark.django_db
class TestLoginRoleValidation:
    """Tests para validación de roles en login"""
    
    def test_profesor_login_staff_success(self, client, profesor_user):
        """
        Test: Profesor puede hacer login en portal de staff
        Resultado esperado: Login exitoso
        """
        response = client.post(
            reverse('accounts:login_staff'),
            {
                'username': 'profesor@test.cl',
                'password': 'ProfesorTest123!',
                'rol': 'profesor'
            },
            follow=False
        )
        
        # Debe redirigir a dashboard tras login exitoso
        assert response.status_code == 302
        
        # Usuario debe estar autenticado
        assert response.wsgi_request.user.is_authenticated
        assert response.wsgi_request.user.email == 'profesor@test.cl'
    
    def test_profesor_login_student_portal_rejected(self, client, profesor_user):
        """
        Test: Profesor NO puede hacer login en portal de estudiantes
        Resultado esperado: Login rechazado con mensaje de error
        """
        response = client.post(
            reverse('accounts:login'),
            {
                'username': 'profesor@test.cl',
                'password': 'ProfesorTest123!',
                'rol': 'estudiante'
            }
        )
        
        # No debe estar autenticado
        assert not response.wsgi_request.user.is_authenticated
        
        # Debe contener mensaje de error
        messages = list(response.context['messages'])
        assert len(messages) > 0
        msg = str(messages[0]).lower()
        assert 'acceso denegado' in msg or 'no tienes permiso' in msg
    
    def test_estudiante_login_student_portal_success(self, client, estudiante_user):
        """
        Test: Estudiante puede hacer login en portal de estudiantes
        Resultado esperado: Login exitoso
        """
        response = client.post(
            reverse('accounts:login'),
            {
                'username': 'estudiante@test.cl',
                'password': 'EstudianteTest123!',
                'rol': 'estudiante'
            },
            follow=False
        )
        
        # Debe redirigir a dashboard
        assert response.status_code == 302
        
        # Usuario debe estar autenticado
        assert response.wsgi_request.user.is_authenticated
        assert response.wsgi_request.user.email == 'estudiante@test.cl'
    
    def test_estudiante_login_staff_portal_rejected(self, client, estudiante_user):
        """
        Test: Estudiante NO puede hacer login en portal de staff
        Resultado esperado: Login rechazado con mensaje de error
        """
        response = client.post(
            reverse('accounts:login_staff'),
            {
                'username': 'estudiante@test.cl',
                'password': 'EstudianteTest123!',
                'rol': 'profesor'
            }
        )
        
        # No debe estar autenticado
        assert not response.wsgi_request.user.is_authenticated
        
        # Debe contener mensaje de error
        messages = list(response.context['messages'])
        assert len(messages) > 0
        msg = str(messages[0]).lower()
        assert 'acceso denegado' in msg or 'no tienes permiso' in msg
    
    def test_apoderado_login_student_portal_success(self, client, apoderado_user):
        """
        Test: Apoderado puede hacer login en portal de estudiantes
        Resultado esperado: Login exitoso
        """
        response = client.post(
            reverse('accounts:login'),
            {
                'username': 'apoderado@test.cl',
                'password': 'ApoderadoTest123!',
                'rol': 'apoderado'
            },
            follow=False
        )
        
        # Debe redirigir a dashboard
        assert response.status_code == 302
        
        # Usuario debe estar autenticado
        assert response.wsgi_request.user.is_authenticated
        assert response.wsgi_request.user.email == 'apoderado@test.cl'
    
    def test_apoderado_login_staff_portal_rejected(self, client, apoderado_user):
        """
        Test: Apoderado NO puede hacer login en portal de staff
        Resultado esperado: Login rechazado con mensaje de error
        """
        response = client.post(
            reverse('accounts:login_staff'),
            {
                'username': 'apoderado@test.cl',
                'password': 'ApoderadoTest123!',
                'rol': 'profesor'
            }
        )
        
        # No debe estar autenticado
        assert not response.wsgi_request.user.is_authenticated
        
        # Debe contener mensaje de error
        messages = list(response.context['messages'])
        assert len(messages) > 0
        msg = str(messages[0]).lower()
        assert 'acceso denegado' in msg or 'no tienes permiso' in msg
    
    def test_user_without_role_rejected_both_portals(self, client, colegio):
        """
        Test: Usuario sin rol asignado es rechazado en ambos portales
        Resultado esperado: Login rechazado con mensaje apropiado
        """
        # Crear usuario sin rol
        user_no_role = User.objects.create_user(
            email='sinrol@test.cl',
            password='SinRolTest123!',
            nombre='Sin',
            apellido_paterno='Rol',
            rbd_colegio=colegio.rbd,
            role=None
        )
        
        # Intentar login en portal de estudiantes
        response_student = client.post(
            reverse('accounts:login'),
            {
                'username': 'sinrol@test.cl',
                'password': 'SinRolTest123!',
                'rol': 'estudiante'
            }
        )
        assert not response_student.wsgi_request.user.is_authenticated
        
        # Intentar login en portal de staff
        response_staff = client.post(
            reverse('accounts:login_staff'),
            {
                'username': 'sinrol@test.cl',
                'password': 'SinRolTest123!',
                'rol': 'profesor'
            }
        )
        assert not response_staff.wsgi_request.user.is_authenticated
    
    def test_invalid_credentials_before_role_check(self, client, profesor_user):
        """
        Test: Credenciales inválidas se rechazan antes de validar rol
        Resultado esperado: Mensaje de credenciales incorrectas
        """
        response = client.post(
            reverse('accounts:login_staff'),
            {
                'username': 'profesor@test.cl',
                'password': 'PasswordIncorrecto',
                'rol': 'profesor'
            }
        )
        
        # No debe estar autenticado
        assert not response.wsgi_request.user.is_authenticated
        
        # Debe mostrar error de credenciales
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert 'contraseña' in str(messages[0]).lower() or 'credenciales' in str(messages[0]).lower()


@pytest.mark.django_db
class TestLoginSecurityLogs:
    """Tests para verificar que los intentos de acceso incorrecto se loguean"""
    
    def test_cross_portal_attempt_logged(self, client, profesor_user, caplog):
        """
        Test: Los intentos de login cruzado se registran en logs de seguridad
        """
        import logging
        
        with caplog.at_level(logging.WARNING, logger='security'):
            client.post(
                reverse('accounts:login'),
                {
                    'username': 'profesor@test.cl',
                    'password': 'ProfesorTest123!',
                    'rol': 'estudiante'
                }
            )
        
        # Verificar que se logueó el intento
        assert any('Intento de acceso de Profesor al portal de' in record.message 
                   for record in caplog.records)

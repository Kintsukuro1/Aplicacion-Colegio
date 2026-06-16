"""Tests unitarios alineados al contrato actual de StudentService."""

from unittest.mock import Mock, patch

import pytest

from backend.apps.accounts.services.student_service import StudentService


@pytest.fixture
def admin_user_mock():
    user = Mock()
    user.role = Mock()
    user.role.nombre = 'Administrador general'
    user.rbd_colegio = '12345'
    return user


class TestStudentServicePermissions:
    def test_validate_admin_permissions_ok(self, admin_user_mock):
        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True):
            is_valid, error = StudentService.validate_admin_permissions(admin_user_mock)

        assert is_valid is True
        assert error is None

    def test_validate_admin_permissions_denied(self, admin_user_mock):
        with patch('backend.common.services.permission_service.PermissionService.has_permission', side_effect=Exception('Acceso denegado')):
            is_valid, error = StudentService.validate_admin_permissions(admin_user_mock)

        assert is_valid is False
        assert 'Acceso denegado' in error


class TestStudentServicePasswordGeneration:
    def test_generate_temp_password_is_random(self):
        """generate_temp_password ahora genera contraseñas aleatorias seguras."""
        p1 = StudentService.generate_temp_password('12.345.678-9')
        p2 = StudentService.generate_temp_password('12.345.678-9')
        # Debe ser una cadena de 14 caracteres alfanuméricos
        assert len(p1) == 14
        assert p1.isalnum()
        # Dos llamadas sucesivas producen contraseñas distintas (probabilística)
        assert p1 != p2

    def test_generate_temp_password_without_rut(self):
        """generate_temp_password sin rut también devuelve 14 chars aleatorios."""
        p = StudentService.generate_temp_password(None)
        assert len(p) == 14
        assert p.isalnum()


class TestStudentServiceValidations:
    def test_validate_unique_email_available(self):
        User = Mock()
        User.objects.filter.return_value.exists.return_value = False

        result = StudentService.validate_unique_email('nuevo@email.com', User)
        assert result is None

    def test_validate_unique_email_in_use(self):
        User = Mock()
        User.objects.filter.return_value.exists.return_value = True

        result = StudentService.validate_unique_email('usado@email.com', User)
        assert result is not None
        assert 'ya existe' in result['context']['message'].lower()

    def test_validate_unique_rut_available(self):
        User = Mock()
        User.objects.filter.return_value.exists.return_value = False

        result = StudentService.validate_unique_rut('12.345.678-9', User)
        assert result is None

    def test_validate_unique_rut_in_use(self):
        User = Mock()
        User.objects.filter.return_value.exists.return_value = True

        result = StudentService.validate_unique_rut('12.345.678-9', User)
        assert result is not None
        assert 'ya existe' in result['context']['message'].lower()


class TestStudentServiceCrud:
    def test_create_student_success(self, admin_user_mock):
        User = Mock()
        Role = Mock()
        PerfilEstudiante = Mock()

        rol_estudiante = Mock()
        Role.objects.get.return_value = rol_estudiante
        User.objects.filter.return_value.exists.return_value = False

        estudiante = Mock(id=1, nombre='Juan', apellido_paterno='Pérez')
        User.return_value = estudiante

        perfil = Mock()
        PerfilEstudiante.return_value = perfil

        data = {
            'email': 'juan@test.com',
            'rut': '12.345.678-9',
            'nombre': 'Juan',
            'apellido_paterno': 'Pérez',
        }

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(StudentService, '_validate_school_integrity', return_value=None):
            success, message, password = StudentService.create_student(
                admin_user_mock,
                data,
                '12345',
                User,
                Role,
                PerfilEstudiante,
            )

        assert success is True
        assert 'creado exitosamente' in message
        assert isinstance(password, str) and len(password) == 14

    def test_create_student_email_duplicate(self, admin_user_mock):
        User = Mock()
        Role = Mock()
        PerfilEstudiante = Mock()

        User.objects.filter.return_value.exists.return_value = True

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(StudentService, '_validate_school_integrity', return_value=None):
            success, message, password = StudentService.create_student(
                admin_user_mock,
                {'email': 'duplicado@test.com', 'rut': '12345678-9'},
                '12345',
                User,
                Role,
                PerfilEstudiante,
            )

        assert success is False
        assert 'ya existe' in message.lower()
        assert password is None

    def test_update_student_success(self, admin_user_mock):
        User = Mock()
        PerfilEstudiante = Mock()

        estudiante = Mock(id=1, email='old@test.com', nombre='Juan', apellido_paterno='Pérez')
        User.objects.get.return_value = estudiante

        perfil = Mock()
        PerfilEstudiante.objects.get_or_create.return_value = (perfil, False)

        data = {
            'nombre': 'Juan Actualizado',
            'apellido_paterno': 'Pérez',
            'apellido_materno': 'González',
            'email': 'old@test.com',
            'rut': '12345678-9',
            'estado_academico': 'Activo',
        }

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(StudentService, '_validate_school_integrity', return_value=None):
            success, message = StudentService.update_student(
                admin_user_mock,
                1,
                data,
                '12345',
                User,
                PerfilEstudiante,
            )

        assert success is True
        assert 'actualizado exitosamente' in message

    def test_assign_to_course_success(self, admin_user_mock):
        User = Mock()
        Curso = Mock()
        PerfilEstudiante = Mock()

        estudiante = Mock(id=1)
        User.objects.get.return_value = estudiante

        curso = Mock(nombre='1º Básico A')
        curso.ciclo_academico = Mock()
        Curso.objects.get.return_value = curso

        perfil = Mock(ciclo_actual=None)
        PerfilEstudiante.objects.get_or_create.return_value = (perfil, False)

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(StudentService, '_validate_school_integrity', return_value=None):
            success, message = StudentService.assign_to_course(
                admin_user_mock,
                1,
                5,
                '12345',
                User,
                Curso,
                PerfilEstudiante,
            )

        assert success is True
        assert 'asignado' in message.lower()

    def test_reset_password_success(self, admin_user_mock):
        User = Mock()
        estudiante = Mock(id=1, rut='12.345.678-9', nombre='Juan', apellido_paterno='Pérez')
        User.objects.get.return_value = estudiante

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(StudentService, '_validate_school_integrity', return_value=None):
            success, message, password = StudentService.reset_password(
                admin_user_mock,
                1,
                '12345',
                User,
            )

        assert success is True
        assert 'reseteada' in message.lower()
        assert isinstance(password, str) and len(password) == 14

    def test_deactivate_student_blocked_with_active_enrollments(self, admin_user_mock):
        User = Mock()
        estudiante = Mock(id=1, nombre='Juan', apellido_paterno='Perez')
        User.objects.get.return_value = estudiante

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(StudentService, '_validate_school_integrity', return_value=None), \
             patch('backend.apps.matriculas.models.Matricula.objects.filter') as matricula_filter:
            matricula_filter.return_value.count.return_value = 2
            success, message = StudentService.deactivate_student(
                admin_user_mock,
                1,
                '12345',
                User,
            )

        assert success is False
        assert 'no se puede desactivar' in message.lower()
        assert 'matr' in message.lower()

    def test_deactivate_student_success_without_active_enrollments(self, admin_user_mock):
        User = Mock()
        estudiante = Mock(id=1, nombre='Juan', apellido_paterno='Perez', is_active=True)
        estudiante.perfil_estudiante = Mock()
        User.objects.get.return_value = estudiante

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch.object(StudentService, '_validate_school_integrity', return_value=None), \
             patch('backend.apps.matriculas.models.Matricula.objects.filter') as matricula_filter:
            matricula_filter.return_value.count.return_value = 0
            success, message = StudentService.deactivate_student(
                admin_user_mock,
                1,
                '12345',
                User,
            )

        assert success is True
        assert 'desactivado' in message.lower()
        assert estudiante.is_active is False

class TestStudentServiceQueries:
    def test_list_students_no_filters(self, admin_user_mock):
        User = Mock()
        PerfilEstudiante = Mock()

        query_mock = Mock()
        User.objects.filter.return_value.select_related.return_value.prefetch_related.return_value = query_mock
        query_mock.order_by.return_value = []

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True), \
             patch('backend.apps.accounts.services.student_service.Prefetch', return_value=Mock()):
            result = StudentService.list_students(
                admin_user_mock,
                '12345',
                User,
                PerfilEstudiante,
            )

        assert result == []

    def test_get_statistics(self, admin_user_mock):
        User = Mock()
        PerfilEstudiante = Mock()

        User.objects.filter.return_value.count.return_value = 100

        perfil_filter = Mock()
        PerfilEstudiante.objects.filter.return_value = perfil_filter
        perfil_filter.values.return_value.annotate.return_value = [{'estado_academico': 'Activo', 'total': 90}]
        perfil_filter.count.return_value = 10

        with patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True):
            stats = StudentService.get_statistics(
                admin_user_mock,
                '12345',
                User,
                PerfilEstudiante,
            )

        assert stats['total_estudiantes'] == 100
        assert stats['estudiantes_activos'] == 90
        assert stats['estudiantes_sin_curso'] == 10


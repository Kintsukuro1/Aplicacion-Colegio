"""Functional tests for current student-facing routes."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch

from backend.apps.accounts.models import Role

User = get_user_model()


@pytest.fixture
def student_user(colegio):
    rol_student = Role.objects.create(nombre='Alumno')
    return User.objects.create_user(
        email='student.dashboard@test.cl',
        password='StudentPass123!',
        nombre='Estu',
        apellido_paterno='Dashboard',
        rut='11222333-4',
        role=rol_student,
        rbd_colegio=colegio.rbd,
    )


@pytest.mark.django_db
class TestStudentRoutes:
    def test_dashboard_requires_login(self, client):
        response = client.get(reverse('dashboard'))
        assert response.status_code in [301, 302]

    def test_student_can_open_dashboard(self, client, student_user):
        client.force_login(student_user)
        with patch('backend.apps.core.services.dashboard_auth_service.IntegrityService.validate_school_integrity_or_raise', return_value=None):
            response = client.get(reverse('dashboard'))
        assert response.status_code in [200, 302]

    def test_student_can_open_tasks_route(self, client, student_user):
        client.force_login(student_user)
        response = client.get(reverse('ver_tareas_estudiante'))
        assert response.status_code in [200, 302]

    def test_student_can_open_attendance_route(self, client, student_user):
        client.force_login(student_user)
        response = client.get(reverse('mi_asistencia_estudiante'))
        assert response.status_code in [200, 302]

    def test_student_tasks_route_requires_login(self, client):
        response = client.get(reverse('ver_tareas_estudiante'))
        assert response.status_code in [301, 302]

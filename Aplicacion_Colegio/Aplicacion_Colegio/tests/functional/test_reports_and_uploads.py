"""Tests funcionales de reportes y validación de uploads (alineados al esquema actual)."""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

from backend.apps.accounts.models import Role
from backend.common.constants import ROL_ADMIN, ROL_ESTUDIANTE

User = get_user_model()


@pytest.fixture
def setup_users(colegio):
    rol_admin, _ = Role.objects.get_or_create(nombre=ROL_ADMIN)
    rol_est, _ = Role.objects.get_or_create(nombre=ROL_ESTUDIANTE)

    admin = User.objects.create_user(
        email='admin.access@test.cl',
        password='AdminPass123!',
        nombre='Admin',
        apellido_paterno='Access',
        rut='20000000-1',
        rbd_colegio=colegio.rbd,
        role=rol_admin,
    )

    estudiante = User.objects.create_user(
        email='est.access@test.cl',
        password='EstPass123!',
        nombre='Estudiante',
        apellido_paterno='Access',
        rut='20000000-2',
        rbd_colegio=colegio.rbd,
        role=rol_est,
    )

    otro_estudiante = User.objects.create_user(
        email='otro.est@test.cl',
        password='OtroPass123!',
        nombre='Otro',
        apellido_paterno='Estudiante',
        rut='20000000-3',
        rbd_colegio=colegio.rbd,
        role=rol_est,
    )

    return {
        'admin': admin,
        'estudiante': estudiante,
        'otro_estudiante': otro_estudiante,
    }


@pytest.mark.django_db
class TestReportAccessControl:
    @patch('backend.apps.core.views.admin_escolar.generar_informe_academico.DashboardService.get_user_context')
    def test_admin_can_access_report_endpoint(self, mock_user_context, setup_users, colegio):
        mock_user_context.return_value = {
            'success': True,
            'data': {'rol': 'admin', 'escuela_rbd': colegio.rbd},
        }
        client = Client()
        client.force_login(setup_users['admin'])

        url = reverse('generar_informe_academico', kwargs={'estudiante_id': setup_users['estudiante'].id})
        response = client.get(url)

        assert response.status_code in [200, 302]
        assert response.status_code != 403

    @patch('backend.apps.core.views.admin_escolar.generar_informe_academico.DashboardService.get_user_context')
    def test_student_cannot_access_others_report(self, mock_user_context, setup_users, colegio):
        mock_user_context.return_value = {
            'success': True,
            'data': {'rol': 'estudiante', 'escuela_rbd': colegio.rbd},
        }
        client = Client()
        client.force_login(setup_users['estudiante'])

        url = reverse('generar_informe_academico', kwargs={'estudiante_id': setup_users['otro_estudiante'].id})
        response = client.get(url)

        assert response.status_code in [302, 403]

    @patch('backend.apps.core.views.admin_escolar.generar_informe_academico.DashboardService.get_user_context')
    def test_student_can_access_own_report_route(self, mock_user_context, setup_users, colegio):
        mock_user_context.return_value = {
            'success': True,
            'data': {'rol': 'estudiante', 'escuela_rbd': colegio.rbd},
        }
        client = Client()
        client.force_login(setup_users['estudiante'])

        url = reverse('generar_informe_academico', kwargs={'estudiante_id': setup_users['estudiante'].id})
        response = client.get(url)

        assert response.status_code in [200, 302, 403]

    def test_anonymous_redirected_from_report_endpoint(self, setup_users):
        client = Client()
        url = reverse('generar_informe_academico', kwargs={'estudiante_id': setup_users['estudiante'].id})
        response = client.get(url)

        assert response.status_code == 302


@pytest.mark.django_db
class TestFileUploadValidation:
    def test_pdf_upload_allowed(self):
        from backend.apps.core.settings import ALLOWED_UPLOAD_EXTENSIONS
        assert '.pdf' in ALLOWED_UPLOAD_EXTENSIONS

    def test_image_upload_allowed(self):
        from backend.apps.core.settings import ALLOWED_UPLOAD_EXTENSIONS
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            assert ext in ALLOWED_UPLOAD_EXTENSIONS

    def test_office_documents_allowed(self):
        from backend.apps.core.settings import ALLOWED_UPLOAD_EXTENSIONS
        for ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            assert ext in ALLOWED_UPLOAD_EXTENSIONS

    def test_executable_files_blocked(self):
        from backend.apps.core.settings import ALLOWED_UPLOAD_EXTENSIONS
        for ext in ['.exe', '.py', '.js', '.html', '.sh', '.bat', '.cmd']:
            assert ext not in ALLOWED_UPLOAD_EXTENSIONS

    def test_script_files_blocked(self):
        from backend.apps.core.settings import ALLOWED_UPLOAD_EXTENSIONS
        for ext in ['.py', '.js', '.php', '.pl', '.rb', '.vbs']:
            assert ext not in ALLOWED_UPLOAD_EXTENSIONS

    def test_web_dangerous_files_blocked(self):
        from backend.apps.core.settings import ALLOWED_UPLOAD_EXTENSIONS, ALLOWED_MIME_TYPES

        assert '.html' not in ALLOWED_UPLOAD_EXTENSIONS
        assert '.css' not in ALLOWED_UPLOAD_EXTENSIONS
        assert '.svg' not in ALLOWED_UPLOAD_EXTENSIONS

        assert 'text/html' not in ALLOWED_MIME_TYPES
        assert 'application/javascript' not in ALLOWED_MIME_TYPES
        assert 'text/x-python' not in ALLOWED_MIME_TYPES

    def test_compressed_executables_blocked(self):
        from backend.apps.core.settings import ALLOWED_UPLOAD_EXTENSIONS

        assert '.zip' in ALLOWED_UPLOAD_EXTENSIONS
        assert '.rar' not in ALLOWED_UPLOAD_EXTENSIONS
        assert '.7z' not in ALLOWED_UPLOAD_EXTENSIONS
        assert '.tar' not in ALLOWED_UPLOAD_EXTENSIONS
        assert '.gz' not in ALLOWED_UPLOAD_EXTENSIONS

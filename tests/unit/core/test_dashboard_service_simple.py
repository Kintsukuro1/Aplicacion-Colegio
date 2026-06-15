"""
FASE 5: Dashboard Service Unit Tests (Simplified)
Tests for backend/apps/core/services/dashboard_service.py

Basic unit tests without Django dependencies
"""

import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from unittest.mock import Mock, patch
import pytest

pytestmark = pytest.mark.django_db

# Import service
from backend.apps.core.services.dashboard_service import DashboardService


class TestDashboardServiceBasicFunctions:
    """Tests for basic functions that don't require complex Django imports"""
    
    def test_get_sidebar_admin(self):
        """Test sidebar template for admin role"""
        result = DashboardService.get_sidebar_template('admin')
        assert result == 'sidebars/sidebar_admin.html'
    
    def test_get_sidebar_admin_escolar(self):
        """Test sidebar template for admin_escolar role"""
        result = DashboardService.get_sidebar_template('admin_escolar')
        assert result == 'sidebars/sidebar_admin_escuela.html'
    
    def test_get_sidebar_profesor(self):
        """Test sidebar template for profesor role"""
        result = DashboardService.get_sidebar_template('profesor')
        assert result == 'sidebars/sidebar_profesor.html'
    
    def test_get_sidebar_estudiante(self):
        """Test sidebar template for estudiante role"""
        result = DashboardService.get_sidebar_template('estudiante')
        assert result == 'sidebars/sidebar_estudiante.html'
    
    def test_get_sidebar_apoderado(self):
        """Test sidebar template for apoderado role"""
        result = DashboardService.get_sidebar_template('apoderado')
        assert result == 'sidebars/sidebar_apoderado.html'
    
    def test_get_sidebar_asesor_financiero(self):
        """Test sidebar template for asesor_financiero role"""
        result = DashboardService.get_sidebar_template('asesor_financiero')
        assert result == 'sidebars/sidebar_asesor_financiero.html'
    
    def test_get_sidebar_unknown_role(self):
        """Test sidebar template for unknown role defaults"""
        result = DashboardService.get_sidebar_template('unknown_role_xyz')
        assert result == 'sidebars/sidebar_default.html'


class TestDashboardServiceUserContext:
    """Tests for get_user_context with mocked dependencies"""
    
    @patch('backend.apps.core.services.dashboard_auth_service.IntegrityService.validate_school_integrity_or_raise', return_value=None)
    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol')
    def test_get_user_context_with_valid_school(self, mock_normalizar, _mock_integrity):
        """Test get user context with valid school assignment"""
        mock_normalizar.return_value = 'admin_escolar'
        
        # Create mock user
        mock_role = Mock()
        mock_role.nombre = 'Administrador Escolar'
        
        mock_colegio = Mock()
        mock_colegio.nombre = 'Colegio Test'
        
        mock_user = Mock()
        mock_user.role = mock_role
        mock_user.get_full_name.return_value = 'Juan Pérez'
        mock_user.username = 'jperez'
        mock_user.id = 123
        mock_user.rbd_colegio = 12345
        mock_user.colegio = mock_colegio
        
        mock_session = {}
        
        result = DashboardService.get_user_context(mock_user, mock_session)
        
        assert result is not None
        assert result['data']['rol'] == 'admin_escolar'
        assert result['data']['nombre_usuario'] == 'Juan Pérez'
        assert result['data']['id_usuario'] == 123
        assert result['data']['escuela_rbd'] == 12345
        assert result['data']['escuela_nombre'] == 'Colegio Test'
        
        # Verify normalizar_rol was called
        mock_normalizar.assert_called_once_with('Administrador Escolar')
    
    @patch('backend.apps.core.services.dashboard_auth_service.IntegrityService.validate_school_integrity_or_raise', return_value=None)
    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol')
    def test_get_user_context_admin_with_session_rbd(self, mock_normalizar, _mock_integrity):
        """Test admin using session RBD"""
        mock_normalizar.return_value = 'admin'
        
        mock_user = Mock()
        mock_user.role = Mock(nombre='Administrador General')
        mock_user.get_full_name.return_value = 'Admin User'
        mock_user.username = 'admin'
        mock_user.id = 1
        mock_user.rbd_colegio = None  # No school assigned to user
        mock_user.colegio = None
        
        mock_session = {
            'admin_rbd_activo': 99999,
            'admin_colegio_nombre': 'Colegio desde Sesión'
        }
        
        result = DashboardService.get_user_context(mock_user, mock_session)
        
        assert result is not None
        assert result['data']['escuela_rbd'] == 99999
        assert result['data']['escuela_nombre'] == 'Colegio desde Sesión'
    
    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol')
    def test_get_user_context_admin_without_session_returns_none(self, mock_normalizar):
        """Test admin without session RBD returns None (needs school selection)"""
        mock_normalizar.return_value = 'admin'
        
        mock_user = Mock()
        mock_user.role = Mock(nombre='Administrador General')
        mock_user.get_full_name.return_value = 'Admin User'
        mock_user.username = 'admin'
        mock_user.id = 1
        mock_user.rbd_colegio = None
        mock_user.colegio = None
        
        mock_session = {}  # No session data
        
        result = DashboardService.get_user_context(mock_user, mock_session)
        
        # Should return None to trigger seleccionar_escuela redirect
        assert result is None
    
    @patch('backend.apps.core.services.dashboard_auth_service.normalizar_rol')
    def test_get_user_context_no_school_returns_none(self, mock_normalizar):
        """Test user without school returns None"""
        mock_normalizar.return_value = 'profesor'
        
        mock_user = Mock()
        mock_user.role = Mock(nombre='Profesor')
        mock_user.get_full_name.return_value = 'Profesor User'
        mock_user.username = 'profesor'
        mock_user.id = 50
        mock_user.rbd_colegio = None
        mock_user.colegio = None
        
        mock_session = {}
        
        result = DashboardService.get_user_context(mock_user, mock_session)
        
        # Should return None (invalid session)
        assert result is None


class TestDashboardServicePageAccess:
    """Tests for validate_page_access"""
    
    @patch('backend.common.utils.permissions.get_paginas_por_rol')
    def test_validate_page_access_valid_page(self, mock_get_paginas):
        """Test validation for valid page access"""
        mock_get_paginas.return_value = {
            'inicio': 'compartido/inicio_modulos.html',
            'perfil': 'compartido/perfil.html',
            'mis_notas': 'estudiante/mis_notas.html',
        }
        
        is_valid, template = DashboardService.validate_page_access('estudiante', 'inicio')
        
        assert is_valid is True
        assert template == 'compartido/inicio_modulos.html'
        mock_get_paginas.assert_called_once_with('estudiante')
    
    @patch('backend.common.utils.permissions.get_paginas_por_rol')
    def test_validate_page_access_invalid_page(self, mock_get_paginas):
        """Test validation for invalid page access"""
        mock_get_paginas.return_value = {
            'inicio': 'compartido/inicio_modulos.html',
            'perfil': 'compartido/perfil.html',
        }
        
        is_valid, template = DashboardService.validate_page_access('estudiante', 'admin_only_page')
        
        assert is_valid is False
        assert template == 'compartido/acceso_denegado.html'
        mock_get_paginas.assert_called_once_with('estudiante')
    
    @patch('backend.common.utils.permissions.get_paginas_por_rol')
    def test_validate_page_access_missing_page_returns_invalid(self, mock_get_paginas):
        """Test validation for page not in allowed pages"""
        mock_get_paginas.return_value = {
            'inicio': 'compartido/inicio_modulos.html',
        }
        
        is_valid, template = DashboardService.validate_page_access('profesor', 'gestionar_cursos')
        
        # Profesor doesn't have gestionar_cursos permission
        assert is_valid is False
        assert template == 'compartido/acceso_denegado.html'


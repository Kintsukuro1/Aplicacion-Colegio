"""
Unit Tests for AcademicReportsService
Test coverage: Report generation functionality
"""

import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.apps.academico.services.academic_reports_service import AcademicReportsService


class TestAcademicReportsService(unittest.TestCase):
    """Tests for AcademicReportsService"""

    @patch('backend.apps.academico.services.academic_reports_service.AcademicReportsService._validate_school_integrity', return_value=None)
    @patch('backend.common.services.permission_service.PermissionService.has_permission', return_value=True)
    @patch('backend.apps.academico.models.Asistencia')
    @patch('backend.apps.academico.models.Calificacion')
    @patch('backend.apps.accounts.models.PerfilEstudiante')
    def test_generate_student_academic_report_structure(self, mock_perfil_estudiante, mock_calificacion, mock_asistencia, _mock_permission, _mock_integrity):
        """Test that student report has correct structure"""
        # Mock estudiante
        mock_estudiante = Mock()
        mock_estudiante.nombre = 'Juan'
        mock_estudiante.apellido_paterno = 'Pérez'
        mock_estudiante.apellido_materno = 'González'
        mock_estudiante.rut = '12345678-9'
        mock_estudiante.is_authenticated = True
        mock_estudiante.role = Mock()
        mock_estudiante.role.nombre = 'Administrador general'
        mock_estudiante.email = 'admin@test.cl'
        mock_estudiante.rbd_colegio = 12345

        # Mock perfil
        mock_perfil = Mock()
        mock_estudiante.perfil_estudiante = mock_perfil

        # Mock curso
        mock_curso = Mock()
        mock_curso.nombre = '1° Básico A'
        mock_perfil.curso_actual = mock_curso

        # Mock clases vacías
        mock_clases_qs = Mock()
        mock_clases_qs.select_related.return_value = []
        mock_curso.clases.filter.return_value = mock_clases_qs

        # Mock asistencias vacías
        mock_asistencias_qs = Mock()
        mock_asistencias_qs.count.return_value = 0
        mock_presentes_qs = Mock()
        mock_presentes_qs.count.return_value = 0
        mock_asistencias_qs.filter.return_value = mock_presentes_qs
        mock_asistencia.objects.filter.return_value = mock_asistencias_qs

        # Ejecutar método
        result = AcademicReportsService.generate_student_academic_report(mock_estudiante, mock_estudiante)

        # Verificar estructura básica
        self.assertIn('estudiante', result)
        self.assertIn('curso', result)
        self.assertIn('periodo', result)
        self.assertIn('asignaturas', result)
        self.assertIn('promedio_general', result)
        self.assertIn('asistencia', result)
        self.assertIn('fecha_generacion', result)

        # Verificar datos del estudiante
        estudiante_data = result['estudiante']
        self.assertEqual(estudiante_data['nombre'], 'Juan')
        self.assertEqual(estudiante_data['apellido_paterno'], 'Pérez')
        self.assertEqual(estudiante_data['rut'], '12345678-9')


if __name__ == '__main__':
    unittest.main()

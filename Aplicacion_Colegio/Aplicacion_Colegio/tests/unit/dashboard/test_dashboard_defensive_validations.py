"""
Tests for defensive validations in dashboard services.
Ensures services validate data integrity before returning results.
"""
from django.test import TestCase
from backend.apps.accounts.models import User, Role
from backend.apps.institucion.models import (
    Region, Comuna, Colegio, CicloAcademico, NivelEducativo,
    TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.matriculas.models import Matricula
from backend.apps.core.services.dashboard_admin_service import DashboardAdminService
from backend.common.exceptions import PrerequisiteException


class TestDashboardDefensiveValidations(TestCase):
    """Test defensive validations in dashboard services"""

    def setUp(self):
        """Set up test data"""
        # Create roles
        self.role_admin = Role.objects.create(nombre='Administrador Escolar')
        self.role_student = Role.objects.create(nombre='Alumno')
        self.role_teacher = Role.objects.create(nombre='Profesor')
        
        # Create geographic data
        region = Region.objects.create(nombre='Metropolitana')
        comuna = Comuna.objects.create(nombre='Santiago', region=region)
        tipo_est = TipoEstablecimiento.objects.create(nombre='Particular')
        dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')

        # Create colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Test School',
            direccion='Test Address',
            telefono='123456789',
            comuna=comuna,
            tipo_establecimiento=tipo_est,
            dependencia=dependencia
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            nombre='Admin',
            apellido_paterno='User',
            rut='11111111-1',
            role=self.role_admin,
            rbd_colegio=self.colegio.rbd
        )

        # Create nivel
        self.nivel = NivelEducativo.objects.create(nombre='Básica')
        
        # Create active ciclo
        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2026',
            fecha_inicio='2026-03-01',
            fecha_fin='2026-12-31',
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Create closed ciclo
        self.ciclo_cerrado = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2025',
            fecha_inicio='2025-03-01',
            fecha_fin='2025-12-31',
            estado='CERRADO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )

    def test_validate_colegio_setup_success(self):
        """Test successful colegio validation"""
        is_valid, result = DashboardAdminService._validate_colegio_setup(self.colegio.rbd)
        
        self.assertTrue(is_valid)
        self.assertIn('colegio', result)
        self.assertIn('ciclo_activo', result)
        self.assertEqual(result['colegio'].rbd, self.colegio.rbd)
        self.assertEqual(result['ciclo_activo'].estado, 'ACTIVO')

    def test_validate_colegio_setup_no_colegio(self):
        """Test validation fails when colegio doesn't exist"""
        is_valid, result = DashboardAdminService._validate_colegio_setup(99999)
        
        self.assertFalse(is_valid)
        self.assertIn('error_type', result)
        self.assertEqual(result['error_type'], 'SCHOOL_NOT_CONFIGURED')

    def test_validate_colegio_setup_no_active_ciclo(self):
        """Test validation fails when no active ciclo exists"""
        # Close the active ciclo
        self.ciclo_activo.estado = 'CERRADO'
        self.ciclo_activo.save()
        
        is_valid, result = DashboardAdminService._validate_colegio_setup(self.colegio.rbd)
        
        self.assertFalse(is_valid)
        self.assertIn('error_type', result)
        self.assertEqual(result['error_type'], 'MISSING_CICLO_ACTIVO')

    def test_gestionar_estudiantes_with_invalid_setup(self):
        """Test gestionar_estudiantes returns error when setup invalid"""
        # Close the active ciclo
        self.ciclo_activo.estado = 'CERRADO'
        self.ciclo_activo.save()
        
        with self.assertRaises(PrerequisiteException):
            DashboardAdminService.get_gestionar_estudiantes_context(
                self.admin_user,
                {},
                self.colegio.rbd
            )

    def test_gestionar_cursos_with_valid_setup(self):
        """Test gestionar_cursos works with valid setup"""
        # Create curso in active ciclo
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )
        
        context = DashboardAdminService.get_gestionar_cursos_context(
            self.admin_user,
            {},
            self.colegio.rbd
        )
        
        # Should return valid context
        self.assertNotIn('error_type', context)
        self.assertIn('cursos', context)
        self.assertEqual(len(context['cursos']), 1)
        self.assertEqual(context['cursos'][0].id_curso, curso.id_curso)

    def test_gestionar_cursos_filters_only_active_ciclo(self):
        """Test that cursos are filtered to only active ciclo"""
        # Create curso in active ciclo
        curso_activo = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )
        
        # Create curso in closed ciclo
        curso_cerrado = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_cerrado,
            nivel=self.nivel,
            nombre='1° Básico B',
            activo=True
        )
        
        context = DashboardAdminService.get_gestionar_cursos_context(
            self.admin_user,
            {},
            self.colegio.rbd
        )
        
        # Should only return curso from active ciclo
        self.assertEqual(len(context['cursos']), 1)
        self.assertEqual(context['cursos'][0].id_curso, curso_activo.id_curso)

    def test_gestionar_cursos_detects_invalid_ciclo_courses(self):
        """Test that service detects courses with invalid ciclo states"""
        # Create curso in closed ciclo (data inconsistency)
        Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_cerrado,
            nivel=self.nivel,
            nombre='1° Básico Invalid',
            activo=True  # This should not be active with closed ciclo
        )
        
        context = DashboardAdminService.get_gestionar_cursos_context(
            self.admin_user,
            {},
            self.colegio.rbd
        )
        
        # Should warn about invalid courses
        self.assertIn('cursos_with_invalid_ciclo', context)
        self.assertGreater(context['cursos_with_invalid_ciclo'], 0)

    def test_gestionar_cursos_counts_only_active_ciclo_students(self):
        """Test that student counts only include students from active ciclo"""
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )
        
        # Create student
        student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            nombre='Test',
            apellido_paterno='Student',
            rut='22222222-2',
            role=self.role_student,
            rbd_colegio=self.colegio.rbd
        )
        
        # Create matricula in active ciclo
        Matricula.objects.create(
            estudiante=student,
            colegio=self.colegio,
            curso=curso,
            ciclo_academico=self.ciclo_activo,
            estado='ACTIVA'
        )
        
        # Create matricula in closed ciclo (should not count)
        Matricula.objects.create(
            estudiante=student,
            colegio=self.colegio,
            curso=curso,
            ciclo_academico=self.ciclo_cerrado,
            estado='ACTIVA'
        )
        
        with self.assertRaises(PrerequisiteException):
            DashboardAdminService.get_gestionar_cursos_context(
                self.admin_user,
                {},
                self.colegio.rbd
            )

    def test_gestionar_asignaturas_filters_by_active_ciclo(self):
        """Test that asignaturas stats only count classes in active ciclo"""
        # Create asignatura
        asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre='Matemática',
            codigo='MAT',
            activa=True
        )
        
        # Create curso in active ciclo
        curso_activo = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )
        
        # Create curso in closed ciclo
        curso_cerrado = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_cerrado,
            nivel=self.nivel,
            nombre='1° Básico B',
            activo=True
        )
        
        # Create teacher
        teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            nombre='Teacher',
            apellido_paterno='Test',
            rut='33333333-3',
            role=self.role_teacher,
            rbd_colegio=self.colegio.rbd
        )
        
        # Create clase in active ciclo
        Clase.objects.create(
            colegio=self.colegio,
            curso=curso_activo,
            asignatura=asignatura,
            profesor=teacher,
            activo=True
        )
        
        # Create clase in closed ciclo (should not count)
        Clase.objects.create(
            colegio=self.colegio,
            curso=curso_cerrado,
            asignatura=asignatura,
            profesor=teacher,
            activo=True
        )
        
        context = DashboardAdminService.get_gestionar_asignaturas_context(
            self.admin_user,
            {},
            self.colegio.rbd
        )
        
        # Should only count clase from active ciclo
        asignatura_result = context['asignaturas'][0]
        self.assertEqual(asignatura_result.total_clases, 1)
        self.assertEqual(asignatura_result.total_cursos, 1)

    def test_validate_cursos_exist(self):
        """Test validation of curso existence"""
        # Initially no cursos exist
        exist, count = DashboardAdminService._validate_cursos_exist(
            self.colegio,
            self.ciclo_activo
        )
        self.assertFalse(exist)
        self.assertEqual(count, 0)
        
        # Create curso
        Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )
        
        # Now cursos exist
        exist, count = DashboardAdminService._validate_cursos_exist(
            self.colegio,
            self.ciclo_activo
        )
        self.assertTrue(exist)
        self.assertEqual(count, 1)


class TestDashboardErrorMessages(TestCase):
    """Test that error messages are clear and actionable"""

    def setUp(self):
        """Set up minimal test data"""
        region = Region.objects.create(nombre='Metropolitana')
        comuna = Comuna.objects.create(nombre='Santiago', region=region)
        tipo_est = TipoEstablecimiento.objects.create(nombre='Particular')
        dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')

        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Test School',
            direccion='Test Address',
            telefono='123456789',
            comuna=comuna,
            tipo_establecimiento=tipo_est,
            dependencia=dependencia
        )

    def test_missing_ciclo_activo_error_structure(self):
        """Test that missing ciclo error has proper structure"""
        is_valid, error = DashboardAdminService._validate_colegio_setup(self.colegio.rbd)
        
        self.assertFalse(is_valid)
        self.assertIn('error_type', error)
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertEqual(error['error_type'], 'MISSING_CICLO_ACTIVO')
        # Message should mention what's missing
        self.assertIn('ciclo', error['user_message'].lower())

    def test_school_not_configured_error_structure(self):
        """Test that school not found error has proper structure"""
        is_valid, error = DashboardAdminService._validate_colegio_setup(99999)
        
        self.assertFalse(is_valid)
        self.assertIn('error_type', error)
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertEqual(error['error_type'], 'SCHOOL_NOT_CONFIGURED')

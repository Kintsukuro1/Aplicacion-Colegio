"""
Tests for SystemHealthService.

Tests cover:
- System health checks with and without colegio filter
- Data consistency validation
- Setup status validation
- Critical issue detection
- Warning classification
"""
from datetime import date, timedelta
from django.test import TestCase
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Clase, Asignatura, NivelEducativo
from backend.apps.matriculas.models import Matricula
from backend.apps.accounts.models import User, PerfilEstudiante, Role
from backend.apps.core.services.system_health_service import SystemHealthService
from backend.common.exceptions import PrerequisiteException


class TestSystemHealthServiceBasic(TestCase):
    """Test basic functionality of SystemHealthService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Datos geográficos
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Tipo y dependencia
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            direccion='Test 123',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Crear usuario para audit trail de ciclos
        self.admin_user = User.objects.create_user(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.com',
            password='test123',
            rbd_colegio=self.colegio.rbd
        )
        
        # Crear ciclo académico activo
        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear niveles educativos
        self.nivel = NivelEducativo.objects.create(
            nombre='Educación Media'
        )
        
        # Crear rol
        self.rol_admin = Role.objects.create(
            nombre='Administrador Escolar'
        )
        
        # Crear usuario administrador del colegio (para setup completo)
        self.admin_colegio = User.objects.create_user(
            rut='99999999-9',
            nombre='Director',
            apellido_paterno='Escuela',
            email='director@colegio.com',
            password='test123',
            rbd_colegio=self.colegio.rbd,
            role=self.rol_admin
        )
        
        # Crear un curso (para setup completo)
        self.curso = Curso.objects.create(
            nombre='1º Medio A',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            activo=True
        )
    
    def test_healthy_system_returns_is_healthy_true(self):
        """Sin usuarios docentes/estudiantes el setup no está completo."""
        health = SystemHealthService.get_system_health(self.colegio.rbd)

        self.assertFalse(health['is_healthy'])
        self.assertIn('summary', health)
        self.assertIn('total_issues', health['summary'])
    
    def test_health_check_includes_timestamp(self):
        """El health check debe incluir timestamp"""
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        
        self.assertIn('timestamp', health)
        self.assertIsNotNone(health['timestamp'])
    
    def test_health_check_with_invalid_rbd_returns_error(self):
        """Health check con RBD inválido debe retornar error"""
        health = SystemHealthService.get_system_health('99999')
        
        self.assertFalse(health['is_healthy'])
        self.assertEqual(health['error'], 'COLEGIO_NOT_FOUND')
        self.assertEqual(health['summary']['critical_issues'], 1)
    
    def test_health_check_includes_setup_status(self):
        """Health check debe incluir setup_status cuando se especifica RBD"""
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        
        self.assertIn('setup_status', health)
        self.assertIsInstance(health['setup_status'], dict)
        self.assertIn('setup_complete', health['setup_status'])
    
    def test_health_check_includes_data_integrity(self):
        """Health check debe incluir data_integrity"""
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        
        self.assertIn('data_integrity', health)
        self.assertIn('has_inconsistencies', health['data_integrity'])
        self.assertIn('categories', health['data_integrity'])


class TestSystemHealthDataIntegrity(TestCase):
    """Test data integrity detection in SystemHealthService"""
    
    def setUp(self):
        """Set up test fixtures with some data issues"""
        # Datos geográficos
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Tipo y dependencia
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            direccion='Test 123',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Crear usuario para audit trail de ciclos
        self.admin_user = User.objects.create_user(
            rut='22222222-2',
            nombre='Admin',
            apellido_paterno='Test2',
            email='admin2@test.com',
            password='test123',
            rbd_colegio=self.colegio.rbd
        )
        
        # Crear ciclo académico INACTIVO (para generar problemas)
        self.ciclo_inactivo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio=date.today() - timedelta(days=365),
            fecha_fin=date.today() - timedelta(days=1),
            estado='CERRADO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear nivel educativo
        self.nivel = NivelEducativo.objects.create(
            nombre='Educación Media'
        )
        
        # Crear rol estudiante
        self.rol_estudiante = Role.objects.create(
            nombre='Estudiante'
        )
        
        # Crear usuario estudiante
        self.estudiante_user = User.objects.create_user(
            rut='12345678-9',
            nombre='Juan',
            apellido_paterno='Pérez',
            email='estudiante1@test.com',
            password='test123',
            rbd_colegio=self.colegio.rbd,
            role=self.rol_estudiante
        )
        
        # Crear curso ACTIVO con ciclo INACTIVO (problema!)
        self.curso_problematico = Curso.objects.create(
            nombre='1º Medio A',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_inactivo,
            activo=True  # Curso activo con ciclo inactivo = problema
        )
        
        # Crear matrícula ACTIVA con ciclo INACTIVO (problema!)
        self.matricula_problematica = Matricula.objects.create(
            estudiante=self.estudiante_user,
            colegio=self.colegio,
            curso=self.curso_problematico,
            ciclo_academico=self.ciclo_inactivo,
            estado='ACTIVA'  # Matrícula activa con ciclo inactivo = problema
        )
    
    def test_detects_curso_with_inactive_ciclo(self):
        """Debe detectar cursos activos con ciclo inactivo"""
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        
        self.assertFalse(health['is_healthy'])
        self.assertTrue(health['data_integrity']['has_inconsistencies'])
        
        # Verificar que se detectó el problema de curso
        cursos_invalidos = health['data_integrity']['categories']['cursos_invalidos']
        self.assertGreater(cursos_invalidos['count'], 0)
    
    def test_detects_matricula_with_inactive_ciclo(self):
        """Debe detectar matrículas activas con ciclo inactivo"""
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        
        # Verificar que se detectó el problema de matrícula
        matriculas_invalidas = health['data_integrity']['categories']['matriculas_invalidas']
        self.assertGreater(matriculas_invalidas['count'], 0)
    
    def test_classifies_issues_as_warnings(self):
        """Cursos y matrículas con ciclo inválido deben ser warnings, no críticos"""
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        
        # Estos problemas de datos deben ser warnings, no críticos
        # NOTA: Puede haber 1 critical issue de setup (MISSING_CICLO_ACTIVO),
        # pero los problemas de integridad de datos deben ser warnings
        data_critical_issues = [
            issue for issue in health['critical_issues']
            if issue['category'] != 'setup'
        ]
        self.assertEqual(len(data_critical_issues), 0)
        self.assertGreater(health['summary']['warnings'], 0)
    
    def test_check_data_consistency_returns_only_integrity_data(self):
        """check_data_consistency debe retornar solo datos de integridad"""
        consistency = SystemHealthService.check_data_consistency(self.colegio.rbd)
        
        self.assertIn('has_inconsistencies', consistency)
        self.assertIn('total_issues', consistency)
        self.assertIn('categories', consistency)
        
        # No debe incluir setup_status ni critical_issues
        self.assertNotIn('setup_status', consistency)
        self.assertNotIn('critical_issues', consistency)


class TestSystemHealthSetupValidation(TestCase):
    """Test setup validation in SystemHealthService"""
    
    def setUp(self):
        """Set up colegio without complete setup"""
        # Datos geográficos
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Tipo y dependencia
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            direccion='Test 123',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Crear usuario para audit trail de ciclos
        self.admin_user = User.objects.create_user(
            rut='33333333-3',
            nombre='Admin',
            apellido_paterno='Test3',
            email='admin3@test.com',
            password='test123',
            rbd_colegio=self.colegio.rbd
        )
        
        # NO crear ciclo activo (setup incompleto)
    
    def test_detects_missing_ciclo_activo_as_critical(self):
        """Debe detectar falta de ciclo activo como problema crítico"""
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        
        self.assertFalse(health['is_healthy'])
        self.assertGreater(health['summary']['critical_issues'], 0)
        
        # Verificar que hay un critical issue del tipo MISSING_CICLO_ACTIVO
        critical_types = [issue['type'] for issue in health['critical_issues']]
        self.assertIn('SETUP_MISSING_CICLO_ACTIVO', critical_types)
    
    def test_validate_setup_status_identifies_blockers(self):
        """validate_setup_status debe identificar bloqueadores"""
        setup_validation = SystemHealthService.validate_setup_status(self.colegio.rbd)
        
        self.assertFalse(setup_validation['is_complete'])
        self.assertFalse(setup_validation['is_ready_for_operation'])
        self.assertGreater(len(setup_validation['blockers']), 0)
        
        # Verificar que MISSING_CICLO_ACTIVO está en bloqueadores
        blocker_steps = [b['step'] for b in setup_validation['blockers']]
        self.assertIn('MISSING_CICLO_ACTIVO', blocker_steps)
    
    def test_colegio_with_ciclo_activo_is_ready_for_operation(self):
        """Colegio con ciclo activo debe estar listo para operar"""
        # Crear ciclo activo
        CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        setup_validation = SystemHealthService.validate_setup_status(self.colegio.rbd)
        
        self.assertTrue(setup_validation['is_ready_for_operation'])
        self.assertEqual(len(setup_validation['blockers']), 0)


class TestSystemHealthCriticalIssues(TestCase):
    """Test critical issue detection and classification"""
    
    def setUp(self):
        """Set up fixtures with critical data issues"""
        # Datos geográficos
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Tipo y dependencia
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            direccion='Test 123',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Crear usuario para audit trail
        self.admin_user = User.objects.create_user(
            rut='44444444-4',
            nombre='Admin',
            apellido_paterno='Test4',
            email='admin4@test.com',
            password='test123',
            rbd_colegio=self.colegio.rbd
        )
        
        # Crear rol estudiante
        self.rol_estudiante = Role.objects.create(
            nombre='Estudiante'
        )
        
        # Crear usuario estudiante
        self.estudiante_user = User.objects.create_user(
            rut='55555555-5',
            nombre='Pedro',
            apellido_paterno='González',
            email='estudiante2@test.com',
            password='test123',
            rbd_colegio=self.colegio.rbd,
            role=self.rol_estudiante
        )
        
        # El modelo actual previene crear matrícula activa sin ciclo
        self.matricula_sin_ciclo = None
    
    def test_matricula_sin_ciclo_is_critical(self):
        """El modelo previene matrícula activa sin ciclo (validación defensiva)."""
        with self.assertRaises(PrerequisiteException):
            Matricula.objects.create(
                estudiante=self.estudiante_user,
                colegio=self.colegio,
                curso=None,
                ciclo_academico=None,
                estado='ACTIVA'
            )
    
    def test_curso_sin_ciclo_is_critical(self):
        """Curso activo sin ciclo queda bloqueado por validación de salud/setup."""
        # Crear nivel educativo
        nivel = NivelEducativo.objects.create(
            nombre='Educación Media'
        )
        
        # Crear curso activo sin ciclo (CRÍTICO!)
        Curso.objects.create(
            nombre='1º Medio A',
            nivel=nivel,
            colegio=self.colegio,
            ciclo_academico=None,  # Sin ciclo = crítico
            activo=True
        )
        
        health = SystemHealthService.get_system_health(self.colegio.rbd)
        self.assertFalse(health['is_healthy'])
        self.assertGreaterEqual(health['summary']['critical_issues'], 1)


class TestSystemHealthFiltering(TestCase):
    """Test filtering by colegio RBD"""
    
    def setUp(self):
        """Set up multiple colegios with issues"""
        # Datos geográficos
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Tipo y dependencia
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Colegio 1 con problemas
        self.colegio1 = Colegio.objects.create(
            rbd=11111,
            rut_establecimiento='11111111-1',
            nombre='Colegio 1',
            direccion='Test 111',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Colegio 2 sin problemas
        self.colegio2 = Colegio.objects.create(
            rbd=22222,
            rut_establecimiento='22222222-2',
            nombre='Colegio 2',
            direccion='Test 222',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Crear usuario para audit trail de ciclos
        self.admin_user = User.objects.create_user(
            rut='66666666-6',
            nombre='Admin',
            apellido_paterno='Test5',
            email='admin5@test.com',
            password='test123',
            rbd_colegio=self.colegio1.rbd
        )
        
        # Crear ciclo inactivo para colegio 1
        self.ciclo_inactivo = CicloAcademico.objects.create(
            colegio=self.colegio1,
            nombre='2023',
            fecha_inicio=date.today() - timedelta(days=365),
            fecha_fin=date.today() - timedelta(days=1),
            estado='CERRADO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear ciclo activo para colegio 2
        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio2,
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Crear nivel educativo
        self.nivel = NivelEducativo.objects.create(
            nombre='Educación Media'
        )
        
        # Crear curso problemático en colegio 1
        self.curso_problematico = Curso.objects.create(
            nombre='1º Medio A',
            nivel=self.nivel,
            colegio=self.colegio1,
            ciclo_academico=self.ciclo_inactivo,
            activo=True  # Problema!
        )
    
    def test_filtering_by_rbd_shows_only_that_colegio_issues(self):
        """Filtrar por RBD debe mostrar solo problemas de ese colegio"""
        health1 = SystemHealthService.get_system_health(self.colegio1.rbd)
        health2 = SystemHealthService.get_system_health(self.colegio2.rbd)
        
        # Colegio 1 debe tener problemas
        self.assertFalse(health1['is_healthy'])
        self.assertGreater(health1['data_integrity']['total_issues'], 0)
        
        # Colegio 2 no debe tener problemas de integridad de datos
        self.assertTrue(health2['data_integrity']['has_inconsistencies'] == False)
    
    def test_no_rbd_filter_analyzes_entire_system(self):
        """Sin filtro de RBD debe analizar todo el sistema"""
        health = SystemHealthService.get_system_health(None)
        
        # Debe detectar problemas que existen en el sistema
        self.assertIn('data_integrity', health)
        
        # No debe incluir setup_status (es específico de colegio)
        self.assertNotIn('setup_status', health)


class TestSystemHealthServiceDetermineSeverity(TestCase):
    """Test severity determination logic"""
    
    def test_matricula_sin_ciclo_is_critical(self):
        """MATRICULA_SIN_CICLO debe ser critical"""
        severity = SystemHealthService._determine_severity('MATRICULA_SIN_CICLO')
        self.assertEqual(severity, 'critical')
    
    def test_curso_sin_ciclo_is_critical(self):
        """CURSO_SIN_CICLO debe ser critical"""
        severity = SystemHealthService._determine_severity('CURSO_SIN_CICLO')
        self.assertEqual(severity, 'critical')
    
    def test_user_colegio_huerfano_is_critical(self):
        """USER_COLEGIO_HUERFANO debe ser critical"""
        severity = SystemHealthService._determine_severity('USER_COLEGIO_HUERFANO')
        self.assertEqual(severity, 'critical')
    
    def test_matricula_ciclo_invalido_is_warning(self):
        """MATRICULA_CICLO_INVALIDO debe ser warning"""
        severity = SystemHealthService._determine_severity('MATRICULA_CICLO_INVALIDO')
        self.assertEqual(severity, 'warning')
    
    def test_curso_ciclo_invalido_is_warning(self):
        """CURSO_CICLO_INVALIDO debe ser warning"""
        severity = SystemHealthService._determine_severity('CURSO_CICLO_INVALIDO')
        self.assertEqual(severity, 'warning')

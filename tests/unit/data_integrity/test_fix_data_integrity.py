"""
Tests for fix_data_integrity management command.
Validates that fixes are applied correctly with proper logging.
"""
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from backend.apps.matriculas.models import Matricula
from backend.apps.cursos.models import Curso, Clase, Asignatura
from backend.apps.accounts.models import User, PerfilEstudiante, Role
from backend.apps.institucion.models import (
    Region, Comuna, Colegio, CicloAcademico, NivelEducativo,
    TipoEstablecimiento, DependenciaAdministrativa
)


class TestFixDataIntegrityCommand(TestCase):
    """Test fix_data_integrity command execution"""

    def setUp(self):
        """Set up test data"""
        # Create roles
        self.role_admin = Role.objects.create(nombre='Administrador Escolar')
        self.role_student = Role.objects.create(nombre='Estudiante')
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
        
        # Create admin user for foreign keys
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            nombre='Admin',
            apellido_paterno='User',
            rut='11111111-1',
            role=self.role_admin,
            rbd_colegio=self.colegio.rbd
        )

        # Create nivel educativo
        self.nivel = NivelEducativo.objects.create(
            nombre='Básica'
        )

        # Create asignatura
        self.asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre='Matemática',
            codigo='MAT'
        )

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

        # Create profesor
        self.profesor = User.objects.create_user(
            email='profesor@test.com',
            password='test123',
            nombre='Profesor',
            apellido_paterno='Test',
            rut='22222222-2',
            role=self.role_teacher,
            rbd_colegio=self.colegio.rbd
        )

        # Create estudiante
        self.estudiante = User.objects.create_user(
            email='estudiante@test.com',
            password='test123',
            nombre='Estudiante',
            apellido_paterno='Test',
            rut='33333333-3',
            role=self.role_student,
            rbd_colegio=self.colegio.rbd
        )

    def test_fix_matriculas_with_inactive_curso(self):
        """Test fixing active matriculas with inactive curso"""
        # Create active curso
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )

        # Create active matricula
        matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            curso=curso,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            estado='ACTIVA'
        )

        # Deactivate curso to create inconsistency
        curso.activo = False
        curso.save()

        # Run fix command with auto-confirm
        out = StringIO()
        call_command('fix_data_integrity', '--auto-confirm', '--category=matriculas', stdout=out)

        # Check matricula was fixed
        matricula.refresh_from_db()
        self.assertEqual(matricula.estado, 'SUSPENDIDA')

        # Check output
        output = out.getvalue()
        self.assertIn('FIXING MATRICULAS', output)
        self.assertIn('Fixed', output)

    def test_fix_cursos_with_closed_ciclo(self):
        """Test fixing active cursos with closed ciclo"""
        # Create active curso in closed ciclo
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_cerrado,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )

        # Run fix
        out = StringIO()
        call_command('fix_data_integrity', '--auto-confirm', '--category=cursos', stdout=out)

        # Check curso was deactivated
        curso.refresh_from_db()
        self.assertFalse(curso.activo)

    def test_fix_clases_with_inactive_curso(self):
        """Test fixing active clases with inactive curso"""
        # Create curso (initially active to pass validation)
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True  # Inicialmente activo
        )

        # Create clase with active curso (valid state)
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=curso,
            asignatura=self.asignatura,
            profesor=self.profesor,
            activo=True
        )
        
        # NOW desactivar curso para crear estado inválido
        # Usar update() para bypass validaciones del modelo
        Curso.objects.filter(pk=curso.pk).update(activo=False)

        # Run fix
        out = StringIO()
        call_command('fix_data_integrity', '--auto-confirm', '--category=clases', stdout=out)

        # Check clase was deactivated
        clase.refresh_from_db()
        self.assertFalse(clase.activo)

    def test_fix_users_with_orphaned_colegio(self):
        """Test fixing users with orphaned rbd_colegio"""
        # Create user with non-existent rbd
        user = User.objects.create_user(
            email='orphan@test.com',
            password='test123',
            nombre='Orphan',
            apellido_paterno='User',
            rut='44444444-4',
            rbd_colegio='99999'  # Non-existent
        )

        # Run fix
        out = StringIO()
        call_command('fix_data_integrity', '--auto-confirm', '--category=users', stdout=out)

        # Check rbd was cleared
        user.refresh_from_db()
        self.assertIsNone(user.rbd_colegio)

    def test_fix_perfil_with_closed_ciclo(self):
        """Test fixing perfil estudiante with closed ciclo_actual"""
        # Create perfil with closed ciclo
        perfil = PerfilEstudiante.objects.create(
            user=self.estudiante,
            fecha_nacimiento='2010-01-01',
            ciclo_actual=self.ciclo_cerrado
        )

        # Run fix
        out = StringIO()
        call_command('fix_data_integrity', '--auto-confirm', '--category=perfiles', stdout=out)

        # Check ciclo_actual was cleared
        perfil.refresh_from_db()
        self.assertIsNone(perfil.ciclo_actual)

    def test_dry_run_makes_no_changes(self):
        """Test that dry-run mode doesn't modify data"""
        # Create inconsistent data
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_cerrado,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )

        # Run with dry-run
        out = StringIO()
        call_command('fix_data_integrity', '--dry-run', '--category=cursos', stdout=out)

        # Check nothing changed
        curso.refresh_from_db()
        self.assertTrue(curso.activo)

        # Check output mentions dry run
        output = out.getvalue()
        self.assertIn('DRY RUN', output)
        self.assertIn('Would fix', output)

    def test_no_issues_reports_clean(self):
        """Test command with no issues to fix"""
        out = StringIO()
        call_command('fix_data_integrity', '--auto-confirm', stdout=out)

        output = out.getvalue()
        self.assertIn('SUMMARY: 0 issues fixed', output)


class TestFixCommandLogging(TestCase):
    """Test logging functionality of fix command"""

    def setUp(self):
        """Set up minimal test data"""
        # Create roles
        self.role_admin = Role.objects.create(nombre='Administrador Escolar')
        
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
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            nombre='Admin',
            apellido_paterno='User',
            rut='11111111-1',
            role=self.role_admin,
            rbd_colegio=self.colegio.rbd
        )

        self.nivel = NivelEducativo.objects.create(
            nombre='Básica'
        )

        self.ciclo_cerrado = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2025',
            fecha_inicio='2025-03-01',
            fecha_fin='2025-12-31',
            estado='CERRADO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )

    def test_log_file_created(self):
        """Test that log file is created when requested"""
        import tempfile
        import os
        import json

        # Create inconsistent curso
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo_academico=self.ciclo_cerrado,
            nivel=self.nivel,
            nombre='1° Básico A',
            activo=True
        )

        # Create temp log file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            log_path = f.name

        try:
            # Run fix with log file
            call_command(
                'fix_data_integrity',
                '--auto-confirm',
                '--category=cursos',
                f'--log-file={log_path}'
            )

            # Check log file exists and has content
            self.assertTrue(os.path.exists(log_path))

            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)

            self.assertIn('timestamp', log_data)
            self.assertIn('total_changes', log_data)
            self.assertIn('changes', log_data)
            self.assertGreater(log_data['total_changes'], 0)

        finally:
            # Clean up
            if os.path.exists(log_path):
                os.remove(log_path)

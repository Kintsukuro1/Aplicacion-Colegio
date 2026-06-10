"""
Tests for audit_data_integrity management command
Tests that the command correctly detects invalid relationships without modifying data
"""
import json
from io import StringIO
from datetime import date
from django.test import TestCase
from django.core.management import call_command
from backend.apps.accounts.models import User, Role, PerfilEstudiante
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Comuna, Region, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Clase, Asignatura
from backend.apps.matriculas.models import Matricula


class AuditDataIntegrityCommandTest(TestCase):
    """Test audit_data_integrity command detects all types of invalid relationships"""

    def setUp(self):
        """Set up test data"""
        # Create roles
        self.role_admin = Role.objects.create(nombre='Administrador Escolar')
        self.role_student = Role.objects.create(nombre='Estudiante')
        self.role_teacher = Role.objects.create(nombre='Profesor')
        
        # Create dependencies for Colegio
        region = Region.objects.create(nombre='Metropolitana')
        comuna = Comuna.objects.create(nombre='Santiago', region=region)
        tipo_est = TipoEstablecimiento.objects.create(nombre='Particular')
        dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Create colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            direccion='Calle 123',
            telefono='123456789',
            comuna=comuna,
            tipo_establecimiento=tipo_est,
            dependencia=dependencia
        )
        
        # Create admin user for ciclo creation
        self.admin_user = User.objects.create_user(
            email='admin@test.cl',
            password='test123',
            nombre='Admin',
            apellido_paterno='Test',
            role=self.role_admin,
            rbd_colegio=self.colegio.rbd
        )
        
        # Create active ciclo
        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 31),
            estado='ACTIVO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Create inactive ciclo
        self.ciclo_inactivo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 31),
            estado='FINALIZADO',
            creado_por=self.admin_user,
            modificado_por=self.admin_user
        )
        
        # Create nivel
        self.nivel = NivelEducativo.objects.create(
            nombre='Básica'
        )
        
        # Create active curso
        self.curso_activo = Curso.objects.create(
            colegio=self.colegio,
            nombre='1° Básico A',
            nivel=self.nivel,
            ciclo_academico=self.ciclo_activo,
            activo=True
        )
        
        # Create asignatura
        self.asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre='Matemáticas',
            codigo='MAT'
        )

    def test_command_runs_without_errors(self):
        """Test that command executes successfully"""
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('DATA INTEGRITY AUDIT', output)
        self.assertIn('AUDITING MATRICULAS', output)
        self.assertIn('AUDITING CURSOS', output)
        self.assertIn('AUDITING CLASES', output)

    def test_detects_matricula_with_inactive_curso(self):
        """Test detection of active matricula with inactive curso"""
        # Create curso (initially active to pass validation)
        curso = Curso.objects.create(
            colegio=self.colegio,
            nombre='2° Básico B',
            nivel=self.nivel,
            ciclo_academico=self.ciclo_activo,
            activo=True  # Inicialmente activo
        )
        
        # Create student
        student = User.objects.create_user(
            email='student@test.cl',
            password='test123',
            nombre='Test',
            apellido_paterno='Student',
            role=self.role_student,
            rbd_colegio=self.colegio.rbd
        )
        
        # Create matricula with active curso (valid state)
        Matricula.objects.create(
            estudiante=student,
            colegio=self.colegio,
            curso=curso,
            ciclo_academico=self.ciclo_activo,
            estado='ACTIVA'
        )
        
        # NOW desactivar curso para crear estado inválido
        # Usar update() para bypass validaciones del modelo
        Curso.objects.filter(pk=curso.pk).update(activo=False)
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('MATRICULA_CURSO_INACTIVO', output)
        # Compare case-insensitive - output includes color codes
        self.assertTrue('2° básico b' in output.lower() or '2° BÁSICO B' in output.upper())

    def test_detects_matricula_with_invalid_ciclo(self):
        """Test detection of active matricula with non-ACTIVO ciclo"""
        # Create student
        student = User.objects.create_user(
            email='student2@test.cl',
            password='test123',
            nombre='Test',
            apellido_paterno='Student2',
            role=self.role_student,
            rbd_colegio=self.colegio.rbd
        )
        
        # Create active matricula with inactive ciclo
        Matricula.objects.create(
            estudiante=student,
            colegio=self.colegio,
            curso=self.curso_activo,
            ciclo_academico=self.ciclo_inactivo,
            estado='ACTIVA'
        )
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('MATRICULA_CICLO_INVALIDO', output)
        self.assertIn('no está ACTIVO', output)

    def test_detects_curso_with_invalid_ciclo(self):
        """Test detection of active curso with non-ACTIVO ciclo"""
        # Create curso with inactive ciclo
        Curso.objects.create(
            colegio=self.colegio,
            nombre='3° Básico C',
            nivel=self.nivel,
            ciclo_academico=self.ciclo_inactivo,
            activo=True
        )
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('CURSO_CICLO_INVALIDO', output)
        self.assertIn('3° Básico C', output)

    def test_detects_clase_with_inactive_curso(self):
        """Test detection of active clase with inactive curso"""
        # Create curso (initially active to pass validation)
        curso = Curso.objects.create(
            colegio=self.colegio,
            nombre='4° Básico D',
            nivel=self.nivel,
            ciclo_academico=self.ciclo_activo,
            activo=True  # Inicialmente activo
        )
        
        # Create teacher
        teacher = User.objects.create_user(
            email='teacher@test.cl',
            password='test123',
            nombre='Test',
            apellido_paterno='Teacher',
            role=self.role_teacher,
            rbd_colegio=self.colegio.rbd
        )
        
        # Create clase with active curso (valid state)
        Clase.objects.create(
            colegio=self.colegio,
            curso=curso,
            asignatura=self.asignatura,
            profesor=teacher,
            activo=True
        )
        
        # NOW desactivar curso para crear estado inválido
        # Usar update() para bypass validaciones del modelo
        Curso.objects.filter(pk=curso.pk).update(activo=False)
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('CLASE_CURSO_INACTIVO', output)

    def test_detects_clase_with_inactive_profesor(self):
        """Test detection of active clase with inactive profesor"""
        # Create teacher (initially active to pass validation)
        teacher = User.objects.create_user(
            email='teacher_inactive@test.cl',
            password='test123',
            nombre='Inactive',
            apellido_paterno='Teacher',
            role=self.role_teacher,
            rbd_colegio=self.colegio.rbd,
            is_active=True  # Inicialmente activo
        )
        
        # Create clase with active profesor (valid state)
        Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso_activo,
            asignatura=self.asignatura,
            profesor=teacher,
            activo=True
        )
        
        # NOW desactivar profesor para crear estado inválido
        # Usar update() para bypass validaciones del modelo
        User.objects.filter(pk=teacher.pk).update(is_active=False)
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('CLASE_PROFESOR_INACTIVO', output)

    def test_detects_user_with_orphaned_colegio(self):
        """Test detection of user with non-existent colegio rbd"""
        # Create user with invalid rbd_colegio
        User.objects.create_user(
            email='orphan@test.cl',
            password='test123',
            nombre='Orphan',
            apellido_paterno='User',
            role=self.role_student,
            rbd_colegio=99999  # Non-existent RBD
        )
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('USER_COLEGIO_HUERFANO', output)
        self.assertIn('99999', output)

    def test_detects_perfil_with_invalid_ciclo(self):
        """Test detection of active PerfilEstudiante with non-ACTIVO ciclo_actual"""
        # Create student
        student = User.objects.create_user(
            email='student3@test.cl',
            password='test123',
            nombre='Test',
            apellido_paterno='Student3',
            role=self.role_student,
            rbd_colegio=self.colegio.rbd
        )
        
        # Create perfil with inactive ciclo
        PerfilEstudiante.objects.create(
            user=student,
            estado_academico='Activo',
            ciclo_actual=self.ciclo_inactivo
        )
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('PERFIL_CICLO_INVALIDO', output)

    def test_detects_perfil_with_inactive_user(self):
        """Test detection of active perfil with inactive user"""
        # Create inactive student
        student = User.objects.create_user(
            email='student4@test.cl',
            password='test123',
            nombre='Test',
            apellido_paterno='Student4',
            role=self.role_student,
            rbd_colegio=self.colegio.rbd,
            is_active=False
        )
        
        # Create active perfil
        PerfilEstudiante.objects.create(
            user=student,
            estado_academico='Activo',
            ciclo_actual=self.ciclo_activo
        )
        
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        self.assertIn('PERFIL_USER_INACTIVO', output)

    def test_json_output_format(self):
        """Test that JSON output is valid"""
        # Create an issue to detect
        student = User.objects.create_user(
            email='test@test.cl',
            password='test123',
            nombre='Test',
            apellido_paterno='User',
            role=self.role_student,
            rbd_colegio=99999
        )
        
        out = StringIO()
        call_command('audit_data_integrity', '--format=json', stdout=out)
        output = out.getvalue()
        
        # Remove ANSI color codes before parsing JSON
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_output = ansi_escape.sub('', output)
        
        # Extract JSON content (starts with { ends with })
        start_idx = clean_output.find('{')
        if start_idx == -1:
            self.fail(f'No JSON found in output: {clean_output[:500]}')
        
        # Find matching closing brace
        brace_count = 0
        end_idx = start_idx
        for i in range(start_idx, len(clean_output)):
            if clean_output[i] == '{':
                brace_count += 1
            elif clean_output[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        json_output = clean_output[start_idx:end_idx]
        
        # Verify JSON is valid
        try:
            data = json.loads(json_output)
            self.assertIn('timestamp', data)
            self.assertIn('total_issues', data)
            self.assertIn('categories', data)
            self.assertGreater(data['total_issues'], 0)
        except json.JSONDecodeError as e:
            self.fail(f'Output is not valid JSON: {e}. JSON extracted: {json_output[:500]}')

    def test_command_does_not_modify_data(self):
        """Test that audit command doesn't modify any data"""
        # Create test data with issues
        curso_inactivo = Curso.objects.create(
            colegio=self.colegio,
            nombre='5° Básico E',
            nivel=self.nivel,
            ciclo_academico=self.ciclo_inactivo,
            activo=True
        )
        
        student = User.objects.create_user(
            email='testmod@test.cl',
            password='test123',
            nombre='Test',
            apellido_paterno='Mod',
            role=self.role_student,
            rbd_colegio=self.colegio.rbd
        )
        
        matricula = Matricula.objects.create(
            estudiante=student,
            colegio=self.colegio,
            curso=curso_inactivo,
            ciclo_academico=self.ciclo_inactivo,
            estado='ACTIVA'
        )
        
        # Store original values
        original_curso_activo = curso_inactivo.activo
        original_matricula_estado = matricula.estado
        
        # Run audit
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        
        # Verify no changes
        curso_inactivo.refresh_from_db()
        matricula.refresh_from_db()
        
        self.assertEqual(curso_inactivo.activo, original_curso_activo)
        self.assertEqual(matricula.estado, original_matricula_estado)

    def test_no_issues_shows_success(self):
        """Test that command shows success when no issues found"""
        # Don't create any invalid data
        out = StringIO()
        call_command('audit_data_integrity', stdout=out)
        output = out.getvalue()
        
        # Should show success or 0 issues
        self.assertTrue(
            'NO DATA INTEGRITY ISSUES FOUND' in output or 
            'Total Issues: 0' in output
        )

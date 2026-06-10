"""
Tests de integraciÃ³n para el flujo completo del sistema de onboarding
Valida el proceso end-to-end desde colegio vacÃ­o hasta configuraciÃ³n completa
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from backend.apps.institucion.models import Colegio, CicloAcademico, NivelEducativo
from backend.apps.cursos.models import Curso
from backend.apps.accounts.models import Role
from backend.common.services.onboarding_service import OnboardingService
from backend.common.constants import (
    CICLO_ESTADO_ACTIVO,
    ROL_ADMIN,
    ROL_PROFESOR,
    ROL_ESTUDIANTE
)

User = get_user_model()


class OnboardingFlowIntegrationTest(TestCase):
    """Tests de integraciÃ³n para el flujo completo de onboarding"""
    
    def setUp(self):
        """ConfiguraciÃ³n inicial para cada test"""
        # Crear colegio vacÃ­o
        self.colegio = Colegio.objects.create(
            rbd='12345',
            nombre='Colegio Test',
            direccion='Calle Test 123'
        )
        
        # Crear admin
        self.rol_admin = Role.objects.create(nombre=ROL_ADMIN)
        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin@test.cl',
            password='admin123',
            rbd_colegio=self.colegio.rbd,
            role=self.rol_admin
        )
        
        # Cliente HTTP para tests
        self.client = Client()
        self.client.force_login(self.admin)
    
    def test_01_initial_state_incomplete(self):
        """Test 1: Estado inicial debe estar incompleto"""
        status = OnboardingService.get_setup_status(self.colegio.rbd)
        
        self.assertFalse(status['setup_complete'])
        self.assertEqual(len(status['steps']), 4)
        
        # Todos los pasos deben estar incompletos
        for step in status['steps']:
            self.assertFalse(step['completado'])
        
        # Progreso debe ser 0%
        progress = OnboardingService.get_setup_progress_percentage(self.colegio.rbd)
        self.assertEqual(progress, 0)
    
    def test_02_create_ciclo_academico(self):
        """Test 2: Crear ciclo acadÃ©mico completa el primer paso"""
        # Antes: paso incompleto
        status_before = OnboardingService.get_setup_status(self.colegio.rbd)
        self.assertFalse(status_before['steps'][0]['completado'])
        
        # Crear ciclo acadÃ©mico
        ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='Primer Semestre 2024',
            anio=2024,
            fecha_inicio=(datetime.now() - timedelta(days=60)).date(),
            fecha_fin=(datetime.now() + timedelta(days=180)).date(),
            estado=CICLO_ESTADO_ACTIVO
        )
        
        # DespuÃ©s: paso completo
        status_after = OnboardingService.get_setup_status(self.colegio.rbd)
        self.assertTrue(status_after['steps'][0]['completado'])
        self.assertFalse(status_after['setup_complete'])
        
        # Progreso debe ser 25%
        progress = OnboardingService.get_setup_progress_percentage(self.colegio.rbd)
        self.assertEqual(progress, 25)
    
    def test_03_create_cursos(self):
        """Test 3: Crear cursos completa el segundo paso"""
        # Prerequisito: crear ciclo
        ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='Primer Semestre 2024',
            anio=2024,
            fecha_inicio=(datetime.now() - timedelta(days=60)).date(),
            fecha_fin=(datetime.now() + timedelta(days=180)).date(),
            estado=CICLO_ESTADO_ACTIVO
        )
        
        # Crear nivel
        nivel = NivelEducativo.objects.create(nombre='BÃ¡sica')
        
        # Crear curso
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo=ciclo,
            nivel=nivel,
            grado='1',
            letra='A'
        )
        
        # Verificar progreso
        status = OnboardingService.get_setup_status(self.colegio.rbd)
        self.assertTrue(status['steps'][0]['completado'])
        self.assertTrue(status['steps'][1]['completado'])
        self.assertFalse(status['setup_complete'])
        
        progress = OnboardingService.get_setup_progress_percentage(self.colegio.rbd)
        self.assertEqual(progress, 50)
    
    def test_04_create_profesores(self):
        """Test 4: Crear profesores completa el tercer paso"""
        # Prerequisites: ciclo y cursos
        ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='Primer Semestre 2024',
            anio=2024,
            fecha_inicio=(datetime.now() - timedelta(days=60)).date(),
            fecha_fin=(datetime.now() + timedelta(days=180)).date(),
            estado=CICLO_ESTADO_ACTIVO
        )
        
        nivel = NivelEducativo.objects.create(nombre='BÃ¡sica')
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo=ciclo,
            nivel=nivel,
            grado='1',
            letra='A'
        )
        
        # Crear profesor
        rol_profesor = Role.objects.create(nombre=ROL_PROFESOR)
        profesor = User.objects.create_user(
            username='profesor_test',
            email='profesor@test.cl',
            password='profesor123',
            rbd_colegio=self.colegio.rbd,
            role=rol_profesor
        )
        
        # Verificar progreso
        status = OnboardingService.get_setup_status(self.colegio.rbd)
        self.assertTrue(status['steps'][2]['completado'])
        self.assertFalse(status['setup_complete'])
        
        progress = OnboardingService.get_setup_progress_percentage(self.colegio.rbd)
        self.assertEqual(progress, 75)
    
    def test_05_complete_setup(self):
        """Test 5: Crear estudiantes completa la configuraciÃ³n"""
        # Prerequisites: todo lo anterior
        ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='Primer Semestre 2024',
            anio=2024,
            fecha_inicio=(datetime.now() - timedelta(days=60)).date(),
            fecha_fin=(datetime.now() + timedelta(days=180)).date(),
            estado=CICLO_ESTADO_ACTIVO
        )
        
        nivel = NivelEducativo.objects.create(nombre='BÃ¡sica')
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo=ciclo,
            nivel=nivel,
            grado='1',
            letra='A'
        )
        
        rol_profesor = Role.objects.create(nombre=ROL_PROFESOR)
        profesor = User.objects.create_user(
            username='profesor_test',
            email='profesor@test.cl',
            password='profesor123',
            rbd_colegio=self.colegio.rbd,
            role=rol_profesor
        )
        
        # Crear estudiante
        rol_estudiante = Role.objects.create(nombre=ROL_ESTUDIANTE)
        estudiante = User.objects.create_user(
            username='estudiante_test',
            email='estudiante@test.cl',
            password='estudiante123',
            rbd_colegio=self.colegio.rbd,
            role=rol_estudiante
        )
        
        # Verificar configuraciÃ³n completa
        status = OnboardingService.get_setup_status(self.colegio.rbd)
        self.assertTrue(status['setup_complete'])
        
        # Todos los pasos deben estar completos
        for step in status['steps']:
            self.assertTrue(step['completado'])
        
        # Progreso debe ser 100%
        progress = OnboardingService.get_setup_progress_percentage(self.colegio.rbd)
        self.assertEqual(progress, 100)
    
    def test_06_prerequisite_validation_blocks_curso_creation(self):
        """Test 6: Validación de prerequisitos bloquea creación de cursos sin ciclo"""
        # Contrato vigente: retorna dict con valid=False (no lanza excepción).
        result = OnboardingService.validate_prerequisite('CREATE_CURSO', self.colegio.rbd)
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
        self.assertEqual(result['error']['error_type'], 'MISSING_CICLO_ACTIVO')

    def test_07_prerequisite_validation_blocks_evaluacion_creation(self):
        """Test 7: Validación de prerequisitos bloquea creación de evaluaciones"""
        # Contrato vigente: retorna dict con valid=False (no lanza excepción).
        result = OnboardingService.validate_prerequisite('CREATE_EVALUACION', self.colegio.rbd)
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
        self.assertEqual(result['error']['error_type'], 'MISSING_TEACHERS_ASSIGNED')

    def test_08_checklist_view_accessible(self):
        """Test 8: Vista de checklist es accesible para admin"""
        response = self.client.get(reverse('setup_checklist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configur')
    
    def test_09_wizard_view_accessible(self):
        """Test 9: Vista de wizard es accesible para admin"""
        response = self.client.get(reverse('setup_wizard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Asistente de Configur')
    
    def test_10_dashboard_shows_setup_banner(self):
        """Test 10: Dashboard muestra banner de configuraciÃ³n incompleta"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Debe contener el banner de setup
        self.assertContains(response, 'setup-alert-banner')
    
    def test_11_notification_created_on_incomplete_setup(self):
        """Test 11: Se crea notificaciÃ³n automÃ¡tica con setup incompleto"""
        from backend.apps.notificaciones.models import Notificacion
        from backend.common.services.onboarding_notification_service import OnboardingNotificationService
        
        # Crear notificaciÃ³n
        notif = OnboardingNotificationService.notify_if_needed(self.admin, self.colegio.rbd)
        
        # Debe haberse creado
        self.assertIsNotNone(notif)
        self.assertEqual(notif.tipo, 'sistema')
        self.assertIn('Configur', notif.titulo)
        
        # Segunda llamada no debe crear otra notificaciÃ³n (cooldown)
        notif2 = OnboardingNotificationService.notify_if_needed(self.admin, self.colegio.rbd)
        self.assertIsNone(notif2)
    
    def test_12_legacy_school_detection(self):
        """Test 12: DetecciÃ³n correcta de colegios legacy"""
        # Crear colegio con todos los datos
        ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='Primer Semestre 2024',
            anio=2024,
            fecha_inicio=(datetime.now() - timedelta(days=60)).date(),
            fecha_fin=(datetime.now() + timedelta(days=180)).date(),
            estado=CICLO_ESTADO_ACTIVO
        )
        
        nivel = NivelEducativo.objects.create(nombre='BÃ¡sica')
        curso = Curso.objects.create(
            colegio=self.colegio,
            ciclo=ciclo,
            nivel=nivel,
            grado='1',
            letra='A'
        )
        
        rol_profesor = Role.objects.create(nombre=ROL_PROFESOR)
        profesor = User.objects.create_user(
            username='profesor_test',
            email='profesor@test.cl',
            password='profesor123',
            rbd_colegio=self.colegio.rbd,
            role=rol_profesor
        )
        
        rol_estudiante = Role.objects.create(nombre=ROL_ESTUDIANTE)
        estudiante = User.objects.create_user(
            username='estudiante_test',
            email='estudiante@test.cl',
            password='estudiante123',
            rbd_colegio=self.colegio.rbd,
            role=rol_estudiante
        )
        
        # Debe ser detectado como legacy (configuraciÃ³n completa)
        is_legacy = OnboardingService.is_legacy_school(self.colegio.rbd)
        self.assertTrue(is_legacy)


class OnboardingWizardIntegrationTest(TestCase):
    """Tests de integraciÃ³n para el wizard de configuraciÃ³n"""
    
    def setUp(self):
        """ConfiguraciÃ³n inicial"""
        self.colegio = Colegio.objects.create(
            rbd='54321',
            nombre='Colegio Wizard Test',
            direccion='Av Test 456'
        )
        
        self.rol_admin = Role.objects.create(nombre=ROL_ADMIN)
        self.admin = User.objects.create_user(
            username='admin_wizard',
            email='admin.wizard@test.cl',
            password='wizard123',
            rbd_colegio=self.colegio.rbd,
            role=self.rol_admin
        )
        
        self.client = Client()
        self.client.force_login(self.admin)
    
    def test_wizard_step_1_ciclo(self):
        """Test: Wizard paso 1 - Crear ciclo acadÃ©mico"""
        response = self.client.post(reverse('setup_wizard'), {
            'nombre': 'Primer Semestre 2024',
            'anio': 2024,
            'fecha_inicio': '2024-03-01',
            'fecha_fin': '2024-09-15'
        })
        
        # Debe redirigir
        self.assertEqual(response.status_code, 302)
        
        # Ciclo debe estar creado
        ciclo = CicloAcademico.objects.filter(colegio=self.colegio).first()
        self.assertIsNotNone(ciclo)
        self.assertEqual(ciclo.nombre, 'Primer Semestre 2024')
        
        # Progreso debe ser 25%
        progress = OnboardingService.get_setup_progress_percentage(self.colegio.rbd)
        self.assertEqual(progress, 25)
    
    def test_wizard_completes_full_flow(self):
        """Test: Wizard completa flujo completo paso a paso"""
        # Prerequisito: crear nivel
        nivel = NivelEducativo.objects.create(nombre='BÃ¡sica')
        
        # Paso 1: Ciclo
        self.client.post(reverse('setup_wizard'), {
            'nombre': 'Primer Semestre 2024',
            'anio': 2024,
            'fecha_inicio': '2024-03-01',
            'fecha_fin': '2024-09-15'
        })
        
        # Paso 2: Curso
        self.client.post(reverse('setup_wizard'), {
            'nivel': nivel.id_nivel,
            'grado': '1',
            'letra': 'A',
            'cantidad': 1
        })
        
        # Paso 3: Profesor
        self.client.post(reverse('setup_wizard'), {
            'username': 'profesor1',
            'email': 'profesor1@test.cl',
            'password': 'Px9!Nube2026',
            'password_confirm': 'Px9!Nube2026',
            'first_name': 'Juan',
            'last_name': 'PÃ©rez',
            'rut': '12345678-5'
        })
        
        # Paso 4: Estudiante
        self.client.post(reverse('setup_wizard'), {
            'estudiante_username': 'estudiante1',
            'estudiante_email': 'estudiante1@test.cl',
            'estudiante_password': 'Ez7!Roca2040',
            'estudiante_password_confirm': 'Ez7!Roca2040',
            'estudiante_first_name': 'MarÃ­a',
            'estudiante_last_name': 'GonzÃ¡lez',
            'estudiante_rut': '22222222-2',
            'apoderado_username': 'apoderado1',
            'apoderado_email': 'apoderado1@test.cl',
            'apoderado_password': 'Ap0!Bosque55',
            'apoderado_password_confirm': 'Ap0!Bosque55',
            'apoderado_first_name': 'Pedro',
            'apoderado_last_name': 'GonzÃ¡lez',
            'apoderado_rut': '11111111-1',
            'parentesco': 'padre'
        })
        
        # Verificar configuraciÃ³n completa
        status = OnboardingService.get_setup_status(self.colegio.rbd)
        self.assertTrue(status['setup_complete'])
        
        progress = OnboardingService.get_setup_progress_percentage(self.colegio.rbd)
        self.assertEqual(progress, 100)



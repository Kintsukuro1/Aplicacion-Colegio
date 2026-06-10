"""
Tests de regresión para validar correcciones de permisos y datos en 0.
Verifica que estudiantes pueden acceder a sus datos sin errores de permisos.
"""
import sys
import os
from django.core.exceptions import PermissionDenied

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.common.test_base import BaseTestCase

from backend.apps.core.services.dashboard_context_service import DashboardContextService
from backend.apps.core.services.dashboard_graficos_service import DashboardGraficosService
from backend.apps.academico.services.attendance_service import AttendanceService
from backend.apps.academico.services.grades_service import GradesService
from backend.apps.academico.services.academic_view_service import AcademicViewService


class EstudiantePermisosRegresionTest(BaseTestCase):
    """Tests de regresión para validar que estudiantes pueden acceder a sus datos"""

    def setUp(self):
        """Configurar usuario estudiante para tests"""
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
        # Este bloque valida escenarios "sin curso actual".
        self.perfil.ciclo_actual = None
        self.perfil.curso_actual_id = None
        self.perfil.save(update_fields=['ciclo_actual', 'curso_actual_id'])
        
    def test_estudiante_puede_acceder_dashboard_context(self):
        """
        REGRESIÓN: get_estudiante_context estaba bloqueado por decorador VIEW_STUDENTS.
        Ahora debe permitir acceso a estudiantes con validación manual.
        """
        try:
            context = DashboardContextService.get_estudiante_context(
                user=self.user,
                pagina_solicitada='inicio',
                escuela_rbd=self.user.rbd_colegio,
                request_get_params=None
            )
            
            # Debe retornar datos, no lanzar PermissionDenied
            self.assertIsNotNone(context)
            self.assertIn('sin_datos', context)
            
            # Validar que tiene flag sin_datos por no tener curso_actual
            self.assertTrue(context['sin_datos'], "Debe tener flag sin_datos=True cuando no hay curso")
            
        except PermissionDenied:
            self.fail("Estudiante no debe recibir PermissionDenied al acceder a su dashboard")
    
    def test_estudiante_puede_acceder_estadisticas(self):
        """
        REGRESIÓN: get_datos_estadisticas estaba bloqueado por decorador VIEW_STUDENTS.
        Ahora debe permitir acceso a estudiantes con validación manual.
        """
        try:
            stats = DashboardGraficosService.get_datos_estadisticas(
                user=self.user,
                rol='estudiante',
                escuela_rbd=self.user.rbd_colegio
            )
            
            # Debe retornar datos, no lanzar PermissionDenied
            self.assertIsNotNone(stats)
            
        except PermissionDenied:
            self.fail("Estudiante no debe recibir PermissionDenied al acceder a estadísticas")
    
    def test_estudiante_puede_acceder_resumen_asistencia(self):
        """
        REGRESIÓN: get_student_attendance_summary estaba bloqueado por VIEW_ATTENDANCE.
        Ahora usa require_permission_any para permitir VIEW_OWN_ATTENDANCE.
        """
        try:
            resumen = AttendanceService.get_student_attendance_summary(
                user=self.user,
                mes_filtro=None,
                anio_filtro=None
            )
            
            # Debe retornar datos, no lanzar PermissionDenied
            self.assertIsNotNone(resumen)
            self.assertIn('total_registros', resumen)
            
        except PermissionDenied:
            self.fail("Estudiante no debe recibir PermissionDenied al ver su asistencia")
    
    def test_estudiante_puede_acceder_perfil(self):
        """
        REGRESIÓN: get_student_profile_and_course estaba bloqueado por VIEW_STUDENTS.
        Ahora usa require_permission_any para permitir VIEW_OWN_GRADES.
        """
        try:
            perfil, curso = AttendanceService.get_student_profile_and_course(self.user)
            
            # Debe retornar perfil (aunque sea None), no lanzar PermissionDenied
            # perfil puede ser None si no existe, pero no debe haber error de permisos
            self.assertIsNotNone(perfil)  # En este caso existe porque lo creamos en setUp
            
        except PermissionDenied:
            self.fail("Estudiante no debe recibir PermissionDenied al acceder a su perfil")
    
    def test_estudiante_puede_ver_notas(self):
        """
        REGRESIÓN: calculate_grades_by_subject validación manual permite estudiantes.
        """
        try:
            # Obtener perfil primero
            perfil, curso_actual = AcademicViewService.get_student_profile(self.user)
            
            # Calcular notas (curso_actual puede ser None)
            resultado = AcademicViewService.calculate_grades_by_subject(
                user=self.user,
                curso_actual=curso_actual
            )
            
            # Debe retornar estructura con sin_datos
            self.assertIsNotNone(resultado)
            self.assertIn('sin_datos', resultado)
            self.assertTrue(resultado['sin_datos'], "Debe tener sin_datos=True cuando no hay curso")
            
        except PermissionDenied:
            self.fail("Estudiante no debe recibir PermissionDenied al ver sus notas")


class FlagSinDatosTest(BaseTestCase):
    """Tests para validar flag sin_datos en servicios"""

    def setUp(self):
        """Configurar usuario estudiante para tests"""
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
    
    def test_flag_sin_datos_en_notas_sin_curso(self):
        """
        VALIDACIÓN: Flag sin_datos debe ser True cuando estudiante no tiene curso_actual.
        """
        resultado = AcademicViewService.calculate_grades_by_subject(
            user=self.user,
            curso_actual=None  # Sin curso asignado
        )
        
        self.assertTrue(resultado['sin_datos'], "sin_datos debe ser True cuando no hay curso")
        self.assertEqual(resultado['promedio_general'], 0)
        self.assertEqual(resultado['total_notas'], 0)
    
    def test_flag_sin_datos_en_dashboard_sin_perfil(self):
        """
        VALIDACIÓN: Dashboard debe retornar sin_datos=True cuando no existe PerfilEstudiante.
        """
        from backend.apps.accounts.models import User
        from backend.apps.core.services.dashboard_service import DashboardService
        
        # Crear usuario sin perfil
        user_sin_perfil = User.objects.create_user(
            email='sinperfil@test.com',
            password='test123',
            nombre='Sin',
            apellido_paterno='Perfil',
            role=self.rol_estudiante
        )
        
        # El método _get_estudiante_inicio_context maneja PerfilEstudiante.DoesNotExist
        # y debe retornar sin_datos=True
        from backend.apps.core.services.dashboard_service import DashboardService
        context = DashboardService._get_estudiante_inicio_context(
            user_sin_perfil,
            escuela_rbd=12345
        )
        
        self.assertTrue(context['sin_datos'], "sin_datos debe ser True cuando no hay perfil")
        self.assertEqual(context['porcentaje_asistencia'], 100)  # Valor default engañoso pero documentado


class DivisionPorCeroTest(BaseTestCase):
    """Tests para validar protección contra divisiones por cero"""

    def setUp(self):
        """Configurar datos de prueba"""
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
    
    def test_division_protegida_en_asistencia(self):
        """
        VALIDACIÓN: Cálculo de porcentaje de asistencia debe proteger división por 0.
        """
        from backend.apps.core.services.dashboard_service import DashboardService
        
        # Usuario sin registros de asistencia no debe causar ZeroDivisionError
        context = DashboardService._get_estudiante_inicio_context(
            self.user,
            escuela_rbd=self.user.rbd_colegio
        )
        
        # No debe lanzar excepción
        self.assertIsNotNone(context)
        self.assertIn('porcentaje_asistencia', context)
        # Valor puede ser 100 (default) o 0, pero no debe causar error
    
    def test_promedio_sin_notas_no_causa_error(self):
        """
        VALIDACIÓN: Cálculo de promedio sin notas debe manejar len(notas)=0.
        """
        resultado = AcademicViewService.calculate_grades_by_subject(
            user=self.user,
            curso_actual=None
        )
        
        # No debe lanzar ZeroDivisionError
        self.assertEqual(resultado['promedio_general'], 0)
        self.assertTrue(resultado['sin_datos'])


class ValidacionEntidadesClaveTest(BaseTestCase):
    """Tests para validar que se logean warnings cuando faltan entidades clave"""

    def setUp(self):
        """Configurar datos de prueba"""
        super().setUp()
        self.user, self.perfil = self.crear_usuario_estudiante()
    
    def test_warning_cuando_no_hay_perfil(self):
        """
        VALIDACIÓN: Debe logear warning cuando usuario no tiene PerfilEstudiante.
        """
        from backend.apps.accounts.models import User
        import logging
        
        # Crear usuario sin perfil
        user_sin_perfil = User.objects.create_user(
            email='sinperfil2@test.com',
            password='test123',
            nombre='Sin',
            apellido_paterno='Perfil2',
            role=self.rol_estudiante
        )
        
        # Capturar logs
        with self.assertLogs('backend.apps.academico.services.academic_view_service', level='WARNING') as cm:
            perfil, curso = AcademicViewService.get_student_profile(user_sin_perfil)
            
            # Debe haber logeado warning
            self.assertTrue(any('no tiene PerfilEstudiante' in msg for msg in cm.output))
    
    def test_warning_cuando_no_hay_curso_actual(self):
        """
        VALIDACIÓN: Debe logear warning cuando estudiante no tiene curso_actual.
        """
        import logging
        
        # El perfil del usuario no tiene curso_actual asignado
        with self.assertLogs('backend.apps.academico.services.academic_view_service', level='WARNING') as cm:
            resultado = AcademicViewService.calculate_grades_by_subject(
                user=self.user,
                curso_actual=None
            )
            
            # Debe haber logeado warning
            self.assertTrue(any('sin curso_actual asignado' in msg for msg in cm.output))

"""
OnboardingService - Detecta configuración incompleta de colegios.

Este servicio valida el estado de configuración de un colegio
siguiendo los 4 pasos obligatorios del onboarding:
1. Ciclo Académico activo
2. Cursos creados
3. Profesores asignados
4. Estudiantes matriculados

Principios:
- Queries simples con .exists() (sin optimización prematura)
- Usa constantes del sistema (no strings hardcodeados)
- Retorna estado estructurado para decisiones en views
- No cachea (mantiene simplicidad)
"""

from datetime import timedelta
from django.utils import timezone

from backend.common.services.policy_service import PolicyService
from backend.common.constants import (
    CICLO_ESTADO_ACTIVO,
    ESTADO_MATRICULA_ACTIVA,
)
from backend.common.utils.error_response import (
    MISSING_CICLO_ACTIVO,
    MISSING_COURSES,
    MISSING_TEACHERS_ASSIGNED,
    MISSING_STUDENTS_ENROLLED,
    ERROR_MESSAGES,
)


class OnboardingService:
    """
    Servicio de detección de configuración incompleta.
    
    Responsabilidades:
    - Validar 4 pasos obligatorios de configuración
    - Retornar estado estructurado con pasos faltantes
    - Identificar colegios legacy (ya configurados)
    - Proporcionar validaciones para prerequisites
    """
    
    @staticmethod
    def get_setup_status(colegio_rbd):
        """
        Obtiene el estado de configuración de un colegio.
        
        Args:
            colegio_rbd (str): RBD del colegio
            
        Returns:
            dict: {
                'has_active_ciclo': bool,
                'has_courses': bool,
                'has_teachers': bool,
                'has_students': bool,
                'setup_complete': bool,
                'missing_steps': [str],  # Códigos tipo MISSING_CICLO_ACTIVO
                'next_required_step': int,  # 1-4
                'steps': [dict]  # Lista de pasos con 'nombre' y 'completado'
            }
        """
        from backend.apps.institucion.models import CicloAcademico, Colegio
        from backend.apps.cursos.models import Curso, Clase
        from backend.apps.matriculas.models import Matricula
        from backend.apps.accounts.models import User, Role
        
        # Paso 1: Validar ciclo académico activo
        has_active_ciclo = CicloAcademico.objects.filter(
            colegio__rbd=colegio_rbd,
            estado=CICLO_ESTADO_ACTIVO
        ).exists()
        
        # Paso 2: Validar cursos activos con ciclo activo
        has_courses = Curso.objects.filter(
            colegio__rbd=colegio_rbd,
            ciclo_academico__estado=CICLO_ESTADO_ACTIVO,
            activo=True
        ).exists()
        
        # Paso 3: Validar que existan profesores activos
        # Camino principal: perfil académico explícito.
        has_teachers = User.objects.filter(
            is_active=True,
            perfil_profesor__isnull=False,
            rbd_colegio=colegio_rbd,
        ).exists()
        # Compatibilidad transicional para datos legacy aún no migrados.
        if not has_teachers:
            active_users = User.objects.filter(
                is_active=True,
                rbd_colegio=colegio_rbd,
            ).select_related('role')
            has_teachers = any(
                PolicyService.has_capability(u, 'CLASS_TAKE_ATTENDANCE')
                and not PolicyService.has_capability(u, 'SYSTEM_CONFIGURE')
                and not PolicyService.has_capability(u, 'SYSTEM_ADMIN')
                and not PolicyService.has_capability(u, 'USER_ASSIGN_ROLE')
                for u in active_users
            )
        
        # Paso 4: Validar que existan estudiantes activos
        # Camino principal: perfil académico explícito.
        has_students = User.objects.filter(
            is_active=True,
            perfil_estudiante__isnull=False,
            rbd_colegio=colegio_rbd,
        ).exists()
        # Compatibilidad transicional para datos legacy aún no migrados.
        if not has_students:
            active_users = User.objects.filter(
                is_active=True,
                rbd_colegio=colegio_rbd,
            ).select_related('role')
            has_students = any(
                PolicyService.has_capability(u, 'CLASS_VIEW')
                and PolicyService.has_capability(u, 'GRADE_VIEW')
                and not PolicyService.has_capability(u, 'STUDENT_VIEW')
                and not PolicyService.has_capability(u, 'SYSTEM_CONFIGURE')
                and not PolicyService.has_capability(u, 'SYSTEM_ADMIN')
                for u in active_users
            )
        
        # Calcular setup_complete
        setup_complete = all([
            has_active_ciclo,
            has_courses,
            has_teachers,
            has_students
        ])
        
        # Generar missing_steps y next_required_step
        missing_steps = []
        next_required_step = None
        
        if not has_active_ciclo:
            missing_steps.append(MISSING_CICLO_ACTIVO)
            if next_required_step is None:
                next_required_step = 1
                
        if not has_courses:
            missing_steps.append(MISSING_COURSES)
            if next_required_step is None:
                next_required_step = 2
                
        if not has_teachers:
            missing_steps.append(MISSING_TEACHERS_ASSIGNED)
            if next_required_step is None:
                next_required_step = 3
                
        if not has_students:
            missing_steps.append(MISSING_STUDENTS_ENROLLED)
            if next_required_step is None:
                next_required_step = 4
        
        # Si todo está completo, no hay próximo step
        if setup_complete:
            next_required_step = None
        
        # Construir lista de steps para compatibilidad con notificaciones
        steps = [
            {
                'key': 'ciclo_academico',
                'nombre': 'Crear Ciclo Académico activo',
                'completado': has_active_ciclo
            },
            {
                'key': 'cursos',
                'nombre': 'Crear al menos un curso',
                'completado': has_courses
            },
            {
                'key': 'profesores',
                'nombre': 'Asignar al menos un profesor',
                'completado': has_teachers
            },
            {
                'key': 'estudiantes',
                'nombre': 'Matricular al menos un estudiante',
                'completado': has_students
            }
        ]
        
        return {
            'has_active_ciclo': has_active_ciclo,
            'has_courses': has_courses,
            'has_teachers': has_teachers,
            'has_students': has_students,
            'setup_complete': setup_complete,
            'missing_steps': missing_steps,
            'next_required_step': next_required_step,
            'steps': steps,
        }
    
    @staticmethod
    def is_legacy_school(colegio_rbd):
        """
        Determina si un colegio es legacy (ya configurado anteriormente).
        
        Un colegio es legacy si:
        - Setup está completo
        - Ciclo activo tiene más de 30 días de antigüedad
        
        Este flag NO mide actividad operacional, solo antigüedad del setup.
        
        Args:
            colegio_rbd (str): RBD del colegio
            
        Returns:
            bool: True si es colegio legacy
        """
        from backend.apps.institucion.models import CicloAcademico
        
        status = OnboardingService.get_setup_status(colegio_rbd)
        
        if not status['setup_complete']:
            return False
        
        # Validar antigüedad del ciclo activo
        ciclo = CicloAcademico.objects.filter(
            colegio__rbd=colegio_rbd,
            estado=CICLO_ESTADO_ACTIVO
        ).first()
        
        if not ciclo:
            return False
        
        # Ciclo con más de 30 días desde fecha_inicio
        threshold_date = timezone.now().date() - timedelta(days=30)
        return ciclo.fecha_inicio < threshold_date
    
    @staticmethod
    def validate_prerequisite(action_type, colegio_rbd):
        """
        Valida que los prerequisitos para una acción estén cumplidos.
        
        Args:
            action_type (str): Tipo de acción (ej: 'CREATE_CURSO')
            colegio_rbd (str): RBD del colegio
            
        Returns:
            dict: {'valid': bool, 'error': dict or None}
            
        Example:
            result = OnboardingService.validate_prerequisite('CREATE_CURSO', '12345')
            if not result['valid']:
                raise PrerequisiteException(result['error']['error_type'])
        """
        from backend.common.utils.error_response import ErrorResponseBuilder
        
        status = OnboardingService.get_setup_status(colegio_rbd)
        
        # Mapeo de acciones a prerequisitos
        prerequisites_map = {
            'CREATE_CURSO': 'has_active_ciclo',
            'ASSIGN_PROFESOR': 'has_courses',
            'ASSIGN_ESTUDIANTE': 'has_courses',
            'CREATE_EVALUACION': 'has_teachers',
        }
        
        prerequisite_error_map = {
            'has_active_ciclo': MISSING_CICLO_ACTIVO,
            'has_courses': MISSING_COURSES,
            'has_teachers': MISSING_TEACHERS_ASSIGNED,
            'has_students': MISSING_STUDENTS_ENROLLED,
        }
        
        if action_type not in prerequisites_map:
            # Acción no requiere validación de prerequisitos
            return {'valid': True, 'error': None}
        
        prerequisite_key = prerequisites_map[action_type]
        
        if not status[prerequisite_key]:
            error_type = prerequisite_error_map[prerequisite_key]
            error = ErrorResponseBuilder.build(error_type, {'colegio_rbd': colegio_rbd})
            return {'valid': False, 'error': error}
        
        return {'valid': True, 'error': None}
    
    @staticmethod
    def get_setup_progress_percentage(colegio_rbd):
        """
        Calcula el porcentaje de progreso del setup.
        
        Args:
            colegio_rbd (str): RBD del colegio
            
        Returns:
            int: Porcentaje de 0 a 100
        """
        status = OnboardingService.get_setup_status(colegio_rbd)
        
        steps_completed = sum([
            status['has_active_ciclo'],
            status['has_courses'],
            status['has_teachers'],
            status['has_students'],
        ])
        
        return int((steps_completed / 4) * 100)


# ============================================================================
# Helpers de Validación
# ============================================================================

def require_setup_complete(view_func):
    """
    Decorator que requiere setup completo para ejecutar una vista.
    
    Usage:
        @require_setup_complete
        def my_view(request):
            # Solo se ejecuta si setup está completo
            pass
    """
    from functools import wraps
    from django.shortcuts import redirect
    from django.contrib import messages
    from backend.common.utils.error_response import ErrorResponseBuilder, SCHOOL_NOT_CONFIGURED
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Obtener RBD del colegio desde sesión
        rbd_colegio = request.session.get('rbd_colegio')
        
        if not rbd_colegio:
            messages.error(request, 'Sesión inválida - sin escuela asignada')
            return redirect('login')
        
        status = OnboardingService.get_setup_status(rbd_colegio)
        
        if not status['setup_complete']:
            error = ErrorResponseBuilder.build(SCHOOL_NOT_CONFIGURED)
            redirect_url = ErrorResponseBuilder.to_django_message(request, error)
            return redirect(redirect_url)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

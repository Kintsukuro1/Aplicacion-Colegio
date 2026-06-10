"""
Servicio para consultar y validar el estado de configuración inicial de un colegio.

Este servicio es SOLO DE CONSULTA - nunca lanza excepciones.
Las excepciones se reservan para ACCIONES que requieren estado válido.

Responsabilidades:
- Detectar pasos de setup faltantes
- Retornar estado estructurado del setup
- Indicar siguiente paso requerido
- NO modificar datos
- NO lanzar excepciones
"""
from datetime import date
from backend.apps.institucion.models import Colegio, CicloAcademico
from backend.apps.cursos.models import Curso, Clase
from backend.apps.matriculas.models import Matricula
from django.contrib.auth import get_user_model


class SetupService:
    """
    Servicio para consultar el estado de configuración de un colegio.
    
    Filosofía:
    - Estado = datos → NO excepciones
    - Acción = intención → SÍ excepciones (pero no aquí)
    """

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        SetupService.validate(operation, params)
        return SetupService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(SetupService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')
    
    @staticmethod
    def _is_valid_ciclo(ciclo):
        """
        Valida que un ciclo académico tenga fechas consistentes.
        
        Un ciclo es válido si:
        - fecha_fin >= fecha_inicio
        - Si está ACTIVO, fecha_fin no debe estar en el pasado
        
        Args:
            ciclo: instancia de CicloAcademico
            
        Returns:
            bool: True si el ciclo es válido
        """
        # Validar orden de fechas
        if ciclo.fecha_fin < ciclo.fecha_inicio:
            return False
        
        # Si está activo, no debe haber expirado
        if ciclo.estado == 'ACTIVO':
            hoy = date.today()
            if ciclo.fecha_fin < hoy:
                return False
        
        return True
    
    @staticmethod
    def get_setup_status(rbd_colegio):
        """
        Obtiene el estado de configuración del colegio.
        
        Retorna estructura con:
        - setup_complete: bool - si el setup está completo
        - missing_steps: list - códigos de pasos faltantes (ej: MISSING_CICLO_ACTIVO)
        - next_required_step: int - número del siguiente paso a completar (1-based)
        - total_steps: int - total de pasos de setup
        - completed_steps: int - pasos ya completados
        
        IMPORTANTE: Este método NUNCA lanza excepciones.
        Si hay error consultando, retorna estado indicando problema.
        
        Args:
            rbd_colegio: RBD del colegio a consultar
            
        Returns:
            dict con estructura de estado
        """
        try:
            colegio = Colegio.objects.get(rbd=rbd_colegio)
        except Colegio.DoesNotExist:
            # Colegio no existe - retornar estado indicando problema crítico
            return {
                'setup_complete': False,
                'missing_steps': ['COLEGIO_NOT_FOUND'],
                'next_required_step': None,
                'next_step': None,
                'total_steps': 5,
                'completed_steps': 0,
                'error': True,
                'error_message': 'Colegio no encontrado'
            }
        
        # Detectar pasos faltantes
        missing_steps = []
        completed_steps = 0
        total_steps = 5  # Total de pasos críticos de setup
        
        # PASO 1: Ciclo académico activo y válido
        ciclos_activos = CicloAcademico.objects.filter(
            colegio=colegio,
            estado='ACTIVO'
        )
        
        # Verificar que existe al menos un ciclo activo CON FECHAS VÁLIDAS
        has_valid_active_ciclo = any(
            SetupService._is_valid_ciclo(ciclo) 
            for ciclo in ciclos_activos
        )
        
        if has_valid_active_ciclo:
            completed_steps += 1
        else:
            missing_steps.append('MISSING_CICLO_ACTIVO')

        ciclos_activos_validos_ids = [
            ciclo.id for ciclo in ciclos_activos if SetupService._is_valid_ciclo(ciclo)
        ]
        
        # PASO 2: Al menos un curso activo en ciclo activo
        has_cursos = Curso.objects.filter(
            colegio=colegio,
            activo=True,
            ciclo_academico_id__in=ciclos_activos_validos_ids,
        ).exists()

        if has_cursos:
            completed_steps += 1
        else:
            missing_steps.append('MISSING_CURSOS')

        # PASO 3: Al menos un profesor activo del colegio
        User = get_user_model()
        has_profesores = User.objects.filter(
            rbd_colegio=colegio.rbd,
            perfil_profesor__isnull=False,
            is_active=True,
        ).exists()

        if has_profesores:
            completed_steps += 1
        else:
            missing_steps.append('MISSING_PROFESOR')

        # PASO 4: Al menos un estudiante matriculado (matrícula activa)
        has_estudiantes_matriculados = Matricula.objects.filter(
            colegio=colegio,
            estado='ACTIVA',
            ciclo_academico_id__in=ciclos_activos_validos_ids,
        ).exists()

        if has_estudiantes_matriculados:
            completed_steps += 1
        else:
            missing_steps.append('MISSING_STUDENT_ENROLLED')

        # PASO 5: Al menos una clase creada en ciclo activo
        has_clases = Clase.objects.filter(
            colegio=colegio,
            activo=True,
            curso__ciclo_academico_id__in=ciclos_activos_validos_ids,
        ).exists()

        if has_clases:
            completed_steps += 1
        else:
            missing_steps.append('MISSING_CLASS_CREATED')

        # Determinar siguiente paso requerido
        # Prioridad: ciclo -> cursos -> profesor -> estudiante matriculado -> clase
        step_priority = {
            'MISSING_CICLO_ACTIVO': 1,
            'MISSING_CURSOS': 2,
            'MISSING_PROFESOR': 3,
            'MISSING_STUDENT_ENROLLED': 4,
            'MISSING_CLASS_CREATED': 5,
        }
        
        next_step = None
        if missing_steps:
            # Encontrar el paso con menor prioridad (más importante)
            next_step = min(
                [step_priority.get(step, 999) for step in missing_steps]
            )
        
        # Construir respuesta
        return {
            'setup_complete': len(missing_steps) == 0,
            'missing_steps': missing_steps,
            'next_required_step': next_step,
            'next_step': next_step,
            'total_steps': total_steps,
            'completed_steps': completed_steps,
            'completion_percentage': int((completed_steps / total_steps) * 100)
        }
    
    @staticmethod
    def get_setup_step_details(step_code):
        """
        Obtiene detalles sobre un paso específico del setup.
        
        Retorna información útil para guiar al usuario:
        - Nombre del paso
        - Descripción
        - URL de acción
        - Ayuda adicional
        
        Args:
            step_code: Código del paso (ej: MISSING_CICLO_ACTIVO)
            
        Returns:
            dict con detalles del paso
        """
        step_details = {
            'MISSING_CICLO_ACTIVO': {
                'name': 'Configurar Ciclo Académico',
                'description': 'Debes crear y activar un ciclo académico para empezar a operar',
                'action_url': '/setup/ciclo/',
                'priority': 1,
                'required_for': 'Crear cursos, matrículas y clases'
            },
            'MISSING_CURSOS': {
                'name': 'Crear Cursos',
                'description': 'Debes crear al menos un curso activo en el ciclo activo',
                'action_url': '/setup/cursos/',
                'priority': 2,
                'required_for': 'Matricular estudiantes y crear clases'
            },
            'MISSING_PROFESOR': {
                'name': 'Crear Profesor',
                'description': 'Debes registrar al menos un profesor activo en el colegio',
                'action_url': '/dashboard/?pagina=gestionar_profesores',
                'priority': 3,
                'required_for': 'Asignar clases y operar académicamente'
            },
            'MISSING_STUDENT_ENROLLED': {
                'name': 'Matricular Estudiante',
                'description': 'Debes tener al menos un estudiante con matrícula activa',
                'action_url': '/dashboard/?pagina=gestionar_estudiantes',
                'priority': 4,
                'required_for': 'Operación académica y financiera'
            },
            'MISSING_CLASS_CREATED': {
                'name': 'Crear Clase',
                'description': 'Debes crear al menos una clase activa en el ciclo activo',
                'action_url': '/dashboard/?pagina=gestionar_asignaturas',
                'priority': 5,
                'required_for': 'Registro de asistencia y notas'
            },
            'COLEGIO_NOT_FOUND': {
                'name': 'Colegio no encontrado',
                'description': 'El colegio especificado no existe en el sistema',
                'action_url': '/colegios/',
                'priority': 0,
                'required_for': 'Todo'
            }
        }
        
        return step_details.get(step_code, {
            'name': 'Paso desconocido',
            'description': f'Paso {step_code} no está definido',
            'action_url': '/setup/',
            'priority': 999,
            'required_for': 'Desconocido'
        })

# Academico services module
from .attendance_service import AttendanceService
from .asistencia_service import AsistenciaService
from .grades_service import GradesService
from .calificaciones_service import CalificacionesService
from .material_clase_service import MaterialClaseService
from .planning_curricular import PlanningCurricularService

__all__ = [
	'AttendanceService',
	'AsistenciaService',
	'GradesService',
	'CalificacionesService',
	'MaterialClaseService',
	'PlanningCurricularService',
]


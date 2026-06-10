"""
FASE 6-16: Academico URLs Configuration
Academic view routing (student, teacher management, reports, student details, teacher tasks, attendance, report generation, PDF views & infrastructure)
"""

from django.urls import path
from backend.apps.academico.views.academic_views import (
    ver_mis_notas,
    ver_mi_asistencia,
    ver_mis_clases,
    ver_mis_clases_profesor,
)
from backend.apps.academico.views.academic_management_views import (
    gestionar_asistencia_profesor,
    crear_evaluacion_online_profesor,
    gestionar_evaluaciones_calificaciones,
    libro_clases,
)
from backend.apps.academico.views.academic_report_views import (
    reportes,
    exportar_reporte_pdf,
    exportar_reporte_excel,
)
from backend.apps.academico.views.student_detail_views import (
    ver_detalle_clase,
    ver_tareas_estudiante,
    calendario_tareas_estudiante,
)
from backend.apps.academico.views.teacher_task_views import (
    gestionar_tareas_profesor,
    ver_entregas_tarea,
)
from backend.apps.academico.views.attendance_views import (
    registro_asistencia_clase,
    reporte_asistencia_clase,
    mi_asistencia_estudiante,
)
from backend.apps.academico.views.pdf_report_views import (
    ver_informe_pdf,
)
from backend.apps.academico.views.infrastructure_views import (
    gestionar_infraestructura,
)

from backend.apps.academico.views.planning_api import (
    planning_api_save,
    planning_api_delete,
    planning_api_enviar,
    planning_api_revisar,
    planning_api_get_oas,
    banco_rubricas_list,
    banco_rubrica_clone,
    banco_evaluaciones_list,
    banco_evaluacion_clone,
)

app_name = 'academico'

urlpatterns = [
    # Student academic views (FASE 6)
    path('estudiante/mis-notas/', ver_mis_notas, name='ver_mis_notas'),
    path('estudiante/mi-asistencia/', ver_mi_asistencia, name='ver_mi_asistencia'),
    path('estudiante/mis-clases/', ver_mis_clases, name='ver_mis_clases'),
    
    # Teacher academic views (FASE 6)
    path('profesor/mis-clases/', ver_mis_clases_profesor, name='ver_mis_clases_profesor'),
    
    # Teacher management views (FASE 7)
    path('profesor/gestionar-asistencia/', gestionar_asistencia_profesor, name='gestionar_asistencia_profesor'),
    path('profesor/gestionar-evaluaciones/', gestionar_evaluaciones_calificaciones, name='gestionar_evaluaciones_calificaciones'),
    path('profesor/evaluaciones-online/', crear_evaluacion_online_profesor, name='crear_evaluacion_online_profesor'),
    path('profesor/libro-clases/', libro_clases, name='libro_clases'),
    
    # Reports & Export (FASE 8)
    path('reportes/', reportes, name='reportes'),
    path('reportes/exportar-pdf/', exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('reportes/exportar-excel/', exportar_reporte_excel, name='exportar_reporte_excel'),
    
    # Student detail views (FASE 9)
    path('estudiante/clase/<int:clase_id>/', ver_detalle_clase, name='ver_detalle_clase'),
    path('estudiante/tareas/', ver_tareas_estudiante, name='ver_tareas_estudiante'),
    path('estudiante/calendario-tareas/', calendario_tareas_estudiante, name='calendario_tareas_estudiante'),
    
    # Teacher task management (FASE 10)
    path('profesor/gestionar-tareas/<int:clase_id>/', gestionar_tareas_profesor, name='gestionar_tareas_profesor'),
    path('profesor/entregas-tarea/<int:tarea_id>/', ver_entregas_tarea, name='ver_entregas_tarea'),
    
    # Attendance management (FASE 11 & 12)
    path('profesor/clase/<int:clase_id>/asistencia/', registro_asistencia_clase, name='registro_asistencia_clase'),
    path('profesor/clase/<int:clase_id>/asistencia/reporte/', reporte_asistencia_clase, name='reporte_asistencia_clase'),
    path('estudiante/mi-asistencia/', mi_asistencia_estudiante, name='mi_asistencia_estudiante'),
    
    # PDF report viewing (FASE 14)
    path('informe-pdf/<int:informe_id>/', ver_informe_pdf, name='ver_informe_pdf'),
    
    # Infrastructure management (FASE 16)
    path('admin/gestionar-infraestructura/', gestionar_infraestructura, name='gestionar_infraestructura'),

    # Curricular Planning & Resources API endpoints (FASE 2.2)
    path('profesor/planificacion/save/', planning_api_save, name='planning_api_save'),
    path('profesor/planificacion/delete/', planning_api_delete, name='planning_api_delete'),
    path('profesor/planificacion/enviar/', planning_api_enviar, name='planning_api_enviar'),
    path('profesor/planificacion/revisar/', planning_api_revisar, name='planning_api_revisar'),
    path('profesor/planificacion/get-oas/', planning_api_get_oas, name='planning_api_get_oas'),
    path('profesor/banco/rubricas/', banco_rubricas_list, name='banco_rubricas_list'),
    path('profesor/banco/rubricas/clonar/', banco_rubrica_clone, name='banco_rubrica_clone'),
    path('profesor/banco/evaluaciones/', banco_evaluaciones_list, name='banco_evaluaciones_list'),
    path('profesor/banco/evaluaciones/clonar/', banco_evaluacion_clone, name='banco_evaluacion_clone'),
]


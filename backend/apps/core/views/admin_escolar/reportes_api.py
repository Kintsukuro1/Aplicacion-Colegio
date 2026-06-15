"""API endpoints para reportes — Admin Escolar.

Contiene vistas para la exportación de reportes institucionales.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime

from django.db.models import Avg
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.apps.cursos.models import Clase, Curso
from backend.common.services.policy_service import PolicyService
from backend.common.utils.view_auth import jwt_or_session_auth_required

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@jwt_or_session_auth_required
def exportar_reporte_cursos_csv(request):
    """Export academic performance details of a course to CSV.

    Validates school tenant boundaries and checks appropriate capabilities.
    """
    rbd = resolve_request_rbd(request)
    if not rbd:
        return JsonResponse({"success": False, "error": "Usuario sin colegio asignado"}, status=400)

    if not PolicyService.has_capability(request.user, "REPORT_VIEW_BASIC", school_id=rbd):
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    curso_id = request.GET.get("curso_id")
    if not curso_id:
        return JsonResponse({"success": False, "error": "curso_id es requerido"}, status=400)

    try:
        # Check course belongs to the tenant school
        curso = ORMAccessService.filter(Curso, id_curso=curso_id, colegio_id=rbd).get()
    except Curso.DoesNotExist:
        return JsonResponse({"success": False, "error": "Curso no encontrado o no pertenece a este colegio"}, status=404)

    # Fetch active classes/subjects for this course
    clases = Clase.objects.filter(
        curso=curso,
        activo=True
    ).select_related('asignatura', 'profesor')

    clases_con_promedio = clases.annotate(
        promedio=Avg('evaluaciones__calificaciones__nota')
    ).order_by('asignatura__nombre')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"reporte_curso_{curso.nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.write('\ufeff')
    writer = csv.writer(response)

    writer.writerow(['REPORTE DE RENDIMIENTO ACADÉMICO POR CURSO'])
    writer.writerow(['Colegio RBD', rbd])
    writer.writerow(['Curso', curso.nombre])
    writer.writerow(['Año Académico', curso.ciclo_academico.nombre if curso.ciclo_academico else ''])
    writer.writerow(['Fecha de generación', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
    writer.writerow([])

    writer.writerow(['Asignatura', 'Profesor a Cargo', 'Total Evaluaciones Activas', 'Promedio General del Curso'])
    for c in clases_con_promedio:
        prom = round(float(c.promedio), 2) if c.promedio is not None else 'Sin calificaciones'
        writer.writerow([
            c.asignatura.nombre,
            c.profesor.get_full_name() if c.profesor else 'Sin docente',
            c.evaluaciones.filter(activa=True).count(),
            prom
        ])

    return response

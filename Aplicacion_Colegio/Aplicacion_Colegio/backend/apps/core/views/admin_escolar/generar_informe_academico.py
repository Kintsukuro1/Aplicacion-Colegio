"""Core view: generar informe academico (Admin escolar).

Permite a administradores escolares generar informes academicos de estudiantes
en formato PDF o Excel con datos reales de calificaciones y asistencia.
"""

from __future__ import annotations

import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from backend.apps.academico.services.academic_reports_service import AcademicReportsService
from backend.apps.auditoria.services.sensitive_action_service import SensitiveActionService
from backend.apps.core.services.academic_report_query_service import AcademicReportQueryService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.common.services.policy_service import PolicyService
from backend.common.utils.report_exporters import ExcelReportExporter, PDFReportExporter

logger = logging.getLogger(__name__)


@login_required(login_url='accounts:login')
def generar_informe_academico(request, estudiante_id: int):
    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, 'Sesion invalida')
        return redirect('accounts:login')

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if rol not in ['admin', 'admin_escolar']:
        messages.error(request, 'No tienes permiso para generar informes')
        return redirect('dashboard')

    if not escuela_rbd:
        messages.error(request, 'No hay escuela asignada')
        return redirect('dashboard')

    try:
        estudiante = AcademicReportQueryService.get_student_with_profile(estudiante_id)
    except Exception:
        raise Http404('Estudiante no encontrado')

    if estudiante.rbd_colegio != escuela_rbd:
        raise Http404('Estudiante no encontrado')

    perfil = getattr(estudiante, 'perfil_estudiante', None)
    if perfil is None:
        messages.error(request, 'El estudiante no tiene perfil asociado')
        return redirect('dashboard')

    curso = perfil.curso_actual
    if curso is None:
        messages.error(request, 'El estudiante no tiene curso asignado')
        return redirect('dashboard')

    periodos = [
        ('1', '1er Semestre'),
        ('2', '2do Semestre'),
        ('anual', 'Anual'),
    ]
    anio_actual = datetime.utcnow().year
    anios = [anio_actual, anio_actual - 1, anio_actual - 2]

    if request.method == 'POST':
        if not PolicyService.authorize(request.user, 'REPORT_EXPORT', context={'school_id': escuela_rbd}):
            messages.error(request, 'No tienes permisos para exportar reportes')
            return redirect('generar_informe_academico', estudiante_id=estudiante_id)

        periodo = request.POST.get('periodo', 'anual')
        anio = request.POST.get('anio', str(anio_actual))
        formato = request.POST.get('formato', 'pdf')
        approval_request_id = request.POST.get('approval_request_id')

        payload = {
            'estudiante_id': estudiante_id,
            'periodo': str(periodo),
            'anio': str(anio),
            'formato': str(formato),
        }

        try:
            colegio = AcademicReportQueryService.get_school_by_rbd(escuela_rbd)
        except Exception:
            messages.error(request, 'Colegio no encontrado')
            return redirect('generar_informe_academico', estudiante_id=estudiante_id)

        try:
            reporte_data = AcademicReportsService.generate_student_academic_report(
                request.user,
                estudiante,
                periodo=periodo,
            )
        except Exception:
            logger.exception('Error al preparar datos de informe academico')
            messages.error(request, 'No se pudo preparar el informe. Intenta nuevamente.')
            return redirect('generar_informe_academico', estudiante_id=estudiante_id)

        if approval_request_id is None:
            request_obj = SensitiveActionService.create_request(
                action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
                requested_by=request.user,
                school_rbd=escuela_rbd,
                target_user=estudiante,
                payload=payload,
                justification='Exportacion de informe academico de estudiante.',
            )
            messages.warning(
                request,
                f'Solicitud registrada #{request_obj.id}. Un segundo usuario debe aprobar y ejecutar la exportacion.',
            )
            return redirect('generar_informe_academico', estudiante_id=estudiante_id)

        try:
            request_obj = SensitiveActionService.validate_and_approve_for_execution(
                request_id=int(approval_request_id),
                actor=request.user,
                action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
                school_rbd=escuela_rbd,
                target_user_id=estudiante.id,
                expected_payload=payload,
            )
        except Exception:
            logger.exception('Error validando solicitud de doble control para exportacion')
            messages.error(request, 'La solicitud de doble control no es valida para esta exportacion.')
            return redirect('generar_informe_academico', estudiante_id=estudiante_id)

        try:
            if formato == 'excel':
                response = ExcelReportExporter.generate_student_academic_excel(reporte_data, colegio)
            else:
                response = PDFReportExporter.generate_student_academic_pdf(reporte_data, colegio)
        except Exception as exc:
            SensitiveActionService.mark_request_failed(
                request_obj,
                actor=request.user,
                error_message=str(exc),
            )
            logger.exception('Error al generar archivo de informe academico')
            messages.error(request, 'No se pudo generar el archivo del informe.')
            return redirect('generar_informe_academico', estudiante_id=estudiante_id)

        SensitiveActionService.mark_request_executed(
            request_obj,
            actor=request.user,
            execution_result={'formato': formato, 'estudiante_id': estudiante_id},
        )
        return response

    context = {
        'estudiante': estudiante,
        'perfil': perfil,
        'curso': curso,
        'periodos': periodos,
        'anios': anios,
    }

    return render(request, 'admin_escolar/generar_informe.html', context)

"""
Vistas orchestradoras para reportes academicos.
Delegacion a AcademicReportService para generacion y exportacion.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from backend.apps.academico.services.academic_reports_service import AcademicReportsService
from backend.apps.auditoria.services.sensitive_action_service import SensitiveActionService
from backend.apps.core.views import load_dashboard_context
from backend.common.services.policy_service import PolicyService
from backend.common.utils.report_exporters import ExcelReportExporter, PDFReportExporter


def _build_export_payload(tipo_reporte: str, filtro_clase_id: str, fecha_inicio_str: str, fecha_fin_str: str, formato: str):
    return {
        'tipo': tipo_reporte,
        'clase_id': str(filtro_clase_id or ''),
        'fecha_inicio': str(fecha_inicio_str or ''),
        'fecha_fin': str(fecha_fin_str or ''),
        'formato': formato,
    }


def _require_export_capability(user, school_rbd):
    if PolicyService.authorize(user, 'REPORT_EXPORT', context={'school_id': school_rbd}):
        return None
    return JsonResponse({'error': 'Sin permisos para exportar reportes'}, status=403)


@login_required
def reportes(request):
    """Vista pasarela para reportes academicos."""
    colegio = getattr(request.user, 'colegio', None)
    if colegio is None:
        return JsonResponse({'error': 'No se pudo determinar el colegio del usuario'}, status=400)

    clases = AcademicReportsService.get_available_classes_for_reports(request.user, colegio)

    tipo_reporte = request.GET.get('tipo', 'asistencia')
    filtro_clase_id = request.GET.get('clase_id', '')
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')

    fecha_inicio, fecha_fin = AcademicReportsService.parse_report_filters(fecha_inicio_str, fecha_fin_str)
    clase_seleccionada = AcademicReportsService.get_selected_class_for_report(request.user, colegio, filtro_clase_id)

    reporte_data = AcademicReportsService.generate_report_data(
        request.user,
        clase_seleccionada,
        tipo_reporte,
        fecha_inicio,
        fecha_fin,
    )

    context = {
        **load_dashboard_context(request),
        'clases': clases,
        'clase_seleccionada': clase_seleccionada,
        'tipo_reporte': tipo_reporte,
        'filtro_clase_id': filtro_clase_id,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'reporte_data': reporte_data,
    }

    if request.GET.get('json'):
        return JsonResponse(context, safe=False)

    return render(request, 'profesor/reportes.html', context)


@login_required
def exportar_reporte_pdf(request):
    """Vista pasarela para exportar reporte a PDF con doble control."""
    colegio = getattr(request.user, 'colegio', None)
    if colegio is None:
        return JsonResponse({'error': 'No se pudo determinar el colegio del usuario'}, status=400)

    denied = _require_export_capability(request.user, colegio.rbd)
    if denied is not None:
        return denied

    tipo_reporte = request.GET.get('tipo', 'asistencia')
    filtro_clase_id = request.GET.get('clase_id', '')
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')
    approval_request_id = request.GET.get('approval_request_id')

    payload = _build_export_payload(tipo_reporte, filtro_clase_id, fecha_inicio_str, fecha_fin_str, 'pdf')

    result = AcademicReportsService.prepare_export_data(
        request.user,
        colegio,
        tipo_reporte,
        filtro_clase_id,
        fecha_inicio_str,
        fecha_fin_str,
    )
    if hasattr(result, 'status_code'):
        return result

    _clase_seleccionada, _fecha_inicio, _fecha_fin, reporte_data = result

    if approval_request_id is None:
        request_obj = SensitiveActionService.create_request(
            action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
            requested_by=request.user,
            school_rbd=colegio.rbd,
            payload=payload,
            justification='Exportacion de reporte academico (PDF).',
        )
        return JsonResponse(
            {
                'success': True,
                'requires_approval': True,
                'request_id': request_obj.id,
                'message': 'Solicitud registrada. Otro usuario debe aprobar la exportacion.',
            },
            status=202,
        )

    request_obj = SensitiveActionService.validate_and_approve_for_execution(
        request_id=int(approval_request_id),
        actor=request.user,
        action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
        school_rbd=colegio.rbd,
        expected_payload=payload,
    )

    try:
        response = PDFReportExporter.generate_student_academic_pdf(reporte_data, colegio)
    except Exception as exc:
        SensitiveActionService.mark_request_failed(
            request_obj,
            actor=request.user,
            error_message=str(exc),
        )
        return JsonResponse({'error': 'Error al generar PDF', 'details': str(exc)}, status=500)

    SensitiveActionService.mark_request_executed(
        request_obj,
        actor=request.user,
        execution_result={'formato': 'pdf'},
    )
    return response


@login_required
def exportar_reporte_excel(request):
    """Vista pasarela para exportar reporte a Excel con doble control."""
    colegio = getattr(request.user, 'colegio', None)
    if colegio is None:
        return JsonResponse({'error': 'No se pudo determinar el colegio del usuario'}, status=400)

    denied = _require_export_capability(request.user, colegio.rbd)
    if denied is not None:
        return denied

    tipo_reporte = request.GET.get('tipo', 'asistencia')
    filtro_clase_id = request.GET.get('clase_id', '')
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')
    approval_request_id = request.GET.get('approval_request_id')

    payload = _build_export_payload(tipo_reporte, filtro_clase_id, fecha_inicio_str, fecha_fin_str, 'excel')

    result = AcademicReportsService.prepare_export_data(
        request.user,
        colegio,
        tipo_reporte,
        filtro_clase_id,
        fecha_inicio_str,
        fecha_fin_str,
    )
    if hasattr(result, 'status_code'):
        return result

    _clase_seleccionada, _fecha_inicio, _fecha_fin, reporte_data = result

    if approval_request_id is None:
        request_obj = SensitiveActionService.create_request(
            action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
            requested_by=request.user,
            school_rbd=colegio.rbd,
            payload=payload,
            justification='Exportacion de reporte academico (Excel).',
        )
        return JsonResponse(
            {
                'success': True,
                'requires_approval': True,
                'request_id': request_obj.id,
                'message': 'Solicitud registrada. Otro usuario debe aprobar la exportacion.',
            },
            status=202,
        )

    request_obj = SensitiveActionService.validate_and_approve_for_execution(
        request_id=int(approval_request_id),
        actor=request.user,
        action_type=SensitiveActionService.ACTION_SENSITIVE_EXPORT,
        school_rbd=colegio.rbd,
        expected_payload=payload,
    )

    try:
        response = ExcelReportExporter.generate_student_academic_excel(reporte_data, colegio)
    except Exception as exc:
        SensitiveActionService.mark_request_failed(
            request_obj,
            actor=request.user,
            error_message=str(exc),
        )
        return JsonResponse({'error': 'Error al generar Excel', 'details': str(exc)}, status=500)

    SensitiveActionService.mark_request_executed(
        request_obj,
        actor=request.user,
        execution_result={'formato': 'excel'},
    )
    return response

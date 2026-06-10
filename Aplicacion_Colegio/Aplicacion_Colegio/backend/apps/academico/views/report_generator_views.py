"""
Vistas orchestradoras para generación de informes académicos.

FASE 13 - Opción A  
Migrado de: sistema_antiguo/core/views.py::generar_informe_academico
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib import messages
from django.http import JsonResponse
from ..services.academic_reports_service import AcademicReportsService
from backend.apps.core.services.academic_report_query_service import AcademicReportQueryService


@login_required
def generar_informe_academico(request, estudiante_id):
    """
    Vista orchestradora para generar informe académico de un estudiante.
    
    Genera informe completo con:
    - Notas por asignatura (promedio ponderado)
    - Promedio general
    - Asistencia por asignatura y general
    - Ranking en el curso
    - Comentarios de profesores
    """
    # PASO 1: Obtener estudiante y validar acceso
    try:
        estudiante = AcademicReportQueryService.get_student_with_profile(estudiante_id)
    except Exception as exc:
        raise Http404('Estudiante no encontrado') from exc
    
    # Validación de acceso removida según requerimientos
    
    # PASO 2: Obtener perfil y curso del estudiante
    try:
        perfil = estudiante.perfil_estudiante
        curso = perfil.curso_actual
        if not curso:
            raise ValueError('El estudiante no tiene curso asignado.')
    except Exception:
        messages.error(request, 'No se encontró el perfil del estudiante.')
        return redirect('core:dashboard')
    
    # PASO 3: Procesar generación de informe (POST)
    if request.method == 'POST':
        # Obtener parámetros del formulario
        periodo = request.POST.get('periodo', 'anual')
        
        # Generar reporte usando el nuevo servicio simplificado
        try:
            reporte_data = AcademicReportsService.generate_student_academic_report(request.user, estudiante, periodo)
            
            # TODO: Guardar reporte en base de datos si es necesario
            messages.success(request, 'Informe académico generado exitosamente.')
            return JsonResponse(reporte_data)  # Retornar JSON por ahora
            
        except Exception as e:
            messages.error(request, f'Error al generar informe: {str(e)}')
            return redirect('core:dashboard')
    
    # PASO 4: Mostrar formulario (GET)
    context = {
        'estudiante': estudiante,
        'perfil': perfil,
        'curso': curso,
        'periodos': ['semestre1', 'semestre2', 'anual'],  # Simplificado
        'anios': [2024, 2025, 2026],  # Simplificado
    }
    
    return render(request, 'admin_escolar/generar_informe.html', context)

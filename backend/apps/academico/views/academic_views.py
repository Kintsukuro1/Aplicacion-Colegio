"""
FASE 6: Academic Views - Student & Teacher
Extracted from sistema_antiguo/core/views.py

Lightweight orchestrators for academic visualization:
- ver_mis_notas (L2712-2802) - Student grades view
- ver_mi_asistencia (L2803-2899) - Student attendance view
- ver_mis_clases (L2900-2972) - Student classes view
- ver_mis_clases_profesor (L2973-3068) - Teacher classes view

Original: ~360 lines total | New: ~120 lines total (67% reduction)
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from backend.apps.academico.services.grades_service import GradesService
from backend.apps.academico.services.attendance_service import AttendanceService


@login_required()
def ver_mis_notas(request):
    """
    Vista pasarela para notas del estudiante.
    """
    context = GradesService.get_student_grades_summary(request.user)
    
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    
    return render(request, 'estudiante/mis_notas.html', context)


@login_required()
def ver_mi_asistencia(request):
    """
    Vista pasarela para asistencia del estudiante.
    """
    # Obtener filtros
    from datetime import date
    mes_filtro = request.GET.get('mes', date.today().month)
    anio_filtro = request.GET.get('anio', date.today().year)
    
    try:
        mes_filtro = int(mes_filtro)
        anio_filtro = int(anio_filtro)
    except (ValueError, TypeError):
        mes_filtro = date.today().month
        anio_filtro = date.today().year
    
    context = AttendanceService.get_student_attendance_summary(
        request.user, mes_filtro, anio_filtro
    )
    
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    
    return render(request, 'estudiante/mi_asistencia.html', context)


@login_required()
def ver_mis_clases(request):
    """
    Vista pasarela para clases del estudiante.
    """
    context = GradesService.get_student_classes_summary(request.user)
    
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    
    return render(request, 'estudiante/mis_clases.html', context)


@login_required()
def ver_mis_clases_profesor(request):
    """
    Vista pasarela para clases del profesor.
    """
    context = AttendanceService.get_teacher_classes_with_stats(request.user)
    
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    
    return render(request, 'profesor/mis_clases.html', context)
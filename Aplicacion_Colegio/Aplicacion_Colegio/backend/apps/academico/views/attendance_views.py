"""
Vistas para gestión de asistencia de clases.
Orchestradores ligeros que delegan lógica al AttendanceService.

FASE 11 - Opción A
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from backend.apps.academico.services import AttendanceService


@login_required()
def registro_asistencia_clase(request, clase_id):
    """
    Vista para registrar asistencia de una clase específica en una fecha.
    
    GET: Muestra formulario con lista de estudiantes y asistencias existentes
    POST: Registra/actualiza asistencia de todos los estudiantes
    """
    user = request.user
    
    # Obtener clase usando servicio
    clase = AttendanceService.get_class_for_user(user, clase_id)
    if not clase:
        messages.error(request, 'Clase no encontrada.')
        return redirect('core:dashboard')
    
    # Procesar POST (registrar asistencia)
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        
        try:
            fecha = AttendanceService.parse_date_from_string(fecha_str)
        except ValueError:
            messages.error(request, '❌ Formato de fecha inválido.')
            return redirect('registro_asistencia_clase', clase_id=clase_id)
        
        # Obtener estudiantes activos
        perfiles = AttendanceService.get_active_students(user, clase.curso)
        
        # Preparar datos de asistencia usando servicio
        attendance_data = AttendanceService.prepare_attendance_data_from_post(user, request.POST, perfiles)
        
        # Registrar asistencia
        count = AttendanceService.register_attendance_for_class(
            user, user.colegio, clase, fecha, attendance_data
        )
        
        messages.success(
            request,
            f'✓ Asistencia registrada para {fecha_str} ({count} estudiantes)'
        )
        
        return redirect('registro_asistencia_clase', clase_id=clase_id)
    
    # GET - Mostrar formulario
    fecha_param = request.GET.get('fecha', date.today().strftime('%Y-%m-%d'))
    
    try:
        fecha = AttendanceService.parse_date_from_string(fecha_param)
    except ValueError:
        fecha = date.today()
        fecha_param = fecha.strftime('%Y-%m-%d')
    
    # Obtener estudiantes con asistencia para la fecha
    estudiantes_data = AttendanceService.get_students_with_attendance(user, user.colegio, clase, fecha)
    
    context = {
        'clase': clase,
        'fecha': fecha,
        'fecha_str': fecha_param,
        'estudiantes': estudiantes_data,
        'total_estudiantes': len(estudiantes_data),
        'estados_choices': AttendanceService.ESTADOS_CHOICES,
    }
    
    return render(request, 'profesor/registro_asistencia.html', context)


@login_required()
def reporte_asistencia_clase(request, clase_id):
    """
    Vista de reporte de asistencia de una clase con estadísticas.
    Muestra estadísticas por estudiante y generales del mes seleccionado.
    
    GET: Muestra reporte con filtros de mes/año
    """
    user = request.user
    
    # Obtener clase usando servicio
    clase = AttendanceService.get_class_for_user(user, clase_id)
    if not clase:
        messages.error(request, 'Clase no encontrada.')
        return redirect('core:dashboard')
    
    # Obtener filtros
    mes_param = request.GET.get('mes', str(date.today().month))
    anio_param = request.GET.get('anio', str(date.today().year))
    
    try:
        mes = int(mes_param)
        anio = int(anio_param)
    except (ValueError, TypeError):
        mes = date.today().month
        anio = date.today().year
    
    # Validar rango de mes
    if mes < 1 or mes > 12:
        mes = date.today().month
    
    # Generar reporte
    reporte = AttendanceService.get_attendance_report(user, clase, mes, anio)
    
    # Obtener listas para selectores
    meses = AttendanceService.get_months_list()
    anios = AttendanceService.get_years_list()
    mes_nombre = AttendanceService.get_month_name(mes)
    
    context = {
        'clase': clase,
        'estudiantes_stats': reporte['estudiantes_stats'],
        'stats_generales': reporte['stats_generales'],
        'mes': mes,
        'anio': anio,
        'meses': meses,
        'anios': anios,
        'mes_nombre': mes_nombre,
    }
    
    return render(request, 'profesor/reporte_asistencia.html', context)


@login_required
def mi_asistencia_estudiante(request):
    """
    Vista orchestradora para que el estudiante vea su propia asistencia.
    
    Muestra:
    - Registros de asistencia del mes seleccionado
    - Estadísticas generales (total, presentes, ausentes, etc.)
    - Estadísticas por asignatura
    - Filtros por mes/año
    """
    # Obtener perfil y curso usando servicio
    perfil, curso_actual = AttendanceService.get_student_profile_and_course(request.user)
    if not perfil or not curso_actual:
        messages.error(request, 'No tienes un curso asignado actualmente.')
        return redirect('core:dashboard')
    
    # Obtener parámetros de filtro
    from datetime import date
    hoy = date.today()
    
    mes = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))
    
    # Obtener asistencias y estadísticas generales del mes
    attendance_data = AttendanceService.get_student_attendance_for_month(
        request.user, perfil, mes, anio
    )
    
    # Obtener estadísticas por asignatura
    asignaturas_stats = AttendanceService.get_student_attendance_by_subject(
        request.user, perfil, mes, anio
    )
    
    # Preparar contexto para el template
    context = {
        'perfil': perfil,
        'asistencias': attendance_data['asistencias'],
        'total': attendance_data['total'],
        'presentes': attendance_data['presentes'],
        'ausentes': attendance_data['ausentes'],
        'tardanzas': attendance_data['tardanzas'],
        'justificadas': attendance_data['justificadas'],
        'porcentaje_asistencia': attendance_data['porcentaje_asistencia'],
        'asignaturas_stats': asignaturas_stats,
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'meses': AttendanceService.get_months_list(),
        'anios': AttendanceService.get_years_list(),
        'mes_nombre': AttendanceService.get_month_name(mes),
    }
    
    return render(request, 'academico/estudiante/mi_asistencia.html', context)


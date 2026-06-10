"""
Vistas pasarela para gestión académica.
Delegación completa a servicios especializados.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from datetime import date, datetime

from backend.apps.academico.services.attendance_service import AttendanceService
from backend.apps.academico.services.grades_service import GradesService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.views import load_dashboard_context


@login_required
def gestionar_asistencia_profesor(request):
    """Vista pasarela para gestión de asistencia."""
    colegio = getattr(request.user, "colegio", None)
    if colegio is None:
        messages.error(request, "No se pudo determinar el colegio del usuario.")
        return redirect("dashboard")
    
    # Procesar POST - delegar a servicio
    if request.method == 'POST':
        result = AttendanceService.process_attendance_action(request.user, colegio, request.POST)
        if result['success']:
            messages.success(request, result['message'])
        else:
            messages.error(request, result['message'])
        return redirect(f"{reverse('dashboard')}?pagina=asistencia")
    
    # GET - obtener datos del servicio
    classes_data = AttendanceService.get_teacher_classes_data(request.user)
    
    # Aplicar filtros
    filtro_clase_id = request.GET.get('clase_id', '')
    filtro_fecha = request.GET.get('fecha', '')
    
    # Selección automática si no hay filtro
    clases = classes_data['clases']
    if not filtro_clase_id and clases.exists():
        filtro_clase_id = str(clases.first().id)
    if not filtro_fecha:
        filtro_fecha = date.today().strftime('%Y-%m-%d')
    
    # Obtener datos de clase seleccionada
    estudiantes_con_asistencia = []
    stats_clase = {}
    
    if filtro_clase_id:
        try:
            clase = clases.get(id=filtro_clase_id)
            fecha_obj = datetime.strptime(filtro_fecha, '%Y-%m-%d').date()
            
            estudiantes_con_asistencia = AttendanceService.get_students_with_attendance(
                request.user, colegio, clase, fecha_obj
            )
            
            stats_clase = AttendanceService.calculate_class_attendance_stats(
                request.user, clase, days=30
            )
        except Exception as e:
            messages.error(request, f'Error al cargar datos: {str(e)}')
    
    context = {
        **load_dashboard_context(request),
        'clases': clases,
        'total_clases': classes_data['total_clases'],
        'clase_seleccionada': clase if 'clase' in locals() else None,
        'estudiantes_con_asistencia': estudiantes_con_asistencia,
        'filtro_clase_id': filtro_clase_id,
        'filtro_fecha': filtro_fecha,
        'stats_clase': stats_clase,
        'fecha_hoy': date.today().strftime('%Y-%m-%d'),
    }
    
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    
    return render(request, 'profesor/gestionar_asistencia.html', context)


@login_required
def gestionar_evaluaciones_calificaciones(request):
    """Vista pasarela para gestión de evaluaciones y calificaciones."""
    colegio = getattr(request.user, "colegio", None)
    if colegio is None:
        messages.error(request, "No se pudo determinar el colegio del usuario.")
        return redirect("dashboard")
    
    # Procesar POST - delegar a servicio
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion in ['crear_evaluacion', 'editar_evaluacion', 'eliminar_evaluacion']:
            result = GradesService.process_evaluation_action(request.user, colegio, request.POST, request.FILES)
        elif accion == 'registrar_calificaciones':
            result = GradesService.process_grades_registration(request.user, colegio, request.POST)
        else:
            result = {'success': False, 'message': 'Acción no válida'}
            
        if result['success']:
            messages.success(request, result['message'])
        else:
            messages.error(request, result['message'])
        
        return redirect(f"{reverse('dashboard')}?pagina=notas")
    
    # GET - obtener datos del servicio
    clases = GradesService.get_teacher_classes_for_grades(request.user, colegio)
    total_clases = clases.count()
    
    # Filtros
    filtro_clase_id = request.GET.get('clase_id', '')
    modo = request.GET.get('modo', 'evaluaciones')
    
    # Datos por defecto
    clase_seleccionada = None
    evaluaciones = []
    evaluacion_seleccionada = None
    estudiantes_con_notas = []
    stats = {'total_evaluaciones': 0, 'total_calificaciones': 0, 'promedio_general': 0}
    
    if filtro_clase_id:
        try:
            clase_seleccionada = clases.get(id=filtro_clase_id)
            evaluaciones = GradesService.get_evaluations_for_class(clase_seleccionada)
            
            # Si está en modo calificar
            if modo == 'calificar':
                evaluacion_id = request.GET.get('evaluacion_id')
                if evaluacion_id:
                    evaluacion_seleccionada = GradesService.get_evaluation_by_id(
                        colegio, int(evaluacion_id)
                    )
                    if evaluacion_seleccionada:
                        estudiantes_con_notas = GradesService.get_students_with_grades(
                            colegio, evaluacion_seleccionada
                        )
            
            # Calcular estadísticas
            stats = GradesService.calculate_class_grades_stats(clase_seleccionada)
        
        except Exception as e:
            messages.error(request, f'Error al cargar datos: {str(e)}')
    
    context = {
        **load_dashboard_context(request),
        'clases': clases,
        'total_clases': total_clases,
        'clase_seleccionada': clase_seleccionada,
        'evaluaciones': evaluaciones,
        'total_evaluaciones': stats['total_evaluaciones'],
        'total_calificaciones': stats['total_calificaciones'],
        'promedio_general': stats['promedio_general'],
        'filtro_clase_id': filtro_clase_id,
        'modo': modo,
        'evaluacion_seleccionada': evaluacion_seleccionada,
        'estudiantes_con_notas': estudiantes_con_notas,
        'fecha_hoy': date.today().strftime('%Y-%m-%d'),
    }
    
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    
    return render(request, 'profesor/gestionar_evaluaciones_calificaciones.html', context)


@login_required
def crear_evaluacion_online_profesor(request):
    """Vista de creación y edición de evaluación online."""
    colegio = getattr(request.user, "colegio", None)
    if colegio is None:
        messages.error(request, "No se pudo determinar el colegio del usuario.")
        return redirect("dashboard")

    clases = GradesService.get_teacher_classes_for_grades(request.user, colegio)
    filtro_clase_id = request.GET.get('clase_id', '')
    evaluacion_id = request.GET.get('evaluacion_id', '')
    clase_seleccionada = None
    evaluacion_seleccionada = None
    actividad_principal = None

    if evaluacion_id:
        try:
            evaluacion_seleccionada = GradesService.get_evaluation_by_id(colegio, int(evaluacion_id))
        except (TypeError, ValueError):
            evaluacion_seleccionada = None

    if evaluacion_seleccionada and not filtro_clase_id:
        filtro_clase_id = str(evaluacion_seleccionada.clase_id)

    if not filtro_clase_id and clases.exists():
        filtro_clase_id = str(clases.first().id)

    if filtro_clase_id:
        try:
            clase_seleccionada = clases.get(id=filtro_clase_id)
        except Exception:
            clase_seleccionada = None

    if evaluacion_seleccionada:
        actividad_principal = GradesService._get_primary_activity(evaluacion_seleccionada)
        if clase_seleccionada is None:
            clase_seleccionada = evaluacion_seleccionada.clase

    preguntas_formulario = []
    if actividad_principal is not None:
        preguntas_queryset = actividad_principal.preguntas.all().order_by('orden', 'id_pregunta')
        for pregunta in preguntas_queryset[:4]:
            opciones = [
                {
                    'texto': opcion.texto,
                    'es_correcta': opcion.es_correcta,
                }
                for opcion in pregunta.opciones.all().order_by('orden', 'id_opcion')
            ]
            preguntas_formulario.append({
                'enunciado': pregunta.enunciado,
                'tipo': pregunta.tipo,
                'puntaje': pregunta.puntaje,
                'respuesta_correcta': pregunta.respuesta_correcta,
                'requiere_revision_docente': pregunta.requiere_revision_docente,
                'opciones': opciones,
            })

    while len(preguntas_formulario) < 4:
        preguntas_formulario.append({
            'enunciado': '',
            'tipo': 'opcion_multiple',
            'puntaje': 1,
            'respuesta_correcta': '',
            'requiere_revision_docente': False,
            'opciones': [
                {'texto': '', 'es_correcta': False},
                {'texto': '', 'es_correcta': False},
                {'texto': '', 'es_correcta': False},
                {'texto': '', 'es_correcta': False},
            ],
        })

    base_context = load_dashboard_context(request)
    rol_contexto = base_context.get('rol') or getattr(getattr(request.user, 'role', None), 'nombre', 'profesor')

    context = {
        **base_context,
        'clases': clases,
        'total_clases': clases.count(),
        'clase_seleccionada': clase_seleccionada,
        'evaluacion_seleccionada': evaluacion_seleccionada,
        'actividad_principal': actividad_principal,
        'preguntas_formulario': preguntas_formulario,
        'filtro_clase_id': filtro_clase_id,
        'modo_formulario': 'editar' if evaluacion_seleccionada else 'crear',
        'fecha_hoy': date.today().strftime('%Y-%m-%d'),
        'sidebar_template': DashboardService.get_sidebar_template(rol_contexto),
        'hide_top_navbar': True,
    }

    if request.GET.get('json'):
        return JsonResponse(context, safe=False)

    return render(request, 'academico/profesor/crear_evaluacion_online.html', context)


@login_required
def libro_clases(request):
    """Vista pasarela para libro de clases."""
    colegio = getattr(request.user, "colegio", None)
    if colegio is None:
        messages.error(request, "No se pudo determinar el colegio del usuario.")
        return redirect("dashboard")
    
    # Obtener clases disponibles
    clases = GradesService.get_teacher_classes_for_gradebook(request.user, colegio)
    total_clases = clases.count()
    
    # Filtros
    filtro_clase_id = request.GET.get('clase_id', '')
    clase_seleccionada = None
    gradebook_data = None
    
    if filtro_clase_id:
        try:
            from backend.apps.cursos.models import Clase
            clase_id = int(filtro_clase_id)
            clase_seleccionada = clases.filter(id=clase_id).first()
            
            if clase_seleccionada:
                gradebook_data = GradesService.build_gradebook_matrix(
                    colegio, clase_seleccionada
                )
        
        except (ValueError, TypeError) as e:
            messages.error(request, f'Error al cargar libro de clases: {str(e)}')
    
    context = {
        **load_dashboard_context(request),
        'clases': clases,
        'total_clases': total_clases,
        'clase_seleccionada': clase_seleccionada,
        'filtro_clase_id': filtro_clase_id,
    }
    
    if gradebook_data:
        context.update({
            'evaluaciones': gradebook_data['evaluaciones'],
            'matriz_calificaciones': gradebook_data['matriz_calificaciones'],
            'promedios_evaluaciones': gradebook_data['promedios_evaluaciones'],
            'total_evaluaciones': gradebook_data['total_evaluaciones'],
            'total_estudiantes': gradebook_data['total_estudiantes'],
            'promedio_general': gradebook_data['promedio_general'],
        })
    
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    
    return render(request, 'profesor/libro_clases.html', context)

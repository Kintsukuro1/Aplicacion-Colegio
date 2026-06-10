from datetime import date, datetime
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from backend.apps.academico.services.attendance_service import AttendanceService
from backend.apps.cursos.models import Clase
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.common.services.policy_service import PolicyService


def gestionar_asistencia(request, colegio, admin_mode=False):
    """
    Maneja GET y POST para la página de asistencia de profesores.
    - GET: Devuelve el contexto para renderizar la página.
    - POST: Procesa el formulario y redirige.
    """
    if request.method == 'POST':
        # Procesar POST
        accion = request.POST.get('accion')
        
        if accion == 'registrar_asistencia':
            try:
                clase = ORMAccessService.get(Clase, id=request.POST.get('clase_id'), colegio=colegio)
                fecha = datetime.strptime(request.POST.get('fecha'), '%Y-%m-%d').date()
                
                # Extraer estados de asistencia del POST
                estudiantes_estados = {}
                for key in request.POST.keys():
                    if key.startswith('estado_'):
                        estudiante_id = key.split('_')[1]
                        estado = request.POST.get(key)
                        if estado:
                            estudiantes_estados[int(estudiante_id)] = estado
                
                count = AttendanceService.register_attendance_for_class(
                    request.user, colegio, clase, fecha, estudiantes_estados
                )
                messages.success(request, f'Asistencia registrada para {count} estudiantes.')
            except Exception:
                logger = __import__('logging').getLogger(__name__)
                logger.exception('Error al registrar asistencia')
                messages.error(request, 'No se pudo registrar la asistencia. Intenta nuevamente.')
        
        elif accion == 'actualizar_observacion':
            try:
                asistencia_id = request.POST.get('asistencia_id')
                observaciones = request.POST.get('observaciones', '')
                AttendanceService.update_attendance_observation(request.user, colegio, int(asistencia_id), observaciones)
                messages.success(request, 'Observación actualizada.')
            except Exception:
                logger = __import__('logging').getLogger(__name__)
                logger.exception('Error al actualizar observación de asistencia')
                messages.error(request, 'No se pudo actualizar la observación. Intenta nuevamente.')
        
        return redirect(f"{reverse('dashboard')}?pagina=asistencia")
    
    else:
        # Procesar GET - Devolver contexto
        if admin_mode:
            # Admin can see all classes
            clases = ORMAccessService.filter(Clase, colegio=colegio, activo=True).select_related('asignatura', 'curso', 'profesor')
        else:
            # Teacher can see their own classes
            clases = ORMAccessService.filter(
                Clase,
                profesor=request.user,
                colegio=colegio,
                activo=True
            ).select_related('asignatura', 'curso', 'profesor')
        total_clases = clases.count()
        
        # Filtros (con memoria de sesión para reducir clics)
        filtro_clase_id = request.GET.get('clase_id')
        filtro_fecha = request.GET.get('fecha')
        
        if not filtro_clase_id:
            filtro_clase_id = request.session.get('last_attendance_clase_id', '')
            if not filtro_clase_id or not clases.filter(id=filtro_clase_id).exists():
                if clases.exists():
                    filtro_clase_id = str(clases.first().id)
                else:
                    filtro_clase_id = ''
        
        if not filtro_fecha:
            filtro_fecha = request.session.get('last_attendance_fecha', date.today().strftime('%Y-%m-%d'))
            
        # Guardar en sesión para la próxima visita
        if filtro_clase_id:
            request.session['last_attendance_clase_id'] = filtro_clase_id
        if filtro_fecha:
            request.session['last_attendance_fecha'] = filtro_fecha
        
        estudiantes_con_asistencia = []
        clase_seleccionada = None
        stats_clase = {}
        
        if filtro_clase_id:
            try:
                clase_seleccionada = ORMAccessService.get(Clase, id=filtro_clase_id, colegio=colegio)
                fecha_obj = datetime.strptime(filtro_fecha, '%Y-%m-%d').date()
                
                estudiantes_con_asistencia = AttendanceService.get_students_with_attendance(
                    request.user, colegio, clase_seleccionada, fecha_obj
                )
                
                stats_clase = AttendanceService.calculate_class_attendance_stats(
                    request.user, clase_seleccionada, days=30
                )
            except Exception:
                logger = __import__('logging').getLogger(__name__)
                logger.exception('Error al cargar datos de asistencia')
                messages.error(request, 'No se pudieron cargar los datos de asistencia.')
        
        context = {
            'clases': clases,
            'total_clases': total_clases,
            'clase_seleccionada': clase_seleccionada,
            'estudiantes_con_asistencia': estudiantes_con_asistencia,
            'filtro_clase_id': filtro_clase_id,
            'filtro_fecha': filtro_fecha,
            'stats_clase': stats_clase,
            'fecha_hoy': date.today().strftime('%Y-%m-%d'),
        }
        return context


def _resolve_sidebar_and_role(user):
    if PolicyService.has_capability(user, 'SYSTEM_ADMIN'):
        return 'sidebars/sidebar_admin.html', 'admin_general'
    if PolicyService.has_capability(user, 'SYSTEM_CONFIGURE'):
        return 'sidebars/sidebar_admin_escuela.html', 'admin_escolar'
    if PolicyService.has_capability(user, 'CLASS_VIEW') and (
        PolicyService.has_capability(user, 'CLASS_EDIT')
        or PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE')
    ):
        return 'sidebars/sidebar_profesor.html', 'profesor'
    return 'sidebars/sidebar_profesor.html', 'profesor'


def registro_asistencia_clase(request, clase_id):
    """Vista para registrar asistencia de una clase."""
    from django.shortcuts import render
    from django.contrib.auth.decorators import login_required

    try:
        clase = ORMAccessService.get(Clase, id=clase_id)  # Fix: Clase.pk es id, no id_curso (Curso).
    except Exception:
        messages.error(request, 'Clase no encontrada.')
        return redirect('dashboard')
    
    # Verificar que es profesor de esta clase
    if request.user.id != clase.profesor_id:
        messages.error(request, 'No tienes permiso para registrar asistencia de esta clase.')
        return redirect('dashboard')
    
    sidebar_template, rol_nombre = _resolve_sidebar_and_role(request.user)
    navigation_access = DashboardService.get_navigation_access(
        rol_nombre,
        user=request.user,
        school_id=request.user.rbd_colegio,
    )
    
    context = {
        'clase': clase,
        'sidebar_template': sidebar_template,
        'content_template': '',
        'rol': rol_nombre,
        'nombre_usuario': request.user.get_full_name(),
        'id_usuario': request.user.id,
        'escuela_rbd': request.user.rbd_colegio,
        'escuela_nombre': request.user.colegio.nombre if hasattr(request.user, 'colegio') and request.user.colegio else 'Sistema',
        'year': datetime.now().year,
        'pagina_actual': 'mis_clases',
        **navigation_access,
    }
    
    return render(request, 'profesor/registro_asistencia.html', context)


def reporte_asistencia_clase(request, clase_id):
    """Vista para ver reportes de asistencia de una clase."""
    from django.shortcuts import render
    from django.contrib.auth.decorators import login_required

    try:
        clase = ORMAccessService.get(Clase, id=clase_id)  # Fix: Clase.pk es id, no id_curso (Curso).
    except Exception:
        messages.error(request, 'Clase no encontrada.')
        return redirect('dashboard')
    
    # Verificar que es profesor de esta clase
    if request.user.id != clase.profesor_id:
        messages.error(request, 'No tienes permiso para ver reportes de asistencia de esta clase.')
        return redirect('dashboard')
    
    # Obtener estadísticas de asistencia
    from backend.apps.academico.models import Asistencia, ClaseEstudiante
    from django.db.models import Count, Q
    
    estudiantes = ORMAccessService.filter(ClaseEstudiante, clase=clase).select_related('estudiante')
    
    reporte_data = []
    for ce in estudiantes:
        asistencias = ORMAccessService.filter(Asistencia, clase=clase, estudiante=ce.estudiante)
        total = asistencias.count()
        presentes = asistencias.filter(estado='P').count()
        ausentes = asistencias.filter(estado='A').count()
        justificados = asistencias.filter(estado='J').count()
        atrasados = asistencias.filter(estado='T').count()
        
        porcentaje = (presentes / total * 100) if total > 0 else 0
        
        reporte_data.append({
            'estudiante': ce.estudiante,
            'total': total,
            'presentes': presentes,
            'ausentes': ausentes,
            'justificados': justificados,
            'atrasados': atrasados,
            'porcentaje': round(porcentaje, 1)
        })
    
    sidebar_template, rol_nombre = _resolve_sidebar_and_role(request.user)
    navigation_access = DashboardService.get_navigation_access(
        rol_nombre,
        user=request.user,
        school_id=request.user.rbd_colegio,
    )
    
    context = {
        'clase': clase,
        'reporte_data': reporte_data,
        'sidebar_template': sidebar_template,
        'content_template': '',
        'rol': rol_nombre,
        'nombre_usuario': request.user.get_full_name(),
        'id_usuario': request.user.id,
        'escuela_rbd': request.user.rbd_colegio,
        'escuela_nombre': request.user.colegio.nombre if hasattr(request.user, 'colegio') and request.user.colegio else 'Sistema',
        'year': datetime.now().year,
        'pagina_actual': 'mis_clases',
        **navigation_access,
    }
    
    return render(request, 'profesor/reporte_asistencia.html', context)
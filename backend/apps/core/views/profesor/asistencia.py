from datetime import date, datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse
from backend.apps.academico.services.attendance_service import AttendanceService
from backend.apps.cursos.models import Clase
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.common.services.policy_service import PolicyService
from backend.common.exceptions import PrerequisiteException
from backend.apps.core.services.demo_visual_service import (
    build_demo_asistencia_estudiantes,
    demo_visual_enabled,
    use_demo_when_empty,
)


def _redirect_registro_asistencia(clase_id, fecha=None, vista_previa=False):
    url = reverse('registro_asistencia_clase', kwargs={'clase_id': clase_id})
    params = []
    if fecha:
        params.append(f'fecha={fecha.strftime("%Y-%m-%d")}')
    if vista_previa:
        params.append('vista_previa=1')
    if params:
        url = f'{url}?{"&".join(params)}'
    return redirect(url)


def _asistencia_resumen_dia(estudiantes_data):
    presentes = ausentes = 0
    for item in estudiantes_data:
        estado = item.get('estado', 'P')
        if estado == 'P':
            presentes += 1
        elif estado == 'A':
            ausentes += 1
    return presentes, ausentes


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
        
        clase_id = request.POST.get('clase_id') or request.session.get('last_attendance_clase_id', '')
        fecha = request.POST.get('fecha') or request.session.get('last_attendance_fecha', '')
        curso_id = request.POST.get('curso_id') or request.GET.get('curso_id')
        url = f"{reverse('dashboard')}?pagina=asistencia"
        if curso_id:
            url += f"&curso_id={curso_id}"
        if clase_id:
            url += f"&clase_id={clase_id}"
        if fecha:
            url += f"&fecha={fecha}"
        return redirect(url)
    
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
        clases_base = clases
        total_clases_escuela = clases_base.count()

        # --- Resolver filtros (GET explícito > sesión) ---
        get_params = request.GET

        if get_params.get('reset_filtros') == '1':
            request.session.pop('last_attendance_clase_id', None)
            request.session.pop('last_attendance_curso_id', None)

        filtro_fecha = get_params.get('fecha')

        if admin_mode:
            if 'curso_id' in get_params:
                filtro_curso_id = get_params.get('curso_id', '').strip()
            elif get_params.get('reset_filtros') == '1':
                filtro_curso_id = ''
            else:
                filtro_curso_id = request.session.get('last_attendance_curso_id', '').strip()
        else:
            filtro_curso_id = ''

        if 'clase_id' in get_params:
            filtro_clase_id = get_params.get('clase_id', '').strip()
        elif get_params.get('reset_filtros') == '1':
            filtro_clase_id = ''
        elif admin_mode and 'curso_id' in get_params and filtro_curso_id:
            filtro_clase_id = ''
        else:
            filtro_clase_id = request.session.get('last_attendance_clase_id', '').strip()

        curso_seleccionado = None
        if admin_mode and filtro_curso_id:
            from backend.apps.cursos.models import Curso
            try:
                curso_seleccionado = ORMAccessService.get(Curso, id_curso=filtro_curso_id, colegio=colegio)
                clases = clases_base.filter(curso_id=filtro_curso_id)
            except Exception:
                filtro_curso_id = ''
                curso_seleccionado = None
                clases = clases_base
        else:
            clases = clases_base

        total_clases = clases.count()

        if filtro_clase_id and not clases.filter(id=filtro_clase_id).exists():
            filtro_clase_id = ''

        if filtro_clase_id and not filtro_curso_id and admin_mode:
            try:
                clase_tmp = ORMAccessService.get(Clase, id=filtro_clase_id, colegio=colegio)
                filtro_curso_id = str(clase_tmp.curso_id)
                curso_seleccionado = clase_tmp.curso
                clases = clases_base.filter(curso_id=filtro_curso_id)
                total_clases = clases.count()
            except Exception:
                pass

        if not filtro_clase_id and clases.exists() and not admin_mode:
            filtro_clase_id = str(clases.first().id)
        
        if not filtro_fecha:
            filtro_fecha = request.session.get('last_attendance_fecha', date.today().strftime('%Y-%m-%d'))
            
        # Guardar en sesión para la próxima visita
        if admin_mode:
            if filtro_curso_id:
                request.session['last_attendance_curso_id'] = filtro_curso_id
            elif 'curso_id' in get_params:
                request.session.pop('last_attendance_curso_id', None)
        if filtro_clase_id:
            request.session['last_attendance_clase_id'] = filtro_clase_id
        elif 'clase_id' in get_params:
            request.session.pop('last_attendance_clase_id', None)
        if filtro_fecha:
            request.session['last_attendance_fecha'] = filtro_fecha
        
        estudiantes_con_asistencia = []
        clase_seleccionada = None
        stats_clase = {}
        registro_dia = {}
        filtro_fecha_display = filtro_fecha or ''

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

                registro_dia = {
                    'total': len(estudiantes_con_asistencia),
                    'presentes': sum(1 for e in estudiantes_con_asistencia if e.get('estado') == 'P'),
                    'ausentes': sum(1 for e in estudiantes_con_asistencia if e.get('estado') == 'A'),
                    'tardanzas': sum(1 for e in estudiantes_con_asistencia if e.get('estado') == 'T'),
                    'justificadas': sum(1 for e in estudiantes_con_asistencia if e.get('estado') == 'J'),
                    'guardado': any(e.get('asistencia') for e in estudiantes_con_asistencia),
                }
                try:
                    filtro_fecha_display = datetime.strptime(filtro_fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    filtro_fecha_display = filtro_fecha
            except Exception:
                logger = __import__('logging').getLogger(__name__)
                logger.exception('Error al cargar datos de asistencia')
                messages.error(request, 'No se pudieron cargar los datos de asistencia.')
        elif admin_mode and curso_seleccionado:
            stats_clase = AttendanceService.calculate_course_attendance_stats(
                colegio, curso_seleccionado, days=30
            )

        stats_chart = {
            'presentes': stats_clase.get('presentes', 0) if stats_clase else 0,
            'ausentes': stats_clase.get('ausentes', 0) if stats_clase else 0,
            'tardanzas': stats_clase.get('tardanzas', 0) if stats_clase else 0,
            'justificadas': stats_clase.get('justificadas', 0) if stats_clase else 0,
            'total_registros': stats_clase.get('total_registros', 0) if stats_clase else 0,
            'porcentaje_asistencia': stats_clase.get('porcentaje_asistencia', 0) if stats_clase else 0,
            'scope': stats_clase.get('scope', ''),
            'scope_label': stats_clase.get('scope_label', ''),
        }
        stats_chart['chart_key'] = (
            f"{stats_chart['scope']}-{stats_chart['scope_label']}-"
            f"{stats_chart['presentes']}-{stats_chart['ausentes']}-"
            f"{stats_chart['tardanzas']}-{stats_chart['justificadas']}"
        )

        asistencia_hero_m1 = total_clases
        asistencia_hero_m1_label = 'Clases'
        if admin_mode and clase_seleccionada:
            asistencia_hero_m1 = len(estudiantes_con_asistencia)
            asistencia_hero_m1_label = 'Estudiantes hoy'
        elif admin_mode and curso_seleccionado:
            asistencia_hero_m1 = total_clases
            asistencia_hero_m1_label = 'Asignaturas'
        elif admin_mode:
            asistencia_hero_m1 = total_clases_escuela
            asistencia_hero_m1_label = 'Clases activas'
        
        context = {
            'clases': clases,
            'clases_todas': clases_base,
            'total_clases': total_clases,
            'total_clases_escuela': total_clases_escuela,
            'clase_seleccionada': clase_seleccionada,
            'curso_seleccionado': curso_seleccionado,
            'estudiantes_con_asistencia': estudiantes_con_asistencia,
            'filtro_clase_id': filtro_clase_id,
            'filtro_curso_id': filtro_curso_id,
            'filtro_fecha': filtro_fecha,
            'stats_clase': stats_clase,
            'stats_chart': stats_chart,
            'asistencia_hero_m1': asistencia_hero_m1,
            'asistencia_hero_m1_label': asistencia_hero_m1_label,
            'registro_dia': registro_dia,
            'filtro_fecha_display': filtro_fecha_display,
            'fecha_hoy': date.today().strftime('%Y-%m-%d'),
            'admin_mode': admin_mode,
        }
        if admin_mode:
            from backend.apps.cursos.models import Curso
            context['cursos_asistencia'] = (
                Curso.objects.filter(colegio=colegio, activo=True)
                .select_related('nivel')
                .order_by('nivel__nombre', 'nombre')
            )
            insights_asistencia = []
            if total_clases == 0 and not curso_seleccionado:
                insights_asistencia.append({
                    'tipo': 'warn',
                    'texto': 'No hay clases activas configuradas. Cree cursos y asignaturas antes de registrar asistencia.',
                })
            elif not filtro_clase_id and not curso_seleccionado:
                insights_asistencia.append({
                    'tipo': 'info',
                    'texto': 'Seleccione un curso o una clase y fecha para cargar el listado de estudiantes.',
                })
            elif curso_seleccionado and not filtro_clase_id and stats_clase.get('total_registros'):
                insights_asistencia.append({
                    'tipo': 'info',
                    'texto': (
                        f'Vista agregada del curso {curso_seleccionado.nombre} (últimos 30 días). '
                        'Elija una asignatura para registrar la asistencia del día.'
                    ),
                })
            elif stats_clase.get('total_registros') and stats_clase.get('porcentaje_asistencia', 100) < 85 and clase_seleccionada:
                insights_asistencia.append({
                    'tipo': 'warn',
                    'texto': (
                        f'Asistencia en los últimos 30 días en {clase_seleccionada.asignatura.nombre} '
                        f'({clase_seleccionada.curso.nombre}): '
                        f'{stats_clase.get("porcentaje_asistencia")}% — revise ausencias recurrentes.'
                    ),
                })
            context['insights_asistencia'] = insights_asistencia
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


@login_required
def registro_asistencia_clase(request, clase_id):
    """Registro de asistencia por clase (lista de estudiantes + guardar por fecha)."""
    clase = AttendanceService.get_class_for_user(request.user, clase_id)
    if not clase:
        messages.error(request, 'Clase no encontrada.')
        return redirect('dashboard')

    if request.user.id != clase.profesor_id:
        messages.error(request, 'No tienes permiso para registrar asistencia de esta clase.')
        return redirect('dashboard')

    colegio = request.user.colegio

    vista_previa = demo_visual_enabled(request)

    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        # En POST, determinamos si es una vista previa real (sin persistencia):
        # 1. Si viene el campo oculto vista_previa=1 en el POST.
        # 2. O bien, si no se envió la asistencia de ningún estudiante real (con ID positivo).
        has_real_submissions = any(
            key.startswith('estado_') and key.split('_', 1)[1].isdigit()
            for key in request.POST
        )
        vista_previa = request.POST.get('vista_previa') == '1' or not has_real_submissions
        try:
            fecha = AttendanceService.parse_date_from_string(fecha_str)
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return _redirect_registro_asistencia(clase.id, vista_previa=vista_previa)

        if vista_previa:
            messages.info(
                request,
                'Vista previa: los cambios no se guardan en la base de datos. '
                'Inscribe alumnos en la clase para registrar asistencia real.',
            )
            return _redirect_registro_asistencia(clase.id, fecha, vista_previa=True)

        estados = {}
        for key in request.POST:
            if key.startswith('estado_'):
                estudiante_id = key.split('_', 1)[1]
                if str(estudiante_id).isdigit():
                    estados[int(estudiante_id)] = request.POST.get(key)

        if not estados:
            messages.error(request, 'Seleccione el estado de al menos un estudiante.')
            return _redirect_registro_asistencia(clase.id, fecha)

        try:
            count = AttendanceService.register_attendance_for_class(
                request.user, colegio, clase, fecha, estados
            )
        except PrerequisiteException as exc:
            ctx = getattr(exc, 'context', None) or {}
            messages.error(
                request,
                ctx.get('message', 'No se pudo registrar la asistencia.'),
            )
            return _redirect_registro_asistencia(clase.id, fecha)

        if count == 0:
            messages.warning(
                request,
                'No se guardó ningún registro. Verifique que los estudiantes pertenezcan al ciclo de la clase.',
            )
        else:
            messages.success(
                request,
                f'Asistencia guardada correctamente ({count} estudiante{"s" if count != 1 else ""}).',
            )
        return _redirect_registro_asistencia(clase.id, fecha)

    fecha_param = request.GET.get('fecha', date.today().strftime('%Y-%m-%d'))
    try:
        fecha = AttendanceService.parse_date_from_string(fecha_param)
    except ValueError:
        fecha = date.today()
        fecha_param = fecha.strftime('%Y-%m-%d')

    estudiantes_data = AttendanceService.get_students_with_attendance(
        request.user, colegio, clase, fecha
    )
    vista_previa = use_demo_when_empty(request, bool(estudiantes_data))
    if vista_previa:
        estudiantes_data = build_demo_asistencia_estudiantes(clase)
    resumen_presentes, resumen_ausentes = _asistencia_resumen_dia(estudiantes_data)

    _, rol_nombre = _resolve_sidebar_and_role(request.user)
    navigation_access = DashboardService.get_navigation_access(
        rol_nombre,
        user=request.user,
        school_id=request.user.rbd_colegio,
    )

    from backend.apps.core.services.profesor_hero_service import ProfesorHeroService

    ra_ctx = {
        'clase': clase,
        'pagina_hero': 'registro_asistencia',
        'hero_sub_clase': f"{clase.curso.nombre} · {clase.asignatura.nombre}",
        'total_estudiantes': len(estudiantes_data),
        'resumen_presentes': resumen_presentes,
        'resumen_ausentes': resumen_ausentes,
        'resumen_fecha': fecha.strftime('%d/%m/%Y'),
    }
    return render(
        request,
        'profesor/registro_asistencia.html',
        {
            'prof_hero': ProfesorHeroService.for_clase_page(clase, ra_ctx),
            'clase': clase,
            'fecha': fecha,
            'fecha_str': fecha_param,
            'fecha_hoy': date.today().strftime('%Y-%m-%d'),
            'estudiantes': estudiantes_data,
            'total_estudiantes': len(estudiantes_data),
            'resumen_presentes': resumen_presentes,
            'resumen_ausentes': resumen_ausentes,
            'resumen_fecha': fecha.strftime('%d/%m/%Y'),
            'asistencia_vista_previa': vista_previa and bool(estudiantes_data),
            'asistencia_sin_alumnos': not estudiantes_data and not vista_previa,
            'asistencia_datos_reales_url': (
                f"{reverse('registro_asistencia_clase', kwargs={'clase_id': clase.id})}"
                f"?fecha={fecha_param}&datos_reales=1"
            ),
            'pagina_actual': 'mis_clases',
            'user': request.user,
            'nombre_usuario': request.user.get_full_name(),
            'escuela_nombre': (
                request.user.colegio.nombre
                if hasattr(request.user, 'colegio') and request.user.colegio
                else 'Portal Académico'
            ),
            **navigation_access,
        },
    )


@login_required
def reporte_asistencia_clase(request, clase_id):
    """Reporte mensual de asistencia por clase."""
    clase = AttendanceService.get_class_for_user(request.user, clase_id)
    if not clase:
        messages.error(request, 'Clase no encontrada.')
        return redirect('dashboard')

    if request.user.id != clase.profesor_id:
        messages.error(request, 'No tienes permiso para ver reportes de asistencia de esta clase.')
        return redirect('dashboard')

    mes_param = request.GET.get('mes', str(date.today().month))
    anio_param = request.GET.get('anio', str(date.today().year))
    try:
        mes = int(mes_param)
        anio = int(anio_param)
    except (ValueError, TypeError):
        mes = date.today().month
        anio = date.today().year
    if mes < 1 or mes > 12:
        mes = date.today().month

    reporte = AttendanceService.get_attendance_report(request.user, clase, mes, anio)

    _, rol_nombre = _resolve_sidebar_and_role(request.user)
    navigation_access = DashboardService.get_navigation_access(
        rol_nombre,
        user=request.user,
        school_id=request.user.rbd_colegio,
    )

    from backend.apps.core.services.profesor_hero_service import ProfesorHeroService

    hero_sub_clase = f"{clase.curso.nombre} · {clase.asignatura.nombre}"
    rep_ctx = {
        'pagina_hero': 'reporte_asistencia',
        'hero_sub_clase': hero_sub_clase,
        'stats_generales': reporte['stats_generales'],
    }
    return render(
        request,
        'profesor/reporte_asistencia.html',
        {
            'prof_hero': ProfesorHeroService.for_clase_page(clase, rep_ctx),
            'hero_sub_clase': hero_sub_clase,
            'clase': clase,
            'estudiantes_stats': reporte['estudiantes_stats'],
            'stats_generales': reporte['stats_generales'],
            'mes': mes,
            'anio': anio,
            'meses': AttendanceService.get_months_list(),
            'anios': AttendanceService.get_years_list(),
            'mes_nombre': AttendanceService.get_month_name(mes),
            'pagina_actual': 'mis_clases',
            'user': request.user,
            'nombre_usuario': request.user.get_full_name(),
            'escuela_nombre': (
                request.user.colegio.nombre
                if hasattr(request.user, 'colegio') and request.user.colegio
                else 'Portal Académico'
            ),
            **navigation_access,
        },
    )
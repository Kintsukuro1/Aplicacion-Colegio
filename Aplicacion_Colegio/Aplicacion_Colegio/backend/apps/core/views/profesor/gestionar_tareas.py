"""
Vista para gestión de tareas del profesor
"""
from decimal import Decimal
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from backend.apps.cursos.models import Clase
from backend.apps.academico.models import EntregaTarea, Tarea
from backend.apps.academico.services.resoluble_service import ResolubleService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.common.services.policy_service import PolicyService


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


def _parse_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'on', 'yes', 'si'}


def _parse_fecha_entrega(value):
    if not value:
        return None
    parsed = datetime.strptime(value, '%Y-%m-%dT%H:%M')
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _build_preguntas_desde_request(request):
    preguntas = []

    for indice in range(1, 3):
        enunciado = (request.POST.get(f'pregunta_{indice}_enunciado') or '').strip()
        if not enunciado:
            continue

        tipo = (request.POST.get(f'pregunta_{indice}_tipo') or 'opcion_multiple').strip()
        pregunta = {
            'tipo': tipo,
            'enunciado': enunciado,
            'orden': indice,
            'puntaje_maximo': request.POST.get(f'pregunta_{indice}_puntaje') or '1.0',
            'respuesta_correcta_texto': (request.POST.get(f'pregunta_{indice}_respuesta_texto') or '').strip(),
            'respuesta_correcta_normalizada': (request.POST.get(f'pregunta_{indice}_respuesta_texto') or '').strip(),
            'requiere_revision_docente': _parse_bool(request.POST.get(f'pregunta_{indice}_requiere_revision_docente')),
            'activa': True,
        }

        if tipo == 'opcion_multiple':
            opciones = []
            for opcion_indice in range(1, 5):
                texto = (request.POST.get(f'pregunta_{indice}_opcion_{opcion_indice}_texto') or '').strip()
                if not texto:
                    continue
                opciones.append(
                    {
                        'texto': texto,
                        'es_correcta': _parse_bool(
                            request.POST.get(f'pregunta_{indice}_opcion_{opcion_indice}_correcta')
                        ),
                        'orden': opcion_indice,
                    }
                )
            pregunta['opciones'] = opciones

        preguntas.append(pregunta)

    return preguntas


def _build_item_tarea(tarea):
    entregas = list(tarea.entregas.select_related('estudiante').all())
    entregas_revisadas = sum(1 for entrega in entregas if entrega.estado == 'revisada' or entrega.calificacion is not None)
    entregas_pendientes = sum(1 for entrega in entregas if entrega.calificacion is None)
    actividad = tarea.actividades_resolubles.all().first()

    total_entregas = len(entregas)
    porcentaje_entregas = round((total_entregas / max(total_entregas, 1)) * 100, 0) if total_entregas else 0

    return {
        'tarea': tarea,
        'actividad_resoluble': actividad,
        'total_entregas': total_entregas,
        'entregas_revisadas': entregas_revisadas,
        'entregas_pendientes': entregas_pendientes,
        'porcentaje_entregas': porcentaje_entregas,
    }


@login_required
def gestionar_tareas_profesor(request, clase_id):
    """Vista para que el profesor gestione tareas de una clase."""
    try:
        clase = ORMAccessService.get(Clase, id=clase_id)  # Fix: Clase.pk es id, no id_curso (Curso).
    except Exception:
        messages.error(request, 'No se encontró la clase solicitada.')
        return redirect('dashboard')
    
    # Verificar que es profesor de esta clase
    if request.user.id != clase.profesor_id:
        messages.error(request, 'No tienes permiso para gestionar tareas de esta clase.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        accion = (request.POST.get('accion') or '').strip()

        if accion in {'crear_tarea', 'crear_actividad_hibrida'}:
            titulo = (request.POST.get('titulo') or '').strip()
            instrucciones = (request.POST.get('instrucciones') or '').strip()
            fecha_entrega_raw = request.POST.get('fecha_entrega')
            modalidad = (request.POST.get('modalidad') or 'MIXTA').strip().upper()
            es_publica = _parse_bool(request.POST.get('es_publica', '1'))
            requiere_aprobacion_docente = _parse_bool(request.POST.get('requiere_aprobacion_docente', '1'))
            auto_correccion_activa = _parse_bool(request.POST.get('auto_correccion_activa', '1'))
            archivo_instrucciones = request.FILES.get('archivo_instrucciones')

            if not titulo or not instrucciones or not fecha_entrega_raw:
                messages.error(request, 'Completa título, instrucciones y fecha de entrega.')
            else:
                try:
                    fecha_entrega = _parse_fecha_entrega(fecha_entrega_raw)
                except ValueError:
                    fecha_entrega = None

                if not fecha_entrega:
                    messages.error(request, 'La fecha de entrega no tiene un formato válido.')
                else:
                    preguntas = _build_preguntas_desde_request(request)

                    with transaction.atomic():
                        tarea = Tarea.objects.create(
                            colegio=clase.colegio,
                            clase=clase,
                            titulo=titulo,
                            instrucciones=instrucciones,
                            archivo_instrucciones=archivo_instrucciones,
                            fecha_entrega=fecha_entrega,
                            es_publica=es_publica,
                            creada_por=request.user,
                            activa=True,
                        )

                        ResolubleService.create_or_update_activity(
                            actor=request.user,
                            payload={
                                'origen_tipo': 'tarea',
                                'origen_id': tarea.id_tarea,
                                'titulo': titulo,
                                'modalidad': modalidad,
                                'archivo_pdf': tarea.archivo_instrucciones,
                                'requiere_aprobacion_docente': requiere_aprobacion_docente,
                                'auto_correccion_activa': auto_correccion_activa,
                                'estado': 'PUBLICADA',
                                'activa': True,
                                'preguntas': preguntas,
                            },
                        )

                    messages.success(request, f'La actividad "{titulo}" fue creada correctamente.')
                    return redirect('gestionar_tareas_profesor', clase_id=clase.id)

        elif accion == 'eliminar_tarea':
            tarea_id = request.POST.get('tarea_id')
            try:
                tarea = Tarea.objects.get(id_tarea=tarea_id, clase=clase)
            except Tarea.DoesNotExist:
                messages.error(request, 'No se encontró la tarea solicitada.')
            else:
                tarea.actividades_resolubles.all().delete()
                tarea.delete()
                messages.success(request, 'La tarea fue eliminada correctamente.')
                return redirect('gestionar_tareas_profesor', clase_id=clase.id)

    tareas_queryset = ORMAccessService.filter(Tarea, clase=clase, activa=True).prefetch_related('actividades_resolubles').order_by('-fecha_creacion')
    tareas = [_build_item_tarea(tarea) for tarea in tareas_queryset]

    total_entregas = EntregaTarea.objects.filter(tarea__clase=clase).count()
    total_pendientes = EntregaTarea.objects.filter(tarea__clase=clase, calificacion__isnull=True).count()
    total_revisadas = EntregaTarea.objects.filter(tarea__clase=clase, calificacion__isnull=False).count()
    
    sidebar_template, rol_nombre = _resolve_sidebar_and_role(request.user)
    navigation_access = DashboardService.get_navigation_access(
        rol_nombre,
        user=request.user,
        school_id=request.user.rbd_colegio,
    )
    
    context = {
        'clase': clase,
        'tareas': tareas,
        'total_tareas': len(tareas),
        'total_entregas': total_entregas,
        'total_pendientes': total_pendientes,
        'total_revisadas': total_revisadas,
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
    
    return render(request, 'academico/profesor/gestionar_tareas.html', context)


@login_required
def ver_entregas_tarea(request, tarea_id):
    """Vista para ver las entregas de una tarea."""
    try:
        tarea = ORMAccessService.get(Tarea, id_tarea=tarea_id)
    except Exception:
        messages.error(request, 'No se encontró la tarea solicitada.')
        return redirect('dashboard')
    clase = tarea.clase
    
    # Verificar que es profesor de esta clase
    if request.user.id != clase.profesor_id:
        messages.error(request, 'No tienes permiso para ver las entregas de esta tarea.')
        return redirect('dashboard')
    
    from backend.apps.academico.models import EntregaTarea
    
    # POST handler for grading tasks (single or bulk)
    if request.method == 'POST':
        accion = (request.POST.get('accion') or '').strip()
        
        if accion == 'calificar_entrega':
            entrega_id = request.POST.get('entrega_id')
            calificacion_val = request.POST.get('calificacion')
            retroalimentacion = (request.POST.get('retroalimentacion') or '').strip()
            
            try:
                entrega = EntregaTarea.objects.get(id_entrega=entrega_id, tarea=tarea)
                entrega.calificacion = Decimal(calificacion_val)
                entrega.retroalimentacion = retroalimentacion
                entrega.estado = 'revisada'
                entrega.revisada_por = request.user
                entrega.save()
                messages.success(request, f'Se calificó la entrega de {entrega.estudiante.get_full_name()} con nota {calificacion_val}.')
            except Exception as e:
                messages.error(request, f'Error al calificar la entrega: {str(e)}')
                
            return redirect('ver_entregas_tarea', tarea_id=tarea.id_tarea)
            
        elif accion == 'calificar_masiva':
            entrega_ids_raw = request.POST.get('entrega_ids', '')
            calificacion_val = request.POST.get('calificacion')
            retroalimentacion = (request.POST.get('retroalimentacion') or '').strip()
            
            if not entrega_ids_raw:
                messages.error(request, 'No se seleccionaron entregas para calificar.')
            else:
                try:
                    entrega_ids = [int(x.strip()) for x in entrega_ids_raw.split(',') if x.strip()]
                    entregas_qs = EntregaTarea.objects.filter(id_entrega__in=entrega_ids, tarea=tarea)
                    
                    with transaction.atomic():
                        count = 0
                        for entrega in entregas_qs:
                            if calificacion_val:
                                entrega.calificacion = Decimal(calificacion_val)
                            if retroalimentacion:
                                entrega.retroalimentacion = retroalimentacion
                            entrega.estado = 'revisada'
                            entrega.revisada_por = request.user
                            entrega.save()
                            count += 1
                            
                    messages.success(request, f'Se calificaron {count} entregas en lote correctamente.')
                except Exception as e:
                    messages.error(request, f'Error al calificar en lote: {str(e)}')
                    
            return redirect('ver_entregas_tarea', tarea_id=tarea.id_tarea)
            
    # Obtener alumnos y cruzar con entregas
    from backend.apps.cursos.models import ClaseEstudiante
    estudiantes_clase = ClaseEstudiante.objects.filter(clase=clase, activo=True).select_related('estudiante')
    
    entregas = EntregaTarea.objects.filter(tarea=tarea)
    entregas_map = {entrega.estudiante_id: entrega for entrega in entregas}
    
    estudiantes_list = []
    total_entregas = 0
    for rel in estudiantes_clase:
        est = rel.estudiante
        ent = entregas_map.get(est.id)
        tiene = ent is not None
        if tiene:
            total_entregas += 1
        estudiantes_list.append({
            'estudiante': est,
            'tiene_entrega': tiene,
            'entrega': ent
        })
        
    sidebar_template, rol_nombre = _resolve_sidebar_and_role(request.user)
    navigation_access = DashboardService.get_navigation_access(
        rol_nombre,
        user=request.user,
        school_id=request.user.rbd_colegio,
    )
    
    context = {
        'clase': clase,
        'tarea': tarea,
        'entregas': entregas,
        'estudiantes': estudiantes_list,
        'total_estudiantes': len(estudiantes_list),
        'total_entregas': total_entregas,
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
    
    return render(request, 'profesor/entregas_tarea.html', context)

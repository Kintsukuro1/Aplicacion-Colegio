import os
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from backend.apps.accounts.models import PerfilEstudiante
from backend.apps.academico.models import EntregaTarea, Tarea
from backend.apps.academico.services.tarea_entrega_service import TareaEntregaService
from backend.apps.cursos.models import Clase
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.services.dashboard_context_service import DashboardContextService
from backend.common.utils.dashboard_helpers import build_dashboard_context
from backend.common.services.policy_service import PolicyService


def _validate_uploaded_file(uploaded_file):
    if not uploaded_file:
        raise ValueError('❌ Debes subir un archivo para entregar la tarea.')

    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)
    if uploaded_file.size and uploaded_file.size > max_size:
        raise ValueError('❌ El archivo excede el tamaño máximo permitido (50 MB).')

    allowed_exts = getattr(settings, 'ALLOWED_UPLOAD_EXTENSIONS', None)
    if allowed_exts:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in allowed_exts:
            raise ValueError('❌ Tipo de archivo no permitido.')

    allowed_mimes = getattr(settings, 'ALLOWED_MIME_TYPES', None)
    content_type = getattr(uploaded_file, 'content_type', None)
    if allowed_mimes and content_type and content_type not in allowed_mimes:
        raise ValueError('❌ Tipo MIME no permitido.')


def _get_estado_entrega(tarea, entrega):
    """Retorna (estado, icono, texto) en el formato esperado por templates."""
    if entrega:
        # Si hay calificación o fue revisada, se considera corregida
        if entrega.calificacion is not None or entrega.estado == 'revisada' or entrega.retroalimentacion:
            return 'corregida', '✅', 'Corregida'

        # Entregada tarde
        if entrega.estado == 'tarde' or entrega.fue_entregada_tarde():
            return 'atrasada', '⏰', 'Entregada tarde'

        return 'entregada', '📤', 'Entregada'

    if tarea.esta_vencida():
        return 'atrasada', '⏰', 'Atrasada'
    return 'pendiente', '📝', 'Pendiente'


def _get_estado_tiempo(tarea):
    ahora = timezone.now()
    if not tarea.fecha_entrega:
        return 'normal'

    tiempo_restante = tarea.fecha_entrega - ahora
    if tiempo_restante.total_seconds() < 0:
        return 'vencida'
    if tiempo_restante.days <= 1:
        return 'urgente'
    if tiempo_restante.days <= 3:
        return 'proximo'
    return 'normal'


def _get_estudiante_perfil_y_curso(user):
    """Resuelve perfil y curso con fallback robusto para evitar falsos vacios."""
    perfil = ORMAccessService.get(PerfilEstudiante, user=user)
    curso = DashboardContextService._resolve_estudiante_curso_actual(user)
    return perfil, curso





@login_required()
def ver_tareas_estudiante(request):
    """Listado de tareas del estudiante + entrega/reemplazo de archivos."""
    can_view_class = PolicyService.has_capability(request.user, 'CLASS_VIEW')
    can_manage_class = (
        PolicyService.has_capability(request.user, 'CLASS_EDIT')
        or PolicyService.has_capability(request.user, 'CLASS_TAKE_ATTENDANCE')
    )
    if not (can_view_class and not can_manage_class):
        return render(request, 'compartido/acceso_denegado.html')

    try:
        perfil, curso_actual = _get_estudiante_perfil_y_curso(request.user)
    except PerfilEstudiante.DoesNotExist:
        messages.error(request, 'No tienes un curso asignado.')
        return redirect('dashboard')

    if not curso_actual:
        messages.error(request, 'No tienes un curso asignado.')
        return redirect('dashboard')

    # Procesar entrega de tarea
    if request.method == 'POST' and request.POST.get('accion') == 'entregar_tarea':
        tarea_id = request.POST.get('tarea_id')
        archivo = request.FILES.get('archivo')
        comentario = request.POST.get('comentario', '')

        try:
            _validate_uploaded_file(archivo)

            try:
                tarea = ORMAccessService.get(
                    Tarea,
                    id_tarea=tarea_id,
                    es_publica=True,
                    activa=True,
                    colegio_id=request.user.rbd_colegio,
                    clase__curso=curso_actual,
                )
            except Exception:
                messages.error(request, '❌ No se encontró la tarea seleccionada.')
                return redirect('ver_tareas_estudiante')

            entrega, created = TareaEntregaService.upsert_entrega(
                tarea=tarea,
                estudiante=request.user,
                archivo=archivo,
                comentario=comentario,
            )

            if not created:
                if tarea.esta_vencida():
                    messages.warning(
                        request,
                        '⚠️ La tarea está vencida. La entrega se marcará como tardía.',
                    )
                messages.success(request, '✓ Entrega actualizada correctamente.')
            else:
                if tarea.esta_vencida():
                    messages.warning(request, '⚠️ Entrega registrada como tardía.')
                else:
                    messages.success(request, '✓ Tarea entregada correctamente.')
        except ValueError as ve:
            messages.error(request, str(ve))
        except Exception as e:
            messages.error(request, f'Error al entregar tarea: {e}')

        return redirect('ver_tareas_estudiante')

    clases = ORMAccessService.filter(
        Clase,
        curso=curso_actual,
        colegio_id=request.user.rbd_colegio,
        activo=True,
    )

    tareas_qs = (
        ORMAccessService.filter(
            Tarea,
            clase__in=clases,
            es_publica=True,
            activa=True,
            colegio_id=request.user.rbd_colegio,
        )
        .select_related('clase__asignatura')
        .order_by('fecha_entrega')
    )

    entregas = ORMAccessService.filter(
        EntregaTarea,
        tarea__in=tareas_qs,
        estudiante=request.user,
    )
    entregas_por_tarea = {e.tarea_id: e for e in entregas}

    tareas_con_entrega = []
    for tarea in tareas_qs:
        entrega = entregas_por_tarea.get(tarea.id_tarea)
        estado, icono_estado, texto_estado = _get_estado_entrega(tarea, entrega)
        tareas_con_entrega.append(
            {
                'tarea': tarea,
                'entrega': entrega,
                'estado': estado,
                'icono_estado': icono_estado,
                'texto_estado': texto_estado,
                'estado_tiempo': _get_estado_tiempo(tarea),
                'dias_restantes': tarea.dias_restantes(),
            }
        )

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='tareas',
        content_template='estudiante/tareas.html',
    )
    if redirect_response:
        return redirect_response

    context.update(
        {
            'tareas': tareas_con_entrega,
            'total_tareas': len(tareas_con_entrega),
        }
    )
    return render(request, 'dashboard.html', context)


@login_required()
def calendario_tareas_estudiante(request):
    """Calendario mensual de tareas del estudiante."""
    can_view_class = PolicyService.has_capability(request.user, 'CLASS_VIEW')
    can_manage_class = (
        PolicyService.has_capability(request.user, 'CLASS_EDIT')
        or PolicyService.has_capability(request.user, 'CLASS_TAKE_ATTENDANCE')
    )
    if not (can_view_class and not can_manage_class):
        return render(request, 'compartido/acceso_denegado.html')

    try:
        perfil, curso_actual = _get_estudiante_perfil_y_curso(request.user)
    except PerfilEstudiante.DoesNotExist:
        messages.error(request, 'No tienes un curso asignado.')
        return redirect('dashboard')

    if not curso_actual:
        messages.error(request, 'No tienes un curso asignado.')
        return redirect('dashboard')

    clases = ORMAccessService.filter(
        Clase,
        curso=curso_actual,
        colegio_id=request.user.rbd_colegio,
        activo=True,
    )

    tareas_qs = (
        ORMAccessService.filter(
            Tarea,
            clase__in=clases,
            es_publica=True,
            activa=True,
            colegio_id=request.user.rbd_colegio,
        )
        .select_related('clase__asignatura', 'creada_por')
        .order_by('fecha_entrega')
    )

    entregas = ORMAccessService.filter(
        EntregaTarea,
        tarea__in=tareas_qs,
        estudiante=request.user,
    )
    entregas_por_tarea = {e.tarea_id: e for e in entregas}

    tareas_json = []
    for tarea in tareas_qs:
        entrega = entregas_por_tarea.get(tarea.id_tarea)
        estado, icono_estado, texto_estado = _get_estado_entrega(tarea, entrega)

        fecha_entrega = tarea.fecha_entrega
        tareas_json.append(
            {
                'id': tarea.id_tarea,
                'titulo': tarea.titulo,
                'instrucciones': tarea.instrucciones,
                'asignatura': tarea.clase.asignatura.nombre,
                'fecha_entrega_date': fecha_entrega.strftime('%Y-%m-%d') if fecha_entrega else None,
                'fecha_entrega_time': fecha_entrega.strftime('%H:%M') if fecha_entrega else None,
                'fecha_entrega_full': fecha_entrega.strftime('%d/%m/%Y %H:%M') if fecha_entrega else 'Sin fecha',
                'estado': estado,
                'icono_estado': icono_estado,
                'texto_estado': texto_estado,
                'archivo_instrucciones': tarea.archivo_instrucciones.url if tarea.archivo_instrucciones else None,
                'calificacion': float(entrega.calificacion) if entrega and entrega.calificacion is not None else None,
            }
        )

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual='calendario_tareas',
        content_template='estudiante/calendario_tareas.html',
    )
    if redirect_response:
        return redirect_response

    # json_script handles JSON serialization safely in template.
    context['tareas_json'] = tareas_json
    return render(request, 'dashboard.html', context)


@login_required()
def mi_asistencia_estudiante(request):
    """Shortcut para asistencia del estudiante.

    El dashboard ya soporta `pagina=asistencia`.
    """
    return redirect(f"{reverse('dashboard')}?pagina=asistencia")


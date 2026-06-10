from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from backend.apps.accounts.models import User
from backend.apps.cursos.models import Clase
from backend.apps.academico.models import PerfilEstudiante
from backend.apps.horarios.models import BloqueHorario
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.common.services.policy_service import PolicyService

@login_required()
def ver_mis_clases_profesor(request):
    """
    Vista para que el profesor vea todas sus clases activas
    Muestra un selector para elegir qué clase ver en detalle
    """
    user = request.user
    
    # Verificar rol
    can_view_class = PolicyService.has_capability(user, 'CLASS_VIEW')
    can_manage_class = (
        PolicyService.has_capability(user, 'CLASS_EDIT')
        or PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE')
    )
    if not (can_view_class and can_manage_class):
        return render(request, 'compartido/acceso_denegado.html')
    
    # Obtener todas las clases activas del profesor
    # ✅ Query optimizado con select_related
    from backend.apps.core.optimizations import get_clases_profesor_optimized
    clases = get_clases_profesor_optimized(user.rbd_colegio, user.id)
    
    mis_clases = []
    total_estudiantes_sum = 0
    total_horas_sum = 0
    cursos_unicos = set()
    
    for clase in clases:
        # Obtener bloques horarios de esta clase
        bloques = ORMAccessService.filter(
            BloqueHorario,
            clase=clase,
            activo=True
        ).order_by('dia_semana', 'bloque_numero')
        
        # Agrupar bloques por día
        horarios_por_dia = {}
        total_bloques = bloques.count()
        
        for bloque in bloques:
            dia_nombre = bloque.get_dia_semana_display()
            if dia_nombre not in horarios_por_dia:
                horarios_por_dia[dia_nombre] = []
            
            horarios_por_dia[dia_nombre].append({
                'bloque_numero': bloque.bloque_numero,
                'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                'hora_fin': bloque.hora_fin.strftime('%H:%M'),
            })
        
        # Contar estudiantes en el curso
        total_estudiantes = ORMAccessService.filter(
            User,
            rbd_colegio=user.rbd_colegio,
            perfil_estudiante__isnull=False,
            perfil_estudiante__ciclo_actual=clase.curso.ciclo_academico,
            is_active=True
        ).count()
        
        mis_clases.append({
            'id_clase': clase.id,
            'asignatura': clase.asignatura.nombre,
            'codigo': clase.asignatura.codigo,
            'color': clase.asignatura.color,
            'horas_semanales': clase.asignatura.horas_semanales,
            'curso_nombre': clase.curso.nombre,
            'total_estudiantes': total_estudiantes,
            'horarios_por_dia': horarios_por_dia,
            'total_bloques': total_bloques,
        })
        
        # Acumular para estadísticas
        total_estudiantes_sum += total_estudiantes
        total_horas_sum += clase.asignatura.horas_semanales
        cursos_unicos.add(clase.curso.id_curso)
    
    # Calcular estadísticas
    total_clases = len(mis_clases)
    promedio_estudiantes = round(total_estudiantes_sum / total_clases) if total_clases > 0 else 0
    total_horas_semanales = total_horas_sum
    total_cursos = len(cursos_unicos)
    
    context = {
        'mis_clases': mis_clases,
        'total_clases': total_clases,
        'promedio_estudiantes': promedio_estudiantes,
        'total_horas_semanales': total_horas_semanales,
        'total_cursos': total_cursos,
    }
    
    return JsonResponse(context, safe=False) if request.GET.get('json') else context


@login_required()
def redirigir_anuncios_clase(request, clase_id):
    """
    Redirige las URLs antiguas de anuncios a la pestaña de anuncios en detalle_clase
    Los anuncios están integrados en la vista de detalle de clase
    """
    from django.shortcuts import redirect
    # Redirigir a la vista de detalle de clase con un ancla para abrir la pestaña de anuncios
    return redirect(f'/estudiante/clase/{clase_id}/#anuncios')


@login_required()
def redirigir_tareas_duplicadas(request):
    """
    Redirige URLs duplicadas de tareas a la URL correcta
    Fix para navegación relativa que causa /estudiante/tareas/estudiante/tareas/
    """
    from django.shortcuts import redirect
    return redirect('/estudiante/tareas/')

@login_required()
def ver_detalle_clase(request, clase_id):
    """Delega la orquestación completa al servicio de detalle de clase."""
    from backend.apps.core.services.class_detail_service import ClassDetailService

    return ClassDetailService.handle_request(request, clase_id)

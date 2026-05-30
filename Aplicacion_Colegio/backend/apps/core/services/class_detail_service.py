"""
Servicio de detalle de clase.
Centraliza la lógica de negocio de la vista ver_detalle_clase.
"""

from datetime import date
from django.contrib import messages
from django.shortcuts import redirect, render

from backend.apps.accounts.models import User, PerfilEstudiante
from backend.apps.academico.services.material_clase_service import MaterialClaseService
from backend.apps.cursos.models import Clase, BloqueHorario
from backend.common.services.policy_service import PolicyService


class ClassDetailService:
    """Orquesta datos y acciones para detalle de clase."""

    @staticmethod
    def handle_request(request, clase_id):
        from backend.apps.academico.models import MaterialClase, Evaluacion, Tarea, EntregaTarea
        from backend.apps.mensajeria.models import Anuncio

        user = request.user
        can_view_class = PolicyService.has_capability(user, 'CLASS_VIEW')
        can_manage_class = (
            PolicyService.has_capability(user, 'CLASS_EDIT')
            or PolicyService.has_capability(user, 'CLASS_TAKE_ATTENDANCE')
        )

        is_teacher = can_view_class and can_manage_class
        is_student = can_view_class and not is_teacher

        if not (is_student or is_teacher):
            return render(request, 'compartido/acceso_denegado.html')

        ver_como_alumno = request.GET.get('ver_como_alumno') == '1' and is_teacher

        if request.method == 'POST' and is_teacher:
            accion = request.POST.get('accion')

            if accion == 'subir_material':
                try:
                    titulo = request.POST.get('titulo')
                    descripcion = request.POST.get('descripcion', '')
                    es_publico = request.POST.get('es_publico') == '1'
                    tipo_archivo = request.POST.get('tipo_archivo', 'documento')
                    archivo = request.FILES.get('archivo')

                    if not titulo or not archivo:
                        messages.error(request, 'El título y el archivo son obligatorios.')
                    else:
                        MaterialClaseService.create(
                            user=user,
                            clase_id=clase_id,
                            titulo=titulo,
                            descripcion=descripcion,
                            archivo=archivo,
                            tipo_archivo=tipo_archivo,
                            es_publico=es_publico,
                        )
                        messages.success(request, f'✓ Material "{titulo}" subido correctamente.')
                        return redirect(f'/estudiante/clase/{clase_id}/')

                except Exception as e:
                    messages.error(request, f'Error al subir material: {str(e)}')

            elif accion == 'eliminar_material':
                try:
                    material_id = request.POST.get('material_id')
                    MaterialClaseService.deactivate(
                        user=user,
                        clase_id=clase_id,
                        material_id=material_id,
                    )
                    messages.success(request, '✓ Material eliminado correctamente.')
                    return redirect(f'/estudiante/clase/{clase_id}/')
                except Exception as e:
                    messages.error(request, f'Error al eliminar material: {str(e)}')

            elif accion == 'cambiar_visibilidad':
                try:
                    material_id = request.POST.get('material_id')
                    material = MaterialClaseService.toggle_visibility(
                        user=user,
                        clase_id=clase_id,
                        material_id=material_id,
                    )
                    estado = 'público' if material.es_publico else 'privado'
                    messages.success(request, f'✓ Material marcado como {estado}.')
                    return redirect(f'/estudiante/clase/{clase_id}/')
                except Exception as e:
                    messages.error(request, f'Error al cambiar visibilidad: {str(e)}')

        try:
            if is_student:
                perfil = PerfilEstudiante.objects.get(user=user)
                ciclo_actual = perfil.ciclo_actual

                clase = Clase.objects.select_related(
                    'asignatura', 'profesor', 'curso', 'colegio'
                ).get(
                    id=clase_id,
                    colegio=user.colegio,
                    curso__ciclo_academico=ciclo_actual,
                    activo=True
                )
            else:
                clase = Clase.objects.select_related(
                    'asignatura', 'profesor', 'curso', 'colegio'
                ).get(
                    id=clase_id,
                    colegio=user.colegio,
                    profesor=user,
                    activo=True
                )

        except (Clase.DoesNotExist, PerfilEstudiante.DoesNotExist):
            messages.error(request, 'No tienes acceso a esta clase.')
            return redirect('dashboard')

        bloques = BloqueHorario.objects.filter(
            clase=clase,
            activo=True
        ).order_by('dia_semana', 'bloque_numero')

        horarios_por_dia = {}
        for bloque in bloques:
            dia_nombre = bloque.get_dia_semana_display()
            if dia_nombre not in horarios_por_dia:
                horarios_por_dia[dia_nombre] = {
                    'bloques': [],
                    'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                    'hora_fin': bloque.hora_fin.strftime('%H:%M')
                }
            else:
                if bloque.hora_fin.strftime('%H:%M') > horarios_por_dia[dia_nombre]['hora_fin']:
                    horarios_por_dia[dia_nombre]['hora_fin'] = bloque.hora_fin.strftime('%H:%M')

            horarios_por_dia[dia_nombre]['bloques'].append({
                'bloque_numero': bloque.bloque_numero,
                'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                'hora_fin': bloque.hora_fin.strftime('%H:%M'),
            })

        evaluaciones_proximas = Evaluacion.objects.filter(
            clase=clase,
            activa=True,
            fecha_evaluacion__gte=date.today()
        ).order_by('fecha_evaluacion')[:5]

        progreso = 0
        nota_actual = None
        calificaciones_detalle = []
        if is_student:
            from backend.apps.academico.models import Calificacion
            from backend.apps.academico.services.grades_service import GradesService

            total_evaluaciones = Evaluacion.objects.filter(
                clase=clase,
                activa=True
            ).count()

            if total_evaluaciones > 0:
                calificaciones_estudiante = Calificacion.objects.filter(
                    estudiante=user,
                    evaluacion__clase=clase,
                    evaluacion__activa=True
                ).count()
                progreso = min(int((calificaciones_estudiante / total_evaluaciones) * 100), 100)

            resultado_nota = GradesService.calculate_student_final_grade(user, clase)
            nota_actual = resultado_nota.get('nota_final')

            calificaciones_obj = Calificacion.objects.filter(
                estudiante=user,
                evaluacion__clase=clase,
                evaluacion__activa=True
            ).select_related('evaluacion').order_by('evaluacion__fecha_evaluacion')

            calificaciones_detalle = [
                {
                    'nombre': c.evaluacion.nombre,
                    'fecha': c.evaluacion.fecha_evaluacion,
                    'nota': float(c.nota),
                    'ponderacion': float(c.evaluacion.ponderacion or 100),
                }
                for c in calificaciones_obj
            ]

        estudiantes_queryset = User.objects.filter(
            rbd_colegio=user.rbd_colegio,
            perfil_estudiante__isnull=False,
            perfil_estudiante__ciclo_actual=clase.curso.ciclo_academico,
            is_active=True
        ).order_by('apellido_paterno', 'apellido_materno', 'nombre')

        if is_student:
            estudiantes_lista = estudiantes_queryset.exclude(id=user.id)
        else:
            estudiantes_lista = estudiantes_queryset

        total_estudiantes = estudiantes_queryset.count()

        if is_student or ver_como_alumno:
            materiales = MaterialClase.objects.filter(
                clase=clase,
                activo=True,
                es_publico=True
            ).select_related('subido_por').order_by('-fecha_creacion')
        else:
            materiales = MaterialClase.objects.filter(
                clase=clase,
                activo=True
            ).select_related('subido_por').order_by('-fecha_creacion')

        if is_student or ver_como_alumno:
            tareas_query = Tarea.objects.filter(
                clase=clase,
                activa=True,
                es_publica=True
            ).order_by('-fecha_entrega')

            tareas = []
            for tarea in tareas_query:
                entrega = EntregaTarea.objects.filter(tarea=tarea, estudiante=user).first()
                tareas.append({
                    'tarea': tarea,
                    'entrega': entrega,
                    'estado': tarea.get_estado(user) if hasattr(tarea, 'get_estado') else 'pendiente',
                    'icono_estado': tarea.get_icono_estado(user) if hasattr(tarea, 'get_icono_estado') else '📝',
                    'texto_estado': tarea.get_texto_estado(user) if hasattr(tarea, 'get_texto_estado') else 'Pendiente',
                })
        else:
            tareas_query = Tarea.objects.filter(
                clase=clase,
                activa=True
            ).order_by('-fecha_entrega')

            tareas = []
            for tarea in tareas_query:
                entregas_count = EntregaTarea.objects.filter(tarea=tarea).count()
                tareas.append({
                    'tarea': tarea,
                    'entregas_count': entregas_count,
                })

        entregas_pendientes = []
        total_entregas_pendientes = 0
        if is_teacher and not ver_como_alumno:
            entregas_pendientes = EntregaTarea.objects.filter(
                tarea__clase=clase,
                tarea__activa=True,
                calificacion__isnull=True
            ).select_related('estudiante', 'tarea').order_by('fecha_entrega')[:10]
            total_entregas_pendientes = entregas_pendientes.count()

        todos_anuncios = Anuncio.objects.filter(clase=clase)

        if is_student:
            no_leidos = []
            leidos = []
            for anuncio in todos_anuncios:
                if hasattr(anuncio, 'esta_leido_por') and anuncio.esta_leido_por(user):
                    leidos.append(anuncio)
                else:
                    no_leidos.append(anuncio)

            no_leidos.sort(key=lambda a: (-getattr(a, 'anclado', False), -a.fecha_creacion.timestamp()))
            leidos.sort(key=lambda a: (-getattr(a, 'anclado', False), -a.fecha_creacion.timestamp()))

            anuncios = no_leidos + leidos
            total_anuncios = len(no_leidos)
        else:
            anuncios = list(todos_anuncios)
            total_anuncios = len(anuncios)

        context = {
            'clase': clase,
            'asignatura': clase.asignatura,
            'profesor': clase.profesor,
            'curso': clase.curso,
            'horarios_por_dia': horarios_por_dia,
            'total_bloques': bloques.count(),
            'evaluaciones_proximas': evaluaciones_proximas,
            'progreso': progreso,
            'nota_actual': nota_actual,
            'calificaciones_detalle': calificaciones_detalle,
            'total_estudiantes': total_estudiantes,
            'estudiantes_lista': estudiantes_lista,
            'es_profesor': is_teacher,
            'ver_como_alumno': ver_como_alumno,
            'materiales': materiales,
            'total_materiales': materiales.count(),
            'tareas': tareas,
            'total_tareas': len(tareas),
            'entregas_pendientes': entregas_pendientes,
            'total_entregas_pendientes': total_entregas_pendientes,
            'total_anuncios': total_anuncios,
            'anuncios': anuncios,
        }

        if ver_como_alumno:
            template = 'estudiante/detalle_clase.html'
        else:
            template = 'profesor/detalle_clase.html' if is_teacher else 'estudiante/detalle_clase.html'

        return render(request, template, context)

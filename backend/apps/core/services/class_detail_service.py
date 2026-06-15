"""
Servicio de detalle de clase.
Centraliza la lógica de negocio de la vista ver_detalle_clase.
"""

from datetime import date, timedelta
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from backend.apps.accounts.models import User, PerfilEstudiante
from backend.apps.academico.services.material_clase_service import MaterialClaseService
from backend.apps.cursos.models import Clase, BloqueHorario
from backend.apps.core.services.demo_visual_service import apply_demo_detalle_clase_context, is_demo_pk
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
                material_id = request.POST.get('material_id')
                if is_demo_pk(material_id):
                    messages.info(request, 'Datos de prueba: este material es solo de ejemplo.')
                    return redirect(f'/estudiante/clase/{clase_id}/')
                try:
                    MaterialClaseService.deactivate(
                        user=user,
                        clase_id=clase_id,
                        material_id=material_id,
                    )
                    messages.success(request, '✓ Material eliminado correctamente.')
                    return redirect(f'/estudiante/clase/{clase_id}/')
                except Exception as e:
                    messages.error(request, f'Error al eliminar material: {str(e)}')

            elif accion == 'eliminar_anuncio':
                anuncio_id = request.POST.get('anuncio_id')
                if is_demo_pk(anuncio_id):
                    messages.info(request, 'Datos de prueba: este anuncio es solo de ejemplo.')
                    return redirect(f'/estudiante/clase/{clase_id}/?tab=anuncios')
                # Fix: el template ya no usa la URL inexistente 'eliminar_anuncio'; POST aquí mismo.
                try:
                    anuncio = Anuncio.objects.get(
                        id_anuncio=anuncio_id,
                        clase_id=clase_id,
                        autor=user,
                    )
                    anuncio.delete()
                    messages.success(request, '✓ Anuncio eliminado correctamente.')
                    return redirect(f'/estudiante/clase/{clase_id}/?tab=anuncios')
                except Anuncio.DoesNotExist:
                    messages.error(request, 'No se encontró el anuncio o no tienes permiso para eliminarlo.')
                    return redirect(f'/estudiante/clase/{clase_id}/')
                except Exception as e:
                    messages.error(request, f'Error al eliminar anuncio: {str(e)}')
                    return redirect(f'/estudiante/clase/{clase_id}/')

            elif accion == 'cambiar_visibilidad':
                material_id = request.POST.get('material_id')
                if is_demo_pk(material_id):
                    messages.info(request, 'Datos de prueba: no se cambia visibilidad en ejemplos.')
                    return redirect(f'/estudiante/clase/{clase_id}/')
                try:
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

        if request.method == 'POST' and is_student:
            accion = request.POST.get('accion')

            if accion == 'entregar_tarea':
                tarea_id = request.POST.get('tarea_id')
                archivo = request.FILES.get('archivo')
                comentario = request.POST.get('comentario', '')

                try:
                    from backend.apps.core.views.estudiante.tareas import _validate_uploaded_file
                    _validate_uploaded_file(archivo)

                    from backend.apps.core.services.dashboard_context_service import DashboardContextService
                    from backend.apps.core.services.orm_access_service import ORMAccessService
                    
                    curso_actual = DashboardContextService._resolve_estudiante_curso_actual(user)
                    
                    try:
                        tarea = ORMAccessService.get(
                            Tarea,
                            id_tarea=tarea_id,
                            es_publica=True,
                            activa=True,
                            colegio_id=user.rbd_colegio,
                            clase__curso=curso_actual,
                        )
                    except Exception:
                        messages.error(request, '❌ No se encontró la tarea seleccionada.')
                        return redirect(f'/estudiante/clase/{clase_id}/?tab=assignments')

                    from backend.apps.academico.services.tarea_entrega_service import TareaEntregaService
                    entrega, created = TareaEntregaService.upsert_entrega(
                        tarea=tarea,
                        estudiante=user,
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

                return redirect(f'/estudiante/clase/{clase_id}/?tab=assignments')

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

            from backend.apps.core.views.estudiante.tareas import _get_estado_entrega, _get_estado_tiempo
            tareas = []
            for tarea in tareas_query:
                entrega = EntregaTarea.objects.filter(tarea=tarea, estudiante=user).first()
                estado, icono_estado, texto_estado = _get_estado_entrega(tarea, entrega)
                tareas.append({
                    'tarea': tarea,
                    'entrega': entrega,
                    'estado': estado,
                    'icono_estado': icono_estado,
                    'texto_estado': texto_estado,
                    'estado_tiempo': _get_estado_tiempo(tarea),
                    'dias_restantes': tarea.dias_restantes(),
                })
        else:
            from backend.apps.cursos.models import ClaseEstudiante

            total_estudiantes = ClaseEstudiante._base_manager.filter(
                clase=clase,
                activo=True,
            ).count()

            tareas_query = Tarea.objects.filter(
                clase=clase,
                activa=True
            ).order_by('-fecha_entrega')

            tareas = []
            ahora = timezone.now()
            for tarea in tareas_query:
                entregas_count = EntregaTarea.objects.filter(tarea=tarea).count()
                pendientes_corregir = EntregaTarea.objects.filter(
                    tarea=tarea,
                    calificacion__isnull=True,
                ).count()
                pct_entrega = (
                    min(100, round((entregas_count / total_estudiantes) * 100))
                    if total_estudiantes
                    else 0
                )
                vence_pronto = False
                if tarea.fecha_entrega and not getattr(tarea, 'esta_vencida', False):
                    delta = tarea.fecha_entrega - ahora
                    vence_pronto = 0 <= delta.total_seconds() <= 48 * 3600

                tareas.append({
                    'tarea': tarea,
                    'entregas_count': entregas_count,
                    'pendientes_corregir': pendientes_corregir,
                    'pct_entrega': pct_entrega,
                    'vence_pronto': vence_pronto,
                })

        entregas_pendientes = []
        total_entregas_pendientes = 0
        if is_teacher and not ver_como_alumno:
            entregas_qs = EntregaTarea.objects.filter(
                tarea__clase=clase,
                tarea__activa=True,
                calificacion__isnull=True,
            ).select_related('estudiante', 'tarea').order_by('fecha_entrega')
            total_entregas_pendientes = entregas_qs.count()
            entregas_pendientes = list(entregas_qs[:8])

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

        if is_student or ver_como_alumno:
            context.update(
                ClassDetailService._enriquecer_estudiante_detalle_clase(
                    user=user,
                    clase=clase,
                    tareas=tareas,
                    evaluaciones_proximas=list(evaluaciones_proximas),
                    calificaciones_detalle=calificaciones_detalle,
                    progreso=progreso,
                    nota_actual=nota_actual,
                    horarios_por_dia=horarios_por_dia,
                )
            )

        if is_teacher and not ver_como_alumno:
            from backend.apps.mensajeria.services import MensajeriaService

            context.update(
                ClassDetailService._enriquecer_profesor_detalle_clase(
                    clase=clase,
                    tareas=tareas,
                    evaluaciones_proximas=list(evaluaciones_proximas),
                    horarios_por_dia=horarios_por_dia,
                    total_estudiantes=total_estudiantes,
                    total_entregas_pendientes=total_entregas_pendientes,
                    entregas_pendientes=entregas_pendientes,
                    materiales_count=materiales.count(),
                )
            )
            context.update(
                MensajeriaService.get_clase_mensajes_panel_context(user, clase)
            )
            context = apply_demo_detalle_clase_context(request, context, clase)
            from backend.apps.core.services.profesor_hero_service import ProfesorHeroService
            context['prof_hero'] = ProfesorHeroService.for_clase_page(clase, context)

        if ver_como_alumno:
            return render(request, 'estudiante/detalle_clase.html', context)

        if is_teacher:
            from backend.common.utils.dashboard_helpers import build_dashboard_context

            shell, redirect_response = build_dashboard_context(
                request,
                pagina_actual='mis_clases',
                content_template='profesor/detalle_clase.html',
            )
            if redirect_response:
                return redirect_response
            shell.update(context)
            return render(request, 'dashboard.html', shell)

        return render(request, 'estudiante/detalle_clase.html', context)

    @staticmethod
    def _enriquecer_estudiante_detalle_clase(
        user,
        clase,
        tareas,
        evaluaciones_proximas,
        calificaciones_detalle,
        progreso,
        nota_actual,
        horarios_por_dia,
    ):
        """Métricas e insights reales para detalle de clase (estudiante)."""
        from backend.apps.academico.models import Asistencia, Evaluacion
        from backend.common.utils.grade_scale import es_aprobado

        hoy = date.today()

        total_evaluaciones = Evaluacion.objects.filter(clase=clase, activa=True).count()
        evaluaciones_con_nota = len(calificaciones_detalle)
        evaluaciones_sin_nota = max(total_evaluaciones - evaluaciones_con_nota, 0)

        tareas_pendientes_count = sum(1 for item in tareas if not item.get('entrega'))
        tareas_entregadas_count = len(tareas) - tareas_pendientes_count

        tareas_vencen_pronto = 0
        proxima_tarea = None
        for item in tareas:
            if item.get('entrega'):
                continue
            tarea = item['tarea']
            if not tarea.fecha_entrega:
                continue
            if tarea.fecha_entrega.date() < hoy:
                tareas_vencen_pronto += 1
            elif proxima_tarea is None or tarea.fecha_entrega < proxima_tarea.fecha_entrega:
                proxima_tarea = tarea

        asist_row = Asistencia.objects.filter(
            estudiante=user,
            clase=clase,
        ).aggregate(
            total=Count('pk'),
            presentes=Count('pk', filter=Q(estado='P')),
        )
        porcentaje_asistencia = None
        if asist_row['total']:
            porcentaje_asistencia = round(
                (asist_row['presentes'] / asist_row['total']) * 100, 0
            )

        fechas_proximas = []
        for ev in evaluaciones_proximas[:6]:
            fechas_proximas.append(
                {
                    'tipo': 'evaluacion',
                    'fecha': ev.fecha_evaluacion,
                    'titulo': ev.nombre,
                    'subtipo': ev.get_tipo_evaluacion_display(),
                }
            )
        for item in tareas:
            if item.get('entrega'):
                continue
            tarea = item['tarea']
            if not tarea.fecha_entrega:
                continue
            f = tarea.fecha_entrega.date()
            if f < hoy or f > hoy + timedelta(days=21):
                continue
            fechas_proximas.append(
                {
                    'tipo': 'tarea',
                    'fecha': f,
                    'titulo': tarea.titulo,
                    'subtipo': 'Entrega',
                }
            )
        fechas_proximas.sort(key=lambda x: x['fecha'])

        profesor = clase.profesor
        profesor_display = profesor.get_full_name() if profesor else 'Sin profesor'
        if profesor_display.endswith(' Docente'):
            profesor_display = profesor_display[:-8].strip()

        horario_resumen = []
        for dia, info in horarios_por_dia.items():
            horario_resumen.append(f'{dia} {info["hora_inicio"]}–{info["hora_fin"]}')

        estado = 'estable'
        estado_label = 'Vas al día en esta asignatura'
        estado_hint = 'Revisa materiales y prepara las próximas evaluaciones.'
        if nota_actual is not None and not es_aprobado(nota_actual, getattr(user, 'colegio', None)):
            estado = 'riesgo'
            estado_label = 'Nota bajo el mínimo de aprobación'
            estado_hint = 'Prioriza estudiar para las evaluaciones pendientes y consulta al profesor.'
        elif tareas_vencen_pronto or (porcentaje_asistencia is not None and porcentaje_asistencia < 85):
            estado = 'atencion'
            estado_label = 'Hay puntos que requieren atención'
            estado_hint = 'Revisa tareas vencidas o tu asistencia en esta asignatura.'

        alertas = []
        if evaluaciones_sin_nota:
            alertas.append(
                f'{evaluaciones_sin_nota} evaluación(es) aún sin nota publicada.'
            )
        if tareas_pendientes_count:
            alertas.append(
                f'{tareas_pendientes_count} tarea(s) por entregar en esta asignatura.'
            )
        if tareas_vencen_pronto:
            alertas.append(f'{tareas_vencen_pronto} tarea(s) con fecha de entrega vencida.')
        if evaluaciones_proximas:
            ev = evaluaciones_proximas[0]
            dias = (ev.fecha_evaluacion - hoy).days
            cuando = 'hoy' if dias == 0 else ('mañana' if dias == 1 else f'en {dias} días')
            alertas.append(f'Próxima evaluación {cuando}: {ev.nombre}.')
        if porcentaje_asistencia is not None and porcentaje_asistencia < 90:
            alertas.append(f'Tu asistencia en esta clase es {porcentaje_asistencia}%.')

        consejo = 'Explora las pestañas Materiales, Tareas y Calificaciones para estar al día.'
        if proxima_tarea and tareas_pendientes_count:
            consejo = (
                f'La entrega más cercana es «{proxima_tarea.titulo}» '
                f'({proxima_tarea.fecha_entrega.strftime("%d/%m %H:%M")}).'
            )
        elif evaluaciones_proximas:
            consejo = f'Prepárate para «{evaluaciones_proximas[0].nombre}» del {evaluaciones_proximas[0].fecha_evaluacion.strftime("%d/%m")}.'

        evaluaciones_pendientes_lista = []
        calificados_nombres = {c['nombre'] for c in calificaciones_detalle}
        for ev in Evaluacion.objects.filter(clase=clase, activa=True).order_by('fecha_evaluacion'):
            if ev.nombre in calificados_nombres:
                continue
            evaluaciones_pendientes_lista.append(
                {
                    'nombre': ev.nombre,
                    'fecha': ev.fecha_evaluacion,
                    'tipo': ev.get_tipo_evaluacion_display(),
                }
            )

        return {
            'profesor_display': profesor_display,
            'total_evaluaciones': total_evaluaciones,
            'evaluaciones_con_nota': evaluaciones_con_nota,
            'evaluaciones_sin_nota': evaluaciones_sin_nota,
            'tareas_pendientes_count': tareas_pendientes_count,
            'tareas_entregadas_count': tareas_entregadas_count,
            'tareas_vencen_pronto': tareas_vencen_pronto,
            'porcentaje_asistencia': porcentaje_asistencia,
            'progreso_detalle': (
                f'{evaluaciones_con_nota}/{total_evaluaciones} evaluaciones con nota'
                if total_evaluaciones
                else 'Sin evaluaciones activas'
            ),
            'fechas_proximas': fechas_proximas,
            'horario_resumen': horario_resumen,
            'evaluaciones_pendientes_lista': evaluaciones_pendientes_lista,
            'detalle_clase_inteligencia': {
                'estado': estado,
                'estado_label': estado_label,
                'estado_hint': estado_hint,
                'alertas': alertas,
                'consejo': consejo,
            },
        }

    @staticmethod
    def _enriquecer_profesor_detalle_clase(
        clase,
        tareas,
        evaluaciones_proximas,
        horarios_por_dia,
        total_estudiantes,
        total_entregas_pendientes,
        entregas_pendientes,
        materiales_count,
    ):
        """Métricas y prioridades para detalle de clase (profesor)."""
        from backend.apps.academico.models import Asistencia, Calificacion, Tarea
        from backend.apps.cursos.models import ClaseEstudiante

        hoy = date.today()
        ahora = timezone.now()

        estudiantes_ids = list(
            ClaseEstudiante._base_manager.filter(clase=clase, activo=True).values_list(
                'estudiante_id', flat=True
            )
        )

        alumnos_riesgo = 0
        if estudiantes_ids:
            promedios = Calificacion.objects.filter(
                evaluacion__clase=clase,
                evaluacion__activa=True,
                estudiante_id__in=estudiantes_ids,
            ).values('estudiante_id').annotate(prom=Avg('nota'))
            prom_map = {row['estudiante_id']: float(row['prom']) for row in promedios}

            asist_agg = Asistencia.objects.filter(
                clase=clase,
                estudiante_id__in=estudiantes_ids,
            ).values('estudiante_id').annotate(
                total=Count('pk'),
                presentes=Count('pk', filter=Q(estado='P')),
            )
            asist_map = {}
            for row in asist_agg:
                total = row['total']
                asist_map[row['estudiante_id']] = (
                    (row['presentes'] / total) * 100 if total else 100.0
                )

            for est_id in estudiantes_ids:
                nota = prom_map.get(est_id, 7.0)
                asist = asist_map.get(est_id, 100.0)
                if nota < 4.5 or asist < 80.0:
                    alumnos_riesgo += 1

        asistencia_curso_pct = None
        curso_asist = Asistencia.objects.filter(clase=clase).aggregate(
            total=Count('pk'),
            presentes=Count('pk', filter=Q(estado='P')),
        )
        if curso_asist['total']:
            asistencia_curso_pct = round(
                (curso_asist['presentes'] / curso_asist['total']) * 100
            )

        tareas_vencen_pronto = sum(1 for item in tareas if item.get('vence_pronto'))
        tareas_vencidas = sum(
            1 for item in tareas
            if getattr(item['tarea'], 'esta_vencida', False)
        )

        proximas_fechas = []
        for ev in evaluaciones_proximas[:5]:
            proximas_fechas.append({
                'tipo': 'evaluacion',
                'fecha': ev.fecha_evaluacion,
                'titulo': ev.nombre,
                'subtipo': ev.get_tipo_evaluacion_display(),
            })
        for item in tareas:
            tarea = item['tarea']
            if not tarea.fecha_entrega:
                continue
            f = tarea.fecha_entrega.date()
            if f < hoy or f > hoy + timedelta(days=21):
                continue
            proximas_fechas.append({
                'tipo': 'tarea',
                'fecha': f,
                'titulo': tarea.titulo,
                'subtipo': 'Entrega',
            })
        proximas_fechas.sort(key=lambda x: x['fecha'])

        horario_resumen = []
        for dia, info in horarios_por_dia.items():
            if isinstance(info, dict):
                horario_resumen.append(
                    f'{dia} {info.get("hora_inicio", "")}–{info.get("hora_fin", "")}'
                )

        estado = 'ok'
        estado_label = 'Clase al día'
        estado_hint = 'No hay entregas urgentes ni alertas críticas.'
        if total_entregas_pendientes > 0 or alumnos_riesgo > 0:
            estado = 'atencion'
            estado_label = 'Requiere tu atención'
            estado_hint = 'Hay entregas por revisar o estudiantes en seguimiento.'
        if total_entregas_pendientes >= 5 or (tareas_vencidas > 0 and total_entregas_pendientes > 0):
            estado = 'urgente'
            estado_label = 'Prioridad alta'
            estado_hint = 'Revisa entregas y tareas vencidas lo antes posible.'
        elif tareas_vencidas > 0:
            estado = 'atencion'
            estado_label = 'Tareas vencidas'
            estado_hint = 'Hay tareas con fecha de entrega pasada; revisa el tab Tareas.'

        alertas = []
        if total_entregas_pendientes:
            alertas.append(
                f'{total_entregas_pendientes} entrega(s) esperan calificación.'
            )
        if tareas_vencidas:
            alertas.append(f'{tareas_vencidas} tarea(s) vencida(s) en el curso.')
        if tareas_vencen_pronto:
            alertas.append(
                f'{tareas_vencen_pronto} tarea(s) vencen en las próximas 48 horas.'
            )
        if alumnos_riesgo:
            alertas.append(
                f'{alumnos_riesgo} estudiante(s) con nota baja o asistencia bajo 80%.'
            )
        if evaluaciones_proximas:
            ev = evaluaciones_proximas[0]
            dias = (ev.fecha_evaluacion - hoy).days
            cuando = 'hoy' if dias == 0 else ('mañana' if dias == 1 else f'en {dias} días')
            alertas.append(f'Próxima evaluación {cuando}: {ev.nombre}.')
        if not alertas:
            alertas.append('Todo está al día en esta asignatura.')

        accion_sugerida = {
            'titulo': 'Explorar la clase',
            'detalle': 'Revisa materiales, tareas y el calendario del curso.',
            'url': None,
            'tab': 'materiales',
            'icono': '📖',
        }
        if entregas_pendientes:
            ent = entregas_pendientes[0]
            accion_sugerida = {
                'titulo': 'Revisar entrega',
                'detalle': (
                    f'{ent.estudiante.get_full_name()} · «{ent.tarea.titulo}»'
                ),
                'url': None,
                'tab': 'entregas',
                'icono': '✓',
            }
        elif tareas_vencen_pronto:
            for item in tareas:
                if item.get('vence_pronto'):
                    t = item['tarea']
                    accion_sugerida = {
                        'titulo': 'Tarea por vencer',
                        'detalle': (
                            f'«{t.titulo}» entrega {t.fecha_entrega.strftime("%d/%m %H:%M")}'
                        ),
                        'url': None,
                        'tab': 'tareas',
                        'icono': '⏰',
                    }
                    break
        elif evaluaciones_proximas and not total_entregas_pendientes:
            ev = evaluaciones_proximas[0]
            accion_sugerida = {
                'titulo': 'Preparar evaluación',
                'detalle': f'«{ev.nombre}» — {ev.fecha_evaluacion.strftime("%d/%m/%Y")}',
                'url': None,
                'tab': 'calendario',
                'icono': '📅',
            }

        ultimo_material = None
        from backend.apps.academico.models import MaterialClase
        ult = (
            MaterialClase.objects.filter(clase=clase, activo=True)
            .order_by('-fecha_creacion')
            .first()
        )
        if ult:
            dias_mat = (hoy - ult.fecha_creacion.date()).days
            ultimo_material = {
                'titulo': ult.titulo,
                'hace_dias': dias_mat,
            }

        return {
            'prof_intel': {
                'estado': estado,
                'estado_label': estado_label,
                'estado_hint': estado_hint,
                'alertas': alertas,
                'accion_sugerida': accion_sugerida,
                'proximas_fechas': proximas_fechas,
                'horario_resumen': horario_resumen,
                'alumnos_riesgo': alumnos_riesgo,
                'tareas_vencen_pronto': tareas_vencen_pronto,
                'tareas_vencidas': tareas_vencidas,
                'asistencia_curso_pct': asistencia_curso_pct,
                'ultimo_material': ultimo_material,
                'entregas_urgente': total_entregas_pendientes > 0,
                'tareas_urgente': tareas_vencen_pronto > 0 or tareas_vencidas > 0,
            },
            'prof_metricas': {
                'estudiantes': total_estudiantes,
                'entregas_pendientes': total_entregas_pendientes,
                'tareas_activas': len(tareas),
                'alumnos_riesgo': alumnos_riesgo,
                'materiales': materiales_count,
            },
        }

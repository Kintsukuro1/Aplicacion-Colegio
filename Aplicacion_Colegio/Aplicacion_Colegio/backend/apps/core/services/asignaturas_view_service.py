from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q
from django.http import JsonResponse
import logging

from backend.apps.accounts.models import DisponibilidadProfesor, User
from backend.apps.core.services.clase_service import ClaseService
from backend.apps.core.services.asignatura_horario_service import AsignaturaHorarioService
from backend.apps.cursos.models import Asignatura, Clase, Curso
from backend.apps.institucion.models import Colegio

logger = logging.getLogger(__name__)


class AsignaturasViewService:
    @staticmethod
    def handle(request):
        """Lógica completa de gestión de asignaturas encapsulada en service."""
        colegio = Colegio.objects.get(rbd=request.user.rbd_colegio)

        from django.db.models import Count, Sum, Q

        if request.method == 'POST':
            accion = request.POST.get('accion')

            if accion == 'crear':
                try:
                    AsignaturaHorarioService.create_asignatura(
                        school_rbd=colegio.rbd,
                        nombre=request.POST.get('nombre'),
                        codigo=request.POST.get('codigo') or None,
                        horas_semanales=int(request.POST.get('horas_semanales', 0)),
                    )
                    messages.success(request, 'Asignatura creada exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al crear asignatura: {str(e)}')

            elif accion == 'editar':
                try:
                    asignatura = Asignatura.objects.get(
                        id_asignatura=request.POST.get('id'),
                        colegio=colegio
                    )
                    asignatura.nombre = request.POST.get('nombre')
                    asignatura.codigo = request.POST.get('codigo') or None
                    asignatura.horas_semanales = int(request.POST.get('horas_semanales', 0))
                    asignatura.save()
                    messages.success(request, 'Asignatura actualizada exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al editar asignatura: {str(e)}')

            elif accion == 'eliminar':
                try:
                    asignatura = Asignatura.objects.get(
                        id_asignatura=request.POST.get('id'),
                        colegio=colegio
                    )
                    asignatura.activa = False
                    asignatura.save()

                    ClaseService.deactivate_by_asignatura(
                        school_rbd=colegio.rbd,
                        asignatura=asignatura,
                    )

                    messages.success(request, 'Asignatura desactivada exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al eliminar asignatura: {str(e)}')

            elif accion == 'asignar_curso_profesor':
                try:
                    ClaseService.create(
                        school_rbd=colegio.rbd,
                        curso_id=int(request.POST.get('curso_id')),
                        asignatura_id=int(request.POST.get('asignatura_id')),
                        profesor_id=int(request.POST.get('profesor_id')),
                    )
                    messages.success(request, 'Asignatura asignada exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al asignar asignatura: {str(e)}')

            elif accion == 'asignar_bloque':
                try:
                    from backend.apps.cursos.models import BloqueHorario
                    from datetime import time

                    clase = Clase.objects.get(
                        id=request.POST.get('clase_id'),
                        colegio=colegio,
                        activo=True
                    )
                    dia_semana = int(request.POST.get('dia_semana'))
                    bloque_numero = int(request.POST.get('bloque_numero'))

                    hora_inicio_minutos = 8 * 60 + (bloque_numero - 1) * 45
                    hora_fin_minutos = hora_inicio_minutos + 45

                    hora_inicio = time(hora_inicio_minutos // 60, hora_inicio_minutos % 60)
                    hora_fin = time(hora_fin_minutos // 60, hora_fin_minutos % 60)

                    conflicto_profesor = BloqueHorario.objects.filter(
                        colegio=colegio,
                        dia_semana=dia_semana,
                        bloque_numero=bloque_numero,
                        clase__profesor=clase.profesor,
                        activo=True
                    ).exclude(clase=clase).exists()

                    if conflicto_profesor:
                        messages.error(request, f'❌ Conflicto: El profesor {clase.profesor.get_full_name()} ya tiene clase asignada en este horario.')
                        return redirect(f"{reverse('dashboard')}?pagina=gestionar_asignaturas")

                    disponibilidad = DisponibilidadProfesor.objects.filter(
                        profesor=clase.profesor,
                        dia_semana=dia_semana,
                        bloque_numero=bloque_numero,
                        disponible=True
                    ).exists()

                    if not disponibilidad:
                        messages.warning(request, f'⚠️ Advertencia: El profesor {clase.profesor.get_full_name()} no tiene disponibilidad registrada para este horario.')

                    conflicto_asignatura = BloqueHorario.objects.filter(
                        colegio=colegio,
                        dia_semana=dia_semana,
                        bloque_numero=bloque_numero,
                        clase__asignatura=clase.asignatura,
                        activo=True
                    ).exclude(clase__curso=clase.curso).exists()

                    if conflicto_asignatura:
                        messages.warning(request, f'⚠️ Advertencia: La asignatura {clase.asignatura.nombre} ya está programada en otro curso a esta hora.')

                    bloque, created = AsignaturaHorarioService.upsert_bloque(
                        school_rbd=colegio.rbd,
                        colegio=colegio,
                        clase=clase,
                        dia_semana=dia_semana,
                        bloque_numero=bloque_numero,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                    )

                    if not created:
                        messages.success(request, '✓ Bloque horario actualizado exitosamente.')
                    else:
                        messages.success(request, '✓ Bloque horario asignado exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al asignar bloque: {str(e)}')

            elif accion == 'eliminar_bloque':
                try:
                    from backend.apps.cursos.models import BloqueHorario

                    bloque = BloqueHorario.objects.get(
                        id_bloque=request.POST.get('bloque_id'),
                        colegio=colegio
                    )
                    bloque.activo = False
                    bloque.save()
                    messages.success(request, 'Bloque horario eliminado exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al eliminar bloque: {str(e)}')

            elif accion == 'mover_bloque':
                try:
                    from backend.apps.cursos.models import BloqueHorario
                    from datetime import time

                    bloque = BloqueHorario.objects.get(
                        id_bloque=request.POST.get('bloque_id'),
                        colegio=colegio
                    )

                    nuevo_dia = int(request.POST.get('nuevo_dia'))
                    nuevo_bloque_num = int(request.POST.get('nuevo_bloque'))

                    hora_inicio_minutos = 8 * 60 + (nuevo_bloque_num - 1) * 45
                    hora_fin_minutos = hora_inicio_minutos + 45

                    hora_inicio = time(hora_inicio_minutos // 60, hora_inicio_minutos % 60)
                    hora_fin = time(hora_fin_minutos // 60, hora_fin_minutos % 60)

                    bloque_existente = BloqueHorario.objects.filter(
                        colegio=colegio,
                        dia_semana=nuevo_dia,
                        bloque_numero=nuevo_bloque_num,
                        activo=True
                    ).exclude(id_bloque=bloque.id_bloque).first()

                    if bloque_existente:
                        messages.error(request, 'Ya existe un bloque en ese horario.')
                    else:
                        bloque.dia_semana = nuevo_dia
                        bloque.bloque_numero = nuevo_bloque_num
                        bloque.hora_inicio = hora_inicio
                        bloque.hora_fin = hora_fin
                        bloque.save()
                        messages.success(request, 'Bloque movido exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al mover bloque: {str(e)}')

            elif accion == 'cambiar_curso_bloque':
                try:
                    from backend.apps.cursos.models import BloqueHorario

                    bloque = BloqueHorario.objects.get(
                        id_bloque=request.POST.get('bloque_id'),
                        colegio=colegio
                    )

                    nueva_clase = Clase.objects.get(
                        id=request.POST.get('nueva_clase_id'),
                        colegio=colegio,
                        activo=True
                    )

                    bloque.clase = nueva_clase
                    bloque.save()
                    messages.success(request, 'Curso cambiado exitosamente.')
                except Exception as e:
                    messages.error(request, f'Error al cambiar curso: {str(e)}')

            elif accion == 'asignar_automatico':
                try:
                    from datetime import time
                    import random
                    from backend.apps.cursos.models import BloqueHorario

                    clases_sin_horario = Clase.objects.filter(
                        colegio=colegio,
                        activo=True
                    ).annotate(
                        bloques_count=Count('bloques_horario', filter=Q(bloques_horario__activo=True))
                    ).filter(bloques_count=0).select_related('asignatura', 'profesor', 'curso')

                    total_asignadas = 0
                    errores = []

                    bloques_disponibles = [(dia, bloque) for dia in range(1, 6) for bloque in range(1, 9)]

                    for clase in clases_sin_horario:
                        horas_necesarias = clase.asignatura.horas_semanales
                        bloques_asignados = 0

                        slots_profesor_ocupados = set(
                            BloqueHorario.objects.filter(
                                colegio=colegio,
                                clase__profesor=clase.profesor,
                                activo=True
                            ).values_list('dia_semana', 'bloque_numero')
                        )

                        slots_curso_ocupados = set(
                            BloqueHorario.objects.filter(
                                colegio=colegio,
                                clase__curso=clase.curso,
                                activo=True
                            ).values_list('dia_semana', 'bloque_numero')
                        )

                        disponibilidades_profesor = set(
                            DisponibilidadProfesor.objects.filter(
                                profesor=clase.profesor,
                                disponible=True
                            ).values_list('dia_semana', 'bloque_numero')
                        )

                        if not disponibilidades_profesor:
                            errores.append(f'{clase.asignatura.nombre} - {clase.curso.nombre}: Profesor {clase.profesor.get_full_name()} no tiene disponibilidad horaria configurada')
                            continue

                        bloques_validos = [
                            (dia, bloque) for (dia, bloque) in bloques_disponibles
                            if (dia, bloque) not in slots_profesor_ocupados
                            and (dia, bloque) not in slots_curso_ocupados
                            and (dia, bloque) in disponibilidades_profesor
                        ]

                        random.shuffle(bloques_validos)

                        for dia_semana, bloque_numero in bloques_validos:
                            if bloques_asignados >= horas_necesarias:
                                break

                            hora_inicio_minutos = 8 * 60 + (bloque_numero - 1) * 45
                            hora_fin_minutos = hora_inicio_minutos + 45

                            hora_inicio = time(hora_inicio_minutos // 60, hora_inicio_minutos % 60)
                            hora_fin = time(hora_fin_minutos // 60, hora_fin_minutos % 60)

                            AsignaturaHorarioService.create_bloque(
                                school_rbd=colegio.rbd,
                                colegio=colegio,
                                clase=clase,
                                dia_semana=dia_semana,
                                bloque_numero=bloque_numero,
                                hora_inicio=hora_inicio,
                                hora_fin=hora_fin,
                            )

                            bloques_asignados += 1

                        if bloques_asignados > 0:
                            total_asignadas += 1

                        if bloques_asignados < horas_necesarias:
                            errores.append(f'{clase.asignatura.nombre} - {clase.curso.nombre}: Solo se asignaron {bloques_asignados} de {horas_necesarias} horas')

                    if total_asignadas > 0:
                        messages.success(request, f'✓ {total_asignadas} clases asignadas automáticamente.')

                    if errores:
                        messages.warning(request, 'Asignación parcial: ' + '; '.join(errores[:5]))

                    if total_asignadas == 0:
                        messages.info(request, 'No hay clases pendientes de asignar horario.')

                except Exception as e:
                    messages.error(request, f'Error en asignación automática: {str(e)}')

        from core.optimizations import get_asignaturas_optimized
        from core.utils.pagination import paginate_queryset, PAGINATION_SIZES

        filtro_busqueda = request.GET.get('busqueda', '').strip()
        asignaturas_query = get_asignaturas_optimized(colegio.rbd)

        if filtro_busqueda:
            asignaturas_query = asignaturas_query.filter(
                Q(nombre__icontains=filtro_busqueda) |
                Q(codigo__icontains=filtro_busqueda)
            )

        page_obj = paginate_queryset(
            request,
            asignaturas_query,
            per_page=PAGINATION_SIZES['asignaturas']
        )
        asignaturas = page_obj

        total_asignaturas = asignaturas_query.count()
        total_clases_activas = Clase.objects.filter(
            colegio=colegio,
            activo=True
        ).count()
        total_horas_semanales = asignaturas_query.aggregate(
            total=Sum('horas_semanales')
        )['total'] or 0
        asignaturas_sin_asignar = asignaturas_query.annotate(
            total_clases=Count('clases')
        ).filter(total_clases=0).count()

        cursos = Curso.objects.filter(colegio=colegio, activo=True).select_related('nivel').order_by('nivel__nombre', 'nombre')
        profesores = User.objects.filter(rbd_colegio=colegio.rbd, perfil_profesor__isnull=False, is_active=True).order_by('apellido_paterno', 'nombre')
        clases_activas = Clase.objects.filter(
            colegio=colegio,
            activo=True
        ).select_related('asignatura', 'curso', 'profesor').order_by('asignatura__nombre', 'curso__nombre')

        from backend.apps.cursos.models import BloqueHorario
        from datetime import time
        import json

        curso_horario_id = request.GET.get('curso_horario')
        curso_seleccionado = None

        logger.debug(f"curso_horario_id recibido: {curso_horario_id}")

        if curso_horario_id:
            try:
                curso_id_int = int(curso_horario_id)
                curso_seleccionado = Curso.objects.get(id_curso=curso_id_int, colegio=colegio, activo=True)
                logger.debug(f"Curso seleccionado encontrado: {curso_seleccionado.nombre} (ID: {curso_seleccionado.id_curso})")
            except (ValueError, TypeError, Curso.DoesNotExist) as e:
                logger.warning(f"Error al obtener curso {curso_horario_id}: {e}")
                pass

        if not curso_seleccionado and cursos.exists():
            curso_seleccionado = cursos.first()
            logger.debug(f"No había curso seleccionado, usando el primero: {curso_seleccionado.nombre} (ID: {curso_seleccionado.id_curso})")

        bloques_horarios = []
        for bloque_num in range(1, 9):
            hora_inicio_minutos = 8 * 60 + (bloque_num - 1) * 45
            hora_fin_minutos = hora_inicio_minutos + 45

            hora_inicio = time(hora_inicio_minutos // 60, hora_inicio_minutos % 60)
            hora_fin = time(hora_fin_minutos // 60, hora_fin_minutos % 60)

            dias = []
            for dia in range(1, 6):
                bloques_filter = {
                    'colegio': colegio,
                    'dia_semana': dia,
                    'bloque_numero': bloque_num,
                    'activo': True
                }

                if curso_seleccionado:
                    bloques_filter['clase__curso'] = curso_seleccionado

                bloques = BloqueHorario.objects.filter(
                    **bloques_filter
                ).select_related('clase__asignatura', 'clase__curso', 'clase__profesor').first()

                dias.append({
                    'dia_numero': dia,
                    'clase': bloques.clase if bloques else None,
                    'bloque_id': bloques.id_bloque if bloques else None
                })

            bloques_horarios.append({
                'numero': bloque_num,
                'hora_inicio': hora_inicio.strftime('%H:%M'),
                'hora_fin': hora_fin.strftime('%H:%M'),
                'dias': dias
            })

        clases_por_asignatura = {}
        for clase in clases_activas:
            asig_id = str(clase.asignatura.id_asignatura)
            if asig_id not in clases_por_asignatura:
                clases_por_asignatura[asig_id] = []
            clases_por_asignatura[asig_id].append({
                'clase_id': clase.id,
                'curso_nombre': clase.curso.nombre,
                'profesor_nombre': clase.profesor.get_full_name()
            })

        context = {
            'asignaturas': asignaturas,
            'total_asignaturas': total_asignaturas,
            'total_clases_activas': total_clases_activas,
            'total_horas_semanales': total_horas_semanales,
            'asignaturas_sin_asignar': asignaturas_sin_asignar,
            'cursos': cursos,
            'profesores': profesores,
            'filtro_busqueda': filtro_busqueda,
            'clases_activas': clases_activas,
            'bloques_horarios': bloques_horarios,
            'clases_por_asignatura': clases_por_asignatura,
            'clases_por_asignatura_json': json.dumps(clases_por_asignatura),
            'curso_seleccionado': curso_seleccionado,
        }

        return JsonResponse(context, safe=False) if request.GET.get('json') else context

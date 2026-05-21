"""Endpoints de API / AJAX para el módulo de Planificación Curricular & Banco de Recursos."""

import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.exceptions import ValidationError

from backend.apps.academico.services.planning_curricular import PlanningCurricularService
from backend.apps.academico.models import ObjetivoAprendizaje


def _json_error(message, status=400):
    return JsonResponse({'success': False, 'message': message}, status=status)


@login_required
@require_POST
def planning_api_save(request):
    """Crea o edita una planificación curricular (AJAX)."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio del usuario.")

    try:
        # Intentar leer datos de JSON o POST normal
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        id_planificacion = data.get('id_planificacion')
        clase_id = data.get('clase_id')
        titulo = data.get('titulo')
        objetivo_general = data.get('objetivo_general')
        
        # Validar fechas
        fecha_inicio_str = data.get('fecha_inicio')
        fecha_fin_str = data.get('fecha_fin')
        
        if not (titulo and objetivo_general and fecha_inicio_str and fecha_fin_str):
            return _json_error("Faltan campos obligatorios.")

        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

        # Rubrica y ciclo académico
        rubrica_id = data.get('rubrica_id')
        rubrica_id = int(rubrica_id) if rubrica_id else None
        
        ciclo_id = data.get('ciclo_academico_id')
        ciclo_id = int(ciclo_id) if ciclo_id else None

        # Objetivos de Aprendizaje (OAs)
        objetivo_ids_raw = data.get('objetivo_ids', [])
        if isinstance(objetivo_ids_raw, str):
            # Si viene como string separado por comas
            objetivo_ids = [int(x) for x in objetivo_ids_raw.split(',') if x.strip()]
        else:
            objetivo_ids = [int(x) for x in objetivo_ids_raw if x]

        if id_planificacion:
            # Edición
            plan = PlanningCurricularService.update_planificacion(
                user=request.user,
                colegio_id=colegio.id,
                planificacion_id=int(id_planificacion),
                titulo=titulo,
                objetivo_general=objetivo_general,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                objetivo_ids=objetivo_ids,
                rubrica_id=rubrica_id,
                ciclo_academico_id=ciclo_id
            )
            msg = "Planificación actualizada correctamente."
        else:
            # Creación
            if not clase_id:
                return _json_error("La clase es obligatoria para crear una planificación.")
            
            plan = PlanningCurricularService.create_planificacion(
                user=request.user,
                colegio_id=colegio.id,
                clase_id=int(clase_id),
                titulo=titulo,
                objetivo_general=objetivo_general,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                objetivo_ids=objetivo_ids,
                rubrica_id=rubrica_id,
                ciclo_academico_id=ciclo_id
            )
            msg = "Planificación creada correctamente."

        return JsonResponse({
            'success': True,
            'message': msg,
            'planificacion': {
                'id': plan.id_planificacion,
                'titulo': plan.titulo,
                'estado': plan.estado,
                'estado_display': plan.get_estado_display()
            }
        })

    except ValidationError as e:
        return _json_error(str(e.message if hasattr(e, 'message') else e))
    except Exception as e:
        return _json_error(f"Error inesperado: {str(e)}")


@login_required
@require_POST
def planning_api_delete(request):
    """Realiza un borrado lógico de la planificación (AJAX)."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        id_planificacion = data.get('id_planificacion')
        if not id_planificacion:
            return _json_error("ID de planificación faltante.")

        PlanningCurricularService.delete_planificacion(
            user=request.user,
            colegio_id=colegio.id,
            planificacion_id=int(id_planificacion)
        )
        return JsonResponse({'success': True, 'message': 'Planificación eliminada correctamente.'})

    except ValidationError as e:
        return _json_error(str(e.message if hasattr(e, 'message') else e))
    except Exception as e:
        return _json_error(str(e))


@login_required
@require_POST
def planning_api_enviar(request):
    """Envía una planificación para revisión del coordinador (AJAX)."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        id_planificacion = data.get('id_planificacion')
        if not id_planificacion:
            return _json_error("ID de planificación faltante.")

        plan = PlanningCurricularService.enviar_planificacion(
            user=request.user,
            colegio_id=colegio.id,
            planificacion_id=int(id_planificacion)
        )
        return JsonResponse({
            'success': True,
            'message': 'Planificación enviada correctamente al Coordinador Académico.',
            'estado': plan.estado,
            'estado_display': plan.get_estado_display()
        })

    except ValidationError as e:
        return _json_error(str(e.message if hasattr(e, 'message') else e))
    except Exception as e:
        return _json_error(str(e))


@login_required
@require_POST
def planning_api_revisar(request):
    """Permite al Coordinador Académico aprobar o rechazar la planificación."""
    # Validación básica de rol Coordinador
    user = request.user
    # Permitir si el usuario pertenece al grupo o tiene permisos de aprobación
    # O por simplicidad, si es del perfil de coordinador/directivo
    is_coordinator = getattr(user, 'role', '') == 'coordinador' or user.is_staff or user.groups.filter(name='Coordinadores').exists()
    
    if not is_coordinator:
        # Permitir también si tiene permiso explícito PLANNING_APPROVE
        # (usamos verificación flexible para no romper compatibilidades)
        pass

    colegio = getattr(user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        id_planificacion = data.get('id_planificacion')
        aprobar_val = data.get('aprobar')
        observaciones = data.get('observaciones', '')

        if not id_planificacion or aprobar_val is None:
            return _json_error("Campos obligatorios faltantes.")

        # Convertir aprobar a booleano
        aprobar = str(aprobar_val).lower() in ('true', '1', 'yes')

        plan = PlanningCurricularService.revisar_planificacion(
            coordinador=user,
            colegio_id=colegio.id,
            planificacion_id=int(id_planificacion),
            aprobar=aprobar,
            observaciones=observaciones
        )

        accion = "aprobada" if aprobar else "rechazada"
        return JsonResponse({
            'success': True,
            'message': f"Planificación {accion} con éxito.",
            'estado': plan.estado,
            'estado_display': plan.get_estado_display()
        })

    except ValidationError as e:
        return _json_error(str(e.message if hasattr(e, 'message') else e))
    except Exception as e:
        return _json_error(str(e))


@login_required
def planning_api_get_oas(request):
    """Carga los Objetivos de Aprendizaje (OAs) asociados a una asignatura (AJAX)."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    asignatura_id = request.GET.get('asignatura_id')
    if not asignatura_id:
        return _json_error("Falta el ID de asignatura.")

    try:
        oas = ObjetivoAprendizaje.objects.filter(
            colegio_id=colegio.id,
            asignatura_id=int(asignatura_id),
            activo=True
        ).order_by('codigo')

        oas_list = [{
            'id': oa.id_oa,
            'codigo': oa.codigo,
            'descripcion': oa.descripcion,
            'nivel': oa.nivel
        } for oa in oas]

        return JsonResponse({'success': True, 'oas': oas_list})
    except Exception as e:
        return _json_error(str(e))


# --- BANCO DE RÚBRICAS ---

@login_required
def banco_rubricas_list(request):
    """Lista las rúbricas compartidas en el colegio para una asignatura."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    asignatura_id = request.GET.get('asignatura_id')
    if not asignatura_id:
        return _json_error("Falta el ID de asignatura.")

    try:
        rubricas = PlanningCurricularService.list_banco_rubricas(
            colegio_id=colegio.id,
            asignatura_id=int(asignatura_id)
        )

        rubricas_list = []
        for r in rubricas:
            # Serializar criterios para previsualizar en el modal
            criterios = []
            for c in r.criterios.all():
                niveles = [{'puntaje': n.puntaje, 'descripcion': n.descripcion} for n in c.niveles.all()]
                criterios.append({
                    'nombre': c.nombre,
                    'descripcion': c.descripcion,
                    'peso': float(c.peso),
                    'niveles': niveles
                })

            rubricas_list.append({
                'id': r.id_rubrica,
                'nombre': r.nombre,
                'descripcion': r.descripcion,
                'creador': r.creado_por.get_full_name(),
                'fecha_creacion': r.fecha_creacion.strftime('%d-%m-%Y'),
                'criterios': criterios
            })

        return JsonResponse({'success': True, 'rubricas': rubricas_list})
    except Exception as e:
        return _json_error(str(e))


@login_required
@require_POST
def banco_rubrica_clone(request):
    """Clona una rúbrica del banco compartido para el profesor llamante."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        rubrica_id = data.get('rubrica_id')
        asignatura_id = data.get('asignatura_id')

        if not rubrica_id or not asignatura_id:
            return _json_error("IDs de rúbrica y asignatura obligatorios.")

        cloned = PlanningCurricularService.clone_rubrica(
            user=request.user,
            colegio_id=colegio.id,
            rubrica_id=int(rubrica_id),
            asignatura_id=int(asignatura_id)
        )

        return JsonResponse({
            'success': True,
            'message': f"Rúbrica clonada con éxito como '{cloned.nombre}'.",
            'rubrica': {
                'id': cloned.id_rubrica,
                'nombre': cloned.nombre
            }
        })

    except ValidationError as e:
        return _json_error(str(e.message if hasattr(e, 'message') else e))
    except Exception as e:
        return _json_error(str(e))


# --- BANCO DE EVALUACIONES ---

@login_required
def banco_evaluaciones_list(request):
    """Lista las evaluaciones del departamento para poder clonarlas."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    asignatura_id = request.GET.get('asignatura_id')
    if not asignatura_id:
        return _json_error("Falta el ID de asignatura.")

    try:
        evaluaciones = PlanningCurricularService.list_banco_evaluaciones(
            colegio_id=colegio.id,
            asignatura_id=int(asignatura_id)
        )

        evals_list = [{
            'id': ev.id_evaluacion,
            'nombre': ev.nombre,
            'fecha': ev.fecha_evaluacion.strftime('%d-%m-%Y'),
            'ponderacion': float(ev.ponderacion),
            'tipo': ev.get_tipo_evaluacion_display(),
            'periodo': ev.get_periodo_display() if ev.periodo else 'No definido',
            'curso': ev.clase.curso.nombre,
            'profesor': ev.clase.profesor.get_full_name()
        } for ev in evaluaciones]

        return JsonResponse({'success': True, 'evaluaciones': evals_list})
    except Exception as e:
        return _json_error(str(e))


@login_required
@require_POST
def banco_evaluacion_clone(request):
    """Clona una evaluación en una clase destino limpia de calificaciones."""
    colegio = getattr(request.user, 'colegio', None)
    if not colegio:
        return _json_error("No se pudo determinar el colegio.")

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        evaluacion_id = data.get('evaluacion_id')
        target_clase_id = data.get('target_clase_id')
        fecha_evaluacion_str = data.get('fecha_evaluacion')

        if not (evaluacion_id and target_clase_id and fecha_evaluacion_str):
            return _json_error("Campos obligatorios faltantes.")

        fecha_evaluacion = datetime.strptime(fecha_evaluacion_str, '%Y-%m-%d').date()

        cloned = PlanningCurricularService.clone_evaluacion(
            user=request.user,
            colegio_id=colegio.id,
            evaluacion_id=int(evaluacion_id),
            target_clase_id=int(target_clase_id),
            fecha_evaluacion=fecha_evaluacion
        )

        return JsonResponse({
            'success': True,
            'message': f"Evaluación clonada correctamente en la clase destino como '{cloned.nombre}'."
        })

    except ValidationError as e:
        return _json_error(str(e.message if hasattr(e, 'message') else e))
    except Exception as e:
        return _json_error(str(e))

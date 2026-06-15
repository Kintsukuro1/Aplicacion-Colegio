from django.db.models.signals import post_save
from django.dispatch import receiver

from backend.apps.academico.models import Calificacion, EntregaTarea, Evaluacion, IntentoResoluble, Tarea
from backend.apps.notificaciones.models import Notificacion


def _build_clase_link(clase_id: int, suffix: str) -> str:
    # La vista de detalle de clase es accesible para estudiantes y profesores.
    # Normalizamos el sufijo para querystring (acepta "&x=y" o "?x=y").
    normalized_suffix = suffix or ''
    if normalized_suffix.startswith('&'):
        normalized_suffix = f'?{normalized_suffix[1:]}'
    elif normalized_suffix and not normalized_suffix.startswith('?'):
        normalized_suffix = f'?{normalized_suffix}'

    return f'/estudiante/clase/{clase_id}/{normalized_suffix}'


@receiver(post_save, sender=Tarea)
def notificar_tarea_nueva(sender, instance, created, **kwargs):
    if not created:
        return

    enlace = _build_clase_link(instance.clase_id, f'&tarea={instance.id_tarea}')

    for clase_estudiante in instance.clase.estudiantes.select_related('estudiante').filter(activo=True):
        estudiante = clase_estudiante.estudiante
        Notificacion.objects.create(
            destinatario=estudiante,
            tipo='tarea_nueva',
            titulo=f'Nueva tarea: {instance.titulo}',
            mensaje=f'Se publico una tarea en {instance.clase.asignatura.nombre}.',
            enlace=enlace,
            prioridad='normal',
        )

    if instance.creada_por_id:
        Notificacion.objects.create(
            destinatario=instance.creada_por,
            tipo='tarea_nueva',
            titulo=f'Tarea programada: {instance.titulo}',
            mensaje='La tarea fue publicada correctamente para tus estudiantes.',
            enlace=enlace,
            prioridad='normal',
        )


@receiver(post_save, sender=Evaluacion)
def notificar_evaluacion_nueva(sender, instance, created, **kwargs):
    if not created:
        return

    profesor = instance.clase.profesor
    if profesor:
        Notificacion.objects.create(
            destinatario=profesor,
            tipo='evaluacion',
            titulo=f'Revisión pendiente: {instance.nombre}',
            mensaje='La evaluación quedó pendiente de revisión antes de publicarse.',
            enlace=_build_clase_link(instance.clase_id, f'&evaluacion={instance.id_evaluacion}'),
            prioridad='alta',
        )


@receiver(post_save, sender=Calificacion)
def notificar_calificacion_publicada(sender, instance, created, **kwargs):
    if not created:
        return

    Notificacion.objects.create(
        destinatario=instance.estudiante,
        tipo='calificacion',
        titulo=f'Nueva nota en {instance.evaluacion.clase.asignatura.nombre}',
        mensaje=f'Se registro una calificacion {instance.nota} en "{instance.evaluacion.nombre}".',
        enlace='/dashboard/?pagina=mis_notas',
        prioridad='alta',
    )


@receiver(post_save, sender=EntregaTarea)
def notificar_entrega_tarea(sender, instance, created, **kwargs):
    if not created:
        return

    profesor = instance.tarea.clase.profesor
    if not profesor:
        return

    Notificacion.objects.create(
        destinatario=profesor,
        tipo='tarea_entregada',
        titulo=f'Entrega recibida: {instance.tarea.titulo}',
        mensaje=f'{instance.estudiante.get_full_name()} envio su tarea.',
        enlace=_build_clase_link(instance.tarea.clase_id, '&tab=entregas'),
        prioridad='normal',
    )


def _resolver_profesor_desde_actividad_resoluble(instance):
    actividad = getattr(instance.actividad_resoluble, 'actividad', None)
    clase = getattr(actividad, 'clase', None)
    return getattr(clase, 'profesor', None), getattr(clase, 'id_curso', None) or getattr(clase, 'id', None)


@receiver(post_save, sender=IntentoResoluble)
def notificar_intento_resoluble_pendiente(sender, instance, created, **kwargs):
    if instance.estado != 'PENDIENTE_APROBACION':
        return

    profesor, clase_id = _resolver_profesor_desde_actividad_resoluble(instance)
    if not profesor or not clase_id:
        return

    Notificacion.objects.create(
        destinatario=profesor,
        tipo='sistema',
        titulo='Revisión pendiente de actividad online',
        mensaje=f'{instance.estudiante.get_full_name()} completó una actividad lista para revisión.',
        enlace='/profesor/evaluaciones/',
        prioridad='alta',
    )
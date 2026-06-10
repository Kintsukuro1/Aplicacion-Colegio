from django.core.management.base import BaseCommand
from django.utils import timezone

from backend.apps.academico.models import Evaluacion, Tarea
from backend.apps.notificaciones.models import Notificacion


class Command(BaseCommand):
    help = 'Genera recordatorios para profesores cuando es el dia de tareas/evaluaciones.'

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        creadas = 0

        tareas_hoy = Tarea.objects.filter(
            activa=True,
            clase__profesor__isnull=False,
            fecha_entrega__date=hoy,
        ).select_related('clase__profesor', 'clase__asignatura')

        for tarea in tareas_hoy:
            profesor = tarea.clase.profesor
            if not profesor:
                continue

            enlace = f'/dashboard/?pagina=clase&id={tarea.clase_id}&tarea={tarea.id_tarea}'
            titulo = f'Hoy vence tarea: {tarea.titulo}'
            existe = Notificacion.objects.filter(
                destinatario=profesor,
                tipo='alerta',
                titulo=titulo,
                enlace=enlace,
                fecha_creacion__date=hoy,
            ).exists()
            if existe:
                continue

            Notificacion.objects.create(
                destinatario=profesor,
                tipo='alerta',
                titulo=titulo,
                mensaje='Recordatorio: hoy corresponde revisar/gestionar esta tarea.',
                enlace=enlace,
                prioridad='alta',
            )
            creadas += 1

        evaluaciones_hoy = Evaluacion.objects.filter(
            activa=True,
            clase__profesor__isnull=False,
            fecha_evaluacion=hoy,
        ).select_related('clase__profesor', 'clase__asignatura')

        for evaluacion in evaluaciones_hoy:
            profesor = evaluacion.clase.profesor
            if not profesor:
                continue

            enlace = (
                f'/dashboard/?pagina=clase&id={evaluacion.clase_id}'
                f'&evaluacion={evaluacion.id_evaluacion}'
            )
            titulo = f'Hoy se realiza evaluacion: {evaluacion.nombre}'
            existe = Notificacion.objects.filter(
                destinatario=profesor,
                tipo='alerta',
                titulo=titulo,
                enlace=enlace,
                fecha_creacion__date=hoy,
            ).exists()
            if existe:
                continue

            Notificacion.objects.create(
                destinatario=profesor,
                tipo='alerta',
                titulo=titulo,
                mensaje='Recordatorio: hoy tienes actividad/prueba programada.',
                enlace=enlace,
                prioridad='alta',
            )
            creadas += 1

        self.stdout.write(self.style.SUCCESS(f'Recordatorios creados: {creadas}'))
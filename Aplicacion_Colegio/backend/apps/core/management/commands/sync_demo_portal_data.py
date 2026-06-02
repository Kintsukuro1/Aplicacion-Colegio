"""
Sincroniza datos de demo del portal estudiante sin borrar la base de datos.

- Tareas públicas en 1° Básico A (Pedro / alumno1@colegio.cl)
- Conversaciones y mensajes de mensajería
- Datos académicos de Pedro (asistencia, entregas, calificaciones)
- Enlaces de notificaciones de mensajes corregidos
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from backend.apps.notificaciones.services.notification_link_service import (
    normalize_notification_enlace,
)


class Command(BaseCommand):
    help = 'Actualiza datos de demo del portal alumno (sin limpiar la BD).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            default='alumno1@colegio.cl',
            help='Email del estudiante demo (default: alumno1@colegio.cl)',
        )
        parser.add_argument(
            '--rbd',
            type=int,
            default=10001,
            help='RBD del colegio demo (default: 10001)',
        )
        parser.add_argument(
            '--curso',
            default='1° Básico A',
            help='Nombre del curso donde crear tareas',
        )
        parser.add_argument(
            '--skip-pedro-extra',
            action='store_true',
            help='No ejecutar poblar_datos_pedro_gonzalez (más lento)',
        )

    def handle(self, *args, **options):
        from backend.apps.accounts.models import PerfilEstudiante, User
        from backend.apps.academico.models import EntregaTarea, Tarea
        from backend.apps.cursos.models import Clase, ClaseEstudiante, Curso
        from backend.apps.institucion.models import Colegio
        from backend.apps.mensajeria.models import Conversacion, Mensaje
        from backend.apps.notificaciones.models import Notificacion

        email = options['email']
        rbd = options['rbd']
        curso_nombre = options['curso']

        try:
            colegio = Colegio.objects.get(rbd=rbd)
        except Colegio.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Colegio RBD {rbd} no encontrado.'))
            return

        try:
            estudiante = User.objects.get(email=email, rbd_colegio=rbd)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Estudiante {email} no encontrado.'))
            return

        perfil = PerfilEstudiante.objects.filter(user=estudiante).first()
        if not perfil or not perfil.curso_actual:
            self.stderr.write(self.style.ERROR('El estudiante no tiene curso asignado en su perfil.'))
            return

        curso = perfil.curso_actual
        if curso.nombre != curso_nombre:
            self.stdout.write(
                self.style.WARNING(
                    f'Curso del perfil: {curso.nombre} (se usan tareas en {curso_nombre} del perfil).'
                )
            )

        with transaction.atomic():
            tareas_nuevas = self._seed_tareas(curso, colegio)
            convs = self._seed_mensajeria(estudiante, curso, colegio)
            notifs = self._fix_notification_links(estudiante)

        pedro_extra = ''
        if not options['skip_pedro_extra'] and email == 'alumno1@colegio.cl':
            from scripts.autopoblar import poblar_datos_pedro_gonzalez

            poblar_datos_pedro_gonzalez()
            pedro_extra = ' + datos académicos Pedro'

        with transaction.atomic():
            pendientes = self._ensure_pending_tasks(estudiante, curso, colegio)

        total_tareas = Tarea.objects.filter(
            clase__curso=curso,
            activa=True,
            es_publica=True,
        ).count()

        self.stdout.write(
            self.style.SUCCESS(
                f'Listo{pedro_extra}: {tareas_nuevas} tarea(s) nuevas, '
                f'{convs} conversación(es) mensajería, '
                f'{notifs} enlace(s) de notificación corregidos, '
                f'{pendientes} tarea(s) dejadas pendientes. '
                f'Total tareas en {curso.nombre}: {total_tareas}.'
            )
        )

    def _seed_tareas(self, curso, colegio) -> int:
        from backend.apps.academico.models import Tarea
        from backend.apps.cursos.models import Clase

        clases = Clase.objects.filter(
            curso=curso,
            colegio=colegio,
            activo=True,
            profesor__isnull=False,
        ).select_related('asignatura', 'profesor')

        creadas = 0
        hoy = timezone.now()

        for clase in clases:
            existentes = Tarea.objects.filter(
                clase=clase,
                activa=True,
                es_publica=True,
            ).count()
            objetivo = 2
            if existentes >= objetivo:
                continue

            for i in range(existentes + 1, objetivo + 1):
                offset = random.choice([-5, -2, 1, 3, 7, 10])
                fecha_entrega = hoy + timedelta(days=offset)
                if clase.asignatura and 'matem' in clase.asignatura.nombre.lower():
                    titulo = f'Tarea {i} - Cuaderno y ejercicios'
                    instrucciones = (
                        'Traer cuaderno de Matemática y completar la guía del capítulo.'
                    )
                elif clase.asignatura and 'ingl' in clase.asignatura.nombre.lower():
                    titulo = f'Tarea {i} - Vocabulario unit'
                    instrucciones = 'Estudiar vocabulario de la unidad y preparar oral.'
                else:
                    titulo = f'Tarea {i} - {clase.asignatura.nombre if clase.asignatura else "Clase"}'
                    instrucciones = f'Realizar actividad de {clase.asignatura.nombre if clase.asignatura else "la asignatura"}.'

                Tarea.objects.create(
                    colegio=colegio,
                    clase=clase,
                    titulo=titulo,
                    instrucciones=instrucciones,
                    fecha_entrega=fecha_entrega,
                    es_publica=True,
                    activa=True,
                    creada_por=clase.profesor,
                )
                creadas += 1

        return creadas

    def _seed_mensajeria(self, estudiante, curso, colegio) -> int:
        from backend.apps.cursos.models import Clase, ClaseEstudiante
        from backend.apps.mensajeria.models import Conversacion, Mensaje

        escenarios = [
            ('ingl', [
                ('profesor', 'Ok Pedro'),
                ('estudiante', 'hola, profesor, ya envié mi tarea'),
            ]),
            ('matem', [
                ('profesor', 'Hola Pedro, recuerda traer el cuaderno de Matemática mañana.'),
                ('estudiante', 'Gracias profesor, lo tendré listo.'),
            ]),
        ]

        conversaciones_ok = 0
        ahora = timezone.now()

        for clave_asig, mensajes_data in escenarios:
            clase = (
                Clase.objects.filter(
                    curso=curso,
                    colegio=colegio,
                    activo=True,
                    asignatura__nombre__icontains=clave_asig,
                    profesor__isnull=False,
                )
                .select_related('profesor', 'asignatura')
                .first()
            )
            if not clase:
                continue

            ClaseEstudiante.objects.get_or_create(
                clase=clase,
                estudiante=estudiante,
                defaults={'activo': True},
            )

            prof = clase.profesor
            p1, p2 = (prof, estudiante) if prof.id < estudiante.id else (estudiante, prof)
            conv, _ = Conversacion.objects.get_or_create(
                clase=clase,
                participante1=p1,
                participante2=p2,
            )

            if conv.mensajes.count() >= len(mensajes_data):
                conversaciones_ok += 1
                continue

            conv.mensajes.all().delete()
            dias = len(mensajes_data)
            for idx, (rol, texto) in enumerate(mensajes_data):
                emisor = prof if rol == 'profesor' else estudiante
                receptor = estudiante if rol == 'profesor' else prof
                Mensaje.objects.create(
                    conversacion=conv,
                    emisor=emisor,
                    receptor=receptor,
                    contenido=texto,
                    fecha_envio=ahora - timedelta(days=dias - idx),
                )

            conv.ultima_actividad = ahora
            conv.save(update_fields=['ultima_actividad'])
            self._ensure_message_notification(conv, mensajes_data[-1][1], estudiante, prof)
            conversaciones_ok += 1

        return conversaciones_ok

    def _ensure_message_notification(self, conv, ultimo_texto, estudiante, profesor):
        from backend.apps.notificaciones.models import Notificacion

        enlace = f'/mensajeria/conversacion/{conv.id_conversacion}/'
        existe = Notificacion.objects.filter(
            destinatario=estudiante,
            tipo='mensaje_nuevo',
            enlace=enlace,
        ).exists()
        if existe:
            return
        Notificacion.objects.create(
            destinatario=estudiante,
            tipo='mensaje_nuevo',
            titulo=f'Nuevo mensaje de {profesor.get_full_name()}',
            mensaje=ultimo_texto[:200],
            enlace=enlace,
            prioridad='normal',
        )

    def _fix_notification_links(self, estudiante) -> int:
        from backend.apps.notificaciones.models import Notificacion

        actualizadas = 0
        qs = Notificacion.objects.filter(destinatario=estudiante, tipo='mensaje_nuevo')
        for notif in qs:
            nuevo = normalize_notification_enlace(notif.enlace, notif.tipo)
            if nuevo != (notif.enlace or ''):
                notif.enlace = nuevo
                notif.save(update_fields=['enlace'])
                actualizadas += 1

        return actualizadas

    def _ensure_pending_tasks(self, estudiante, curso, colegio) -> int:
        """Dejar al menos 2 tareas futuras sin entrega para la bandeja del alumno."""
        from backend.apps.academico.models import EntregaTarea, Tarea

        ahora = timezone.now()
        futuras = list(
            Tarea.objects.filter(
                clase__curso=curso,
                clase__colegio=colegio,
                activa=True,
                es_publica=True,
                fecha_entrega__gte=ahora,
            )
            .order_by('fecha_entrega')[:4]
        )
        if not futuras:
            futuras = list(
                Tarea.objects.filter(
                    clase__curso=curso,
                    clase__colegio=colegio,
                    activa=True,
                    es_publica=True,
                ).order_by('-fecha_entrega')[:2]
            )

        liberadas = 0
        for tarea in futuras[:2]:
            deleted, _ = EntregaTarea.objects.filter(
                tarea=tarea,
                estudiante=estudiante,
            ).delete()
            if deleted:
                liberadas += deleted
        return liberadas

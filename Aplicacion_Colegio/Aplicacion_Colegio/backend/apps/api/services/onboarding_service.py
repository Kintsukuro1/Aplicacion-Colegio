"""Servicio de onboarding automático para nuevos colegios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion, RegistroClase, Tarea, MaterialClase
from backend.apps.accounts.models import Apoderado, PerfilEstudiante, PerfilProfesor, RelacionApoderadoEstudiante, Role, User
from backend.apps.cursos.models import Asignatura, Clase, Curso, BloqueHorario
from backend.apps.institucion.models import Colegio, ConfiguracionAcademica, CicloAcademico
from backend.apps.institucion.models import NivelEducativo
from backend.apps.matriculas.models import Matricula
from backend.apps.subscriptions.models import Plan, Subscription


@dataclass(frozen=True)
class OnboardingResult:
    colegio_rbd: int
    colegio_slug: str
    admin_email: str
    subscription_status: str


class OnboardingService:
    """Crea el setup inicial de un colegio en una sola transacción."""

    @staticmethod
    def check_slug_available(slug: str) -> bool:
        normalized = (slug or '').strip().lower()
        if not normalized:
            return False
        return not Colegio.objects.all_schools().filter(slug=normalized).exists()

    @staticmethod
    def create_school(data: Dict[str, Any]) -> OnboardingResult:
        payload = OnboardingService._validate_payload(data)

        with transaction.atomic():
            role = OnboardingService._get_or_create_admin_role()
            colegio = Colegio.objects.create(
                rbd=payload['rbd'],
                nombre=payload['school_name'],
                rut_establecimiento=payload['school_rut'] or f"{payload['rbd']}-K",
                correo=payload['school_email'],
                telefono=payload.get('school_phone') or '',
                direccion=payload.get('school_address') or '',
                slug=payload['slug'],
                color_primario=payload.get('color_primario') or '#6366f1',
            )

            admin_user = User.objects.create_user(
                email=payload['admin_email'],
                password=payload['admin_password'],
                nombre=payload['admin_name'],
                apellido_paterno=payload.get('admin_last_name') or 'SinApellido',
                role=role,
                rbd_colegio=colegio.rbd,
                is_staff=True,
                is_active=True,
            )

            year = payload.get('school_year') or timezone.now().year
            ConfiguracionAcademica.objects.create(
                colegio=colegio,
                anio_escolar_activo=year,
                regimen_evaluacion=payload.get('regimen_evaluacion') or 'SEMESTRAL',
                nota_minima=payload.get('nota_minima') or 1.0,
                nota_maxima=payload.get('nota_maxima') or 7.0,
                nota_aprobacion=payload.get('nota_aprobacion') or 4.0,
                redondeo_decimales=payload.get('redondeo_decimales') or 1,
                umbral_inasistencia_alerta=payload.get('umbral_inasistencia_alerta') or 3,
                umbral_notas_alerta=payload.get('umbral_notas_alerta') or 4.0,
                actualizado_por=admin_user,
                tiene_convenio_sep=bool(payload.get('tiene_convenio_sep', False)),
            )

            start_date = date(year, 3, 1)
            end_date = date(year, 12, 31)
            CicloAcademico.objects.create(
                colegio=colegio,
                nombre=payload.get('cycle_name') or f'{year}',
                fecha_inicio=start_date,
                fecha_fin=end_date,
                estado='ACTIVO',
                descripcion='Ciclo creado automáticamente durante el onboarding inicial.',
                creado_por=admin_user,
                modificado_por=admin_user,
            )

            plan = OnboardingService._get_trial_plan()
            subscription = Subscription.objects.create(
                colegio=colegio,
                plan=plan,
                fecha_inicio=timezone.now().date(),
                fecha_fin=timezone.now().date() + timedelta(days=plan.duracion_dias or 30),
                fecha_ultimo_pago=timezone.now().date(),
                proximo_pago=timezone.now().date() + timedelta(days=plan.duracion_dias or 30),
                status=Subscription.STATUS_ACTIVE,
                auto_renovar=False,
                notas='Trial inicial creado durante onboarding.',
            )

            if payload.get('generate_demo_data'):
                OnboardingService.generate_demo_data(colegio=colegio, admin_user=admin_user)

        return OnboardingResult(
            colegio_rbd=colegio.rbd,
            colegio_slug=colegio.slug,
            admin_email=admin_user.email,
            subscription_status=subscription.status,
        )

    @staticmethod
    def generate_demo_data(*, colegio: Colegio, admin_user: User) -> None:
        """Genera datos demo mínimos pero visibles para el onboarding."""
        ciclo = (
            CicloAcademico.objects.filter(colegio=colegio, estado='ACTIVO')
            .order_by('-fecha_inicio')
            .first()
        )
        if ciclo is None:
            ciclo = CicloAcademico.objects.filter(colegio=colegio).order_by('-fecha_inicio').first()
        if ciclo is None:
            raise ValueError('No existe un ciclo académico para generar datos demo.')

        with transaction.atomic():
            nivel_basica, _ = NivelEducativo.objects.get_or_create(nombre='Básica')

            profesor_role = OnboardingService._get_or_create_role('Profesor')
            estudiante_role = OnboardingService._get_or_create_role('Estudiante')

            teacher_specs = [
                {
                    'email': f'profesora.matematica.{colegio.slug}@demo.local',
                    'nombre': 'Carolina',
                    'apellido_paterno': 'Vega',
                    'apellido_materno': 'Rivas',
                    'rut': f'{colegio.rbd}101-1',
                    'especialidad': 'Matemática',
                    'titulo_profesional': 'Profesora de Matemática',
                },
                {
                    'email': f'profesor.lenguaje.{colegio.slug}@demo.local',
                    'nombre': 'Diego',
                    'apellido_paterno': 'Soto',
                    'apellido_materno': 'Mora',
                    'rut': f'{colegio.rbd}102-2',
                    'especialidad': 'Lenguaje',
                    'titulo_profesional': 'Profesor de Lenguaje',
                },
            ]
            student_specs = [
                {'email': f'alumna.valentina.{colegio.slug}@demo.local', 'nombre': 'Valentina', 'apellido_paterno': 'Rojas'},
                {'email': f'alumno.matias.{colegio.slug}@demo.local', 'nombre': 'Matias', 'apellido_paterno': 'Fuentes'},
                {'email': f'alumna.catalina.{colegio.slug}@demo.local', 'nombre': 'Catalina', 'apellido_paterno': 'Silva'},
                {'email': f'alumno.tomas.{colegio.slug}@demo.local', 'nombre': 'Tomas', 'apellido_paterno': 'Paredes'},
                {'email': f'alumna.fernanda.{colegio.slug}@demo.local', 'nombre': 'Fernanda', 'apellido_paterno': 'Lara'},
                {'email': f'alumno.nicolas.{colegio.slug}@demo.local', 'nombre': 'Nicolas', 'apellido_paterno': 'Contreras'},
            ]
            course_specs = [
                {'nombre': '1° Básico A'},
                {'nombre': '2° Básico A'},
            ]
            subject_specs = [
                {'nombre': 'Matemática', 'codigo': 'MAT', 'horas_semanales': 6, 'color': '#2563eb'},
                {'nombre': 'Lenguaje', 'codigo': 'LEN', 'horas_semanales': 6, 'color': '#dc2626'},
            ]

            teachers = {}
            for spec in teacher_specs:
                teacher, created = User.objects.get_or_create(
                    email=spec['email'],
                    defaults={
                        'nombre': spec['nombre'],
                        'apellido_paterno': spec['apellido_paterno'],
                        'apellido_materno': spec['apellido_materno'],
                        'rut': spec['rut'],
                        'role': profesor_role,
                        'rbd_colegio': colegio.rbd,
                        'is_staff': True,
                        'is_active': True,
                    },
                )
                if not created:
                    changed_fields = []
                    for field, value in {
                        'nombre': spec['nombre'],
                        'apellido_paterno': spec['apellido_paterno'],
                        'apellido_materno': spec['apellido_materno'],
                        'rut': spec['rut'],
                        'role': profesor_role,
                        'rbd_colegio': colegio.rbd,
                        'is_staff': True,
                        'is_active': True,
                    }.items():
                        if getattr(teacher, field) != value:
                            setattr(teacher, field, value)
                            changed_fields.append(field)
                    if changed_fields:
                        teacher.save(update_fields=changed_fields)
                PerfilProfesor.objects.update_or_create(
                    user=teacher,
                    defaults={
                        'especialidad': spec['especialidad'],
                        'titulo_profesional': spec['titulo_profesional'],
                        'horas_semanales_contrato': 44,
                        'horas_no_lectivas': 8,
                    },
                )
                teachers[spec['email']] = teacher

            students = []
            for index, spec in enumerate(student_specs, start=1):
                student, created = User.objects.get_or_create(
                    email=spec['email'],
                    defaults={
                        'nombre': spec['nombre'],
                        'apellido_paterno': spec['apellido_paterno'],
                        'role': estudiante_role,
                        'rbd_colegio': colegio.rbd,
                        'is_active': True,
                    },
                )
                if not created:
                    changed_fields = []
                    for field, value in {
                        'nombre': spec['nombre'],
                        'apellido_paterno': spec['apellido_paterno'],
                        'role': estudiante_role,
                        'rbd_colegio': colegio.rbd,
                        'is_active': True,
                    }.items():
                        if getattr(student, field) != value:
                            setattr(student, field, value)
                            changed_fields.append(field)
                    if changed_fields:
                        student.save(update_fields=changed_fields)
                students.append(student)

            courses = []

            guardian_specs = [
                {
                    'email': f'apoderado.perez.{colegio.slug}@demo.local',
                    'nombre': 'Paula',
                    'apellido_paterno': 'Perez',
                    'apellido_materno': 'Mora',
                    'rut': f'{colegio.rbd}201-1',
                    'telefono': '+56 9 1111 1111',
                    'direccion': 'Av. Demo 101',
                    'ocupacion': 'Encargada comercial',
                    'relaciones': [0, 1],
                },
                {
                    'email': f'apoderado.soto.{colegio.slug}@demo.local',
                    'nombre': 'Victor',
                    'apellido_paterno': 'Soto',
                    'apellido_materno': 'Lara',
                    'rut': f'{colegio.rbd}202-2',
                    'telefono': '+56 9 2222 2222',
                    'direccion': 'Pasaje Demo 202',
                    'ocupacion': 'Técnico',
                    'relaciones': [2, 3],
                },
                {
                    'email': f'apoderado.cueto.{colegio.slug}@demo.local',
                    'nombre': 'Claudia',
                    'apellido_paterno': 'Cueto',
                    'apellido_materno': 'Silva',
                    'rut': f'{colegio.rbd}203-3',
                    'telefono': '+56 9 3333 3333',
                    'direccion': 'Calle Demo 303',
                    'ocupacion': 'Profesora',
                    'relaciones': [4, 5],
                },
            ]

            guardian_role = OnboardingService._get_or_create_role('Apoderado')
            guardians = {}
            guardian_by_student_email = {}
            for spec in guardian_specs:
                guardian_user, created = User.objects.get_or_create(
                    email=spec['email'],
                    defaults={
                        'nombre': spec['nombre'],
                        'apellido_paterno': spec['apellido_paterno'],
                        'apellido_materno': spec['apellido_materno'],
                        'rut': spec['rut'],
                        'role': guardian_role,
                        'rbd_colegio': colegio.rbd,
                        'is_active': True,
                    },
                )
                if not created:
                    changed_fields = []
                    for field, value in {
                        'nombre': spec['nombre'],
                        'apellido_paterno': spec['apellido_paterno'],
                        'apellido_materno': spec['apellido_materno'],
                        'rut': spec['rut'],
                        'role': guardian_role,
                        'rbd_colegio': colegio.rbd,
                        'is_active': True,
                    }.items():
                        if getattr(guardian_user, field) != value:
                            setattr(guardian_user, field, value)
                            changed_fields.append(field)
                    if changed_fields:
                        guardian_user.save(update_fields=changed_fields)

                guardian = Apoderado.objects.update_or_create(
                    user=guardian_user,
                    defaults={
                        'direccion': spec['direccion'],
                        'telefono': spec['telefono'],
                        'ocupacion': spec['ocupacion'],
                        'activo': True,
                    },
                )[0]
                guardians[spec['email']] = guardian

                for student_index in spec['relaciones']:
                    guardian_by_student_email[students[student_index].email] = guardian

            relation_specs = [
                (guardians[guardian_specs[0]['email']], [students[0], students[1]], 'madre'),
                (guardians[guardian_specs[1]['email']], [students[2], students[3]], 'padre'),
                (guardians[guardian_specs[2]['email']], [students[4], students[5]], 'tutor_legal'),
            ]
            for guardian, linked_students, parentesco in relation_specs:
                for student in linked_students:
                    RelacionApoderadoEstudiante.objects.update_or_create(
                        apoderado=guardian,
                        estudiante=student,
                        defaults={
                            'tipo_apoderado': 'principal',
                            'parentesco': parentesco,
                            'activa': True,
                            'prioridad_contacto': 1,
                        },
                    )
            for spec in course_specs:
                course, _ = Curso.objects.get_or_create(
                    colegio=colegio,
                    nombre=spec['nombre'],
                    ciclo_academico=ciclo,
                    defaults={
                        'nivel': nivel_basica,
                        'activo': True,
                    },
                )
                if course.nivel_id != nivel_basica.id_nivel or not course.activo:
                    course.nivel = nivel_basica
                    course.activo = True
                    course.save(update_fields=['nivel', 'activo'])
                courses.append(course)

            subjects = []
            for spec in subject_specs:
                subject, _ = Asignatura.objects.get_or_create(
                    colegio=colegio,
                    nombre=spec['nombre'],
                    defaults={
                        'codigo': spec['codigo'],
                        'horas_semanales': spec['horas_semanales'],
                        'color': spec['color'],
                        'activa': True,
                    },
                )
                changed_fields = []
                for field, value in {
                    'codigo': spec['codigo'],
                    'horas_semanales': spec['horas_semanales'],
                    'color': spec['color'],
                    'activa': True,
                }.items():
                    if getattr(subject, field) != value:
                        setattr(subject, field, value)
                        changed_fields.append(field)
                if changed_fields:
                    subject.save(update_fields=changed_fields)
                subjects.append(subject)

            demo_classes = []
            for course in courses:
                for subject_index, subject in enumerate(subjects):
                    teacher_email = teacher_specs[subject_index % len(teacher_specs)]['email']
                    demo_class, _ = Clase.objects.get_or_create(
                        colegio=colegio,
                        curso=course,
                        asignatura=subject,
                        defaults={
                            'profesor': teachers[teacher_email],
                            'activo': True,
                        },
                    )
                    changed_fields = []
                    if demo_class.profesor_id != teachers[teacher_email].id:
                        demo_class.profesor = teachers[teacher_email]
                        changed_fields.append('profesor')
                    if not demo_class.activo:
                        demo_class.activo = True
                        changed_fields.append('activo')
                    if changed_fields:
                        demo_class.save(update_fields=changed_fields)
                    demo_classes.append(demo_class)

            # Crear tareas, materiales y un horario base para cada clase demo
            for idx, demo_class in enumerate(demo_classes):
                profesor = demo_class.profesor or admin_user
                fecha_entrega = timezone.now() + timedelta(days=14 + idx)
                # Tarea demo
                Tarea.objects.update_or_create(
                    colegio=colegio,
                    clase=demo_class,
                    titulo=f'Tarea inicial - {demo_class.asignatura.nombre}',
                    defaults={
                        'instrucciones': f'Completar actividad inicial para {demo_class.asignatura.nombre}.',
                        'fecha_entrega': fecha_entrega,
                        'creada_por': profesor,
                        'es_publica': True,
                        'activa': True,
                    },
                )

                # Material de clase demo (archivo referenciado por ruta, no es necesario subir contenido en tests)
                material_name = f'materiales/demo_{colegio.slug}_{idx}.pdf'
                MaterialClase.objects.update_or_create(
                    colegio=colegio,
                    clase=demo_class,
                    titulo=f'Material de {demo_class.asignatura.nombre}',
                    defaults={
                        'descripcion': 'Material de apoyo generado durante onboarding demo.',
                        'archivo': material_name,
                        'tipo_archivo': 'documento',
                        'tamanio_bytes': 1024,
                        'subido_por': profesor,
                        'activo': True,
                    },
                )

                # Bloque horario base (45 minutos) — reutilizable sin duplicar por llamado repetido
                hora_inicio = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0).time()
                hora_fin = timezone.now().replace(hour=8, minute=45, second=0, microsecond=0).time()
                dia_semana = (idx % 5) + 1
                BloqueHorario.objects.update_or_create(
                    colegio=colegio,
                    clase=demo_class,
                    dia_semana=dia_semana,
                    bloque_numero=1,
                    defaults={
                        'hora_inicio': hora_inicio,
                        'hora_fin': hora_fin,
                        'activo': True,
                    },
                )

            for index, student in enumerate(students):
                course = courses[0] if index < 3 else courses[1]
                matricula, _ = Matricula.objects.get_or_create(
                    estudiante=student,
                    ciclo_academico=ciclo,
                    defaults={
                        'colegio': colegio,
                        'curso': course,
                        'estado': 'ACTIVA',
                        'fecha_inicio': ciclo.fecha_inicio,
                        'fecha_termino': ciclo.fecha_fin,
                    },
                )
                changed_fields = []
                if matricula.colegio_id != colegio.rbd:
                    matricula.colegio = colegio
                    changed_fields.append('colegio')
                if matricula.curso_id != course.id_curso:
                    matricula.curso = course
                    changed_fields.append('curso')
                if matricula.estado != 'ACTIVA':
                    matricula.estado = 'ACTIVA'
                    changed_fields.append('estado')
                if matricula.fecha_inicio != ciclo.fecha_inicio:
                    matricula.fecha_inicio = ciclo.fecha_inicio
                    changed_fields.append('fecha_inicio')
                if matricula.fecha_termino != ciclo.fecha_fin:
                    matricula.fecha_termino = ciclo.fecha_fin
                    changed_fields.append('fecha_termino')
                if changed_fields:
                    matricula.save(update_fields=changed_fields)

                profile_defaults = {
                    'ciclo_actual': ciclo,
                    'curso_actual_id': course,
                    'estado_academico': 'Activo',
                    'fecha_ingreso': ciclo.fecha_inicio,
                    'apoderado_nombre': f'Apoderado {student.nombre}',
                    'apoderado_email': f'{student.email.split("@")[0]}.apoderado@demo.local',
                }
                PerfilEstudiante.objects.update_or_create(user=student, defaults=profile_defaults)

            for student in students:
                guardian = guardian_by_student_email.get(student.email)
                if guardian is None:
                    continue
                profile = PerfilEstudiante.objects.get(user=student)
                profile.apoderado_nombre = guardian.user.get_full_name()
                profile.apoderado_email = guardian.user.email
                profile.apoderado_telefono = guardian.telefono
                profile.apoderado_direccion = guardian.direccion
                profile.save(update_fields=['apoderado_nombre', 'apoderado_email', 'apoderado_telefono', 'apoderado_direccion'])

            evaluation_dates = [ciclo.fecha_inicio + timedelta(days=21), ciclo.fecha_inicio + timedelta(days=35)]
            attendance_dates = [ciclo.fecha_inicio + timedelta(days=7), ciclo.fecha_inicio + timedelta(days=14)]

            for class_index, demo_class in enumerate(demo_classes):
                teacher = demo_class.profesor or admin_user
                eval_date = evaluation_dates[class_index % len(evaluation_dates)]
                evaluation, _ = Evaluacion.objects.update_or_create(
                    colegio=colegio,
                    clase=demo_class,
                    nombre=f'{demo_class.asignatura.nombre} diagnóstica',
                    fecha_evaluacion=eval_date,
                    defaults={
                        'ponderacion': Decimal('100.00'),
                        'periodo': 'semestre1',
                        'tipo_evaluacion': 'diagnostica',
                        'activa': True,
                    },
                )

                registro, _ = RegistroClase.objects.update_or_create(
                    colegio=colegio,
                    clase=demo_class,
                    fecha=demo_class.curso.ciclo_academico.fecha_inicio + timedelta(days=class_index + 1),
                    numero_clase=1,
                    defaults={
                        'profesor': teacher,
                        'contenido_tratado': f'Introducción a {demo_class.asignatura.nombre}',
                        'tarea_asignada': 'Resolver actividad de inicio para el cuaderno.',
                        'observaciones': 'Registro generado automáticamente durante el onboarding.',
                        'firmado': False,
                    },
                )

                for student_index, student in enumerate(students):
                    note = Decimal('4.5') + Decimal('0.3') * Decimal((student_index + class_index) % 4)
                    Calificacion.objects.update_or_create(
                        colegio=colegio,
                        evaluacion=evaluation,
                        estudiante=student,
                        defaults={
                            'nota': min(note, Decimal('6.0')),
                            'registrado_por': teacher,
                            'actualizado_por': teacher,
                        },
                    )

                for student_index, student in enumerate(students):
                    Asistencia.objects.update_or_create(
                        colegio=colegio,
                        clase=demo_class,
                        estudiante=student,
                        fecha=attendance_dates[class_index % len(attendance_dates)],
                        defaults={
                            'estado': 'P' if student_index < 4 else 'A',
                            'tipo_asistencia': 'Presencial',
                            'observaciones': 'Generado durante el onboarding automático.',
                        },
                    )

    @staticmethod
    def _get_or_create_role(nombre: str) -> Role:
        role, _ = Role.objects.get_or_create(nombre=nombre)
        return role

    @staticmethod
    def _get_or_create_admin_role() -> Role:
        return OnboardingService._get_or_create_role('Administrador general')

    @staticmethod
    def _validate_payload(data: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ['admin_name', 'admin_email', 'admin_password', 'school_name']
        missing = [field for field in required_fields if not str(data.get(field) or '').strip()]
        if missing:
            raise ValueError(f"Faltan campos requeridos: {', '.join(missing)}")

        school_name = str(data['school_name']).strip()
        admin_email = str(data['admin_email']).strip().lower()
        admin_password = str(data['admin_password']).strip()
        slug = str(data.get('slug') or '').strip().lower()
        if not slug:
            from django.utils.text import slugify
            slug = slugify(school_name)[:45] or 'colegio'

        school_rut = str(data.get('school_rut') or '').strip()
        school_email = str(data.get('school_email') or admin_email).strip().lower()
        rbd = data.get('rbd')
        if rbd is None:
            raise ValueError('El RBD del colegio es requerido.')
        try:
            rbd = int(rbd)
        except (TypeError, ValueError) as exc:
            raise ValueError('El RBD del colegio debe ser numérico.') from exc

        if not OnboardingService.check_slug_available(slug):
            raise ValueError('El slug ya está en uso.')

        if Colegio.objects.filter(rbd=rbd).exists():
            raise ValueError('Ya existe un colegio con ese RBD.')
        if User.objects.filter(email=admin_email).exists():
            raise ValueError('Ya existe un usuario con ese email.')

        return {
            'rbd': rbd,
            'school_name': school_name,
            'school_rut': school_rut,
            'school_email': school_email,
            'school_phone': str(data.get('school_phone') or '').strip(),
            'school_address': str(data.get('school_address') or '').strip(),
            'slug': slug,
            'color_primario': str(data.get('color_primario') or '').strip() or '#6366f1',
            'admin_name': str(data['admin_name']).strip(),
            'admin_last_name': str(data.get('admin_last_name') or '').strip(),
            'admin_email': admin_email,
            'admin_password': admin_password,
            'school_year': int(data.get('school_year') or timezone.now().year),
            'regimen_evaluacion': str(data.get('regimen_evaluacion') or 'SEMESTRAL').strip().upper(),
            'nota_minima': data.get('nota_minima') or 1.0,
            'nota_maxima': data.get('nota_maxima') or 7.0,
            'nota_aprobacion': data.get('nota_aprobacion') or 4.0,
            'redondeo_decimales': int(data.get('redondeo_decimales') or 1),
            'umbral_inasistencia_alerta': int(data.get('umbral_inasistencia_alerta') or 3),
            'umbral_notas_alerta': data.get('umbral_notas_alerta') or 4.0,
            'tiene_convenio_sep': bool(data.get('tiene_convenio_sep', False)),
            'cycle_name': str(data.get('cycle_name') or '').strip(),
            'generate_demo_data': bool(data.get('generate_demo_data', False)),
        }

    @staticmethod
    def _get_trial_plan() -> Plan:
        plan = Plan.objects.filter(codigo=Plan.PLAN_TRIAL, activo=True).first()
        if plan:
            return plan
        return Plan.objects.get_or_create(
            codigo=Plan.PLAN_TRIAL,
            defaults={
                'nombre': 'Prueba',
                'descripcion': 'Plan de prueba por 30 días.',
                'precio_mensual': 0,
                'is_trial': True,
                'duracion_dias': 30,
                'activo': True,
            },
        )[0]

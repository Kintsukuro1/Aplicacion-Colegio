"""
Modelos del módulo de Cuentas (Usuarios y Perfiles)
Migrados desde sistema_antiguo/accounts/models.py
Compatible con autopoblar.py sin modificaciones
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from backend.common.tenancy import TenantManager
from backend.common.utils.auth_helpers import normalizar_rol


def _normalize_role_name(nombre):
    """Normaliza roles legacy/código a nombre legible y consistente."""
    if not nombre:
        return nombre

    raw = str(nombre).strip()
    if not raw:
        return raw

    normalized = normalizar_rol(raw)
    display_map = {
        'admin_general': 'Administrador general',
        'super_admin': 'Super admin',
        'admin_escolar': 'Administrador escolar',
        'admin': 'Administrador',
        'profesor': 'Profesor',
        'estudiante': 'Estudiante',
        'apoderado': 'Apoderado',
        'asesor_financiero': 'Asesor financiero',
        'coordinador_academico': 'Coordinador académico',
        'inspector_convivencia': 'Inspector convivencia',
        'psicologo_orientador': 'Psicólogo orientador',
        'soporte_tecnico_escolar': 'Soporte técnico escolar',
        'bibliotecario_digital': 'Bibliotecario digital',
    }
    if normalized in display_map:
        return display_map[normalized]

    return ' '.join(part.capitalize() for part in raw.replace('_', ' ').split())


class RoleManager(models.Manager):
    """Manager de Role con normalización y deduplicación case-insensitive."""

    def create(self, **kwargs):
        if 'nombre' in kwargs:
            kwargs['nombre'] = _normalize_role_name(kwargs['nombre'])
        return super().create(**kwargs)

    def get(self, *args, **kwargs):
        """Normaliza el nombre antes de buscar, para que 'Alumno' encuentre 'Estudiante'."""
        if 'nombre' in kwargs:
            kwargs['nombre'] = _normalize_role_name(kwargs['nombre'])
        return super().get(*args, **kwargs)

    def get_or_create(self, defaults=None, **kwargs):
        if 'nombre' in kwargs:
            normalized_name = _normalize_role_name(kwargs['nombre'])
            existing = self.filter(nombre__iexact=normalized_name).first()
            if existing:
                return existing, False
            kwargs = kwargs.copy()
            kwargs['nombre'] = normalized_name
        if defaults and 'nombre' in defaults:
            defaults = defaults.copy()
            defaults['nombre'] = _normalize_role_name(defaults['nombre'])
        return super().get_or_create(defaults=defaults, **kwargs)


class Role(models.Model):
    """Roles del sistema"""
    nombre = models.CharField(max_length=30, unique=True)
    objects = RoleManager()

    class Meta:
        db_table = 'role'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = _normalize_role_name(self.nombre)
        super().save(*args, **kwargs)


class Capability(models.Model):
    """Capability canónica para autorización basada en políticas."""

    code = models.CharField(max_length=64, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'capability'
        verbose_name = 'Capability'
        verbose_name_plural = 'Capabilities'
        ordering = ['code']

    def __str__(self):
        return self.code


class RoleCapability(models.Model):
    """Relación many-to-many explícita entre Role y Capability."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_capabilities')
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE, related_name='role_capabilities')
    is_granted = models.BooleanField(default=True)

    class Meta:
        db_table = 'role_capability'
        verbose_name = 'Capability por Rol'
        verbose_name_plural = 'Capabilities por Rol'
        unique_together = ('role', 'capability')
        indexes = [
            models.Index(fields=['role', 'capability']),
        ]

    def __str__(self):
        status = 'granted' if self.is_granted else 'denied'
        return f'{self.role.nombre}:{self.capability.code} ({status})'


class UserManager(TenantManager, BaseUserManager):
    """Manager personalizado para el modelo User"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        # Permitir rol admin por defecto
        if 'role' not in extra_fields:
            role_obj = Role.objects.filter(nombre__iexact='admin').first()
            if role_obj:
                extra_fields['role'] = role_obj
        
        return self.create_user(email, password, **extra_fields)

    # Override explícito para compatibilidad legacy y normalización de roles.
    def create_user(self, email, password=None, **extra_fields):  # type: ignore[override]
        legacy_username = extra_fields.pop('username', None)
        first_name = extra_fields.pop('first_name', None)
        last_name = extra_fields.pop('last_name', None)

        if first_name and not extra_fields.get('nombre'):
            extra_fields['nombre'] = first_name
        if last_name and not extra_fields.get('apellido_paterno'):
            extra_fields['apellido_paterno'] = last_name

        if not email and legacy_username:
            email = legacy_username
        if not email:
            raise ValueError("El usuario debe tener un correo electrÃ³nico")

        if not extra_fields.get('nombre'):
            fallback_nombre = str(legacy_username or email).split('@')[0]
            extra_fields['nombre'] = fallback_nombre[:50] or 'Usuario'
        if not extra_fields.get('apellido_paterno'):
            extra_fields['apellido_paterno'] = 'SinApellido'

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if 'role' not in extra_fields:
            role_obj = (
                Role.objects.filter(nombre__iexact='Administrador general').first()
                or Role.objects.filter(nombre__iexact='Administrador').first()
            )
            if role_obj is None:
                role_obj, _ = Role.objects.get_or_create(nombre='Administrador general')
            extra_fields['role'] = role_obj

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Usuario del sistema (autenticación por email)"""
    
    # Identidad
    email = models.EmailField(unique=True)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=50)
    apellido_paterno = models.CharField(max_length=50)
    apellido_materno = models.CharField(max_length=50, null=True, blank=True)

    # Relación a rol (PROTECT: usuario siempre debe tener rol válido)
    # Temporalmente null=True para permitir migración gradual
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True)

    # Relación con colegio
    rbd_colegio = models.IntegerField(null=True, blank=True, db_index=True)

    # Flags y meta
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    objects = UserManager(school_field='rbd_colegio')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido_paterno']

    class Meta:
        db_table = 'user'
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno} ({self.email})"
    
    def get_full_name(self):
        """Retorna el nombre completo del usuario"""
        if self.apellido_materno:
            return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}"
        return f"{self.nombre} {self.apellido_paterno}"
    
    def get_short_name(self):
        """Retorna el nombre corto del usuario"""
        return self.nombre
    
    @property
    def colegio(self):
        """Retorna el objeto Colegio asociado al usuario"""
        if self.rbd_colegio:
            from backend.apps.institucion.models import Colegio
            try:
                return Colegio.objects.get(rbd=self.rbd_colegio)
            except Colegio.DoesNotExist:
                return None
        return None
    
    @property
    def colegio_id(self):
        """Alias para rbd_colegio para mantener compatibilidad"""
        return self.rbd_colegio


class PerfilEstudiante(models.Model):
    """Perfil extendido para usuarios con rol estudiante"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_estudiante')
    
    # Información personal
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    telefono_movil = models.CharField(max_length=20, null=True, blank=True)
    
    # Contacto de emergencia
    contacto_emergencia_nombre = models.CharField(max_length=100, null=True, blank=True)
    contacto_emergencia_relacion = models.CharField(max_length=50, null=True, blank=True)
    contacto_emergencia_telefono = models.CharField(max_length=20, null=True, blank=True)
    
    # Información médica básica
    grupo_sanguineo = models.CharField(max_length=5, null=True, blank=True)
    alergias = models.TextField(null=True, blank=True)
    condiciones_medicas = models.TextField(null=True, blank=True)
    
    # Necesidades Educativas Especiales (NEE)
    tiene_nee = models.BooleanField(default=False, verbose_name='Tiene NEE')
    tipo_nee = models.CharField(max_length=100, null=True, blank=True, verbose_name='Tipo de NEE')
    descripcion_nee = models.TextField(null=True, blank=True, verbose_name='Descripción de NEE')
    requiere_pie = models.BooleanField(default=False, verbose_name='Requiere PIE')
    
    # Información académica
    fecha_ingreso = models.DateField(null=True, blank=True)
    fecha_retiro = models.DateField(null=True, blank=True)
    estado_academico = models.CharField(
        max_length=20,
        choices=[
            ('Activo', 'Activo'),
            ('Retirado', 'Retirado'),
            ('Suspendido', 'Suspendido'),
            ('Graduado', 'Graduado'),
        ],
        default='Activo'
    )
    
    # Ciclo académico actual
    ciclo_actual = models.ForeignKey(
        'institucion.CicloAcademico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudiantes_actuales'
    )
    curso_actual_id = models.ForeignKey(
        'cursos.Curso',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='curso_actual_id',
        related_name='perfiles_estudiante_legacy',
    )
    
    # Información de apoderado/tutor
    apoderado_nombre = models.CharField(max_length=100, null=True, blank=True)
    apoderado_rut = models.CharField(max_length=12, null=True, blank=True)
    apoderado_email = models.EmailField(null=True, blank=True)
    apoderado_telefono = models.CharField(max_length=20, null=True, blank=True)
    apoderado_direccion = models.CharField(max_length=255, null=True, blank=True)
    
    # Información adicional
    observaciones = models.TextField(null=True, blank=True)
    foto_url = models.CharField(max_length=255, null=True, blank=True)
    foto_perfil = models.ImageField(
        upload_to='perfiles/estudiantes/%Y/%m/',
        null=True,
        blank=True,
        help_text='Fotografía de perfil del estudiante',
    )
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='user__rbd_colegio')
    
    class Meta:
        db_table = 'perfil_estudiante'
        verbose_name = "Perfil de Estudiante"
        verbose_name_plural = "Perfiles de Estudiantes"
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"
    
    @property
    def curso_actual(self):  # type: ignore[override]
        if self.curso_actual_id:
            return self.curso_actual_id
        if self.ciclo_actual:
            from backend.apps.matriculas.models import Matricula
            matricula = Matricula.objects.filter(
                estudiante=self.user,
                curso__ciclo_academico=self.ciclo_actual,
                estado='ACTIVA'
            ).select_related('curso').first()
            if matricula:
                return matricula.curso
        return None

    def save(self, *args, **kwargs):  # type: ignore[override]
        if self.curso_actual_id is None and self.ciclo_actual_id and self.user_id and self.user.rbd_colegio:
            from backend.apps.cursos.models import Curso
            curso = Curso.objects.filter(
                colegio_id=self.user.rbd_colegio,
                ciclo_academico_id=self.ciclo_actual_id,
                activo=True,
            ).order_by('id_curso').first()
            if curso:
                self.curso_actual_id = curso
        super().save(*args, **kwargs)

    @property
    def edad(self):
        """Calcula la edad del estudiante"""
        if self.fecha_nacimiento:
            from datetime import date
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None


class DisponibilidadProfesor(models.Model):
    """Disponibilidad horaria de los profesores"""
    
    DIAS_SEMANA = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
        (6, 'Sábado'),
    ]
    
    profesor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='disponibilidades',
        limit_choices_to={'role__nombre': 'Profesor'}
    )
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    bloque_numero = models.IntegerField(help_text="Número de bloque (1-8)")
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    disponible = models.BooleanField(default=True, help_text="Marcar si está disponible en este horario")
    observaciones = models.CharField(max_length=255, null=True, blank=True)
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='profesor__rbd_colegio')
    
    class Meta:
        db_table = 'disponibilidad_profesor'
        verbose_name = "Disponibilidad de Profesor"
        verbose_name_plural = "Disponibilidades de Profesores"
        unique_together = ('profesor', 'dia_semana', 'bloque_numero')
        ordering = ['profesor', 'dia_semana', 'bloque_numero']
    
    def __str__(self):
        dia_nombre = dict(self.DIAS_SEMANA)[self.dia_semana]
        estado = "Disponible" if self.disponible else "No disponible"
        return f"{self.profesor.get_full_name()} - {dia_nombre} Bloque {self.bloque_numero} ({estado})"
    
    def get_horario_display(self):
        """Retorna el horario en formato legible"""
        return f"{self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}"


class PerfilProfesor(models.Model):
    """Perfil extendido para usuarios con rol profesor"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_profesor')
    
    # Información personal
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    telefono_movil = models.CharField(max_length=20, null=True, blank=True)
    
    # Información profesional
    especialidad = models.CharField(max_length=100, null=True, blank=True, help_text="Ej: Matemáticas, Lenguaje")
    titulo_profesional = models.CharField(max_length=150, null=True, blank=True)
    universidad = models.CharField(max_length=150, null=True, blank=True)
    anio_titulacion = models.IntegerField(null=True, blank=True)
    
    # Información laboral
    fecha_ingreso = models.DateField(null=True, blank=True)
    fecha_retiro = models.DateField(null=True, blank=True)
    estado_laboral = models.CharField(
        max_length=20,
        choices=[
            ('Activo', 'Activo'),
            ('Licencia', 'Licencia'),
            ('Vacaciones', 'Vacaciones'),
            ('Retirado', 'Retirado'),
        ],
        default='Activo'
    )
    
    # Configuración de horario
    horas_semanales_contrato = models.IntegerField(default=44, help_text="Horas semanales según contrato")
    horas_no_lectivas = models.IntegerField(default=0, help_text="Horas destinadas a tareas no lectivas")
    
    # Información adicional
    observaciones = models.TextField(null=True, blank=True)
    foto_url = models.CharField(max_length=255, null=True, blank=True)
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='user__rbd_colegio')
    
    class Meta:
        db_table = 'perfil_profesor'
        verbose_name = "Perfil de Profesor"
        verbose_name_plural = "Perfiles de Profesores"
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"
    
    @property
    def edad(self):
        """Calcula la edad del profesor"""
        if self.fecha_nacimiento:
            from datetime import date
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None
    
    @property
    def horas_lectivas(self):
        """Calcula las horas lectivas disponibles"""
        return self.horas_semanales_contrato - self.horas_no_lectivas
    
    def tiene_disponibilidad(self, dia_semana, bloque_numero):
        """Verifica si el profesor está disponible en un día y bloque específico"""
        return self.user.disponibilidades.filter(
            dia_semana=dia_semana,
            bloque_numero=bloque_numero,
            disponible=True
        ).exists()


class Apoderado(models.Model):
    """Apoderados de estudiantes"""
    
    TIPO_APODERADO = [
        ('principal', 'Apoderado Principal'),
        ('secundario', 'Apoderado Secundario'),
    ]
    
    # Usuario asociado (login del apoderado)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_apoderado')
    
    # Información personal
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    telefono_movil = models.CharField(max_length=20, null=True, blank=True)
    
    # Relación con estudiantes (muchos a muchos a través de tabla intermedia)
    estudiantes = models.ManyToManyField(
        User,
        through='RelacionApoderadoEstudiante',
        related_name='apoderados',
        limit_choices_to={'role__nombre': 'Estudiante'}
    )
    
    # Información profesional/ocupación
    ocupacion = models.CharField(max_length=100, null=True, blank=True)
    lugar_trabajo = models.CharField(max_length=150, null=True, blank=True)
    telefono_trabajo = models.CharField(max_length=20, null=True, blank=True)
    
    # Permisos generales
    puede_ver_notas = models.BooleanField(default=True, verbose_name='Puede ver notas')
    puede_ver_asistencia = models.BooleanField(default=True, verbose_name='Puede ver asistencia')
    puede_recibir_comunicados = models.BooleanField(default=True, verbose_name='Puede recibir comunicados')
    puede_firmar_citaciones = models.BooleanField(default=True, verbose_name='Puede firmar citaciones')
    puede_autorizar_salidas = models.BooleanField(default=False, verbose_name='Puede autorizar salidas')
    puede_ver_tareas = models.BooleanField(default=True, verbose_name='Puede ver tareas')
    puede_ver_materiales = models.BooleanField(default=True, verbose_name='Puede ver materiales')
    
    # Estado del apoderado
    activo = models.BooleanField(default=True)
    motivo_inactivacion = models.TextField(null=True, blank=True)
    fecha_inactivacion = models.DateField(null=True, blank=True)
    
    # Información adicional
    observaciones = models.TextField(null=True, blank=True)
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='user__rbd_colegio')
    
    class Meta:
        db_table = 'apoderado'
        verbose_name = "Apoderado"
        verbose_name_plural = "Apoderados"
        ordering = ['-activo', 'user__apellido_paterno', 'user__nombre']
    
    def __str__(self):
        return f"Apoderado: {self.user.get_full_name()}"
    
    @property
    def edad(self):
        """Calcula la edad del apoderado"""
        if self.fecha_nacimiento:
            from datetime import date
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None
    
    def get_estudiantes_activos(self):
        """Retorna los estudiantes activos asociados a este apoderado"""
        return self.estudiantes.filter(
            is_active=True,
            perfil_estudiante__estado_academico='Activo'
        )
    
    def es_apoderado_principal_de(self, estudiante):
        """Verifica si es apoderado principal de un estudiante específico"""
        return RelacionApoderadoEstudiante.objects.filter(
            apoderado=self,
            estudiante=estudiante,
            tipo_apoderado='principal'
        ).exists()
    
    def get_permisos_dict(self):
        """Retorna un diccionario con todos los permisos"""
        return {
            'ver_notas': self.puede_ver_notas,
            'ver_asistencia': self.puede_ver_asistencia,
            'recibir_comunicados': self.puede_recibir_comunicados,
            'firmar_citaciones': self.puede_firmar_citaciones,
            'autorizar_salidas': self.puede_autorizar_salidas,
            'ver_tareas': self.puede_ver_tareas,
            'ver_materiales': self.puede_ver_materiales,
        }


class RelacionApoderadoEstudiante(models.Model):
    """Relación entre apoderados y estudiantes"""
    
    TIPO_APODERADO = [
        ('principal', 'Apoderado Principal'),
        ('secundario', 'Apoderado Secundario'),
    ]
    
    PARENTESCO = [
        ('padre', 'Padre'),
        ('madre', 'Madre'),
        ('abuelo', 'Abuelo/a'),
        ('tio', 'Tío/a'),
        ('hermano', 'Hermano/a'),
        ('tutor_legal', 'Tutor Legal'),
        ('otro', 'Otro'),
    ]
    
    apoderado = models.ForeignKey(Apoderado, on_delete=models.CASCADE, related_name='relaciones_estudiantes')
    estudiante = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='relaciones_apoderados',
        limit_choices_to={'role__nombre': 'Estudiante'}
    )
    
    tipo_apoderado = models.CharField(max_length=20, choices=TIPO_APODERADO, default='principal')
    parentesco = models.CharField(max_length=20, choices=PARENTESCO, default='padre')
    
    # Permisos específicos por relación
    usar_permisos_personalizados = models.BooleanField(default=False)
    puede_ver_notas = models.BooleanField(default=True, null=True, blank=True)
    puede_ver_asistencia = models.BooleanField(default=True, null=True, blank=True)
    puede_recibir_comunicados = models.BooleanField(default=True, null=True, blank=True)
    puede_firmar_citaciones = models.BooleanField(default=True, null=True, blank=True)
    puede_autorizar_salidas = models.BooleanField(default=False, null=True, blank=True)
    puede_ver_tareas = models.BooleanField(default=True, null=True, blank=True)
    puede_ver_materiales = models.BooleanField(default=True, null=True, blank=True)
    
    # Prioridad de contacto
    prioridad_contacto = models.IntegerField(default=1)
    
    # Estado de la relación
    activa = models.BooleanField(default=True)
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='apoderado__user__rbd_colegio')
    
    class Meta:
        db_table = 'relacion_apoderado_estudiante'
        verbose_name = "Relación Apoderado-Estudiante"
        verbose_name_plural = "Relaciones Apoderado-Estudiante"
        unique_together = ('apoderado', 'estudiante')
        ordering = ['estudiante', 'prioridad_contacto']
    
    def __str__(self):
        tipo = dict(self.TIPO_APODERADO)[self.tipo_apoderado]
        return f"{self.apoderado.user.get_full_name()} ({tipo}) → {self.estudiante.get_full_name()}"
    
    def get_permisos_efectivos(self):
        """Retorna los permisos efectivos (personalizados o heredados del apoderado)"""
        if self.usar_permisos_personalizados:
            return {
                'ver_notas': self.puede_ver_notas,
                'ver_asistencia': self.puede_ver_asistencia,
                'recibir_comunicados': self.puede_recibir_comunicados,
                'firmar_citaciones': self.puede_firmar_citaciones,
                'autorizar_salidas': self.puede_autorizar_salidas,
                'ver_tareas': self.puede_ver_tareas,
                'ver_materiales': self.puede_ver_materiales,
            }
        else:
            return self.apoderado.get_permisos_dict()


class FirmaDigitalApoderado(models.Model):
    """Firmas digitales de apoderados en documentos"""
    
    TIPO_DOCUMENTO = [
        ('citacion', 'Citación'),
        ('comunicado', 'Comunicado'),
        ('autorizacion_salida', 'Autorización de Salida'),
        ('autorizacion_actividad', 'Autorización de Actividad'),
        ('compromiso_academico', 'Compromiso Académico'),
        ('acta_reunion', 'Acta de Reunión'),
        ('consentimiento_pie', 'Consentimiento PIE'),
        ('otro', 'Otro Documento'),
    ]
    
    # Apoderado que firma
    apoderado = models.ForeignKey(Apoderado, on_delete=models.PROTECT, related_name='firmas')
    
    # Estudiante relacionado (si aplica)
    estudiante = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='firmas_apoderado',
        null=True,
        blank=True,
        limit_choices_to={'role__nombre': 'Estudiante'}
    )
    
    # Información del documento
    tipo_documento = models.CharField(max_length=30, choices=TIPO_DOCUMENTO)
    titulo_documento = models.CharField(max_length=255)
    contenido_documento = models.TextField(help_text='Contenido o resumen del documento firmado')
    
    # ID del documento original
    documento_id = models.IntegerField(null=True, blank=True)
    documento_tipo_modelo = models.CharField(max_length=50, null=True, blank=True)
    
    # Datos de la firma digital
    timestamp_firma = models.DateTimeField(auto_now_add=True, verbose_name='Fecha y hora de firma')
    ip_address = models.GenericIPAddressField(verbose_name='Dirección IP')
    user_agent = models.TextField(null=True, blank=True)
    
    # Usuario que firmó
    usuario_firmante = models.ForeignKey(User, on_delete=models.PROTECT, related_name='firmas_realizadas')
    
    # Firma en representación
    firma_en_representacion = models.BooleanField(default=False)
    
    # Hash de integridad
    hash_documento = models.CharField(max_length=64, null=True, blank=True)
    
    # Estado de la firma
    firma_valida = models.BooleanField(default=True)
    motivo_invalidacion = models.TextField(null=True, blank=True)
    fecha_invalidacion = models.DateTimeField(null=True, blank=True)
    invalidada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='firmas_invalidadas'
    )
    
    # Observaciones adicionales
    observaciones = models.TextField(null=True, blank=True)
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='apoderado__user__rbd_colegio')
    
    class Meta:
        db_table = 'firma_digital_apoderado'
        verbose_name = "Firma Digital de Apoderado"
        verbose_name_plural = "Firmas Digitales de Apoderados"
        ordering = ['-timestamp_firma']
        indexes = [
            models.Index(fields=['apoderado', '-timestamp_firma']),
            models.Index(fields=['estudiante', '-timestamp_firma']),
            models.Index(fields=['tipo_documento', '-timestamp_firma']),
            models.Index(fields=['documento_tipo_modelo', 'documento_id']),
        ]
    
    def __str__(self):
        tipo = dict(self.TIPO_DOCUMENTO)[self.tipo_documento]
        return f"{tipo} - {self.apoderado.user.get_full_name()} - {self.timestamp_firma.strftime('%d/%m/%Y %H:%M')}"
    
    def invalidar_firma(self, motivo, usuario):
        """Invalida la firma registrando el motivo y quién la invalidó"""
        self.firma_valida = False
        self.motivo_invalidacion = motivo
        self.fecha_invalidacion = timezone.now()
        self.invalidada_por = usuario
        self.save()
    
    def get_documento_relacionado(self):
        """Intenta obtener el objeto del documento relacionado"""
        if not self.documento_tipo_modelo or not self.documento_id:
            return None
        
        try:
            from django.apps import apps
            app_label, model_name = self.documento_tipo_modelo.split('.')
            model = apps.get_model(app_label, model_name)
            return model.objects.get(pk=self.documento_id)
        except Exception:
            return None
    
    @staticmethod
    def crear_firma(apoderado, tipo_documento, titulo, contenido, ip_address, user_agent=None, 
                    estudiante=None, documento_id=None, documento_tipo_modelo=None):
        """Método helper para crear una firma digital con todos los datos necesarios"""
        import hashlib
        
        # Generar hash del contenido
        hash_obj = hashlib.sha256(contenido.encode('utf-8'))
        hash_documento = hash_obj.hexdigest()
        
        firma = FirmaDigitalApoderado.objects.create(
            apoderado=apoderado,
            estudiante=estudiante,
            tipo_documento=tipo_documento,
            titulo_documento=titulo,
            contenido_documento=contenido,
            documento_id=documento_id,
            documento_tipo_modelo=documento_tipo_modelo,
            ip_address=ip_address,
            user_agent=user_agent,
            usuario_firmante=apoderado.user,
            hash_documento=hash_documento,
            firma_valida=True
        )
        
        return firma


class PerfilAsesorFinanciero(models.Model):
    """Perfil extendido para usuarios con rol Asesor Financiero"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='perfil_asesor_financiero'
    )
    
    # Información profesional
    area_especialidad = models.CharField(
        max_length=100,
        choices=[
            ('contabilidad', 'Contabilidad'),
            ('finanzas', 'Finanzas'),
            ('tesoreria', 'Tesorería'),
            ('cobranzas', 'Cobranzas'),
            ('general', 'General'),
        ],
        default='general'
    )
    
    titulo_profesional = models.CharField(max_length=150, null=True, blank=True)
    registro_profesional = models.CharField(max_length=50, null=True, blank=True)
    
    # Permisos específicos
    puede_aprobar_descuentos = models.BooleanField(default=True)
    puede_anular_pagos = models.BooleanField(default=False)
    puede_modificar_aranceles = models.BooleanField(default=True)
    puede_generar_reportes_contables = models.BooleanField(default=True)
    acceso_configuracion_transbank = models.BooleanField(default=False)
    
    # Información de contacto adicional
    telefono_oficina = models.CharField(max_length=15, null=True, blank=True)
    extension = models.CharField(max_length=10, null=True, blank=True)
    
    # Horarios de atención
    horario_atencion = models.TextField(null=True, blank=True)
    
    # Estado
    fecha_ingreso = models.DateField(null=True, blank=True)
    estado_laboral = models.CharField(
        max_length=20,
        choices=[
            ('Activo', 'Activo'),
            ('Licencia', 'Con Licencia'),
            ('Vacaciones', 'De Vacaciones'),
            ('Inactivo', 'Inactivo'),
        ],
        default='Activo'
    )
    
    # Observaciones
    notas_internas = models.TextField(null=True, blank=True)
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='user__rbd_colegio')
    
    class Meta:
        db_table = 'perfil_asesor_financiero'
        verbose_name = "Perfil de Asesor Financiero"
        verbose_name_plural = "Perfiles de Asesores Financieros"
        ordering = ['user__nombre', 'user__apellido_paterno']
    
    def __str__(self):
        return f"Asesor Financiero: {self.user.get_full_name()} ({self.get_area_especialidad_display()})"
    
    @property
    def colegio(self):
        """Retorna el colegio al que pertenece el asesor"""
        return self.user.colegio
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del asesor"""
        return self.user.get_full_name()
    
    @property
    def tiene_permisos_completos(self):
        """Indica si tiene todos los permisos financieros"""
        return all([
            self.puede_aprobar_descuentos,
            self.puede_anular_pagos,
            self.puede_modificar_aranceles,
            self.puede_generar_reportes_contables,
            self.acceso_configuracion_transbank
        ])


# Alias para compatibilidad con código antiguo
Profesor = PerfilProfesor
Estudiante = PerfilEstudiante

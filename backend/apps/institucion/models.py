"""
Modelos del módulo de Institución
Migrados desde sistema_antiguo/institucion/models.py
Compatible con autopoblar.py sin modificaciones
"""
from django.db import models
from django.db.models import CheckConstraint, Q, F
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from backend.common.tenancy import TenantManager


class Region(models.Model):
    """Región de Chile"""
    id_region = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'region'
        verbose_name = 'Región'
        verbose_name_plural = 'Regiones'

    def __str__(self):
        return self.nombre


class Comuna(models.Model):
    """Comuna de Chile"""
    id_comuna = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='comunas')

    class Meta:
        db_table = 'comuna'
        verbose_name = 'Comuna'
        verbose_name_plural = 'Comunas'
        unique_together = ('nombre', 'region')

    def __str__(self):
        return f"{self.nombre} ({self.region.nombre})"


class TipoEstablecimiento(models.Model):
    """Tipo de establecimiento educativo"""
    id_tipo_establecimiento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'tipo_establecimiento'
        verbose_name = 'Tipo de Establecimiento'
        verbose_name_plural = 'Tipos de Establecimientos'

    def __str__(self):
        return self.nombre


class DependenciaAdministrativa(models.Model):
    """Dependencia administrativa del colegio"""
    id_dependencia = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'dependencia_administrativa'
        verbose_name = 'Dependencia Administrativa'
        verbose_name_plural = 'Dependencias Administrativas'

    def __str__(self):
        return self.nombre


class NivelEducativo(models.Model):
    """Nivel educativo (Parvularia, Básica, Media)"""
    id_nivel = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'nivel_educativo'
        verbose_name = 'Nivel Educativo'
        verbose_name_plural = 'Niveles Educativos'

    def __str__(self):
        return self.nombre


class TipoInfraestructura(models.Model):
    """Tipo de infraestructura"""
    id_tipo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'tipo_infraestructura'
        verbose_name = 'Tipo de Infraestructura'
        verbose_name_plural = 'Tipos de Infraestructura'

    def __str__(self):
        return self.nombre


class Colegio(models.Model):
    """Colegio o institución educativa"""

    TIPO_DEPENDENCIA = [
        ('MUNICIPAL', 'Municipal'),
        ('SUBVENCIONADO', 'Particular Subvencionado'),
        ('PARTICULAR', 'Particular Pagado'),
        ('TP', 'Técnico-Profesional'),
    ]

    rbd = models.IntegerField(primary_key=True)  # RBD viene desde la entidad ministerial
    rut_establecimiento = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=150, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    correo = models.EmailField(max_length=100, unique=True, null=True, blank=True)
    web = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(max_length=50, unique=True, null=True, blank=True)
    logo = models.ImageField(upload_to='colegios/logos/', null=True, blank=True)
    color_primario = models.CharField(max_length=7, default='#6366f1')
    capacidad_maxima = models.IntegerField(null=True, blank=True)
    fecha_fundacion = models.DateField(null=True, blank=True)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_DEPENDENCIA,
        default='SUBVENCIONADO',
        help_text='Tipo de dependencia del establecimiento (determina subvenciones disponibles)',
    )
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT, related_name='colegios')
    tipo_establecimiento = models.ForeignKey(TipoEstablecimiento, on_delete=models.PROTECT)
    dependencia = models.ForeignKey(DependenciaAdministrativa, on_delete=models.PROTECT)
    objects = TenantManager(school_field='rbd')

    class Meta:
        db_table = 'colegio'
        verbose_name = 'Colegio'
        verbose_name_plural = 'Colegios'

    def __str__(self):
        return f"{self.nombre} ({self.rbd})"

    def _assign_defaults_if_needed(self):
        """Compatibilidad: completar catálogos requeridos si no se enviaron."""
        if self.comuna_id is None:
            region, _ = Region.objects.get_or_create(nombre='Región Metropolitana')
            self.comuna, _ = Comuna.objects.get_or_create(
                nombre='Santiago',
                defaults={'region': region},
            )
        if self.tipo_establecimiento_id is None:
            self.tipo_establecimiento, _ = TipoEstablecimiento.objects.get_or_create(
                nombre='Sin especificar'
            )
        if self.dependencia_id is None:
            self.dependencia, _ = DependenciaAdministrativa.objects.get_or_create(
                nombre='Sin especificar'
            )
        if not self.rut_establecimiento:
            self.rut_establecimiento = f"{self.rbd}-K"

    def save(self, *args, **kwargs):
        self._assign_defaults_if_needed()
        if not self.slug:
            base_slug = slugify(self.nombre or f'colegio-{self.rbd}')[:45] or f'colegio-{self.rbd}'
            candidate = base_slug
            i = 1
            while Colegio.objects.all_schools().exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f'{base_slug[:45]}-{i}'
                i += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class ColegioInfraestructura(models.Model):
    """Relación entre colegio e infraestructura"""
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='infraestructura')
    tipo_infra = models.ForeignKey(TipoInfraestructura, on_delete=models.PROTECT)
    cantidad = models.IntegerField(default=0)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'colegio_infraestructura'
        verbose_name = 'Infraestructura del Colegio'
        verbose_name_plural = 'Infraestructuras de Colegios'
        unique_together = ('colegio', 'tipo_infra')

    def __str__(self):
        return f"{self.colegio.nombre} - {self.tipo_infra.nombre} ({self.cantidad})"


class Infraestructura(models.Model):
    """Modelo para gestionar salas, espacios y recursos físicos del establecimiento"""
    
    TIPO_CHOICES = [
        ('Sala de Clases', '🚪 Sala de Clases'),
        ('Laboratorio', '🔬 Laboratorio'),
        ('Biblioteca', '📚 Biblioteca'),
        ('Gimnasio', '🏃 Gimnasio'),
        ('Comedor', '🍽️ Comedor'),
        ('Auditorio', '🎭 Auditorio'),
        ('Sala de Profesores', '👨‍🏫 Sala de Profesores'),
        ('Oficina Administrativa', '💼 Oficina Administrativa'),
        ('Baños', '🚻 Baños'),
        ('Patio', '🌳 Patio'),
        ('Cancha Deportiva', '⚽ Cancha Deportiva'),
        ('Otro', '🏢 Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('Operativo', '✅ Operativo'),
        ('En Mantenimiento', '🔧 En Mantenimiento'),
        ('Fuera de Servicio', '❌ Fuera de Servicio'),
    ]
    
    rbd_colegio = models.IntegerField(db_index=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    piso = models.IntegerField(default=1)
    capacidad_estudiantes = models.IntegerField(default=0)
    ancho_metros = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    largo_metros = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    alto_metros = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='Operativo')
    observaciones = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='rbd_colegio')
    
    class Meta:
        db_table = 'infraestructura'
        verbose_name = 'Infraestructura'
        verbose_name_plural = 'Infraestructura'
        ordering = ['tipo', 'piso', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.tipo})"
    
    def save(self, *args, **kwargs):
        # Calcular área automáticamente
        if self.ancho_metros and self.largo_metros:
            self.area_m2 = self.ancho_metros * self.largo_metros
        super().save(*args, **kwargs)


class CicloAcademicoManager(TenantManager):
    """Manager con compatibilidad para payload legacy (campo `anio`)."""

    def create(self, **kwargs):
        kwargs.pop('anio', None)
        if 'creado_por' not in kwargs or 'modificado_por' not in kwargs:
            from backend.apps.accounts.models import User

            colegio_obj = kwargs.get('colegio')
            colegio_id = kwargs.get('colegio_id') or (colegio_obj.rbd if colegio_obj else None)
            fallback_user = None
            if colegio_id is not None:
                fallback_user = User.objects.filter(rbd_colegio=colegio_id).order_by('id').first()
            if fallback_user is None:
                fallback_user = User.objects.order_by('id').first()

            if fallback_user is not None:
                kwargs.setdefault('creado_por', fallback_user)
                kwargs.setdefault('modificado_por', fallback_user)
        return super().create(**kwargs)


class CicloAcademico(models.Model):
    """
    Ciclo académico (año escolar) - representa un período académico completo.
    """

    ESTADOS = [
        ('PLANIFICACION', 'En Planificación'),
        ('ACTIVO', 'Activo'),
        ('EVALUACION', 'En Evaluación'),
        ('FINALIZADO', 'Finalizado'),
        ('CERRADO', 'Cerrado'),
    ]

    TRANSICIONES_VALIDAS = {
        'PLANIFICACION': ['ACTIVO'],
        'ACTIVO': ['EVALUACION', 'FINALIZADO'],
        'EVALUACION': ['FINALIZADO'],
        'FINALIZADO': ['CERRADO'],
        'CERRADO': [],  # Estado final, no hay transiciones
    }

    colegio = models.ForeignKey(
        Colegio,
        on_delete=models.CASCADE,
        related_name='ciclos_academicos'
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Ejemplo: '2024-2025'"
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PLANIFICACION'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción opcional del ciclo académico"
    )

    # Configuración de períodos académicos
    periodos_config = models.JSONField(
        default=dict,
        help_text="""
        Configuración de períodos: {
            "periodos": [
                {"nombre": "Primer Semestre", "inicio": "2024-03-01", "fin": "2024-07-31"},
                {"nombre": "Segundo Semestre", "inicio": "2024-08-01", "fin": "2024-12-20"}
            ]
        }
        """
    )

    # Metadata con audit trail
    creado_por = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='ciclos_creados'
    )
    modificado_por = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='ciclos_modificados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    objects = CicloAcademicoManager(school_field='colegio_id')

    class Meta:
        db_table = 'ciclo_academico'
        verbose_name = 'Ciclo Académico'
        verbose_name_plural = 'Ciclos Académicos'
        unique_together = ('colegio', 'nombre')
        ordering = ['-fecha_inicio']
        constraints = [
            CheckConstraint(
                condition=Q(fecha_inicio__lt=F('fecha_fin')),
                name='ciclo_fechas_validas'
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.colegio.nombre}"

    def clean(self):
        """Validaciones de negocio"""
        if self.fecha_inicio >= self.fecha_fin:
            raise ValidationError('La fecha de inicio debe ser anterior a la fecha fin')

        # Validar que no se solape con otros ciclos del mismo colegio
        ciclos_solapados = CicloAcademico.objects.filter(
            colegio=self.colegio,
            fecha_inicio__lt=self.fecha_fin,
            fecha_fin__gt=self.fecha_inicio
        ).exclude(pk=self.pk)

        if ciclos_solapados.exists():
            raise ValidationError('Las fechas del ciclo se solapan con otro ciclo existente')

    def puede_transitar_a(self, nuevo_estado):
        """Verifica si una transición de estado es válida"""
        return nuevo_estado in self.TRANSICIONES_VALIDAS.get(self.estado, [])

    def transitar_estado(self, nuevo_estado, usuario):
        """Realiza una transición de estado con validación"""
        if not self.puede_transitar_a(nuevo_estado):
            raise ValidationError(f'No se puede transitar de {self.estado} a {nuevo_estado}')

        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.modificado_por = usuario
        self.save()

        # Aquí se podría agregar lógica para audit trail (e.g., crear CambioEstado)

    def esta_activo(self):
        """Verifica si el ciclo está activo"""
        return self.estado == 'ACTIVO'

    def get_periodo_actual(self):
        """Retorna el período académico actual basado en la fecha (placeholder)"""
        # Implementar lógica para determinar período actual desde periodos_config
        return None


class ConfiguracionAcademica(models.Model):
    """
    Configuración académica por establecimiento.

    Almacena parámetros operativos del colegio que condicionan el comportamiento
    del sistema: régimen de evaluación, período activo, criterios SEP, etc.
    Un único registro activo por colegio (enforcement via unique_together + activo).
    """

    REGIMEN_CHOICES = [
        ('SEMESTRAL', 'Semestral (2 períodos)'),
        ('TRIMESTRAL', 'Trimestral (3 períodos)'),
        ('ANUAL', 'Anual (1 período)'),
    ]

    colegio = models.OneToOneField(
        Colegio,
        on_delete=models.CASCADE,
        related_name='configuracion_academica',
        help_text='Establecimiento al que aplica esta configuración',
    )
    anio_escolar_activo = models.PositiveSmallIntegerField(
        help_text='Año escolar en curso (ej: 2025)',
    )
    regimen_evaluacion = models.CharField(
        max_length=15,
        choices=REGIMEN_CHOICES,
        default='SEMESTRAL',
        help_text='Régimen de períodos de evaluación del colegio',
    )
    # SEP – Subvención Escolar Preferencial
    tiene_convenio_sep = models.BooleanField(
        default=False,
        help_text='¿El colegio tiene convenio SEP vigente con el MINEDUC?',
    )
    porcentaje_alumnos_prioritarios = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='% de alumnos prioritarios sobre matrícula total (para reporte SEP)',
    )
    # Escala de notas — configurable por colegio (Chile: 1.0-7.0 por defecto)
    nota_minima = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=1.0,
        help_text='Nota mínima de la escala (ej: 1.0 para Chile)',
    )
    nota_maxima = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=7.0,
        help_text='Nota máxima de la escala (ej: 7.0 para Chile)',
    )
    nota_aprobacion = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=4.0,
        help_text='Nota mínima de aprobación (ej: 4.0 estándar Chile, 3.5 en algunos decretos)',
    )
    redondeo_decimales = models.PositiveSmallIntegerField(
        default=1,
        help_text='Cantidad de decimales a redondear en notas (1 = un decimal)',
    )
    # Alertas tempranas — umbrales configurables
    umbral_inasistencia_alerta = models.PositiveSmallIntegerField(
        default=3,
        help_text='Número de inasistencias consecutivas que activa una alerta temprana',
    )
    umbral_notas_alerta = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=4.0,
        help_text='Promedio mínimo; si el alumno baja de este valor se genera alerta',
    )
    # Metadata
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configuraciones_actualizadas',
    )
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'configuracion_academica'
        verbose_name = 'Configuración Académica'
        verbose_name_plural = 'Configuraciones Académicas'

    def __str__(self):
        return f"Config {self.colegio.nombre} — {self.anio_escolar_activo}"

    @property
    def es_sep(self):
        """True si el colegio tiene convenio SEP activo."""
        return self.tiene_convenio_sep

    @classmethod
    def get_escala_para_colegio(cls, colegio):
        """
        Retorna la configuración de escala de notas para un colegio.
        Si no existe configuración, retorna defaults chilenos (1.0 - 7.0, aprobación 4.0).

        Returns:
            dict: {nota_minima, nota_maxima, nota_aprobacion, redondeo_decimales}
        """
        from decimal import Decimal
        try:
            config = cls.objects.get(colegio=colegio)
            return {
                'nota_minima': config.nota_minima,
                'nota_maxima': config.nota_maxima,
                'nota_aprobacion': config.nota_aprobacion,
                'redondeo_decimales': config.redondeo_decimales,
            }
        except cls.DoesNotExist:
            return {
                'nota_minima': Decimal('1.0'),
                'nota_maxima': Decimal('7.0'),
                'nota_aprobacion': Decimal('4.0'),
                'redondeo_decimales': 1,
            }


class EventoCalendario(models.Model):
    """
    Eventos del calendario escolar académico.

    Tipos:
    - feriado: días feriados nacionales / regionales
    - vacaciones: recesos escolares
    - evaluacion: pruebas institucionales / SIMCE
    - reunion: reuniones de apoderados, consejo de profesores
    - actividad: actividades extracurriculares, salidas pedagógicas
    - ceremonia: licenciaturas, actos cívicos
    - administrativo: matrículas, inscripciones, pagos
    """
    TIPOS_EVENTO = [
        ('feriado', '📅 Feriado'),
        ('vacaciones', '🏖️ Vacaciones'),
        ('evaluacion', '📝 Evaluación Institucional'),
        ('reunion', '👥 Reunión'),
        ('actividad', '🎯 Actividad'),
        ('ceremonia', '🎓 Ceremonia'),
        ('administrativo', '📋 Administrativo'),
        ('otro', '📌 Otro'),
    ]

    VISIBILIDAD = [
        ('todos', 'Todos'),
        ('profesores', 'Solo Profesores'),
        ('estudiantes', 'Solo Estudiantes'),
        ('apoderados', 'Solo Apoderados'),
        ('administrativos', 'Solo Administrativos'),
    ]

    id_evento = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(
        Colegio, on_delete=models.CASCADE, related_name='eventos_calendario'
    )
    ciclo_academico = models.ForeignKey(
        CicloAcademico, on_delete=models.CASCADE,
        related_name='eventos_calendario', null=True, blank=True
    )

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_EVENTO, default='otro')

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True, help_text='Para eventos de más de un día')
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    todo_el_dia = models.BooleanField(default=False)

    lugar = models.CharField(max_length=200, blank=True, null=True)
    visibilidad = models.CharField(max_length=20, choices=VISIBILIDAD, default='todos')
    es_feriado_nacional = models.BooleanField(default=False, help_text='No hay clases')
    color = models.CharField(max_length=7, default='#3B82F6', help_text='Color hex para el calendario')

    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT, related_name='eventos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'evento_calendario'
        verbose_name = 'Evento del Calendario'
        verbose_name_plural = 'Eventos del Calendario'
        ordering = ['fecha_inicio', 'hora_inicio']
        indexes = [
            models.Index(fields=['colegio', 'fecha_inicio']),
            models.Index(fields=['tipo', 'fecha_inicio']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.titulo} ({self.fecha_inicio})"

    @property
    def es_multidia(self):
        return self.fecha_fin is not None and self.fecha_fin > self.fecha_inicio


class SolicitudReunion(models.Model):
    """
    Solicitud de reunión apoderado → profesor.

    Flujo: pendiente → confirmada / reprogramada / rechazada → completada / cancelada
    """
    ESTADOS = [
        ('pendiente', '⏳ Pendiente'),
        ('confirmada', '✅ Confirmada'),
        ('reprogramada', '🔄 Reprogramada'),
        ('rechazada', '❌ Rechazada'),
        ('completada', '✔️ Completada'),
        ('cancelada', '🚫 Cancelada'),
    ]

    TIPOS = [
        ('academica', 'Académica'),
        ('conductual', 'Conductual'),
        ('orientacion', 'Orientación'),
        ('administrativa', 'Administrativa'),
        ('general', 'General'),
    ]

    MODALIDADES = [
        ('presencial', 'Presencial'),
        ('virtual', 'Virtual (videollamada)'),
        ('telefonica', 'Telefónica'),
    ]

    colegio = models.ForeignKey(
        Colegio, on_delete=models.CASCADE, related_name='solicitudes_reunion'
    )
    apoderado = models.ForeignKey(
        'accounts.Apoderado', on_delete=models.CASCADE, related_name='solicitudes_reunion'
    )
    profesor = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='reuniones_solicitadas'
    )
    estudiante = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reuniones_como_tema'
    )

    motivo = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS, default='general')

    # Fecha propuesta por el apoderado
    fecha_propuesta = models.DateField(null=True, blank=True)
    hora_propuesta = models.TimeField(null=True, blank=True)

    # Fecha confirmada por el profesor
    fecha_confirmada = models.DateField(null=True, blank=True)
    hora_confirmada = models.TimeField(null=True, blank=True)
    duracion_minutos = models.IntegerField(default=30)

    modalidad = models.CharField(max_length=20, choices=MODALIDADES, default='presencial')
    lugar = models.CharField(max_length=200, blank=True, null=True)
    enlace_virtual = models.URLField(blank=True, null=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    observaciones_apoderado = models.TextField(blank=True, null=True)
    respuesta_profesor = models.TextField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'solicitud_reunion'
        verbose_name = 'Solicitud de Reunión'
        verbose_name_plural = 'Solicitudes de Reunión'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['profesor', 'estado']),
            models.Index(fields=['apoderado', 'estado']),
        ]

    def __str__(self):
        return (
            f'{self.get_tipo_display()} — '
            f'{self.apoderado.user.get_full_name() if self.apoderado and self.apoderado.user else "?"} '
            f'→ {self.profesor.get_full_name() if self.profesor else "?"} '
            f'({self.get_estado_display()})'
        )


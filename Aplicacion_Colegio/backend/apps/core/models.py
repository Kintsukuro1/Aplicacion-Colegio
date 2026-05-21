"""
Modelos Fase 3 (Domain Redesign).

Este módulo es la ubicación canónica de los modelos del dominio core,
incluyendo matrícula mejorada y modelos de nuevos roles.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from backend.apps.institucion.models import Colegio, CicloAcademico, NivelEducativo  # noqa: F401
from backend.apps.accounts.models import User
from backend.apps.cursos.models import Asignatura
from backend.common.tenancy import TenantManager


class CambioEstado(models.Model):
    ciclo_academico = models.ForeignKey(
        CicloAcademico,
        on_delete=models.CASCADE,
        related_name='cambios_estado'
    )

    estado_anterior = models.CharField(max_length=20, choices=CicloAcademico.ESTADOS)
    estado_nuevo = models.CharField(max_length=20, choices=CicloAcademico.ESTADOS)

    cambiado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cambios_estado_realizados'
    )

    fecha_cambio = models.DateTimeField(auto_now_add=True)
    razon = models.TextField(blank=True)

    class Meta:
        db_table = 'cambio_estado_ciclo'
        verbose_name = 'Cambio de Estado'
        verbose_name_plural = 'Cambios de Estado'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"{self.ciclo_academico.nombre}: {self.estado_anterior} → {self.estado_nuevo}"


class EstadoMatricula(models.Model):
    ESTADOS_CHOICES = [
        ('PREMATRICULA', 'Pre-matrícula'),
        ('MATRICULADO', 'Matriculado'),
        ('ACTIVO', 'Activo'),
        ('INACTIVO_TEMPORAL', 'Inactivo Temporal'),
        ('SUSPENDIDO', 'Suspendido'),
        ('RETIRADO', 'Retirado'),
        ('GRADUADO', 'Graduado'),
        ('CERRADO', 'Cerrado'),
    ]

    nombre = models.CharField(max_length=50, unique=True, choices=ESTADOS_CHOICES)
    descripcion = models.TextField()
    es_activo = models.BooleanField(default=True, help_text="Si el estudiante puede acceder al sistema")
    permite_cambios = models.BooleanField(default=True, help_text="Si se permiten modificaciones en este estado")
    requiere_documentacion = models.BooleanField(default=False, help_text="Si requiere documentación especial")
    transiciones_posibles = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        help_text="Estados a los que se puede transitar desde este"
    )
    activo = models.BooleanField(default=True)
    orden = models.IntegerField(default=0)

    class Meta:
        db_table = 'estado_matricula'
        verbose_name = 'Estado de Matrícula'
        verbose_name_plural = 'Estados de Matrícula'
        ordering = ['orden']

    def __str__(self):
        return f"{self.nombre} - {self.descripcion[:50]}"


class MatriculaMejorada(models.Model):
    estudiante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='matriculas_mejoradas'
    )

    colegio = models.ForeignKey(
        Colegio,
        on_delete=models.CASCADE,
        related_name='matriculas_mejoradas'
    )

    ciclo_academico = models.ForeignKey(
        CicloAcademico,
        on_delete=models.CASCADE,
        related_name='matriculas_mejoradas_ciclo'
    )

    curso = models.ForeignKey(
        'cursos.Curso',
        on_delete=models.PROTECT,
        related_name='matriculas_mejoradas'
    )

    estado = models.ForeignKey(
        EstadoMatricula,
        on_delete=models.PROTECT,
        related_name='matriculas'
    )

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    valor_matricula = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )

    creado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='matriculas_creadas'
    )
    modificado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='matriculas_modificadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    observaciones = models.TextField(blank=True)
    numero_matricula = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número único de matrícula"
    )

    class Meta:
        db_table = 'matricula_mejorada'
        verbose_name = 'Matrícula Mejorada'
        verbose_name_plural = 'Matrículas Mejoradas'
        unique_together = ('estudiante', 'ciclo_academico')
        ordering = ['-fecha_creacion']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fecha_inicio__lte=models.F('fecha_fin')) | models.Q(fecha_fin__isnull=True),
                name='matricula_fechas_validas'
            ),
        ]

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.ciclo_academico.nombre}"

    def clean(self):
        super().clean()

        if self.fecha_inicio < self.ciclo_academico.fecha_inicio:
            raise ValidationError('La fecha de inicio debe ser posterior al inicio del ciclo académico')

        if self.fecha_fin and self.fecha_fin > self.ciclo_academico.fecha_fin:
            raise ValidationError('La fecha fin no puede ser posterior al fin del ciclo académico')

        if self.estado.es_activo:
            matriculas_activas = MatriculaMejorada.objects.filter(
                estudiante=self.estudiante,
                ciclo_academico=self.ciclo_academico,
                estado__es_activo=True
            ).exclude(pk=self.pk)

            if matriculas_activas.exists():
                raise ValidationError('El estudiante ya tiene una matrícula activa en este ciclo académico')

    def puede_cambiar_estado(self, nuevo_estado):
        return self.estado.transiciones_posibles.filter(pk=nuevo_estado.pk).exists()

    def cambiar_estado(self, nuevo_estado, usuario, razon=""):
        if not self.puede_cambiar_estado(nuevo_estado):
            raise ValidationError(
                f'No se puede cambiar del estado {self.estado.nombre} al estado {nuevo_estado.nombre}'
            )

        CambioEstadoMatricula.objects.create(
            matricula=self,
            estado_anterior=self.estado,
            estado_nuevo=nuevo_estado,
            cambiado_por=usuario,
            razon=razon or "Cambio manual de estado"
        )

        self.estado = nuevo_estado
        self.modificado_por = usuario
        self.save()


class CambioEstadoMatricula(models.Model):
    matricula = models.ForeignKey(
        MatriculaMejorada,
        on_delete=models.CASCADE,
        related_name='cambios_estado'
    )

    estado_anterior = models.ForeignKey(
        EstadoMatricula,
        on_delete=models.PROTECT,
        related_name='cambios_desde'
    )
    estado_nuevo = models.ForeignKey(
        EstadoMatricula,
        on_delete=models.PROTECT,
        related_name='cambios_hacia'
    )

    cambiado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cambios_estado_matricula'
    )

    fecha_cambio = models.DateTimeField(auto_now_add=True)
    razon = models.TextField(blank=True)

    class Meta:
        db_table = 'cambio_estado_matricula'
        verbose_name = 'Cambio de Estado de Matrícula'
        verbose_name_plural = 'Cambios de Estado de Matrícula'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"{self.matricula}: {self.estado_anterior.nombre} → {self.estado_nuevo.nombre}"


# ---------------------------------------------------------------------------
# Inspector Convivencia
# ---------------------------------------------------------------------------

class AnotacionConvivencia(models.Model):
    """Anotaciones positivas, negativas o neutras registradas por el inspector."""

    TIPOS = [
        ('POSITIVA', 'Positiva'),
        ('NEGATIVA', 'Negativa'),
        ('NEUTRA', 'Neutra'),
    ]

    CATEGORIAS = [
        ('COMPORTAMIENTO', 'Comportamiento'),
        ('PUNTUALIDAD', 'Puntualidad'),
        ('UNIFORME', 'Uniforme'),
        ('CONVIVENCIA', 'Convivencia'),
        ('OTRO', 'Otro'),
    ]

    GRAVEDADES = [
        (1, 'Leve'),
        (2, 'Moderada'),
        (3, 'Grave'),
    ]

    id_anotacion = models.AutoField(primary_key=True)
    estudiante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='anotaciones_convivencia',
        limit_choices_to={'role__nombre': 'Alumno'},
    )
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='anotaciones_convivencia')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='OTRO')
    descripcion = models.TextField()
    gravedad = models.IntegerField(choices=GRAVEDADES, default=1)
    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='anotaciones_registradas',
    )
    fecha = models.DateTimeField(default=timezone.now)
    notificado_apoderado = models.BooleanField(default=False)
    fecha_notificacion = models.DateTimeField(null=True, blank=True)

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'anotacion_convivencia'
        verbose_name = 'Anotación de Convivencia'
        verbose_name_plural = 'Anotaciones de Convivencia'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['estudiante', '-fecha']),
            models.Index(fields=['colegio', '-fecha']),
            models.Index(fields=['tipo']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estudiante.get_full_name()} - {self.fecha.strftime('%d/%m/%Y')}"


class JustificativoInasistencia(models.Model):
    """Justificativos de inasistencia presentados por apoderados y revisados por el inspector."""

    TIPOS = [
        ('MEDICO', 'Médico'),
        ('FAMILIAR', 'Familiar'),
        ('OTRO', 'Otro'),
    ]

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    id_justificativo = models.AutoField(primary_key=True)
    estudiante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='justificativos_inasistencia',
        limit_choices_to={'role__nombre': 'Alumno'},
    )
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='justificativos_inasistencia')
    fecha_ausencia = models.DateField()
    fecha_fin_ausencia = models.DateField(
        null=True, blank=True,
        help_text='Dejar vacío si la ausencia fue de un solo día',
    )
    motivo = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default='OTRO')
    documento_adjunto = models.FileField(upload_to='justificativos/%Y/%m/', null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='PENDIENTE')
    presentado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='justificativos_presentados',
        help_text='Apoderado o encargado que presenta el justificativo',
    )
    revisado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='justificativos_revisados',
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)
    observaciones_revision = models.TextField(blank=True, default='')

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'justificativo_inasistencia'
        verbose_name = 'Justificativo de Inasistencia'
        verbose_name_plural = 'Justificativos de Inasistencia'
        ordering = ['-fecha_ausencia']
        indexes = [
            models.Index(fields=['estudiante', '-fecha_ausencia']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.fecha_ausencia} ({self.get_estado_display()})"


# ---------------------------------------------------------------------------
# Psicólogo Orientador
# ---------------------------------------------------------------------------

class EntrevistaOrientacion(models.Model):
    """Entrevistas de orientación psicológica — datos confidenciales."""

    MOTIVOS = [
        ('ACADEMICO', 'Académico'),
        ('SOCIOEMOCIONAL', 'Socioemocional'),
        ('CONDUCTUAL', 'Conductual'),
        ('FAMILIAR', 'Familiar'),
        ('DERIVACION', 'Derivación'),
    ]

    id_entrevista = models.AutoField(primary_key=True)
    estudiante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='entrevistas_orientacion',
        limit_choices_to={'role__nombre': 'Alumno'},
    )
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='entrevistas_orientacion')
    psicologo = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='entrevistas_realizadas',
    )
    fecha = models.DateTimeField()
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    observaciones = models.TextField(help_text='Notas confidenciales de la entrevista')
    acuerdos = models.TextField(blank=True, default='')
    recomendaciones_profesor = models.TextField(
        blank=True, default='',
        help_text='Recomendaciones visibles para el profesor jefe (no confidenciales)',
    )
    seguimiento_requerido = models.BooleanField(default=False)
    fecha_siguiente_sesion = models.DateField(null=True, blank=True)
    confidencial = models.BooleanField(default=True)

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'entrevista_orientacion'
        verbose_name = 'Entrevista de Orientación'
        verbose_name_plural = 'Entrevistas de Orientación'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['estudiante', '-fecha']),
            models.Index(fields=['psicologo', '-fecha']),
        ]

    def __str__(self):
        return f"Entrevista {self.estudiante.get_full_name()} - {self.fecha.strftime('%d/%m/%Y')}"


class DerivacionExterna(models.Model):
    """Derivaciones a profesionales externos."""

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En proceso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]

    id_derivacion = models.AutoField(primary_key=True)
    estudiante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='derivaciones_externas',
        limit_choices_to={'role__nombre': 'Alumno'},
    )
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='derivaciones_externas')
    derivado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='derivaciones_realizadas',
    )
    profesional_destino = models.CharField(max_length=200)
    especialidad = models.CharField(max_length=100)
    motivo = models.TextField()
    estado = models.CharField(max_length=12, choices=ESTADOS, default='PENDIENTE')
    fecha_derivacion = models.DateField()
    fecha_retorno = models.DateField(null=True, blank=True)
    informe_retorno = models.TextField(blank=True, default='')

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'derivacion_externa'
        verbose_name = 'Derivación Externa'
        verbose_name_plural = 'Derivaciones Externas'
        ordering = ['-fecha_derivacion']
        indexes = [
            models.Index(fields=['estudiante', '-fecha_derivacion']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f"{self.estudiante.get_full_name()} → {self.profesional_destino} ({self.get_estado_display()})"


# ---------------------------------------------------------------------------
# Soporte Técnico Escolar
# ---------------------------------------------------------------------------

class TicketSoporte(models.Model):
    """Tickets de soporte técnico reportados por usuarios del colegio."""

    CATEGORIAS = [
        ('ACCESO', 'Problemas de acceso'),
        ('PLATAFORMA', 'Error en plataforma'),
        ('CONTRASEÑA', 'Reset de contraseña'),
        ('OTRO', 'Otro'),
    ]

    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    ESTADOS = [
        ('ABIERTO', 'Abierto'),
        ('EN_PROGRESO', 'En progreso'),
        ('RESUELTO', 'Resuelto'),
        ('CERRADO', 'Cerrado'),
    ]

    id_ticket = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='tickets_soporte')
    reportado_por = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='tickets_reportados',
    )
    asignado_a = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets_asignados',
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=12, choices=CATEGORIAS, default='OTRO')
    prioridad = models.CharField(max_length=8, choices=PRIORIDADES, default='MEDIA')
    estado = models.CharField(max_length=12, choices=ESTADOS, default='ABIERTO')
    resolucion = models.TextField(blank=True, default='')
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'ticket_soporte'
        verbose_name = 'Ticket de Soporte'
        verbose_name_plural = 'Tickets de Soporte'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['prioridad']),
            models.Index(fields=['asignado_a', 'estado']),
        ]

    def __str__(self):
        return f"#{self.id_ticket} {self.titulo} ({self.get_estado_display()})"


# ---------------------------------------------------------------------------
# Bibliotecario Digital
# ---------------------------------------------------------------------------

class RecursoDigital(models.Model):
    """Recursos educativos digitales gestionados por el bibliotecario."""

    TIPOS = [
        ('LIBRO', 'Libro'),
        ('VIDEO', 'Video'),
        ('DOCUMENTO', 'Documento'),
        ('ENLACE', 'Enlace'),
        ('SOFTWARE', 'Software'),
        ('MATERIAL_CRA', 'Material CRA/Didáctico'),
    ]

    id_recurso = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='recursos_digitales')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=12, choices=TIPOS, default='DOCUMENTO')
    asignatura = models.ForeignKey(
        Asignatura, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recursos_digitales',
    )
    nivel = models.ForeignKey(
        NivelEducativo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recursos_digitales',
    )
    archivo = models.FileField(upload_to='recursos_digitales/%Y/%m/', null=True, blank=True)
    url_externa = models.URLField(blank=True, default='')
    publicado = models.BooleanField(default=False)
    es_plan_lector = models.BooleanField(default=False, help_text="Indica si el recurso pertenece al Plan Lector obligatorio")
    publicado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='recursos_publicados',
    )
    descargas = models.IntegerField(default=0)

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'recurso_digital'
        verbose_name = 'Recurso Digital'
        verbose_name_plural = 'Recursos Digitales'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['colegio', 'tipo']),
            models.Index(fields=['publicado']),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"


class PrestamoRecurso(models.Model):
    """Préstamos de recursos (libros físicos o licencias digitales)."""

    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('DEVUELTO', 'Devuelto'),
        ('VENCIDO', 'Vencido'),
    ]

    id_prestamo = models.AutoField(primary_key=True)
    recurso = models.ForeignKey(RecursoDigital, on_delete=models.CASCADE, related_name='prestamos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prestamos_recursos')
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='prestamos_recursos')
    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion_esperada = models.DateField()
    fecha_devolucion_real = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='ACTIVO')

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'prestamo_recurso'
        verbose_name = 'Préstamo de Recurso'
        verbose_name_plural = 'Préstamos de Recursos'
        ordering = ['-fecha_prestamo']
        indexes = [
            models.Index(fields=['usuario', 'estado']),
            models.Index(fields=['recurso', 'estado']),
        ]

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.recurso.titulo} ({self.get_estado_display()})"

    @property
    def esta_vencido(self):
        """Verifica si el préstamo está vencido."""
        if self.estado == 'ACTIVO' and self.fecha_devolucion_esperada:
            from datetime import date
            return date.today() > self.fecha_devolucion_esperada
        return False


# ---------------------------------------------------------------------------
# Citación a Apoderados y Protocolos de Convivencia (Ley Aula Segura)
# ---------------------------------------------------------------------------

class CitacionApoderado(models.Model):
    """Reuniones y citaciones formales a apoderados gestionadas por psicólogos/orientadores."""

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('ASISTIO', 'Asistió'),
        ('INASISTENTE', 'Inasistente'),
        ('CANCELADA', 'Cancelada'),
    ]

    id_citacion = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='citaciones_apoderados')
    estudiante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='citaciones_recibidas',
        limit_choices_to={'role__nombre__in': ['Alumno', 'Estudiante']},
    )
    solicitado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='citaciones_creadas')
    fecha_citacion = models.DateTimeField()
    motivo = models.CharField(max_length=200)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='PENDIENTE')
    observaciones = models.TextField(blank=True, default='', help_text='Notas confidenciales de la citación')
    acuerdos = models.TextField(blank=True, default='', help_text='Acuerdos alcanzados en la reunión')

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'citacion_apoderado'
        verbose_name = 'Citación de Apoderado'
        verbose_name_plural = 'Citaciones de Apoderados'
        ordering = ['-fecha_citacion']
        indexes = [
            models.Index(fields=['estudiante', '-fecha_citacion']),
            models.Index(fields=['colegio', '-fecha_citacion']),
        ]

    def __str__(self):
        return f"Citación {self.estudiante.get_full_name()} - {self.fecha_citacion.strftime('%d/%m/%Y')} ({self.get_estado_display()})"


class CasoBullyingConvivencia(models.Model):
    """Casos de bullying, ciberbullying y violencia bajo la ley Aula Segura."""

    TIPOS = [
        ('BULLYING', 'Bullying'),
        ('CIBERBULLYING', 'Ciberbullying'),
        ('AGRESION_FISICA', 'Agresión Física'),
        ('AGRESION_VERBAL', 'Agresión Verbal'),
        ('DISCRIMINACION', 'Discriminación'),
        ('OTRA_GRAVE', 'Otra Falta Grave'),
    ]

    ESTADOS = [
        ('ABIERTO', 'Abierto'),
        ('EN_INVESTIGACION', 'En Investigación'),
        ('MEDIDAS_APLICADAS', 'Medidas Aplicadas'),
        ('CERRADO', 'Cerrado'),
    ]

    id_caso = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='casos_bullying')
    estudiante_implicado = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='casos_convivencia_implicado',
        limit_choices_to={'role__nombre__in': ['Alumno', 'Estudiante']},
    )
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='casos_convivencia_registrados')
    tipo_falta = models.CharField(max_length=20, choices=TIPOS)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ABIERTO')
    descripcion_hechos = models.TextField()
    medidas_tomadas = models.TextField(blank=True, default='', help_text='Medidas disciplinarias/apoyo aplicadas')
    apoderado_notificado = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(default=timezone.now)

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'caso_bullying_convivencia'
        verbose_name = 'Caso de Bullying y Convivencia'
        verbose_name_plural = 'Casos de Bullying y Convivencia'
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['estudiante_implicado', '-fecha_registro']),
            models.Index(fields=['colegio', '-fecha_registro']),
        ]

    def __str__(self):
        return f"{self.get_tipo_falta_display()} - {self.estudiante_implicado.get_full_name()} ({self.get_estado_display()})"


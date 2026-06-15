"""
Modelos del módulo Académico
Migrados desde sistema_antiguo/academico/models.py
Compatible con autopoblar.py sin modificaciones
"""
import hashlib
import json
from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from backend.apps.institucion.models import Colegio, CicloAcademico
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.accounts.models import User
from backend.common.tenancy import TenantManager


class ObjetivoAprendizaje(models.Model):
    """Objetivos de Aprendizaje (OA) del MINEDUC o personalizados"""
    id_oa = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='objetivos_aprendizaje')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='objetivos_aprendizaje')
    codigo = models.CharField(max_length=50)
    descripcion = models.TextField()
    nivel = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'objetivo_aprendizaje'
        verbose_name = 'Objetivo de Aprendizaje'
        verbose_name_plural = 'Objetivos de Aprendizaje'
        unique_together = ('colegio', 'asignatura', 'codigo', 'nivel')
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} ({self.nivel}) - {self.asignatura.nombre}"


class Rubrica(models.Model):
    """Rúbrica de evaluación compartida o propia"""
    id_rubrica = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='rubricas')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='rubricas')
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rubricas_creadas')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    es_compartida = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'rubrica'
        verbose_name = 'Rúbrica'
        verbose_name_plural = 'Rúbricas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre} - {self.asignatura.nombre}"


class CriterioRubrica(models.Model):
    """Criterios de evaluación dentro de una rúbrica"""
    id_criterio = models.AutoField(primary_key=True)
    rubrica = models.ForeignKey(Rubrica, on_delete=models.CASCADE, related_name='criterios')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    peso = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    orden = models.IntegerField(default=1)
    objects = TenantManager(school_field='rubrica__colegio_id')

    class Meta:
        db_table = 'criterio_rubrica'
        verbose_name = 'Criterio de Rúbrica'
        verbose_name_plural = 'Criterios de Rúbrica'
        ordering = ['orden']

    def __str__(self):
        return f"{self.nombre} - {self.rubrica.nombre}"


class NivelRubrica(models.Model):
    """Nivel de desempeño de un criterio"""
    id_nivel = models.AutoField(primary_key=True)
    criterio = models.ForeignKey(CriterioRubrica, on_delete=models.CASCADE, related_name='niveles')
    puntaje = models.IntegerField()
    descripcion = models.TextField()
    orden = models.IntegerField(default=1)
    objects = TenantManager(school_field='criterio__rubrica__colegio_id')

    class Meta:
        db_table = 'nivel_rubrica'
        verbose_name = 'Nivel de Rúbrica'
        verbose_name_plural = 'Niveles de Rúbrica'
        ordering = ['-puntaje', 'orden']

    def __str__(self):
        return f"{self.puntaje} pts - {self.criterio.nombre}"


class Planificacion(models.Model):
    """Planificación de clases del profesor"""
    id_planificacion = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='planificaciones')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='planificaciones')
    titulo = models.CharField(max_length=200)
    objetivo_general = models.TextField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    ciclo_academico = models.ForeignKey(
        CicloAcademico,
        on_delete=models.CASCADE,
        related_name='planificaciones',
        null=True,
        blank=True
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ('BORRADOR', 'Borrador'),
            ('ENVIADA', 'Enviada'),
            ('APROBADA', 'Aprobada'),
            ('RECHAZADA', 'Rechazada'),
        ],
        default='BORRADOR',
        null=True,
        blank=True,
    )
    observaciones_coordinador = models.TextField(
        blank=True, default='',
        help_text='Observaciones del coordinador académico al revisar la planificación',
    )
    aprobado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planificaciones_aprobadas',
        help_text='Coordinador que aprobó/rechazó la planificación',
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    enviada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planificaciones_enviadas',
        help_text='Profesor que envió la planificación para revisión',
    )
    fecha_envio = models.DateTimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Nuevas relaciones del módulo curricular
    objetivos_aprendizaje = models.ManyToManyField(
        ObjetivoAprendizaje,
        blank=True,
        related_name='planificaciones',
        db_table='planificacion_oa_link'
    )
    rubrica = models.ForeignKey(
        Rubrica,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='planificaciones'
    )
    
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'planificacion'
        verbose_name = 'Planificación'
        verbose_name_plural = 'Planificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.titulo} - {self.clase}"


class PlanificacionObjetivo(models.Model):
    """Objetivos específicos de una planificación"""
    id_objetivo = models.AutoField(primary_key=True)
    planificacion = models.ForeignKey(Planificacion, on_delete=models.CASCADE, related_name='objetivos')
    descripcion = models.TextField()
    orden = models.IntegerField()
    objects = TenantManager(school_field='planificacion__colegio_id')

    class Meta:
        db_table = 'planificacion_objetivo'
        verbose_name = 'Objetivo de Planificación'
        verbose_name_plural = 'Objetivos de Planificación'
        ordering = ['orden']

    def __str__(self):
        return f"Objetivo {self.orden} - {self.planificacion.titulo}"


class PlanificacionActividad(models.Model):
    """Actividades de una planificación"""
    id_actividad = models.AutoField(primary_key=True)
    planificacion = models.ForeignKey(Planificacion, on_delete=models.CASCADE, related_name='actividades')
    descripcion = models.TextField()
    orden = models.IntegerField()
    objects = TenantManager(school_field='planificacion__colegio_id')

    class Meta:
        db_table = 'planificacion_actividad'
        verbose_name = 'Actividad de Planificación'
        verbose_name_plural = 'Actividades de Planificación'
        ordering = ['orden']

    def __str__(self):
        return f"Actividad {self.orden} - {self.planificacion.titulo}"


class PlanificacionRecurso(models.Model):
    """Recursos necesarios para una planificación"""
    id_recurso = models.AutoField(primary_key=True)
    planificacion = models.ForeignKey(Planificacion, on_delete=models.CASCADE, related_name='recursos')
    descripcion = models.TextField()
    orden = models.IntegerField()
    objects = TenantManager(school_field='planificacion__colegio_id')

    class Meta:
        db_table = 'planificacion_recurso'
        verbose_name = 'Recurso de Planificación'
        verbose_name_plural = 'Recursos de Planificación'
        ordering = ['orden']

    def __str__(self):
        return f"Recurso {self.orden} - {self.planificacion.titulo}"


class PlanificacionEvaluacion(models.Model):
    """Evaluaciones asociadas a una planificación"""
    id_evaluacion = models.AutoField(primary_key=True)
    planificacion = models.ForeignKey(Planificacion, on_delete=models.CASCADE, related_name='evaluaciones')
    descripcion = models.TextField()
    orden = models.IntegerField()
    objects = TenantManager(school_field='planificacion__colegio_id')

    class Meta:
        db_table = 'planificacion_evaluacion'
        verbose_name = 'Evaluación de Planificación'
        verbose_name_plural = 'Evaluaciones de Planificación'
        ordering = ['orden']

    def __str__(self):
        return f"Evaluación {self.orden} - {self.planificacion.titulo}"


class Asistencia(models.Model):
    """Registro de asistencia de estudiantes"""
    ESTADOS = [
        ('P', 'Presente'),
        ('A', 'Ausente'),
        ('T', 'Tardanza'),
        ('J', 'Justificada'),
    ]
    
    id_asistencia = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='asistencias')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='asistencias')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField()
    estado = models.CharField(max_length=2, choices=ESTADOS)
    tipo_asistencia = models.CharField(max_length=20, default='Presencial')
    observaciones = models.TextField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'asistencia'
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-fecha']
        unique_together = ('clase', 'estudiante', 'fecha')

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.fecha} - {self.get_estado_display()}"


class Evaluacion(models.Model):
    """Evaluaciones (pruebas, trabajos, etc.)"""
    PERIODOS = [
        ('semestre1', 'Primer Semestre'),
        ('semestre2', 'Segundo Semestre'),
        ('trimestre1', 'Primer Trimestre'),
        ('trimestre2', 'Segundo Trimestre'),
        ('trimestre3', 'Tercer Trimestre'),
        ('bimestre1', 'Primer Bimestre'),
        ('bimestre2', 'Segundo Bimestre'),
        ('bimestre3', 'Tercer Bimestre'),
        ('bimestre4', 'Cuarto Bimestre'),
    ]
    
    TIPOS_EVALUACION = [
        ('formativa', 'Formativa'),
        ('sumativa', 'Sumativa'),
        ('diagnostica', 'Diagnóstica'),
        ('acumulativa', 'Acumulativa'),
    ]
    
    id_evaluacion = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='evaluaciones')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='evaluaciones')
    nombre = models.CharField(max_length=200)
    fecha_evaluacion = models.DateField()
    ponderacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text='Porcentaje de peso en el promedio (0-100%)'
    )
    periodo = models.CharField(max_length=20, choices=PERIODOS, null=True, blank=True)
    tipo_evaluacion = models.CharField(max_length=20, choices=TIPOS_EVALUACION, default='sumativa')
    es_recuperacion = models.BooleanField(default=False)
    evaluacion_original = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recuperaciones'
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    actividades_resolubles = GenericRelation(
        'ActividadResoluble',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='evaluacion_resoluble',
    )
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'evaluacion'
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'
        ordering = ['-fecha_evaluacion']

    def __str__(self):
        return f"{self.nombre} - {self.clase} - {self.fecha_evaluacion}"


class Calificacion(models.Model):
    """Calificaciones/notas de estudiantes en evaluaciones"""
    id_calificacion = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='calificaciones')
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='calificaciones')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notas')
    nota = models.DecimalField(max_digits=3, decimal_places=1)  # 1.0 - 7.0
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='calificaciones_registradas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='calificaciones_actualizadas',
        null=True,
        blank=True
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'calificacion'
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
        unique_together = ('evaluacion', 'estudiante')
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.evaluacion.nombre}: {self.nota}"

    def clean(self):
        """Valida la nota contra la escala configurada del colegio."""
        from django.core.exceptions import ValidationError
        from backend.apps.institucion.models import ConfiguracionAcademica
        from backend.common.utils.grade_scale import normalize_grade_value

        super().clean()

        if self.nota is not None:
            self.nota = normalize_grade_value(self.nota)
            if self.colegio_id:
                escala = ConfiguracionAcademica.get_escala_para_colegio(self.colegio)
                if self.nota < escala['nota_minima'] or self.nota > escala['nota_maxima']:
                    raise ValidationError({
                        'nota': f"La nota debe estar entre {escala['nota_minima']} y {escala['nota_maxima']} "
                                f"según la configuración del colegio."
                    })

    def save(self, *args, **kwargs):
        from backend.common.utils.grade_scale import normalize_grade_value
        if self.nota is not None:
            self.nota = normalize_grade_value(self.nota)
        super().save(*args, **kwargs)

    def get_nota_efectiva(self):
        """Retorna la nota efectiva considerando recuperaciones"""
        if not self.evaluacion.es_recuperacion and self.evaluacion.recuperaciones.exists():
            # Buscar si este estudiante tiene nota en alguna recuperación
            recuperacion = Calificacion.objects.filter(
                evaluacion__evaluacion_original=self.evaluacion,
                estudiante=self.estudiante
            ).order_by('-nota').first()
            
            if recuperacion and recuperacion.nota > self.nota:
                return recuperacion.nota
        
        return self.nota


class RegistroClase(models.Model):
    """Acta diaria de clase para libro de clases digital."""

    id_registro = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='registros_clase')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='registros_clase')
    profesor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='registros_clase')
    fecha = models.DateField()
    numero_clase = models.PositiveIntegerField(default=1)
    contenido_tratado = models.TextField()
    tarea_asignada = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    firmado = models.BooleanField(default=False)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    hash_contenido = models.CharField(max_length=64, blank=True, default='')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'registro_clase'
        verbose_name = 'Registro de Clase'
        verbose_name_plural = 'Registros de Clase'
        ordering = ['-fecha', '-numero_clase']
        unique_together = ('clase', 'fecha', 'numero_clase')

    def __str__(self):
        return f"{self.clase} - {self.fecha} - Bloque {self.numero_clase}"

    def _contenido_firma_payload(self):
        payload = {
            'clase_id': self.clase_id,
            'colegio_id': self.colegio_id,
            'profesor_id': self.profesor_id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'numero_clase': self.numero_clase,
            'contenido_tratado': self.contenido_tratado,
            'tarea_asignada': self.tarea_asignada or '',
            'observaciones': self.observaciones or '',
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=True)

    def compute_hash_contenido(self):
        return hashlib.sha256(self._contenido_firma_payload().encode('utf-8')).hexdigest()

    def clean(self):
        if not self.pk:
            return

        current = RegistroClase._base_manager.filter(pk=self.pk).values(
            'firmado',
            'clase_id',
            'colegio_id',
            'profesor_id',
            'fecha',
            'numero_clase',
            'contenido_tratado',
            'tarea_asignada',
            'observaciones',
            'hash_contenido',
        ).first()
        if not current or not current['firmado']:
            return

        blocked_fields_changed = any(
            [
                current['clase_id'] != self.clase_id,
                current['colegio_id'] != self.colegio_id,
                current['profesor_id'] != self.profesor_id,
                current['fecha'] != self.fecha,
                current['numero_clase'] != self.numero_clase,
                current['contenido_tratado'] != self.contenido_tratado,
                (current['tarea_asignada'] or '') != (self.tarea_asignada or ''),
                (current['observaciones'] or '') != (self.observaciones or ''),
            ]
        )
        if blocked_fields_changed:
            raise ValidationError('El registro de clase firmado es inmutable y no puede editarse.')

    def firmar(self, *, profesor, ip_address='', user_agent=''):
        if self.firmado:
            raise ValidationError('El registro de clase ya se encuentra firmado.')

        timestamp = timezone.now()
        self.hash_contenido = self.compute_hash_contenido()
        self.firmado = True
        self.fecha_firma = timestamp
        self.save(update_fields=['hash_contenido', 'firmado', 'fecha_firma', 'fecha_actualizacion'])

        FirmaRegistroClase.objects.update_or_create(
            registro_clase=self,
            defaults={
                'profesor': profesor,
                'estado': 'FIRMADO',
                'firma_hash': self.hash_contenido,
                'ip_address': ip_address,
                'user_agent': (user_agent or '')[:255],
                'timestamp_servidor': timestamp,
            },
        )


class FirmaRegistroClase(models.Model):
    """Firma de docente sobre registro de clase."""

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('FIRMADO', 'Firmado'),
        ('RECTIFICADO', 'Rectificado'),
    ]

    id_firma = models.AutoField(primary_key=True)
    registro_clase = models.OneToOneField(
        RegistroClase,
        on_delete=models.CASCADE,
        related_name='firma_docente',
    )
    profesor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='firmas_registro_clase')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    firma_hash = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default='')
    timestamp_servidor = models.DateTimeField(default=timezone.now)
    objects = TenantManager(school_field='registro_clase__colegio_id')

    class Meta:
        db_table = 'firma_registro_clase'
        verbose_name = 'Firma de Registro de Clase'
        verbose_name_plural = 'Firmas de Registro de Clase'
        ordering = ['-timestamp_servidor']

    def __str__(self):
        return f"Firma {self.registro_clase_id} - {self.estado}"


class MaterialClase(models.Model):
    """Materiales y archivos de clase"""
    TIPOS_ARCHIVO = [
        ('documento', 'Documento'),
        ('presentacion', 'Presentación'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('imagen', 'Imagen'),
        ('otro', 'Otro'),
    ]
    
    id_material = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='materiales')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='materiales')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    archivo = models.FileField(upload_to='materiales/%Y/%m/')
    tipo_archivo = models.CharField(max_length=20, choices=TIPOS_ARCHIVO, default='documento')
    es_publico = models.BooleanField(default=True, help_text='Si es público, los estudiantes pueden verlo')
    tamanio_bytes = models.BigIntegerField(default=0)
    subido_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='materiales_subidos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'material_clase'
        verbose_name = 'Material de Clase'
        verbose_name_plural = 'Materiales de Clase'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.clase}"
    
    def get_extension(self):
        """Retorna la extensión del archivo"""
        import os
        return os.path.splitext(self.archivo.name)[1].lower()
    
    def get_icono(self):
        """Retorna el ícono según el tipo de archivo"""
        iconos = {
            'documento': '📄',
            'presentacion': '📊',
            'video': '🎥',
            'audio': '🎵',
            'imagen': '🖼️',
            'otro': '📎',
        }
        return iconos.get(self.tipo_archivo, '📎')
    
    def get_tamanio_legible(self):
        """Retorna el tamaño en formato legible (KB, MB, GB)"""
        size = self.tamanio_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class Tarea(models.Model):
    """Tareas asignadas por el profesor"""
    id_tarea = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='tareas')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='tareas')
    titulo = models.CharField(max_length=150)
    instrucciones = models.TextField()
    archivo_instrucciones = models.FileField(
        upload_to='tareas/instrucciones/%Y/%m/',
        blank=True,
        null=True
    )
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField()
    es_publica = models.BooleanField(default=True)
    creada_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tareas_creadas')
    activa = models.BooleanField(default=True)
    actividades_resolubles = GenericRelation(
        'ActividadResoluble',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='tarea_resoluble',
    )
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'tarea'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['-fecha_entrega']
    
    def __str__(self):
        return f"{self.titulo} - {self.clase}"
    
    def esta_vencida(self):
        """Verifica si la tarea está vencida"""
        if not self.fecha_entrega:
            return False
        return timezone.now() > self.fecha_entrega
    
    def dias_restantes(self):
        """Calcula los días restantes para entregar"""
        if not self.fecha_entrega:
            return 0
        delta = self.fecha_entrega - timezone.now()
        return delta.days if delta.days >= 0 else 0


class EntregaTarea(models.Model):
    """Entregas de tareas por parte de los estudiantes"""
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('entregada', 'Entregada'),
        ('revisada', 'Revisada'),
        ('tarde', 'Entrega Tardía'),
    ]
    
    id_entrega = models.AutoField(primary_key=True)
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='entregas')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entregas_tareas')
    archivo = models.FileField(upload_to='tareas/entregas/%Y/%m/', null=True, blank=True)
    comentario_estudiante = models.TextField(blank=True, null=True)
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    calificacion = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    retroalimentacion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='entregada')
    revisada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tareas_revisadas'
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)
    objects = TenantManager(school_field='tarea__colegio_id')
    
    class Meta:
        db_table = 'entrega_tarea'
        verbose_name = 'Entrega de Tarea'
        verbose_name_plural = 'Entregas de Tareas'
        ordering = ['-fecha_entrega']
        unique_together = ('tarea', 'estudiante')
    
    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.tarea.titulo}"
    
    def fue_entregada_tarde(self):
        """Verifica si la entrega fue tardía"""
        return self.fecha_entrega > self.tarea.fecha_entrega
    
    def get_tamanio_archivo(self):
        """Retorna el tamaño del archivo en formato legible"""
        try:
            size = self.archivo.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except:
            return "N/A"


class ActividadResoluble(models.Model):
    """Capa común para tareas y evaluaciones con resolución PDF u online."""

    MODALIDADES = [
        ('PDF', 'PDF'),
        ('ONLINE', 'Online'),
        ('MIXTA', 'Mixta'),
    ]

    ESTADOS = [
        ('BORRADOR', 'Borrador'),
        ('PUBLICADA', 'Publicada'),
        ('EN_REVISION', 'En revisión'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
    ]

    id_actividad_resoluble = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='actividades_resolubles')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    actividad = GenericForeignKey('content_type', 'object_id')
    titulo = models.CharField(max_length=200, blank=True, default='')
    modalidad = models.CharField(max_length=10, choices=MODALIDADES, default='PDF')
    archivo_pdf = models.FileField(upload_to='actividades/pdf/%Y/%m/', blank=True, null=True)
    requiere_aprobacion_docente = models.BooleanField(default=True)
    auto_correccion_activa = models.BooleanField(default=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR')
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'actividad_resoluble'
        verbose_name = 'Actividad Resoluble'
        verbose_name_plural = 'Actividades Resolubles'
        unique_together = ('content_type', 'object_id')
        ordering = ['-fecha_creacion']

    def __str__(self):
        etiqueta = self.titulo or getattr(self.actividad, 'titulo', None) or getattr(self.actividad, 'nombre', None) or 'Actividad'
        return f"{etiqueta} - {self.get_modalidad_display()}"

    def es_online(self):
        return self.modalidad in {'ONLINE', 'MIXTA'}

    def tiene_pdf(self):
        return bool(self.archivo_pdf)


class PreguntaResoluble(models.Model):
    """Pregunta configurable para resolución online."""

    TIPOS = [
        ('opcion_multiple', 'Opción múltiple'),
        ('respuesta_corta', 'Respuesta corta'),
        ('abierta', 'Abierta'),
    ]

    id_pregunta = models.AutoField(primary_key=True)
    actividad_resoluble = models.ForeignKey(
        ActividadResoluble,
        on_delete=models.CASCADE,
        related_name='preguntas',
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, default='opcion_multiple')
    enunciado = models.TextField()
    orden = models.PositiveIntegerField(default=1)
    puntaje_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'))
    respuesta_correcta_texto = models.TextField(blank=True, default='')
    respuesta_correcta_normalizada = models.TextField(blank=True, default='')
    requiere_revision_docente = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)
    objects = TenantManager(school_field='actividad_resoluble__colegio_id')

    class Meta:
        db_table = 'pregunta_resoluble'
        verbose_name = 'Pregunta Resoluble'
        verbose_name_plural = 'Preguntas Resolubles'
        ordering = ['orden', 'id_pregunta']

    def __str__(self):
        return f"P{self.orden} - {self.actividad_resoluble}"

    def clean(self):
        super().clean()
        if self.pk and self.tipo != 'opcion_multiple' and self.opciones.exists():
            raise ValidationError('Solo las preguntas de opción múltiple pueden tener opciones.')

    def es_objetiva(self):
        return self.tipo in {'opcion_multiple', 'respuesta_corta'} and not self.requiere_revision_docente


class OpcionPreguntaResoluble(models.Model):
    """Opciones disponibles para una pregunta de opción múltiple."""

    id_opcion = models.AutoField(primary_key=True)
    pregunta = models.ForeignKey(
        PreguntaResoluble,
        on_delete=models.CASCADE,
        related_name='opciones',
    )
    texto = models.CharField(max_length=300)
    es_correcta = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'opcion_pregunta_resoluble'
        verbose_name = 'Opción de Pregunta Resoluble'
        verbose_name_plural = 'Opciones de Preguntas Resolubles'
        ordering = ['orden', 'id_opcion']

    def __str__(self):
        return f"Opción {self.orden} - {self.pregunta_id}"


class IntentoResoluble(models.Model):
    """Intento de resolución para una tarea o evaluación."""

    ESTADOS = [
        ('BORRADOR', 'Borrador'),
        ('ENVIADO', 'Enviado'),
        ('AUTOCORREGIDO', 'Autocorregido'),
        ('PENDIENTE_APROBACION', 'Pendiente de aprobación'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    id_intento = models.AutoField(primary_key=True)
    actividad_resoluble = models.ForeignKey(
        ActividadResoluble,
        on_delete=models.CASCADE,
        related_name='intentos',
    )
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intentos_resolubles')
    estado = models.CharField(max_length=30, choices=ESTADOS, default='BORRADOR')
    puntaje_maximo = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    puntaje_obtenido = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    nota_sugerida = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    retroalimentacion = models.TextField(blank=True, default='')
    requiere_revision_docente = models.BooleanField(default=False)
    aprobado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intentos_resolubles_aprobados',
    )
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    resultado_publicado = models.OneToOneField(
        'Calificacion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='origen_intento_resoluble',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='actividad_resoluble__colegio_id')

    class Meta:
        db_table = 'intento_resoluble'
        verbose_name = 'Intento Resoluble'
        verbose_name_plural = 'Intentos Resolubles'
        unique_together = ('actividad_resoluble', 'estudiante')
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.actividad_resoluble}"

    def recalcular_resultado(self):
        total = Decimal('0.00')
        maximo = Decimal('0.00')
        requiere_revision = False

        for respuesta in self.respuestas.select_related('pregunta').all():
            maximo += respuesta.pregunta.puntaje_maximo or Decimal('0.00')
            total += respuesta.puntaje_obtenido or Decimal('0.00')
            if respuesta.pregunta.requiere_revision_docente or respuesta.pregunta.tipo == 'abierta':
                requiere_revision = True

        self.puntaje_maximo = maximo
        self.puntaje_obtenido = total
        self.requiere_revision_docente = requiere_revision
        if maximo > 0:
            self.nota_sugerida = (Decimal('1.0') + (Decimal('6.0') * (total / maximo))).quantize(Decimal('0.1'))
        else:
            self.nota_sugerida = None

        if self.estado == 'BORRADOR':
            self.estado = 'PENDIENTE_APROBACION' if requiere_revision else 'AUTOCORREGIDO'

    def aprobar(self, *, profesor, retroalimentacion=''):
        self.aprobado_por = profesor
        self.retroalimentacion = retroalimentacion or self.retroalimentacion
        self.estado = 'APROBADO'
        self.fecha_aprobacion = timezone.now()
        self.fecha_revision = self.fecha_revision or self.fecha_aprobacion
        self.save(update_fields=['aprobado_por', 'retroalimentacion', 'estado', 'fecha_aprobacion', 'fecha_revision', 'fecha_actualizacion'])


class RespuestaResoluble(models.Model):
    """Respuesta del estudiante para una pregunta resoluble."""

    id_respuesta = models.AutoField(primary_key=True)
    intento = models.ForeignKey(
        IntentoResoluble,
        on_delete=models.CASCADE,
        related_name='respuestas',
    )
    pregunta = models.ForeignKey(
        PreguntaResoluble,
        on_delete=models.CASCADE,
        related_name='respuestas',
    )
    respuesta_texto = models.TextField(blank=True, default='')
    opcion_seleccionada = models.ForeignKey(
        OpcionPreguntaResoluble,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='respuestas',
    )
    es_correcta = models.BooleanField(default=False)
    puntaje_obtenido = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    observaciones = models.TextField(blank=True, default='')
    revisado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='respuestas_resolubles_revisadas',
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)

    objects = TenantManager(school_field='intento__actividad_resoluble__colegio_id')

    class Meta:
        db_table = 'respuesta_resoluble'
        verbose_name = 'Respuesta Resoluble'
        verbose_name_plural = 'Respuestas Resolubles'
        unique_together = ('intento', 'pregunta')
        ordering = ['pregunta__orden', 'id_respuesta']

    def __str__(self):
        return f"{self.intento_id} - {self.pregunta_id}"

    def normalizar_respuesta(self):
        texto = (self.respuesta_texto or '').strip().lower()
        return ' '.join(texto.split())


class InformeAcademico(models.Model):
    """Informes académicos (boletines) de estudiantes"""
    PERIODOS = [
        ('semestre1', 'Primer Semestre'),
        ('semestre2', 'Segundo Semestre'),
        ('trimestre1', 'Primer Trimestre'),
        ('trimestre2', 'Segundo Trimestre'),
        ('trimestre3', 'Tercer Trimestre'),
        ('anual', 'Informe Anual'),
    ]
    
    id_informe = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='informes_academicos')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='informes_academicos')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='informes_academicos')
    periodo = models.CharField(max_length=20, choices=PERIODOS)
    anio_escolar = models.IntegerField()
    
    # Datos calculados
    promedio_general = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    porcentaje_asistencia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ranking_curso = models.IntegerField(null=True, blank=True)
    total_estudiantes_curso = models.IntegerField(null=True, blank=True)
    
    # Comentarios
    comentario_general = models.TextField(null=True, blank=True)
    comentario_profesor_jefe = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    
    # Metadata
    generado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='informes_generados')
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'informe_academico'
        verbose_name = 'Informe Académico'
        verbose_name_plural = 'Informes Académicos'
        unique_together = ('estudiante', 'periodo', 'anio_escolar')
        ordering = ['-anio_escolar', '-periodo']
    
    def __str__(self):
        return f"Informe {self.estudiante.get_full_name()} - {self.get_periodo_display()} {self.anio_escolar}"


class DetalleInformeAcademico(models.Model):
    """Detalle de notas por asignatura en el informe académico"""
    id_detalle = models.AutoField(primary_key=True)
    informe = models.ForeignKey(InformeAcademico, on_delete=models.CASCADE, related_name='detalles')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE)
    profesor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='detalles_informe_profesor')
    
    # Notas
    nota_final = models.DecimalField(max_digits=3, decimal_places=1)
    nota_parcial_1 = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    nota_parcial_2 = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    nota_parcial_3 = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    
    # Asistencia específica de la asignatura
    clases_asistidas = models.IntegerField(default=0)
    total_clases = models.IntegerField(default=0)
    porcentaje_asistencia_asignatura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Comentario del profesor
    comentario_profesor = models.TextField(null=True, blank=True)
    objects = TenantManager(school_field='informe__colegio_id')
    
    class Meta:
        db_table = 'detalle_informe_academico'
        verbose_name = 'Detalle de Informe Académico'
        verbose_name_plural = 'Detalles de Informes Académicos'
        ordering = ['asignatura__nombre']
    
    def __str__(self):
        return f"{self.informe.estudiante.get_full_name()} - {self.asignatura.nombre}"

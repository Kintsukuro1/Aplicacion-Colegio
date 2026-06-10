# comunicados/models.py
from django.db import models
from django.utils import timezone
from backend.apps.institucion.models import Colegio
from backend.apps.cursos.models import Curso
from backend.apps.accounts.models import User
from backend.common.tenancy import TenantManager


class Comunicado(models.Model):
    """
    Modelo para comunicados y circulares del colegio.
    """
    TIPOS = [
        ('comunicado', '📋 Comunicado General'),
        ('evento', '📅 Evento'),
        ('citacion', '👥 Citación de Apoderados'),
        ('noticia', '📰 Noticia'),
        ('urgente', '🚨 Urgente'),
    ]
    
    DESTINATARIOS = [
        ('todos', 'Todos (Profesores, Estudiantes y Apoderados)'),
        ('profesores', 'Solo Profesores'),
        ('estudiantes', 'Solo Estudiantes'),
        ('apoderados', 'Solo Apoderados'),
        ('curso_especifico', 'Curso Específico'),
    ]
    
    id_comunicado = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='comunicados')
    
    # Información básica
    tipo = models.CharField(max_length=20, choices=TIPOS, default='comunicado')
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    
    # Destinatarios
    destinatario = models.CharField(max_length=20, choices=DESTINATARIOS, default='todos')
    cursos_destinatarios = models.ManyToManyField(Curso, blank=True, related_name='comunicados_recibidos')
    
    # Archivos adjuntos
    archivo_adjunto = models.FileField(
        upload_to='comunicados/%Y/%m/',
        null=True,
        blank=True,
        help_text='Archivo adjunto (PDF, imágenes, documentos)'
    )
    
    # Para eventos y citaciones
    fecha_evento = models.DateTimeField(null=True, blank=True, help_text='Para eventos o citaciones')
    lugar_evento = models.CharField(max_length=200, null=True, blank=True)
    requiere_confirmacion = models.BooleanField(default=False, help_text='¿Requiere confirmación de lectura?')
    
    # Prioridad y estado
    es_prioritario = models.BooleanField(default=False)
    es_destacado = models.BooleanField(default=False, help_text='Aparece en banner principal')
    activo = models.BooleanField(default=True)
    
    # Metadata
    publicado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='comunicados_publicados')
    fecha_publicacion = models.DateTimeField(default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'comunicado'
        ordering = ['-fecha_publicacion']
        verbose_name = 'Comunicado'
        verbose_name_plural = 'Comunicados'
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"
    
    def get_destinatarios_count(self):
        """Retorna el número aproximado de destinatarios"""
        if self.destinatario == 'curso_especifico':
            return self.cursos_destinatarios.count()
        # Esto se puede calcular según usuarios activos
        return 0
    
    def get_confirmaciones_count(self):
        """Retorna el número de confirmaciones de lectura"""
        return self.confirmaciones.filter(leido=True).count()


class ConfirmacionLectura(models.Model):
    """
    Registro de confirmación de lectura de comunicados.
    """
    id_confirmacion = models.AutoField(primary_key=True)
    comunicado = models.ForeignKey(Comunicado, on_delete=models.CASCADE, related_name='confirmaciones')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comunicados_leidos')
    
    leido = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    confirmado = models.BooleanField(default=False, help_text='Para citaciones que requieren confirmación')
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    
    observaciones = models.TextField(null=True, blank=True)
    objects = TenantManager(school_field='comunicado__colegio_id')
    
    class Meta:
        unique_together = ('comunicado', 'usuario')
        verbose_name = 'Confirmación de Lectura'
        verbose_name_plural = 'Confirmaciones de Lectura'
        db_table = 'confirmacion_lectura'
        ordering = ['-fecha_lectura']
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.comunicado.titulo}"
    
    def marcar_como_leido(self):
        """Marca el comunicado como leído"""
        if not self.leido:
            self.leido = True
            self.fecha_lectura = timezone.now()
            self.save()
    
    def confirmar_asistencia(self):
        """Confirma asistencia a un evento o citación"""
        if not self.confirmado:
            self.confirmado = True
            self.fecha_confirmacion = timezone.now()
            self.save()


class AdjuntoComunicado(models.Model):
    """
    Archivos adjuntos adicionales para comunicados (múltiples archivos).
    """
    id_adjunto = models.AutoField(primary_key=True)
    comunicado = models.ForeignKey(Comunicado, on_delete=models.CASCADE, related_name='adjuntos_adicionales')
    
    archivo = models.FileField(upload_to='comunicados/adjuntos/%Y/%m/')
    nombre_archivo = models.CharField(max_length=200)
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    tamanio_bytes = models.BigIntegerField(default=0)
    tipo_mime = models.CharField(max_length=100, null=True, blank=True)
    
    fecha_subida = models.DateTimeField(auto_now_add=True)
    objects = TenantManager(school_field='comunicado__colegio_id')
    
    class Meta:
        verbose_name = 'Adjunto de Comunicado'
        verbose_name_plural = 'Adjuntos de Comunicados'
    
    def __str__(self):
        return f"{self.nombre_archivo} - {self.comunicado.titulo}"
    
    def get_tamanio_legible(self):
        """Retorna el tamaño del archivo en formato legible"""
        size = self.tamanio_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class PlantillaComunicado(models.Model):
    """
    Plantillas predefinidas para comunicados recurrentes
    Permite usar variables como {{nombre_estudiante}}, {{curso}}, etc.
    """
    CATEGORIAS = [
        ('general', '📋 General'),
        ('eventos', '📅 Eventos'),
        ('citaciones', '👥 Citaciones'),
        ('informes', '📊 Informes'),
        ('recordatorios', '⏰ Recordatorios'),
        ('emergencias', '🚨 Emergencias'),
    ]
    
    id_plantilla = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='plantillas_comunicados')
    
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Plantilla',
        help_text='Nombre descriptivo de la plantilla'
    )
    
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        default='general',
        verbose_name='Categoría'
    )
    
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Descripción breve de cuándo usar esta plantilla'
    )
    
    # Contenido de la plantilla
    titulo_plantilla = models.CharField(
        max_length=200,
        verbose_name='Título',
        help_text='Puede incluir variables: {{nombre}}, {{curso}}, {{fecha}}, etc.'
    )
    
    contenido_plantilla = models.TextField(
        verbose_name='Contenido',
        help_text='Usa variables entre llaves: {{variable}}. Disponibles: {{nombre_estudiante}}, {{curso}}, {{fecha}}, {{hora}}, {{lugar}}, {{nombre_apoderado}}, {{rut_estudiante}}, {{nombre_colegio}}'
    )
    
    # Configuración predeterminada
    tipo_default = models.CharField(
        max_length=20,
        choices=Comunicado.TIPOS,
        default='comunicado',
        verbose_name='Tipo por Defecto'
    )
    
    destinatario_default = models.CharField(
        max_length=20,
        choices=Comunicado.DESTINATARIOS,
        default='todos',
        verbose_name='Destinatario por Defecto'
    )
    
    requiere_confirmacion_default = models.BooleanField(
        default=False,
        verbose_name='Requiere Confirmación por Defecto'
    )
    
    es_prioritario_default = models.BooleanField(
        default=False,
        verbose_name='Es Prioritario por Defecto'
    )
    
    # Metadata
    activa = models.BooleanField(default=True, verbose_name='Activa')
    veces_usada = models.PositiveIntegerField(
        default=0,
        verbose_name='Veces Usada',
        help_text='Contador automático de usos'
    )
    
    creada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='plantillas_creadas'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        ordering = ['categoria', 'nombre']
        verbose_name = 'Plantilla de Comunicado'
        verbose_name_plural = 'Plantillas de Comunicados'
        indexes = [
            models.Index(fields=['colegio', 'activa']),
            models.Index(fields=['categoria']),
        ]
    
    def __str__(self):
        return f"{self.get_categoria_display()} - {self.nombre}"
    
    def incrementar_contador_uso(self):
        """Incrementa el contador de usos"""
        self.veces_usada += 1
        self.save(update_fields=['veces_usada'])
    
    def get_variables_disponibles(self):
        """Retorna lista de variables disponibles para esta plantilla"""
        return [
            '{{nombre_estudiante}}',
            '{{curso}}',
            '{{fecha}}',
            '{{hora}}',
            '{{lugar}}',
            '{{nombre_apoderado}}',
            '{{rut_estudiante}}',
            '{{nombre_colegio}}',
            '{{direccion_colegio}}',
            '{{telefono_colegio}}',
        ]
    
    def renderizar(self, contexto=None):
        """
        Renderiza la plantilla reemplazando variables con valores reales
        
        Args:
            contexto (dict): Diccionario con valores para reemplazar
                Ejemplo: {'nombre_estudiante': 'Juan Pérez', 'curso': '3° Básico A'}
        
        Returns:
            tuple: (titulo_renderizado, contenido_renderizado)
        """
        if contexto is None:
            contexto = {}
        
        # Agregar valores por defecto
        from django.utils import timezone
        if 'fecha' not in contexto:
            contexto['fecha'] = timezone.now().strftime('%d/%m/%Y')
        if 'hora' not in contexto:
            contexto['hora'] = timezone.now().strftime('%H:%M')
        
        titulo = self.titulo_plantilla
        contenido = self.contenido_plantilla
        
        # Reemplazar variables
        for key, value in contexto.items():
            placeholder = '{{' + key + '}}'
            titulo = titulo.replace(placeholder, str(value))
            contenido = contenido.replace(placeholder, str(value))
        
        return titulo, contenido


class EstadisticaComunicado(models.Model):
    """
    Estadísticas agregadas de alcance y lectura de comunicados
    Se actualiza periódicamente o al solicitar estadísticas
    """
    id_estadistica = models.AutoField(primary_key=True)
    comunicado = models.OneToOneField(
        Comunicado,
        on_delete=models.CASCADE,
        related_name='estadisticas'
    )
    
    # Alcance
    total_destinatarios = models.PositiveIntegerField(
        default=0,
        verbose_name='Total de Destinatarios',
        help_text='Número total de usuarios a los que se envió'
    )
    
    # Lectura
    total_leidos = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Leídos',
        help_text='Número de usuarios que leyeron el comunicado'
    )
    
    porcentaje_lectura = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Porcentaje de Lectura'
    )
    
    # Confirmaciones (para citaciones/eventos)
    total_confirmados = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Confirmados',
        help_text='Número de usuarios que confirmaron asistencia'
    )
    
    porcentaje_confirmacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Porcentaje de Confirmación'
    )
    
    # Desglose por rol
    destinatarios_profesores = models.PositiveIntegerField(default=0)
    leidos_profesores = models.PositiveIntegerField(default=0)
    
    destinatarios_estudiantes = models.PositiveIntegerField(default=0)
    leidos_estudiantes = models.PositiveIntegerField(default=0)
    
    destinatarios_apoderados = models.PositiveIntegerField(default=0)
    leidos_apoderados = models.PositiveIntegerField(default=0)
    
    # Tiempos promedio
    tiempo_promedio_lectura_horas = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name='Tiempo Promedio de Lectura (horas)',
        help_text='Tiempo promedio entre publicación y primera lectura'
    )
    
    # Metadata
    fecha_calculo = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Actualización'
    )
    objects = TenantManager(school_field='comunicado__colegio_id')
    
    class Meta:
        verbose_name = 'Estadística de Comunicado'
        verbose_name_plural = 'Estadísticas de Comunicados'
    
    def __str__(self):
        return f"Estadísticas: {self.comunicado.titulo}"
    
    def calcular_estadisticas(self):
        """
        Calcula y actualiza todas las estadísticas del comunicado
        """
        from django.db.models import Count, Q, Avg
        from datetime import timedelta
        
        comunicado = self.comunicado
        
        # Total de destinatarios (confirmaciones creadas)
        confirmaciones = ConfirmacionLectura.objects.filter(comunicado=comunicado)
        self.total_destinatarios = confirmaciones.count()
        
        # Total leídos
        confirmaciones_leidas = confirmaciones.filter(leido=True)
        self.total_leidos = confirmaciones_leidas.count()
        
        # Porcentaje de lectura
        if self.total_destinatarios > 0:
            self.porcentaje_lectura = (self.total_leidos / self.total_destinatarios) * 100
        else:
            self.porcentaje_lectura = 0
        
        # Total confirmados (si requiere confirmación)
        if comunicado.requiere_confirmacion:
            confirmaciones_confirmadas = confirmaciones.filter(confirmado=True)
            self.total_confirmados = confirmaciones_confirmadas.count()
            
            if self.total_destinatarios > 0:
                self.porcentaje_confirmacion = (self.total_confirmados / self.total_destinatarios) * 100
            else:
                self.porcentaje_confirmacion = 0
        
        # Desglose por perfil de dominio
        # Profesores
        confirmaciones_profesores = confirmaciones.filter(usuario__perfil_profesor__isnull=False)
        self.destinatarios_profesores = confirmaciones_profesores.count()
        self.leidos_profesores = confirmaciones_profesores.filter(leido=True).count()
        
        # Estudiantes
        confirmaciones_estudiantes = confirmaciones.filter(usuario__perfil_estudiante__isnull=False)
        self.destinatarios_estudiantes = confirmaciones_estudiantes.count()
        self.leidos_estudiantes = confirmaciones_estudiantes.filter(leido=True).count()
        
        # Apoderados
        confirmaciones_apoderados = confirmaciones.filter(usuario__perfil_apoderado__isnull=False)
        self.destinatarios_apoderados = confirmaciones_apoderados.count()
        self.leidos_apoderados = confirmaciones_apoderados.filter(leido=True).count()
        
        # Tiempo promedio de lectura
        if confirmaciones_leidas.exists():
            tiempos = []
            for conf in confirmaciones_leidas.filter(fecha_lectura__isnull=False):
                if conf.fecha_lectura and comunicado.fecha_publicacion:
                    diff = conf.fecha_lectura - comunicado.fecha_publicacion
                    tiempos.append(diff.total_seconds() / 3600)  # Convertir a horas
            
            if tiempos:
                self.tiempo_promedio_lectura_horas = sum(tiempos) / len(tiempos)
        
        self.save()
        return self
    
    def get_porcentaje_lectura_por_rol(self, rol):
        """
        Retorna el porcentaje de lectura para un rol específico
        
        Args:
            rol (str): 'profesores', 'estudiantes' o 'apoderados'
        """
        if rol == 'profesores':
            if self.destinatarios_profesores > 0:
                return (self.leidos_profesores / self.destinatarios_profesores) * 100
        elif rol == 'estudiantes':
            if self.destinatarios_estudiantes > 0:
                return (self.leidos_estudiantes / self.destinatarios_estudiantes) * 100
        elif rol == 'apoderados':
            if self.destinatarios_apoderados > 0:
                return (self.leidos_apoderados / self.destinatarios_apoderados) * 100
        return 0

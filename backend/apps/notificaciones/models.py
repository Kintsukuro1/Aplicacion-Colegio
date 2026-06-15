"""
Modelos del modulo Notificaciones.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from backend.common.tenancy import TenantManager


class Notificacion(models.Model):
    """Notificaciones del sistema para usuarios."""

    TIPO_CHOICES = [
        ('calificacion', 'Nueva Calificacion'),
        ('asistencia', 'Registro de Asistencia'),
        ('evaluacion', 'Nueva Evaluacion'),
        ('alerta', 'Alerta Academica'),
        ('sistema', 'Informacion del Sistema'),
        ('tarea_nueva', 'Nueva Tarea'),
        ('tarea_entregada', 'Tarea Entregada'),
        ('tarea_calificada', 'Tarea Calificada'),
        ('anuncio_nuevo', 'Nuevo Anuncio'),
        ('mensaje_nuevo', 'Mensaje Nuevo'),
        ('comunicado_nuevo', 'Nuevo Comunicado'),
        ('evento_nuevo', 'Nuevo Evento'),
        ('citacion_nueva', 'Nueva Citacion'),
        ('noticia_nueva', 'Nueva Noticia'),
        ('urgente_nuevo', 'Comunicado Urgente'),
    ]

    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        verbose_name='Destinatario',
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    titulo = models.CharField(max_length=200, verbose_name='Titulo')
    mensaje = models.TextField(verbose_name='Mensaje')
    enlace = models.CharField(max_length=300, blank=True, null=True, verbose_name='Enlace')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='normal', verbose_name='Prioridad')
    leido = models.BooleanField(default=False, verbose_name='Leido')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creacion')
    fecha_lectura = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Lectura')
    objects = TenantManager(school_field='destinatario__rbd_colegio')

    class Meta:
        db_table = 'notificacion'
        verbose_name = 'Notificacion'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['destinatario', 'fecha_creacion']),
            models.Index(fields=['destinatario', 'leido']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo} ({self.destinatario.get_full_name()})"

    def marcar_como_leido(self):
        """Marca la notificacion como leida."""
        from django.utils import timezone

        if not self.leido:
            self.leido = True
            self.fecha_lectura = timezone.now()
            self.save(update_fields=['leido', 'fecha_lectura'])


class PreferenciaNotificacion(models.Model):
    """Preferencias de notificacion por usuario y tipo."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferencias_notificacion',
        verbose_name='Usuario',
    )

    tipo_notificacion = models.CharField(
        max_length=20,
        choices=Notificacion.TIPO_CHOICES,
        verbose_name='Tipo de Notificacion',
    )

    canal_web = models.BooleanField(default=True, verbose_name='Web/Aplicacion')
    canal_email = models.BooleanField(default=False, verbose_name='Correo Electronico')
    canal_push = models.BooleanField(default=True, verbose_name='Notificacion Push')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Ultima Modificacion')
    objects = TenantManager(school_field='usuario__rbd_colegio')

    class Meta:
        db_table = 'preferencia_notificacion'
        verbose_name = 'Preferencia de Notificacion'
        verbose_name_plural = 'Preferencias de Notificaciones'
        unique_together = [['usuario', 'tipo_notificacion']]
        ordering = ['usuario', 'tipo_notificacion']

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_tipo_notificacion_display()}"

    @staticmethod
    def obtener_o_crear_defecto(usuario, tipo_notificacion):
        """Obtiene la preferencia o crea una con valores por defecto."""
        preferencia, _created = PreferenciaNotificacion.objects.get_or_create(
            usuario=usuario,
            tipo_notificacion=tipo_notificacion,
            defaults={
                'canal_web': True,
                'canal_email': tipo_notificacion in ['urgente_nuevo', 'citacion_nueva', 'alerta'],
                'canal_push': tipo_notificacion not in ['mensaje_nuevo'],
                'activo': True,
            },
        )
        return preferencia

    def puede_enviar_por_canal(self, canal):
        """Verifica si se puede enviar por el canal especificado."""
        if not self.activo:
            return False

        canal_map = {
            'web': self.canal_web,
            'email': self.canal_email,
            'push': self.canal_push,
        }
        return canal_map.get(canal, False)


class DispositivoMovil(models.Model):
    """Dispositivos moviles registrados para notificaciones push."""

    PLATAFORMA_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web (PWA)'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dispositivos_moviles',
        verbose_name='Usuario',
    )

    token_fcm = models.CharField(max_length=255, unique=True, verbose_name='Token FCM')
    plataforma = models.CharField(max_length=10, choices=PLATAFORMA_CHOICES, verbose_name='Plataforma')
    nombre_dispositivo = models.CharField(max_length=100, blank=True, verbose_name='Nombre del Dispositivo')
    modelo = models.CharField(max_length=100, blank=True, verbose_name='Modelo')
    version_app = models.CharField(max_length=20, blank=True, verbose_name='Version de la App')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')
    ultima_actividad = models.DateTimeField(auto_now=True, verbose_name='Ultima Actividad')

    total_notificaciones_enviadas = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Total Notificaciones Enviadas',
    )

    total_notificaciones_fallidas = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Total Notificaciones Fallidas',
    )
    objects = TenantManager(school_field='usuario__rbd_colegio')

    class Meta:
        db_table = 'dispositivo_movil'
        verbose_name = 'Dispositivo Movil'
        verbose_name_plural = 'Dispositivos Moviles'
        ordering = ['-ultima_actividad']

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_plataforma_display()} ({self.nombre_dispositivo or 'Sin nombre'})"

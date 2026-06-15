"""
Modelos del módulo Mensajería
Migrados desde sistema_antiguo/mensajeria/models.py
Compatible con autopoblar.py sin modificaciones
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from backend.apps.accounts.models import User
from backend.apps.cursos.models import Clase
from backend.common.tenancy import TenantManager


def validate_file_size(file):
    """Valida el tamaño máximo del archivo (10 MB)"""
    max_size_mb = 10
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'El archivo no puede superar {max_size_mb} MB')


class Anuncio(models.Model):
    """Anuncios del profesor para toda la clase"""
    id_anuncio = models.AutoField(primary_key=True)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='anuncios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anuncios_creados')
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    archivo_adjunto = models.FileField(upload_to='anuncios/', null=True, blank=True)
    anclado = models.BooleanField(default=False)
    enviar_email = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    leido_por = models.ManyToManyField(User, related_name='anuncios_leidos', blank=True)
    objects = TenantManager(school_field='clase__colegio__rbd')

    class Meta:
        db_table = 'anuncio'
        ordering = ['-anclado', '-fecha_creacion']
        verbose_name = 'Anuncio'
        verbose_name_plural = 'Anuncios'

    def __str__(self):
        return f"{self.titulo} - {self.clase}"
    
    def esta_leido_por(self, usuario):
        """Verifica si el anuncio ha sido leído por el usuario"""
        return self.leido_por.filter(id=usuario.id).exists()
    
    def marcar_como_leido(self, usuario):
        """Marca el anuncio como leído por el usuario"""
        if not self.esta_leido_por(usuario):
            self.leido_por.add(usuario)


class Conversacion(models.Model):
    """Conversación entre dos usuarios en el contexto de una clase"""
    id_conversacion = models.AutoField(primary_key=True)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='conversaciones')
    participante1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones_como_p1')
    participante2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones_como_p2')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    ultima_actividad = models.DateTimeField(default=timezone.now)
    objects = TenantManager(school_field='clase__colegio__rbd')

    class Meta:
        db_table = 'conversacion'
        unique_together = ('clase', 'participante1', 'participante2')
        ordering = ['-ultima_actividad']
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'

    def __str__(self):
        return f"Conversación: {self.participante1.get_full_name()} ↔ {self.participante2.get_full_name()}"

    def get_otro_participante(self, usuario):
        """Retorna el otro participante de la conversación"""
        if self.participante1 == usuario:
            return self.participante2
        return self.participante1

    def marcar_leidos(self, usuario):
        """Marca todos los mensajes como leídos para un usuario"""
        self.mensajes.filter(receptor=usuario, leido=False).update(leido=True)


class Mensaje(models.Model):
    """Mensaje individual dentro de una conversación"""
    id_mensaje = models.AutoField(primary_key=True)
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    emisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados')
    receptor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_recibidos')
    contenido = models.TextField()
    archivo_adjunto = models.FileField(upload_to='mensajes/', null=True, blank=True)
    leido = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(default=timezone.now)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    objects = TenantManager(school_field='conversacion__clase__colegio_id')

    class Meta:
        db_table = 'mensaje'
        ordering = ['fecha_envio']
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
        indexes = [
            models.Index(fields=['conversacion', 'fecha_envio']),
            models.Index(fields=['receptor', 'leido']),
        ]

    def __str__(self):
        return f"Mensaje de {self.emisor.get_full_name()} a {self.receptor.get_full_name()}"

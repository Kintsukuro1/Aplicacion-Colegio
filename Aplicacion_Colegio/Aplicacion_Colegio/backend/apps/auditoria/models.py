"""
Modelos del módulo Auditoría
Migrados desde sistema_antiguo/auditoria/models.py
Compatible con autopoblar.py sin modificaciones
Sistema de trazabilidad para Ley 20.370 (Chile)
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from backend.common.tenancy import TenantManager


class AuditoriaEvento(models.Model):
    """Registro de auditoría para trazabilidad completa del sistema"""
    
    # Tipos de acción
    CREAR = 'CREATE'
    MODIFICAR = 'UPDATE'
    ELIMINAR = 'DELETE'
    VISUALIZAR = 'VIEW'
    EXPORTAR = 'EXPORT'
    RESTAURAR = 'RESTORE'
    
    TIPOS_ACCION = [
        (CREAR, 'Crear'),
        (MODIFICAR, 'Modificar'),
        (ELIMINAR, 'Eliminar'),
        (VISUALIZAR, 'Visualizar'),
        (EXPORTAR, 'Exportar'),
        (RESTAURAR, 'Restaurar'),
    ]
    
    # Categorías de eventos
    CATEGORIA_ACADEMICO = 'academico'
    CATEGORIA_ASISTENCIA = 'asistencia'
    CATEGORIA_COMUNICACION = 'comunicacion'
    CATEGORIA_ESTUDIANTES = 'estudiantes'
    CATEGORIA_USUARIOS = 'usuarios'
    CATEGORIA_SEGURIDAD = 'seguridad'
    CATEGORIA_SISTEMA = 'sistema'
    
    CATEGORIAS = [
        (CATEGORIA_ACADEMICO, 'Académico'),
        (CATEGORIA_ASISTENCIA, 'Asistencia'),
        (CATEGORIA_COMUNICACION, 'Comunicación'),
        (CATEGORIA_ESTUDIANTES, 'Estudiantes'),
        (CATEGORIA_USUARIOS, 'Usuarios'),
        (CATEGORIA_SEGURIDAD, 'Seguridad'),
        (CATEGORIA_SISTEMA, 'Sistema'),
    ]
    
    # Usuario que realizó la acción
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eventos_auditoria'
    )
    
    # Información del usuario (almacenada por si el usuario se elimina)
    usuario_rut = models.CharField(max_length=12, null=True, blank=True)
    usuario_nombre = models.CharField(max_length=255, null=True, blank=True)
    usuario_email = models.EmailField(null=True, blank=True)
    usuario_rol = models.CharField(max_length=50, null=True, blank=True)
    
    # Colegio (para multi-tenancy)
    colegio_rbd = models.CharField(max_length=10, db_index=True)
    
    # Tipo de acción realizada
    accion = models.CharField(max_length=10, choices=TIPOS_ACCION, db_index=True)
    
    # Categoría del evento
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default=CATEGORIA_SISTEMA, db_index=True)
    
    # Tabla/Modelo afectado (usando ContentType)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Información adicional del modelo
    tabla_afectada = models.CharField(max_length=100, db_index=True)
    
    # Descripción de la acción
    descripcion = models.TextField()
    
    # Valores antes y después del cambio (JSON)
    valor_previo = models.JSONField(null=True, blank=True)
    valor_nuevo = models.JSONField(null=True, blank=True)
    
    # Campos modificados
    campos_modificados = models.JSONField(null=True, blank=True)
    
    # Fecha y hora del evento
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Información técnica adicional
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # Metadatos adicionales
    metadata = models.JSONField(null=True, blank=True)
    objects = TenantManager(school_field='colegio_rbd', coerce_school_id_to_str=True)
    
    # Nivel de importancia
    NIVEL_INFO = 'info'
    NIVEL_WARNING = 'warning'
    NIVEL_CRITICAL = 'critical'
    
    NIVELES = [
        (NIVEL_INFO, 'Información'),
        (NIVEL_WARNING, 'Advertencia'),
        (NIVEL_CRITICAL, 'Crítico'),
    ]
    
    nivel = models.CharField(max_length=10, choices=NIVELES, default=NIVEL_INFO, db_index=True)
    
    class Meta:
        db_table = 'auditoria_evento'
        verbose_name = 'Evento de Auditoría'
        verbose_name_plural = 'Eventos de Auditoría'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['colegio_rbd', '-fecha_hora']),
            models.Index(fields=['usuario', '-fecha_hora']),
            models.Index(fields=['tabla_afectada', '-fecha_hora']),
            models.Index(fields=['accion', 'categoria', '-fecha_hora']),
            models.Index(fields=['nivel', '-fecha_hora']),
        ]
    
    def __str__(self):
        return f"{self.fecha_hora.strftime('%Y-%m-%d %H:%M:%S')} - {self.usuario_nombre or 'Sistema'} - {self.get_accion_display()} en {self.tabla_afectada}"
    
    def save(self, *args, **kwargs):
        """Al guardar, extraer información del usuario automáticamente"""
        if self.usuario and not self.usuario_nombre:
            self.usuario_rut = self.usuario.rut
            self.usuario_nombre = f"{self.usuario.nombre} {self.usuario.apellido_paterno}"
            self.usuario_email = self.usuario.email
            self.usuario_rol = self.usuario.role.nombre if self.usuario.role else 'Sin rol'
            
            if not self.colegio_rbd:
                self.colegio_rbd = self.usuario.rbd_colegio if self.usuario.rbd_colegio else '__global__'
        
        if not self.colegio_rbd:
            self.colegio_rbd = '__system__'
        
        super().save(*args, **kwargs)
    
    @classmethod
    def registrar_evento(cls, usuario, accion, tabla_afectada, descripcion, 
                        valor_previo=None, valor_nuevo=None, categoria='sistema',
                        content_object=None, campos_modificados=None, nivel='info',
                        ip_address=None, user_agent=None, metadata=None):
        """Método helper para registrar eventos de auditoría fácilmente"""
        evento = cls(
            usuario=usuario,
            accion=accion,
            tabla_afectada=tabla_afectada,
            descripcion=descripcion,
            valor_previo=valor_previo,
            valor_nuevo=valor_nuevo,
            categoria=categoria,
            campos_modificados=campos_modificados,
            nivel=nivel,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
        
        if content_object:
            evento.content_object = content_object
        
        evento.save()
        return evento
    
    def get_cambios_legibles(self):
        """Retorna los cambios en formato legible"""
        if not self.campos_modificados or not self.valor_previo or not self.valor_nuevo:
            return []
        
        cambios = []
        for campo in self.campos_modificados:
            cambios.append({
                'campo': campo,
                'anterior': self.valor_previo.get(campo, 'N/A'),
                'nuevo': self.valor_nuevo.get(campo, 'N/A')
            })
        
        return cambios


class ConfiguracionAuditoria(models.Model):
    """Configuración de auditoría por colegio"""
    colegio_rbd = models.CharField(max_length=10, unique=True, db_index=True)
    
    # Activación por categoría
    auditar_academico = models.BooleanField(default=True, help_text='Auditar notas, evaluaciones')
    auditar_asistencia = models.BooleanField(default=True, help_text='Auditar asistencia')
    auditar_comunicacion = models.BooleanField(default=True, help_text='Auditar comunicados, mensajes')
    auditar_estudiantes = models.BooleanField(default=True, help_text='Auditar cambios en estudiantes')
    auditar_usuarios = models.BooleanField(default=True, help_text='Auditar usuarios y roles')
    auditar_seguridad = models.BooleanField(default=True, help_text='Auditar login, permisos')
    
    # Configuración de retención
    dias_retencion = models.IntegerField(default=1825, help_text='Días de retención (5 años por defecto)')
    
    # Activar auditoría de vistas
    auditar_visualizaciones = models.BooleanField(default=False, help_text='Auditar visualizaciones')
    
    # Captura de datos técnicos
    capturar_ip = models.BooleanField(default=True)
    capturar_user_agent = models.BooleanField(default=False)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_rbd', coerce_school_id_to_str=True)
    
    class Meta:
        db_table = 'auditoria_configuracion'
        verbose_name = 'Configuración de Auditoría'
        verbose_name_plural = 'Configuraciones de Auditoría'
    
    def __str__(self):
        return f"Configuración Auditoría - RBD {self.colegio_rbd}"
    
    @classmethod
    def get_config(cls, colegio_rbd):
        """Obtiene o crea la configuración de auditoría para un colegio"""
        if colegio_rbd is None:
            return cls(
                colegio_rbd='__global__',
                auditar_academico=True,
                auditar_asistencia=True,
                auditar_comunicacion=True,
                auditar_estudiantes=True,
                auditar_usuarios=True,
                auditar_seguridad=True,
                capturar_ip=True
            )
        
        config, created = cls.objects.get_or_create(colegio_rbd=str(colegio_rbd))
        return config


class SensitiveActionRequest(models.Model):
    """Solicitud para acciones sensibles con doble control obligatorio."""

    ACTION_ROLE_CHANGE = 'ROLE_CHANGE'
    ACTION_PASSWORD_RESET = 'PASSWORD_RESET'
    ACTION_SENSITIVE_EXPORT = 'SENSITIVE_EXPORT'

    ACTION_TYPES = [
        (ACTION_ROLE_CHANGE, 'Cambio de rol'),
        (ACTION_PASSWORD_RESET, 'Reset de contraseña'),
        (ACTION_SENSITIVE_EXPORT, 'Exportación de datos sensibles'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_EXECUTED = 'EXECUTED'
    STATUS_FAILED = 'FAILED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_APPROVED, 'Aprobada'),
        (STATUS_EXECUTED, 'Ejecutada'),
        (STATUS_FAILED, 'Fallida'),
        (STATUS_REJECTED, 'Rechazada'),
    ]

    action_type = models.CharField(max_length=32, choices=ACTION_TYPES, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    school_rbd = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sensitive_requests_created',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sensitive_requests_approved',
    )
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sensitive_requests_executed',
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sensitive_requests_targeted',
    )

    justification = models.TextField(blank=True, default='')
    approval_comment = models.TextField(blank=True, default='')
    payload = models.JSONField(default=dict, blank=True)
    execution_result = models.JSONField(null=True, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    objects = TenantManager(school_field='school_rbd', coerce_school_id_to_str=True)

    class Meta:
        db_table = 'auditoria_sensitive_action_request'
        verbose_name = 'Solicitud de Acción Sensible'
        verbose_name_plural = 'Solicitudes de Acciones Sensibles'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['school_rbd', 'status', '-requested_at'], name='aud_sar_school_status_idx'),
            models.Index(fields=['action_type', 'status', '-requested_at'], name='aud_sar_action_status_idx'),
            models.Index(fields=['requested_by', '-requested_at'], name='aud_sar_requested_at_idx'),
        ]

    def __str__(self):
        return f'{self.action_type} [{self.status}] #{self.id}'

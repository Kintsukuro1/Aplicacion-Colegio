"""
Modelos del módulo Suscripciones
Migrados desde sistema_antiguo/subscriptions/models.py
Compatible con autopoblar.py sin modificaciones
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from backend.common.tenancy import TenantManager


class Plan(models.Model):
    """Plan de suscripción con características y límites"""
    
    # Tipos de plan
    PLAN_TESTER = 'tester'
    PLAN_TRIAL = 'trial'
    PLAN_BASIC = 'basic'
    PLAN_STANDARD = 'standard'
    PLAN_PREMIUM = 'premium'
    PLAN_ENTERPRISE = 'enterprise'
    
    PLAN_CHOICES = [
        (PLAN_TESTER, 'Tester (Ilimitado)'),
        (PLAN_TRIAL, 'Prueba (30 días)'),
        (PLAN_BASIC, 'Básico'),
        (PLAN_STANDARD, 'Estándar'),
        (PLAN_PREMIUM, 'Premium'),
        (PLAN_ENTERPRISE, 'Enterprise'),
    ]
    
    # Información básica
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=50, unique=True, choices=PLAN_CHOICES)
    descripcion = models.TextField(blank=True)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Flags especiales
    is_unlimited = models.BooleanField(
        default=False,
        help_text="Plan TESTER: sin límites, para demos y desarrollo"
    )
    is_trial = models.BooleanField(
        default=False,
        help_text="Plan TRIAL: 30 días de prueba con límites"
    )
    duracion_dias = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duración del plan en días (solo para TRIAL)"
    )
    
    # Límites de uso (999999 = ilimitado)
    max_estudiantes = models.IntegerField(default=999999, help_text="Número máximo de estudiantes activos")
    max_profesores = models.IntegerField(default=999999, help_text="Número máximo de profesores activos")
    max_cursos = models.IntegerField(default=999999, help_text="Número máximo de cursos activos")
    max_mensajes_mes = models.IntegerField(default=999999, help_text="Mensajes por mes")
    max_evaluaciones_mes = models.IntegerField(default=999999, help_text="Evaluaciones por mes")
    max_almacenamiento_mb = models.IntegerField(default=999999, help_text="Almacenamiento en MB")
    max_comunicados_mes = models.IntegerField(default=999999, help_text="Comunicados por mes")
    
    # Features/Características
    has_attendance = models.BooleanField(default=True, help_text="Módulo de asistencia")
    has_grades = models.BooleanField(default=True, help_text="Módulo de calificaciones")
    has_messaging = models.BooleanField(default=True, help_text="Mensajería interna")
    has_reports = models.BooleanField(default=False, help_text="Reportes básicos")
    has_advanced_reports = models.BooleanField(default=False, help_text="Reportes avanzados y analytics")
    has_file_attachments = models.BooleanField(default=True, help_text="Adjuntar archivos")
    has_webpay_integration = models.BooleanField(default=False, help_text="Integración Webpay")
    has_api_access = models.BooleanField(default=False, help_text="Acceso a API REST")
    has_priority_support = models.BooleanField(default=False, help_text="Soporte prioritario")
    has_custom_branding = models.BooleanField(default=False, help_text="Personalización de marca")
    
    # Metadata
    activo = models.BooleanField(default=True)
    orden_visualizacion = models.IntegerField(default=0, help_text="Orden para mostrar")
    destacado = models.BooleanField(default=False, help_text="Marcar como plan destacado")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'plan'
        ordering = ['orden_visualizacion', 'precio_mensual']
        verbose_name = 'Plan de Suscripción'
        verbose_name_plural = 'Planes de Suscripción'
    
    def __str__(self):
        if self.is_unlimited:
            return f"{self.nombre} (ILIMITADO)"
        elif self.is_trial:
            return f"{self.nombre} (PRUEBA {self.duracion_dias} días)"
        return f"{self.nombre} - ${self.precio_mensual}/mes"
    
    def get_limite_display(self, campo):
        """Retorna 'Ilimitado' si el valor es 999999"""
        valor = getattr(self, campo, 0)
        if valor >= 999999 or self.is_unlimited:
            return 'Ilimitado'
        return str(valor)


class Subscription(models.Model):
    """Suscripción de un colegio a un plan"""
    
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_SUSPENDED = 'suspended'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Activa'),
        (STATUS_EXPIRED, 'Expirada'),
        (STATUS_CANCELLED, 'Cancelada'),
        (STATUS_SUSPENDED, 'Suspendida'),
    ]
    
    # Relaciones
    colegio = models.OneToOneField(
        'institucion.Colegio',
        on_delete=models.CASCADE,
        related_name='subscription',
        to_field='rbd'
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    
    # Fechas
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField(null=True, blank=True)
    fecha_ultimo_pago = models.DateField(null=True, blank=True)
    proximo_pago = models.DateField(null=True, blank=True)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    auto_renovar = models.BooleanField(default=True, help_text="Renovar automáticamente al vencer")
    
    # Metadata
    notas = models.TextField(blank=True, help_text="Notas internas sobre la suscripción")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'subscription'
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'
        indexes = [
            models.Index(fields=['status', 'fecha_fin']),
            models.Index(fields=['plan', 'status']),
        ]
    
    def __str__(self):
        return f"{self.colegio.nombre} - {self.plan.nombre} ({self.get_status_display()})"
    
    def is_active(self):
        """Verifica si la suscripción está activa"""
        if self.plan.is_unlimited:
            return True
        
        if self.status != self.STATUS_ACTIVE:
            return False
        
        if self.fecha_fin and timezone.now().date() > self.fecha_fin:
            return False
        
        return True
    
    def dias_restantes(self):
        """Retorna días restantes (None si ilimitado)"""
        if self.plan.is_unlimited:
            return None
        
        if not self.fecha_fin:
            return None
        
        delta = self.fecha_fin - timezone.now().date()
        return max(0, delta.days)
    
    def porcentaje_tiempo_usado(self):
        """Retorna porcentaje del período usado (0-100)"""
        if self.plan.is_unlimited or not self.fecha_inicio or not self.fecha_fin:
            return 0
        
        total_dias = (self.fecha_fin - self.fecha_inicio).days
        dias_transcurridos = (timezone.now().date() - self.fecha_inicio).days
        
        if total_dias <= 0:
            return 100
        
        return min(100, int((dias_transcurridos / total_dias) * 100))
    
    def renovar(self, dias=30):
        """Renovar la suscripción por X días más"""
        if self.plan.is_unlimited:
            return
        
        if not self.fecha_fin:
            self.fecha_fin = timezone.now().date() + timedelta(days=dias)
        else:
            self.fecha_fin += timedelta(days=dias)
        
        self.fecha_ultimo_pago = timezone.now().date()
        self.proximo_pago = self.fecha_fin
        self.status = self.STATUS_ACTIVE
        self.save()
    
    def upgrade_to(self, nuevo_plan):
        """Actualizar a un nuevo plan"""
        self.plan = nuevo_plan
        
        if nuevo_plan.is_unlimited:
            self.fecha_fin = None
            self.proximo_pago = None
        
        if self.plan.is_trial and not nuevo_plan.is_trial:
            self.fecha_fin = timezone.now().date() + timedelta(days=30)
            self.proximo_pago = self.fecha_fin
        
        self.status = self.STATUS_ACTIVE
        self.save()
    
    def cancelar(self):
        """Cancelar la suscripción"""
        if self.plan.is_unlimited:
            return False
        
        self.status = self.STATUS_CANCELLED
        self.auto_renovar = False
        self.save()
        return True
    
    def suspender(self, razon=''):
        """Suspender temporalmente la suscripción"""
        self.status = self.STATUS_SUSPENDED
        if razon:
            self.notas = f"{self.notas}\n[{timezone.now()}] Suspendida: {razon}"
        self.save()
    
    def reactivar(self):
        """Reactivar una suscripción suspendida"""
        if self.status == self.STATUS_SUSPENDED:
            self.status = self.STATUS_ACTIVE
            self.save()
            return True
        return False


class Payment(models.Model):
    """Registro de pagos procesados por suscripción."""

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_APPROVED, 'Aprobado'),
        (STATUS_REJECTED, 'Rechazado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    external_id = models.CharField(max_length=100, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, default='CLP')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    gateway = models.CharField(max_length=40, default='mercadopago')
    metadata_json = models.JSONField(default=dict, blank=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['subscription', 'status']),
            models.Index(fields=['gateway', 'external_id']),
        ]

    def __str__(self):
        return f"{self.subscription.colegio.nombre} - {self.external_id} ({self.get_status_display()})"

    def mark_approved(self, *, paid_at=None):
        self.status = self.STATUS_APPROVED
        self.fecha_pago = paid_at or timezone.now()
        self.save()

    def mark_rejected(self):
        self.status = self.STATUS_REJECTED
        self.save()


class UsageLog(models.Model):
    """
    Modelo de Seguimiento de Uso
    
    Rastrea el uso mensual de recursos por colegio.
    Se resetea automáticamente cada mes.
    Anteriormente llamado UsageTracking en sistema_antiguo
    """
    
    # Relaciones
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    
    # Período de seguimiento
    periodo_anio = models.IntegerField()
    periodo_mes = models.IntegerField()  # 1-12
    
    # Contadores de uso (se resetean cada mes)
    student_count = models.IntegerField(
        default=0,
        help_text="Estudiantes activos actuales"
    )
    teacher_count = models.IntegerField(
        default=0,
        help_text="Profesores activos actuales"
    )
    course_count = models.IntegerField(
        default=0,
        help_text="Cursos activos actuales"
    )
    messages_sent = models.IntegerField(
        default=0,
        help_text="Mensajes enviados este mes"
    )
    evaluations_created = models.IntegerField(
        default=0,
        help_text="Evaluaciones creadas este mes"
    )
    storage_used_mb = models.IntegerField(
        default=0,
        help_text="Almacenamiento usado en MB"
    )
    comunicados_sent = models.IntegerField(
        default=0,
        help_text="Comunicados enviados este mes"
    )
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='subscription__colegio_id')
    
    class Meta:
        db_table = 'usage_log'
        unique_together = [['subscription', 'periodo_anio', 'periodo_mes']]
        ordering = ['-periodo_anio', '-periodo_mes']
        verbose_name = 'Registro de Uso'
        verbose_name_plural = 'Registros de Uso'
        indexes = [
            models.Index(fields=['subscription', 'periodo_anio', 'periodo_mes']),
        ]
    
    def __str__(self):
        return f"{self.subscription.colegio.nombre} - {self.periodo_mes}/{self.periodo_anio}"
    
    @classmethod
    def get_current_period(cls, subscription):
        """Obtiene o crea el registro de uso para el período actual"""
        now = timezone.now()
        periodo_anio = now.year
        periodo_mes = now.month
        
        usage, created = cls.objects.get_or_create(
            subscription=subscription,
            periodo_anio=periodo_anio,
            periodo_mes=periodo_mes
        )
        
        return usage
    
    def update_student_count(self, count):
        """Actualiza el conteo de estudiantes activos"""
        self.student_count = count
        self.save(update_fields=['student_count', 'fecha_actualizacion'])
    
    def increment_messages(self, count=1):
        """Incrementa el contador de mensajes"""
        self.messages_sent += count
        self.save(update_fields=['messages_sent', 'fecha_actualizacion'])
    
    def increment_evaluations(self, count=1):
        """Incrementa el contador de evaluaciones"""
        self.evaluations_created += count
        self.save(update_fields=['evaluations_created', 'fecha_actualizacion'])
    
    def increment_comunicados(self, count=1):
        """Incrementa el contador de comunicados"""
        self.comunicados_sent += count
        self.save(update_fields=['comunicados_sent', 'fecha_actualizacion'])
    
    def check_limit(self, field_name):
        """
        Verifica si se ha alcanzado el límite para un campo específico
        
        Returns:
            tuple: (has_limit_reached, current_value, limit_value)
        """
        # Si el plan es ilimitado (TESTER), nunca hay límite
        if self.subscription.plan.is_unlimited:
            return (False, getattr(self, field_name, 0), None)
        
        current_value = getattr(self, field_name, 0)
        
        # Mapear campos de uso a campos de límite en el plan
        limit_mapping = {
            'student_count': 'max_estudiantes',
            'teacher_count': 'max_profesores',
            'course_count': 'max_cursos',
            'messages_sent': 'max_mensajes_mes',
            'evaluations_created': 'max_evaluaciones_mes',
            'storage_used_mb': 'max_almacenamiento_mb',
            'comunicados_sent': 'max_comunicados_mes',
        }
        
        limit_field = limit_mapping.get(field_name)
        if not limit_field:
            return (False, current_value, None)
        
        limit_value = getattr(self.subscription.plan, limit_field, 999999)
        
        # 999999 se considera ilimitado
        if limit_value >= 999999:
            return (False, current_value, None)
        
        has_reached = current_value >= limit_value
        return (has_reached, current_value, limit_value)
    
    def get_usage_percentage(self, field_name):
        """Retorna el porcentaje de uso de un límite (0-100)"""
        has_reached, current, limit = self.check_limit(field_name)
        
        if limit is None or limit >= 999999:
            return 0
        
        if limit == 0:
            return 100
        
        return min(100, int((current / limit) * 100))

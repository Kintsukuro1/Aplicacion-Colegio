"""
Modelos del módulo de Matrículas y Finanzas
Migrados desde sistema_antiguo/matriculas/models.py
Compatible con autopoblar.py sin modificaciones
NOTA: Versión simplificada con los modelos que usa autopoblar.py
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from backend.apps.institucion.models import Colegio, CicloAcademico
from backend.apps.accounts.models import User
from backend.common.tenancy import TenantManager
from backend.common.exceptions import PrerequisiteException


class Matricula(models.Model):
    """Matrícula de un estudiante en un curso"""
    ESTADO_CHOICES = [
        ('ACTIVA', 'Activa'),
        ('SUSPENDIDA', 'Suspendida'),
        ('RETIRADA', 'Retirada'),
        ('FINALIZADA', 'Finalizada'),
    ]
    
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matriculas')
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='matriculas')
    curso = models.ForeignKey(
        'cursos.Curso',
        on_delete=models.PROTECT,
        related_name='matriculas',
        null=True,
        blank=True
    )
    
    # Valores base
    valor_matricula = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    valor_mensual = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Estado y fechas
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVA')
    ciclo_academico = models.ForeignKey(
        CicloAcademico,
        on_delete=models.PROTECT,
        related_name='matriculas',
        null=True,
        blank=True
    )
    fecha_matricula = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_termino = models.DateField(null=True, blank=True)
    
    # Metadata
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'matricula'
        verbose_name = 'Matrícula'
        verbose_name_plural = 'Matrículas'
        ordering = ['-ciclo_academico__fecha_inicio', '-fecha_matricula']
        indexes = [
            models.Index(fields=['estudiante', 'ciclo_academico']),
            models.Index(fields=['estado', 'ciclo_academico']),
            models.Index(fields=['colegio', 'estado']),
        ]
    
    def __str__(self):
        curso_str = f" - {self.curso.nombre}" if self.curso else ""
        ciclo_nombre = self.ciclo_academico.nombre if self.ciclo_academico else "Sin ciclo"
        return f"{self.estudiante.get_full_name()}{curso_str} ({ciclo_nombre})"

    @property
    def anio_escolar(self):
        if self.ciclo_academico and self.ciclo_academico.fecha_inicio:
            return self.ciclo_academico.fecha_inicio.year
        return None

    def clean(self):
        # Reglas defensivas de dominio para matrículas activas.
        if self.estado != 'ACTIVA':
            return

        if not self.ciclo_academico:
            raise PrerequisiteException(
                error_type='MISSING_CICLO_ACTIVO',
                context={
                    'colegio_rbd': self.colegio_id,
                    'message': 'No se puede crear matrícula activa sin ciclo académico.',
                }
            )

        if (
            self.estudiante_id
            and self.estudiante.rbd_colegio is not None
            and int(self.estudiante.rbd_colegio) != int(self.colegio_id)
        ):
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Matricula',
                    'related_entity': 'Estudiante',
                    'estudiante_id': self.estudiante_id,
                    'estudiante_colegio_rbd': self.estudiante.rbd_colegio,
                    'matricula_colegio_rbd': self.colegio_id,
                    'message': 'El estudiante no pertenece al colegio de la matricula.',
                }
            )

        if self.curso_id and self.curso.colegio_id != self.colegio_id:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Matricula',
                    'related_entity': 'Curso',
                    'curso_id': self.curso_id,
                    'curso_colegio_rbd': self.curso.colegio_id,
                    'matricula_colegio_rbd': self.colegio_id,
                    'message': 'El curso no pertenece al colegio de la matricula.',
                }
            )

        if self.ciclo_academico_id and self.ciclo_academico.colegio_id != self.colegio_id:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                context={
                    'entity': 'Matricula',
                    'related_entity': 'CicloAcademico',
                    'ciclo_academico_id': self.ciclo_academico_id,
                    'ciclo_colegio_rbd': self.ciclo_academico.colegio_id,
                    'matricula_colegio_rbd': self.colegio_id,
                    'message': 'El ciclo academico no pertenece al colegio de la matricula.',
                }
            )

        if self.curso and not self.curso.activo:
            raise PrerequisiteException(
                error_type='INVALID_CURSO_STATE',
                context={
                    'curso_id': self.curso_id,
                    'colegio_rbd': self.colegio_id,
                    'message': 'No se puede crear matrícula activa en curso inactivo.',
                }
            )

        duplicada = Matricula.objects.filter(
            estudiante_id=self.estudiante_id,
            ciclo_academico_id=self.ciclo_academico_id,
            estado='ACTIVA',
        )
        if self.pk:
            duplicada = duplicada.exclude(pk=self.pk)
        if duplicada.exists():
            raise PrerequisiteException(
                error_type='DUPLICATE_ACTIVE_MATRICULA',
                context={
                    'estudiante_id': self.estudiante_id,
                    'ciclo_academico_id': self.ciclo_academico_id,
                    'message': 'El estudiante ya tiene matrícula activa en este ciclo.',
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Cuota(models.Model):
    """Cuotas mensuales de pago"""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADA', 'Pagada'),
        ('PAGADA_PARCIAL', 'Pagada Parcialmente'),
        ('VENCIDA', 'Vencida'),
        ('CONDONADA', 'Condonada'),
    ]
    
    MES_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'),
        (4, 'Abril'), (5, 'Mayo'), (6, 'Junio'),
        (7, 'Julio'), (8, 'Agosto'), (9, 'Septiembre'),
        (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
    ]
    
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name='cuotas')
    
    # Detalles de la cuota
    numero_cuota = models.IntegerField(default=1)
    mes = models.IntegerField(choices=MES_CHOICES)
    anio = models.IntegerField(default=2025)
    
    # Montos
    monto_original = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    monto_descuento = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    monto_final = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Fechas
    fecha_vencimiento = models.DateField()
    fecha_pago_completo = models.DateTimeField(null=True, blank=True)
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    
    # Metadata
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='matricula__colegio_id')
    
    class Meta:
        db_table = 'cuota'
        verbose_name = 'Cuota'
        verbose_name_plural = 'Cuotas'
        ordering = ['anio', 'mes', 'numero_cuota']
        indexes = [
            models.Index(fields=['matricula', 'estado']),
            models.Index(fields=['estado', 'fecha_vencimiento']),
            models.Index(fields=['anio', 'mes']),
        ]
    
    def __str__(self):
        mes_nombre = dict(self.MES_CHOICES).get(self.mes, self.mes)
        return f"{self.matricula.estudiante.get_full_name()} - {mes_nombre} {self.anio}"
    
    def saldo_pendiente(self):
        """Calcula el saldo pendiente de pago"""
        return self.monto_final - self.monto_pagado


class Pago(models.Model):
    """Registro de pagos realizados"""
    METODO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('WEBPAY', 'Webpay (Tarjeta)'),
        ('CHEQUE', 'Cheque'),
        ('MERCADO_PAGO', 'Mercado Pago'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('ANULADO', 'Anulado'),
    ]
    
    cuota = models.ForeignKey(Cuota, on_delete=models.CASCADE, related_name='pagos')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pagos')
    
    # Detalles del pago
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('1'))]
    )
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES)
    
    # Referencia del pago
    numero_comprobante = models.CharField(max_length=100, blank=True, null=True)
    numero_transaccion = models.CharField(max_length=100, blank=True, null=True)
    
    # Archivo del comprobante
    comprobante = models.FileField(
        upload_to='comprobantes/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    fecha_pago = models.DateTimeField(default=timezone.now)
    
    # Registro de quién procesó el pago
    procesado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos_procesados'
    )
    fecha_procesamiento = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='cuota__matricula__colegio_id')
    
    class Meta:
        db_table = 'pago'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']
        indexes = [
            models.Index(fields=['cuota', 'estado']),
            models.Index(fields=['estudiante', '-fecha_pago']),
            models.Index(fields=['estado', 'fecha_pago']),
        ]
    
    def __str__(self):
        return f"Pago ${self.monto} - {self.estudiante.get_full_name()} - {self.fecha_pago.strftime('%d/%m/%Y')}"


class EstadoCuenta(models.Model):
    """Estado de cuenta mensual del estudiante"""
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='estados_cuenta')
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='estados_cuenta')
    
    # Periodo
    mes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    anio = models.IntegerField(default=2025)
    
    # Resumen financiero
    total_deuda = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0
    )
    total_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0
    )
    saldo_pendiente = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=[
            ('GENERADO', 'Generado'),
            ('ENVIADO', 'Enviado'),
            ('PAGADO', 'Pagado'),
        ],
        default='GENERADO'
    )
    
    # Archivo PDF generado
    archivo_pdf = models.FileField(
        upload_to='estados_cuenta/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Fechas
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    observaciones = models.TextField(blank=True, null=True)
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'estado_cuenta'
        verbose_name = 'Estado de Cuenta'
        verbose_name_plural = 'Estados de Cuenta'
        ordering = ['-anio', '-mes']
        unique_together = ['estudiante', 'mes', 'anio']
        indexes = [
            models.Index(fields=['estudiante', 'anio', 'mes']),
            models.Index(fields=['colegio', 'estado']),
        ]
    
    def __str__(self):
        return f"Estado Cuenta {self.estudiante.get_full_name()} - {self.mes}/{self.anio}"


class Beca(models.Model):
    """Becas y descuentos aplicados a estudiantes"""
    TIPO_CHOICES = [
        ('SOCIOECONOMICA', 'Socioeconómica'),
        ('RENDIMIENTO', 'Rendimiento Académico'),
        ('DEPORTIVA', 'Deportiva'),
        ('ARTISTICA', 'Artística'),
        ('HERMANOS', 'Descuento por Hermanos'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('SOLICITADA', 'Solicitada'),
        ('EN_REVISION', 'En Revisión'),
        ('APROBADA', 'Aprobada'),
        ('VIGENTE', 'Vigente'),
        ('RECHAZADA', 'Rechazada'),
        ('VENCIDA', 'Vencida'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='becas')
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name='becas')
    
    # Tipo y porcentaje
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    porcentaje_descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # Aplicabilidad
    aplica_matricula = models.BooleanField(default=True)
    aplica_mensualidad = models.BooleanField(default=True)
    aplica_otros_aranceles = models.BooleanField(default=False)
    
    # Detalles
    motivo = models.TextField()
    descripcion = models.TextField(blank=True, null=True)
    
    # Aplicabilidad
    aplica_matricula = models.BooleanField(default=True)
    aplica_mensualidad = models.BooleanField(default=True)
    aplica_otros_aranceles = models.BooleanField(default=False)
    
    # Vigencia
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='SOLICITADA')
    
    # Aprobación
    aprobada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='becas_aprobadas'
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True, null=True)
    
    # Metadata
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objects = TenantManager(school_field='matricula__colegio_id')
    
    class Meta:
        db_table = 'beca'
        verbose_name = 'Beca'
        verbose_name_plural = 'Becas'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estudiante', 'estado']),
            models.Index(fields=['estado', 'fecha_inicio', 'fecha_fin']),
        ]
    
    def __str__(self):
        return f"Beca {self.get_tipo_display()} {self.porcentaje_descuento}% - {self.estudiante.get_full_name()}"


class Boleta(models.Model):
    """Boletas o facturas emitidas"""
    ESTADO_CHOICES = [
        ('EMITIDA', 'Emitida'),
        ('ANULADA', 'Anulada'),
    ]
    
    pago = models.ForeignKey(Pago, on_delete=models.CASCADE, related_name='boletas')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='boletas')
    
    # Número de boleta
    numero_boleta = models.CharField(max_length=50, unique=True)
    
    # Detalles
    monto_total = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    detalle = models.TextField()
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='EMITIDA')
    
    # Archivo PDF
    archivo_pdf = models.FileField(
        upload_to='boletas/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Fechas
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    
    # Usuario que anula
    anulada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boletas_anuladas'
    )
    motivo_anulacion = models.TextField(blank=True, null=True)
    
    # Metadata
    observaciones = models.TextField(blank=True, null=True)
    objects = TenantManager(school_field='pago__cuota__matricula__colegio_id')
    
    class Meta:
        db_table = 'boleta'
        verbose_name = 'Boleta'
        verbose_name_plural = 'Boletas'
        ordering = ['-fecha_emision']
        indexes = [
            models.Index(fields=['estudiante', '-fecha_emision']),
            models.Index(fields=['numero_boleta']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        return f"Boleta N° {self.numero_boleta} - {self.estudiante.get_full_name()}"


class SolicitudAdmision(models.Model):
    """Solicitud de admisión para un alumno (nuevo o existente)"""
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Revisión'),
        ('DOCUMENTOS_RECHAZADOS', 'Documentos Rechazados'),
        ('EN_LISTA_ESPERA', 'En Lista de Espera'),
        ('ACEPTADA', 'Aceptada (Cupo Reservado)'),
        ('FIRMADA', 'Contrato Firmado / Matriculado'),
        ('RECHAZADA', 'Rechazada'),
        ('CANCELADA', 'Cancelada por el Apoderado'),
    ]
    
    id_solicitud = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='solicitudes_admision')
    apoderado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_admision_apoderado')
    ciclo_academico = models.ForeignKey(CicloAcademico, on_delete=models.CASCADE, related_name='solicitudes_admision_ciclo')
    curso_postulado = models.ForeignKey('cursos.Curso', on_delete=models.CASCADE, related_name='solicitudes_admision_curso')
    
    # Datos del estudiante
    estudiante = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_admision_estudiante'
    )
    nombre_estudiante = models.CharField(max_length=100)
    apellido_paterno_estudiante = models.CharField(max_length=100)
    apellido_materno_estudiante = models.CharField(max_length=100)
    rut_estudiante = models.CharField(max_length=20, null=True, blank=True)
    fecha_nacimiento_estudiante = models.DateField(null=True, blank=True)
    genero_estudiante = models.CharField(
        max_length=20,
        choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')],
        default='O'
    )
    
    # Ficha familiar / Contacto
    direccion_hogar = models.CharField(max_length=255, blank=True, default='')
    telefono_contacto = models.CharField(max_length=50, blank=True, default='')
    parentesco = models.CharField(
        max_length=50,
        choices=[
            ('PADRE', 'Padre'),
            ('MADRE', 'Madre'),
            ('ABUELO', 'Abuelo/a'),
            ('TIO', 'Tío/a'),
            ('TUTOR_LEGAL', 'Tutor Legal'),
            ('OTRO', 'Otro')
        ],
        default='OTRO'
    )
    
    # Certificados adjuntos
    certificado_nacimiento = models.FileField(
        upload_to='admisiones/certificados_nacimiento/%Y/%m/',
        blank=True,
        null=True
    )
    certificado_medico = models.FileField(
        upload_to='admisiones/certificados_medicos/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Estado del trámite y cola
    estado = models.CharField(max_length=30, choices=ESTADOS, default='PENDIENTE')
    posicion_lista_espera = models.IntegerField(null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True, default='')
    
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'solicitud_admision'
        verbose_name = 'Solicitud de Admisión'
        verbose_name_plural = 'Solicitudes de Admisión'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Solicitud {self.nombre_estudiante} - {self.curso_postulado.nombre} ({self.estado})"


class ContratoServicioEducacional(models.Model):
    """Contrato de prestación de servicios educacionales y su firma electrónica"""
    id_contrato = models.AutoField(primary_key=True)
    solicitud = models.OneToOneField(SolicitudAdmision, on_delete=models.CASCADE, related_name='contrato')
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='contratos_admision')
    apoderado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contratos_apoderado')
    ciclo_academico = models.ForeignKey(CicloAcademico, on_delete=models.CASCADE, related_name='contratos_ciclo')
    
    # Datos financieros
    valor_arancel_anual = models.DecimalField(max_digits=10, decimal_places=0, default=Decimal('2500000'))
    valor_matricula = models.DecimalField(max_digits=10, decimal_places=0, default=Decimal('150000'))
    numero_cuotas = models.IntegerField(default=10)
    
    # Cuerpo legal
    titulo_contrato = models.CharField(max_length=200, default='Contrato de Prestación de Servicios Educacionales')
    cuerpo_contrato = models.TextField()
    
    # Auditoría Firma Electrónica Simple
    firmado = models.BooleanField(default=False)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    ip_firma = models.GenericIPAddressField(null=True, blank=True)
    user_agent_firma = models.TextField(null=True, blank=True)
    rut_firmante = models.CharField(max_length=20, null=True, blank=True)
    firma_hash = models.CharField(max_length=64, null=True, blank=True)
    firma_token = models.CharField(max_length=100, null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    objects = TenantManager(school_field='colegio_id')
    
    class Meta:
        db_table = 'contrato_servicio_educacional'
        verbose_name = 'Contrato de Servicio Educacional'
        verbose_name_plural = 'Contratos de Servicio Educacional'
        
    def __str__(self):
        estado_str = "FIRMADO" if self.firmado else "PENDIENTE"
        return f"Contrato {self.solicitud.nombre_estudiante} ({estado_str})"


# Fase 3 (Domain Redesign): modelos avanzados expuestos desde el módulo de matrículas
from backend.apps.core.models import (  # noqa: E402,F401
    EstadoMatricula,
    MatriculaMejorada,
    CambioEstadoMatricula,
)

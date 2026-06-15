# comunicados/admin.py
from django.contrib import admin
from .models import Comunicado, ConfirmacionLectura, AdjuntoComunicado, PlantillaComunicado, EstadisticaComunicado


class AdjuntoInline(admin.TabularInline):
    model = AdjuntoComunicado
    extra = 1
    readonly_fields = ('tamanio_bytes', 'tipo_mime', 'fecha_subida')


@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'destinatario', 'es_prioritario', 'es_destacado', 'fecha_publicacion', 'publicado_por', 'activo')
    list_filter = ('tipo', 'destinatario', 'es_prioritario', 'es_destacado', 'activo', 'fecha_publicacion')
    search_fields = ('titulo', 'contenido')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    filter_horizontal = ('cursos_destinatarios',)
    inlines = [AdjuntoInline]
    date_hierarchy = 'fecha_publicacion'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('colegio', 'tipo', 'titulo', 'contenido')
        }),
        ('Destinatarios', {
            'fields': ('destinatario', 'cursos_destinatarios')
        }),
        ('Archivos', {
            'fields': ('archivo_adjunto',)
        }),
        ('Evento/Citación', {
            'fields': ('fecha_evento', 'lugar_evento', 'requiere_confirmacion'),
            'classes': ('collapse',)
        }),
        ('Configuración', {
            'fields': ('es_prioritario', 'es_destacado', 'activo')
        }),
        ('Metadata', {
            'fields': ('publicado_por', 'fecha_publicacion', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ConfirmacionLectura)
class ConfirmacionLecturaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'comunicado', 'leido', 'fecha_lectura', 'confirmado', 'fecha_confirmacion')
    list_filter = ('leido', 'confirmado', 'fecha_lectura')
    search_fields = ('usuario__nombre', 'usuario__apellido_paterno', 'comunicado__titulo')


@admin.register(PlantillaComunicado)
class PlantillaComunicadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'colegio', 'veces_usada', 'activa', 'fecha_creacion', 'creada_por')
    list_filter = ('categoria', 'activa', 'tipo_default', 'destinatario_default', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion', 'titulo_plantilla', 'contenido_plantilla')
    readonly_fields = ('veces_usada', 'fecha_creacion', 'fecha_actualizacion')
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('colegio', 'nombre', 'categoria', 'descripcion', 'activa')
        }),
        ('Contenido de la Plantilla', {
            'fields': ('titulo_plantilla', 'contenido_plantilla'),
            'description': 'Usa variables como {{nombre_estudiante}}, {{curso}}, {{fecha}}, etc.'
        }),
        ('Configuración por Defecto', {
            'fields': ('tipo_default', 'destinatario_default', 'requiere_confirmacion_default', 'es_prioritario_default')
        }),
        ('Estadísticas', {
            'fields': ('veces_usada',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('creada_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'colegio'):
            return qs.filter(colegio=request.user.colegio)
        return qs.none()


@admin.register(EstadisticaComunicado)
class EstadisticaComunicadoAdmin(admin.ModelAdmin):
    list_display = (
        'comunicado', 
        'total_destinatarios', 
        'total_leidos', 
        'porcentaje_lectura',
        'total_confirmados',
        'porcentaje_confirmacion',
        'tiempo_promedio_lectura_horas',
        'fecha_calculo'
    )
    list_filter = ('comunicado__tipo', 'comunicado__destinatario')
    search_fields = ('comunicado__titulo',)
    readonly_fields = (
        'comunicado',
        'total_destinatarios',
        'total_leidos',
        'porcentaje_lectura',
        'total_confirmados',
        'porcentaje_confirmacion',
        'destinatarios_profesores',
        'leidos_profesores',
        'destinatarios_estudiantes',
        'leidos_estudiantes',
        'destinatarios_apoderados',
        'leidos_apoderados',
        'tiempo_promedio_lectura_horas',
        'fecha_calculo'
    )
    
    fieldsets = (
        ('Comunicado', {
            'fields': ('comunicado',)
        }),
        ('Estadísticas Generales', {
            'fields': (
                'total_destinatarios',
                'total_leidos',
                'porcentaje_lectura',
                'tiempo_promedio_lectura_horas'
            )
        }),
        ('Confirmaciones', {
            'fields': (
                'total_confirmados',
                'porcentaje_confirmacion'
            ),
            'classes': ('collapse',)
        }),
        ('Desglose por Rol', {
            'fields': (
                ('destinatarios_profesores', 'leidos_profesores'),
                ('destinatarios_estudiantes', 'leidos_estudiantes'),
                ('destinatarios_apoderados', 'leidos_apoderados')
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('fecha_calculo',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalcular_estadisticas']
    
    def recalcular_estadisticas(self, request, queryset):
        """Acción para recalcular estadísticas de comunicados seleccionados"""
        for estadistica in queryset:
            estadistica.calcular_estadisticas()
        self.message_user(request, f'✅ Se recalcularon las estadísticas de {queryset.count()} comunicados.')
    recalcular_estadisticas.short_description = '🔄 Recalcular estadísticas'
    
    def has_add_permission(self, request):
        # Las estadísticas se crean automáticamente
        return False
    
    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar estadísticas manualmente
        return False


@admin.register(AdjuntoComunicado)
class AdjuntoComunicadoAdmin(admin.ModelAdmin):
    list_display = ('nombre_archivo', 'comunicado', 'tamanio_bytes', 'fecha_subida')
    list_filter = ('fecha_subida',)
    search_fields = ('nombre_archivo', 'descripcion', 'comunicado__titulo')
    readonly_fields = ('tamanio_bytes', 'tipo_mime', 'fecha_subida')

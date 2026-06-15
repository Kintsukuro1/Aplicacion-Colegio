"""
Modelos del módulo de Cursos
Migrados desde sistema_antiguo/cursos/models.py
Compatible con autopoblar.py sin modificaciones
"""
from django.db import models
from backend.apps.institucion.models import Colegio, NivelEducativo, CicloAcademico
from backend.apps.accounts.models import User
from backend.common.tenancy import TenantManager


class CursoManager(TenantManager):
    """Manager con compatibilidad para payloads legacy de creación de cursos."""

    def create(self, **kwargs):
        legacy_ciclo = kwargs.pop('ciclo', None)
        grado = kwargs.pop('grado', None)
        letra = kwargs.pop('letra', None)
        kwargs.pop('anio_escolar', None)

        if legacy_ciclo is not None and 'ciclo_academico' not in kwargs:
            kwargs['ciclo_academico'] = legacy_ciclo

        if not kwargs.get('nombre'):
            if grado and letra:
                kwargs['nombre'] = f"{grado}° {letra}"
            elif grado:
                kwargs['nombre'] = str(grado)
            else:
                kwargs['nombre'] = 'Curso'

        return super().create(**kwargs)


class Curso(models.Model):
    """Curso (ejemplo: 1° Básico A)"""
    id_curso = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='cursos')
    nombre = models.CharField(max_length=50)
    nivel = models.ForeignKey(NivelEducativo, on_delete=models.PROTECT)
    ciclo_academico = models.ForeignKey(
        CicloAcademico,
        on_delete=models.CASCADE,
        related_name='cursos',
        null=True,
        blank=True
    )
    activo = models.BooleanField(default=True)
    objects = CursoManager(school_field='colegio_id')

    class Meta:
        db_table = 'curso'
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        unique_together = ('colegio', 'nombre', 'ciclo_academico')

    def __str__(self):
        ciclo_nombre = self.ciclo_academico.nombre if self.ciclo_academico else "Sin ciclo"
        return f"{self.nombre} - {self.colegio.nombre} ({ciclo_nombre})"

    @property
    def anio_escolar(self):
        if self.ciclo_academico and self.ciclo_academico.fecha_inicio:
            return self.ciclo_academico.fecha_inicio.year
        return None


class Asignatura(models.Model):
    """Asignatura o materia"""
    id_asignatura = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='asignaturas')
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, null=True, blank=True)
    horas_semanales = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#667eea')  # Color en formato hexadecimal
    activa = models.BooleanField(default=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'asignatura'
        verbose_name = 'Asignatura'
        verbose_name_plural = 'Asignaturas'
        unique_together = ('colegio', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.colegio.nombre})"
    
    def save(self, *args, **kwargs):
        # Asignar color aleatorio si no tiene uno
        if not self.color or self.color == '#667eea':
            import random
            colores_disponibles = [
                '#667eea', '#764ba2', '#f093fb', '#4facfe',
                '#43e97b', '#fa709a', '#fee140', '#30cfd0',
                '#a8edea', '#fbc2eb', '#ff9a9e', '#ffecd2',
                '#fcb69f', '#ff6e7f', '#bfe9ff', '#c471f5',
                '#fa709a', '#ffd89b', '#19547b', '#ff758c'
            ]
            self.color = random.choice(colores_disponibles)
        super().save(*args, **kwargs)


class Clase(models.Model):
    """Representa la combinación curso+asignatura+profesor en un colegio"""
    id = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='clases')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='clases')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='clases')
    # SET_NULL: permite desactivar profesor pero preserva historial de clases
    profesor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='clases_impartidas'
    )
    activo = models.BooleanField(default=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'clase'
        verbose_name = 'Clase'
        verbose_name_plural = 'Clases'
        # unique_together removido: profesor puede ser NULL

    def __str__(self):
        return f"{self.colegio.nombre} - {self.curso.nombre} - {self.asignatura.nombre} ({self.profesor})"
    
    def clean(self):
        """
        Validaciones de integridad de negocio.
        
        REGLAS DE NEGOCIO:
        1. No se puede asignar profesor INACTIVO a clase
        2. Clase ACTIVA requiere curso ACTIVO
        3. Clase ACTIVA requiere asignatura ACTIVA
        """
        from backend.common.exceptions import PrerequisiteException
        
        # Solo validar clases activas (para permitir historial de clases inactivas)
        if not self.activo:
            return
        
        # VALIDACIÓN 1: Profesor debe estar activo
        if self.profesor and not self.profesor.is_active:
            raise PrerequisiteException(
                error_type='INVALID_PROFESOR_STATE',
                context={
                    'profesor_id': self.profesor.id,
                    'profesor_nombre': self.profesor.get_full_name(),
                    'clase_id': self.pk,
                    'message': f'No se puede asignar profesor inactivo a clase activa: {self.profesor.get_full_name()}',
                    'action': 'Active al profesor primero o asigne otro profesor'
                }
            )
        
        # VALIDACIÓN 2: Curso debe estar activo
        if self.curso and not self.curso.activo:
            raise PrerequisiteException(
                error_type='INVALID_CURSO_STATE',
                context={
                    'curso_id': self.curso.id_curso,
                    'curso_nombre': self.curso.nombre,
                    'clase_id': self.pk,
                    'message': f'No se puede tener clase activa con curso inactivo: {self.curso.nombre}',
                    'action': 'Active el curso primero o desactive la clase'
                }
            )
        
        # VALIDACIÓN 3: Asignatura debe estar activa
        if self.asignatura and not self.asignatura.activa:
            raise PrerequisiteException(
                error_type='INVALID_ASIGNATURA_STATE',
                context={
                    'asignatura_id': self.asignatura.id_asignatura,
                    'asignatura_nombre': self.asignatura.nombre,
                    'clase_id': self.pk,
                    'message': f'No se puede tener clase activa con asignatura inactiva: {self.asignatura.nombre}',
                    'action': 'Active la asignatura primero o desactive la clase'
                }
            )
    
    def save(self, *args, **kwargs):
        """Override save para ejecutar validaciones de negocio."""
        self.clean()
        super().save(*args, **kwargs)


class BloqueHorario(models.Model):
    """Bloque de horario semanal (45 minutos cada bloque)"""
    DIAS_SEMANA = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
    ]
    
    id_bloque = models.AutoField(primary_key=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='bloques_horario')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='bloques_horario')
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)  # 1=Lunes, 2=Martes... 5=Viernes
    bloque_numero = models.IntegerField()  # 1, 2, 3, 4... (cada bloque = 45 min)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)
    objects = TenantManager(school_field='colegio_id')

    class Meta:
        db_table = 'bloque_horario'
        verbose_name = 'Bloque Horario'
        verbose_name_plural = 'Bloques Horarios'
        unique_together = ('colegio', 'dia_semana', 'bloque_numero', 'clase')
        ordering = ['dia_semana', 'bloque_numero']

    def __str__(self):
        return f"{self.get_dia_semana_display()} - Bloque {self.bloque_numero} - {self.clase.asignatura.nombre} ({self.clase.curso.nombre})"


class ClaseEstudiante(models.Model):
    """Relación entre clase y estudiante (matrícula en clase específica)"""
    id_clase_estudiante = models.AutoField(primary_key=True)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='estudiantes')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clases_matriculadas')
    fecha_matricula = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    objects = TenantManager(school_field='clase__colegio_id')

    class Meta:
        db_table = 'clase_estudiante'
        verbose_name = 'Estudiante en Clase'
        verbose_name_plural = 'Estudiantes en Clases'
        unique_together = ('clase', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.clase.asignatura.nombre} ({self.clase.curso.nombre})"

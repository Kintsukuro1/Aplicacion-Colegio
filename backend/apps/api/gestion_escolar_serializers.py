"""
Serializers para funcionalidades Semana 3-4:
D. Gestión de Profesores (CRUD administrativo)
E. Firma Digital de Apoderados
F. Materiales de Clase
G. Horario Semanal del Profesor
"""
from rest_framework import serializers

from backend.apps.accounts.models import (
    FirmaDigitalApoderado,
    PerfilProfesor,
    User,
)
from backend.apps.academico.models import MaterialClase
from backend.apps.cursos.models import BloqueHorario, Clase


# ───────────────────────────────────────────
# D. Gestión de Profesores
# ───────────────────────────────────────────

class TeacherAdminSerializer(serializers.ModelSerializer):
    """Serializer completo para vista/detalle de profesor por admin."""
    role = serializers.CharField(source='role.nombre', read_only=True)
    perfil = serializers.SerializerMethodField()
    clases_activas = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'rut', 'nombre', 'apellido_paterno',
            'apellido_materno', 'is_active', 'rbd_colegio', 'role',
            'fecha_creacion', 'perfil', 'clases_activas',
        ]
        read_only_fields = ['id', 'rbd_colegio', 'role', 'fecha_creacion']

    @staticmethod
    def get_perfil(obj):
        perfil = getattr(obj, 'perfil_profesor', None)
        if not perfil:
            return None
        return {
            'especialidad': perfil.especialidad,
            'titulo_profesional': perfil.titulo_profesional,
            'universidad': perfil.universidad,
            'anio_titulacion': perfil.anio_titulacion,
            'estado_laboral': perfil.estado_laboral,
            'fecha_ingreso': perfil.fecha_ingreso.isoformat() if perfil.fecha_ingreso else None,
            'horas_semanales_contrato': perfil.horas_semanales_contrato,
            'horas_no_lectivas': perfil.horas_no_lectivas,
            'horas_lectivas': perfil.horas_lectivas,
            'telefono': perfil.telefono,
            'telefono_movil': perfil.telefono_movil,
            'direccion': perfil.direccion,
        }

    @staticmethod
    def get_clases_activas(obj):
        return obj.clases_como_profesor.filter(activo=True).count() if hasattr(obj, 'clases_como_profesor') else 0


class TeacherAdminListSerializer(serializers.ModelSerializer):
    """Lista compacta de profesores."""
    nombre_completo = serializers.CharField(source='get_full_name', read_only=True)
    estado = serializers.SerializerMethodField()
    especialidad = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'nombre_completo', 'email', 'estado', 'especialidad']

    @staticmethod
    def get_estado(obj):
        return 'ACTIVO' if obj.is_active else 'INACTIVO'

    @staticmethod
    def get_especialidad(obj):
        perfil = getattr(obj, 'perfil_profesor', None)
        return perfil.especialidad if perfil else None


class TeacherAdminCreateUpdateSerializer(serializers.Serializer):
    """Creación/actualización de profesor."""
    email = serializers.EmailField()
    rut = serializers.CharField(max_length=12, required=False, allow_blank=True)
    nombre = serializers.CharField(max_length=50)
    apellido_paterno = serializers.CharField(max_length=50)
    apellido_materno = serializers.CharField(max_length=50, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)
    # Perfil
    especialidad = serializers.CharField(max_length=100, required=False, allow_blank=True)
    titulo_profesional = serializers.CharField(max_length=150, required=False, allow_blank=True)
    universidad = serializers.CharField(max_length=150, required=False, allow_blank=True)
    anio_titulacion = serializers.IntegerField(required=False, allow_null=True)
    horas_semanales_contrato = serializers.IntegerField(required=False, default=44)
    horas_no_lectivas = serializers.IntegerField(required=False, default=0)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)


class TeacherAssignClassSerializer(serializers.Serializer):
    """Asignar un profesor a una clase."""
    clase_id = serializers.IntegerField()


# ───────────────────────────────────────────
# E. Firma Digital Apoderado
# ───────────────────────────────────────────

class FirmaDigitalSerializer(serializers.ModelSerializer):
    """Firma digital completa (lectura)."""
    apoderado_nombre = serializers.SerializerMethodField()
    estudiante_nombre = serializers.SerializerMethodField()

    class Meta:
        model = FirmaDigitalApoderado
        fields = [
            'id', 'apoderado', 'apoderado_nombre', 'estudiante', 'estudiante_nombre',
            'tipo_documento', 'titulo_documento', 'contenido_documento',
            'documento_id', 'documento_tipo_modelo',
            'timestamp_firma', 'ip_address',
            'firma_en_representacion', 'firma_valida',
            'observaciones',
        ]

    @staticmethod
    def get_apoderado_nombre(obj):
        return obj.apoderado.user.get_full_name() if obj.apoderado and obj.apoderado.user else None

    @staticmethod
    def get_estudiante_nombre(obj):
        return obj.estudiante.get_full_name() if obj.estudiante else None


class FirmaDigitalListSerializer(serializers.ModelSerializer):
    """Lista compacta de firmas."""
    class Meta:
        model = FirmaDigitalApoderado
        fields = ['id', 'tipo_documento', 'titulo_documento', 'timestamp_firma', 'firma_valida']


class FirmaDigitalCreateSerializer(serializers.Serializer):
    """Crear una firma digital."""
    estudiante_id = serializers.IntegerField(required=False, allow_null=True)
    tipo_documento = serializers.ChoiceField(
        choices=[c[0] for c in FirmaDigitalApoderado.TIPO_DOCUMENTO]
    )
    titulo_documento = serializers.CharField(max_length=255)
    contenido_documento = serializers.CharField()
    documento_id = serializers.IntegerField(required=False, allow_null=True)
    documento_tipo_modelo = serializers.CharField(max_length=50, required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


# ───────────────────────────────────────────
# F. Materiales de Clase
# ───────────────────────────────────────────

class MaterialClaseSerializer(serializers.ModelSerializer):
    """Material completo (lectura)."""
    subido_por_nombre = serializers.CharField(source='subido_por.get_full_name', read_only=True)
    asignatura_nombre = serializers.SerializerMethodField()
    curso_nombre = serializers.SerializerMethodField()
    tamanio_legible = serializers.CharField(source='get_tamanio_legible', read_only=True)
    icono = serializers.CharField(source='get_icono', read_only=True)

    class Meta:
        model = MaterialClase
        fields = [
            'id_material', 'colegio_id', 'clase_id',
            'titulo', 'descripcion', 'archivo', 'tipo_archivo',
            'es_publico', 'tamanio_legible', 'icono',
            'subido_por', 'subido_por_nombre',
            'asignatura_nombre', 'curso_nombre',
            'activo', 'fecha_creacion', 'fecha_actualizacion',
        ]

    @staticmethod
    def get_asignatura_nombre(obj):
        return obj.clase.asignatura.nombre if obj.clase and obj.clase.asignatura else None

    @staticmethod
    def get_curso_nombre(obj):
        return obj.clase.curso.nombre if obj.clase and obj.clase.curso else None


class MaterialClaseListSerializer(serializers.ModelSerializer):
    """Lista compacta de materiales."""
    icono = serializers.CharField(source='get_icono', read_only=True)

    class Meta:
        model = MaterialClase
        fields = ['id_material', 'titulo', 'tipo_archivo', 'icono', 'es_publico', 'fecha_creacion']


# ───────────────────────────────────────────
# G. Horario Semanal
# ───────────────────────────────────────────

class BloqueHorarioSerializer(serializers.ModelSerializer):
    """Bloque de horario para vista semanal."""
    asignatura_nombre = serializers.SerializerMethodField()
    curso_nombre = serializers.SerializerMethodField()
    profesor_nombre = serializers.SerializerMethodField()
    dia_nombre = serializers.CharField(source='get_dia_semana_display', read_only=True)

    class Meta:
        model = BloqueHorario
        fields = [
            'id_bloque', 'dia_semana', 'dia_nombre', 'bloque_numero',
            'hora_inicio', 'hora_fin',
            'clase_id', 'asignatura_nombre', 'curso_nombre', 'profesor_nombre',
            'activo',
        ]

    @staticmethod
    def get_asignatura_nombre(obj):
        return obj.clase.asignatura.nombre if obj.clase and obj.clase.asignatura else None

    @staticmethod
    def get_curso_nombre(obj):
        return obj.clase.curso.nombre if obj.clase and obj.clase.curso else None

    @staticmethod
    def get_profesor_nombre(obj):
        return obj.clase.profesor.get_full_name() if obj.clase and obj.clase.profesor else None

"""
Serializers para endpoints de perfil personal (self-service).

Cada rol tiene su propio serializer que expone solo los campos que el
propio usuario puede ver y editar de su perfil.
"""
from rest_framework import serializers

from backend.apps.accounts.models import (
    Apoderado,
    PerfilEstudiante,
    PerfilProfesor,
    User,
)


# ───────────────────────────────────────────
# Base: campos comunes de User
# ───────────────────────────────────────────

class _UserBaseReadSerializer(serializers.ModelSerializer):
    """Campos de User de solo lectura compartidos por todos los roles."""
    role = serializers.CharField(source='role.nombre', read_only=True)
    colegio_nombre = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'rut', 'nombre', 'apellido_paterno',
            'apellido_materno', 'rbd_colegio', 'role', 'colegio_nombre',
            'is_active', 'fecha_creacion',
        ]

    @staticmethod
    def get_colegio_nombre(obj):
        colegio = getattr(obj, 'colegio', None)
        return getattr(colegio, 'nombre', None) if colegio else None


class _UserSelfUpdateSerializer(serializers.Serializer):
    """Campos de User que cualquier usuario puede editar de sí mismo."""
    telefono_movil = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)


# ───────────────────────────────────────────
# ESTUDIANTE
# ───────────────────────────────────────────

class StudentSelfProfileReadSerializer(serializers.ModelSerializer):
    """GET: Perfil completo del estudiante (user + perfil_estudiante)."""
    user = _UserBaseReadSerializer(read_only=True)
    curso_actual_nombre = serializers.SerializerMethodField()
    edad = serializers.IntegerField(read_only=True)

    class Meta:
        model = PerfilEstudiante
        fields = [
            'user',
            'fecha_nacimiento', 'direccion', 'telefono', 'telefono_movil',
            'contacto_emergencia_nombre', 'contacto_emergencia_relacion',
            'contacto_emergencia_telefono',
            'grupo_sanguineo', 'alergias', 'condiciones_medicas',
            'tiene_nee', 'tipo_nee',
            'estado_academico', 'curso_actual_nombre', 'edad',
            'foto_url',
        ]

    @staticmethod
    def get_curso_actual_nombre(obj):
        curso = obj.curso_actual
        return getattr(curso, 'nombre', None) if curso else None


class StudentSelfProfileUpdateSerializer(serializers.Serializer):
    """PATCH: Campos que un estudiante puede editar de sí mismo."""
    telefono_movil = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    contacto_emergencia_nombre = serializers.CharField(max_length=100, required=False, allow_blank=True)
    contacto_emergencia_relacion = serializers.CharField(max_length=50, required=False, allow_blank=True)
    contacto_emergencia_telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    alergias = serializers.CharField(required=False, allow_blank=True)
    condiciones_medicas = serializers.CharField(required=False, allow_blank=True)


# ───────────────────────────────────────────
# PROFESOR
# ───────────────────────────────────────────

class TeacherSelfProfileReadSerializer(serializers.ModelSerializer):
    """GET: Perfil completo del profesor (user + perfil_profesor)."""
    user = _UserBaseReadSerializer(read_only=True)
    edad = serializers.IntegerField(read_only=True)
    horas_lectivas = serializers.IntegerField(read_only=True)

    class Meta:
        model = PerfilProfesor
        fields = [
            'user',
            'fecha_nacimiento', 'direccion', 'telefono', 'telefono_movil',
            'especialidad', 'titulo_profesional', 'universidad', 'anio_titulacion',
            'fecha_ingreso', 'estado_laboral',
            'horas_semanales_contrato', 'horas_no_lectivas', 'horas_lectivas',
            'foto_url', 'edad',
        ]


class TeacherSelfProfileUpdateSerializer(serializers.Serializer):
    """PATCH: Campos que un profesor puede editar de sí mismo."""
    telefono_movil = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    foto_url = serializers.CharField(max_length=255, required=False, allow_blank=True)


# ───────────────────────────────────────────
# APODERADO
# ───────────────────────────────────────────

class ApoderadoSelfProfileReadSerializer(serializers.ModelSerializer):
    """GET: Perfil completo del apoderado (user + apoderado)."""
    user = _UserBaseReadSerializer(read_only=True)
    estudiantes_vinculados = serializers.SerializerMethodField()

    class Meta:
        model = Apoderado
        fields = [
            'user',
            'fecha_nacimiento', 'direccion', 'telefono', 'telefono_movil',
            'ocupacion', 'lugar_trabajo', 'telefono_trabajo',
            'puede_ver_notas', 'puede_ver_asistencia',
            'puede_recibir_comunicados', 'puede_firmar_citaciones',
            'puede_autorizar_salidas', 'puede_ver_tareas', 'puede_ver_materiales',
            'activo', 'estudiantes_vinculados',
        ]

    @staticmethod
    def get_estudiantes_vinculados(obj):
        from backend.apps.accounts.models import RelacionApoderadoEstudiante
        relaciones = RelacionApoderadoEstudiante.objects.filter(
            apoderado=obj, activa=True
        ).select_related('estudiante')
        return [
            {
                'id': rel.estudiante.id,
                'nombre': rel.estudiante.get_full_name(),
                'parentesco': rel.parentesco,
                'tipo_apoderado': rel.tipo_apoderado,
            }
            for rel in relaciones
        ]


class ApoderadoSelfProfileUpdateSerializer(serializers.Serializer):
    """PATCH: Campos que un apoderado puede editar de sí mismo."""
    telefono_movil = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    ocupacion = serializers.CharField(max_length=100, required=False, allow_blank=True)
    lugar_trabajo = serializers.CharField(max_length=150, required=False, allow_blank=True)
    telefono_trabajo = serializers.CharField(max_length=20, required=False, allow_blank=True)


# ───────────────────────────────────────────
# ADMINISTRADOR / ADMIN ESCOLAR
# ───────────────────────────────────────────

class AdminSelfProfileReadSerializer(serializers.ModelSerializer):
    """GET: Perfil de administrador (user sin perfil extendido)."""
    role = serializers.CharField(source='role.nombre', read_only=True)
    colegio_nombre = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'rut', 'nombre', 'apellido_paterno',
            'apellido_materno', 'rbd_colegio', 'role', 'colegio_nombre',
            'is_active', 'fecha_creacion',
        ]

    @staticmethod
    def get_colegio_nombre(obj):
        colegio = getattr(obj, 'colegio', None)
        return getattr(colegio, 'nombre', None) if colegio else None


class AdminSelfProfileUpdateSerializer(serializers.Serializer):
    """PATCH: Campos que un admin puede editar de sí mismo (nombre, etc)."""
    nombre = serializers.CharField(max_length=50, required=False)
    apellido_paterno = serializers.CharField(max_length=50, required=False)
    apellido_materno = serializers.CharField(max_length=50, required=False, allow_blank=True)


# ───────────────────────────────────────────
# Cambio de contraseña (todos los roles)
# ───────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña por el propio usuario."""
    password_actual = serializers.CharField(write_only=True, min_length=1)
    password_nueva = serializers.CharField(write_only=True, min_length=6)
    password_confirmar = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        if attrs['password_nueva'] != attrs['password_confirmar']:
            raise serializers.ValidationError({
                'password_confirmar': 'Las contraseñas nuevas no coinciden.'
            })
        return attrs

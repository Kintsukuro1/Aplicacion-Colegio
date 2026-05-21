from rest_framework import serializers

from backend.apps.accounts.models import Apoderado, PerfilEstudiante, RelacionApoderadoEstudiante, User
from backend.apps.academico.models import (
    ActividadResoluble,
    Asistencia,
    Calificacion,
    Evaluacion,
    IntentoResoluble,
    OpcionPreguntaResoluble,
    PreguntaResoluble,
    RespuestaResoluble,
)
from backend.apps.cursos.models import Asignatura, Clase, ClaseEstudiante
from backend.apps.cursos.models import Curso
from backend.apps.institucion.models import CicloAcademico, NivelEducativo
from backend.apps.matriculas.models import Matricula
from backend.apps.academico.services.resoluble_service import ResolubleService


class StudentSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.nombre', read_only=True)
    estado_academico = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'rut',
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'is_active',
            'rbd_colegio',
            'role',
            'estado_academico',
        ]
        read_only_fields = ['id', 'rbd_colegio', 'role']

    def get_estado_academico(self, obj):
        perfil = getattr(obj, 'perfil_estudiante', None)
        return getattr(perfil, 'estado_academico', None)


class StudentListSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'nombre',
            'estado',
        ]

    def get_nombre(self, obj):
        return obj.get_full_name()

    def get_estado(self, obj):
        return 'ACTIVO' if obj.is_active else 'INACTIVO'


class StudentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'rut',
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'is_active',
        ]


class CursoSerializer(serializers.ModelSerializer):
    colegio_id = serializers.IntegerField(read_only=True)
    nivel_id = serializers.PrimaryKeyRelatedField(source='nivel', queryset=NivelEducativo.objects.all())
    ciclo_academico_id = serializers.PrimaryKeyRelatedField(
        source='ciclo_academico',
        queryset=CicloAcademico.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Curso
        fields = [
            'id_curso',
            'nombre',
            'activo',
            'colegio_id',
            'nivel_id',
            'ciclo_academico_id',
        ]


class CursoListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_curso', read_only=True)
    estado = serializers.SerializerMethodField()
    activo = serializers.BooleanField(read_only=True)
    colegio_id = serializers.IntegerField(read_only=True)
    nivel_id = serializers.IntegerField(read_only=True)
    ciclo_academico_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Curso
        fields = [
            'id',
            'id_curso',
            'nombre',
            'estado',
            'activo',
            'colegio_id',
            'nivel_id',
            'ciclo_academico_id',
        ]

    def get_estado(self, obj):
        return 'ACTIVO' if obj.activo else 'INACTIVO'


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilEstudiante
        fields = [
            'fecha_nacimiento',
            'direccion',
            'telefono',
            'telefono_movil',
            'estado_academico',
            'apoderado_nombre',
            'apoderado_email',
            'apoderado_telefono',
            'observaciones',
        ]


class TeacherClassSerializer(serializers.ModelSerializer):
    curso_id = serializers.IntegerField(read_only=True)
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)
    asignatura_id = serializers.IntegerField(read_only=True)
    asignatura_nombre = serializers.CharField(source='asignatura.nombre', read_only=True)
    profesor_id = serializers.IntegerField(read_only=True)
    colegio_id = serializers.IntegerField(read_only=True)
    total_estudiantes = serializers.SerializerMethodField()

    class Meta:
        model = Clase
        fields = [
            'id',
            'colegio_id',
            'curso_id',
            'curso_nombre',
            'asignatura_id',
            'asignatura_nombre',
            'profesor_id',
            'activo',
            'total_estudiantes',
        ]

    def get_total_estudiantes(self, obj):
        return obj.estudiantes.filter(activo=True).count()


class TeacherClassCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clase
        fields = [
            'id',
            'curso_id',
            'asignatura_id',
            'activo',
        ]


class AttendanceSerializer(serializers.ModelSerializer):
    colegio_id = serializers.IntegerField(read_only=True)
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)

    class Meta:
        model = Asistencia
        fields = [
            'id_asistencia',
            'colegio_id',
            'clase',
            'estudiante',
            'estudiante_nombre',
            'fecha',
            'estado',
            'tipo_asistencia',
            'observaciones',
        ]
        read_only_fields = ['id_asistencia', 'colegio_id', 'estudiante_nombre']


class AttendanceCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asistencia
        fields = [
            'id_asistencia',
            'fecha',
            'estado',
        ]


class EvaluationSerializer(serializers.ModelSerializer):
    colegio_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Evaluacion
        fields = [
            'id_evaluacion',
            'colegio_id',
            'clase',
            'nombre',
            'fecha_evaluacion',
            'ponderacion',
            'periodo',
            'tipo_evaluacion',
            'es_recuperacion',
            'evaluacion_original',
            'activa',
        ]
        read_only_fields = ['id_evaluacion', 'colegio_id']


class EvaluationCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluacion
        fields = [
            'id_evaluacion',
            'clase',
            'fecha_evaluacion',
            'activa',
        ]


class GradeSerializer(serializers.ModelSerializer):
    colegio_id = serializers.IntegerField(read_only=True)
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)

    class Meta:
        model = Calificacion
        fields = [
            'id_calificacion',
            'colegio_id',
            'evaluacion',
            'estudiante',
            'estudiante_nombre',
            'nota',
            'registrado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = [
            'id_calificacion',
            'colegio_id',
            'estudiante_nombre',
            'registrado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_actualizacion',
        ]

    def validate_nota(self, value):
        from backend.common.utils.grade_scale import normalize_grade_value
        return normalize_grade_value(value)


class GradeCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calificacion
        fields = [
            'id_calificacion',
            'evaluacion',
            'estudiante',
            'nota',
        ]

    def validate_nota(self, value):
        from backend.common.utils.grade_scale import normalize_grade_value
        return normalize_grade_value(value)


class OpcionPreguntaResolubleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionPreguntaResoluble
        fields = [
            'id_opcion',
            'texto',
            'es_correcta',
            'orden',
        ]
        read_only_fields = ['id_opcion']


class PreguntaResolubleSerializer(serializers.ModelSerializer):
    opciones = OpcionPreguntaResolubleSerializer(many=True, required=False)

    class Meta:
        model = PreguntaResoluble
        fields = [
            'id_pregunta',
            'tipo',
            'enunciado',
            'orden',
            'puntaje_maximo',
            'respuesta_correcta_texto',
            'respuesta_correcta_normalizada',
            'requiere_revision_docente',
            'activa',
            'opciones',
        ]
        read_only_fields = ['id_pregunta']


class ActividadResolubleSerializer(serializers.ModelSerializer):
    origen_tipo = serializers.CharField(write_only=True, required=False)
    origen_id = serializers.IntegerField(write_only=True, required=False)
    preguntas = PreguntaResolubleSerializer(many=True, required=False)
    preguntas_total = serializers.SerializerMethodField(read_only=True)
    intentos_total = serializers.SerializerMethodField(read_only=True)
    archivo_pdf = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = ActividadResoluble
        fields = [
            'id_actividad_resoluble',
            'colegio',
            'origen_tipo',
            'origen_id',
            'titulo',
            'modalidad',
            'archivo_pdf',
            'requiere_aprobacion_docente',
            'auto_correccion_activa',
            'estado',
            'activa',
            'preguntas_total',
            'intentos_total',
            'preguntas',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = ['id_actividad_resoluble', 'colegio', 'preguntas_total', 'intentos_total', 'fecha_creacion', 'fecha_actualizacion']

    def get_preguntas_total(self, obj):
        return obj.preguntas.count()

    def get_intentos_total(self, obj):
        return obj.intentos.count()

    def validate(self, attrs):
        if self.instance is None:
            if not attrs.get('origen_tipo') or attrs.get('origen_id') is None:
                raise serializers.ValidationError({'origen_tipo': 'Este campo es requerido.', 'origen_id': 'Este campo es requerido.'})
        return attrs

    def create(self, validated_data):
        preguntas = validated_data.pop('preguntas', [])
        payload = {**validated_data, 'preguntas': preguntas}
        return ResolubleService.create_or_update_activity(actor=self.context['request'].user, payload=payload)

    def update(self, instance, validated_data):
        preguntas = validated_data.pop('preguntas', None)
        payload = {**validated_data, 'preguntas': preguntas if preguntas is not None else []}
        if preguntas is None:
            payload.pop('preguntas')
        return ResolubleService.create_or_update_activity(actor=self.context['request'].user, payload={
            'origen_tipo': 'tarea' if instance.actividad.__class__.__name__ == 'Tarea' else 'evaluacion',
            'origen_id': instance.object_id,
            **payload,
        })


class RespuestaResolubleSerializer(serializers.ModelSerializer):
    pregunta_texto = serializers.CharField(source='pregunta.enunciado', read_only=True)

    class Meta:
        model = RespuestaResoluble
        fields = [
            'id_respuesta',
            'pregunta',
            'pregunta_texto',
            'respuesta_texto',
            'opcion_seleccionada',
            'es_correcta',
            'puntaje_obtenido',
            'observaciones',
        ]
        read_only_fields = ['id_respuesta', 'es_correcta', 'puntaje_obtenido', 'observaciones']


class IntentoResolubleSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    respuestas = RespuestaResolubleSerializer(many=True, read_only=True)
    actividad_titulo = serializers.CharField(source='actividad_resoluble.titulo', read_only=True)

    class Meta:
        model = IntentoResoluble
        fields = [
            'id_intento',
            'actividad_resoluble',
            'actividad_titulo',
            'estudiante',
            'estudiante_nombre',
            'estado',
            'puntaje_maximo',
            'puntaje_obtenido',
            'nota_sugerida',
            'retroalimentacion',
            'requiere_revision_docente',
            'aprobado_por',
            'fecha_envio',
            'fecha_revision',
            'fecha_aprobacion',
            'resultado_publicado',
            'respuestas',
        ]
        read_only_fields = [
            'id_intento',
            'actividad_titulo',
            'estudiante_nombre',
            'estado',
            'puntaje_maximo',
            'puntaje_obtenido',
            'nota_sugerida',
            'requiere_revision_docente',
            'aprobado_por',
            'fecha_envio',
            'fecha_revision',
            'fecha_aprobacion',
            'resultado_publicado',
            'respuestas',
        ]


class IntentoSubmitSerializer(serializers.Serializer):
    actividad_resoluble_id = serializers.IntegerField()
    respuestas = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class IntentoApproveSerializer(serializers.Serializer):
    intento_id = serializers.IntegerField()
    retroalimentacion = serializers.CharField(required=False, allow_blank=True, default='')


class StudentSelfSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.nombre', read_only=True)
    perfil_estudiante = StudentProfileUpdateSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'rut',
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'rbd_colegio',
            'role',
            'perfil_estudiante',
        ]


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    clase_id = serializers.IntegerField(read_only=True)
    curso_id = serializers.IntegerField(source='clase.curso_id', read_only=True)
    curso_nombre = serializers.CharField(source='clase.curso.nombre', read_only=True)
    asignatura_id = serializers.IntegerField(source='clase.asignatura_id', read_only=True)
    asignatura_nombre = serializers.CharField(source='clase.asignatura.nombre', read_only=True)
    profesor_id = serializers.IntegerField(source='clase.profesor_id', read_only=True)
    profesor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ClaseEstudiante
        fields = [
            'id_clase_estudiante',
            'clase_id',
            'curso_id',
            'curso_nombre',
            'asignatura_id',
            'asignatura_nombre',
            'profesor_id',
            'profesor_nombre',
            'fecha_matricula',
            'activo',
        ]

    def get_profesor_nombre(self, obj):
        profesor = getattr(obj.clase, 'profesor', None)
        return profesor.get_full_name() if profesor else None


class StudentGradeSerializer(serializers.ModelSerializer):
    evaluacion_nombre = serializers.CharField(source='evaluacion.nombre', read_only=True)
    clase_id = serializers.IntegerField(source='evaluacion.clase_id', read_only=True)
    fecha_evaluacion = serializers.DateField(source='evaluacion.fecha_evaluacion', read_only=True)
    tipo_evaluacion = serializers.CharField(source='evaluacion.tipo_evaluacion', read_only=True)

    class Meta:
        model = Calificacion
        fields = [
            'id_calificacion',
            'evaluacion',
            'evaluacion_nombre',
            'clase_id',
            'fecha_evaluacion',
            'tipo_evaluacion',
            'nota',
            'fecha_creacion',
        ]

    def validate_nota(self, value):
        from backend.common.utils.grade_scale import normalize_grade_value
        return normalize_grade_value(value)


class StudentAttendanceSerializer(serializers.ModelSerializer):
    clase_id = serializers.IntegerField(read_only=True)
    curso_nombre = serializers.CharField(source='clase.curso.nombre', read_only=True)
    asignatura_nombre = serializers.CharField(source='clase.asignatura.nombre', read_only=True)

    class Meta:
        model = Asistencia
        fields = [
            'id_asistencia',
            'clase_id',
            'curso_nombre',
            'asignatura_nombre',
            'fecha',
            'estado',
            'tipo_asistencia',
            'observaciones',
        ]


class AsignaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asignatura
        fields = [
            'id_asignatura',
            'colegio',
            'nombre',
            'codigo',
            'horas_semanales',
            'color',
            'activa',
        ]
        read_only_fields = ['id_asignatura', 'colegio']


class AsignaturaListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_asignatura', read_only=True)
    estado = serializers.SerializerMethodField()

    class Meta:
        model = Asignatura
        fields = [
            'id',
            'nombre',
            'estado',
        ]

    def get_estado(self, obj):
        return 'ACTIVO' if obj.activa else 'INACTIVO'


class CicloAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CicloAcademico
        fields = [
            'id',
            'colegio',
            'nombre',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'descripcion',
            'periodos_config',
            'creado_por',
            'modificado_por',
        ]
        read_only_fields = ['id', 'colegio', 'creado_por', 'modificado_por']


class CicloAcademicoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CicloAcademico
        fields = [
            'id',
            'nombre',
            'estado',
        ]


class MatriculaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)

    class Meta:
        model = Matricula
        fields = [
            'id',
            'estudiante',
            'estudiante_nombre',
            'colegio',
            'curso',
            'valor_matricula',
            'valor_mensual',
            'estado',
            'ciclo_academico',
            'fecha_matricula',
            'fecha_inicio',
            'fecha_termino',
            'observaciones',
        ]
        read_only_fields = ['id', 'colegio', 'fecha_matricula']


class MatriculaListSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)

    class Meta:
        model = Matricula
        fields = [
            'id',
            'nombre',
            'estado',
        ]


class ApoderadoSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    nombre = serializers.CharField(source='user.nombre', read_only=True)
    apellido_paterno = serializers.CharField(source='user.apellido_paterno', read_only=True)
    apellido_materno = serializers.CharField(source='user.apellido_materno', read_only=True)
    rut = serializers.CharField(source='user.rut', read_only=True)

    class Meta:
        model = Apoderado
        fields = [
            'id',
            'user_id',
            'email',
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'rut',
            'fecha_nacimiento',
            'direccion',
            'telefono',
            'telefono_movil',
            'ocupacion',
            'lugar_trabajo',
            'telefono_trabajo',
            'puede_ver_notas',
            'puede_ver_asistencia',
            'puede_recibir_comunicados',
            'puede_firmar_citaciones',
            'puede_autorizar_salidas',
            'puede_ver_tareas',
            'puede_ver_materiales',
            'activo',
            'observaciones',
        ]


class ApoderadoListSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='user.get_full_name', read_only=True)
    estado = serializers.SerializerMethodField()

    class Meta:
        model = Apoderado
        fields = [
            'id',
            'nombre',
            'estado',
        ]

    def get_estado(self, obj):
        return 'ACTIVO' if obj.activo else 'INACTIVO'


class ApoderadoCreateUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nombre = serializers.CharField(max_length=50)
    apellido_paterno = serializers.CharField(max_length=50)
    apellido_materno = serializers.CharField(max_length=50, required=False, allow_blank=True)
    rut = serializers.CharField(max_length=12, required=False, allow_blank=True)
    fecha_nacimiento = serializers.DateField(required=False)
    direccion = serializers.CharField(required=False, allow_blank=True)
    telefono = serializers.CharField(required=False, allow_blank=True)
    telefono_movil = serializers.CharField(required=False, allow_blank=True)
    ocupacion = serializers.CharField(required=False, allow_blank=True)
    lugar_trabajo = serializers.CharField(required=False, allow_blank=True)
    telefono_trabajo = serializers.CharField(required=False, allow_blank=True)
    puede_ver_notas = serializers.BooleanField(required=False)
    puede_ver_asistencia = serializers.BooleanField(required=False)
    puede_recibir_comunicados = serializers.BooleanField(required=False)
    puede_firmar_citaciones = serializers.BooleanField(required=False)
    puede_autorizar_salidas = serializers.BooleanField(required=False)
    puede_ver_tareas = serializers.BooleanField(required=False)
    puede_ver_materiales = serializers.BooleanField(required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class ApoderadoRelacionSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    fecha_inicio = serializers.SerializerMethodField()
    fecha_fin = serializers.SerializerMethodField()

    class Meta:
        model = RelacionApoderadoEstudiante
        fields = [
            'id',
            'apoderado',
            'estudiante',
            'estudiante_nombre',
            'tipo_apoderado',
            'parentesco',
            'usar_permisos_personalizados',
            'puede_ver_notas',
            'puede_ver_asistencia',
            'puede_recibir_comunicados',
            'puede_firmar_citaciones',
            'puede_autorizar_salidas',
            'puede_ver_tareas',
            'puede_ver_materiales',
            'prioridad_contacto',
            'activa',
            'fecha_inicio',
            'fecha_fin',
            'observaciones',
        ]
        read_only_fields = ['id']

    def _serialize_date_like(self, value):
        if value is None:
            return None
        if hasattr(value, 'date'):
            try:
                return value.date().isoformat()
            except Exception:
                return str(value)
        return value.isoformat() if hasattr(value, 'isoformat') else str(value)

    def get_fecha_inicio(self, obj):
        return self._serialize_date_like(getattr(obj, 'fecha_inicio', None))

    def get_fecha_fin(self, obj):
        return self._serialize_date_like(getattr(obj, 'fecha_fin', None))

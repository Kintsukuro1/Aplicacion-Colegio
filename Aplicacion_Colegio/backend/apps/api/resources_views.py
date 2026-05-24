from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.accounts.models import Apoderado, User
from backend.apps.academico.models import ActividadResoluble, Asistencia, Calificacion, Evaluacion
from backend.apps.academico.services.resoluble_service import ResolubleService
from backend.apps.api.base import CapabilityModelViewSet
from backend.apps.api.helpers import (
    apply_search_filter,
    ensure_same_school,
    ensure_teacher_owns_class,
    forbid_without_cap,
    has_cap,
    is_global_admin,
    is_teacher,
    school_id,
)
from backend.apps.api.permissions import HasCapability
from backend.apps.api.services.academic_batch_api_service import AcademicBatchApiService
from backend.apps.api.services.asignatura_api_service import AsignaturaApiService
from backend.apps.api.services.apoderado_api_service import ApoderadoApiService
from backend.apps.api.services.chile_reports_service import ChileReportsService
from backend.apps.api.services.ciclo_academico_api_service import CicloAcademicoApiService
from backend.apps.api.services.curso_api_service import CursoApiService
from backend.apps.api.services.dashboard_api_service import DashboardApiService
from backend.apps.api.services.matricula_api_service import MatriculaApiService
from backend.apps.api.services.student_api_service import StudentApiService
from backend.apps.api.services.student_portal_api_service import StudentPortalApiService
from backend.apps.api.resources_serializers import (
    ApoderadoListSerializer,
    ApoderadoCreateUpdateSerializer,
    ApoderadoRelacionSerializer,
    ApoderadoSerializer,
    AsignaturaListSerializer,
    AsignaturaSerializer,
    AttendanceSerializer,
    AttendanceCompactSerializer,
    CicloAcademicoListSerializer,
    CicloAcademicoSerializer,
    CursoSerializer,
    CursoListSerializer,
    EvaluationSerializer,
    EvaluationCompactSerializer,
    GradeSerializer,
    GradeCompactSerializer,
    ActividadResolubleSerializer,
    IntentoApproveSerializer,
    IntentoResolubleSerializer,
    IntentoSubmitSerializer,
    MatriculaListSerializer,
    MatriculaSerializer,
    StudentCreateUpdateSerializer,
    StudentProfileUpdateSerializer,
    StudentSerializer,
    StudentListSerializer,
    TeacherClassSerializer,
    TeacherClassCompactSerializer,
)
from backend.apps.cursos.models import Asignatura, Clase, ClaseEstudiante, Curso
from backend.apps.institucion.models import CicloAcademico, Colegio
from backend.apps.matriculas.models import Matricula



class StudentViewSet(CapabilityModelViewSet):
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'STUDENT_VIEW',
        'retrieve': 'STUDENT_VIEW',
        'create': 'STUDENT_EDIT',
        'update': 'STUDENT_EDIT',
        'partial_update': 'STUDENT_EDIT',
        'destroy': 'STUDENT_EDIT',
        'profile': 'STUDENT_EDIT',
        'bulk_deactivate': 'STUDENT_EDIT',
    }

    def get_queryset(self):
        base_qs = User.objects.select_related('role').filter(
            Q(role__nombre__iexact='Estudiante') | Q(role__nombre__iexact='Alumno')
        )
        if not is_global_admin(self.request.user):
            base_qs = base_qs.filter(rbd_colegio=self.request.user.rbd_colegio)

        # Búsqueda por nombre, email, RUT
        base_qs = apply_search_filter(
            base_qs,
            self.request.query_params.get('search'),
            ['nombre', 'apellido_paterno', 'apellido_materno', 'email', 'rut'],
        )

        # Filtro por estado activo
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            base_qs = base_qs.filter(is_active=is_active.lower() == 'true')

        return base_qs.order_by('apellido_paterno', 'nombre')

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return StudentCreateUpdateSerializer
        if self.action == 'list':
            return StudentListSerializer
        return StudentSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        sid = self.request.user.rbd_colegio
        if is_global_admin(self.request.user):
            sid = self.request.data.get('rbd_colegio') or sid
        StudentApiService.create_student(serializer=serializer, school_id=sid)

    @transaction.atomic
    def perform_destroy(self, instance):
        # Soft delete para evitar perder trazabilidad.
        StudentApiService.soft_delete_student(student=instance)

    @action(detail=True, methods=['patch'])
    def profile(self, request, pk=None):
        student = self.get_object()
        payload = StudentApiService.update_student_profile(
            student=student,
            payload=request.data,
            serializer_class=StudentProfileUpdateSerializer,
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='bulk-deactivate')
    @transaction.atomic
    def bulk_deactivate(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            raise ValidationError({'ids': 'Debe enviar una lista no vacia de IDs.'})
        payload = StudentApiService.bulk_deactivate_students(queryset=self.get_queryset(), ids=ids)
        return Response(payload, status=status.HTTP_200_OK)


class CursoViewSet(CapabilityModelViewSet):
    queryset = Curso.objects.select_related('colegio', 'nivel', 'ciclo_academico')
    serializer_class = CursoSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'COURSE_VIEW',
        'retrieve': 'COURSE_VIEW',
        'create': 'COURSE_CREATE',
        'update': 'COURSE_EDIT',
        'partial_update': 'COURSE_EDIT',
        'destroy': 'COURSE_DELETE',
    }

    def get_queryset(self):
        base_qs = super().get_queryset()
        if not is_global_admin(self.request.user):
            base_qs = base_qs.filter(colegio_id=self.request.user.rbd_colegio)

        # Búsqueda por nombre
        base_qs = apply_search_filter(
            base_qs,
            self.request.query_params.get('search'),
            ['nombre'],
        )

        return base_qs.order_by('nombre')

    def get_serializer_class(self):
        if self.action == 'list':
            return CursoListSerializer
        return CursoSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        CursoApiService.create_course(
            serializer=serializer,
            actor=self.request.user,
            requested_school_id=self.request.data.get('colegio_id'),
        )

    @transaction.atomic
    def perform_update(self, serializer):
        CursoApiService.update_course(serializer=serializer, actor=self.request.user)


class AsignaturaViewSet(CapabilityModelViewSet):
    queryset = Asignatura.objects.select_related('colegio')
    serializer_class = AsignaturaSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'COURSE_VIEW',
        'retrieve': 'COURSE_VIEW',
        'create': 'COURSE_CREATE',
        'update': 'COURSE_EDIT',
        'partial_update': 'COURSE_EDIT',
        'destroy': 'COURSE_DELETE',
    }

    def get_queryset(self):
        base_qs = super().get_queryset()
        if not is_global_admin(self.request.user):
            base_qs = base_qs.filter(colegio_id=self.request.user.rbd_colegio)

        base_qs = apply_search_filter(
            base_qs,
            self.request.query_params.get('search'),
            ['nombre'],
        )

        return base_qs.order_by('nombre')

    def get_serializer_class(self):
        if self.action == 'list':
            return AsignaturaListSerializer
        return AsignaturaSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        AsignaturaApiService.create_for_school(serializer=serializer, school_id=self.request.user.rbd_colegio)


class CicloAcademicoViewSet(CapabilityModelViewSet):
    queryset = CicloAcademico.objects.select_related('colegio', 'creado_por', 'modificado_por')
    serializer_class = CicloAcademicoSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'SYSTEM_CONFIGURE',
        'retrieve': 'SYSTEM_CONFIGURE',
        'create': 'SYSTEM_CONFIGURE',
        'update': 'SYSTEM_CONFIGURE',
        'partial_update': 'SYSTEM_CONFIGURE',
        'destroy': 'SYSTEM_CONFIGURE',
        'activate': 'SYSTEM_CONFIGURE',
    }

    def get_queryset(self):
        base_qs = super().get_queryset()
        if not is_global_admin(self.request.user):
            base_qs = base_qs.filter(colegio_id=self.request.user.rbd_colegio)
        return base_qs.order_by('-fecha_inicio')

    def get_serializer_class(self):
        if self.action == 'list':
            return CicloAcademicoListSerializer
        return CicloAcademicoSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        CicloAcademicoApiService.create_for_school(
            serializer=serializer,
            actor=self.request.user,
            school_id=self.request.user.rbd_colegio,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        CicloAcademicoApiService.update_with_audit(serializer=serializer, actor=self.request.user)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def activate(self, request, pk=None):
        ciclo = self.get_object()
        changed = CicloAcademicoApiService.activate_cycle(ciclo=ciclo, actor=request.user)
        if not changed:
            return Response({'detail': 'El ciclo ya esta activo.'}, status=status.HTTP_200_OK)
        return Response({'detail': 'Ciclo academico activado.'}, status=status.HTTP_200_OK)


class MatriculaViewSet(CapabilityModelViewSet):
    queryset = Matricula.objects.select_related('estudiante', 'colegio', 'curso', 'ciclo_academico')
    serializer_class = MatriculaSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'ENROLLMENT_VIEW',
        'retrieve': 'ENROLLMENT_VIEW',
        'create': 'ENROLLMENT_CREATE',
        'update': 'ENROLLMENT_EDIT',
        'partial_update': 'ENROLLMENT_EDIT',
        'destroy': 'ENROLLMENT_DELETE',
        'bulk_close': 'ENROLLMENT_EDIT',
    }

    def get_queryset(self):
        base_qs = super().get_queryset()
        if not is_global_admin(self.request.user):
            base_qs = base_qs.filter(colegio_id=self.request.user.rbd_colegio)

        estudiante_id = self.request.query_params.get('estudiante_id')
        if estudiante_id:
            base_qs = base_qs.filter(estudiante_id=estudiante_id)

        ciclo_id = self.request.query_params.get('ciclo_id')
        if ciclo_id:
            base_qs = base_qs.filter(ciclo_academico_id=ciclo_id)

        estado = self.request.query_params.get('estado')
        if estado:
            base_qs = base_qs.filter(estado=estado)

        return base_qs.order_by('-fecha_matricula')

    def get_serializer_class(self):
        if self.action == 'list':
            return MatriculaListSerializer
        return MatriculaSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        MatriculaApiService.create_for_school(serializer=serializer, school_id=self.request.user.rbd_colegio)

    @action(detail=False, methods=['post'], url_path='bulk-close')
    @transaction.atomic
    def bulk_close(self, request):
        ids = request.data.get('ids') or []
        updated = MatriculaApiService.bulk_close_active(queryset=self.get_queryset(), ids=ids)
        return Response({'updated': updated}, status=status.HTTP_200_OK)


class ApoderadoViewSet(CapabilityModelViewSet):
    queryset = Apoderado.objects.select_related('user')
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'USER_VIEW',
        'retrieve': 'USER_VIEW',
        'create': 'USER_CREATE',
        'update': 'USER_EDIT',
        'partial_update': 'USER_EDIT',
        'destroy': 'USER_DELETE',
        'link_student': 'USER_EDIT',
        'relationships': 'USER_VIEW',
    }

    def get_queryset(self):
        base_qs = super().get_queryset()
        if not is_global_admin(self.request.user):
            base_qs = base_qs.filter(user__rbd_colegio=self.request.user.rbd_colegio)

        # Búsqueda por nombre/email del usuario vinculado
        base_qs = apply_search_filter(
            base_qs,
            self.request.query_params.get('search'),
            ['user__nombre', 'user__apellido_paterno', 'user__email', 'user__rut'],
        )

        return base_qs.order_by('-activo', 'user__apellido_paterno', 'user__nombre')

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return ApoderadoCreateUpdateSerializer
        if self.action == 'list':
            return ApoderadoListSerializer
        return ApoderadoSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created, message = ApoderadoApiService.create_apoderado(
            actor=request.user,
            data=serializer.validated_data,
            school_id=request.user.rbd_colegio,
        )
        payload = ApoderadoSerializer(created).data if created else {'detail': message}
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(payload, status=status_code)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        ApoderadoApiService.update_apoderado(
            actor=request.user,
            apoderado_id=instance.user_id,
            data=serializer.validated_data,
            school_id=request.user.rbd_colegio,
        )

        instance.refresh_from_db()
        return Response(ApoderadoSerializer(instance).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def perform_destroy(self, instance):
        ApoderadoApiService.deactivate_apoderado(
            actor=self.request.user,
            apoderado_id=instance.user_id,
            school_id=self.request.user.rbd_colegio,
        )

    @action(detail=True, methods=['post'], url_path='link-student')
    @transaction.atomic
    def link_student(self, request, pk=None):
        guardian = self.get_object()
        relation = ApoderadoApiService.link_student(
            guardian=guardian,
            actor=request.user,
            student_id=request.data.get('student_id'),
            parentesco=request.data.get('parentesco', 'padre'),
            tipo_apoderado=request.data.get('tipo_apoderado', 'principal'),
            is_global_admin=is_global_admin(request.user),
        )
        return Response(ApoderadoRelacionSerializer(relation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def relationships(self, request, pk=None):
        guardian = self.get_object()
        qs = ApoderadoApiService.relationships(guardian=guardian)
        return Response(ApoderadoRelacionSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class TeacherClassViewSet(CapabilityModelViewSet):
    queryset = Clase.objects.select_related('curso', 'asignatura', 'profesor')
    serializer_class = TeacherClassSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'CLASS_VIEW',
        'retrieve': 'CLASS_VIEW',
    }
    http_method_names = ['get', 'head', 'options']

    def get_serializer_class(self):
        compact_mode = self.request.query_params.get('compact') == '1'
        if self.action == 'list' and compact_mode:
            return TeacherClassCompactSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        base_qs = super().get_queryset()
        if not is_global_admin(user):
            sid = school_id(user)
            if not sid:
                return base_qs.none()
            base_qs = base_qs.filter(colegio_id=sid)
            if is_teacher(user):
                base_qs = base_qs.filter(profesor_id=user.id)
        return base_qs.order_by('curso__nombre', 'asignatura__nombre')


class TeacherAttendanceViewSet(CapabilityModelViewSet):
    queryset = Asistencia.objects.select_related('clase__curso', 'clase__asignatura', 'estudiante')
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'CLASS_VIEW_ATTENDANCE',
        'retrieve': 'CLASS_VIEW_ATTENDANCE',
        'create': 'CLASS_TAKE_ATTENDANCE',
        'update': 'CLASS_TAKE_ATTENDANCE',
        'partial_update': 'CLASS_TAKE_ATTENDANCE',
        'destroy': 'CLASS_TAKE_ATTENDANCE',
        'bulk_update_state': 'CLASS_TAKE_ATTENDANCE',
    }

    def get_serializer_class(self):
        compact_mode = self.request.query_params.get('compact') == '1'
        if self.action == 'list' and compact_mode:
            return AttendanceCompactSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        base_qs = super().get_queryset()
        if not is_global_admin(user):
            base_qs = base_qs.filter(colegio_id=school_id(user))
            if is_teacher(user):
                base_qs = base_qs.filter(clase__profesor_id=user.id)

        clase_id = self.request.query_params.get('clase_id')
        if clase_id:
            base_qs = base_qs.filter(clase_id=clase_id)

        fecha = self.request.query_params.get('fecha')
        if fecha:
            base_qs = base_qs.filter(fecha=fecha)

        return base_qs.order_by('-fecha', 'id_asistencia')

    @transaction.atomic
    def perform_create(self, serializer):
        clase = serializer.validated_data['clase']
        estudiante = serializer.validated_data['estudiante']
        ensure_same_school(self.request.user, clase.colegio_id)
        ensure_teacher_owns_class(self.request.user, clase)

        if not ClaseEstudiante.objects.filter(clase=clase, estudiante=estudiante, activo=True).exists():
            raise ValidationError({'estudiante': 'El estudiante no esta matriculado en esta clase.'})

        serializer.save(colegio_id=clase.colegio_id)

    @transaction.atomic
    def perform_update(self, serializer):
        clase = serializer.validated_data.get('clase', serializer.instance.clase)
        ensure_same_school(self.request.user, clase.colegio_id)
        ensure_teacher_owns_class(self.request.user, clase)
        serializer.save()

    @action(detail=False, methods=['post'], url_path='bulk-update-state')
    @transaction.atomic
    def bulk_update_state(self, request):
        payload = AcademicBatchApiService.bulk_update_attendance_state(
            actor=request.user,
            queryset=self.get_queryset().select_related('clase'),
            ids=request.data.get('ids') or [],
            target_state=request.data.get('estado'),
            serializer_class=self.get_serializer_class(),
        )
        return Response(payload, status=status.HTTP_200_OK)


class TeacherEvaluationViewSet(CapabilityModelViewSet):
    queryset = Evaluacion.objects.select_related('clase__curso', 'clase__asignatura')
    serializer_class = EvaluationSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'GRADE_VIEW',
        'retrieve': 'GRADE_VIEW',
        'create': 'GRADE_CREATE',
        'update': 'GRADE_EDIT',
        'partial_update': 'GRADE_EDIT',
        'destroy': 'GRADE_DELETE',
        'bulk_toggle_active': 'GRADE_EDIT',
    }

    def get_serializer_class(self):
        compact_mode = self.request.query_params.get('compact') == '1'
        if self.action == 'list' and compact_mode:
            return EvaluationCompactSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        base_qs = super().get_queryset()
        if not is_global_admin(user):
            base_qs = base_qs.filter(colegio_id=school_id(user))
            if is_teacher(user):
                base_qs = base_qs.filter(clase__profesor_id=user.id)

        clase_id = self.request.query_params.get('clase_id')
        if clase_id:
            base_qs = base_qs.filter(clase_id=clase_id)

        return base_qs.order_by('-fecha_evaluacion', '-id_evaluacion')

    @transaction.atomic
    def perform_create(self, serializer):
        clase = serializer.validated_data['clase']
        ensure_same_school(self.request.user, clase.colegio_id)
        ensure_teacher_owns_class(self.request.user, clase)
        serializer.save(colegio_id=clase.colegio_id)

    @transaction.atomic
    def perform_update(self, serializer):
        clase = serializer.validated_data.get('clase', serializer.instance.clase)
        ensure_same_school(self.request.user, clase.colegio_id)
        ensure_teacher_owns_class(self.request.user, clase)
        serializer.save()

    @action(detail=False, methods=['post'], url_path='bulk-toggle-active')
    @transaction.atomic
    def bulk_toggle_active(self, request):
        payload = AcademicBatchApiService.bulk_toggle_evaluation_active(
            queryset=self.get_queryset(),
            ids=request.data.get('ids') or [],
            target_active=request.data.get('activa', None),
        )
        return Response(payload, status=status.HTTP_200_OK)


class TeacherGradeViewSet(CapabilityModelViewSet):
    queryset = Calificacion.objects.select_related('evaluacion__clase', 'estudiante')
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'GRADE_VIEW',
        'retrieve': 'GRADE_VIEW',
        'create': 'GRADE_CREATE',
        'update': 'GRADE_EDIT',
        'partial_update': 'GRADE_EDIT',
        'destroy': 'GRADE_DELETE',
        'bulk_delete': 'GRADE_DELETE',
    }

    def get_serializer_class(self):
        compact_mode = self.request.query_params.get('compact') == '1'
        if self.action == 'list' and compact_mode:
            return GradeCompactSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        base_qs = super().get_queryset()
        if not is_global_admin(user):
            base_qs = base_qs.filter(colegio_id=school_id(user))
            if is_teacher(user):
                base_qs = base_qs.filter(evaluacion__clase__profesor_id=user.id)

        evaluacion_id = self.request.query_params.get('evaluacion_id')
        if evaluacion_id:
            base_qs = base_qs.filter(evaluacion_id=evaluacion_id)

        clase_id = self.request.query_params.get('clase_id')
        if clase_id:
            base_qs = base_qs.filter(evaluacion__clase_id=clase_id)

        estudiante_id = self.request.query_params.get('estudiante_id')
        if estudiante_id:
            base_qs = base_qs.filter(estudiante_id=estudiante_id)

        return base_qs.order_by('-fecha_creacion', '-id_calificacion')

    @transaction.atomic
    def perform_create(self, serializer):
        evaluacion = serializer.validated_data['evaluacion']
        ensure_same_school(self.request.user, evaluacion.colegio_id)
        ensure_teacher_owns_class(self.request.user, evaluacion.clase)
        serializer.save(
            colegio_id=evaluacion.colegio_id,
            registrado_por=self.request.user,
            actualizado_por=self.request.user,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        evaluacion = serializer.validated_data.get('evaluacion', serializer.instance.evaluacion)
        ensure_same_school(self.request.user, evaluacion.colegio_id)
        ensure_teacher_owns_class(self.request.user, evaluacion.clase)
        serializer.save(actualizado_por=self.request.user)

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    @transaction.atomic
    def bulk_delete(self, request):
        payload = AcademicBatchApiService.bulk_delete_grades(
            queryset=self.get_queryset(),
            ids=request.data.get('ids') or [],
        )
        return Response(payload, status=status.HTTP_200_OK)


class ActividadResolubleViewSet(viewsets.ModelViewSet):
    queryset = ActividadResoluble.objects.select_related('colegio', 'content_type').prefetch_related('preguntas__opciones', 'intentos__respuestas')
    serializer_class = ActividadResolubleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = super().get_queryset()
        if not is_global_admin(user):
            base_qs = base_qs.filter(colegio_id=school_id(user))
            if is_teacher(user):
                base_qs = base_qs.filter(
                    Q(tarea_resoluble__clase__profesor_id=user.id)
                    | Q(evaluacion_resoluble__clase__profesor_id=user.id)
                )
            else:
                base_qs = base_qs.filter(estado__in=['PUBLICADA', 'APROBADA']).filter(
                    Q(tarea_resoluble__clase__estudiantes__estudiante_id=user.id)
                    | Q(evaluacion_resoluble__clase__estudiantes__estudiante_id=user.id)
                )
        return base_qs.distinct().order_by('-fecha_creacion', '-id_actividad_resoluble')

    def create(self, request, *args, **kwargs):
        if not is_global_admin(request.user) and not is_teacher(request.user):
            raise PermissionDenied('No tiene permisos para crear actividades resolubles.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actividad = serializer.save()
        output = self.get_serializer(actividad)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not is_global_admin(request.user) and not is_teacher(request.user):
            raise PermissionDenied('No tiene permisos para modificar actividades resolubles.')
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        actividad = serializer.save()
        output = self.get_serializer(actividad)
        return Response(output.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        if not is_global_admin(request.user) and not is_teacher(request.user):
            raise PermissionDenied('No tiene permisos para eliminar actividades resolubles.')
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='submit')
    @transaction.atomic
    def submit(self, request, pk=None):
        actividad = self.get_object()
        serializer = IntentoSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['actividad_resoluble_id'] != actividad.id_actividad_resoluble:
            raise ValidationError({'actividad_resoluble_id': 'No coincide con la actividad solicitada.'})

        intento = ResolubleService.submit_attempt(
            actividad=actividad,
            estudiante=request.user,
            responses=serializer.validated_data['respuestas'],
        )
        return Response(IntentoResolubleSerializer(intento, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='approve-attempt')
    @transaction.atomic
    def approve_attempt(self, request, pk=None):
        actividad = self.get_object()
        serializer = IntentoApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        intento = actividad.intentos.select_related('estudiante').get(id_intento=serializer.validated_data['intento_id'])
        if not is_global_admin(request.user) and not is_teacher(request.user):
            raise PermissionDenied('No tiene permisos para aprobar este intento.')

        if not is_global_admin(request.user):
            if actividad.actividad.__class__.__name__ == 'Tarea' and actividad.actividad.clase.profesor_id != request.user.id:
                raise PermissionDenied('No puede aprobar intentos de otra clase.')
            if actividad.actividad.__class__.__name__ == 'Evaluacion' and actividad.actividad.clase.profesor_id != request.user.id:
                raise PermissionDenied('No puede aprobar intentos de otra clase.')

        calificacion = ResolubleService.approve_attempt(
            intento=intento,
            profesor=request.user,
            retroalimentacion=serializer.validated_data.get('retroalimentacion', ''),
        )
        return Response(
            GradeSerializer(calificacion, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    try:
        payload = DashboardApiService.build_dashboard_payload(
            user=request.user,
            query_params=request.query_params,
        )
    except PermissionDenied as exc:
        detail = getattr(exc, 'detail', 'No autorizado')
        return Response({'detail': str(detail)}, status=status.HTTP_403_FORBIDDEN)

    return Response(payload, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_schools(request):
    if not is_global_admin(request.user):
        return Response({'detail': 'No tiene permisos para listar colegios.'}, status=status.HTTP_403_FORBIDDEN)

    schools = (
        Colegio.objects.all_schools()
        .select_related('comuna')
        .order_by('nombre')
        .values('rbd', 'nombre', 'slug', 'comuna__nombre')
    )
    return Response(
        {
            'results': [
                {
                    'rbd': row['rbd'],
                    'nombre': row['nombre'],
                    'slug': row['slug'],
                    'comuna': row['comuna__nombre'],
                }
                for row in schools
            ]
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_executive(request):
    """Vista ejecutiva del dashboard con datos para gráficos y alertas."""
    from backend.apps.api.services.dashboard_analytics_service import DashboardAnalyticsService

    scope = request.query_params.get('scope', 'auto')
    user_school_id = getattr(request.user, 'rbd_colegio', None)
    requested_school = request.query_params.get('colegio_id')

    try:
        if scope == 'global':
            effective_school_id = None
        else:
            effective_school_id = int(requested_school) if requested_school else user_school_id
    except (TypeError, ValueError):
        effective_school_id = user_school_id

    try:
        payload = DashboardAnalyticsService.get_executive_payload(
            user=request.user,
            school_id=effective_school_id,
            scope=scope,
        )
    except PermissionDenied as exc:
        detail = getattr(exc, 'detail', 'No autorizado')
        return Response({'detail': str(detail)}, status=status.HTTP_403_FORBIDDEN)

    return Response(payload, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ministerial_monthly_report(request):
    user = request.user
    if not is_global_admin(user) and not has_cap(user, 'REPORT_VIEW_BASIC'):
        return Response({'detail': 'No tiene permisos para este recurso.'}, status=status.HTTP_403_FORBIDDEN)

    year, month = ChileReportsService.resolve_month(request.query_params.get('month'))
    school_id = ChileReportsService.resolve_school_id(
        user=user,
        requested_school_id=request.query_params.get('colegio_id'),
        is_global_admin=is_global_admin(user),
    )
    payload = ChileReportsService.build_ministerial_monthly_payload(school_id=school_id, year=year, month=month)

    export_format = (request.query_params.get('export') or 'json').strip().lower()
    if export_format == 'json':
        return Response(payload, status=status.HTTP_200_OK)

    export = ChileReportsService.export_payload(payload, export_format)
    response = HttpResponse(export.content, content_type=export.content_type)
    response['Content-Disposition'] = f'attachment; filename="{export.filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_my_profile(request):
    forbid_without_cap(request.user, 'DASHBOARD_VIEW_SELF')
    payload = StudentPortalApiService.serialize_profile(user=request.user)
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_my_classes(request):
    forbid_without_cap(request.user, 'CLASS_VIEW')
    payload = StudentPortalApiService.serialize_my_classes(user=request.user)
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_my_grades(request):
    forbid_without_cap(request.user, 'GRADE_VIEW')
    payload = StudentPortalApiService.serialize_my_grades(
        user=request.user,
        clase_id=request.query_params.get('clase_id'),
        evaluacion_id=request.query_params.get('evaluacion_id'),
    )
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_my_attendance(request):
    forbid_without_cap(request.user, 'CLASS_VIEW_ATTENDANCE')
    payload = StudentPortalApiService.serialize_my_attendance(
        user=request.user,
        clase_id=request.query_params.get('clase_id'),
        fecha_desde=request.query_params.get('fecha_desde'),
        fecha_hasta=request.query_params.get('fecha_hasta'),
    )
    return Response(payload, status=status.HTTP_200_OK)

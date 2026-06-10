"""
Views para funcionalidades Semana 3-4.

D. TeacherAdminViewSet — CRUD de profesores (admin)
E. FirmaDigitalViewSet — Firmas de apoderados
F. MaterialClaseViewSet — Materiales de clase
G. teacher_my_schedule — Horario semanal del profesor
H. Historial multi-ciclo (filtro ?ciclo=<id> ya soportado en endpoints existentes)
"""
import hashlib
import logging

from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.accounts.models import (
    Apoderado,
    FirmaDigitalApoderado,
    PerfilProfesor,
    RelacionApoderadoEstudiante,
    Role,
    User,
)
from backend.apps.academico.models import MaterialClase
from backend.apps.api.base import CapabilityModelViewSet
from backend.apps.api.permissions import HasCapability
from backend.apps.api.gestion_escolar_serializers import (
    BloqueHorarioSerializer,
    FirmaDigitalCreateSerializer,
    FirmaDigitalListSerializer,
    FirmaDigitalSerializer,
    MaterialClaseListSerializer,
    MaterialClaseSerializer,
    TeacherAdminCreateUpdateSerializer,
    TeacherAdminListSerializer,
    TeacherAdminSerializer,
    TeacherAssignClassSerializer,
)
from backend.apps.cursos.models import BloqueHorario, Clase, ClaseEstudiante
from backend.common.services.policy_service import PolicyService

logger = logging.getLogger('api')


def _is_global_admin(user):
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN')


def _has_capability(user, capability):
    return PolicyService.has_capability(
        user, capability,
        school_id=getattr(user, 'rbd_colegio', None),
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def demo_panel(request):
    """Resumen demo para panel de bienvenida del colegio (tareas, materiales, horario)."""
    school_id = getattr(request.user, 'rbd_colegio', None)
    if school_id is None:
        return Response({'detail': 'No asociado a colegio.'}, status=status.HTTP_400_BAD_REQUEST)

    # counts
    from backend.apps.academico.models import Tarea, MaterialClase
    tareas_qs = Tarea.objects.filter(colegio__rbd=school_id).select_related('clase')
    materiales_qs = MaterialClase.objects.filter(colegio__rbd=school_id).select_related('clase')
    bloques_qs = BloqueHorario.objects.filter(colegio__rbd=school_id).select_related('clase__asignatura', 'clase__curso')

    counts = {
        'tareas': tareas_qs.count(),
        'materiales': materiales_qs.count(),
        'bloques': bloques_qs.count(),
    }

    tareas = [
        {
            'id_tarea': t.id_tarea,
            'titulo': t.titulo,
            'clase_nombre': str(t.clase),
            'fecha_entrega': t.fecha_entrega.isoformat() if t.fecha_entrega else None,
        }
        for t in tareas_qs.order_by('-fecha_entrega')[:5]
    ]

    materiales = [
        {
            'id_material': m.id_material,
            'titulo': m.titulo,
            'clase_nombre': str(m.clase),
            'archivo': m.archivo.name if m.archivo else None,
        }
        for m in materiales_qs.order_by('-fecha_creacion')[:5]
    ]

    # horario agrupado por dia
    horario = {}
    for b in bloques_qs.order_by('dia_semana', 'bloque_numero'):
        dia = b.get_dia_semana_display()
        horario.setdefault(dia, []).append(BloqueHorarioSerializer(b).data)

    return Response({'counts': counts, 'tareas': tareas, 'materiales': materiales, 'horario': horario})


# ─────────────────────────────────────────────
# D. Gestión Completa de Profesores
# ─────────────────────────────────────────────

class TeacherAdminViewSet(CapabilityModelViewSet):
    """CRUD administrativo de profesores. Solo para admin escolar / admin general."""
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'USER_VIEW',
        'retrieve': 'USER_VIEW',
        'create': 'USER_CREATE',
        'update': 'USER_EDIT',
        'partial_update': 'USER_EDIT',
        'destroy': 'USER_EDIT',
        'assign_class': 'CLASS_EDIT',
        'unassign_class': 'CLASS_EDIT',
    }

    def get_queryset(self):
        base_qs = User.objects.select_related('role', 'perfil_profesor').filter(
            role__nombre__iexact='Profesor'
        )
        if _is_global_admin(self.request.user):
            return base_qs.order_by('apellido_paterno', 'nombre')
        return base_qs.filter(
            rbd_colegio=self.request.user.rbd_colegio
        ).order_by('apellido_paterno', 'nombre')

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return TeacherAdminCreateUpdateSerializer
        if self.action == 'list':
            return TeacherAdminListSerializer
        return TeacherAdminSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = TeacherAdminCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        school_id = request.user.rbd_colegio

        # Verificar email duplicado en el colegio
        if User.objects.filter(email=data['email'], rbd_colegio=school_id).exists():
            raise ValidationError({'email': 'Ya existe un usuario con este email en el colegio.'})

        # Crear usuario con rol Profesor
        role = Role.objects.get_or_create(nombre='Profesor')[0]
        teacher = User.objects.create_user(
            email=data['email'],
            nombre=data['nombre'],
            apellido_paterno=data['apellido_paterno'],
            apellido_materno=data.get('apellido_materno', ''),
            rut=data.get('rut') or None,
            role=role,
            rbd_colegio=school_id,
            is_active=data.get('is_active', True),
        )

        # Crear perfil profesor
        perfil_fields = {
            k: v for k, v in data.items()
            if k in {
                'especialidad', 'titulo_profesional', 'universidad',
                'anio_titulacion', 'horas_semanales_contrato',
                'horas_no_lectivas', 'telefono', 'direccion',
            } and v is not None
        }
        PerfilProfesor.objects.create(user=teacher, **perfil_fields)

        logger.info(f"Profesor creado — id={teacher.id} email={teacher.email} by={request.user.email}")
        return Response(
            TeacherAdminSerializer(teacher).data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        teacher = self.get_object()
        serializer = TeacherAdminCreateUpdateSerializer(data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_fields = ['email', 'nombre', 'apellido_paterno', 'apellido_materno', 'rut', 'is_active']
        updated_user = []
        for field in user_fields:
            if field in data:
                setattr(teacher, field, data[field])
                updated_user.append(field)
        if updated_user:
            teacher.save(update_fields=updated_user)

        perfil_fields = {
            'especialidad', 'titulo_profesional', 'universidad',
            'anio_titulacion', 'horas_semanales_contrato',
            'horas_no_lectivas', 'telefono', 'direccion',
        }
        perfil, _ = PerfilProfesor.objects.get_or_create(user=teacher)
        updated_perfil = []
        for field in perfil_fields:
            if field in data:
                setattr(perfil, field, data[field])
                updated_perfil.append(field)
        if updated_perfil:
            perfil.save(update_fields=updated_perfil + ['fecha_actualizacion'])

        logger.info(f"Profesor actualizado — id={teacher.id} by={request.user.email}")
        teacher.refresh_from_db()
        return Response(TeacherAdminSerializer(teacher).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        logger.info(f"Profesor desactivado — id={instance.id}")

    @action(detail=True, methods=['post'], url_path='assign-class')
    @transaction.atomic
    def assign_class(self, request, pk=None):
        """Asigna este profesor a una clase existente."""
        teacher = self.get_object()
        ser = TeacherAssignClassSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        clase = Clase.objects.filter(id=ser.validated_data['clase_id']).first()
        if not clase:
            raise ValidationError({'clase_id': 'Clase no encontrada.'})

        if not _is_global_admin(request.user):
            if clase.colegio_id != request.user.rbd_colegio:
                raise PermissionDenied('No puede operar clases de otro colegio.')

        clase.profesor = teacher
        clase.save(update_fields=['profesor_id'])
        logger.info(f"Clase {clase.id} asignada a profesor {teacher.id}")
        return Response({'detail': f'Clase asignada a {teacher.get_full_name()}.'})

    @action(detail=True, methods=['post'], url_path='unassign-class')
    @transaction.atomic
    def unassign_class(self, request, pk=None):
        """Des-asigna este profesor de una clase."""
        teacher = self.get_object()
        ser = TeacherAssignClassSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        clase = Clase.objects.filter(
            id=ser.validated_data['clase_id'], profesor=teacher
        ).first()
        if not clase:
            raise ValidationError({'clase_id': 'El profesor no tiene asignada esa clase.'})

        clase.profesor = None
        clase.save(update_fields=['profesor_id'])
        logger.info(f"Clase {clase.id} des-asignada de profesor {teacher.id}")
        return Response({'detail': 'Clase des-asignada.'})


# ─────────────────────────────────────────────
# E. Firma Digital Apoderado
# ─────────────────────────────────────────────

class FirmaDigitalViewSet(CapabilityModelViewSet):
    """Firmas digitales de apoderados."""
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'DASHBOARD_VIEW_SELF',
        'retrieve': 'DASHBOARD_VIEW_SELF',
        'create': 'DASHBOARD_VIEW_SELF',
    }
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        base_qs = FirmaDigitalApoderado.objects.select_related(
            'apoderado__user', 'estudiante'
        )
        if _is_global_admin(user):
            return base_qs.order_by('-timestamp_firma')

        # Apoderado ve solo sus propias firmas
        try:
            apoderado = Apoderado.objects.get(user=user)
            return base_qs.filter(apoderado=apoderado).order_by('-timestamp_firma')
        except Apoderado.DoesNotExist:
            # Admin puede ver firmas del colegio
            if _has_capability(user, 'USER_VIEW'):
                return base_qs.filter(
                    apoderado__user__rbd_colegio=user.rbd_colegio
                ).order_by('-timestamp_firma')
            return base_qs.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return FirmaDigitalListSerializer
        if self.action == 'create':
            return FirmaDigitalCreateSerializer
        return FirmaDigitalSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = FirmaDigitalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        try:
            apoderado = Apoderado.objects.get(user=user)
        except Apoderado.DoesNotExist:
            raise PermissionDenied('Solo apoderados pueden firmar documentos.')

        # Validar que el estudiante pertenece al apoderado
        estudiante = None
        if data.get('estudiante_id'):
            rel = RelacionApoderadoEstudiante.objects.filter(
                apoderado=apoderado, estudiante_id=data['estudiante_id'], activa=True
            ).first()
            if not rel:
                raise ValidationError({'estudiante_id': 'No tiene relación activa con este estudiante.'})
            estudiante = rel.estudiante

        # Generar hash de integridad
        content_to_hash = f"{data['titulo_documento']}|{data['contenido_documento']}|{user.id}|{apoderado.id}"
        hash_doc = hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()

        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
            or request.META.get('REMOTE_ADDR', '')
        ua = request.META.get('HTTP_USER_AGENT', '')

        firma = FirmaDigitalApoderado.objects.create(
            apoderado=apoderado,
            estudiante=estudiante,
            tipo_documento=data['tipo_documento'],
            titulo_documento=data['titulo_documento'],
            contenido_documento=data['contenido_documento'],
            documento_id=data.get('documento_id'),
            documento_tipo_modelo=data.get('documento_tipo_modelo', ''),
            ip_address=ip or '0.0.0.0',
            user_agent=ua,
            usuario_firmante=user,
            hash_documento=hash_doc,
            observaciones=data.get('observaciones', ''),
        )

        logger.info(f"Firma digital creada — id={firma.id} apoderado={apoderado.id} tipo={data['tipo_documento']}")
        return Response(FirmaDigitalSerializer(firma).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# F. Materiales de Clase
# ─────────────────────────────────────────────

class MaterialClaseViewSet(CapabilityModelViewSet):
    """Materiales de clase. Profesores: CRUD. Alumnos: solo lectura pública."""
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        'list': 'CLASS_VIEW',
        'retrieve': 'CLASS_VIEW',
        'create': 'GRADE_CREATE',
        'update': 'GRADE_EDIT',
        'partial_update': 'GRADE_EDIT',
        'destroy': 'GRADE_DELETE',
        'toggle_visibility': 'GRADE_EDIT',
    }

    def get_queryset(self):
        user = self.request.user
        base_qs = MaterialClase.objects.select_related(
            'clase__curso', 'clase__asignatura', 'subido_por'
        ).filter(activo=True)

        if _is_global_admin(user):
            qs = base_qs
        else:
            school_id = getattr(user, 'rbd_colegio', None)
            base_qs = base_qs.filter(colegio_id=school_id)

            role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()
            if role_name in {'estudiante', 'alumno'}:
                # Solo materiales públicos de sus clases
                mis_clases = ClaseEstudiante.objects.filter(
                    estudiante_id=user.id, activo=True
                ).values_list('clase_id', flat=True)
                base_qs = base_qs.filter(clase_id__in=mis_clases, es_publico=True)
            elif role_name == 'profesor':
                base_qs = base_qs.filter(clase__profesor_id=user.id)

            qs = base_qs

        clase_id = self.request.query_params.get('clase_id')
        if clase_id:
            qs = qs.filter(clase_id=clase_id)

        return qs.order_by('-fecha_creacion')

    def get_serializer_class(self):
        if self.action == 'list':
            return MaterialClaseListSerializer
        return MaterialClaseSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        clase = Clase.objects.filter(id=self.request.data.get('clase_id')).first()
        if not clase:
            raise ValidationError({'clase_id': 'Clase no encontrada.'})

        if not _is_global_admin(self.request.user):
            if clase.colegio_id != self.request.user.rbd_colegio:
                raise PermissionDenied('No puede operar clases de otro colegio.')
            role_name = getattr(getattr(self.request.user, 'role', None), 'nombre', '').strip().lower()
            if role_name == 'profesor' and clase.profesor_id != self.request.user.id:
                raise PermissionDenied('Solo puede subir materiales a sus propias clases.')

        archivo = self.request.FILES.get('archivo')
        serializer.save(
            colegio_id=clase.colegio_id,
            clase=clase,
            subido_por=self.request.user,
            tamanio_bytes=archivo.size if archivo else 0,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.activo = False
        instance.save(update_fields=['activo'])

    @action(detail=True, methods=['post'], url_path='toggle-visibility')
    @transaction.atomic
    def toggle_visibility(self, request, pk=None):
        material = self.get_object()
        material.es_publico = not material.es_publico
        material.save(update_fields=['es_publico', 'fecha_actualizacion'])
        return Response({
            'es_publico': material.es_publico,
            'detail': f'Material ahora {"público" if material.es_publico else "privado"}.',
        })


# ─────────────────────────────────────────────
# G. Horario Semanal del Profesor
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_my_schedule(request):
    """
    GET /api/profesor/mi-horario/
    Retorna el horario semanal del profesor autenticado agrupado por día.
    También soporta ?estudiante_id=<id> para que un alumno vea su horario.
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()

    if role_name == 'profesor':
        class_ids = Clase.objects.filter(
            profesor_id=user.id, activo=True
        ).values_list('id', flat=True)
    elif role_name in {'estudiante', 'alumno'}:
        class_ids = ClaseEstudiante.objects.filter(
            estudiante_id=user.id, activo=True
        ).values_list('clase_id', flat=True)
    elif _is_global_admin(user):
        teacher_id = request.query_params.get('profesor_id')
        if not teacher_id:
            raise ValidationError({'profesor_id': 'Requerido para admin global.'})
        class_ids = Clase.objects.filter(
            profesor_id=teacher_id, activo=True
        ).values_list('id', flat=True)
    else:
        raise PermissionDenied('Rol no soportado para este endpoint.')

    bloques = BloqueHorario.objects.filter(
        clase_id__in=class_ids, activo=True,
    ).select_related(
        'clase__asignatura', 'clase__curso', 'clase__profesor'
    ).order_by('dia_semana', 'bloque_numero')

    # Agrupar por día
    DIAS = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes'}
    horario = {dia: [] for dia in DIAS.values()}

    for bloque in bloques:
        dia_name = DIAS.get(bloque.dia_semana, f'Día {bloque.dia_semana}')
        horario[dia_name].append(BloqueHorarioSerializer(bloque).data)

    return Response({
        'horario': horario,
        'total_bloques': bloques.count(),
    })


# ─────────────────────────────────────────────
# H. Historial Académico Multi-Ciclo (filtro)
# Esto lo logramos agregando soporte de ?ciclo=<id>
# al StudentPortalApiService existente.
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_academic_history(request):
    """
    GET /api/estudiante/historial-academico/?ciclo=<id>
    Retorna notas y asistencia del estudiante filtradas por ciclo académico.
    Si no se pasa ciclo, retorna el ciclo activo.
    """
    user = request.user
    role_name = getattr(getattr(user, 'role', None), 'nombre', '').strip().lower()
    if role_name not in {'estudiante', 'alumno'} and not _is_global_admin(user):
        raise PermissionDenied('Solo estudiantes pueden acceder a su historial.')

    from django.db.models import Avg
    from backend.apps.academico.models import Asistencia, Calificacion
    from backend.apps.institucion.models import CicloAcademico

    school_id = getattr(user, 'rbd_colegio', None)
    ciclo_id = request.query_params.get('ciclo')

    # Resolver ciclo
    if ciclo_id:
        try:
            ciclo = CicloAcademico.objects.get(id=ciclo_id, colegio_id=school_id)
        except CicloAcademico.DoesNotExist:
            raise ValidationError({'ciclo': 'Ciclo académico no encontrado.'})
    else:
        ciclo = CicloAcademico.objects.filter(
            colegio_id=school_id, estado='ACTIVO'
        ).first()

    if not ciclo:
        return Response({
            'ciclo': None,
            'asignaturas': [],
            'ciclos_disponibles': [],
        })

    # Clases del ciclo
    mis_clases = ClaseEstudiante.objects.filter(
        estudiante_id=user.id, activo=True,
        clase__curso__ciclo_academico=ciclo,
    ).select_related('clase__asignatura', 'clase__curso')

    asignaturas = []
    for ce in mis_clases:
        clase = ce.clase
        notas = Calificacion.objects.filter(
            estudiante_id=user.id, evaluacion__clase=clase
        ).values_list('nota', flat=True)

        att_total = Asistencia.objects.filter(
            estudiante_id=user.id, clase=clase
        ).count()
        att_present = Asistencia.objects.filter(
            estudiante_id=user.id, clase=clase, estado='P'
        ).count()

        asignaturas.append({
            'clase_id': clase.id,
            'asignatura': clase.asignatura.nombre if clase.asignatura else '',
            'curso': clase.curso.nombre if clase.curso else '',
            'notas': [float(n) for n in notas],
            'promedio': round(float(sum(notas)) / len(notas), 1) if notas else None,
            'total_clases': att_total,
            'asistencias': att_present,
            'porcentaje_asistencia': round((att_present / att_total) * 100, 1) if att_total else 100.0,
        })

    # Ciclos disponibles
    ciclos = CicloAcademico.objects.filter(
        colegio_id=school_id
    ).order_by('-fecha_inicio').values('id', 'nombre', 'estado')

    return Response({
        'ciclo': {
            'id': ciclo.id,
            'nombre': ciclo.nombre,
            'estado': ciclo.estado,
        },
        'asignaturas': asignaturas,
        'ciclos_disponibles': list(ciclos),
    })


# ─────────────────────────────────────────────
# Apoderado: Materiales por pupilo
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def apoderado_pupilo_materiales(request, student_id):
    """
    GET /api/apoderado/pupilo/<student_id>/materiales/
    Retorna materiales públicos de las clases del pupilo.
    """
    user = request.user

    try:
        apoderado = Apoderado.objects.get(user=user)
    except Apoderado.DoesNotExist:
        raise PermissionDenied('Solo apoderados pueden acceder a este recurso.')

    # Verificar relación
    if not RelacionApoderadoEstudiante.objects.filter(
        apoderado=apoderado, estudiante_id=student_id, activa=True
    ).exists():
        raise PermissionDenied('No tiene relación activa con este estudiante.')

    # Verificar permiso de ver materiales
    if not apoderado.puede_ver_materiales:
        raise PermissionDenied('No tiene permisos para ver materiales.')

    # Clases del estudiante
    clases_ids = ClaseEstudiante.objects.filter(
        estudiante_id=student_id, activo=True
    ).values_list('clase_id', flat=True)

    materiales = MaterialClase.objects.filter(
        clase_id__in=clases_ids, es_publico=True, activo=True,
    ).select_related(
        'clase__asignatura', 'clase__curso', 'subido_por'
    ).order_by('-fecha_creacion')

    return Response(MaterialClaseSerializer(materiales, many=True).data)

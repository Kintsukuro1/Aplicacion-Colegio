from django.db.models import Avg, Count, Q, Sum
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.academico.models import Asistencia, Calificacion
from backend.apps.accounts.models import RelacionApoderadoEstudiante
from backend.apps.comunicados.models import Comunicado
from backend.apps.core.models import AnotacionConvivencia, JustificativoInasistencia
from backend.apps.matriculas.models import Cuota, EstadoCuenta, Matricula


def _guardian_relations(user):
    return (
        RelacionApoderadoEstudiante.objects.select_related("estudiante", "apoderado")
        .filter(
            apoderado__user=user,
            apoderado__activo=True,
            activa=True,
            estudiante__is_active=True,
        )
        .order_by("prioridad_contacto", "estudiante__apellido_paterno", "estudiante__nombre")
    )


def _relation_for_student(user, student_id):
    return (
        _guardian_relations(user)
        .filter(estudiante_id=student_id)
        .first()
    )


def _forbidden_if_not_guardian(user):
    if not hasattr(user, "perfil_apoderado"):
        return Response(
            {"detail": "El usuario autenticado no tiene perfil de apoderado."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _check_student_access(user, student_id, permission_key=None):
    relation = _relation_for_student(user, student_id)
    if not relation:
        return None, Response(
            {"detail": "No tiene relacion activa con el pupilo solicitado."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if permission_key:
        permisos = relation.get_permisos_efectivos()
        if not permisos.get(permission_key, False):
            return None, Response(
                {"detail": "Su relacion con este pupilo no permite acceder a este recurso."},
                status=status.HTTP_403_FORBIDDEN,
            )
    return relation, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_mis_pupilos(request):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    relaciones = list(_guardian_relations(request.user))
    pupil_ids = [r.estudiante_id for r in relaciones]

    promedio_by_student = {
        row["estudiante"]: row["promedio"]
        for row in Calificacion.objects.filter(estudiante_id__in=pupil_ids)
        .values("estudiante")
        .annotate(promedio=Avg("nota"))
    }
    asistencia_by_student = {
        row["estudiante"]: row
        for row in Asistencia.objects.filter(estudiante_id__in=pupil_ids)
        .values("estudiante")
        .annotate(
            total=Count("id_asistencia"),
            presentes=Count("id_asistencia", filter=Q(estado="P")),
        )
    }
    pendientes_justif_by_student = {
        row["estudiante"]: row["pendientes"]
        for row in JustificativoInasistencia.objects.filter(
            estudiante_id__in=pupil_ids,
            estado="PENDIENTE",
        )
        .values("estudiante")
        .annotate(pendientes=Count("id_justificativo"))
    }

    matriculas = (
        Matricula.objects.select_related("curso", "ciclo_academico")
        .filter(estudiante_id__in=pupil_ids, estado="ACTIVA")
        .order_by("estudiante_id", "-fecha_matricula")
    )
    matricula_by_student = {}
    for m in matriculas:
        matricula_by_student.setdefault(m.estudiante_id, m)

    payload = []
    for rel in relaciones:
        student = rel.estudiante
        asistencia_row = asistencia_by_student.get(student.id, {"total": 0, "presentes": 0})
        total_asis = asistencia_row.get("total", 0) or 0
        presentes = asistencia_row.get("presentes", 0) or 0
        porcentaje_asistencia = round((presentes * 100.0 / total_asis), 2) if total_asis else 0.0
        matricula = matricula_by_student.get(student.id)

        payload.append(
            {
                "id": student.id,
                "nombre_completo": student.get_full_name(),
                "rut": student.rut,
                "curso": matricula.curso.nombre if matricula and matricula.curso else None,
                "ciclo_academico": matricula.ciclo_academico.nombre if matricula and matricula.ciclo_academico else None,
                "parentesco": rel.parentesco,
                "tipo_apoderado": rel.tipo_apoderado,
                "promedio_notas": float(promedio_by_student.get(student.id)) if promedio_by_student.get(student.id) is not None else None,
                "asistencia_porcentaje": porcentaje_asistencia,
                "justificativos_pendientes": pendientes_justif_by_student.get(student.id, 0),
            }
        )

    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_pupilo_notas(request, student_id):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    _, error = _check_student_access(request.user, student_id, permission_key="ver_notas")
    if error:
        return error

    notas_qs = (
        Calificacion.objects.filter(estudiante_id=student_id)
        .select_related("evaluacion", "evaluacion__clase", "evaluacion__clase__asignatura", "evaluacion__clase__curso")
        .order_by("-evaluacion__fecha_evaluacion", "-id_calificacion")
    )

    promedio = notas_qs.aggregate(promedio=Avg("nota"))["promedio"]
    data = [
        {
            "id_calificacion": row.id_calificacion,
            "nota": float(row.nota),
            "evaluacion": row.evaluacion.nombre,
            "fecha_evaluacion": row.evaluacion.fecha_evaluacion,
            "tipo_evaluacion": row.evaluacion.tipo_evaluacion,
            "asignatura": row.evaluacion.clase.asignatura.nombre,
            "curso": row.evaluacion.clase.curso.nombre,
            "ponderacion": float(row.evaluacion.ponderacion),
        }
        for row in notas_qs
    ]

    return Response(
        {
            "student_id": student_id,
            "promedio": float(promedio) if promedio is not None else None,
            "total_notas": len(data),
            "resultados": data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_pupilo_asistencia(request, student_id):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    _, error = _check_student_access(request.user, student_id, permission_key="ver_asistencia")
    if error:
        return error

    asistencia_qs = (
        Asistencia.objects.filter(estudiante_id=student_id)
        .select_related("clase", "clase__curso", "clase__asignatura")
        .order_by("-fecha", "-id_asistencia")
    )
    stats = asistencia_qs.aggregate(
        total=Count("id_asistencia"),
        presentes=Count("id_asistencia", filter=Q(estado="P")),
        ausentes=Count("id_asistencia", filter=Q(estado="A")),
        tardanzas=Count("id_asistencia", filter=Q(estado="T")),
        justificadas=Count("id_asistencia", filter=Q(estado="J")),
    )

    total = stats["total"] or 0
    presentes = stats["presentes"] or 0
    porcentaje = round((presentes * 100.0 / total), 2) if total else 0.0

    data = [
        {
            "id_asistencia": row.id_asistencia,
            "fecha": row.fecha,
            "estado": row.estado,
            "estado_display": row.get_estado_display(),
            "asignatura": row.clase.asignatura.nombre,
            "curso": row.clase.curso.nombre,
            "tipo_asistencia": row.tipo_asistencia,
            "observaciones": row.observaciones,
        }
        for row in asistencia_qs[:200]
    ]

    return Response(
        {
            "student_id": student_id,
            "resumen": {
                "total": total,
                "presentes": presentes,
                "ausentes": stats["ausentes"] or 0,
                "tardanzas": stats["tardanzas"] or 0,
                "justificadas": stats["justificadas"] or 0,
                "porcentaje_asistencia": porcentaje,
            },
            "resultados": data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_pupilo_anotaciones(request, student_id):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    _, error = _check_student_access(request.user, student_id)
    if error:
        return error

    anotaciones_qs = (
        AnotacionConvivencia.objects.filter(estudiante_id=student_id)
        .select_related("registrado_por")
        .order_by("-fecha")
    )

    data = [
        {
            "id_anotacion": row.id_anotacion,
            "fecha": row.fecha,
            "tipo": row.tipo,
            "tipo_display": row.get_tipo_display(),
            "categoria": row.categoria,
            "gravedad": row.gravedad,
            "descripcion": row.descripcion,
            "registrado_por": row.registrado_por.get_full_name() if row.registrado_por else None,
            "notificado_apoderado": row.notificado_apoderado,
            "fecha_notificacion": row.fecha_notificacion,
        }
        for row in anotaciones_qs
    ]

    return Response(
        {
            "student_id": student_id,
            "total": len(data),
            "resultados": data,
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def apoderado_justificativos(request):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    if request.method == "GET":
        from backend.apps.core.views.school_context import resolve_request_rbd
        from backend.apps.core.services.apoderado_api_service import ApoderadoApiService
        rbd = resolve_request_rbd(request)
        if not rbd:
            relaciones = list(_guardian_relations(request.user))
            if relaciones:
                rbd = relaciones[0].estudiante.rbd_colegio
        
        if not rbd:
            return Response({"success": True, "justificativos": []})

        data = ApoderadoApiService.list_justificativos(request.user, rbd)
        return Response({"success": True, "justificativos": data})

    # POST method (Create justificativo)
    student_id = request.data.get("estudiante_id") or request.data.get("pupilo_id")
    if not student_id:
        return Response({"detail": "Debe enviar 'estudiante_id' o 'pupilo_id'."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        student_id = int(student_id)
    except (TypeError, ValueError):
        return Response({"detail": "El identificador del pupilo es invalido."}, status=status.HTTP_400_BAD_REQUEST)

    relation, error = _check_student_access(request.user, student_id)
    if error:
        return error

    fecha_ausencia = request.data.get("fecha_ausencia")
    motivo = (request.data.get("motivo") or "").strip()
    tipo = request.data.get("tipo", "OTRO")
    fecha_fin_ausencia = request.data.get("fecha_fin_ausencia") or None
    documento = (
        request.FILES.get("foto")
        or request.FILES.get("documento")
        or request.FILES.get("documento_adjunto")
    )

    if not fecha_ausencia:
        return Response({"detail": "La fecha_ausencia es obligatoria."}, status=status.HTTP_400_BAD_REQUEST)
    if not motivo:
        return Response({"detail": "El motivo es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

    valid_tipos = {key for key, _ in JustificativoInasistencia.TIPOS}
    if tipo not in valid_tipos:
        return Response({"detail": "Tipo de justificativo invalido."}, status=status.HTTP_400_BAD_REQUEST)

    pupil = relation.estudiante
    justificativo = JustificativoInasistencia.objects.create(
        estudiante_id=student_id,
        colegio_id=pupil.rbd_colegio,
        fecha_ausencia=fecha_ausencia,
        fecha_fin_ausencia=fecha_fin_ausencia,
        motivo=motivo,
        tipo=tipo,
        documento_adjunto=documento,
        presentado_por=request.user,
    )

    return Response(
        {
            "id_justificativo": justificativo.id_justificativo,
            "estado": justificativo.estado,
            "message": "Justificativo creado correctamente.",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_listar_firmas(request):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    import logging
    logger = logging.getLogger(__name__)

    try:
        apoderado = request.user.perfil_apoderado
        from backend.apps.core.services.apoderado_api_service import ApoderadoApiService
        pendientes, firmados = ApoderadoApiService.list_firmas_apoderado(apoderado)
        return Response({
            "success": True,
            "pendientes": pendientes,
            "firmados": firmados,
        })
    except Exception as e:
        logger.exception("Error listando documentos de firma")
        return Response({"detail": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def apoderado_firmar_documento(request):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    import logging
    logger = logging.getLogger(__name__)

    try:
        tipo_documento = request.data.get("tipo_documento")
        titulo = request.data.get("titulo", "")
        contenido = request.data.get("contenido", "")
        estudiante_id = request.data.get("estudiante_id")
        documento_id = request.data.get("documento_id")
        documento_tipo_modelo = request.data.get("documento_tipo_modelo")

        if not tipo_documento or not titulo:
            return Response({"detail": "Datos incompletos"}, status=status.HTTP_400_BAD_REQUEST)

        apoderado = request.user.perfil_apoderado
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        from backend.apps.core.services.apoderado_api_service import ApoderadoApiService
        estudiante = None
        if estudiante_id:
            est_ids = ApoderadoApiService.get_estudiante_ids_for_apoderado(request.user)
            if int(estudiante_id) not in est_ids:
                return Response({"detail": "Estudiante no autorizado"}, status=status.HTTP_403_FORBIDDEN)
            
            from backend.apps.accounts.models import User as DjangoUser
            try:
                estudiante = DjangoUser.objects.get(id=int(estudiante_id))
            except DjangoUser.DoesNotExist:
                return Response({"detail": "Estudiante no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        firma = ApoderadoApiService.firmar_documento(
            apoderado=apoderado,
            tipo_documento=tipo_documento,
            titulo=titulo,
            contenido=contenido,
            ip_address=ip_address,
            user_agent=user_agent,
            estudiante=estudiante,
            documento_id=documento_id,
            documento_tipo_modelo=documento_tipo_modelo,
        )

        return Response({
            "success": True,
            "message": "Documento firmado correctamente",
            "firma_id": firma.id,
        })
    except Exception as e:
        logger.exception("Error firmando documento")
        return Response({"detail": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_opciones_admision(request):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    from backend.apps.core.views.school_context import resolve_request_rbd
    rbd = resolve_request_rbd(request)
    if not rbd:
        relaciones = list(_guardian_relations(request.user))
        if relaciones:
            rbd = relaciones[0].estudiante.rbd_colegio
            
    if not rbd:
        rbd = request.user.rbd_colegio

    if not rbd:
        return Response({"cursos": [], "ciclos": []})

    from backend.apps.cursos.models import Curso
    from backend.apps.institucion.models import CicloAcademico

    cursos = Curso.objects.filter(colegio_id=rbd, activo=True).order_by("nombre")
    ciclos = CicloAcademico.objects.filter(colegio_id=rbd).order_by("-fecha_inicio")

    cursos_data = [{"id": c.id_curso, "nombre": c.nombre} for c in cursos]
    ciclos_data = [{"id": c.id, "nombre": c.nombre, "estado": c.estado} for c in ciclos]

    return Response({
        "cursos": cursos_data,
        "ciclos": ciclos_data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_comunicados(request):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    relaciones = list(_guardian_relations(request.user))
    pupil_ids = [r.estudiante_id for r in relaciones]
    if not pupil_ids:
        return Response([])

    school_ids = list({r.estudiante.rbd_colegio for r in relaciones if r.estudiante.rbd_colegio})
    course_ids = list(
        Matricula.objects.filter(estudiante_id__in=pupil_ids, estado="ACTIVA")
        .exclude(curso_id__isnull=True)
        .values_list("curso_id", flat=True)
    )

    base_qs = Comunicado.objects.select_related("publicado_por", "colegio").filter(activo=True)
    if school_ids:
        base_qs = base_qs.filter(colegio_id__in=school_ids)

    comunicados = base_qs.filter(
        Q(destinatario="todos")
        | Q(destinatario="apoderados")
        | Q(destinatario="curso_especifico", cursos_destinatarios__in=course_ids)
    ).distinct().order_by("-es_prioritario", "-fecha_publicacion", "-id_comunicado")

    data = [
        {
            "id_comunicado": row.id_comunicado,
            "tipo": row.tipo,
            "titulo": row.titulo,
            "contenido": row.contenido,
            "destinatario": row.destinatario,
            "es_prioritario": row.es_prioritario,
            "es_destacado": row.es_destacado,
            "fecha_publicacion": row.fecha_publicacion,
            "fecha_evento": row.fecha_evento,
            "lugar_evento": row.lugar_evento,
            "requiere_confirmacion": row.requiere_confirmacion,
            "archivo_adjunto": row.archivo_adjunto.url if row.archivo_adjunto else None,
            "colegio": row.colegio.nombre if row.colegio else None,
            "publicado_por": row.publicado_por.get_full_name() if row.publicado_por else None,
        }
        for row in comunicados[:100]
    ]

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def apoderado_pagos_estado(request):
    profile_error = _forbidden_if_not_guardian(request.user)
    if profile_error:
        return profile_error

    relaciones = list(_guardian_relations(request.user))
    pupil_ids = [r.estudiante_id for r in relaciones]
    if not pupil_ids:
        return Response({"resumen": {"total_deuda": 0, "total_pagado": 0, "saldo_pendiente": 0}, "pupilos": []})

    estados_qs = EstadoCuenta.objects.filter(estudiante_id__in=pupil_ids).select_related("estudiante").order_by("estudiante_id", "-anio", "-mes")
    latest_by_student = {}
    for row in estados_qs:
        latest_by_student.setdefault(row.estudiante_id, row)

    cuotas_stats = {
        row["matricula__estudiante"]: row
        for row in Cuota.objects.filter(matricula__estudiante_id__in=pupil_ids)
        .values("matricula__estudiante")
        .annotate(
            deuda_vencida=Sum("monto_final", filter=Q(estado="VENCIDA")),
            pendiente=Sum("monto_final", filter=Q(estado="PENDIENTE")),
            pagado=Sum("monto_pagado"),
        )
    }

    pupilos = []
    total_deuda = 0.0
    total_pagado = 0.0
    total_saldo = 0.0

    for rel in relaciones:
        student = rel.estudiante
        estado = latest_by_student.get(student.id)
        cuota = cuotas_stats.get(student.id, {})

        deuda_vencida = float(cuota.get("deuda_vencida") or 0)
        pendiente = float(cuota.get("pendiente") or 0)
        pagado = float(cuota.get("pagado") or 0)

        if estado:
            deuda = float(estado.total_deuda)
            saldo = float(estado.saldo_pendiente)
            pagado_estado = float(estado.total_pagado)
            periodo = f"{estado.mes:02d}-{estado.anio}"
        else:
            deuda = deuda_vencida + pendiente
            saldo = deuda
            pagado_estado = pagado
            periodo = None

        total_deuda += deuda
        total_pagado += pagado_estado
        total_saldo += saldo

        pupilos.append(
            {
                "student_id": student.id,
                "nombre_completo": student.get_full_name(),
                "periodo_estado": periodo,
                "total_deuda": deuda,
                "total_pagado": pagado_estado,
                "saldo_pendiente": saldo,
                "deuda_vencida": deuda_vencida,
                "pendiente": pendiente,
                "pagado_historico": pagado,
            }
        )

    return Response(
        {
            "resumen": {
                "total_deuda": round(total_deuda, 2),
                "total_pagado": round(total_pagado, 2),
                "saldo_pendiente": round(total_saldo, 2),
            },
            "pupilos": pupilos,
        }
    )

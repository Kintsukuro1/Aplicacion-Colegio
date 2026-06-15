import io
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from backend.apps.accounts.models import PerfilEstudiante, User
from backend.apps.academico.models import Asistencia, Calificacion
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.common.services.policy_service import PolicyService


def _pdf_response(filename: str, build_fn) -> HttpResponse:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    build_fn(c)
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def _can_access_student(request_user, estudiante: User) -> bool:
    if PolicyService.has_capability(request_user, 'SYSTEM_ADMIN'):
        return True

    if PolicyService.has_capability(request_user, 'DASHBOARD_VIEW_SCHOOL'):
        return True

    return request_user.id == estudiante.id


@login_required()
def descargar_certificado_notas(request, estudiante_id: int):
    """Genera un PDF simple de certificado de notas (migrado)."""
    try:
        estudiante = ORMAccessService.get(User, id=estudiante_id)
    except Exception:
        return HttpResponseForbidden('Estudiante no encontrado')

    if not _can_access_student(request.user, estudiante):
        return HttpResponseForbidden('No tiene permisos para acceder a este certificado')

    # Limitar al colegio actual del usuario en sesión cuando aplique
    colegio_id = request.user.rbd_colegio or estudiante.rbd_colegio

    calificaciones = (
        ORMAccessService.filter(Calificacion, estudiante_id=estudiante.id, colegio_id=colegio_id)
        .select_related('evaluacion__clase__asignatura')
        .order_by('evaluacion__clase__asignatura__nombre', 'evaluacion__fecha_evaluacion')
    )

    # Promedio general
    notas = [float(c.nota) for c in calificaciones if c.nota is not None]
    promedio_general = round(sum(notas) / len(notas), 1) if notas else None

    hoy = timezone.localdate()
    anio = hoy.year
    rut = getattr(estudiante, 'rut', '') or ''

    def build(c):
        width, height = A4
        y = height - 2.0 * cm

        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(width / 2, y, 'CERTIFICADO DE NOTAS')
        y -= 1.0 * cm

        c.setFont('Helvetica', 10)
        colegio = estudiante.colegio
        colegio_nombre = colegio.nombre if colegio else 'Sistema Escolar'
        c.drawString(2.0 * cm, y, f'Colegio: {colegio_nombre}')
        y -= 0.6 * cm
        c.drawString(2.0 * cm, y, f'Estudiante: {estudiante.get_full_name()}')
        y -= 0.6 * cm
        c.drawString(2.0 * cm, y, f'RUT: {rut}')
        y -= 0.6 * cm
        c.drawString(2.0 * cm, y, f'Año: {anio}')
        y -= 0.8 * cm

        if promedio_general is not None:
            c.setFont('Helvetica-Bold', 10)
            c.drawString(2.0 * cm, y, f'Promedio general: {promedio_general}')
            y -= 0.8 * cm

        c.setFont('Helvetica-Bold', 10)
        c.drawString(2.0 * cm, y, 'Detalle de calificaciones:')
        y -= 0.6 * cm

        c.setFont('Helvetica-Bold', 9)
        c.drawString(2.0 * cm, y, 'Asignatura')
        c.drawString(10.5 * cm, y, 'Evaluación')
        c.drawString(17.5 * cm, y, 'Nota')
        y -= 0.4 * cm
        c.line(2.0 * cm, y, width - 2.0 * cm, y)
        y -= 0.5 * cm

        c.setFont('Helvetica', 9)
        if not calificaciones:
            c.drawString(2.0 * cm, y, 'No hay calificaciones registradas para este estudiante.')
            return

        for cal in calificaciones:
            asignatura = getattr(getattr(getattr(cal.evaluacion, 'clase', None), 'asignatura', None), 'nombre', '-')
            evaluacion = getattr(cal.evaluacion, 'nombre', '-')
            nota = f"{cal.nota}" if cal.nota is not None else '-'

            c.drawString(2.0 * cm, y, str(asignatura)[:40])
            c.drawString(10.5 * cm, y, str(evaluacion)[:35])
            c.drawRightString(width - 2.0 * cm, y, nota)
            y -= 0.45 * cm

            if y < 2.5 * cm:
                c.showPage()
                y = height - 2.0 * cm
                c.setFont('Helvetica', 9)

        c.setFont('Helvetica-Oblique', 8)
        c.drawString(2.0 * cm, 1.8 * cm, f'Generado el {hoy.strftime("%d/%m/%Y")}.')

    filename = f'certificado_notas_{rut or estudiante.id}_{anio}.pdf'
    return _pdf_response(filename, build)


@login_required()
def descargar_certificado_matricula(request, estudiante_id: int):
    """Genera un PDF simple de certificado de matrícula (migrado)."""
    try:
        estudiante = ORMAccessService.get(User, id=estudiante_id)
    except Exception:
        return HttpResponseForbidden('Estudiante no encontrado')

    if not _can_access_student(request.user, estudiante):
        return HttpResponseForbidden('No tiene permisos para acceder a este certificado')

    perfil = ORMAccessService.filter(PerfilEstudiante, user=estudiante).first()
    curso = perfil.curso_actual if perfil else None
    hoy = timezone.localdate()
    anio = hoy.year
    rut = getattr(estudiante, 'rut', '') or ''

    def build(c):
        width, height = A4
        y = height - 2.0 * cm

        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(width / 2, y, 'CERTIFICADO DE MATRÍCULA')
        y -= 1.2 * cm

        colegio = estudiante.colegio
        colegio_nombre = colegio.nombre if colegio else 'Sistema Escolar'

        c.setFont('Helvetica', 11)
        c.drawString(2.0 * cm, y, f'Colegio: {colegio_nombre}')
        y -= 0.8 * cm
        c.drawString(2.0 * cm, y, f'Estudiante: {estudiante.get_full_name()}')
        y -= 0.8 * cm
        c.drawString(2.0 * cm, y, f'RUT: {rut}')
        y -= 0.8 * cm
        c.drawString(2.0 * cm, y, f'Curso: {curso or "(sin curso asignado)"}')
        y -= 0.8 * cm
        c.drawString(2.0 * cm, y, f'Año académico: {anio}')
        y -= 1.2 * cm

        c.setFont('Helvetica', 10)
        texto = (
            'Se certifica que el/la estudiante indicado(a) se encuentra matriculado(a) '
            'en el establecimiento para el año académico señalado.'
        )
        c.drawString(2.0 * cm, y, texto)

        c.setFont('Helvetica-Oblique', 8)
        c.drawString(2.0 * cm, 1.8 * cm, f'Generado el {hoy.strftime("%d/%m/%Y")}.')

    filename = f'certificado_matricula_{rut or estudiante.id}_{anio}.pdf'
    return _pdf_response(filename, build)


@login_required()
def descargar_informe_rendimiento(request, estudiante_id: int):
    """Genera un PDF simple de informe de rendimiento (migrado)."""
    try:
        estudiante = ORMAccessService.get(User, id=estudiante_id)
    except Exception:
        return HttpResponseForbidden('Estudiante no encontrado')

    if not _can_access_student(request.user, estudiante):
        return HttpResponseForbidden('No tiene permisos para acceder a este certificado')

    colegio_id = request.user.rbd_colegio or estudiante.rbd_colegio
    hoy = timezone.localdate()
    anio = hoy.year

    calificaciones = ORMAccessService.filter(Calificacion, estudiante_id=estudiante.id, colegio_id=colegio_id)
    notas = [float(c.nota) for c in calificaciones if c.nota is not None]
    promedio_general = round(sum(notas) / len(notas), 1) if notas else None

    # Asistencia (si existe data)
    asistencias = ORMAccessService.filter(Asistencia, estudiante_id=estudiante.id, colegio_id=colegio_id, fecha__year=anio)
    total = asistencias.count()
    presentes = asistencias.filter(estado='P').count()
    porcentaje_asistencia = round((presentes / total) * 100, 0) if total else None

    rut = getattr(estudiante, 'rut', '') or ''

    def build(c):
        width, height = A4
        y = height - 2.0 * cm

        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(width / 2, y, 'INFORME DE RENDIMIENTO')
        y -= 1.2 * cm

        colegio = estudiante.colegio
        colegio_nombre = colegio.nombre if colegio else 'Sistema Escolar'

        c.setFont('Helvetica', 11)
        c.drawString(2.0 * cm, y, f'Colegio: {colegio_nombre}')
        y -= 0.8 * cm
        c.drawString(2.0 * cm, y, f'Estudiante: {estudiante.get_full_name()}')
        y -= 0.8 * cm
        c.drawString(2.0 * cm, y, f'RUT: {rut}')
        y -= 0.8 * cm
        c.drawString(2.0 * cm, y, f'Año: {anio}')
        y -= 1.2 * cm

        c.setFont('Helvetica-Bold', 11)
        c.drawString(2.0 * cm, y, 'Resumen:')
        y -= 0.8 * cm

        c.setFont('Helvetica', 10)
        c.drawString(2.0 * cm, y, f'Promedio general: {promedio_general if promedio_general is not None else "N/A"}')
        y -= 0.6 * cm
        c.drawString(2.0 * cm, y, f'Asistencia: {str(int(porcentaje_asistencia)) + "%" if porcentaje_asistencia is not None else "N/A"}')
        y -= 0.6 * cm
        c.drawString(2.0 * cm, y, f'Total de evaluaciones calificadas: {calificaciones.count()}')

        c.setFont('Helvetica-Oblique', 8)
        c.drawString(2.0 * cm, 1.8 * cm, f'Generado el {hoy.strftime("%d/%m/%Y")}.')

    filename = f'informe_rendimiento_{rut or estudiante.id}_{anio}.pdf'
    return _pdf_response(filename, build)


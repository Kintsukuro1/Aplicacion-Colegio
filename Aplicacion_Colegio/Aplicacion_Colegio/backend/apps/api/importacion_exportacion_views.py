"""
Views de importación masiva y exportación de reportes — Semana 11-12.

M. Importación masiva de datos vía API REST (CSV/Excel)
   - Expone ImportacionCSVService como endpoints REST
   - Agrega soporte para archivos Excel (.xlsx)
   - Incluye descarga de plantillas CSV

Exportación de reportes académicos vía API
   - Informe académico por estudiante (PDF)
   - Reporte de asistencia por clase (Excel)
   - Reporte de rendimiento por clase (Excel)
   - Listado de estudiantes/profesores (CSV export)
"""
import csv
import io
import logging
from datetime import date

from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.accounts.models import PerfilEstudiante, PerfilProfesor, Role, User
from backend.apps.core.services.import_csv_service import ImportacionCSVService
from backend.common.services.policy_service import PolicyService

logger = logging.getLogger('api')


def _is_admin(user):
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN') or \
        PolicyService.has_capability(user, 'SYSTEM_CONFIGURE')


def _school_id(user):
    return getattr(user, 'rbd_colegio', None)


def _parse_positive_int(value, field_name):
    """Parsea enteros positivos y retorna ValidationError controlado si falla."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: 'Debe ser un entero valido.'})

    if parsed <= 0:
        raise ValidationError({field_name: 'Debe ser un entero mayor a 0.'})

    return parsed


# ═══════════════════════════════════════════════
# M. IMPORTACIÓN MASIVA VÍA API REST
# ═══════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def api_importar_datos(request):
    """
    POST /api/importacion/importar/
    Importación masiva de usuarios desde CSV o Excel.

    Form-data:
      - archivo: archivo CSV o Excel (.csv, .xlsx)
      - tipo: "estudiantes" | "profesores" | "apoderados"
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores pueden importar datos.')

    archivo = request.FILES.get('archivo')
    tipo = request.data.get('tipo', '').strip().lower()

    if not archivo:
        raise ValidationError({'archivo': 'Se requiere un archivo CSV o Excel.'})

    if tipo not in ('estudiantes', 'profesores', 'apoderados'):
        raise ValidationError({'tipo': 'Debe ser: estudiantes, profesores o apoderados.'})

    school_id = _school_id(user)
    if not school_id:
        raise ValidationError({'colegio': 'No tiene colegio asignado.'})

    # Detectar formato y convertir Excel a CSV-like si es necesario
    filename = archivo.name.lower()

    # Validar tamano para cualquier formato antes de procesar.
    if archivo.size > ImportacionCSVService.MAX_FILE_SIZE:
        raise ValidationError({'archivo': 'El archivo excede el tamano maximo de 5 MB.'})

    if filename.endswith('.xlsx'):
        archivo = _convert_excel_to_csv_file(archivo)
    elif not filename.endswith('.csv'):
        raise ValidationError({'archivo': 'Formato no soportado. Use CSV (.csv) o Excel (.xlsx).'})

    # Validar archivo resultante (si viene xlsx, ya convertido a csv)
    valido, mensaje = ImportacionCSVService.validar_archivo(archivo)
    if not valido:
        raise ValidationError({'archivo': mensaje})

    # Ejecutar importación según tipo
    try:
        if tipo == 'estudiantes':
            exitosos, fallidos, errores = ImportacionCSVService.importar_estudiantes(archivo, school_id)
        elif tipo == 'profesores':
            exitosos, fallidos, errores = ImportacionCSVService.importar_profesores(archivo, school_id)
        elif tipo == 'apoderados':
            exitosos, fallidos, errores = ImportacionCSVService.importar_apoderados(archivo, school_id)
    except Exception as e:
        logger.error(f'Error en importación masiva: {e}')
        raise ValidationError({'detail': str(e)})

    if (exitosos + fallidos) == 0:
        raise ValidationError({'archivo': 'El archivo no contiene filas de datos para importar.'})

    logger.info(
        f'Importación {tipo} — exitosos={exitosos} fallidos={fallidos} '
        f'user={user.email} colegio={school_id}'
    )

    return Response({
        'tipo': tipo,
        'exitosos': exitosos,
        'fallidos': fallidos,
        'total_procesados': exitosos + fallidos,
        'errores': errores[:50],  # Limitar errores para no saturar respuesta
        'tiene_mas_errores': len(errores) > 50,
    })


def _convert_excel_to_csv_file(excel_file):
    """
    Convierte un archivo Excel (.xlsx) a un objeto file-like CSV
    para reutilizar ImportacionCSVService.
    """
    try:
        import openpyxl
    except ImportError:
        raise ValidationError({
            'archivo': 'Para importar Excel se requiere la librería openpyxl. '
                       'Instale con: pip install openpyxl'
        })

    try:
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active

        output = io.StringIO()
        writer = csv.writer(output)

        for row in ws.iter_rows(values_only=True):
            writer.writerow([str(cell) if cell is not None else '' for cell in row])

        # Crear un archivo-like que sea compatible con ImportacionCSVService
        csv_content = output.getvalue().encode('utf-8')
        csv_file = io.BytesIO(csv_content)
        csv_file.name = excel_file.name.replace('.xlsx', '.csv').replace('.xls', '.csv')
        csv_file.size = len(csv_content)

        wb.close()
        return csv_file
    except Exception as e:
        raise ValidationError({'archivo': f'Error al procesar archivo Excel: {str(e)}'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_descargar_plantilla(request, tipo):
    """
    GET /api/importacion/plantilla/<tipo>/
    Descarga la plantilla CSV de ejemplo.

    Tipos: estudiantes, profesores, apoderados
    """
    if not _is_admin(request.user):
        raise PermissionDenied('Solo administradores.')

    if tipo == 'estudiantes':
        contenido = ImportacionCSVService.generar_plantilla_estudiantes()
    elif tipo == 'profesores':
        contenido = ImportacionCSVService.generar_plantilla_profesores()
    elif tipo == 'apoderados':
        contenido = ImportacionCSVService.generar_plantilla_apoderados()
    else:
        raise ValidationError({'tipo': 'Debe ser: estudiantes, profesores o apoderados.'})

    response = HttpResponse(contenido, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="plantilla_{tipo}.csv"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_importacion_dashboard(request):
    """
    GET /api/importacion/dashboard/
    Muestra resumen de datos actuales del colegio (conteos por rol).
    """
    if not _is_admin(request.user):
        raise PermissionDenied('Solo administradores.')

    school_id = _school_id(request.user)
    if not school_id:
        raise ValidationError({'colegio': 'No tiene colegio asignado.'})

    data = ImportacionCSVService.get_importar_datos_dashboard(school_id)

    return Response({
        'total_estudiantes': data['total_estudiantes'],
        'total_profesores': data['total_profesores'],
        'total_apoderados': data['total_apoderados'],
    })


# ═══════════════════════════════════════════════
# EXPORTACIÓN DE REPORTES VÍA API
# ═══════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_estudiantes(request):
    """
    GET /api/exportacion/estudiantes/
    Exporta listado de estudiantes del colegio en CSV.

    Query params: ?estado=Activo&curso_id=5
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores.')

    school_id = _school_id(user)

    rol_estudiante = (
        Role.objects.filter(nombre__iexact='Alumno').first()
        or Role.objects.filter(nombre__iexact='Estudiante').first()
    )
    if not rol_estudiante:
        raise ValidationError({'detail': 'Rol de estudiante no configurado.'})

    qs = User.objects.filter(
        rbd_colegio=school_id,
        role=rol_estudiante,
    ).select_related('perfil_estudiante').order_by('apellido_paterno', 'nombre')

    estado = request.query_params.get('estado')
    if estado:
        qs = qs.filter(perfil_estudiante__estado_academico=estado)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="estudiantes_{school_id}_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'RUT', 'Nombre', 'Apellido Paterno', 'Apellido Materno',
        'Email', 'Estado', 'Tiene NEE', 'Tipo NEE', 'Requiere PIE',
        'Fecha Ingreso', 'Teléfono',
    ])

    for est in qs:
        perfil = getattr(est, 'perfil_estudiante', None)
        writer.writerow([
            est.rut or '',
            est.nombre or '',
            est.apellido_paterno or '',
            est.apellido_materno or '',
            est.email or '',
            getattr(perfil, 'estado_academico', '') if perfil else '',
            'Sí' if perfil and perfil.tiene_nee else 'No',
            getattr(perfil, 'tipo_nee', '') if perfil else '',
            'Sí' if perfil and perfil.requiere_pie else 'No',
            getattr(perfil, 'fecha_ingreso', '') if perfil else '',
            getattr(perfil, 'telefono_movil', '') if perfil else '',
        ])

    logger.info(f'Exportación estudiantes — user={user.email} colegio={school_id}')
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_profesores(request):
    """
    GET /api/exportacion/profesores/
    Exporta listado de profesores del colegio en CSV.
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores.')

    school_id = _school_id(user)

    rol_profesor = Role.objects.filter(nombre__iexact='Profesor').first()
    if not rol_profesor:
        raise ValidationError({'detail': 'Rol de profesor no configurado.'})

    qs = User.objects.filter(
        rbd_colegio=school_id,
        role=rol_profesor,
    ).select_related('perfil_profesor').order_by('apellido_paterno', 'nombre')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="profesores_{school_id}_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'RUT', 'Nombre', 'Apellido Paterno', 'Apellido Materno',
        'Email', 'Especialidad', 'Título', 'Universidad',
        'Estado Laboral', 'Horas Contrato', 'Fecha Ingreso',
    ])

    for prof in qs:
        perfil = getattr(prof, 'perfil_profesor', None)
        writer.writerow([
            prof.rut or '',
            prof.nombre or '',
            prof.apellido_paterno or '',
            prof.apellido_materno or '',
            prof.email or '',
            getattr(perfil, 'especialidad', '') if perfil else '',
            getattr(perfil, 'titulo_profesional', '') if perfil else '',
            getattr(perfil, 'universidad', '') if perfil else '',
            getattr(perfil, 'estado_laboral', '') if perfil else '',
            getattr(perfil, 'horas_semanales_contrato', '') if perfil else '',
            getattr(perfil, 'fecha_ingreso', '') if perfil else '',
        ])

    logger.info(f'Exportación profesores — user={user.email} colegio={school_id}')
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_reporte_academico(request):
    """
    GET /api/exportacion/reporte-academico/
    Exporta reporte de rendimiento académico de una clase en CSV.

    Query params: ?clase_id=5&ciclo_id=1
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores.')

    school_id = _school_id(user)
    clase_id_raw = request.query_params.get('clase_id')
    if not clase_id_raw:
        raise ValidationError({'clase_id': 'Requerido.'})
    clase_id = _parse_positive_int(clase_id_raw, 'clase_id')

    from backend.apps.cursos.models import Clase
    from backend.apps.academico.models import Calificacion, Evaluacion

    try:
        clase = Clase.objects.select_related('curso', 'asignatura').get(
            id=clase_id, curso__ciclo_academico__colegio_id=school_id,
        )
    except Clase.DoesNotExist:
        raise ValidationError({'clase_id': 'Clase no encontrada.'})

    # Obtener evaluaciones y notas
    evaluaciones = Evaluacion.objects.filter(
        clase=clase, activa=True
    ).order_by('fecha_evaluacion')

    from backend.apps.cursos.models import ClaseEstudiante
    estudiantes = ClaseEstudiante.objects.filter(
        clase=clase
    ).select_related('estudiante').order_by(
        'estudiante__apellido_paterno', 'estudiante__nombre'
    )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="reporte_{clase.asignatura.nombre}_{clase.curso.nombre}_{date.today()}.csv"'
    )

    writer = csv.writer(response)

    # Header: Estudiante + cada evaluación + Promedio
    header = ['RUT', 'Nombre Completo']
    for ev in evaluaciones:
        header.append(f'{ev.nombre} ({ev.fecha_evaluacion})')
    header.append('Promedio')
    writer.writerow(header)

    for ce in estudiantes:
        est = ce.estudiante
        row = [est.rut or '', est.get_full_name()]

        notas = []
        for ev in evaluaciones:
            cal = Calificacion.objects.filter(
                evaluacion=ev, estudiante=est,
            ).first()
            nota = float(cal.nota) if cal else ''
            row.append(nota)
            if cal:
                notas.append(float(cal.nota))

        promedio = round(sum(notas) / len(notas), 1) if notas else ''
        row.append(promedio)
        writer.writerow(row)

    logger.info(f'Exportación reporte académico — clase={clase_id} user={user.email}')
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_asistencia(request):
    """
    GET /api/exportacion/asistencia/
    Exporta reporte de asistencia de una clase en CSV.

    Query params: ?clase_id=5&mes=4&anio=2026
    """
    user = request.user
    if not _is_admin(user):
        raise PermissionDenied('Solo administradores.')

    school_id = _school_id(user)
    clase_id_raw = request.query_params.get('clase_id')
    if not clase_id_raw:
        raise ValidationError({'clase_id': 'Requerido.'})
    clase_id = _parse_positive_int(clase_id_raw, 'clase_id')

    mes_raw = request.query_params.get('mes')
    anio_raw = request.query_params.get('anio')

    mes = None
    if mes_raw is not None and mes_raw != '':
        mes = _parse_positive_int(mes_raw, 'mes')
        if mes < 1 or mes > 12:
            raise ValidationError({'mes': 'Debe estar entre 1 y 12.'})

    anio = date.today().year
    if anio_raw is not None and anio_raw != '':
        anio = _parse_positive_int(anio_raw, 'anio')

    from backend.apps.cursos.models import Clase, ClaseEstudiante
    from backend.apps.academico.models import Asistencia

    try:
        clase = Clase.objects.select_related('curso', 'asignatura').get(
            id=clase_id, curso__ciclo_academico__colegio_id=school_id,
        )
    except Clase.DoesNotExist:
        raise ValidationError({'clase_id': 'Clase no encontrada.'})

    estudiantes = ClaseEstudiante.objects.filter(
        clase=clase
    ).select_related('estudiante').order_by(
        'estudiante__apellido_paterno', 'estudiante__nombre'
    )

    att_qs = Asistencia.objects.filter(clase=clase)
    if mes:
        att_qs = att_qs.filter(fecha__month=mes, fecha__year=anio)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="asistencia_{clase.asignatura.nombre}_{clase.curso.nombre}_{date.today()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'RUT', 'Nombre', 'Total Clases', 'Presente', 'Ausente',
        'Justificado', 'Tardanza', '% Asistencia',
    ])

    for ce in estudiantes:
        est = ce.estudiante
        att_est = att_qs.filter(estudiante=est)
        total = att_est.count()
        presente = att_est.filter(estado='P').count()
        ausente = att_est.filter(estado='A').count()
        justificado = att_est.filter(estado='J').count()
        tardanza = att_est.filter(estado='T').count()
        pct = round((presente / total) * 100, 1) if total else 0

        writer.writerow([
            est.rut or '', est.get_full_name(),
            total, presente, ausente, justificado, tardanza, f'{pct}%',
        ])

    logger.info(f'Exportación asistencia — clase={clase_id} user={user.email}')
    return response

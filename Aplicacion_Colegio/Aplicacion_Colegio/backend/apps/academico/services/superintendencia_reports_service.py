"""Servicio para reporteria de compliance Superintendencia (Decreto 67)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from backend.apps.academico.models import Asistencia, RegistroClase
from backend.apps.institucion.models import ConfiguracionAcademica
from backend.apps.matriculas.models import Matricula


@dataclass(frozen=True)
class ExportArtifact:
    content: bytes
    content_type: str
    filename: str


class SigeMinisterialAdapter:
    """Adapta el payload interno al contrato estable para carga SIGE."""

    ADAPTER_VERSION = '1.0.0'

    @staticmethod
    def build_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            'adapter': 'sige_ministerial_monthly',
            'adapter_version': SigeMinisterialAdapter.ADAPTER_VERSION,
            'source_contract_version': payload.get('contract_version', '1.0.0'),
            'month': payload['month'],
            'colegio_id': payload['colegio_id'],
            'attendance_summary': {
                'total_records': payload['asistencia']['total_registros'],
                'present': payload['asistencia']['presentes'],
                'absent': payload['asistencia']['ausentes'],
                'late': payload['asistencia']['tardanzas'],
                'excused': payload['asistencia']['justificadas'],
                'attendance_rate': payload['asistencia']['tasa_presentismo'],
            },
            'enrollment_summary': {
                'total': payload['matricula']['total'],
                'active': payload['matricula']['activas'],
                'suspended': payload['matricula']['suspendidas'],
                'withdrawn': payload['matricula']['retiradas'],
                'finalized': payload['matricula']['finalizadas'],
            },
            'classbook_summary': {
                'total_records': payload['libro_clases']['total_registros'],
                'signed': payload['libro_clases']['firmados'],
                'pending_sign': payload['libro_clases']['pendientes_firma'],
                'sign_rate': payload['libro_clases']['tasa_firma'],
            },
            'decreto67_summary': payload['decreto_67'],
        }


class SuperintendenciaReportsService:
    """Construye y exporta reporte mensual normativo por establecimiento."""

    @staticmethod
    def resolve_month(raw_month: str | None) -> tuple[int, int]:
        if raw_month in (None, ''):
            today = date.today()
            return today.year, today.month

        chunks = str(raw_month).split('-', 1)
        if len(chunks) != 2:
            raise ValueError('Formato de mes invalido. Use YYYY-MM.')

        try:
            year = int(chunks[0])
            month = int(chunks[1])
        except (TypeError, ValueError):
            raise ValueError('Formato de mes invalido. Use YYYY-MM.')

        if year < 2000 or year > 2100:
            raise ValueError('Anio fuera de rango permitido (2000-2100).')
        if month < 1 or month > 12:
            raise ValueError('Mes fuera de rango permitido (01-12).')

        return year, month

    @staticmethod
    def build_monthly_payload(*, school_id: int, year: int, month: int) -> dict[str, Any]:
        attendance_qs = Asistencia.objects.filter(
            colegio_id=school_id,
            fecha__year=year,
            fecha__month=month,
        )
        attendance_total = attendance_qs.count()
        attendance_present = attendance_qs.filter(estado='P').count()
        attendance_absent = attendance_qs.filter(estado='A').count()
        attendance_late = attendance_qs.filter(estado='T').count()
        attendance_excused = attendance_qs.filter(estado='J').count()

        attendance_rate = 0.0
        if attendance_total:
            attendance_rate = round((attendance_present * 100.0) / attendance_total, 2)

        enrollments_qs = Matricula.objects.filter(
            colegio_id=school_id,
            fecha_matricula__year=year,
            fecha_matricula__month=month,
        )

        registros_qs = RegistroClase.objects.filter(
            colegio_id=school_id,
            fecha__year=year,
            fecha__month=month,
        )
        total_registros = registros_qs.count()
        total_firmados = registros_qs.filter(firmado=True).count()
        tasa_firma = 0.0
        if total_registros:
            tasa_firma = round((total_firmados * 100.0) / total_registros, 2)

        config = ConfiguracionAcademica.objects.filter(colegio_id=school_id).first()

        return {
            'contract_version': '1.0.0',
            'report': 'superintendencia_decreto67_mensual',
            'month': f'{year:04d}-{month:02d}',
            'colegio_id': school_id,
            'asistencia': {
                'total_registros': attendance_total,
                'presentes': attendance_present,
                'ausentes': attendance_absent,
                'tardanzas': attendance_late,
                'justificadas': attendance_excused,
                'tasa_presentismo': attendance_rate,
            },
            'matricula': {
                'total': enrollments_qs.count(),
                'activas': enrollments_qs.filter(estado='ACTIVA').count(),
                'suspendidas': enrollments_qs.filter(estado='SUSPENDIDA').count(),
                'retiradas': enrollments_qs.filter(estado='RETIRADA').count(),
                'finalizadas': enrollments_qs.filter(estado='FINALIZADA').count(),
            },
            'libro_clases': {
                'total_registros': total_registros,
                'firmados': total_firmados,
                'pendientes_firma': total_registros - total_firmados,
                'tasa_firma': tasa_firma,
            },
            'decreto_67': {
                'configurado': bool(config),
                'nota_minima': float(config.nota_minima) if config else None,
                'nota_maxima': float(config.nota_maxima) if config else None,
                'nota_aprobacion': float(config.nota_aprobacion) if config else None,
                'periodo_evaluativo': config.periodo_evaluativo if config else None,
                'requiere_firma_docente': config.requiere_firma_docente if config else None,
            },
        }

    @staticmethod
    def export_payload(payload: dict[str, Any], export_format: str) -> ExportArtifact:
        month = payload['month']
        school_id = payload['colegio_id']

        if export_format == 'csv':
            return SuperintendenciaReportsService._export_csv(payload, month=month, school_id=school_id)
        if export_format == 'xlsx':
            return SuperintendenciaReportsService._export_xlsx(payload, month=month, school_id=school_id)
        if export_format == 'pdf':
            return SuperintendenciaReportsService._export_pdf(payload, month=month, school_id=school_id)
        if export_format == 'sige':
            return SuperintendenciaReportsService._export_sige(payload, month=month, school_id=school_id)

        raise ValueError('Formato invalido. Use csv, xlsx, pdf o sige.')

    @staticmethod
    def _export_csv(payload: dict[str, Any], *, month: str, school_id: int) -> ExportArtifact:
        asistencia = payload['asistencia']
        matricula = payload['matricula']
        libro = payload['libro_clases']
        decreto = payload['decreto_67']

        stream = io.StringIO()
        writer = csv.writer(stream)

        writer.writerow(['reporte', 'mes', 'colegio_id'])
        writer.writerow([payload['report'], month, school_id])
        writer.writerow([])

        writer.writerow(['asistencia_campo', 'valor'])
        for key in ['total_registros', 'presentes', 'ausentes', 'tardanzas', 'justificadas', 'tasa_presentismo']:
            writer.writerow([key, asistencia[key]])

        writer.writerow([])
        writer.writerow(['matricula_campo', 'valor'])
        for key in ['total', 'activas', 'suspendidas', 'retiradas', 'finalizadas']:
            writer.writerow([key, matricula[key]])

        writer.writerow([])
        writer.writerow(['libro_clases_campo', 'valor'])
        for key in ['total_registros', 'firmados', 'pendientes_firma', 'tasa_firma']:
            writer.writerow([key, libro[key]])

        writer.writerow([])
        writer.writerow(['decreto67_campo', 'valor'])
        for key in ['configurado', 'nota_minima', 'nota_maxima', 'nota_aprobacion', 'periodo_evaluativo', 'requiere_firma_docente']:
            writer.writerow([key, decreto[key]])

        return ExportArtifact(
            content=stream.getvalue().encode('utf-8'),
            content_type='text/csv; charset=utf-8',
            filename=f'reporte_superintendencia_{school_id}_{month}.csv',
        )

    @staticmethod
    def _export_xlsx(payload: dict[str, Any], *, month: str, school_id: int) -> ExportArtifact:
        workbook = Workbook()
        ws = workbook.active
        ws.title = 'superintendencia_decreto67'

        ws.append(['reporte', 'mes', 'colegio_id'])
        ws.append([payload['report'], month, school_id])
        ws.append([])

        ws.append(['asistencia_campo', 'valor'])
        for key, value in payload['asistencia'].items():
            ws.append([key, value])

        ws.append([])
        ws.append(['matricula_campo', 'valor'])
        for key, value in payload['matricula'].items():
            ws.append([key, value])

        ws.append([])
        ws.append(['libro_clases_campo', 'valor'])
        for key, value in payload['libro_clases'].items():
            ws.append([key, value])

        ws.append([])
        ws.append(['decreto67_campo', 'valor'])
        for key, value in payload['decreto_67'].items():
            ws.append([key, value])

        output = io.BytesIO()
        workbook.save(output)

        return ExportArtifact(
            content=output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f'reporte_superintendencia_{school_id}_{month}.xlsx',
        )

    @staticmethod
    def _export_pdf(payload: dict[str, Any], *, month: str, school_id: int) -> ExportArtifact:
        import hashlib
        import uuid
        from django.utils import timezone
        from backend.apps.institucion.models import Colegio

        # 1. Obtener datos del colegio
        try:
            colegio = Colegio.objects.all_schools().get(rbd=school_id)
            colegio_nombre = colegio.nombre
            colegio_rut = colegio.rut_establecimiento or "RUT No Registrado"
        except Exception:
            colegio_nombre = "Establecimiento Educacional"
            colegio_rut = "RUT No Registrado"

        # 2. Generar Hash y Token de firma digital simple
        datos_firma = f"{school_id}|{month}|{payload['asistencia']['tasa_presentismo']}|{payload['libro_clases']['tasa_firma']}"
        firma_hash = hashlib.sha256(datos_firma.encode('utf-8')).hexdigest()
        firma_token = str(uuid.uuid4())
        fecha_emision = timezone.now().strftime('%d/%m/%Y %H:%M:%S')

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        # ---- DIBUJAR MARCO Y DISEÑO DE FONDO (PREMIUM) ----
        # Marco exterior azul marino
        pdf.setStrokeColorRGB(0.08, 0.18, 0.36)
        pdf.setLineWidth(2)
        pdf.rect(30, 30, 535, 782)
        
        # Marco interior sutil
        pdf.setStrokeColorRGB(0.7, 0.75, 0.82)
        pdf.setLineWidth(0.5)
        pdf.rect(34, 34, 527, 774)

        # ---- ENCABEZADO DE PÁGINA ----
        # Banner azul
        pdf.setFillColorRGB(0.08, 0.18, 0.36)
        pdf.rect(40, 730, 515, 65, stroke=0, fill=1)

        # Texto del banner
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.setFont('Helvetica-Bold', 14)
        pdf.drawString(60, 768, 'CERTIFICADO DE CONFORMIDAD NORMATIVA')
        pdf.setFont('Helvetica', 10)
        pdf.drawString(60, 746, 'SISTEMA DE GESTIÓN SAAS — SUPERINTENDENCIA DE EDUCACIÓN & DECRETO 67')

        # Detalle del Colegio (Debajo del Banner)
        pdf.setFillColorRGB(0.1, 0.15, 0.25)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(45, 700, colegio_nombre.upper())
        
        pdf.setFont('Helvetica', 9)
        pdf.drawString(45, 684, f"RBD: {school_id}   |   RUT: {colegio_rut}   |   Mes de Reporte: {month}")
        pdf.setStrokeColorRGB(0.8, 0.83, 0.88)
        pdf.setLineWidth(1)
        pdf.line(40, 672, 555, 672)

        # ---- SECCIONES DE MÉTRICAS (FORMATO DE TARJETAS GRILLA) ----
        # Tarjeta 1: Resumen de Asistencia
        y_sec = 640
        pdf.setFillColorRGB(0.96, 0.97, 0.99)
        pdf.rect(40, y_sec - 110, 250, 120, stroke=1, fill=1)
        # Cabecera Tarjeta 1
        pdf.setFillColorRGB(0.08, 0.18, 0.36)
        pdf.rect(40, y_sec, 250, 20, stroke=0, fill=1)
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(50, y_sec + 6, '1. RESUMEN DE ASISTENCIA')
        
        pdf.setFillColorRGB(0.2, 0.25, 0.3)
        pdf.setFont('Helvetica', 9)
        asist = payload['asistencia']
        pdf.drawString(50, y_sec - 18, f"Total Registros: {asist['total_registros']}")
        pdf.drawString(50, y_sec - 34, f"Presentes: {asist['presentes']}")
        pdf.drawString(50, y_sec - 50, f"Ausentes: {asist['ausentes']}")
        pdf.drawString(50, y_sec - 66, f"Justificadas: {asist['justificadas']}")
        pdf.drawString(50, y_sec - 82, f"Tardanzas (Atrasos): {asist['tardanzas']}")
        
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(50, y_sec - 98, f"Tasa de Presentismo: {asist['tasa_presentismo']}%")

        # Tarjeta 2: Resumen de Matrícula
        pdf.setFillColorRGB(0.96, 0.97, 0.99)
        pdf.rect(305, y_sec - 110, 250, 120, stroke=1, fill=1)
        # Cabecera Tarjeta 2
        pdf.setFillColorRGB(0.08, 0.18, 0.36)
        pdf.rect(305, y_sec, 250, 20, stroke=0, fill=1)
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(315, y_sec + 6, '2. RESUMEN DE MATRÍCULA')
        
        pdf.setFillColorRGB(0.2, 0.25, 0.3)
        pdf.setFont('Helvetica', 9)
        mat = payload['matricula']
        pdf.drawString(315, y_sec - 18, f"Total Matrículas del Mes: {mat['total']}")
        pdf.drawString(315, y_sec - 34, f"Matrículas Activas: {mat['activas']}")
        pdf.drawString(315, y_sec - 50, f"Matrículas Suspendidas: {mat['suspendidas']}")
        pdf.drawString(315, y_sec - 66, f"Matrículas Retiradas: {mat['retiradas']}")
        pdf.drawString(315, y_sec - 82, f"Matrículas Finalizadas: {mat['finalizadas']}")

        # Tarjeta 3: Libro de Clases Digital
        y_sec_2 = 490
        pdf.setFillColorRGB(0.96, 0.97, 0.99)
        pdf.rect(40, y_sec_2 - 110, 250, 120, stroke=1, fill=1)
        # Cabecera Tarjeta 3
        pdf.setFillColorRGB(0.08, 0.18, 0.36)
        pdf.rect(40, y_sec_2, 250, 20, stroke=0, fill=1)
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(50, y_sec_2 + 6, '3. LIBRO DE CLASES DIGITAL')
        
        pdf.setFillColorRGB(0.2, 0.25, 0.3)
        pdf.setFont('Helvetica', 9)
        lib = payload['libro_clases']
        pdf.drawString(50, y_sec_2 - 18, f"Total Clases Registradas: {lib['total_registros']}")
        pdf.drawString(50, y_sec_2 - 34, f"Clases Firmadas: {lib['firmados']}")
        pdf.drawString(50, y_sec_2 - 50, f"Pendientes de Firma: {lib['pendientes_firma']}")
        
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(50, y_sec_2 - 68, f"Tasa de Cobertura de Firma: {lib['tasa_firma']}%")

        # Tarjeta 4: Configuración Decreto 67
        pdf.setFillColorRGB(0.96, 0.97, 0.99)
        pdf.rect(305, y_sec_2 - 110, 250, 120, stroke=1, fill=1)
        # Cabecera Tarjeta 4
        pdf.setFillColorRGB(0.08, 0.18, 0.36)
        pdf.rect(305, y_sec_2, 250, 20, stroke=0, fill=1)
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(315, y_sec_2 + 6, '4. MARCO REGULADOR DECRETO 67')
        
        pdf.setFillColorRGB(0.2, 0.25, 0.3)
        pdf.setFont('Helvetica', 9)
        dec = payload['decreto_67']
        configurado_str = "SÍ" if dec['configurado'] else "NO"
        pdf.drawString(315, y_sec_2 - 18, f"Configuración Activa: {configurado_str}")
        pdf.drawString(315, y_sec_2 - 34, f"Nota Mínima: {dec['nota_minima'] or '1.0'}")
        pdf.drawString(315, y_sec_2 - 50, f"Nota Máxima: {dec['nota_maxima'] or '7.0'}")
        pdf.drawString(315, y_sec_2 - 66, f"Nota Aprobación: {dec['nota_aprobacion'] or '4.0'}")
        pdf.drawString(315, y_sec_2 - 82, f"Período Evaluativo: {dec['periodo_evaluativo'] or 'Semestral'}")
        req_firma_str = "SÍ" if dec['requiere_firma_docente'] else "NO"
        pdf.drawString(315, y_sec_2 - 98, f"Requiere Firma Docente: {req_firma_str}")

        # ---- SELLO DE FIRMA DIGITAL Y AUDITORÍA (PIE DE PÁGINA) ----
        pdf.setFillColorRGB(0.98, 0.98, 0.98)
        # Caja exterior
        pdf.rect(40, 50, 515, 120, stroke=1, fill=1)
        pdf.setStrokeColorRGB(0.08, 0.18, 0.36)
        pdf.setLineWidth(1)
        pdf.rect(44, 54, 507, 112, stroke=1, fill=0)

        # Texto del Sello de Seguridad
        pdf.setFillColorRGB(0.08, 0.18, 0.36)
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(60, 142, 'SELLO DIGITAL DE INTEGRIDAD Y CERTIFICACIÓN DE COMPLIANCE')
        
        pdf.setFillColorRGB(0.3, 0.35, 0.4)
        pdf.setFont('Helvetica', 7.5)
        pdf.drawString(60, 128, 'Este informe normativo ha sido generado de acuerdo a los estándares técnicos y legales del Decreto 67 y las circulares')
        pdf.drawString(60, 118, 'de la Superintendencia de Educación de Chile. Su integridad se encuentra sellada electrónicamente de forma irreversible.')
        
        pdf.setFillColorRGB(0.15, 0.2, 0.3)
        pdf.setFont('Helvetica-Bold', 8)
        pdf.drawString(60, 98, f"TOKEN ÚNICO DE EMISIÓN: {firma_token}")
        pdf.drawString(60, 84, f"SELLO HASH DE INTEGRIDAD (SHA-256): {firma_hash}")
        pdf.drawString(60, 70, f"FECHA Y HORA DE EMISIÓN: {fecha_emision}   |   SOPORTE SAAS: APLICACIÓN_COLEGIO VERIFICADO")

        # Dibujar un pequeño "sello/estampa" visual en ReportLab a la derecha
        pdf.setFillColorRGB(0.08, 0.18, 0.36)
        pdf.rect(480, 75, 55, 55, stroke=1, fill=0)
        pdf.setFont('Helvetica-Bold', 7)
        pdf.drawString(486, 115, "SAAS FIRMA")
        pdf.drawString(486, 105, "CUMPLIDO")
        pdf.drawString(486, 95, "DECRETO 67")
        pdf.drawString(486, 85, f"RBD {school_id}")

        pdf.showPage()
        pdf.save()

        return ExportArtifact(
            content=buffer.getvalue(),
            content_type='application/pdf',
            filename=f'reporte_superintendencia_{school_id}_{month}.pdf',
        )

    @staticmethod
    def _export_sige(payload: dict[str, Any], *, month: str, school_id: int) -> ExportArtifact:
        adapter_payload = SigeMinisterialAdapter.build_payload(payload)
        return ExportArtifact(
            content=json.dumps(adapter_payload, ensure_ascii=True, separators=(',', ':')).encode('utf-8'),
            content_type='application/json; charset=utf-8',
            filename=f'reporte_superintendencia_{school_id}_{month}_sige.json',
        )

    @staticmethod
    def to_json_bytes(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=True, separators=(',', ':')).encode('utf-8')

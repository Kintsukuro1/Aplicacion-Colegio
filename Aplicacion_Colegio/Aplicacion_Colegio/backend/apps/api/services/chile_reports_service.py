from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, Tuple

from openpyxl import Workbook
from rest_framework.exceptions import PermissionDenied, ValidationError

from backend.apps.academico.models import Asistencia
from backend.apps.matriculas.models import Matricula


@dataclass(frozen=True)
class ExportArtifact:
    content: bytes
    content_type: str
    filename: str


class SigeMinisterialAdapter:
    """Builds a stable payload contract for SIGE monthly upload automation."""

    ADAPTER_VERSION = '1.0.0'

    @staticmethod
    def build_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        month = payload['month']
        school_id = payload['colegio_id']
        attendance = payload['asistencia']
        enrollment = payload['matricula']

        return {
            'adapter': 'sige_ministerial_monthly',
            'adapter_version': SigeMinisterialAdapter.ADAPTER_VERSION,
            'source_contract_version': payload.get('contract_version', '1.0.0'),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'month': month,
            'colegio_id': school_id,
            'attendance_summary': {
                'total_records': attendance['total_registros'],
                'present': attendance['presentes'],
                'absent': attendance['ausentes'],
                'late': attendance['tardanzas'],
                'excused': attendance['justificadas'],
                'attendance_rate': attendance['tasa_presentismo'],
            },
            'enrollment_summary': {
                'total': enrollment['total'],
                'active': enrollment['activas'],
                'suspended': enrollment['suspendidas'],
                'withdrawn': enrollment['retiradas'],
                'finalized': enrollment['finalizadas'],
            },
        }


class ChileReportsService:
    @staticmethod
    def resolve_month(raw_month: str | None) -> Tuple[int, int]:
        if raw_month in (None, ''):
            today = date.today()
            return today.year, today.month

        chunks = str(raw_month).split('-', 1)
        if len(chunks) != 2:
            raise ValidationError({'month': 'Formato invalido. Use YYYY-MM.'})

        try:
            year = int(chunks[0])
            month = int(chunks[1])
        except (TypeError, ValueError):
            raise ValidationError({'month': 'Formato invalido. Use YYYY-MM.'})

        if year < 2000 or year > 2100:
            raise ValidationError({'month': 'El anio debe estar entre 2000 y 2100.'})
        if month < 1 or month > 12:
            raise ValidationError({'month': 'El mes debe estar entre 01 y 12.'})

        return year, month

    @staticmethod
    def resolve_school_id(*, user, requested_school_id: str | None, is_global_admin: bool) -> int:
        school_id = requested_school_id
        if school_id is None:
            school_id = getattr(user, 'rbd_colegio', None)

        if school_id is None:
            raise ValidationError({'colegio_id': 'Usuario sin colegio asignado.'})

        try:
            school_id = int(school_id)
        except (TypeError, ValueError):
            raise ValidationError({'colegio_id': 'Debe ser un entero valido.'})

        if not is_global_admin and getattr(user, 'rbd_colegio', None) != school_id:
            raise PermissionDenied('No puede consultar reportes de otro colegio.')

        return school_id

    @staticmethod
    def build_ministerial_monthly_payload(*, school_id: int, year: int, month: int) -> Dict[str, Any]:
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

        return {
            'contract_version': '1.0.0',
            'report': 'ministerial_monthly',
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
        }

    @staticmethod
    def export_payload(payload: Dict[str, Any], export_format: str) -> ExportArtifact:
        month = payload['month']
        school_id = payload['colegio_id']
        if export_format == 'csv':
            return ChileReportsService._export_csv(payload, month=month, school_id=school_id)
        if export_format == 'xlsx':
            return ChileReportsService._export_xlsx(payload, month=month, school_id=school_id)
        if export_format == 'sige':
            return ChileReportsService._export_sige(payload, month=month, school_id=school_id)
        raise ValidationError({'format': 'Valor invalido. Use json, csv, xlsx o sige.'})

    @staticmethod
    def _export_csv(payload: Dict[str, Any], *, month: str, school_id: int) -> ExportArtifact:
        attendance = payload['asistencia']
        enrollments = payload['matricula']

        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['reporte', 'mes', 'colegio_id'])
        writer.writerow(['ministerial_monthly', month, school_id])
        writer.writerow([])
        writer.writerow(['asistencia_campo', 'valor'])
        writer.writerow(['total_registros', attendance['total_registros']])
        writer.writerow(['presentes', attendance['presentes']])
        writer.writerow(['ausentes', attendance['ausentes']])
        writer.writerow(['tardanzas', attendance['tardanzas']])
        writer.writerow(['justificadas', attendance['justificadas']])
        writer.writerow(['tasa_presentismo', attendance['tasa_presentismo']])
        writer.writerow([])
        writer.writerow(['matricula_campo', 'valor'])
        writer.writerow(['total', enrollments['total']])
        writer.writerow(['activas', enrollments['activas']])
        writer.writerow(['suspendidas', enrollments['suspendidas']])
        writer.writerow(['retiradas', enrollments['retiradas']])
        writer.writerow(['finalizadas', enrollments['finalizadas']])

        return ExportArtifact(
            content=stream.getvalue().encode('utf-8'),
            content_type='text/csv; charset=utf-8',
            filename=f'reporte_ministerial_{school_id}_{month}.csv',
        )

    @staticmethod
    def _export_xlsx(payload: Dict[str, Any], *, month: str, school_id: int) -> ExportArtifact:
        attendance = payload['asistencia']
        enrollments = payload['matricula']

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'reporte_ministerial'

        worksheet.append(['reporte', 'mes', 'colegio_id'])
        worksheet.append(['ministerial_monthly', month, school_id])
        worksheet.append([])
        worksheet.append(['asistencia_campo', 'valor'])
        worksheet.append(['total_registros', attendance['total_registros']])
        worksheet.append(['presentes', attendance['presentes']])
        worksheet.append(['ausentes', attendance['ausentes']])
        worksheet.append(['tardanzas', attendance['tardanzas']])
        worksheet.append(['justificadas', attendance['justificadas']])
        worksheet.append(['tasa_presentismo', attendance['tasa_presentismo']])
        worksheet.append([])
        worksheet.append(['matricula_campo', 'valor'])
        worksheet.append(['total', enrollments['total']])
        worksheet.append(['activas', enrollments['activas']])
        worksheet.append(['suspendidas', enrollments['suspendidas']])
        worksheet.append(['retiradas', enrollments['retiradas']])
        worksheet.append(['finalizadas', enrollments['finalizadas']])

        output = io.BytesIO()
        workbook.save(output)
        return ExportArtifact(
            content=output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f'reporte_ministerial_{school_id}_{month}.xlsx',
        )

    @staticmethod
    def _export_sige(payload: Dict[str, Any], *, month: str, school_id: int) -> ExportArtifact:
        adapter_payload = SigeMinisterialAdapter.build_payload(payload)
        return ExportArtifact(
            content=json.dumps(adapter_payload, ensure_ascii=True, separators=(',', ':')).encode('utf-8'),
            content_type='application/json; charset=utf-8',
            filename=f'reporte_ministerial_{school_id}_{month}_sige.json',
        )

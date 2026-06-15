from __future__ import annotations

from decimal import Decimal

from backend.apps.auditoria.models import AuditoriaEvento
from backend.apps.matriculas.models import Beca, Boleta


class FinancialDocumentsService:
    @staticmethod
    def create_beca(*, user, matricula, data: dict, fecha_inicio, fecha_fin, ip_address=None, user_agent=None):
        beca = Beca.objects.create(
            estudiante=matricula.estudiante,
            matricula=matricula,
            tipo=data['tipo_beca'],
            porcentaje_descuento=Decimal(str(data['porcentaje_descuento'])),
            motivo=data['motivo_solicitud'],
            descripcion=data.get('observaciones', ''),
            aplica_matricula=data.get('aplica_matricula', True),
            aplica_mensualidad=data.get('aplica_mensualidad', True),
            aplica_otros_aranceles=data.get('aplica_otros_aranceles', False),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=data.get('estado', 'SOLICITADA'),
        )

        AuditoriaEvento.objects.create(
            usuario=user,
            accion='CREATE',
            categoria='estudiantes',
            tabla_afectada='Beca',
            descripcion=(
                f"Beca creada para estudiante {matricula.estudiante.get_full_name()} "
                f"(RUT: {matricula.estudiante.rut}) - Tipo: {beca.get_tipo_display()} "
                f"- Porcentaje: {beca.porcentaje_descuento}%"
            ),
            ip_address=ip_address,
            user_agent=user_agent,
            nivel='info',
        )
        return beca

    @staticmethod
    def create_boleta(*, user, estudiante, pago, numero_boleta: str, monto_total, detalle='', ip_address=None, user_agent=None):
        """Crea boleta consistente con el modelo (requiere pago asociado)."""
        boleta = Boleta.objects.create(
            estudiante=estudiante,
            pago=pago,
            numero_boleta=numero_boleta,
            monto_total=Decimal(str(monto_total)),
            detalle=detalle,
            estado='EMITIDA',
        )

        AuditoriaEvento.objects.create(
            usuario=user,
            accion='CREATE',
            categoria='estudiantes',
            tabla_afectada='Boleta',
            descripcion=(
                f"Boleta creada para estudiante {estudiante.get_full_name()} "
                f"(RUT: {estudiante.rut}) - Monto: ${boleta.monto_total} "
                f"- Número: {boleta.numero_boleta}"
            ),
            ip_address=ip_address,
            user_agent=user_agent,
            nivel='info',
        )

        return boleta

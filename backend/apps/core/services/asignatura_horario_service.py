from __future__ import annotations

from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.cursos.models import Asignatura, BloqueHorario


class AsignaturaHorarioService:
    @classmethod
    def create_asignatura(cls, *, school_rbd: int, nombre: str, codigo: str | None, horas_semanales: int):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='ASIGNATURA_CREATE',
        )
        return Asignatura.objects.create(
            colegio_id=school_rbd,
            nombre=nombre,
            codigo=codigo,
            horas_semanales=horas_semanales,
        )

    @classmethod
    def upsert_bloque(
        cls,
        *,
        school_rbd: int,
        colegio,
        clase,
        dia_semana: int,
        bloque_numero: int,
        hora_inicio,
        hora_fin,
    ):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='BLOQUE_HORARIO_UPSERT',
        )

        bloque, created = BloqueHorario.objects.get_or_create(
            colegio=colegio,
            dia_semana=dia_semana,
            bloque_numero=bloque_numero,
            clase=clase,
            defaults={
                'hora_inicio': hora_inicio,
                'hora_fin': hora_fin,
                'activo': True,
            }
        )
        if not created:
            bloque.hora_inicio = hora_inicio
            bloque.hora_fin = hora_fin
            bloque.activo = True
            bloque.save()

        return bloque, created

    @classmethod
    def create_bloque(
        cls,
        *,
        school_rbd: int,
        colegio,
        clase,
        dia_semana: int,
        bloque_numero: int,
        hora_inicio,
        hora_fin,
    ):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='BLOQUE_HORARIO_CREATE',
        )

        return BloqueHorario.objects.create(
            colegio=colegio,
            clase=clase,
            dia_semana=dia_semana,
            bloque_numero=bloque_numero,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            activo=True,
        )

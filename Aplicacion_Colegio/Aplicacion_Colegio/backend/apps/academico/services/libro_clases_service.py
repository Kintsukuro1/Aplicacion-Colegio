"""Servicio de dominio para libro de clases digital."""

from __future__ import annotations

from datetime import date
from typing import Optional

from django.core.exceptions import ValidationError

from backend.apps.academico.models import RegistroClase
from backend.apps.cursos.models import Clase


class LibroClasesService:
    """Orquesta operaciones de registro y firma del libro de clases."""

    @staticmethod
    def _get_clase_profesor(*, clase_id: int, colegio_id: int, profesor_id: int) -> Clase:
        return Clase.objects.select_related('colegio', 'curso', 'asignatura').get(
            id=clase_id,
            colegio_id=colegio_id,
            profesor_id=profesor_id,
            activo=True,
        )

    @staticmethod
    def upsert_registro_profesor(
        *,
        user,
        colegio_id: int,
        clase_id: int,
        fecha: date,
        numero_clase: int,
        contenido_tratado: str,
        tarea_asignada: str = '',
        observaciones: str = '',
    ) -> tuple[RegistroClase, bool]:
        clase = LibroClasesService._get_clase_profesor(
            clase_id=clase_id,
            colegio_id=colegio_id,
            profesor_id=user.id,
        )

        registro, created = RegistroClase.objects.get_or_create(
            colegio_id=colegio_id,
            clase=clase,
            fecha=fecha,
            numero_clase=numero_clase,
            defaults={
                'profesor': user,
                'contenido_tratado': contenido_tratado,
                'tarea_asignada': tarea_asignada,
                'observaciones': observaciones,
            },
        )

        if not created:
            if registro.firmado:
                raise ValidationError('No se puede editar un registro ya firmado.')

            registro.contenido_tratado = contenido_tratado
            registro.tarea_asignada = tarea_asignada
            registro.observaciones = observaciones
            registro.save(
                update_fields=[
                    'contenido_tratado',
                    'tarea_asignada',
                    'observaciones',
                    'fecha_actualizacion',
                ]
            )

        return registro, created

    @staticmethod
    def firmar_registro_profesor(
        *,
        user,
        colegio_id: int,
        registro_id: int,
        ip_address: str = '',
        user_agent: str = '',
    ) -> RegistroClase:
        registro = RegistroClase.objects.select_related('clase').get(
            id_registro=registro_id,
            colegio_id=colegio_id,
            clase__profesor_id=user.id,
        )
        registro.firmar(profesor=user, ip_address=ip_address, user_agent=user_agent)
        return registro

    @staticmethod
    def get_registro(
        *,
        colegio_id: int,
        registro_id: int,
        profesor_id: Optional[int] = None,
    ) -> RegistroClase:
        filters = {
            'id_registro': registro_id,
            'colegio_id': colegio_id,
        }
        if profesor_id is not None:
            filters['clase__profesor_id'] = profesor_id

        return RegistroClase.objects.select_related(
            'clase',
            'clase__curso',
            'clase__asignatura',
            'profesor',
        ).get(**filters)

    @staticmethod
    def list_registros(
        *,
        colegio_id: int,
        clase_id: Optional[int] = None,
        fecha: Optional[date] = None,
        profesor_id: Optional[int] = None,
        limit: int = 100,
    ):
        qs = RegistroClase.objects.select_related(
            'clase',
            'clase__curso',
            'clase__asignatura',
            'profesor',
        ).filter(colegio_id=colegio_id)

        if clase_id is not None:
            qs = qs.filter(clase_id=clase_id)
        if fecha is not None:
            qs = qs.filter(fecha=fecha)
        if profesor_id is not None:
            qs = qs.filter(clase__profesor_id=profesor_id)

        return qs.order_by('-fecha', '-numero_clase')[:limit]

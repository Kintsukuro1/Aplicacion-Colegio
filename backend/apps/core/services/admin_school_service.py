from __future__ import annotations

from django.db import transaction

from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.cursos.models import Clase, Curso
from backend.apps.institucion.models import CicloAcademico, Colegio, NivelEducativo
from backend.common.constants import (
    CICLO_ESTADO_ACTIVO,
    CICLO_ESTADO_CERRADO,
    CICLO_ESTADO_PLANIFICACION,
)
from backend.common.exceptions import PrerequisiteException


class AdminSchoolService:
    @staticmethod
    def _validate_integrity_with_allowed_errors(*, school_rbd: int, action: str, allowed_errors: tuple[str, ...] = ()):
        report = IntegrityService.get_school_integrity_report(school_rbd)
        disallowed_errors = [
            error
            for error in report.get('errors', [])
            if not any(error.startswith(allowed) for allowed in allowed_errors)
        ]

        if disallowed_errors:
            raise PrerequisiteException(
                error_type='DATA_INCONSISTENCY',
                context={
                    'school_id': school_rbd,
                    'action': action,
                    'integrity_errors': disallowed_errors,
                    'message': 'Se detectaron inconsistencias de datos. Corrige la integridad antes de continuar.',
                },
            )

    @staticmethod
    def create_course(*, user, school_rbd: int, nombre: str, nivel_id: int):
        AdminSchoolService._validate_integrity_with_allowed_errors(
            school_rbd=school_rbd,
            action='ADMIN_ESCOLAR_CREATE_CURSO',
            allowed_errors=(
                'No active academic cycle',
                'No courses exist',
            ),
        )

        colegio = Colegio.objects.get(rbd=school_rbd)
        nivel = NivelEducativo.objects.get(id_nivel=nivel_id)

        ciclo_activo = CicloAcademico.objects.filter(
            colegio=colegio,
            estado=CICLO_ESTADO_ACTIVO,
        ).first()

        if ciclo_activo is None:
            raise PrerequisiteException(
                error_type='MISSING_CICLO_ACTIVO',
                context={
                    'colegio_id': school_rbd,
                    'message': 'No existe un ciclo académico activo para crear cursos.',
                    'action': 'Active o cree un ciclo académico antes de continuar.',
                },
            )

        if Curso.objects.filter(
            colegio=colegio,
            nombre=nombre,
            ciclo_academico=ciclo_activo,
        ).exists():
            raise ValueError('Ya existe un curso con ese nombre en el ciclo activo.')

        return Curso.objects.create(
            colegio=colegio,
            nombre=nombre,
            nivel=nivel,
            ciclo_academico=ciclo_activo,
            activo=True,
        )

    @staticmethod
    def create_academic_cycle(
        *,
        user,
        school_rbd: int,
        nombre: str,
        fecha_inicio,
        fecha_fin,
        descripcion: str = '',
        activate: bool = False,
    ):
        AdminSchoolService._validate_integrity_with_allowed_errors(
            school_rbd=school_rbd,
            action='ADMIN_ESCOLAR_CREATE_CICLO',
            allowed_errors=(
                'No active academic cycle',
                'No courses exist',
            ),
        )

        colegio = Colegio.objects.get(rbd=school_rbd)

        if CicloAcademico.objects.filter(colegio=colegio, nombre=nombre).exists():
            raise ValueError('Ya existe un ciclo académico con ese nombre.')

        estado = CICLO_ESTADO_ACTIVO if activate else CICLO_ESTADO_PLANIFICACION

        return CicloAcademico.objects.create(
            colegio=colegio,
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            descripcion=descripcion,
            estado=estado,
            creado_por=user,
            modificado_por=user,
        )

    @staticmethod
    def activate_academic_cycle(*, user, school_rbd: int, ciclo_id: int):
        AdminSchoolService._validate_integrity_with_allowed_errors(
            school_rbd=school_rbd,
            action='ADMIN_ESCOLAR_ACTIVATE_CICLO',
            allowed_errors=(
                'No active academic cycle',
                'No courses exist',
            ),
        )

        colegio = Colegio.objects.get(rbd=school_rbd)
        ciclo = CicloAcademico.objects.get(id=ciclo_id, colegio=colegio)

        with transaction.atomic():
            CicloAcademico.objects.filter(
                colegio=colegio,
                estado=CICLO_ESTADO_ACTIVO,
            ).exclude(id=ciclo.id).update(
                estado=CICLO_ESTADO_PLANIFICACION,
                modificado_por=user,
            )

            ciclo.estado = CICLO_ESTADO_ACTIVO
            ciclo.modificado_por = user
            ciclo.save(update_fields=['estado', 'modificado_por', 'fecha_modificacion'])

        return ciclo

    @staticmethod
    def close_academic_cycle(*, user, school_rbd: int, ciclo_id: int):
        AdminSchoolService._validate_integrity_with_allowed_errors(
            school_rbd=school_rbd,
            action='ADMIN_ESCOLAR_CLOSE_CICLO',
            allowed_errors=(
                'No active academic cycle',
                'No courses exist',
            ),
        )

        colegio = Colegio.objects.get(rbd=school_rbd)
        ciclo = CicloAcademico.objects.get(id=ciclo_id, colegio=colegio)

        has_active_classes = Clase.objects.filter(
            colegio=colegio,
            curso__ciclo_academico=ciclo,
            activo=True,
        ).exists()
        if has_active_classes:
            raise ValueError('No se puede cerrar el ciclo: existen clases activas asociadas.')

        ciclo.estado = CICLO_ESTADO_CERRADO
        ciclo.modificado_por = user
        ciclo.save(update_fields=['estado', 'modificado_por', 'fecha_modificacion'])
        return ciclo
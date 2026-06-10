from __future__ import annotations

from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.core.services.admin_school_service import AdminSchoolService
from backend.apps.institucion.models import CicloAcademico, Colegio


class CicloAcademicoService:
    @classmethod
    def validations(
        cls,
        *,
        school_rbd: int,
        nombre: str,
        fecha_inicio,
        fecha_fin,
        ciclo_id: int | None = None,
    ):
        if not nombre:
            raise ValueError('Campo requerido: nombre')
        if not fecha_inicio or not fecha_fin:
            raise ValueError('Campos requeridos: fecha_inicio y fecha_fin')
        if fecha_inicio > fecha_fin:
            raise ValueError('La fecha de inicio no puede ser mayor que la fecha de fin.')

        colegio = Colegio.objects.get(rbd=school_rbd)
        ciclos = CicloAcademico.objects.filter(colegio=colegio, nombre=nombre)
        if ciclo_id is not None:
            ciclos = ciclos.exclude(id=ciclo_id)
        if ciclos.exists():
            raise ValueError('Ya existe un ciclo académico con ese nombre.')

    @classmethod
    def create(cls, *, user, school_rbd: int, nombre: str, fecha_inicio, fecha_fin, descripcion: str = '', activate: bool = False):
        IntegrityService.validate_ciclo_creation(school_rbd)
        cls.validations(
            school_rbd=school_rbd,
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        return AdminSchoolService.create_academic_cycle(
            user=user,
            school_rbd=school_rbd,
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            descripcion=descripcion,
            activate=activate,
        )

    @classmethod
    def activate(cls, *, user, school_rbd: int, ciclo_id: int):
        return AdminSchoolService.activate_academic_cycle(
            user=user,
            school_rbd=school_rbd,
            ciclo_id=ciclo_id,
        )

    @classmethod
    def update(cls, *, user, school_rbd: int, ciclo_id: int, nombre: str, fecha_inicio, fecha_fin, descripcion: str = ''):
        cls.validations(
            school_rbd=school_rbd,
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            ciclo_id=ciclo_id,
        )
        IntegrityService.validate_ciclo_update(school_rbd)

        colegio = Colegio.objects.get(rbd=school_rbd)
        ciclo = CicloAcademico.objects.get(id=ciclo_id, colegio=colegio)

        if CicloAcademico.objects.filter(colegio=colegio, nombre=nombre).exclude(id=ciclo.id).exists():
            raise ValueError('Ya existe un ciclo académico con ese nombre.')

        ciclo.nombre = nombre
        ciclo.fecha_inicio = fecha_inicio
        ciclo.fecha_fin = fecha_fin
        ciclo.descripcion = descripcion
        ciclo.modificado_por = user
        ciclo.save()
        return ciclo

    @classmethod
    def get(cls, *, school_rbd: int, ciclo_id: int):
        colegio = Colegio.objects.get(rbd=school_rbd)
        return CicloAcademico.objects.get(id=ciclo_id, colegio=colegio)

    @classmethod
    def delete(cls, *, user, school_rbd: int, ciclo_id: int):
        IntegrityService.validate_ciclo_deletion(school_rbd)

        colegio = Colegio.objects.get(rbd=school_rbd)
        ciclo = CicloAcademico.objects.get(id=ciclo_id, colegio=colegio)

        if ciclo.estado == 'ACTIVO':
            raise ValueError('No se puede eliminar un ciclo activo')

        ciclo.delete()
        return True

    @classmethod
    def close(cls, *, user, school_rbd: int, ciclo_id: int):
        return AdminSchoolService.close_academic_cycle(
            user=user,
            school_rbd=school_rbd,
            ciclo_id=ciclo_id,
        )

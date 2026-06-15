from __future__ import annotations

from django.db import transaction

from backend.apps.accounts.models import PerfilEstudiante, User
from backend.apps.core.services.admin_school_service import AdminSchoolService
from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.cursos.models import Clase, Curso
from backend.apps.institucion.models import Colegio, NivelEducativo


class CursoService:
    @classmethod
    def validations(
        cls,
        *,
        school_rbd: int,
        nombre: str,
        nivel_id: int,
        curso_id: int | None = None,
    ):
        if not nombre:
            raise ValueError('Campo requerido: nombre')

        colegio = Colegio.objects.get(rbd=school_rbd)
        nivel = NivelEducativo.objects.get(id_nivel=nivel_id)

        cursos = Curso.objects.filter(
            colegio=colegio,
            nombre=nombre,
            activo=True,
        )
        if curso_id is not None:
            cursos = cursos.exclude(id_curso=curso_id)
        if cursos.exists():
            raise ValueError('Ya existe un curso activo con ese nombre.')

        return {'colegio': colegio, 'nivel': nivel}

    @classmethod
    def create(cls, *, user, school_rbd: int, nombre: str, nivel_id: int):
        IntegrityService.validate_curso_creation(school_rbd)
        cls.validations(school_rbd=school_rbd, nombre=nombre, nivel_id=nivel_id)
        return AdminSchoolService.create_course(
            user=user,
            school_rbd=school_rbd,
            nombre=nombre,
            nivel_id=nivel_id,
        )

    @classmethod
    def update(cls, *, user, school_rbd: int, curso_id: int, nombre: str, nivel_id: int):
        validated = cls.validations(
            school_rbd=school_rbd,
            nombre=nombre,
            nivel_id=nivel_id,
            curso_id=curso_id,
        )
        IntegrityService.validate_curso_update(school_rbd)

        colegio = validated['colegio']
        curso = Curso.objects.get(id_curso=curso_id, colegio=colegio)
        nivel = validated['nivel']

        if Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=curso.ciclo_academico,
            nombre=nombre,
        ).exclude(id_curso=curso.id_curso).exists():
            raise ValueError('Ya existe un curso con ese nombre en el ciclo actual.')

        curso.nombre = nombre
        curso.nivel = nivel
        curso.save(update_fields=['nombre', 'nivel'])
        return curso

    @classmethod
    def get(cls, *, school_rbd: int, curso_id: int):
        colegio = Colegio.objects.get(rbd=school_rbd)
        return Curso.objects.get(id_curso=curso_id, colegio=colegio)

    @classmethod
    def delete(cls, *, user, school_rbd: int, curso_id: int):
        IntegrityService.validate_curso_deletion(school_rbd)

        colegio = Colegio.objects.get(rbd=school_rbd)
        curso = Curso.objects.get(id_curso=curso_id, colegio=colegio)

        with transaction.atomic():
            curso.activo = False
            curso.save(update_fields=['activo'])
            Clase.objects.filter(colegio=colegio, curso=curso, activo=True).update(activo=False)

        return curso

    @classmethod
    def assign_students(cls, *, user, school_rbd: int, curso_id: int, estudiantes_ids: list[int]):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='ADMIN_ESCOLAR_ASSIGN_ESTUDIANTES_CURSO',
        )

        colegio = Colegio.objects.get(rbd=school_rbd)
        curso = Curso.objects.get(id_curso=curso_id, colegio=colegio, activo=True)

        usuarios = User.objects.filter(id__in=estudiantes_ids, rbd_colegio=school_rbd)
        user_ids = list(usuarios.values_list('id', flat=True))

        with transaction.atomic():
            for user_id in user_ids:
                perfil, _created = PerfilEstudiante.objects.get_or_create(user_id=user_id)
                if not perfil.ciclo_actual:
                    perfil.ciclo_actual = curso.ciclo_academico
                    perfil.save(update_fields=['ciclo_actual'])

        return len(user_ids)

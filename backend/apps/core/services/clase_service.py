from __future__ import annotations

from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.accounts.models import User
from backend.apps.cursos.models import Asignatura, Clase, Curso
from backend.apps.institucion.models import Colegio
from backend.common.exceptions import PrerequisiteException


class ClaseService:
    @classmethod
    def validations(cls, *, school_rbd: int, curso_id: int, asignatura_id: int, profesor_id: int):
        try:
            colegio = Colegio.objects.get(rbd=school_rbd)
        except Colegio.DoesNotExist as exc:
            raise PrerequisiteException(
                error_type='SCHOOL_NOT_CONFIGURED',
                context={'school_rbd': school_rbd, 'message': 'Colegio no encontrado.'},
            ) from exc

        curso = Curso.objects.get(id_curso=curso_id, colegio=colegio, activo=True)
        asignatura = Asignatura.objects.get(id_asignatura=asignatura_id, colegio=colegio, activa=True)
        profesor = User.objects.get(id=profesor_id, rbd_colegio=school_rbd, is_active=True)

        return {
            'colegio': colegio,
            'curso': curso,
            'asignatura': asignatura,
            'profesor': profesor,
        }

    @classmethod
    def create(cls, *, school_rbd: int, curso_id: int, asignatura_id: int, profesor_id: int):
        curso_exists = Curso.objects.filter(id_curso=curso_id, colegio_id=school_rbd).exists()
        asignatura_exists = Asignatura.objects.filter(id_asignatura=asignatura_id, colegio_id=school_rbd).exists()
        profesor_exists = User.objects.filter(id=profesor_id, rbd_colegio=school_rbd).exists()

        if not curso_exists and not asignatura_exists and not profesor_exists:
            raise PrerequisiteException(
                error_type='DATA_INCONSISTENCY',
                context={
                    'school_rbd': school_rbd,
                    'curso_id': curso_id,
                    'asignatura_id': asignatura_id,
                    'profesor_id': profesor_id,
                    'message': 'No se encontraron entidades base para crear la clase.',
                },
            )

        validated = cls.validations(
            school_rbd=school_rbd,
            curso_id=curso_id,
            asignatura_id=asignatura_id,
            profesor_id=profesor_id,
        )
        IntegrityService.validate_clase_creation(school_rbd)

        colegio = validated['colegio']
        curso = validated['curso']
        asignatura = validated['asignatura']
        profesor = validated['profesor']

        clase, _created = Clase.objects.get_or_create(
            colegio=colegio,
            curso=curso,
            asignatura=asignatura,
            defaults={'profesor': profesor, 'activo': True},
        )

        if clase.profesor_id != profesor.id or not clase.activo:
            clase.profesor = profesor
            clase.activo = True
            clase.save(update_fields=['profesor', 'activo'])

        return clase

    @classmethod
    def update(cls, *, school_rbd: int, clase_id: int, curso_id: int, asignatura_id: int, profesor_id: int):
        validated = cls.validations(
            school_rbd=school_rbd,
            curso_id=curso_id,
            asignatura_id=asignatura_id,
            profesor_id=profesor_id,
        )
        IntegrityService.validate_clase_update(school_rbd)

        clase = Clase.objects.get(id=clase_id, colegio=validated['colegio'])
        clase.curso = validated['curso']
        clase.asignatura = validated['asignatura']
        clase.profesor = validated['profesor']
        clase.activo = True
        clase.save(update_fields=['curso', 'asignatura', 'profesor', 'activo'])
        return clase

    @classmethod
    def get(cls, *, school_rbd: int, clase_id: int):
        colegio = Colegio.objects.get(rbd=school_rbd)
        return Clase.objects.get(id=clase_id, colegio=colegio)

    @classmethod
    def assign_profesor(cls, *, school_rbd: int, clase_id: int, profesor_id: int):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='ADMIN_ESCOLAR_ASSIGN_PROFESOR_CLASE',
        )

        colegio = Colegio.objects.get(rbd=school_rbd)
        clase = Clase.objects.get(id=clase_id, colegio=colegio)
        profesor = User.objects.get(id=profesor_id, rbd_colegio=school_rbd, is_active=True)

        clase.profesor = profesor
        clase.activo = True
        clase.save(update_fields=['profesor', 'activo'])
        return clase

    @classmethod
    def delete(cls, *, school_rbd: int, clase_id: int):
        IntegrityService.validate_clase_deletion(school_rbd)

        colegio = Colegio.objects.get(rbd=school_rbd)
        clase = Clase.objects.get(id=clase_id, colegio=colegio)
        clase.activo = False
        clase.save(update_fields=['activo'])
        return clase

    @classmethod
    def deactivate_by_asignatura(cls, *, school_rbd: int, asignatura):
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='ADMIN_ESCOLAR_DEACTIVATE_CLASES_POR_ASIGNATURA',
        )

        return Clase.objects.filter(
            asignatura=asignatura,
            colegio_id=school_rbd,
            activo=True,
        ).update(activo=False)

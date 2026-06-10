from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from backend.apps.accounts.models import Apoderado, RelacionApoderadoEstudiante, Role, User
from backend.apps.accounts.services.apoderado_service import ApoderadoService


class ApoderadoApiService:
    """Logica de dominio para endpoints API de apoderados."""

    @staticmethod
    @transaction.atomic
    def create_apoderado(*, actor, data: dict, school_id: int):
        success, message, _password = ApoderadoService.execute(
            'create_apoderado',
            {
                'user': actor,
                'data': data,
                'escuela_rbd': school_id,
                'User': User,
                'Role': Role,
                'Apoderado': Apoderado,
            },
        )
        if not success:
            raise ValidationError({'detail': message})

        email = data['email'].strip().lower()
        created = Apoderado.objects.select_related('user').filter(user__email=email).first()
        return created, message

    @staticmethod
    @transaction.atomic
    def update_apoderado(*, actor, apoderado_id: int, data: dict, school_id: int):
        success, message = ApoderadoService.execute(
            'update_apoderado',
            {
                'user': actor,
                'apoderado_id': apoderado_id,
                'data': data,
                'escuela_rbd': school_id,
                'User': User,
                'Apoderado': Apoderado,
            },
        )
        if not success:
            raise ValidationError({'detail': message})

    @staticmethod
    @transaction.atomic
    def deactivate_apoderado(*, actor, apoderado_id: int, school_id: int):
        success, message = ApoderadoService.execute(
            'deactivate_apoderado',
            {
                'user': actor,
                'apoderado_id': apoderado_id,
                'escuela_rbd': school_id,
                'User': User,
                'Apoderado': Apoderado,
            },
        )
        if not success:
            raise ValidationError({'detail': message})

    @staticmethod
    @transaction.atomic
    def link_student(
        *,
        guardian,
        actor,
        student_id,
        parentesco: str,
        tipo_apoderado: str,
        is_global_admin: bool,
    ):
        if not student_id:
            raise ValidationError({'student_id': 'Campo requerido.'})

        student = User.objects.filter(pk=student_id).first()
        if not student:
            raise ValidationError({'student_id': 'Estudiante no encontrado.'})

        if not is_global_admin and student.rbd_colegio != actor.rbd_colegio:
            raise PermissionDenied('No puede vincular estudiantes de otro colegio.')

        return ApoderadoService.link_student(
            apoderado=guardian,
            estudiante=student,
            parentesco=str(parentesco),
            tipo_apoderado=str(tipo_apoderado),
        )

    @staticmethod
    def relationships(*, guardian):
        return RelacionApoderadoEstudiante.objects.select_related('estudiante').filter(apoderado=guardian)

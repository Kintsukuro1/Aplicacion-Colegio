"""Servicio de perfiles académicos (estudiante/profesor)."""

from typing import Any, Dict

from django.db import transaction

from backend.apps.accounts.models import PerfilEstudiante, PerfilProfesor, User
from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.auth_helpers import es_estudiante, es_profesor


class AcademicProfileService:
    """Operaciones críticas para perfiles de profesor y estudiante."""

    @staticmethod
    def _validate_user_school(user: User) -> None:
        if user.rbd_colegio is None:
            raise PrerequisiteException(
                error_type='MISSING_REQUIRED_FIELD',
                context={
                    'field': 'rbd_colegio',
                    'user_id': user.id,
                    'message': 'El usuario debe pertenecer a un colegio para tener perfil académico.',
                }
            )

        IntegrityService.validate_school_integrity_or_raise(
            school_id=user.rbd_colegio,
            action='ACADEMIC_PROFILE_SERVICE_OPERATION',
        )

    @staticmethod
    def _validate_student_scope(user: User) -> None:
        if not es_estudiante(user):
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'user_id': user.id,
                    'expected_role': 'estudiante',
                    'current_role': user.role.nombre if user.role else None,
                    'message': 'El rol del usuario no coincide con el perfil a crear.',
                }
            )

    @staticmethod
    def _validate_teacher_scope(user: User) -> None:
        if not es_profesor(user):
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                context={
                    'user_id': user.id,
                    'expected_role': 'profesor',
                    'current_role': user.role.nombre if user.role else None,
                    'message': 'El rol del usuario no coincide con el perfil a crear.',
                }
            )

    @staticmethod
    def create_student_profile(user: User, **profile_data: Any) -> PerfilEstudiante:
        AcademicProfileService._validate_user_school(user)
        AcademicProfileService._validate_student_scope(user)

        if hasattr(user, 'perfil_estudiante'):
            raise PrerequisiteException(
                error_type='DUPLICATE_RECORD',
                context={'user_id': user.id, 'message': 'El usuario ya tiene perfil de estudiante.'}
            )

        with transaction.atomic():
            return PerfilEstudiante.objects.create(user=user, **profile_data)

    @staticmethod
    def create_teacher_profile(user: User, **profile_data: Any) -> PerfilProfesor:
        AcademicProfileService._validate_user_school(user)
        AcademicProfileService._validate_teacher_scope(user)

        if hasattr(user, 'perfil_profesor'):
            raise PrerequisiteException(
                error_type='DUPLICATE_RECORD',
                context={'user_id': user.id, 'message': 'El usuario ya tiene perfil de profesor.'}
            )

        with transaction.atomic():
            return PerfilProfesor.objects.create(user=user, **profile_data)

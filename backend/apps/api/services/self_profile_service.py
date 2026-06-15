"""
Self-Service Profile API Service.

Lógica de dominio para que cada usuario pueda ver y editar su propio perfil
sin requerir permisos administrativos. El servicio:
  - Identifica el rol del usuario y selecciona el perfil correcto.
  - Serializa la lectura (GET) con datos completos read-only.
  - Aplica updates (PATCH) solo a campos permitidos para cada rol.
  - Gestiona el cambio de contraseña con auditoría.

Principio: un usuario NUNCA puede escalar sus propios permisos ni modificar
campos que afectan su identidad (email, RUT) sin intervención de un admin.
"""
import logging
from typing import Dict, Any, Tuple

from rest_framework.exceptions import ValidationError as DRFValidationError

from backend.apps.accounts.models import Apoderado, PerfilEstudiante, PerfilProfesor, User
from backend.apps.api.profile_serializers import (
    AdminSelfProfileReadSerializer,
    AdminSelfProfileUpdateSerializer,
    ApoderadoSelfProfileReadSerializer,
    ApoderadoSelfProfileUpdateSerializer,
    ChangePasswordSerializer,
    StudentSelfProfileReadSerializer,
    StudentSelfProfileUpdateSerializer,
    TeacherSelfProfileReadSerializer,
    TeacherSelfProfileUpdateSerializer,
)
from backend.common.utils.auth_helpers import normalizar_rol

logger = logging.getLogger('accounts')


def _role_key(user) -> str:
    """Retorna un key normalizado del rol del usuario."""
    role_name = getattr(getattr(user, 'role', None), 'nombre', '') or ''
    return normalizar_rol(role_name)


class SelfProfileService:
    """Servicio para operaciones de perfil propio de cada usuario."""

    # ──────────────────────────────────────
    # GET  —  Obtener perfil propio
    # ──────────────────────────────────────

    @staticmethod
    def get_my_profile(user: User) -> dict:
        """Retorna el perfil serializado del usuario autenticado."""
        role = _role_key(user)

        if role == 'estudiante':
            perfil = SelfProfileService._get_or_create_perfil_estudiante(user)
            return StudentSelfProfileReadSerializer(perfil).data

        if role == 'profesor':
            perfil = SelfProfileService._get_or_create_perfil_profesor(user)
            return TeacherSelfProfileReadSerializer(perfil).data

        if role == 'apoderado':
            perfil = SelfProfileService._get_apoderado(user)
            return ApoderadoSelfProfileReadSerializer(perfil).data

        # Admin general, Admin escolar, y otros roles
        return AdminSelfProfileReadSerializer(user).data

    # ──────────────────────────────────────
    # PATCH  —  Actualizar perfil propio
    # ──────────────────────────────────────

    @staticmethod
    def update_my_profile(user: User, data: Dict[str, Any]) -> dict:
        """
        Actualiza los campos permitidos del perfil del usuario.
        Retorna el perfil actualizado serializado.

        Raises:
            DRFValidationError: si los datos son inválidos
        """
        role = _role_key(user)

        if role == 'estudiante':
            return SelfProfileService._update_estudiante(user, data)

        if role == 'profesor':
            return SelfProfileService._update_profesor(user, data)

        if role == 'apoderado':
            return SelfProfileService._update_apoderado(user, data)

        # Admin
        return SelfProfileService._update_admin(user, data)

    # ──────────────────────────────────────
    # PASSWORD  —  Cambiar contraseña
    # ──────────────────────────────────────

    @staticmethod
    def change_password(user: User, data: Dict[str, Any], client_ip: str = '') -> dict:
        """
        Cambia la contraseña del usuario previa verificación de la actual.

        Returns:
            dict con 'message'

        Raises:
            DRFValidationError: si la contraseña actual es incorrecta o las nuevas no coinciden
        """
        serializer = ChangePasswordSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        if not user.check_password(validated['password_actual']):
            logger.warning(
                f"Cambio de contraseña fallido (password incorrecta) — "
                f"user={user.email} ip={client_ip}"
            )
            raise DRFValidationError({
                'password_actual': 'La contraseña actual es incorrecta.'
            })

        user.set_password(validated['password_nueva'])
        user.save(update_fields=['password'])

        logger.info(
            f"Contraseña cambiada exitosamente — user={user.email} "
            f"role={_role_key(user)} ip={client_ip}"
        )

        return {'message': 'Contraseña cambiada exitosamente.'}

    # ──────────────────────────────────────
    # Helpers internos por rol
    # ──────────────────────────────────────

    @staticmethod
    def _get_or_create_perfil_estudiante(user: User) -> PerfilEstudiante:
        perfil, _ = PerfilEstudiante.objects.get_or_create(user=user)
        return perfil

    @staticmethod
    def _get_or_create_perfil_profesor(user: User) -> PerfilProfesor:
        perfil, _ = PerfilProfesor.objects.get_or_create(user=user)
        return perfil

    @staticmethod
    def _get_apoderado(user: User) -> Apoderado:
        try:
            return Apoderado.objects.select_related('user').get(user=user)
        except Apoderado.DoesNotExist:
            raise DRFValidationError({
                'detail': 'No se encontró perfil de apoderado para este usuario.'
            })

    @staticmethod
    def _update_estudiante(user: User, data: dict) -> dict:
        serializer = StudentSelfProfileUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        perfil = SelfProfileService._get_or_create_perfil_estudiante(user)

        updated_fields = []
        for field, value in validated.items():
            if hasattr(perfil, field):
                setattr(perfil, field, value)
                updated_fields.append(field)

        if updated_fields:
            perfil.save(update_fields=updated_fields + ['fecha_actualizacion'])
            logger.info(f"Perfil estudiante actualizado — user={user.email} campos={updated_fields}")

        return StudentSelfProfileReadSerializer(perfil).data

    @staticmethod
    def _update_profesor(user: User, data: dict) -> dict:
        serializer = TeacherSelfProfileUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        perfil = SelfProfileService._get_or_create_perfil_profesor(user)

        updated_fields = []
        for field, value in validated.items():
            if hasattr(perfil, field):
                setattr(perfil, field, value)
                updated_fields.append(field)

        if updated_fields:
            perfil.save(update_fields=updated_fields + ['fecha_actualizacion'])
            logger.info(f"Perfil profesor actualizado — user={user.email} campos={updated_fields}")

        return TeacherSelfProfileReadSerializer(perfil).data

    @staticmethod
    def _update_apoderado(user: User, data: dict) -> dict:
        serializer = ApoderadoSelfProfileUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        apoderado = SelfProfileService._get_apoderado(user)

        updated_fields = []
        for field, value in validated.items():
            if hasattr(apoderado, field):
                setattr(apoderado, field, value)
                updated_fields.append(field)

        if updated_fields:
            apoderado.save(update_fields=updated_fields + ['fecha_actualizacion'])
            logger.info(f"Perfil apoderado actualizado — user={user.email} campos={updated_fields}")

        return ApoderadoSelfProfileReadSerializer(apoderado).data

    @staticmethod
    def _update_admin(user: User, data: dict) -> dict:
        serializer = AdminSelfProfileUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated_fields = []
        for field, value in validated.items():
            if hasattr(user, field):
                setattr(user, field, value)
                updated_fields.append(field)

        if updated_fields:
            user.save(update_fields=updated_fields)
            logger.info(f"Perfil admin actualizado — user={user.email} campos={updated_fields}")

        return AdminSelfProfileReadSerializer(user).data

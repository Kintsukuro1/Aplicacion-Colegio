from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.apps.accounts.services.academic_profile_service import AcademicProfileService


pytestmark = pytest.mark.django_db


class _FlexiblePrerequisiteException(Exception):
    def __init__(self, error_type=None, **kwargs):
        self.error_type = error_type
        self.context = kwargs.get('context', {})
        super().__init__(str(error_type))


@pytest.fixture(autouse=True)
def _patch_prereq(monkeypatch):
    monkeypatch.setattr(
        'backend.apps.accounts.services.academic_profile_service.PrerequisiteException',
        _FlexiblePrerequisiteException,
    )


def _user(user_id=1, school_rbd=123, role_name='Alumno'):
    return SimpleNamespace(
        id=user_id,
        rbd_colegio=school_rbd,
        role=SimpleNamespace(nombre=role_name),
    )


class TestAcademicProfileService:
    def test_create_student_profile_requires_school(self):
        user = _user(school_rbd=None)

        with pytest.raises(_FlexiblePrerequisiteException):
            AcademicProfileService.create_student_profile(user)

    @patch('backend.apps.accounts.services.academic_profile_service.IntegrityService.validate_school_integrity_or_raise')
    @patch('backend.apps.accounts.services.academic_profile_service.es_estudiante', return_value=False)
    def test_create_student_profile_requires_student_scope(self, _mock_scope, _mock_integrity):
        user = _user(role_name='Profesor')

        with pytest.raises(_FlexiblePrerequisiteException):
            AcademicProfileService.create_student_profile(user)

    @patch('backend.apps.accounts.services.academic_profile_service.IntegrityService.validate_school_integrity_or_raise')
    @patch('backend.apps.accounts.services.academic_profile_service.es_estudiante', return_value=True)
    @patch('backend.apps.accounts.services.academic_profile_service.PerfilEstudiante')
    def test_create_student_profile_success(self, mock_perfil_estudiante, _mock_scope, _mock_integrity):
        user = _user(role_name='Alumno')
        created = Mock()
        mock_perfil_estudiante.objects.create.return_value = created

        result = AcademicProfileService.create_student_profile(user, numero_lista=12)

        assert result is created
        mock_perfil_estudiante.objects.create.assert_called_once_with(user=user, numero_lista=12)

    @patch('backend.apps.accounts.services.academic_profile_service.IntegrityService.validate_school_integrity_or_raise')
    @patch('backend.apps.accounts.services.academic_profile_service.es_profesor', return_value=False)
    def test_create_teacher_profile_requires_teacher_scope(self, _mock_scope, _mock_integrity):
        user = _user(role_name='Alumno')

        with pytest.raises(_FlexiblePrerequisiteException):
            AcademicProfileService.create_teacher_profile(user)

    @patch('backend.apps.accounts.services.academic_profile_service.IntegrityService.validate_school_integrity_or_raise')
    @patch('backend.apps.accounts.services.academic_profile_service.es_profesor', return_value=True)
    @patch('backend.apps.accounts.services.academic_profile_service.PerfilProfesor')
    def test_create_teacher_profile_success(self, mock_perfil_profesor, _mock_scope, _mock_integrity):
        user = _user(role_name='Profesor')
        created = Mock()
        mock_perfil_profesor.objects.create.return_value = created

        result = AcademicProfileService.create_teacher_profile(user, especialidad='Matemáticas')

        assert result is created
        mock_perfil_profesor.objects.create.assert_called_once_with(user=user, especialidad='Matemáticas')

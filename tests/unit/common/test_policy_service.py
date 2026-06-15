from types import SimpleNamespace
from unittest.mock import patch

from backend.common.services.policy_service import PolicyService


def _user(*, user_id=1, role='Estudiante', school_id=123, active=True):
    return SimpleNamespace(
        id=user_id,
        is_authenticated=True,
        is_active=active,
        email='user@test.cl',
        rbd_colegio=school_id,
        role=SimpleNamespace(nombre=role),
    )


def test_authorize_student_context_allows_only_own_student_id():
    user = _user(user_id=10)

    with patch.object(PolicyService, 'has_capability', return_value=True), \
         patch.object(PolicyService, '_is_student_actor', return_value=True), \
         patch.object(PolicyService, '_is_guardian_actor', return_value=False):
        assert PolicyService.authorize(user, 'GRADE_VIEW', context={'student_id': 10}) is True
        assert PolicyService.authorize(user, 'GRADE_VIEW', context={'student_id': 99}) is False


def test_authorize_guardian_context_uses_relation_check():
    user = _user(role='Apoderado')
    relation = SimpleNamespace(get_permisos_efectivos=lambda: {'ver_notas': True})

    with patch.object(PolicyService, 'has_capability', return_value=True), \
         patch.object(PolicyService, '_is_student_actor', return_value=False), \
         patch.object(PolicyService, '_is_guardian_actor', return_value=True), \
         patch.object(PolicyService, '_get_guardian_relation', return_value=relation) as relation_check:
        assert PolicyService.authorize(user, 'GRADE_VIEW', context={'student_id': 33}) is True
        relation_check.assert_called_once_with(user, 33)


def test_authorize_guardian_context_applies_relation_permission_flags():
    user = _user(role='Apoderado')
    relation = SimpleNamespace(get_permisos_efectivos=lambda: {'ver_notas': False})

    with patch.object(PolicyService, 'has_capability', return_value=True), \
         patch.object(PolicyService, '_is_student_actor', return_value=False), \
         patch.object(PolicyService, '_is_guardian_actor', return_value=True), \
         patch.object(PolicyService, '_get_guardian_relation', return_value=relation):
        allowed = PolicyService.authorize(user, 'GRADE_VIEW', context={'student_id': 33})

    assert allowed is False


def test_authorize_teacher_context_uses_course_ownership():
    user = _user(role='Profesor')

    with patch.object(PolicyService, 'has_capability', return_value=True), \
         patch.object(PolicyService, '_is_student_actor', return_value=False), \
         patch.object(PolicyService, '_is_guardian_actor', return_value=False), \
         patch.object(PolicyService, '_is_teacher_actor', return_value=True), \
         patch.object(PolicyService, '_is_teacher_of_course', return_value=False) as teacher_check:
        assert PolicyService.authorize(user, 'CLASS_TAKE_ATTENDANCE', context={'course_id': 7}) is False
        teacher_check.assert_called_once_with(user, 7)


def test_authorize_blocks_cross_tenant_without_global_scope():
    user = _user(role='Profesor', school_id=111)

    def _capability(_user, capability, school_id=None):
        return capability != 'SYSTEM_ADMIN'

    with patch.object(PolicyService, 'has_capability', side_effect=_capability), \
         patch.object(PolicyService, '_is_student_actor', return_value=False), \
         patch.object(PolicyService, '_is_guardian_actor', return_value=False), \
         patch.object(PolicyService, '_is_teacher_actor', return_value=False):
        allowed = PolicyService.authorize(
            user,
            'CLASS_VIEW',
            context={'school_id': 999},
        )

    assert allowed is False


def test_authorize_denies_when_capability_missing():
    user = _user()

    with patch.object(PolicyService, 'has_capability', return_value=False):
        assert PolicyService.authorize(user, 'GRADE_VIEW', context={'student_id': 1}) is False

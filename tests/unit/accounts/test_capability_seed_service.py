import pytest

from backend.apps.accounts.models import Capability, Role, RoleCapability
from backend.apps.accounts.services.capability_seed_service import seed_role_capabilities


pytestmark = pytest.mark.django_db


def test_seed_role_capabilities_creates_defaults_for_existing_roles():
    role, _ = Role.objects.get_or_create(nombre='Inspector convivencia')
    RoleCapability.objects.filter(role=role).delete()

    summary = seed_role_capabilities()

    assert summary['role_capabilities_created'] > 0
    assert Capability.objects.filter(code='DISCIPLINE_VIEW').exists()
    assert RoleCapability.objects.filter(
        role=role,
        capability__code='DISCIPLINE_VIEW',
        is_granted=True,
    ).exists()


def test_seed_role_capabilities_is_additive_and_respects_denies():
    role, _ = Role.objects.get_or_create(nombre='Apoderado')
    RoleCapability.objects.filter(role=role).delete()
    capability, _ = Capability.objects.get_or_create(code='GRADE_VIEW', defaults={'description': 'Grade view'})
    RoleCapability.objects.create(role=role, capability=capability, is_granted=False)

    seed_role_capabilities()

    role_capability = RoleCapability.objects.get(role=role, capability__code='GRADE_VIEW')
    assert role_capability.is_granted is False
    assert RoleCapability.objects.filter(role=role, capability__code='STUDENT_VIEW', is_granted=True).exists()


def test_seed_role_capabilities_covers_fase1_libro_de_clases_permissions():
    profesor, _ = Role.objects.get_or_create(nombre='Profesor')
    admin_escolar, _ = Role.objects.get_or_create(nombre='Administrador escolar')
    RoleCapability.objects.filter(role__in=[profesor, admin_escolar]).delete()

    seed_role_capabilities()

    assert RoleCapability.objects.filter(
        role=profesor,
        capability__code='LIBRO_CLASE_VIEW',
        is_granted=True,
    ).exists()
    assert RoleCapability.objects.filter(
        role=profesor,
        capability__code='LIBRO_CLASE_EDIT',
        is_granted=True,
    ).exists()
    assert RoleCapability.objects.filter(
        role=profesor,
        capability__code='LIBRO_CLASE_FIRMAR',
        is_granted=True,
    ).exists()
    assert RoleCapability.objects.filter(
        role=admin_escolar,
        capability__code='LIBRO_CLASE_VIEW_RBD',
        is_granted=True,
    ).exists()
    assert RoleCapability.objects.filter(
        role=admin_escolar,
        capability__code='REPORT_EXPORT_SUPERINTENDENCIA',
        is_granted=True,
    ).exists()

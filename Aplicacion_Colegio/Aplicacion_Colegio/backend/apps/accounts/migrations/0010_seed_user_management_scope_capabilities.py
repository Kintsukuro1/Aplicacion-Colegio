from django.db import migrations


NEW_CAPABILITIES = [
    'USER_MANAGE_SCHOOL',
    'USER_MANAGE_GLOBAL',
]


ROLE_SCOPE_CAPABILITIES = {
    'admin_general': {'USER_MANAGE_SCHOOL', 'USER_MANAGE_GLOBAL'},
    'admin': {'USER_MANAGE_SCHOOL', 'USER_MANAGE_GLOBAL'},
    'admin_escolar': {'USER_MANAGE_SCHOOL'},
}


ROLE_ALIASES = {
    'administrador general': 'admin_general',
    'admin general': 'admin_general',
    'super admin': 'admin_general',
    'admin_general': 'admin_general',
    'administrador': 'admin',
    'admin': 'admin',
    'administrador escolar': 'admin_escolar',
    'admin escolar': 'admin_escolar',
    'admin_escolar': 'admin_escolar',
}


def _normalize_role_name(nombre):
    raw = (nombre or '').strip().lower()
    raw = ' '.join(raw.split())
    return ROLE_ALIASES.get(raw, raw.replace(' ', '_'))


def seed_user_management_scope_capabilities(apps, schema_editor):
    Capability = apps.get_model('accounts', 'Capability')
    Role = apps.get_model('accounts', 'Role')
    RoleCapability = apps.get_model('accounts', 'RoleCapability')

    for capability_code in NEW_CAPABILITIES:
        Capability.objects.get_or_create(
            code=capability_code,
            defaults={
                'description': capability_code.replace('_', ' ').title(),
                'is_active': True,
            },
        )

    capability_by_code = {
        row.code: row
        for row in Capability.objects.filter(code__in=NEW_CAPABILITIES)
    }

    for role in Role.objects.all():
        normalized_role = _normalize_role_name(role.nombre)
        role_capabilities = ROLE_SCOPE_CAPABILITIES.get(normalized_role, set())
        for capability_code in role_capabilities:
            capability = capability_by_code.get(capability_code)
            if capability is None:
                continue
            RoleCapability.objects.get_or_create(
                role=role,
                capability=capability,
                defaults={'is_granted': True},
            )


def noop_reverse(apps, schema_editor):
    # No eliminamos registros para respetar configuraciones productivas.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_seed_missing_capabilities_for_operational_roles'),
    ]

    operations = [
        migrations.RunPython(seed_user_management_scope_capabilities, noop_reverse),
    ]

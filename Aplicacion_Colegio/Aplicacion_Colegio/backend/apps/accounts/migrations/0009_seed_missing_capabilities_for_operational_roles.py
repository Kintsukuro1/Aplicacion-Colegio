from django.db import migrations


MISSING_CAPABILITIES = [
    'DISCIPLINE_VIEW',
    'DISCIPLINE_CREATE',
    'DISCIPLINE_EDIT',
    'JUSTIFICATION_VIEW',
    'JUSTIFICATION_APPROVE',
    'COUNSELING_VIEW',
    'COUNSELING_CREATE',
    'COUNSELING_EDIT',
    'REFERRAL_VIEW',
    'REFERRAL_CREATE',
    'REFERRAL_EDIT',
    'SUPPORT_VIEW_TICKETS',
    'SUPPORT_CREATE_TICKET',
    'SUPPORT_RESOLVE_TICKET',
    'SUPPORT_RESET_PASSWORD',
    'LIBRARY_VIEW',
    'LIBRARY_CREATE',
    'LIBRARY_EDIT',
    'LIBRARY_DELETE',
    'LIBRARY_MANAGE_LOANS',
    'PLANNING_VIEW',
    'PLANNING_APPROVE',
]


ROLE_MISSING_CAPABILITIES = {
    'admin_general': set(MISSING_CAPABILITIES),
    'admin': set(MISSING_CAPABILITIES),
    'coordinador_academico': {
        'PLANNING_VIEW',
        'PLANNING_APPROVE',
    },
    'coordinador': {
        'PLANNING_VIEW',
        'PLANNING_APPROVE',
    },
    'inspector_convivencia': {
        'DISCIPLINE_VIEW',
        'DISCIPLINE_CREATE',
        'DISCIPLINE_EDIT',
        'JUSTIFICATION_VIEW',
        'JUSTIFICATION_APPROVE',
    },
    'inspector': {
        'DISCIPLINE_VIEW',
        'DISCIPLINE_CREATE',
        'DISCIPLINE_EDIT',
        'JUSTIFICATION_VIEW',
        'JUSTIFICATION_APPROVE',
    },
    'psicologo_orientador': {
        'COUNSELING_VIEW',
        'COUNSELING_CREATE',
        'COUNSELING_EDIT',
        'REFERRAL_VIEW',
        'REFERRAL_CREATE',
        'REFERRAL_EDIT',
        'DISCIPLINE_VIEW',
    },
    'psicologo': {
        'COUNSELING_VIEW',
        'COUNSELING_CREATE',
        'COUNSELING_EDIT',
        'REFERRAL_VIEW',
        'REFERRAL_CREATE',
        'REFERRAL_EDIT',
        'DISCIPLINE_VIEW',
    },
    'soporte_tecnico_escolar': {
        'SUPPORT_VIEW_TICKETS',
        'SUPPORT_CREATE_TICKET',
        'SUPPORT_RESOLVE_TICKET',
        'SUPPORT_RESET_PASSWORD',
    },
    'bibliotecario_digital': {
        'LIBRARY_VIEW',
        'LIBRARY_CREATE',
        'LIBRARY_EDIT',
        'LIBRARY_DELETE',
        'LIBRARY_MANAGE_LOANS',
    },
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
    'coordinador academico': 'coordinador_academico',
    'coordinador académico': 'coordinador_academico',
    'coordinador': 'coordinador',
    'inspector convivencia': 'inspector_convivencia',
    'inspector_convivencia': 'inspector_convivencia',
    'inspector': 'inspector',
    'psicologo orientador': 'psicologo_orientador',
    'psicólogo orientador': 'psicologo_orientador',
    'psicologo': 'psicologo',
    'psicólogo': 'psicologo',
    'soporte tecnico escolar': 'soporte_tecnico_escolar',
    'soporte técnico escolar': 'soporte_tecnico_escolar',
    'soporte_tecnico_escolar': 'soporte_tecnico_escolar',
    'bibliotecario digital': 'bibliotecario_digital',
    'bibliotecario_digital': 'bibliotecario_digital',
}


def _normalize_role_name(nombre):
    raw = (nombre or '').strip().lower()
    raw = ' '.join(raw.split())
    return ROLE_ALIASES.get(raw, raw.replace(' ', '_'))


def seed_missing_capabilities(apps, schema_editor):
    Capability = apps.get_model('accounts', 'Capability')
    Role = apps.get_model('accounts', 'Role')
    RoleCapability = apps.get_model('accounts', 'RoleCapability')

    for code in MISSING_CAPABILITIES:
        Capability.objects.get_or_create(
            code=code,
            defaults={'description': code.replace('_', ' ').title(), 'is_active': True},
        )

    capability_by_code = {
        cap.code: cap
        for cap in Capability.objects.filter(code__in=MISSING_CAPABILITIES)
    }

    for role in Role.objects.all():
        normalized_role = _normalize_role_name(role.nombre)
        capabilities = ROLE_MISSING_CAPABILITIES.get(normalized_role, set())
        for capability_code in capabilities:
            capability = capability_by_code.get(capability_code)
            if capability is None:
                continue
            RoleCapability.objects.get_or_create(
                role=role,
                capability=capability,
                defaults={'is_granted': True},
            )


def noop_reverse(apps, schema_editor):
    # No eliminamos datos para evitar perder configuraciones de permisos en producción.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_apoderado_estudiantes_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_missing_capabilities, noop_reverse),
    ]

from django.db import migrations


NEW_CAPABILITIES = [
    ('LIBRO_CLASE_VIEW', 'Ver registros propios del libro de clases digital'),
    ('LIBRO_CLASE_EDIT', 'Crear y editar registros propios no firmados del libro de clases digital'),
    ('REPORT_EXPORT_SUPERINTENDENCIA', 'Exportar reportes normativos para Superintendencia/MINEDUC'),
]


ROLE_CAPABILITIES = {
    'admin_general': {'LIBRO_CLASE_VIEW', 'LIBRO_CLASE_EDIT', 'REPORT_EXPORT_SUPERINTENDENCIA'},
    'admin': {'LIBRO_CLASE_VIEW', 'LIBRO_CLASE_EDIT', 'REPORT_EXPORT_SUPERINTENDENCIA'},
    'admin_escolar': {'LIBRO_CLASE_VIEW_RBD', 'REPORT_EXPORT_SUPERINTENDENCIA'},
    'profesor': {'LIBRO_CLASE_VIEW', 'LIBRO_CLASE_EDIT', 'LIBRO_CLASE_FIRMAR'},
    'coordinador_academico': {'LIBRO_CLASE_VIEW_RBD', 'REPORT_EXPORT_SUPERINTENDENCIA'},
    'jefe_utp': {'LIBRO_CLASE_VIEW_RBD', 'REPORT_EXPORT_SUPERINTENDENCIA'},
}


ROLE_ALIASES = {
    'administrador general': 'admin_general',
    'admin general': 'admin_general',
    'admin_general': 'admin_general',
    'administrador': 'admin',
    'admin': 'admin',
    'administrador escolar': 'admin_escolar',
    'admin escolar': 'admin_escolar',
    'admin_escolar': 'admin_escolar',
    'profesor': 'profesor',
    'docente': 'profesor',
    'coordinador academico': 'coordinador_academico',
    'coordinador académico': 'coordinador_academico',
    'coordinador_academico': 'coordinador_academico',
    'jefe utp': 'jefe_utp',
    'jefe_utp': 'jefe_utp',
}


def _normalize_role_name(nombre):
    raw = (nombre or '').strip().lower()
    raw = ' '.join(raw.split())
    return ROLE_ALIASES.get(raw, raw.replace(' ', '_'))


def seed_fase1_capabilities(apps, schema_editor):
    Capability = apps.get_model('accounts', 'Capability')
    Role = apps.get_model('accounts', 'Role')
    RoleCapability = apps.get_model('accounts', 'RoleCapability')

    for code, description in NEW_CAPABILITIES:
        Capability.objects.get_or_create(
            code=code,
            defaults={'description': description, 'is_active': True},
        )

    capability_codes = {code for code, _description in NEW_CAPABILITIES}
    capability_codes.update({'LIBRO_CLASE_FIRMAR', 'LIBRO_CLASE_VIEW_RBD'})
    capability_by_code = {
        capability.code: capability
        for capability in Capability.objects.filter(code__in=capability_codes)
    }

    for role in Role.objects.all():
        normalized_role = _normalize_role_name(role.nombre)
        for capability_code in ROLE_CAPABILITIES.get(normalized_role, set()):
            capability = capability_by_code.get(capability_code)
            if capability is None:
                continue
            RoleCapability.objects.get_or_create(
                role=role,
                capability=capability,
                defaults={'is_granted': True},
            )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_seed_jefe_utp_role_and_chile_capabilities'),
    ]

    operations = [
        migrations.RunPython(seed_fase1_capabilities, noop_reverse),
    ]

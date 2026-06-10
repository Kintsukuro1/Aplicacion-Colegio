from django.db import migrations


NEW_ROLES_IN_ORDER = [
    ('coordinador_academico', 'Coordinador académico'),
    ('inspector_convivencia', 'Inspector convivencia'),
    ('psicologo_orientador', 'Psicólogo orientador'),
    ('soporte_tecnico_escolar', 'Soporte técnico escolar'),
    ('bibliotecario_digital', 'Bibliotecario digital'),
]

NEW_ROLE_CAPABILITIES = {
    'coordinador_academico': [
        'DASHBOARD_VIEW_SCHOOL', 'DASHBOARD_VIEW_ANALYTICS',
        'STUDENT_VIEW', 'STUDENT_VIEW_ACADEMIC',
        'TEACHER_VIEW', 'TEACHER_VIEW_PERFORMANCE',
        'COURSE_VIEW', 'CLASS_VIEW', 'CLASS_VIEW_ATTENDANCE',
        'GRADE_VIEW', 'GRADE_VIEW_ANALYTICS',
        'REPORT_VIEW_ACADEMIC', 'REPORT_EXPORT',
    ],
    'inspector_convivencia': [
        'DASHBOARD_VIEW_SCHOOL',
        'STUDENT_VIEW', 'STUDENT_VIEW_DISCIPLINE',
        'CLASS_VIEW', 'CLASS_TAKE_ATTENDANCE', 'CLASS_VIEW_ATTENDANCE',
        'REPORT_VIEW_BASIC',
        'ANNOUNCEMENT_VIEW',
    ],
    'psicologo_orientador': [
        'DASHBOARD_VIEW_SCHOOL',
        'STUDENT_VIEW', 'STUDENT_VIEW_ACADEMIC', 'STUDENT_VIEW_CONFIDENTIAL',
        'REPORT_VIEW_BASIC', 'REPORT_VIEW_ACADEMIC',
        'ANNOUNCEMENT_VIEW',
        'AUDIT_VIEW',
    ],
    'soporte_tecnico_escolar': [
        'DASHBOARD_VIEW_SCHOOL',
        'USER_VIEW', 'USER_EDIT',
        'SYSTEM_VIEW_AUDIT',
        'REPORT_VIEW_BASIC',
        'ANNOUNCEMENT_VIEW',
        # Soporte: tickets capabilities
        'SUPPORT_VIEW_TICKETS',
        'SUPPORT_CREATE_TICKET',
        'SUPPORT_RESOLVE_TICKET',
    ],
    'bibliotecario_digital': [
        'DASHBOARD_VIEW_SCHOOL',
        'STUDENT_VIEW', 'TEACHER_VIEW',
        'CLASS_VIEW',
        'REPORT_VIEW_BASIC', 'REPORT_EXPORT',
        'ANNOUNCEMENT_VIEW', 'ANNOUNCEMENT_CREATE',
    ],
}


def seed_new_roles_and_capabilities(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    Capability = apps.get_model('accounts', 'Capability')
    RoleCapability = apps.get_model('accounts', 'RoleCapability')

    role_by_code = {}
    for role_code, role_name in NEW_ROLES_IN_ORDER:
        role_obj, _ = Role.objects.get_or_create(nombre=role_name)
        role_by_code[role_code] = role_obj

    for role_code, capability_codes in NEW_ROLE_CAPABILITIES.items():
        role_obj = role_by_code.get(role_code)
        if role_obj is None:
            continue

        for capability_code in capability_codes:
            capability_obj = Capability.objects.filter(code=capability_code).first()
            if capability_obj is None:
                continue

            RoleCapability.objects.get_or_create(
                role=role_obj,
                capability=capability_obj,
                defaults={'is_granted': True},
            )


def rollback_new_role_capabilities(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    RoleCapability = apps.get_model('accounts', 'RoleCapability')

    role_names = [role_name for _, role_name in NEW_ROLES_IN_ORDER]
    roles = Role.objects.filter(nombre__in=role_names)
    RoleCapability.objects.filter(role__in=roles).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_capabilities_policy'),
    ]

    operations = [
        migrations.RunPython(seed_new_roles_and_capabilities, rollback_new_role_capabilities),
    ]

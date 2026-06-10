"""
Migración: Fase 1 — Rol Jefe UTP y nuevas capabilities para mercado chileno.

Agrega:
- Capabilities Chile: ACADEMIC_SUPERVISION, LIBRO_CLASE_FIRMAR, LIBRO_CLASE_VIEW_RBD,
  SEP_VIEW, SEP_MANAGE, SEP_REPORT_EXPORT, ALERT_VIEW, ALERT_MANAGE, ALERT_RESOLVE,
  CERTIFICATE_EMIT
- Rol 'jefe_utp' con sus RoleCapability correspondientes
"""
from django.db import migrations


NUEVAS_CAPABILITIES = [
    ('ACADEMIC_SUPERVISION', 'Supervisión académica integral (Jefe UTP)'),
    ('LIBRO_CLASE_FIRMAR', 'Firmar / validar entradas del libro de clases digital'),
    ('LIBRO_CLASE_VIEW_RBD', 'Ver libro de clases de todo el establecimiento'),
    ('SEP_VIEW', 'Ver nómina y beneficios SEP'),
    ('SEP_MANAGE', 'Gestionar estudiantes prioritarios SEP'),
    ('SEP_REPORT_EXPORT', 'Exportar reportes SEP para MINEDUC'),
    ('ALERT_VIEW', 'Ver alertas tempranas de estudiantes'),
    ('ALERT_MANAGE', 'Crear y editar alertas tempranas'),
    ('ALERT_RESOLVE', 'Marcar alertas como resueltas'),
    ('CERTIFICATE_EMIT', 'Emitir certificados con código QR'),
]

JEFE_UTP_CAPABILITIES = [
    'DASHBOARD_VIEW_SCHOOL',
    'DASHBOARD_VIEW_ANALYTICS',
    'STUDENT_VIEW',
    'STUDENT_VIEW_ACADEMIC',
    'TEACHER_VIEW',
    'TEACHER_VIEW_PERFORMANCE',
    'COURSE_VIEW',
    'CLASS_VIEW',
    'CLASS_VIEW_ATTENDANCE',
    'GRADE_VIEW',
    'GRADE_VIEW_ANALYTICS',
    'REPORT_VIEW_ACADEMIC',
    'REPORT_EXPORT',
    'PLANNING_VIEW',
    'PLANNING_APPROVE',
    'ACADEMIC_SUPERVISION',
    'LIBRO_CLASE_FIRMAR',
    'LIBRO_CLASE_VIEW_RBD',
    'SEP_VIEW',
    'SEP_REPORT_EXPORT',
    'ALERT_VIEW',
    'CERTIFICATE_EMIT',
    'ANNOUNCEMENT_VIEW',
]


def seed_jefe_utp(apps, schema_editor):
    Capability = apps.get_model('accounts', 'Capability')
    Role = apps.get_model('accounts', 'Role')
    RoleCapability = apps.get_model('accounts', 'RoleCapability')

    # 1. Crear nuevas capabilities
    for code, description in NUEVAS_CAPABILITIES:
        Capability.objects.get_or_create(
            code=code,
            defaults={'description': description, 'is_active': True},
        )

    # 2. Crear rol jefe_utp
    role_obj, _ = Role.objects.get_or_create(
        nombre='jefe_utp',
        defaults={'nombre': 'jefe_utp'},
    )

    # 3. Asignar capabilities al rol
    all_jefe_caps = Capability.objects.filter(code__in=JEFE_UTP_CAPABILITIES)
    for cap in all_jefe_caps:
        RoleCapability.objects.get_or_create(
            role=role_obj,
            capability=cap,
            defaults={'is_granted': True},
        )


def noop_reverse(apps, schema_editor):
    # Conservamos datos para no romper producción en rollback.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_seed_user_management_scope_capabilities'),
    ]

    operations = [
        migrations.RunPython(seed_jefe_utp, noop_reverse),
    ]

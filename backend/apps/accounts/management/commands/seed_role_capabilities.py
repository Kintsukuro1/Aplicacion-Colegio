from django.core.management.base import BaseCommand

from backend.apps.accounts.services.capability_seed_service import seed_role_capabilities


class Command(BaseCommand):
    help = 'Crea/actualiza RoleCapability desde DEFAULT_CAPABILITIES_BY_ROLE.'

    def handle(self, *args, **options):
        summary = seed_role_capabilities()
        self.stdout.write(
            self.style.SUCCESS(
                'RoleCapability seed completado: '
                f"{summary['capabilities_created']} capabilities nuevas, "
                f"{summary['role_capabilities_created']} asignaciones nuevas, "
                f"{summary['role_capabilities_existing']} asignaciones existentes, "
                f"{summary['role_capabilities_denied']} denegaciones respetadas."
            )
        )

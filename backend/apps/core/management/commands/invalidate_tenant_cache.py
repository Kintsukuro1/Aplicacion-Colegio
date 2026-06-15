"""Invalida cache namespaced por tenant para evitar contaminacion cross-tenant."""

from django.core.management.base import BaseCommand

from backend.common.services.tenant_cache_service import TenantCacheService


class Command(BaseCommand):
    help = 'Invalidate tenant cache namespace for dashboard_summary (or all tenants).'

    def add_arguments(self, parser):
        parser.add_argument('--tenant-id', type=int, default=None, help='Tenant/colegio id (rbd).')
        parser.add_argument('--namespace', type=str, default='dashboard_summary', help='Cache namespace to invalidate.')

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        namespace = options.get('namespace')

        removed = TenantCacheService.invalidate_namespace(namespace, tenant_id=tenant_id)
        if tenant_id is None:
            self.stdout.write(self.style.SUCCESS(f'Invalidacion solicitada para namespace={namespace} en todos los tenants. keys={removed}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Invalidacion solicitada para namespace={namespace} tenant={tenant_id}. keys={removed}'))

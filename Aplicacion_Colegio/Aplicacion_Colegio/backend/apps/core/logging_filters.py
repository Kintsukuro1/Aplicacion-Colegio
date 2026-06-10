"""Filtros de logging para enriquecer trazabilidad operacional."""

from backend.common.utils.request_context import get_request_id


class RequestIdLogFilter:
    """Inyecta request_id en todos los log records."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True

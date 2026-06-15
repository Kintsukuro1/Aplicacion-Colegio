from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class StandardCursorPagination(CursorPagination):
    """Cursor pagination estable para movil, manteniendo `count` por compatibilidad de contrato."""

    page_size = 25
    ordering = "-pk"
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        # Mobile clients typically use `limit`; keep `page_size` for backward compatibility.
        raw_limit = request.query_params.get("limit")
        if raw_limit is not None:
            try:
                requested = int(raw_limit)
            except (TypeError, ValueError):
                requested = None

            if requested and requested > 0:
                return min(requested, self.max_page_size)

        return super().get_page_size(request)

    def paginate_queryset(self, queryset, request, view=None):
        self.total_count = queryset.count()
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response(
            {
                "count": getattr(self, "total_count", None),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )

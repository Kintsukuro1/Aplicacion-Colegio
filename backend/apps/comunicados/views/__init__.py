# comunicados/views/__init__.py
from .comunicados import (
    lista_comunicados,
    detalle_comunicado,
    crear_comunicado,
    estadisticas_comunicado,
)
from .confirmaciones import (
    confirmaciones_masivas,
    enviar_recordatorio_masivo,
)
from .estadisticas import (
    estadisticas_dashboard,
)
from .plantillas import (
    lista_plantillas,
    crear_plantilla,
    editar_plantilla,
    eliminar_plantilla,
    usar_plantilla,
)
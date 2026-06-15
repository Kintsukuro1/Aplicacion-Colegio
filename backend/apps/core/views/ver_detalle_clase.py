"""View delgada de detalle de clase: delega en servicio especializado."""

from django.contrib.auth.decorators import login_required
from backend.apps.core.services.class_detail_service import ClassDetailService


@login_required()
def ver_detalle_clase(request, clase_id):
    return ClassDetailService.handle_request(request, clase_id)


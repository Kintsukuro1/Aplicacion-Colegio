"""API de contexto para administrador general."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.institucion.models import Colegio
from backend.common.services.policy_service import PolicyService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_active_school_context(request):
    """
    GET /api/v1/admin/contexto-colegio/
    Devuelve el colegio activo en sesión para el administrador general.
    """
    if not PolicyService.has_capability(request.user, 'SYSTEM_ADMIN'):
        raise PermissionDenied('Solo administradores generales pueden consultar este contexto.')

    session_rbd = request.session.get('admin_rbd_activo')
    if not session_rbd:
        return Response({
            'activo': False,
            'rbd': None,
            'nombre': None,
        })

    colegio = Colegio.objects.filter(rbd=session_rbd).only('rbd', 'nombre').first()
    if not colegio:
        return Response({
            'activo': False,
            'rbd': None,
            'nombre': None,
        })

    session_name = request.session.get('admin_colegio_nombre')
    if session_name != colegio.nombre:
        request.session['admin_colegio_nombre'] = colegio.nombre
        request.session.modified = True

    return Response({
        'activo': True,
        'rbd': colegio.rbd,
        'nombre': colegio.nombre,
    })

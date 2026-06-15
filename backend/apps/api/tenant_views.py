from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from backend.apps.api.helpers import has_cap, is_global_admin
from backend.apps.institucion.models import Colegio


def _build_tenant_payload(colegio):
    logo_url = colegio.logo.url if getattr(colegio, 'logo', None) else None
    return {
        'id': colegio.rbd,
        'slug': colegio.slug,
        'nombre': colegio.nombre,
        'logo': logo_url,
        'color_primario': colegio.color_primario,
    }


def _resolve_tenant_from_request(request):
    colegio = getattr(request, 'tenant_school', None)
    if colegio is not None:
        return colegio

    slug = request.GET.get('slug')
    if slug:
        colegio = Colegio.objects.all_schools().filter(slug=slug).first()
        if colegio is not None:
            return colegio

    school_id = request.GET.get('rbd') or request.GET.get('colegio_id')
    if school_id:
        try:
            return Colegio.objects.all_schools().filter(rbd=int(school_id)).first()
        except (TypeError, ValueError):
            return None

    return None


@api_view(['GET'])
@permission_classes([AllowAny])
def tenant_info(request):
    colegio = _resolve_tenant_from_request(request)

    if colegio is None:
        return Response({'detail': 'Tenant no encontrado.'}, status=404)

    return Response(_build_tenant_payload(colegio))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tenant_config(request):
    user_school_id = getattr(request.user, 'rbd_colegio', None)
    colegio = None

    if is_global_admin(request.user):
        tenant_school_id = request.GET.get('colegio_id') or getattr(request, 'tenant_school_id', None)
        if tenant_school_id:
            colegio = Colegio.objects.all_schools().filter(rbd=tenant_school_id).first()
    else:
        if has_cap(request.user, 'SYSTEM_CONFIGURE') and user_school_id:
            colegio = Colegio.objects.all_schools().filter(rbd=user_school_id).first()

    if colegio is None:
        return Response({'detail': 'No autorizado para ver configuracion del tenant.'}, status=403)

    payload = _build_tenant_payload(colegio)
    payload.update(
        {
            'correo': colegio.correo,
            'telefono': colegio.telefono,
            'web': colegio.web,
            'direccion': colegio.direccion,
            'comuna': getattr(getattr(colegio, 'comuna', None), 'nombre', None),
        }
    )
    return Response(payload)

from rest_framework.permissions import BasePermission

from backend.common.services.policy_service import PolicyService


class HasCapability(BasePermission):
    """Valida capabilities declaradas por vista en `required_capability`."""

    message = 'No tiene permisos para esta operacion.'

    def has_permission(self, request, view):
        required_capability = getattr(view, 'required_capability', None)
        if not required_capability:
            return True
        return PolicyService.has_capability(
            request.user,
            required_capability,
            school_id=getattr(request.user, 'rbd_colegio', None),
        )

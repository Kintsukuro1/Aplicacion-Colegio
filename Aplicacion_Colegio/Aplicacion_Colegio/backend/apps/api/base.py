from rest_framework import viewsets


class CapabilityModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet que mapea actions DRF a capabilities del sistema."""

    action_capabilities = {}

    def get_permissions(self):
        # HasCapability inspecciona `required_capability` en la vista.
        self.required_capability = self.action_capabilities.get(self.action)
        return super().get_permissions()

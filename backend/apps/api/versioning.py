from rest_framework.exceptions import NotAcceptable
from rest_framework.versioning import AcceptHeaderVersioning


class QueryParamOrAcceptHeaderVersioning(AcceptHeaderVersioning):
    """Allows API version negotiation via query param for mobile clients.

    Priority:
    1. `?version=` query param
    2. `Accept` header version parameter
    3. DRF default version
    """

    query_param = 'version'

    def determine_version(self, request, *args, **kwargs):
        query_version = request.query_params.get(self.query_param)
        if query_version:
            if not self.is_allowed_version(query_version):
                raise NotAcceptable(self.invalid_version_message)
            return query_version
        return super().determine_version(request, *args, **kwargs)

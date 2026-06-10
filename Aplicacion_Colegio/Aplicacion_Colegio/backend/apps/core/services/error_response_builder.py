"""
Error response builder (capa core).

Implementación alineada al roadmap y compatible con el sistema
existente en backend.common.utils.error_response.
"""

from backend.common.utils.error_response import ErrorResponseBuilder as CommonErrorResponseBuilder


class ErrorResponseBuilder:
    """Builder estándar de respuestas de error en capa core."""

    @staticmethod
    def build(error_type, message=None, action=None, context=None):
        """
        Construye un error estructurado.

        Prioridad:
        1) Usa builder central común (fuente de verdad de mensajes)
        2) Si se pasa message/action, sobrescribe para casos específicos
        """
        context = context or {}

        try:
            base = CommonErrorResponseBuilder.build(error_type, context=context)
            response = {
                'error': True,
                'type': base.get('error_type', error_type),
                'message': message or base.get('user_message', 'Error de dominio'),
                'action': action or base.get('action_url'),
                'context': base.get('context', context),
            }
            return response
        except Exception:
            return {
                'error': True,
                'type': error_type,
                'message': message or 'Error de dominio',
                'action': action,
                'context': context,
            }

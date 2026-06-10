"""
Excepciones estándar del dominio (capa core).

Este módulo define excepciones estructuradas para el dominio,
alineadas al roadmap de hardening comercial.
"""


class DomainException(Exception):
    """
    Excepción base de dominio con payload estructurado.

    Args:
        error (dict): Error estructurado. Ejemplo:
            {
                'error': True,
                'type': 'DATA_INCONSISTENCY',
                'message': 'Se detectó inconsistencia',
                'action': '/admin/verificar_datos/'
            }
    """

    def __init__(self, error):
        self.error = error or {}
        message = self.error.get('message') or self.error.get('user_message') or 'Domain error'
        super().__init__(message)

    @property
    def error_type(self):
        """Retorna el tipo/código del error estructurado."""
        return self.error.get('type') or self.error.get('error_type')

    @property
    def action(self):
        """Retorna acción sugerida (URL o hint), si existe."""
        return self.error.get('action') or self.error.get('action_url')

    def to_dict(self):
        """Retorna payload serializable para respuestas/controladores."""
        return {
            'error': True,
            'type': self.error_type,
            'message': str(self),
            'action': self.action,
            'context': self.error.get('context', {}),
        }

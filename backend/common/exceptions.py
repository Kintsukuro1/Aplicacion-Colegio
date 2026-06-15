"""
Exceptions personalizadas para el sistema.

Este módulo define exceptions específicas del dominio
que encapsulan errores estructurados del ErrorResponseBuilder.
"""

from backend.common.utils.error_response import ErrorResponseBuilder


class PrerequisiteException(Exception):
    """
    Exception lanzada cuando faltan prerequisites para una acción.
    
    Esta exception encapsula un error estructurado de ErrorResponseBuilder,
    manteniendo una sola fuente de verdad para mensajes y action_urls.
    
    Usage:
        raise PrerequisiteException('MISSING_CICLO_ACTIVO', {'colegio_rbd': '12345'})
        
    En views:
        try:
            service_method()
        except PrerequisiteException as e:
            redirect_url = e.error.to_django_message(request)
            return redirect(redirect_url)
    """
    
    def __init__(self, error_type, context=None):
        """
        Inicializa la exception con un error estructurado.
        
        Args:
            error_type (str): Constante de error (ej: MISSING_CICLO_ACTIVO)
            context (dict, optional): Contexto adicional del error
        """
        self.error_type = error_type
        self.context = context or {}
        
        # Construir error estructurado internamente
        self.error = ErrorResponseBuilder.build(error_type, context)
        
        # Mensaje para Exception estándar de Python
        super().__init__(self.error['user_message'])
    
    def to_django_message(self, request):
        """
        Shortcut para agregar mensaje a Django messages.
        
        Args:
            request: HttpRequest de Django
            
        Returns:
            str: action_url para redirección
        """
        return ErrorResponseBuilder.to_django_message(request, self.error)


class ConfigurationError(Exception):
    """
    Exception para errores de configuración del sistema.
    
    Diferente a PrerequisiteException: esta es para configuración
    técnica incorrecta, no para pasos de onboarding faltantes.
    """
    pass


class BusinessRuleViolation(Exception):
    """
    Exception para violaciones de reglas de negocio.
    
    Ejemplo: Intentar matricular estudiante en curso de otro colegio,
             intentar evaluar en evaluación cerrada, etc.
    """
    
    def __init__(self, rule_violated, details=None):
        """
        Args:
            rule_violated (str): Descripción de la regla violada
            details (dict, optional): Detalles adicionales de la violación
        """
        self.rule_violated = rule_violated
        self.details = details or {}
        super().__init__(f"Regla de negocio violada: {rule_violated}")

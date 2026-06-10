"""
Tests unitarios para ErrorResponseBuilder.

Valida:
- Construcción correcta de objetos de error
- Mapeo de constantes a mensajes
- Resolución de action_urls
- Integración con Django messages framework
"""

import pytest
from django.contrib.messages import get_messages
from django.test import RequestFactory
from django.conf import settings

# Configurar Django settings si no están configurados
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='test-secret-key',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django.contrib.sessions',
            'django.contrib.messages',
        ],
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
    )

from backend.common.utils.error_response import (
    ErrorResponseBuilder,
    MISSING_CICLO_ACTIVO,
    MISSING_COURSES,
    MISSING_TEACHERS_ASSIGNED,
    MISSING_STUDENTS_ENROLLED,
    INVALID_PREREQUISITE,
    ERROR_MESSAGES,
    DEFAULT_ACTION_URL,
    validate_error_type,
    get_all_error_types,
)


class TestErrorResponseBuilder:
    """Tests para construcción de objetos de error."""
    
    def test_build_returns_complete_structure(self):
        """Verifica que build() retorna estructura completa."""
        error = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO)
        
        assert 'error_type' in error
        assert 'user_message' in error
        assert 'action_url' in error
        assert 'context' in error
        
    def test_build_uses_correct_error_type(self):
        """Verifica que error_type se preserva correctamente."""
        error = ErrorResponseBuilder.build(MISSING_COURSES)
        
        assert error['error_type'] == MISSING_COURSES
        
    def test_build_retrieves_correct_message(self):
        """Verifica que el mensaje corresponde al error_type."""
        error = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO)
        
        assert error['user_message'] == ERROR_MESSAGES[MISSING_CICLO_ACTIVO]
        assert 'Ciclo Académico activo' in error['user_message']
        
    def test_build_with_undefined_error_raises_exception(self):
        """Verifica que error_type no definido lanza KeyError."""
        with pytest.raises(KeyError) as exc_info:
            ErrorResponseBuilder.build('NONEXISTENT_ERROR')
        
        assert 'no está definido' in str(exc_info.value)
        
    def test_build_includes_context(self):
        """Verifica que el contexto se incluye en el error."""
        context = {'colegio_rbd': '12345', 'extra_data': 'test'}
        error = ErrorResponseBuilder.build(MISSING_COURSES, context=context)
        
        assert error['context'] == context
        assert error['context']['colegio_rbd'] == '12345'
        
    def test_build_with_no_context_uses_empty_dict(self):
        """Verifica que sin context se usa dict vacío."""
        error = ErrorResponseBuilder.build(MISSING_STUDENTS_ENROLLED)
        
        assert error['context'] == {}


class TestActionUrlResolution:
    """Tests para resolución de URLs de acción."""
    
    def test_action_url_uses_default_when_not_defined(self):
        """Verifica que usa DEFAULT_ACTION_URL si no hay mapeo."""
        error = ErrorResponseBuilder.build(INVALID_PREREQUISITE)
        
        assert error['action_url'] == DEFAULT_ACTION_URL
        
    def test_action_url_uses_custom_from_context(self):
        """Verifica que context['action_url'] tiene prioridad."""
        custom_url = '/custom/setup/page/'
        context = {'action_url': custom_url}
        error = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO, context=context)
        
        assert error['action_url'] == custom_url
        
    def test_action_url_mapped_for_each_error_type(self):
        """Verifica que errores principales tienen URL específica."""
        error_ciclo = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO)
        error_courses = ErrorResponseBuilder.build(MISSING_COURSES)
        
        # URLs deben ser diferentes y específicas
        assert error_ciclo['action_url'] != DEFAULT_ACTION_URL
        assert error_courses['action_url'] != DEFAULT_ACTION_URL
        assert error_ciclo['action_url'] != error_courses['action_url']


class TestDjangoMessagesIntegration:
    """Tests para integración con Django messages framework."""
    
    def test_to_django_message_adds_message(self):
        """Verifica que el mensaje se agrega a Django messages."""
        factory = RequestFactory()
        request = factory.get('/')
        
        # Django messages requiere session y messages middleware
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        
        error = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO)
        ErrorResponseBuilder.to_django_message(request, error)
        
        messages = list(get_messages(request))
        assert len(messages) == 1
        assert ERROR_MESSAGES[MISSING_CICLO_ACTIVO] in str(messages[0])
        
    def test_to_django_message_returns_action_url(self):
        """Verifica que retorna action_url para redirect."""
        factory = RequestFactory()
        request = factory.get('/')
        
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        
        error = ErrorResponseBuilder.build(MISSING_COURSES)
        redirect_url = ErrorResponseBuilder.to_django_message(request, error)
        
        assert redirect_url == error['action_url']
        
    def test_to_django_message_respects_level(self):
        """Verifica que se puede cambiar el nivel del mensaje."""
        factory = RequestFactory()
        request = factory.get('/')
        
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.messages import constants
        
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        
        error = ErrorResponseBuilder.build(MISSING_TEACHERS_ASSIGNED)
        ErrorResponseBuilder.to_django_message(request, error, level='warning')
        
        messages = list(get_messages(request))
        assert len(messages) == 1
        assert messages[0].level == constants.WARNING


class TestHelperFunctions:
    """Tests para funciones helper."""
    
    def test_validate_error_type_accepts_valid_types(self):
        """Verifica que validate_error_type acepta tipos válidos."""
        assert validate_error_type(MISSING_CICLO_ACTIVO) is True
        assert validate_error_type(MISSING_COURSES) is True
        
    def test_validate_error_type_rejects_invalid_types(self):
        """Verifica que validate_error_type rechaza tipos inválidos."""
        with pytest.raises(KeyError):
            validate_error_type('INVALID_TYPE')
            
    def test_get_all_error_types_returns_list(self):
        """Verifica que get_all_error_types retorna lista completa."""
        error_types = get_all_error_types()
        
        assert isinstance(error_types, list)
        assert MISSING_CICLO_ACTIVO in error_types
        assert MISSING_COURSES in error_types
        assert MISSING_TEACHERS_ASSIGNED in error_types
        assert MISSING_STUDENTS_ENROLLED in error_types
        
    def test_all_error_constants_have_messages(self):
        """Verifica que todas las constantes tienen mensaje definido."""
        error_types = get_all_error_types()
        
        for error_type in error_types:
            assert error_type in ERROR_MESSAGES
            assert len(ERROR_MESSAGES[error_type]) > 0


class TestErrorMessageQuality:
    """Tests para validar calidad de mensajes de error."""
    
    def test_messages_are_actionable(self):
        """Verifica que los mensajes son accionables, no genéricos."""
        for error_type, message in ERROR_MESSAGES.items():
            # Mensajes deben tener al menos 30 caracteres (no triviales)
            assert len(message) > 30
            # Mensajes deben dar contexto o acción
            assert any(keyword in message.lower() for keyword in [
                'debe', 'necesario', 'requiere', 'completa', 'verifica', 'contacta',
                'corrige', 'actualiza', 'antes de', 'puede', 'pueden',
                'inconsisten', 'inválid', 'depende'
            ])
            
    def test_onboarding_messages_explain_prerequisites(self):
        """Verifica que mensajes de onboarding explican qué falta."""
        onboarding_errors = [
            MISSING_CICLO_ACTIVO,
            MISSING_COURSES,
            MISSING_TEACHERS_ASSIGNED,
            MISSING_STUDENTS_ENROLLED,
        ]
        
        for error_type in onboarding_errors:
            message = ERROR_MESSAGES[error_type]
            # Deben mencionar "antes de continuar" o similar
            assert any(keyword in message.lower() for keyword in [
                'antes de', 'necesario', 'requerido', 'debe'
            ])

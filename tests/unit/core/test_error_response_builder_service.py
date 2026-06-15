from unittest.mock import patch

from backend.apps.core.services.error_response_builder import ErrorResponseBuilder


def test_build_uses_common_builder_defaults():
    with patch('backend.apps.core.services.error_response_builder.CommonErrorResponseBuilder.build', return_value={
        'error_type': 'INVALID_STATE',
        'user_message': 'Mensaje base',
        'action_url': '/accion',
        'context': {'k': 'v'},
    }):
        result = ErrorResponseBuilder.build('INVALID_STATE')

    assert result == {
        'error': True,
        'type': 'INVALID_STATE',
        'message': 'Mensaje base',
        'action': '/accion',
        'context': {'k': 'v'},
    }


def test_build_overrides_message_and_action():
    with patch('backend.apps.core.services.error_response_builder.CommonErrorResponseBuilder.build', return_value={
        'error_type': 'X',
        'user_message': 'base',
        'action_url': '/base',
        'context': {'base': 1},
    }):
        result = ErrorResponseBuilder.build('X', message='custom', action='/custom', context={'ctx': 2})

    assert result['message'] == 'custom'
    assert result['action'] == '/custom'
    assert result['context'] == {'base': 1}


def test_build_fallback_when_common_builder_fails():
    with patch('backend.apps.core.services.error_response_builder.CommonErrorResponseBuilder.build', side_effect=Exception('boom')):
        result = ErrorResponseBuilder.build('NOT_FOUND', context={'id': 1})

    assert result == {
        'error': True,
        'type': 'NOT_FOUND',
        'message': 'Error de dominio',
        'action': None,
        'context': {'id': 1},
    }

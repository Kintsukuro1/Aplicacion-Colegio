"""
Test simple de validación de ErrorResponseBuilder (sin framework de tests).
Ejecutar con: python test_error_response_simple.py
"""

import sys
import os

# Agregar path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.common.utils.error_response import (
    ErrorResponseBuilder,
    MISSING_CICLO_ACTIVO,
    MISSING_COURSES,
    MISSING_TEACHERS_ASSIGNED,
    MISSING_STUDENTS_ENROLLED,
    ERROR_MESSAGES,
    DEFAULT_ACTION_URL,
    get_all_error_types,
)


def test_build_returns_complete_structure():
    """Verifica que build() retorna estructura completa."""
    error = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO)
    
    assert 'error_type' in error, "Falta error_type"
    assert 'user_message' in error, "Falta user_message"
    assert 'action_url' in error, "Falta action_url"
    assert 'context' in error, "Falta context"
    print("✓ build() retorna estructura completa")


def test_build_uses_correct_error_type():
    """Verifica que error_type se preserva correctamente."""
    error = ErrorResponseBuilder.build(MISSING_COURSES)
    assert error['error_type'] == MISSING_COURSES, f"error_type incorrecto: {error['error_type']}"
    print("✓ error_type se preserva correctamente")


def test_build_retrieves_correct_message():
    """Verifica que el mensaje corresponde al error_type."""
    error = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO)
    expected_message = ERROR_MESSAGES[MISSING_CICLO_ACTIVO]
    
    assert error['user_message'] == expected_message, "Mensaje no coincide"
    assert 'Ciclo Académico activo' in error['user_message'], "Mensaje no menciona Ciclo Académico"
    print("✓ Mensaje correcto recuperado")


def test_build_with_undefined_error_raises_exception():
    """Verifica que error_type no definido lanza KeyError."""
    try:
        ErrorResponseBuilder.build('NONEXISTENT_ERROR')
        assert False, "Debería haber lanzado KeyError"
    except KeyError as e:
        assert 'no está definido' in str(e), f"Mensaje de error incorrecto: {e}"
        print("✓ Error no definido lanza KeyError apropiado")


def test_build_includes_context():
    """Verifica que el contexto se incluye en el error."""
    context = {'colegio_rbd': '12345', 'extra_data': 'test'}
    error = ErrorResponseBuilder.build(MISSING_COURSES, context=context)
    
    assert error['context'] == context, "Context no coincide"
    assert error['context']['colegio_rbd'] == '12345', "Campo context incorrecto"
    print("✓ Context se incluye correctamente")


def test_action_url_uses_default_when_not_defined():
    """Verifica que usa DEFAULT_ACTION_URL si no hay mapeo."""
    from backend.common.utils.error_response import INVALID_PREREQUISITE
    error = ErrorResponseBuilder.build(INVALID_PREREQUISITE)
    
    assert error['action_url'] == DEFAULT_ACTION_URL, f"URL incorrecta: {error['action_url']}"
    print("✓ URL default se usa correctamente")


def test_action_url_uses_custom_from_context():
    """Verifica que context['action_url'] tiene prioridad."""
    custom_url = '/custom/setup/page/'
    context = {'action_url': custom_url}
    error = ErrorResponseBuilder.build(MISSING_CICLO_ACTIVO, context=context)
    
    assert error['action_url'] == custom_url, f"URL custom no aplicada: {error['action_url']}"
    print("✓ URL custom desde context tiene prioridad")


def test_all_error_constants_have_messages():
    """Verifica que todas las constantes tienen mensaje definido."""
    error_types = get_all_error_types()
    
    assert len(error_types) > 0, "No hay error types definidos"
    
    for error_type in error_types:
        assert error_type in ERROR_MESSAGES, f"Error type {error_type} sin mensaje"
        assert len(ERROR_MESSAGES[error_type]) > 0, f"Mensaje vacío para {error_type}"
    
    print(f"✓ Todos los {len(error_types)} error types tienen mensajes")


def test_messages_are_actionable():
    """Verifica que los mensajes son accionables."""
    for error_type, message in ERROR_MESSAGES.items():
        assert len(message) > 30, f"Mensaje muy corto para {error_type}"
        
        # Mensajes deben dar contexto o acción
        has_action_word = any(keyword in message.lower() for keyword in [
            'debe', 'necesario', 'requiere', 'completa', 'verifica', 'contacta',
            'corrige', 'actualiza', 'antes de', 'puede', 'pueden',
            'inconsisten', 'inválid', 'depende'
        ])
        assert has_action_word, f"Mensaje no accionable para {error_type}: {message}"
    
    print("✓ Todos los mensajes son accionables")


def run_all_tests():
    """Ejecuta todos los tests."""
    print("="*70)
    print("TESTS DE VALIDACIÓN: ErrorResponseBuilder")
    print("="*70)
    print()
    
    tests = [
        test_build_returns_complete_structure,
        test_build_uses_correct_error_type,
        test_build_retrieves_correct_message,
        test_build_with_undefined_error_raises_exception,
        test_build_includes_context,
        test_action_url_uses_default_when_not_defined,
        test_action_url_uses_custom_from_context,
        test_all_error_constants_have_messages,
        test_messages_are_actionable,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: ERROR - {e}")
            failed += 1
    
    print()
    print("="*70)
    print(f"RESULTADOS: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

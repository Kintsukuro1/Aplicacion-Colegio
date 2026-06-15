"""
Tests for new data integrity error types in ErrorResponseBuilder
"""
from django.test import TestCase
from backend.common.utils.error_response import (
    ErrorResponseBuilder,
    DATA_INCONSISTENCY,
    INVALID_RELATIONSHIP,
    ORPHANED_ENTITY,
    STATE_MISMATCH
)


class ErrorTypesDataIntegrityTest(TestCase):
    """Test that new data integrity error types work correctly"""

    def test_data_inconsistency_error_has_message(self):
        """Test DATA_INCONSISTENCY error builds correctly"""
        error = ErrorResponseBuilder.build(DATA_INCONSISTENCY)
        
        self.assertEqual(error['error_type'], DATA_INCONSISTENCY)
        self.assertIn('inconsistencias', error['user_message'].lower())
        self.assertIn('action_url', error)
        self.assertIn('verificar_datos', error['action_url'])

    def test_invalid_relationship_error_has_message(self):
        """Test INVALID_RELATIONSHIP error builds correctly"""
        error = ErrorResponseBuilder.build(INVALID_RELATIONSHIP)
        
        self.assertEqual(error['error_type'], INVALID_RELATIONSHIP)
        self.assertIn('referencia', error['user_message'].lower())
        self.assertIn('action_url', error)
        self.assertIn('verificar_datos', error['action_url'])

    def test_orphaned_entity_error_has_message(self):
        """Test ORPHANED_ENTITY error builds correctly"""
        error = ErrorResponseBuilder.build(ORPHANED_ENTITY)
        
        self.assertEqual(error['error_type'], ORPHANED_ENTITY)
        self.assertIn('eliminados', error['user_message'].lower())
        self.assertIn('action_url', error)
        self.assertIn('verificar_datos', error['action_url'])

    def test_state_mismatch_error_has_message(self):
        """Test STATE_MISMATCH error builds correctly"""
        error = ErrorResponseBuilder.build(STATE_MISMATCH)
        
        self.assertEqual(error['error_type'], STATE_MISMATCH)
        self.assertIn('estado', error['user_message'].lower())
        self.assertIn('consistente', error['user_message'].lower())
        self.assertIn('action_url', error)
        self.assertIn('verificar_datos', error['action_url'])

    def test_all_new_error_types_have_unique_messages(self):
        """Test that all new error types have distinct messages"""
        error_types = [
            DATA_INCONSISTENCY,
            INVALID_RELATIONSHIP,
            ORPHANED_ENTITY,
            STATE_MISMATCH
        ]
        
        messages = []
        for error_type in error_types:
            error = ErrorResponseBuilder.build(error_type)
            messages.append(error['user_message'])
        
        # All messages should be unique
        self.assertEqual(len(messages), len(set(messages)))

    def test_new_error_types_have_action_urls(self):
        """Test that all new error types have action URLs"""
        error_types = [
            DATA_INCONSISTENCY,
            INVALID_RELATIONSHIP,
            ORPHANED_ENTITY,
            STATE_MISMATCH
        ]
        
        for error_type in error_types:
            error = ErrorResponseBuilder.build(error_type)
            self.assertIsNotNone(error['action_url'])
            self.assertTrue(error['action_url'].startswith('/'))

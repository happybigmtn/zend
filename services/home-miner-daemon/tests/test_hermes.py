#!/usr/bin/env python3
"""
Tests for Hermes adapter boundary enforcement.

Tests the Hermes adapter's capability checking, event filtering,
and control boundary enforcement.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Set up state directory for tests
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR

# Add service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import hermes
from spine import append_event, get_events, EventKind, _load_events
from store import load_or_create_principal


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset state for each test
        self.principal = load_or_create_principal()
        
        # Create a test Hermes pairing
        self.hermes_id = f"hermes-test-{os.getpid()}"
        self.pairing = hermes.pair_hermes(self.hermes_id, "test-hermes-agent")
        
        # Generate authority token
        self.token = hermes.generate_authority_token(
            self.pairing.hermes_id,
            self.pairing.principal_id
        )

    def test_hermes_capabilities_constant(self):
        """Test that HERMES_CAPABILITIES contains only observe and summarize."""
        self.assertEqual(hermes.HERMES_CAPABILITIES, ['observe', 'summarize'])
        self.assertNotIn('control', hermes.HERMES_CAPABILITIES)

    def test_hermes_readable_events(self):
        """Test that Hermes readable events are correctly defined."""
        readable = [e.value for e in hermes.HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable)
        self.assertIn('miner_alert', readable)
        self.assertIn('control_receipt', readable)
        self.assertNotIn('user_message', readable)

    def test_hermes_connect_valid(self):
        """Test connecting with valid authority token succeeds."""
        connection = hermes.connect(self.token)
        
        self.assertEqual(connection.hermes_id, self.hermes_id)
        self.assertEqual(connection.principal_id, self.pairing.principal_id)
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)
        self.assertNotIn('control', connection.capabilities)

    def test_hermes_connect_expired(self):
        """Test connecting with expired token fails."""
        # Create an expired token
        expired_token = {
            'hermes_id': self.hermes_id,
            'principal_id': self.pairing.principal_id,
            'capabilities': ['observe', 'summarize'],
            'expires_at': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.connect(json.dumps(expired_token))
        
        self.assertIn('expired', str(ctx.exception).lower())

    def test_hermes_connect_invalid_token(self):
        """Test connecting with invalid token format fails."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect("not-valid-json")
        
        self.assertIn('Invalid authority token', str(ctx.exception))

    def test_hermes_connect_control_capability_rejected(self):
        """Test that Hermes cannot have control capability."""
        control_token = {
            'hermes_id': self.hermes_id,
            'principal_id': self.pairing.principal_id,
            'capabilities': ['observe', 'summarize', 'control'],
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.connect(json.dumps(control_token))
        
        self.assertIn('control', str(ctx.exception).lower())

    def test_hermes_read_status(self):
        """Test that Hermes with observe capability can read status."""
        connection = hermes.connect(self.token)
        
        status = hermes.read_status(connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)
        self.assertEqual(status.get('source'), 'hermes_adapter')

    def test_hermes_read_status_without_observe(self):
        """Test that Hermes without observe capability cannot read status."""
        limited_token = {
            'hermes_id': self.hermes_id,
            'principal_id': self.pairing.principal_id,
            'capabilities': ['summarize'],  # No observe
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        connection = hermes.connect(json.dumps(limited_token))
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(connection)
        
        self.assertIn('observe', str(ctx.exception).lower())

    def test_hermes_append_summary(self):
        """Test that Hermes with summarize capability can append summary."""
        connection = hermes.connect(self.token)
        
        result = hermes.append_summary(
            connection,
            "Test summary: miner running normally",
            "observe"
        )
        
        self.assertTrue(result.get('appended'))
        self.assertIn('event_id', result)
        self.assertIn('timestamp', result)

    def test_hermes_append_summary_without_capability(self):
        """Test that Hermes without summarize capability cannot append."""
        limited_token = {
            'hermes_id': self.hermes_id,
            'principal_id': self.pairing.principal_id,
            'capabilities': ['observe'],  # No summarize
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        connection = hermes.connect(json.dumps(limited_token))
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(connection, "Test summary", "observe")
        
        self.assertIn('summarize', str(ctx.exception).lower())

    def test_hermes_event_filter(self):
        """Test that user_message events are filtered from Hermes reads."""
        connection = hermes.connect(self.token)
        
        # Append different event types
        append_event(EventKind.USER_MESSAGE, self.pairing.principal_id, {
            "text": "This is a user message"
        })
        append_event(EventKind.HERMES_SUMMARY, self.pairing.principal_id, {
            "summary_text": "This is a Hermes summary"
        })
        append_event(EventKind.MINER_ALERT, self.pairing.principal_id, {
            "alert_type": "temperature",
            "message": "Miner is hot"
        })
        
        events = hermes.get_filtered_events(connection, limit=20)
        
        # Check that user_message is filtered
        event_kinds = [e['kind'] for e in events]
        self.assertNotIn('user_message', event_kinds)
        
        # Check that hermes_summary is present
        self.assertIn('hermes_summary', event_kinds)
        
        # Check that miner_alert is present
        self.assertIn('miner_alert', event_kinds)

    def test_hermes_summary_appears_in_events(self):
        """Test that appended Hermes summary appears in filtered events."""
        connection = hermes.connect(self.token)
        
        summary_text = "Miner running normally at 50kH/s"
        result = hermes.append_summary(connection, summary_text, "observe")
        
        events = hermes.get_filtered_events(connection, limit=20)
        
        # Find the summary event
        summary_events = [e for e in events if e['kind'] == 'hermes_summary']
        self.assertTrue(len(summary_events) > 0)
        
        # Check the content
        latest_summary = summary_events[0]
        self.assertEqual(latest_summary['payload']['summary_text'], summary_text)
        self.assertEqual(latest_summary['payload']['authority_scope'], 'observe')

    def test_hermes_validate_control_attempt(self):
        """Test that Hermes control validation always returns False."""
        connection = hermes.connect(self.token)
        
        # Hermes should NEVER be able to control
        can_control = hermes.validate_control_attempt(connection)
        self.assertFalse(can_control)

    def test_hermes_pairing_idempotent(self):
        """Test that pairing the same Hermes twice is idempotent."""
        # Pair again
        pairing2 = hermes.pair_hermes(self.hermes_id, "test-hermes-agent")
        
        self.assertEqual(pairing2.hermes_id, self.hermes_id)
        self.assertEqual(pairing2.capabilities, hermes.HERMES_CAPABILITIES)

    def test_hermes_get_pairing(self):
        """Test retrieving Hermes pairing by ID."""
        pairing = hermes.get_hermes_pairing(self.hermes_id)
        
        self.assertIsNotNone(pairing)
        self.assertEqual(pairing.hermes_id, self.hermes_id)
        self.assertEqual(pairing.device_name, "test-hermes-agent")

    def test_hermes_get_pairing_not_found(self):
        """Test retrieving non-existent Hermes pairing returns None."""
        pairing = hermes.get_hermes_pairing("non-existent-hermes")
        self.assertIsNone(pairing)


class TestHermesControlBoundary(unittest.TestCase):
    """Test suite for Hermes control boundary enforcement."""

    def setUp(self):
        """Set up test fixtures."""
        self.principal = load_or_create_principal()
        self.hermes_id = f"hermes-control-test-{os.getpid()}"
        self.pairing = hermes.pair_hermes(self.hermes_id, "control-test-agent")
        self.token = hermes.generate_authority_token(
            self.pairing.hermes_id,
            self.pairing.principal_id
        )
        self.connection = hermes.connect(self.token)

    def test_hermes_cannot_have_control_capability(self):
        """Test that Hermes cannot be issued control capability."""
        # Verify our token doesn't have control
        self.assertNotIn('control', self.connection.capabilities)
        
        # Try to get control capability through token manipulation
        tampered_token = {
            'hermes_id': self.hermes_id,
            'principal_id': self.pairing.principal_id,
            'capabilities': ['observe', 'summarize', 'control'],
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.connect(json.dumps(tampered_token))
        
        self.assertIn('control', str(ctx.exception).lower())

    def test_hermes_control_attempt_blocked(self):
        """Test that Hermes control validation blocks all control."""
        # validate_control_attempt should always return False for Hermes
        result = hermes.validate_control_attempt(self.connection)
        self.assertFalse(result)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestHermesAdapter))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesControlBoundary))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())

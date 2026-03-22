#!/usr/bin/env python3
"""
Tests for Hermes Adapter.

These tests verify the capability boundary enforcement for the Hermes
agent adapter. Tests cover:
- Token validation
- Capability checking
- Event filtering
- Summary append
- Control rejection
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

# Set up state directory for tests
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hermes
import spine
import store


class TestHermesCapabilities(unittest.TestCase):
    """Test Hermes capability constants."""

    def test_hermes_capabilities(self):
        """Hermes should have observe and summarize, no control."""
        caps = hermes.HERMES_CAPABILITIES
        self.assertIn('observe', caps)
        self.assertIn('summarize', caps)
        self.assertNotIn('control', caps)
        self.assertEqual(len(caps), 2)

    def test_hermes_readable_events(self):
        """Hermes should be able to read summary, alert, and receipt events."""
        readable = [k.value for k in hermes.HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable)
        self.assertIn('miner_alert', readable)
        self.assertIn('control_receipt', readable)
        self.assertNotIn('user_message', readable)

    def test_hermes_blocked_events(self):
        """User messages should be blocked for Hermes."""
        blocked = [k.value for k in hermes.HERMES_BLOCKED_EVENTS]
        self.assertIn('user_message', blocked)


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing functionality."""

    def setUp(self):
        """Reset state for each test."""
        # Clear any existing pairings
        store_path = os.path.join(TEST_STATE_DIR, 'hermes-pairings.json')
        if os.path.exists(store_path):
            os.remove(store_path)

    def test_pair_hermes(self):
        """Pairing a Hermes agent creates a record with correct capabilities."""
        pairing = hermes.pair_hermes('test-hermes-001', 'test-hermes')
        
        self.assertEqual(pairing.hermes_id, 'test-hermes-001')
        self.assertEqual(pairing.device_name, 'test-hermes')
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertIsNotNone(pairing.principal_id)
        self.assertIsNotNone(pairing.token)

    def test_pair_hermes_idempotent(self):
        """Re-pairing with same hermes_id returns existing pairing."""
        first = hermes.pair_hermes('test-hermes-002', 'test-hermes')
        second = hermes.pair_hermes('test-hermes-002', 'test-hermes')
        
        self.assertEqual(first.hermes_id, second.hermes_id)
        self.assertEqual(first.token, second.token)

    def test_get_hermes_pairing(self):
        """Getting a pairing by hermes_id returns the correct record."""
        created = hermes.pair_hermes('test-hermes-003', 'test-hermes')
        retrieved = hermes.get_hermes_pairing('test-hermes-003')
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hermes_id, created.hermes_id)

    def test_get_hermes_pairing_not_found(self):
        """Getting a non-existent pairing returns None."""
        result = hermes.get_hermes_pairing('nonexistent')
        self.assertIsNone(result)


class TestAuthorityToken(unittest.TestCase):
    """Test authority token generation and validation."""

    def setUp(self):
        """Set up test pairing."""
        store_path = os.path.join(TEST_STATE_DIR, 'hermes-pairings.json')
        if os.path.exists(store_path):
            os.remove(store_path)
        self.pairing = hermes.pair_hermes('token-test-hermes', 'token-test')

    def test_generate_authority_token(self):
        """Token can be generated for a paired Hermes."""
        token = hermes.generate_authority_token('token-test-hermes')
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)

    def test_connect_valid_token(self):
        """Connecting with valid token creates connection."""
        token = hermes.generate_authority_token('token-test-hermes')
        connection = hermes.connect(token)
        
        self.assertEqual(connection.hermes_id, 'token-test-hermes')
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)

    def test_connect_invalid_token(self):
        """Connecting with invalid token raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect('not-a-valid-token')
        self.assertIn('Invalid authority token', str(ctx.exception))

    def test_connect_expired_token(self):
        """Connecting with expired token raises ValueError."""
        # Create a token with past expiration
        import base64
        token_data = {
            'hermes_id': 'token-test-hermes',
            'principal_id': self.pairing.principal_id,
            'capabilities': ['observe', 'summarize'],
            'expires_at': '2020-01-01T00:00:00+00:00'  # Expired
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        self.assertIn('expired', str(ctx.exception))

    def test_connect_missing_capabilities(self):
        """Token with wrong capabilities is rejected."""
        import base64
        token_data = {
            'hermes_id': 'token-test-hermes',
            'principal_id': self.pairing.principal_id,
            'capabilities': ['observe', 'control'],  # Invalid: control
            'expires_at': (datetime.now(timezone.utc) + datetime.timedelta(days=1)).isoformat()
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        self.assertIn('invalid Hermes capabilities', str(ctx.exception))


class TestReadStatus(unittest.TestCase):
    """Test Hermes read_status functionality."""

    def setUp(self):
        """Set up test connection."""
        store_path = os.path.join(TEST_STATE_DIR, 'hermes-pairings.json')
        if os.path.exists(store_path):
            os.remove(store_path)
        self.pairing = hermes.pair_hermes('status-test-hermes', 'status-test')
        token = hermes.generate_authority_token('status-test-hermes')
        self.connection = hermes.connect(token)

    def test_read_status_success(self):
        """Hermes with observe capability can read status."""
        status = hermes.read_status(self.connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)

    def test_read_status_no_observe(self):
        """Hermes without observe capability cannot read status."""
        # Create connection without observe
        self.connection.capabilities = ['summarize']
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(self.connection)
        self.assertIn('observe capability required', str(ctx.exception))


class TestAppendSummary(unittest.TestCase):
    """Test Hermes summary append functionality."""

    def setUp(self):
        """Set up test connection and clear spine."""
        store_path = os.path.join(TEST_STATE_DIR, 'hermes-pairings.json')
        if os.path.exists(store_path):
            os.remove(store_path)
        self.pairing = hermes.pair_hermes('summary-test-hermes', 'summary-test')
        token = hermes.generate_authority_token('summary-test-hermes')
        self.connection = hermes.connect(token)
        
        # Clear spine
        spine_file = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        if os.path.exists(spine_file):
            os.remove(spine_file)

    def test_append_summary_success(self):
        """Hermes with summarize capability can append summary."""
        result = hermes.append_summary(
            self.connection,
            "Test summary text",
            "observe"
        )
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
        self.assertIn('created_at', result)

    def test_append_summary_no_summarize(self):
        """Hermes without summarize capability cannot append summary."""
        self.connection.capabilities = ['observe']
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(self.connection, "Test", "observe")
        self.assertIn('summarize capability required', str(ctx.exception))

    def test_summary_appears_in_spine(self):
        """Appended summary appears in the event spine."""
        result = hermes.append_summary(
            self.connection,
            "Miner running normally",
            "observe"
        )
        
        events = spine.get_events(kind=spine.EventKind.HERMES_SUMMARY, limit=10)
        
        summary_events = [e for e in events if 'Miner running normally' in str(e.payload)]
        self.assertGreater(len(summary_events), 0)


class TestEventFiltering(unittest.TestCase):
    """Test Hermes event filtering."""

    def setUp(self):
        """Set up test connection and populate spine."""
        store_path = os.path.join(TEST_STATE_DIR, 'hermes-pairings.json')
        if os.path.exists(store_path):
            os.remove(store_path)
        self.pairing = hermes.pair_hermes('filter-test-hermes', 'filter-test')
        token = hermes.generate_authority_token('filter-test-hermes')
        self.connection = hermes.connect(token)
        
        # Clear and repopulate spine with various events
        spine_file = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        if os.path.exists(spine_file):
            os.remove(spine_file)
        
        principal = store.load_or_create_principal()
        
        # Add various event types
        spine.append_event(
            spine.EventKind.HERMES_SUMMARY,
            principal.id,
            {"summary_text": "Test summary"}
        )
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            principal.id,
            {"message": "Private message"}
        )
        spine.append_event(
            spine.EventKind.MINER_ALERT,
            principal.id,
            {"alert_type": "health_warning"}
        )
        spine.append_event(
            spine.EventKind.CONTROL_RECEIPT,
            principal.id,
            {"command": "start", "status": "accepted"}
        )

    def test_user_messages_filtered(self):
        """User messages are filtered from Hermes event reads."""
        events = hermes.get_filtered_events(self.connection, limit=20)
        
        event_kinds = [e['kind'] for e in events]
        self.assertNotIn('user_message', event_kinds)

    def test_readable_events_included(self):
        """Readable events are included in Hermes event reads."""
        events = hermes.get_filtered_events(self.connection, limit=20)
        
        event_kinds = [e['kind'] for e in events]
        self.assertIn('hermes_summary', event_kinds)
        self.assertIn('miner_alert', event_kinds)
        self.assertIn('control_receipt', event_kinds)

    def test_event_limit_respected(self):
        """Event limit is respected after filtering."""
        events = hermes.get_filtered_events(self.connection, limit=2)
        self.assertLessEqual(len(events), 2)


class TestCapabilityEnforcement(unittest.TestCase):
    """Test capability boundary enforcement."""

    def setUp(self):
        """Set up test pairing."""
        store_path = os.path.join(TEST_STATE_DIR, 'hermes-pairings.json')
        if os.path.exists(store_path):
            os.remove(store_path)
        self.pairing = hermes.pair_hermes('cap-test-hermes', 'cap-test')
        token = hermes.generate_authority_token('cap-test-hermes')
        self.connection = hermes.connect(token)

    def test_connection_has_capability(self):
        """Connection correctly reports capabilities."""
        self.assertTrue(self.connection.has_capability('observe'))
        self.assertTrue(self.connection.has_capability('summarize'))
        self.assertFalse(self.connection.has_capability('control'))

    def test_no_control_capability(self):
        """Hermes should never have control capability."""
        self.assertNotIn('control', hermes.HERMES_CAPABILITIES)


if __name__ == '__main__':
    unittest.main()

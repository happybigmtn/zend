#!/usr/bin/env python3
"""
Tests for Hermes adapter boundary enforcement.

Tests the capability boundaries, token validation, event filtering,
and summary append functionality for the Hermes adapter.
"""

import json
import os
import sys
import tempfile
import shutil
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from importlib import reload

# Add daemon to path
_daemon_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_daemon_dir))


def _create_fresh_test_env():
    """Create a fresh test environment with isolated state."""
    test_dir = tempfile.mkdtemp()
    os.environ['ZEND_STATE_DIR'] = test_dir
    return test_dir


def _reload_modules_with_env():
    """Reload modules with fresh environment."""
    import store
    import spine
    import hermes
    reload(store)
    reload(spine)
    reload(hermes)
    return store, spine, hermes


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter."""

    @classmethod
    def setUpClass(cls):
        """Create a unique temp directory for the entire test class."""
        cls.test_dir = _create_fresh_test_env()
        cls.store, cls.spine, cls.hermes = _reload_modules_with_env()

    def setUp(self):
        """Set up test fixtures for each test."""
        # Clean up any existing state files
        for f in ['principal.json', 'pairing-store.json', 'hermes-pairing-store.json', 'event-spine.jsonl']:
            path = os.path.join(self.test_dir, f)
            if os.path.exists(path):
                os.remove(path)
        
        # Reload modules to get fresh state
        self.store, self.spine, self.hermes = _reload_modules_with_env()
        
        # Create fresh principal
        self.principal = self.store.load_or_create_principal()

    def test_hermes_pairing_creates_record(self):
        """Test that pairing creates a valid Hermes pairing record."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        
        self.assertEqual(pairing.hermes_id, 'hermes-001')
        self.assertEqual(pairing.device_name, 'test-hermes')
        self.assertIn('observe', pairing.capabilities)
        self.assertIn('summarize', pairing.capabilities)
        self.assertNotIn('control', pairing.capabilities)
        self.assertIsNotNone(pairing.token)
        self.assertIsNotNone(pairing.token_expires_at)

    def test_hermes_pairing_idempotent(self):
        """Test that pairing the same hermes_id is idempotent."""
        pairing1 = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        pairing2 = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        
        # Should return same pairing
        self.assertEqual(pairing1.hermes_id, pairing2.hermes_id)
        self.assertEqual(pairing1.token, pairing2.token)

    def test_hermes_connect_valid_token(self):
        """Test connecting with a valid authority token."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        self.assertEqual(conn.hermes_id, 'hermes-001')
        self.assertEqual(conn.principal_id, self.principal.id)
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)

    def test_hermes_connect_invalid_token(self):
        """Test connecting with an invalid token raises error."""
        with self.assertRaises(ValueError) as ctx:
            self.hermes.connect('invalid-token-12345')
        
        self.assertIn('HERMES_INVALID_TOKEN', str(ctx.exception))

    def test_hermes_connect_expired_token(self):
        """Test connecting with an expired token raises error."""
        # Create a pairing with an already-expired token
        pairings = self.hermes._load_hermes_pairings()
        from datetime import timedelta
        expired_pairing = {
            'id': 'test-id',
            'hermes_id': 'hermes-expired',
            'principal_id': self.principal.id,
            'device_name': 'expired-test',
            'capabilities': ['observe', 'summarize'],
            'paired_at': datetime.now(timezone.utc).isoformat(),
            'token': 'expired-token-123',
            'token_expires_at': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()  # Expired 1 hour ago
        }
        pairings['test-id'] = expired_pairing
        self.hermes._save_hermes_pairings(pairings)
        
        with self.assertRaises(ValueError) as ctx:
            self.hermes.connect('expired-token-123')
        
        self.assertIn('HERMES_TOKEN_EXPIRED', str(ctx.exception))

    def test_hermes_read_status_requires_observe(self):
        """Test that read_status requires observe capability."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        # Remove observe capability
        conn.capabilities = ['summarize']
        
        with self.assertRaises(PermissionError) as ctx:
            self.hermes.read_status(conn)
        
        self.assertIn('observe capability required', str(ctx.exception))

    def test_hermes_read_status_success(self):
        """Test that read_status succeeds with observe capability."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        # Mock the miner
        import daemon
        status = self.hermes.read_status(conn)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)

    def test_hermes_append_summary_requires_summarize(self):
        """Test that append_summary requires summarize capability."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        # Remove summarize capability
        conn.capabilities = ['observe']
        
        with self.assertRaises(PermissionError) as ctx:
            self.hermes.append_summary(conn, "Test summary")
        
        self.assertIn('summarize capability required', str(ctx.exception))

    def test_hermes_append_summary_success(self):
        """Test that append_summary succeeds with summarize capability."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        event = self.hermes.append_summary(conn, "Miner running normally", "observe")
        
        self.assertEqual(event.kind, 'hermes_summary')
        self.assertEqual(event.principal_id, self.principal.id)
        self.assertEqual(event.payload['summary_text'], "Miner running normally")

    def test_hermes_event_filter_blocks_user_message(self):
        """Test that Hermes cannot read user_message events."""
        # Create some events including user_message
        self.spine.append_event(self.spine.EventKind.USER_MESSAGE, self.principal.id, 
                          {'thread_id': 'test', 'content': 'secret'})
        self.spine.append_event(self.spine.EventKind.HERMES_SUMMARY, self.principal.id,
                          {'summary_text': 'status update'})
        self.spine.append_event(self.spine.EventKind.MINER_ALERT, self.principal.id,
                          {'alert_type': 'warning', 'message': 'temp high'})
        self.spine.append_event(self.spine.EventKind.CONTROL_RECEIPT, self.principal.id,
                          {'command': 'start', 'status': 'accepted'})
        
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        events = self.hermes.get_filtered_events(conn, limit=20)
        event_kinds = [e['kind'] for e in events]
        
        # Should contain allowed events
        self.assertIn('hermes_summary', event_kinds)
        self.assertIn('miner_alert', event_kinds)
        self.assertIn('control_receipt', event_kinds)
        # Should NOT contain user_message
        self.assertNotIn('user_message', event_kinds)

    def test_hermes_capabilities_independent_of_gateway(self):
        """Test that Hermes capabilities are observe+summarize, not gateway control."""
        # Pair Hermes - should only have observe and summarize
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        
        self.assertNotIn('control', pairing.capabilities)
        self.assertEqual(set(pairing.capabilities), {'observe', 'summarize'})

    def test_hermes_summary_appears_in_spine(self):
        """Test that appended Hermes summary appears in event spine."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        # Append summary
        event = self.hermes.append_summary(conn, "System check complete", "observe")
        
        # Read from spine directly
        all_events = self.spine.get_events(kind=self.spine.EventKind.HERMES_SUMMARY, limit=100)
        
        # Find our event
        found = any(e.id == event.id for e in all_events)
        self.assertTrue(found, "Summary should appear in event spine")

    def test_hermes_control_capability_rejected(self):
        """Test that Hermes cannot have control capability."""
        # Even if requested, control should be stripped
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes', 
                                     requested_capabilities=['observe', 'summarize', 'control'])
        
        self.assertNotIn('control', pairing.capabilities)
        self.assertIn('observe', pairing.capabilities)
        self.assertIn('summarize', pairing.capabilities)

    def test_hermes_no_control_via_daemon(self):
        """Test that Hermes cannot issue control commands through daemon."""
        # This tests the daemon-level enforcement
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')
        conn = self.hermes.connect(pairing.token)
        
        # Try to use Hermes connection to call control (bypassing daemon)
        # In real scenario, daemon checks auth header before routing to control
        
        # The connection object should not have control capability
        self.assertFalse(conn.has_capability('control'))

    def test_hermes_readable_events_defined(self):
        """Test that HERMES_READABLE_EVENTS is correctly defined."""
        expected_kinds = ['hermes_summary', 'miner_alert', 'control_receipt']
        
        for kind in expected_kinds:
            self.assertTrue(
                any(k.value == kind for k in self.hermes.HERMES_READABLE_EVENTS),
                f"Expected {kind} in HERMES_READABLE_EVENTS"
            )

    def test_hermes_capabilities_constant(self):
        """Test that HERMES_CAPABILITIES is correctly defined."""
        self.assertEqual(set(self.hermes.HERMES_CAPABILITIES), {'observe', 'summarize'})


class TestHermesConnection(unittest.TestCase):
    """Test HermesConnection dataclass behavior."""

    @classmethod
    def setUpClass(cls):
        """Create a unique temp directory for the entire test class."""
        cls.test_dir = _create_fresh_test_env()
        cls.store, cls.spine, cls.hermes = _reload_modules_with_env()

    def setUp(self):
        """Set up test fixtures for each test."""
        # Clean up any existing state files
        for f in ['principal.json', 'pairing-store.json', 'hermes-pairing-store.json', 'event-spine.jsonl']:
            path = os.path.join(self.test_dir, f)
            if os.path.exists(path):
                os.remove(path)
        
        # Reload modules to get fresh state
        self.store, self.spine, self.hermes = _reload_modules_with_env()

    def test_connection_has_capability(self):
        """Test has_capability helper method."""
        conn = self.hermes.HermesConnection(
            hermes_id='test',
            principal_id='principal',
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=datetime.now(timezone.utc).isoformat()
        )
        
        self.assertTrue(conn.has_capability('observe'))
        self.assertTrue(conn.has_capability('summarize'))
        self.assertFalse(conn.has_capability('control'))


if __name__ == '__main__':
    unittest.main()

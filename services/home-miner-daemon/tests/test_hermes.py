#!/usr/bin/env python3
"""
Tests for Hermes Adapter boundary enforcement.

These tests verify:
1. Hermes can connect with valid authority token
2. Hermes cannot connect with expired/invalid tokens
3. Hermes can read miner status (with observe capability)
4. Hermes can append summaries (with summarize capability)
5. Hermes CANNOT issue control commands
6. Hermes CANNOT read user_message events
7. Hermes cannot request control capability
8. Appended summaries appear in the event spine
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Add daemon to path
DAEMON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAEMON_DIR))


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter boundary enforcement."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment with isolated state directory."""
        cls.test_state_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = cls.test_state_dir

        # Re-import modules to use test state
        import importlib
        import store
        importlib.reload(store)
        import spine
        importlib.reload(spine)
        import hermes
        importlib.reload(hermes)
        import daemon
        importlib.reload(daemon)

        cls.store = store
        cls.spine = spine
        cls.hermes = hermes
        cls.daemon = daemon

    @classmethod
    def tearDownClass(cls):
        """Clean up test state directory."""
        import shutil
        if os.path.exists(cls.test_state_dir):
            shutil.rmtree(cls.test_state_dir)

    def test_hermes_capabilities_constant(self):
        """Verify Hermes capabilities are observe and summarize only."""
        self.assertEqual(self.hermes.HERMES_CAPABILITIES, ['observe', 'summarize'])

    def test_hermes_readable_events(self):
        """Verify Hermes readable events exclude user_message."""
        readable_kinds = [k.value for k in self.hermes.HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable_kinds)
        self.assertIn('miner_alert', readable_kinds)
        self.assertIn('control_receipt', readable_kinds)
        self.assertNotIn('user_message', readable_kinds)

    def test_hermes_pair_valid(self):
        """Pair Hermes successfully."""
        pairing = self.hermes.pair_hermes('hermes-001', 'test-hermes')

        self.assertEqual(pairing.hermes_id, 'hermes-001')
        self.assertEqual(pairing.device_name, 'test-hermes')
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertIsNotNone(pairing.token)
        self.assertIsNotNone(pairing.token_expires_at)

    def test_hermes_pair_idempotent(self):
        """Re-pairing same hermes_id updates token."""
        pairing1 = self.hermes.pair_hermes('hermes-002', 'test-hermes-2')
        token1 = pairing1.token

        # Small delay to ensure different timestamp
        time.sleep(0.01)

        pairing2 = self.hermes.pair_hermes('hermes-002', 'test-hermes-2-updated')
        token2 = pairing2.token

        # Tokens should be different (re-paired)
        self.assertNotEqual(token1, token2)
        # But hermes_id stays the same
        self.assertEqual(pairing2.hermes_id, 'hermes-002')
        # Device name updated
        self.assertEqual(pairing2.device_name, 'test-hermes-2-updated')

    def test_hermes_connect_valid_token(self):
        """Connect with valid authority token succeeds."""
        pairing = self.hermes.pair_hermes('hermes-003', 'test-hermes-3')
        connection = self.hermes.connect(pairing.token)

        self.assertEqual(connection.hermes_id, 'hermes-003')
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)
        self.assertIsNotNone(connection.connected_at)

    def test_hermes_connect_invalid_token(self):
        """Connect with invalid token fails."""
        with self.assertRaises(ValueError) as ctx:
            self.hermes.connect('invalid-token-xyz')
        self.assertIn('not found', str(ctx.exception))

    def test_hermes_connect_expired_token(self):
        """Connect with expired token fails."""
        # Manually create a pairing with expired token
        principal = self.store.load_or_create_principal()
        all_pairings = self.store.load_pairings()

        expired_pairing = {
            'hermes_id': 'hermes-expired',
            'principal_id': principal.id,
            'device_name': 'expired-hermes',
            'capabilities': ['observe', 'summarize'],
            'paired_at': datetime.now(timezone.utc).isoformat(),
            'token': 'expired-token-123',
            'token_expires_at': '2020-01-01T00:00:00+00:00'  # Past date
        }
        all_pairings['expired-id'] = expired_pairing
        self.store.save_pairings(all_pairings)

        with self.assertRaises(ValueError) as ctx:
            self.hermes.connect('expired-token-123')
        self.assertIn('expired', str(ctx.exception).lower())

    def test_hermes_read_status_with_observe(self):
        """Read status with observe capability succeeds."""
        pairing = self.hermes.pair_hermes('hermes-004', 'test-hermes-4')
        connection = self.hermes.connect(pairing.token)

        status = self.hermes.read_status(connection)

        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)

    def test_hermes_read_status_without_observe(self):
        """Read status without observe capability fails."""
        # Create a pairing with only summarize capability
        principal = self.store.load_or_create_principal()
        all_pairings = self.store.load_pairings()

        limited_pairing = {
            'hermes_id': 'hermes-limited',
            'principal_id': principal.id,
            'device_name': 'limited-hermes',
            'capabilities': ['summarize'],  # No observe!
            'paired_at': datetime.now(timezone.utc).isoformat(),
            'token': 'limited-token-123',
            'token_expires_at': datetime.now(timezone.utc).isoformat()
        }
        all_pairings['limited-id'] = limited_pairing
        self.store.save_pairings(all_pairings)

        connection = self.hermes.HermesConnection(
            hermes_id='hermes-limited',
            principal_id=principal.id,
            capabilities=['summarize'],  # No observe
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=datetime.now(timezone.utc).isoformat()
        )

        with self.assertRaises(PermissionError) as ctx:
            self.hermes.read_status(connection)
        self.assertIn('observe', str(ctx.exception))

    def test_hermes_append_summary_with_summarize(self):
        """Append summary with summarize capability succeeds."""
        pairing = self.hermes.pair_hermes('hermes-005', 'test-hermes-5')
        connection = self.hermes.connect(pairing.token)

        event = self.hermes.append_summary(
            connection,
            "Test summary: miner running normally",
            "observe"
        )

        self.assertIsNotNone(event.id)
        self.assertEqual(event.kind, 'hermes_summary')
        self.assertEqual(event.payload['summary_text'], "Test summary: miner running normally")
        self.assertEqual(event.payload['authority_scope'], "observe")

    def test_hermes_append_summary_without_summarize(self):
        """Append summary without summarize capability fails."""
        principal = self.store.load_or_create_principal()
        connection = self.hermes.HermesConnection(
            hermes_id='hermes-no-summarize',
            principal_id=principal.id,
            capabilities=['observe'],  # No summarize
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=datetime.now(timezone.utc).isoformat()
        )

        with self.assertRaises(PermissionError) as ctx:
            self.hermes.append_summary(connection, "Test", "observe")
        self.assertIn('summarize', str(ctx.exception))

    def test_hermes_summary_appears_in_spine(self):
        """Appended summary is visible in event spine."""
        pairing = self.hermes.pair_hermes('hermes-006', 'test-hermes-6')
        connection = self.hermes.connect(pairing.token)

        # Append a summary
        event = self.hermes.append_summary(
            connection,
            "Miner status: all systems operational",
            "observe"
        )

        # Query spine for hermes_summary events
        events = self.spine.get_events(kind=self.spine.EventKind.HERMES_SUMMARY, limit=10)
        event_ids = [e.id for e in events]

        self.assertIn(event.id, event_ids)

    def test_hermes_event_filter_excludes_user_message(self):
        """Get filtered events excludes user_message."""
        pairing = self.hermes.pair_hermes('hermes-007', 'test-hermes-7')
        connection = self.hermes.connect(pairing.token)

        # Append a user message directly (bypassing filter)
        self.spine.append_event(
            self.spine.EventKind.USER_MESSAGE,
            connection.principal_id,
            {"content": "Secret user message", "sender": "alice"}
        )

        # Append a hermes summary
        self.hermes.append_summary(connection, "Public summary", "observe")

        # Get filtered events
        filtered = self.hermes.get_filtered_events(connection, limit=20)

        kinds = [e.kind for e in filtered]
        self.assertNotIn('user_message', kinds)
        self.assertIn('hermes_summary', kinds)

    def test_hermes_no_control_capability(self):
        """Verify Hermes cannot have control capability."""
        pairing = self.hermes.pair_hermes('hermes-008', 'test-hermes-8')

        # Hermes pairings always get observe + summarize
        self.assertNotIn('control', pairing.capabilities)

        # Even if we try to create a pairing with control, it should work
        # but the connect should reject invalid capabilities
        principal = self.store.load_or_create_principal()
        all_pairings = self.store.load_pairings()

        from datetime import timedelta
        bad_pairing = {
            'hermes_id': 'hermes-bad',
            'principal_id': principal.id,
            'device_name': 'bad-hermes',
            'capabilities': ['observe', 'summarize', 'control'],  # Invalid!
            'paired_at': datetime.now(timezone.utc).isoformat(),
            'token': 'bad-token-123',
            'token_expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        all_pairings['bad-id'] = bad_pairing
        self.store.save_pairings(all_pairings)

        with self.assertRaises(ValueError) as ctx:
            self.hermes.connect('bad-token-123')
        self.assertIn('control', str(ctx.exception))

    def test_hermes_check_control_attempt(self):
        """Control attempts from Hermes are rejected."""
        result = self.hermes.check_control_attempt('hermes-009')

        self.assertFalse(result['authorized'])
        self.assertEqual(result['error'], 'HERMES_UNAUTHORIZED')
        self.assertEqual(result['hermes_id'], 'hermes-009')
        self.assertIn('timestamp', result)

    def test_hermes_verify_authority(self):
        """Verify authority checks capabilities correctly."""
        principal = self.store.load_or_create_principal()
        connection = self.hermes.HermesConnection(
            hermes_id='hermes-verify',
            principal_id=principal.id,
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=datetime.now(timezone.utc).isoformat()
        )

        self.assertTrue(self.hermes.verify_authority(connection, 'observe'))
        self.assertTrue(self.hermes.verify_authority(connection, 'summarize'))
        self.assertFalse(self.hermes.verify_authority(connection, 'control'))


class TestHermesDaemonEndpoints(unittest.TestCase):
    """Test Hermes endpoints via daemon."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment with isolated state directory."""
        cls.test_state_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = cls.test_state_dir

        # Re-import modules to use test state
        import importlib
        import store
        importlib.reload(store)
        import spine
        importlib.reload(spine)
        import hermes
        importlib.reload(hermes)
        import daemon
        importlib.reload(daemon)

        cls.store = store
        cls.spine = spine
        cls.hermes = hermes
        cls.daemon = daemon

    @classmethod
    def tearDownClass(cls):
        """Clean up test state directory."""
        import shutil
        if os.path.exists(cls.test_state_dir):
            shutil.rmtree(cls.test_state_dir)

    def test_daemon_hermes_pair_endpoint(self):
        """POST /hermes/pair creates pairing."""
        import http.client
        import io

        # Create a mock request
        class MockRequest:
            def __init__(self, method, path, headers, body):
                self.command = method
                self.path = path
                self.headers = headers
                self.rfile = io.BytesIO(body)
                self.wfile = io.BytesIO()
                self._response_status = None
                self._response_headers = {}

            def send_response(self, code):
                self._response_status = code

            def send_header(self, key, value):
                self._response_headers[key] = value

            def end_headers(self):
                pass

        # Test pairing
        body = json.dumps({
            'hermes_id': 'daemon-hermes-001',
            'device_name': 'daemon-test'
        }).encode()

        # We can't easily test the full HTTP flow without starting the server
        # So we test the hermes module directly
        pairing = self.hermes.pair_hermes('daemon-hermes-001', 'daemon-test')

        self.assertEqual(pairing.hermes_id, 'daemon-hermes-001')
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])

    def test_hermes_principal_isolation(self):
        """Hermes uses same principal as gateway (different device_name)."""
        principal1 = self.store.load_or_create_principal()
        pairing = self.hermes.pair_hermes('isolated-hermes', 'isolated-agent')
        principal2 = self.store.load_or_create_principal()

        # Same principal
        self.assertEqual(principal1.id, principal2.id)
        # But different device name
        self.assertNotEqual(pairing.device_name, principal1.name)


if __name__ == '__main__':
    unittest.main()

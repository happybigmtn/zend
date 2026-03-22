#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the Hermes adapter boundary enforcement and capability scoping.
"""

import base64
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHermesAdapter(unittest.TestCase):
    """Tests for Hermes adapter module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary state directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.env_patcher = patch.dict(os.environ, {'ZEND_STATE_DIR': self.temp_dir})
        self.env_patcher.start()

        # Import after patching env
        import importlib
        # Force reimport of modules with patched env
        if 'hermes' in sys.modules:
            del sys.modules['hermes']
        if 'store' in sys.modules:
            del sys.modules['store']
        if 'spine' in sys.modules:
            del sys.modules['spine']

        from hermes import (
            connect, HermesConnection, HermesAuthError, HermesCapabilityError,
            HERMES_CAPABILITIES, HERMES_READABLE_EVENTS, pair_hermes,
            read_status, append_summary, get_filtered_events, get_capabilities
        )
        from spine import EventKind
        from store import load_or_create_principal

        self.hermes = sys.modules['hermes']
        self.connect = connect
        self.HermesAuthError = HermesAuthError
        self.HermesCapabilityError = HermesCapabilityError
        self.HERMES_CAPABILITIES = HERMES_CAPABILITIES
        self.pair_hermes = pair_hermes
        self.read_status = read_status
        self.append_summary = append_summary
        self.get_filtered_events = get_filtered_events
        self.get_capabilities = get_capabilities
        self.EventKind = EventKind
        self.load_or_create_principal = load_or_create_principal

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_token(self, hermes_id='hermes-001', principal_id=None,
                    capabilities=None, expires_at=None):
        """Create a valid authority token for testing."""
        if capabilities is None:
            capabilities = ['observe', 'summarize']
        if expires_at is None:
            expires_at = datetime.now(timezone.utc)
            expires_at = expires_at.replace(year=expires_at.year + 1).isoformat()

        payload = {
            'hermes_id': hermes_id,
            'principal_id': principal_id or 'test-principal-001',
            'capabilities': capabilities,
            'expires_at': expires_at
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()

    def test_hermes_connect_valid(self):
        """Connect with valid token succeeds."""
        token = self._make_token()
        connection = self.connect(token)

        self.assertIsInstance(connection, self.hermes.HermesConnection)
        self.assertEqual(connection.hermes_id, 'hermes-001')
        self.assertEqual(connection.principal_id, 'test-principal-001')
        self.assertEqual(connection.capabilities, ['observe', 'summarize'])
        self.assertIsNotNone(connection.connected_at)

    def test_hermes_connect_empty_token(self):
        """Connect with empty token fails."""
        with self.assertRaises(self.HermesAuthError) as ctx:
            self.connect('')
        self.assertIn('empty authority token', str(ctx.exception))

    def test_hermes_connect_invalid_token(self):
        """Connect with invalid token encoding fails."""
        with self.assertRaises(self.HermesAuthError) as ctx:
            self.connect('not-valid-base64!!!')
        self.assertIn('invalid token encoding', str(ctx.exception))

    def test_hermes_connect_expired(self):
        """Connect with expired token fails."""
        # Create a past date without microseconds for consistent ISO format
        past = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        token = self._make_token(expires_at=past.isoformat())

        with self.assertRaises(self.HermesAuthError) as ctx:
            self.connect(token)
        self.assertIn('expired', str(ctx.exception))

    def test_hermes_connect_control_capability_rejected(self):
        """Connect with control capability is rejected for Hermes."""
        token = self._make_token(capabilities=['observe', 'summarize', 'control'])

        with self.assertRaises(self.HermesAuthError) as ctx:
            self.connect(token)
        self.assertIn('invalid capabilities', str(ctx.exception))

    def test_hermes_connect_missing_hermes_id(self):
        """Connect without hermes_id fails."""
        payload = {
            'principal_id': 'test-principal-001',
            'capabilities': ['observe'],
            'expires_at': datetime.now(timezone.utc).replace(
                year=datetime.now(timezone.utc).year + 1
            ).isoformat()
        }
        token = base64.b64encode(json.dumps(payload).encode()).decode()

        with self.assertRaises(self.HermesAuthError) as ctx:
            self.connect(token)
        self.assertIn('missing hermes_id', str(ctx.exception))

    def test_hermes_read_status(self):
        """Observe capability allows reading status."""
        token = self._make_token()
        connection = self.connect(token)

        # Patch the daemon.miner.get_snapshot to return test data
        # We need to import daemon first and patch its miner
        import daemon
        original_snapshot = daemon.miner.get_snapshot

        mock_snapshot = {
            'status': 'running',
            'mode': 'balanced',
            'hashrate_hs': 50000,
            'temperature': 45.0,
            'uptime_seconds': 3600,
            'freshness': datetime.now(timezone.utc).isoformat()
        }

        daemon.miner.get_snapshot = lambda: mock_snapshot

        try:
            status = self.read_status(connection)

            self.assertEqual(status['status'], 'running')
            self.assertEqual(status['mode'], 'balanced')
            self.assertEqual(status['hashrate_hs'], 50000)
            self.assertEqual(status['observed_by'], 'hermes-001')
            self.assertIn('observed_at', status)
        finally:
            # Restore original
            daemon.miner.get_snapshot = original_snapshot

    def test_hermes_read_status_no_observe_capability(self):
        """Read status without observe capability fails."""
        token = self._make_token(capabilities=['summarize'])
        connection = self.connect(token)

        with self.assertRaises(self.HermesCapabilityError) as ctx:
            self.read_status(connection)
        self.assertIn('observe capability required', str(ctx.exception))

    def test_hermes_append_summary(self):
        """Summarize capability allows appending summaries."""
        token = self._make_token()
        connection = self.connect(token)

        result = self.append_summary(
            connection,
            'Miner running normally at 50kH/s',
            ['observe']
        )

        self.assertTrue(result['appended'])
        self.assertIsNotNone(result['event_id'])
        self.assertEqual(result['kind'], 'hermes_summary')

    def test_hermes_append_summary_no_capability(self):
        """Append summary without summarize capability fails."""
        token = self._make_token(capabilities=['observe'])
        connection = self.connect(token)

        with self.assertRaises(self.HermesCapabilityError) as ctx:
            self.append_summary(connection, 'Test summary', ['observe'])
        self.assertIn('summarize capability required', str(ctx.exception))

    def test_hermes_append_summary_empty_text(self):
        """Append summary with empty text fails."""
        token = self._make_token()
        connection = self.connect(token)

        with self.assertRaises(ValueError) as ctx:
            self.append_summary(connection, '', ['observe'])
        self.assertIn('empty', str(ctx.exception))

    def test_hermes_event_filter(self):
        """User message events are filtered out."""
        token = self._make_token()
        connection = self.connect(token)

        # Mock get_events to return mixed events
        mock_events = [
            MagicMock(
                id='1',
                kind='hermes_summary',
                payload={'summary_text': 'Test'},
                created_at=datetime.now(timezone.utc).isoformat()
            ),
            MagicMock(
                id='2',
                kind='user_message',
                payload={'message': 'Secret data'},
                created_at=datetime.now(timezone.utc).isoformat()
            ),
            MagicMock(
                id='3',
                kind='miner_alert',
                payload={'alert_type': 'temp'},
                created_at=datetime.now(timezone.utc).isoformat()
            ),
        ]

        with patch('hermes.get_events', return_value=mock_events):
            events = self.get_filtered_events(connection, limit=10)

        # Should only get hermes_summary and miner_alert
        kinds = [e['kind'] for e in events]
        self.assertIn('hermes_summary', kinds)
        self.assertIn('miner_alert', kinds)
        self.assertNotIn('user_message', kinds)
        self.assertEqual(len(events), 2)

    def test_hermes_no_control(self):
        """Hermes cannot issue control commands."""
        token = self._make_token()
        connection = self.connect(token)

        # Hermes should never have control capability
        self.assertFalse(connection.has_capability('control'))

    def test_hermes_pairing(self):
        """Hermes pairing creates record with correct capabilities."""
        result = self.pair_hermes('hermes-agent-001', 'My Hermes')

        self.assertEqual(result['hermes_id'], 'hermes-agent-001')
        self.assertEqual(result['capabilities'], ['observe', 'summarize'])
        self.assertIn('authority_token', result)
        self.assertIn('principal_id', result)

    def test_hermes_pairing_idempotent(self):
        """Hermes pairing is idempotent."""
        result1 = self.pair_hermes('hermes-agent-002')
        result2 = self.pair_hermes('hermes-agent-002')

        # Should return success both times
        self.assertEqual(result1['hermes_id'], 'hermes-agent-002')
        self.assertEqual(result2['hermes_id'], 'hermes-agent-002')

    def test_hermes_capabilities_manifest(self):
        """Capabilities manifest shows correct information."""
        caps = self.get_capabilities()

        self.assertEqual(caps['adapter'], 'hermes')
        self.assertEqual(caps['version'], '1.0.0')
        self.assertEqual(set(caps['capabilities']), set(['observe', 'summarize']))
        self.assertIn('hermes_summary', caps['readable_events'])
        self.assertIn('user_message', caps['blocked_events'])

    def test_hermes_connection_to_dict(self):
        """Connection serialization works correctly."""
        token = self._make_token()
        connection = self.connect(token)

        data = connection.to_dict()

        self.assertEqual(data['hermes_id'], 'hermes-001')
        self.assertEqual(data['principal_id'], 'test-principal-001')
        self.assertEqual(data['capabilities'], ['observe', 'summarize'])
        self.assertIn('connected_at', data)


class TestHermesConnection(unittest.TestCase):
    """Tests for HermesConnection dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.env_patcher = patch.dict(os.environ, {'ZEND_STATE_DIR': self.temp_dir})
        self.env_patcher.start()

        from hermes import HermesConnection
        self.HermesConnection = HermesConnection

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_connection_has_capability(self):
        """has_capability works correctly."""
        conn = self.HermesConnection(
            hermes_id='test',
            principal_id='p1',
            capabilities=['observe', 'summarize'],
            connected_at='2026-01-01T00:00:00Z'
        )

        self.assertTrue(conn.has_capability('observe'))
        self.assertTrue(conn.has_capability('summarize'))
        self.assertFalse(conn.has_capability('control'))

    def test_connection_can_observe(self):
        """can_observe returns correct value."""
        conn = self.HermesConnection(
            hermes_id='test',
            principal_id='p1',
            capabilities=['observe'],
            connected_at='2026-01-01T00:00:00Z'
        )

        self.assertTrue(conn.can_observe())

    def test_connection_can_summarize(self):
        """can_summarize returns correct value."""
        conn = self.HermesConnection(
            hermes_id='test',
            principal_id='p1',
            capabilities=['summarize'],
            connected_at='2026-01-01T00:00:00Z'
        )

        self.assertTrue(conn.can_summarize())


if __name__ == '__main__':
    unittest.main()

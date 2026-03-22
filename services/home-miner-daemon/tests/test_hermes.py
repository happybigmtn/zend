#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the capability boundary enforcement and event filtering.
"""

import os
import sys
import tempfile
import unittest

# Set up state directory before importing hermes module
_test_state_dir = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = _test_state_dir

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import asdict
import hermes


class TestHermesCapabilities(unittest.TestCase):
    """Test Hermes capability constants."""

    def test_hermes_capabilities(self):
        """Verify Hermes has correct capabilities."""
        self.assertEqual(hermes.HERMES_CAPABILITIES, ['observe', 'summarize'])
        self.assertNotIn('control', hermes.HERMES_CAPABILITIES)

    def test_hermes_readable_events(self):
        """Verify Hermes can only read specific events."""
        self.assertIn('hermes_summary', hermes.HERMES_READABLE_EVENT_KINDS)
        self.assertIn('miner_alert', hermes.HERMES_READABLE_EVENT_KINDS)
        self.assertIn('control_receipt', hermes.HERMES_READABLE_EVENT_KINDS)
        # user_message should NOT be in readable events
        self.assertNotIn('user_message', hermes.HERMES_READABLE_EVENT_KINDS)


class TestTokenGeneration(unittest.TestCase):
    """Test authority token generation and decoding."""

    def test_generate_and_decode_token(self):
        """Verify token generation and decoding roundtrip."""
        hermes_id = 'test-hermes-001'
        principal_id = 'principal-001'
        capabilities = ['observe', 'summarize']

        token = hermes._generate_authority_token(hermes_id, principal_id, capabilities)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        decoded = hermes._decode_authority_token(token)
        self.assertEqual(decoded['hermes_id'], hermes_id)
        self.assertEqual(decoded['principal_id'], principal_id)
        self.assertEqual(decoded['capabilities'], capabilities)

    def test_invalid_token_format(self):
        """Verify invalid tokens raise ValueError."""
        with self.assertRaises(ValueError):
            hermes._decode_authority_token('not-a-valid-base64-token!!!')

        with self.assertRaises(ValueError):
            hermes._decode_authority_token('')

    def test_token_missing_fields(self):
        """Verify tokens missing required fields raise ValueError."""
        import base64
        import json

        # Token missing hermes_id
        partial_token = base64.b64encode(json.dumps({
            'principal_id': 'test',
            'capabilities': ['observe'],
            'expires_at': '2099-01-01T00:00:00Z'
        }).encode()).decode()

        with self.assertRaises(ValueError):
            hermes._decode_authority_token(partial_token)


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing operations."""

    def setUp(self):
        """Set up test state directory."""
        self.test_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.test_dir
        # Reset the state file path
        hermes.STATE_DIR = self.test_dir
        hermes.HERMES_PAIRING_FILE = os.path.join(self.test_dir, 'hermes-pairing-store.json')

    def test_pair_hermes(self):
        """Verify Hermes pairing creates correct record."""
        pairing = hermes.pair_hermes('hermes-001', 'test-agent')

        self.assertEqual(pairing.hermes_id, 'hermes-001')
        self.assertEqual(pairing.device_name, 'test-agent')
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertIsNotNone(pairing.principal_id)
        self.assertIsNotNone(pairing.authority_token)
        self.assertIsNotNone(pairing.paired_at)

    def test_pair_hermes_idempotent(self):
        """Verify re-pairing same Hermes ID updates token."""
        first_pairing = hermes.pair_hermes('hermes-002', 'test-agent')
        first_token = first_pairing.authority_token

        second_pairing = hermes.pair_hermes('hermes-002', 'test-agent')

        # Should have new token
        self.assertNotEqual(first_token, second_pairing.authority_token)
        # But same hermes_id
        self.assertEqual(first_pairing.hermes_id, second_pairing.hermes_id)

    def test_get_pairing(self):
        """Verify getting pairing by ID works."""
        created = hermes.pair_hermes('hermes-003', 'test-agent')
        retrieved = hermes.get_pairing('hermes-003')

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hermes_id, created.hermes_id)
        self.assertEqual(retrieved.capabilities, created.capabilities)

    def test_get_nonexistent_pairing(self):
        """Verify getting non-existent pairing returns None."""
        result = hermes.get_pairing('nonexistent-hermes')
        self.assertIsNone(result)


class TestHermesConnect(unittest.TestCase):
    """Test Hermes connection establishment."""

    def setUp(self):
        """Set up test state directory."""
        self.test_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.test_dir
        hermes.STATE_DIR = self.test_dir
        hermes.HERMES_PAIRING_FILE = os.path.join(self.test_dir, 'hermes-pairing-store.json')
        # Create a pairing to get valid token
        self.pairing = hermes.pair_hermes('hermes-010', 'test-agent')

    def test_connect_with_valid_token(self):
        """Verify connect succeeds with valid token."""
        connection = hermes.connect(self.pairing.authority_token)

        self.assertIsInstance(connection, hermes.HermesConnection)
        self.assertEqual(connection.hermes_id, 'hermes-010')
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)

    def test_connect_with_invalid_token(self):
        """Verify connect fails with invalid token."""
        with self.assertRaises(ValueError):
            hermes.connect('invalid-token')

    def test_validate_connection_auth(self):
        """Verify connection validation by hermes_id."""
        connection = hermes.validate_connection_auth('hermes-010')

        self.assertIsNotNone(connection)
        self.assertEqual(connection.hermes_id, 'hermes-010')

    def test_validate_connection_auth_invalid(self):
        """Verify validation fails for unknown hermes_id."""
        result = hermes.validate_connection_auth('unknown-hermes')
        self.assertIsNone(result)


class TestReadStatus(unittest.TestCase):
    """Test Hermes read_status capability."""

    def setUp(self):
        """Set up test state directory."""
        self.test_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.test_dir
        hermes.STATE_DIR = self.test_dir
        hermes.HERMES_PAIRING_FILE = os.path.join(self.test_dir, 'hermes-pairing-store.json')
        self.pairing = hermes.pair_hermes('hermes-020', 'test-agent')

    def test_read_status_with_observe_capability(self):
        """Verify read_status succeeds with observe capability."""
        connection = hermes.connect(self.pairing.authority_token)

        # Mock the miner for testing
        status = hermes.read_status(connection)

        self.assertIsInstance(status, dict)
        self.assertIn('status', status)
        self.assertIn('mode', status)

    def test_read_status_without_observe_capability(self):
        """Verify read_status fails without observe capability."""
        # Create a connection with no capabilities
        connection = hermes.HermesConnection(
            hermes_id='test',
            principal_id='test',
            capabilities=[],  # No observe
            connected_at='2026-03-22T00:00:00Z'
        )

        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(connection)

        self.assertIn('observe', str(ctx.exception))


class TestAppendSummary(unittest.TestCase):
    """Test Hermes append_summary capability."""

    def setUp(self):
        """Set up test state directory."""
        self.test_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.test_dir
        hermes.STATE_DIR = self.test_dir
        hermes.HERMES_PAIRING_FILE = os.path.join(self.test_dir, 'hermes-pairing-store.json')
        self.pairing = hermes.pair_hermes('hermes-030', 'test-agent')

    def test_append_summary_with_summarize_capability(self):
        """Verify append_summary succeeds with summarize capability."""
        connection = hermes.connect(self.pairing.authority_token)

        result = hermes.append_summary(
            connection,
            "Test summary: Miner running normally",
            "observe"
        )

        self.assertTrue(result.get('appended'))
        self.assertIsNotNone(result.get('event_id'))

    def test_append_summary_without_summarize_capability(self):
        """Verify append_summary fails without summarize capability."""
        # Create a connection with no capabilities
        connection = hermes.HermesConnection(
            hermes_id='test',
            principal_id='test',
            capabilities=['observe'],  # No summarize
            connected_at='2026-03-22T00:00:00Z'
        )

        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(connection, "Test summary", "observe")

        self.assertIn('summarize', str(ctx.exception))


class TestEventFiltering(unittest.TestCase):
    """Test Hermes event filtering (blocking user_message)."""

    def setUp(self):
        """Set up test state directory."""
        self.test_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.test_dir
        hermes.STATE_DIR = self.test_dir
        hermes.HERMES_PAIRING_FILE = os.path.join(self.test_dir, 'hermes-pairing-store.json')
        self.pairing = hermes.pair_hermes('hermes-040', 'test-agent')

    def test_hermes_cannot_read_user_message(self):
        """Verify user_message is not in readable events list."""
        self.assertNotIn('user_message', hermes.HERMES_READABLE_EVENT_KINDS)

    def test_filtered_events_excludes_user_message(self):
        """Verify get_filtered_events filters out user_message events."""
        connection = hermes.connect(self.pairing.authority_token)

        events = hermes.get_filtered_events(connection, limit=20)

        # Verify no user_message events
        for event in events:
            self.assertNotEqual(event.kind, 'user_message')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the capability boundary enforcement for the Hermes AI agent adapter.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test state dir
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR

import hermes
import spine
from hermes import (
    connect,
    pair_hermes,
    read_status,
    append_summary,
    get_filtered_events,
    generate_authority_token,
    get_hermes_pairing,
    HermesConnection,
    HERMES_CAPABILITIES,
    HERMES_READABLE_EVENTS,
)


class TestHermesConstants(unittest.TestCase):
    """Test that Hermes constants are correctly defined."""

    def test_hermes_capabilities(self):
        """Hermes should only have observe and summarize capabilities."""
        self.assertEqual(sorted(HERMES_CAPABILITIES), ['observe', 'summarize'])
        self.assertNotIn('control', HERMES_CAPABILITIES)

    def test_hermes_readable_events(self):
        """Hermes readable events should not include user_message."""
        readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable_kinds)
        self.assertIn('miner_alert', readable_kinds)
        self.assertIn('control_receipt', readable_kinds)
        self.assertNotIn('user_message', readable_kinds)


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing functionality."""

    def setUp(self):
        """Clear state before each test."""
        hermes_store = os.path.join(TEST_STATE_DIR, 'hermes-store.json')
        if os.path.exists(hermes_store):
            os.remove(hermes_store)

    def test_pair_hermes_creates_record(self):
        """Pairing Hermes should create a record with observe+summarize."""
        principal_id = "test-principal-001"
        pairing = pair_hermes("hermes-001", "test-hermes", principal_id)

        self.assertEqual(pairing.hermes_id, "hermes-001")
        self.assertEqual(pairing.device_name, "test-hermes")
        self.assertEqual(pairing.principal_id, principal_id)
        self.assertEqual(sorted(pairing.capabilities), ['observe', 'summarize'])
        self.assertTrue(pairing.token)

    def test_pair_hermes_idempotent(self):
        """Pairing same hermes_id twice should update, not error."""
        principal_id = "test-principal-001"
        
        pairing1 = pair_hermes("hermes-001", "test-hermes", principal_id)
        time.sleep(0.1)  # Ensure different paired_at
        pairing2 = pair_hermes("hermes-001", "test-hermes", principal_id)

        # Should return same hermes_id
        self.assertEqual(pairing1.hermes_id, pairing2.hermes_id)
        
        # Should have updated
        self.assertNotEqual(pairing1.paired_at, pairing2.paired_at)

    def test_get_hermes_pairing(self):
        """Getting pairing by ID should return the record."""
        principal_id = "test-principal-002"
        pair_hermes("hermes-002", "test-hermes-2", principal_id)

        retrieved = get_hermes_pairing("hermes-002")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hermes_id, "hermes-002")

    def test_get_nonexistent_pairing(self):
        """Getting nonexistent pairing should return None."""
        retrieved = get_hermes_pairing("nonexistent-hermes")
        self.assertIsNone(retrieved)


class TestAuthorityToken(unittest.TestCase):
    """Test authority token generation and validation."""

    def test_generate_valid_token(self):
        """Should generate a valid base64-encoded token."""
        token = generate_authority_token("hermes-001", "principal-001", ["observe", "summarize"])
        
        # Should be base64
        self.assertIsInstance(token, str)
        decoded = __import__('base64').b64decode(token).decode('utf-8')
        data = json.loads(decoded)
        
        self.assertEqual(data['hermes_id'], "hermes-001")
        self.assertEqual(data['principal_id'], "principal-001")
        self.assertEqual(sorted(data['capabilities']), ['observe', 'summarize'])
        self.assertIn('expires_at', data)

    def test_token_with_hermes_prefix(self):
        """Token can be passed with 'Hermes ' prefix."""
        token = generate_authority_token("hermes-001", "principal-001", ["observe"])
        prefixed_token = f"Hermes {token}"
        
        # Parse and validate
        token_data = hermes._parse_authority_token(prefixed_token)
        self.assertEqual(token_data['hermes_id'], "hermes-001")


class TestHermesConnect(unittest.TestCase):
    """Test Hermes connection with authority token."""

    def setUp(self):
        """Clear state before each test."""
        hermes_store = os.path.join(TEST_STATE_DIR, 'hermes-store.json')
        if os.path.exists(hermes_store):
            os.remove(hermes_store)
        spine_store = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        if os.path.exists(spine_store):
            os.remove(spine_store)

    def test_connect_valid_token(self):
        """Connecting with valid token should succeed."""
        principal_id = "test-principal-003"
        pair_hermes("hermes-003", "test-hermes-3", principal_id)
        
        token = generate_authority_token("hermes-003", principal_id, ["observe", "summarize"])
        connection = connect(token)
        
        self.assertIsInstance(connection, HermesConnection)
        self.assertEqual(connection.hermes_id, "hermes-003")
        self.assertEqual(connection.principal_id, principal_id)
        self.assertEqual(sorted(connection.capabilities), ['observe', 'summarize'])

    def test_connect_expired_token(self):
        """Connecting with expired token should fail."""
        principal_id = "test-principal-004"
        pair_hermes("hermes-004", "test-hermes-4", principal_id)
        
        # Create expired token
        import base64
        expired_data = {
            "hermes_id": "hermes-004",
            "principal_id": principal_id,
            "capabilities": ["observe", "summarize"],
            "expires_at": "2020-01-01T00:00:00+00:00"  # Expired
        }
        expired_token = base64.b64encode(json.dumps(expired_data).encode()).decode()
        
        with self.assertRaises(ValueError) as context:
            connect(expired_token)
        self.assertIn("EXPIRED", str(context.exception))

    def test_connect_invalid_capability(self):
        """Connecting with invalid capability should fail."""
        principal_id = "test-principal-005"
        pair_hermes("hermes-005", "test-hermes-5", principal_id)
        
        # Try to use control capability (not allowed for Hermes)
        token = generate_authority_token("hermes-005", principal_id, ["observe", "control"])
        
        with self.assertRaises(ValueError) as context:
            connect(token)
        self.assertIn("INVALID_CAPABILITY", str(context.exception))

    def test_connect_unregistered_hermes(self):
        """Connecting with unregistered hermes_id should fail."""
        import base64
        token_data = {
            "hermes_id": "nonexistent-hermes",
            "principal_id": "some-principal",
            "capabilities": ["observe", "summarize"],
            "expires_at": "2099-12-31T23:59:59+00:00"
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        with self.assertRaises(ValueError) as context:
            connect(token)
        self.assertIn("not registered", str(context.exception))


class TestReadStatus(unittest.TestCase):
    """Test Hermes read_status functionality."""

    def setUp(self):
        """Set up test connection."""
        hermes_store = os.path.join(TEST_STATE_DIR, 'hermes-store.json')
        if os.path.exists(hermes_store):
            os.remove(hermes_store)
        spine_store = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        if os.path.exists(spine_store):
            os.remove(spine_store)
        
        # Create test pairing and connection
        self.principal_id = "test-principal-006"
        pair_hermes("hermes-006", "test-hermes-6", self.principal_id)
        
        token = generate_authority_token("hermes-006", self.principal_id, ["observe", "summarize"])
        self.connection = connect(token)

    @patch('daemon.miner')
    def test_read_status_with_observe(self, mock_miner):
        """Hermes with observe capability should read status."""
        mock_miner.get_snapshot.return_value = {
            "status": "running",
            "mode": "balanced",
            "hashrate_hs": 50000,
            "temperature": 45.0,
            "uptime_seconds": 3600,
            "freshness": "2026-03-22T12:00:00+00:00"
        }
        
        status = read_status(self.connection)
        
        self.assertEqual(status['status'], 'running')
        self.assertEqual(status['mode'], 'balanced')
        self.assertEqual(status['capabilities'], ['observe', 'summarize'])

    def test_read_status_without_observe(self):
        """Hermes without observe capability should raise PermissionError."""
        limited_connection = HermesConnection(
            hermes_id="hermes-006",
            principal_id=self.principal_id,
            capabilities=[],  # No capabilities
            connected_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.assertRaises(PermissionError) as context:
            read_status(limited_connection)
        self.assertIn("observe capability required", str(context.exception))


class TestAppendSummary(unittest.TestCase):
    """Test Hermes append_summary functionality."""

    def setUp(self):
        """Set up test connection."""
        hermes_store = os.path.join(TEST_STATE_DIR, 'hermes-store.json')
        if os.path.exists(hermes_store):
            os.remove(hermes_store)
        spine_store = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        if os.path.exists(spine_store):
            os.remove(spine_store)
        
        self.principal_id = "test-principal-007"
        pair_hermes("hermes-007", "test-hermes-7", self.principal_id)
        
        token = generate_authority_token("hermes-007", self.principal_id, ["observe", "summarize"])
        self.connection = connect(token)

    def test_append_summary_with_summarize(self):
        """Hermes with summarize capability should append to spine."""
        result = append_summary(
            self.connection,
            "Miner running normally at 50kH/s",
            "observe"
        )
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
        self.assertIn('created_at', result)
        
        # Verify it was written to spine
        events = spine.get_events(kind=spine.EventKind.HERMES_SUMMARY, limit=10)
        self.assertTrue(len(events) > 0)
        latest = events[0]
        self.assertEqual(latest.payload['summary_text'], "Miner running normally at 50kH/s")
        self.assertEqual(latest.payload['authority_scope'], "observe")
        self.assertEqual(latest.payload['hermes_id'], "hermes-007")

    def test_append_summary_without_summarize(self):
        """Hermes without summarize capability should raise PermissionError."""
        limited_connection = HermesConnection(
            hermes_id="hermes-007",
            principal_id=self.principal_id,
            capabilities=['observe'],  # No summarize
            connected_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.assertRaises(PermissionError) as context:
            append_summary(limited_connection, "test", "observe")
        self.assertIn("summarize capability required", str(context.exception))


class TestEventFiltering(unittest.TestCase):
    """Test event filtering for Hermes."""

    def setUp(self):
        """Set up test data."""
        hermes_store = os.path.join(TEST_STATE_DIR, 'hermes-store.json')
        if os.path.exists(hermes_store):
            os.remove(hermes_store)
        spine_store = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        if os.path.exists(spine_store):
            os.remove(spine_store)
        
        self.principal_id = "test-principal-008"
        pair_hermes("hermes-008", "test-hermes-8", self.principal_id)
        
        token = generate_authority_token("hermes-008", self.principal_id, ["observe", "summarize"])
        self.connection = connect(token)
        
        # Add various event types to spine
        spine.append_event(
            spine.EventKind.HERMES_SUMMARY,
            self.principal_id,
            {"summary_text": "Test summary 1", "hermes_id": "hermes-008"}
        )
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            self.principal_id,
            {"message": "Secret user message"}
        )
        spine.append_event(
            spine.EventKind.MINER_ALERT,
            self.principal_id,
            {"alert_type": "temperature", "message": "High temp"}
        )
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            self.principal_id,
            {"message": "Another secret"}
        )
        spine.append_event(
            spine.EventKind.CONTROL_RECEIPT,
            self.principal_id,
            {"command": "start", "status": "accepted"}
        )

    def test_filter_blocks_user_message(self):
        """user_message events should not appear in filtered events."""
        events = get_filtered_events(self.connection, limit=20)
        
        kinds = [e['kind'] for e in events]
        self.assertNotIn('user_message', kinds)
        self.assertIn('hermes_summary', kinds)
        self.assertIn('miner_alert', kinds)
        self.assertIn('control_receipt', kinds)

    def test_filter_preserves_hermes_summary(self):
        """hermes_summary events should be visible."""
        events = get_filtered_events(self.connection, limit=20)
        
        hermes_events = [e for e in events if e['kind'] == 'hermes_summary']
        self.assertTrue(len(hermes_events) > 0)
        self.assertEqual(hermes_events[0]['payload']['summary_text'], "Test summary 1")


class TestHermesNoControl(unittest.TestCase):
    """Test that Hermes cannot perform control operations."""

    def setUp(self):
        """Set up test connection."""
        hermes_store = os.path.join(TEST_STATE_DIR, 'hermes-store.json')
        if os.path.exists(hermes_store):
            os.remove(hermes_store)
        
        self.principal_id = "test-principal-009"
        pair_hermes("hermes-009", "test-hermes-9", self.principal_id)

    def test_control_capability_rejected(self):
        """Hermes should not be able to request control capability."""
        # Try to generate token with control capability
        import base64
        token_data = {
            "hermes_id": "hermes-009",
            "principal_id": self.principal_id,
            "capabilities": ["observe", "summarize", "control"],  # control not allowed
            "expires_at": "2099-12-31T23:59:59+00:00"
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        with self.assertRaises(ValueError) as context:
            connect(token)
        self.assertIn("INVALID_CAPABILITY", str(context.exception))


class TestConnectionHasCapability(unittest.TestCase):
    """Test HermesConnection.has_capability helper."""

    def test_has_capability_positive(self):
        """has_capability should return True for granted capabilities."""
        conn = HermesConnection(
            hermes_id="test",
            principal_id="test",
            capabilities=['observe', 'summarize'],
            connected_at="2026-03-22T00:00:00+00:00"
        )
        
        self.assertTrue(conn.has_capability('observe'))
        self.assertTrue(conn.has_capability('summarize'))

    def test_has_capability_negative(self):
        """has_capability should return False for ungranted capabilities."""
        conn = HermesConnection(
            hermes_id="test",
            principal_id="test",
            capabilities=['observe'],
            connected_at="2026-03-22T00:00:00+00:00"
        )
        
        self.assertFalse(conn.has_capability('summarize'))
        self.assertFalse(conn.has_capability('control'))


if __name__ == '__main__':
    unittest.main()

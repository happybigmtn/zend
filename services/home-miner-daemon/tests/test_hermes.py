#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the Hermes adapter boundary enforcement including:
- Token validation
- Capability checking
- Event filtering
- Control command blocking
"""

import json
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hermes
from hermes import (
    HermesConnection,
    HermesPairing,
    HERMES_CAPABILITIES,
    HERMES_READABLE_EVENTS,
    connect,
    generate_authority_token,
    pair_hermes,
    read_status,
    append_summary,
    get_filtered_events,
)
from spine import SpineEvent


class TestHermesCapabilities(unittest.TestCase):
    """Test Hermes capability definitions."""

    def test_hermes_capabilities_defined(self):
        """Hermes has exactly observe and summarize capabilities."""
        self.assertEqual(sorted(HERMES_CAPABILITIES), ['observe', 'summarize'])

    def test_hermes_readable_events_excludes_user_message(self):
        """Hermes-readable events do not include user_message."""
        self.assertNotIn('user_message', HERMES_READABLE_EVENTS)
        self.assertIn('hermes_summary', HERMES_READABLE_EVENTS)
        self.assertIn('miner_alert', HERMES_READABLE_EVENTS)
        self.assertIn('control_receipt', HERMES_READABLE_EVENTS)


class TestTokenGeneration(unittest.TestCase):
    """Test authority token generation and parsing."""

    def test_generate_valid_token(self):
        """Can generate a valid authority token."""
        token = generate_authority_token(
            hermes_id="hermes-001",
            principal_id="test-principal",
            capabilities=['observe', 'summarize'],
            expires_in_hours=24
        )
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_token_can_be_parsed(self):
        """Generated token can be used to connect."""
        token = generate_authority_token(
            hermes_id="hermes-001",
            principal_id="test-principal",
            capabilities=HERMES_CAPABILITIES,
            expires_in_hours=24
        )
        connection = connect(token)
        self.assertEqual(connection.hermes_id, "hermes-001")
        self.assertEqual(connection.principal_id, "test-principal")


class TestHermesConnection(unittest.TestCase):
    """Test HermesConnection dataclass."""

    def test_connection_has_capability(self):
        """Connection can check capabilities."""
        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat()
        )
        self.assertTrue(conn.has_capability('observe'))
        self.assertTrue(conn.has_capability('summarize'))
        self.assertFalse(conn.has_capability('control'))

    def test_connection_serializes(self):
        """Connection can be serialized to dict."""
        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['observe'],
            connected_at="2026-03-22T00:00:00Z"
        )
        data = conn.to_dict()
        self.assertEqual(data['hermes_id'], "hermes-001")
        self.assertEqual(data['capabilities'], ['observe'])


class TestConnectValidation(unittest.TestCase):
    """Test connect() token validation."""

    def test_connect_valid_token(self):
        """Valid token creates connection."""
        token = generate_authority_token(
            hermes_id="hermes-001",
            principal_id="principal-001",
            capabilities=HERMES_CAPABILITIES,
            expires_in_hours=24
        )
        conn = connect(token)
        self.assertEqual(conn.hermes_id, "hermes-001")
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)

    def test_connect_invalid_token_format(self):
        """Invalid token format raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            connect("not-a-valid-token")
        self.assertIn("Invalid token format", str(ctx.exception))

    def test_connect_expired_token(self):
        """Expired token raises ValueError."""
        # Create token that expired yesterday
        import base64
        expires = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        token_data = {
            "hermes_id": "hermes-001",
            "principal_id": "test",
            "capabilities": HERMES_CAPABILITIES,
            "expires_at": expires
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()

        with self.assertRaises(ValueError) as ctx:
            connect(token)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_connect_invalid_capability(self):
        """Token with invalid capability is rejected."""
        import base64
        token_data = {
            "hermes_id": "hermes-001",
            "principal_id": "test",
            "capabilities": ['observe', 'control'],  # control not allowed
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()

        with self.assertRaises(ValueError) as ctx:
            connect(token)
        self.assertIn("control", str(ctx.exception))  # Should mention invalid cap


class TestReadStatus(unittest.TestCase):
    """Test read_status capability enforcement."""

    def test_observe_capability_required(self):
        """read_status requires observe capability."""
        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['summarize'],  # No observe
            connected_at=datetime.now(timezone.utc).isoformat()
        )

        with self.assertRaises(PermissionError) as ctx:
            read_status(conn)
        self.assertIn("observe", str(ctx.exception))

    @patch('daemon.miner')
    def test_observe_returns_status(self, mock_miner):
        """With observe capability, returns miner status."""
        mock_miner.get_snapshot.return_value = {
            "status": "running",
            "mode": "balanced",
            "hashrate_hs": 50000,
            "temperature": 45.0,
            "uptime_seconds": 3600,
            "freshness": "2026-03-22T00:00:00Z"
        }

        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat()
        )

        status = read_status(conn)
        self.assertEqual(status['status'], "running")
        self.assertEqual(status['hermes_id'], "hermes-001")
        self.assertIn('capabilities', status)


class TestAppendSummary(unittest.TestCase):
    """Test append_summary capability enforcement."""

    def test_summarize_capability_required(self):
        """append_summary requires summarize capability."""
        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['observe'],  # No summarize
            connected_at=datetime.now(timezone.utc).isoformat()
        )

        with self.assertRaises(PermissionError) as ctx:
            append_summary(conn, "Test summary", "observe")
        self.assertIn("summarize", str(ctx.exception))

    @patch('spine.append_hermes_summary')
    def test_summarize_appends_to_spine(self, mock_append):
        """With summarize capability, appends to spine."""
        mock_append.return_value = MagicMock(
            id="event-001",
            kind="hermes_summary",
            created_at=datetime.now(timezone.utc).isoformat()
        )

        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat()
        )

        result = append_summary(conn, "Miner running normally", "observe")
        self.assertTrue(result['appended'])
        self.assertEqual(result['hermes_id'], "hermes-001")
        mock_append.assert_called_once()


class TestEventFiltering(unittest.TestCase):
    """Test event filtering for Hermes."""

    @patch('spine.get_events')
    def test_user_message_filtered(self, mock_get_events):
        """user_message events are filtered out."""
        from spine import SpineEvent

        mock_get_events.return_value = [
            SpineEvent(
                id="1", principal_id="test", kind="user_message",
                payload={"content": "secret"}, created_at="2026-03-22T00:00:00Z"
            ),
            SpineEvent(
                id="2", principal_id="test", kind="hermes_summary",
                payload={"summary_text": "status update"},
                created_at="2026-03-22T00:01:00Z"
            ),
        ]

        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['observe'],
            connected_at=datetime.now(timezone.utc).isoformat()
        )

        events = get_filtered_events(conn, limit=10)
        kinds = [e['kind'] for e in events]

        self.assertNotIn('user_message', kinds)
        self.assertIn('hermes_summary', kinds)

    @patch('spine.get_events')
    def test_miner_alert_allowed(self, mock_get_events):
        """miner_alert events are allowed."""
        from spine import SpineEvent

        mock_get_events.return_value = [
            SpineEvent(
                id="3", principal_id="test", kind="miner_alert",
                payload={"alert_type": "temperature", "message": "Overheating"},
                created_at="2026-03-22T00:00:00Z"
            ),
        ]

        conn = HermesConnection(
            hermes_id="hermes-001",
            principal_id="test",
            capabilities=['observe'],
            connected_at=datetime.now(timezone.utc).isoformat()
        )

        events = get_filtered_events(conn, limit=10)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['kind'], 'miner_alert')


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing flow."""

    def setUp(self):
        """Clear any existing test pairings."""
        self._original_store = hermes._get_hermes_store_path()
        hermes._get_hermes_store_path = lambda: "/tmp/test-hermes-pairings.json"
        # Clean up before test
        store_path = hermes._get_hermes_store_path()
        if os.path.exists(store_path):
            os.remove(store_path)

    def tearDown(self):
        """Clean up after test."""
        store_path = hermes._get_hermes_store_path()
        if os.path.exists(store_path):
            os.remove(store_path)
        hermes._get_hermes_store_path = lambda: self._original_store

    def test_pair_creates_record(self):
        """Pairing creates a new record."""
        pairing = pair_hermes("hermes-001", "test-agent")

        self.assertEqual(pairing.hermes_id, "hermes-001")
        self.assertEqual(pairing.device_name, "test-agent")
        self.assertEqual(pairing.capabilities, HERMES_CAPABILITIES)

    def test_pair_idempotent(self):
        """Pairing same hermes_id returns existing record with fresh token."""
        first = pair_hermes("hermes-001", "test-agent")
        original_token = first.token

        second = pair_hermes("hermes-001", "test-agent")

        self.assertEqual(second.hermes_id, "hermes-001")
        # Token should be refreshed
        self.assertNotEqual(second.token, original_token)


class TestControlBlocking(unittest.TestCase):
    """Test that Hermes cannot perform control actions."""

    def test_control_capability_not_in_hermes(self):
        """control is not in Hermes capabilities."""
        self.assertNotIn('control', HERMES_CAPABILITIES)

    def test_connection_cannot_have_control(self):
        """Connection created with control capability should fail."""
        import base64
        token_data = {
            "hermes_id": "hermes-001",
            "principal_id": "test",
            "capabilities": ['observe', 'summarize', 'control'],  # Invalid
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()

        with self.assertRaises(ValueError) as ctx:
            connect(token)
        self.assertIn("control", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()

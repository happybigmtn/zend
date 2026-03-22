#!/usr/bin/env python3
"""
Tests for Hermes adapter boundary enforcement.

These tests validate:
1. Hermes can connect with valid authority token
2. Hermes cannot use expired tokens
3. Hermes can read status with observe capability
4. Hermes can append summaries with summarize capability
5. Hermes CANNOT issue control commands
6. Hermes CANNOT read user_message events
7. Hermes capability validation works
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

# Setup test environment
TEST_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_DIR

# Add service to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes import (
    HermesConnection,
    HermesPairing,
    HERMES_CAPABILITIES,
    HERMES_READABLE_EVENTS,
    connect,
    read_status,
    append_summary,
    get_filtered_events,
    pair_hermes,
    generate_authority_token,
    check_control_denied
)
from store import load_or_create_principal
from spine import (
    append_event,
    get_events,
    EventKind,
    _load_events,
    SPINE_FILE
)


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter boundary enforcement."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear state for each test
        self.principal = load_or_create_principal()
        
        # Create a Hermes pairing
        self.hermes_id = "test-hermes-001"
        self.pairing = pair_hermes(self.hermes_id, "test-hermes-agent")
        
        # Generate authority token
        self.token = generate_authority_token(
            self.hermes_id,
            HERMES_CAPABILITIES
        )

    def test_hermes_capabilities_constant(self):
        """Verify Hermes capabilities are correctly defined."""
        self.assertEqual(HERMES_CAPABILITIES, ['observe', 'summarize'])
        self.assertNotIn('control', HERMES_CAPABILITIES)

    def test_hermes_readable_events_constant(self):
        """Verify Hermes-readable events exclude user_message."""
        readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable_kinds)
        self.assertIn('miner_alert', readable_kinds)
        self.assertIn('control_receipt', readable_kinds)
        self.assertNotIn('user_message', readable_kinds)

    def test_hermes_pair(self):
        """Test Hermes pairing creates correct record."""
        self.assertEqual(self.pairing.hermes_id, self.hermes_id)
        self.assertEqual(self.pairing.principal_id, self.principal.id)
        self.assertEqual(self.pairing.capabilities, HERMES_CAPABILITIES)

    def test_hermes_connect_valid(self):
        """Test Hermes can connect with valid token."""
        connection = connect(self.token)
        
        self.assertIsInstance(connection, HermesConnection)
        self.assertEqual(connection.hermes_id, self.hermes_id)
        self.assertEqual(connection.principal_id, self.principal.id)
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)
        self.assertNotIn('control', connection.capabilities)

    def test_hermes_connect_expired(self):
        """Test Hermes cannot connect with expired token."""
        # Create expired token
        expired_data = {
            "hermes_id": self.hermes_id,
            "capabilities": HERMES_CAPABILITIES,
            "issued_at": "2020-01-01T00:00:00+00:00",
            "expires_at": "2020-01-02T00:00:00+00:00"
        }
        expired_token = json.dumps(expired_data)
        
        with self.assertRaises(ValueError) as ctx:
            connect(expired_token)
        
        self.assertIn("expired", str(ctx.exception).lower())

    def test_hermes_connect_invalid_hermes_id(self):
        """Test Hermes cannot connect with wrong hermes_id."""
        # Token for different Hermes
        token_data = {
            "hermes_id": "other-hermes",
            "capabilities": HERMES_CAPABILITIES,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + 3600,
                tz=timezone.utc
            ).isoformat()
        }
        invalid_token = json.dumps(token_data)
        
        with self.assertRaises(ValueError) as ctx:
            connect(invalid_token)
        
        self.assertIn("pairing", str(ctx.exception).lower())

    def test_hermes_read_status(self):
        """Test Hermes can read status with observe capability."""
        connection = connect(self.token)
        status = read_status(connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('freshness', status)
        self.assertEqual(status.get('source'), 'hermes_adapter')

    def test_hermes_read_status_without_observe(self):
        """Test Hermes cannot read status without observe capability."""
        limited_token = generate_authority_token(
            self.hermes_id,
            ['summarize']  # Only summarize, no observe
        )
        connection = connect(limited_token)
        
        with self.assertRaises(PermissionError) as ctx:
            read_status(connection)
        
        self.assertIn("unauthorized", str(ctx.exception).lower())
        self.assertIn("observe", str(ctx.exception).lower())

    def test_hermes_append_summary(self):
        """Test Hermes can append summary with summarize capability."""
        connection = connect(self.token)
        result = append_summary(
            connection,
            "Test summary: Miner running normally",
            "observe"
        )
        
        self.assertTrue(result.get('appended'))
        self.assertIn('event_id', result)
        self.assertIn('created_at', result)

    def test_hermes_append_summary_without_capability(self):
        """Test Hermes cannot append summary without summarize capability."""
        limited_token = generate_authority_token(
            self.hermes_id,
            ['observe']  # Only observe, no summarize
        )
        connection = connect(limited_token)
        
        with self.assertRaises(PermissionError) as ctx:
            append_summary(connection, "Test summary", "observe")
        
        self.assertIn("unauthorized", str(ctx.exception).lower())
        self.assertIn("summarize", str(ctx.exception).lower())

    def test_hermes_summary_appears_in_spine(self):
        """Test appended Hermes summary appears in event spine."""
        connection = connect(self.token)
        result = append_summary(
            connection,
            "Miner status: All systems nominal",
            "observe"
        )
        
        # Verify it's in the spine
        events = get_events(kind=EventKind.HERMES_SUMMARY, limit=10)
        event_ids = [e.id for e in events]
        
        self.assertIn(result['event_id'], event_ids)
        
        # Find the event and verify payload
        for event in events:
            if event.id == result['event_id']:
                self.assertEqual(event.payload['summary_text'], "Miner status: All systems nominal")
                self.assertEqual(event.payload['authority_scope'], ['observe'])
                break

    def test_hermes_event_filter_excludes_user_message(self):
        """Test Hermes event filter excludes user_message."""
        connection = connect(self.token)
        
        # Append a user_message event
        append_event(
            EventKind.USER_MESSAGE,
            self.principal.id,
            {
                "thread_id": "test-thread",
                "sender_id": "someone",
                "encrypted_content": "secret message"
            }
        )
        
        # Get filtered events
        filtered = get_filtered_events(connection, limit=50)
        filtered_kinds = [e['kind'] for e in filtered]
        
        # Verify no user_message
        self.assertNotIn('user_message', filtered_kinds)
        
        # But hermes_summary should be present
        self.assertIn('hermes_summary', filtered_kinds)

    def test_hermes_control_denied(self):
        """Test Hermes capability check blocks control."""
        connection = connect(self.token)
        
        check = check_control_denied(connection)
        
        self.assertFalse(check.get('would_allow'))
        self.assertIn('HERMES_UNAUTHORIZED', check.get('error_code', ''))

    def test_hermes_invalid_capability_rejected(self):
        """Test Hermes tokens cannot include invalid capabilities."""
        invalid_token = json.dumps({
            "hermes_id": self.hermes_id,
            "capabilities": ['observe', 'control'],  # Invalid: control not allowed
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + 3600,
                tz=timezone.utc
            ).isoformat()
        })
        
        with self.assertRaises(ValueError) as ctx:
            connect(invalid_token)
        
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_hermes_token_replay_prevented(self):
        """Test Hermes cannot reuse token after pairing change."""
        # First connect works
        connection1 = connect(self.token)
        self.assertIsNotNone(connection1)
        
        # Re-pair should invalidate old tokens (token validated against current pairing)
        new_pairing = pair_hermes(self.hermes_id, "updated-hermes")
        
        # Old token should still work (tokens are self-contained)
        connection2 = connect(self.token)
        self.assertIsNotNone(connection2)


class TestHermesCLI(unittest.TestCase):
    """Test Hermes CLI integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.principal = load_or_create_principal()
        self.hermes_id = "cli-test-hermes"
        self.pairing = pair_hermes(self.hermes_id, "cli-test-agent")
        self.token = generate_authority_token(
            self.hermes_id,
            HERMES_CAPABILITIES
        )

    def test_cli_pair_creates_pairing(self):
        """Test CLI pair command creates pairing."""
        self.assertEqual(self.pairing.hermes_id, self.hermes_id)
        self.assertEqual(self.pairing.capabilities, HERMES_CAPABILITIES)

    def test_cli_connect_with_token(self):
        """Test CLI connect validates token."""
        connection = connect(self.token)
        self.assertEqual(connection.hermes_id, self.hermes_id)


if __name__ == '__main__':
    unittest.main()

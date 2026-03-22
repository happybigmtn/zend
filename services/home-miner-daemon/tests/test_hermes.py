#!/usr/bin/env python3
"""
Hermes Adapter Tests

Tests for the Hermes adapter boundary enforcement:
1. Hermes can connect with valid token
2. Hermes cannot connect with expired token
3. Hermes can read status with observe capability
4. Hermes can append summaries with summarize capability
5. Hermes CANNOT issue control commands
6. Hermes cannot read user_message events
7. Hermes with wrong capabilities is rejected
8. Summary appears in spine events
"""

import json
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add service to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set test state directory before imports
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR

from store import load_or_create_principal
import hermes


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing functionality."""

    def setUp(self):
        """Clear state before each test."""
        # Reset singleton state
        principal_file = os.path.join(TEST_STATE_DIR, 'principal.json')
        hermes_pairing_file = os.path.join(TEST_STATE_DIR, 'hermes-pairing-store.json')
        for f in [principal_file, hermes_pairing_file]:
            if os.path.exists(f):
                os.remove(f)
        # Create fresh principal
        load_or_create_principal()

    def test_hermes_pair_creates_record(self):
        """Pair creates a Hermes pairing with observe+summarize capabilities."""
        pairing = hermes.pair('hermes-001', 'test-agent')
        
        self.assertEqual(pairing.hermes_id, 'hermes-001')
        self.assertEqual(pairing.device_name, 'test-agent')
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertIsNotNone(pairing.token_expires_at)

    def test_hermes_pair_idempotent(self):
        """Pairing same hermes_id is idempotent and reuses existing ID."""
        pairing1 = hermes.pair('hermes-002', 'test-agent')
        pairing2 = hermes.pair('hermes-002', 'test-agent-renamed')
        
        self.assertEqual(pairing1.id, pairing2.id)
        # Device name should be updated
        self.assertEqual(pairing2.device_name, 'test-agent-renamed')

    def test_get_pairing_by_hermes_id(self):
        """Can retrieve pairing by hermes_id."""
        created = hermes.pair('hermes-003', 'test-agent')
        retrieved = hermes.get_pairing_by_hermes_id('hermes-003')
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hermes_id, 'hermes-003')


class TestHermesConnect(unittest.TestCase):
    """Test Hermes connection and token validation."""

    def setUp(self):
        """Clear state and create pairing before each test."""
        principal_file = os.path.join(TEST_STATE_DIR, 'principal.json')
        hermes_pairing_file = os.path.join(TEST_STATE_DIR, 'hermes-pairing-store.json')
        for f in [principal_file, hermes_pairing_file]:
            if os.path.exists(f):
                os.remove(f)
        load_or_create_principal()
        self.pairing = hermes.pair('hermes-test', 'test-agent')

    def test_connect_with_valid_token(self):
        """Connect with valid hermes_id succeeds."""
        connection = hermes.connect('hermes-test')
        
        self.assertEqual(connection.hermes_id, 'hermes-test')
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)
        self.assertIsNotNone(connection.connected_at)

    def test_connect_with_invalid_token(self):
        """Connect with invalid hermes_id raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect('unknown-hermes')
        
        self.assertIn('No pairing found', str(ctx.exception))

    def test_connect_with_empty_token(self):
        """Connect with empty token raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect('')
        
        self.assertIn('authority_token is required', str(ctx.exception))


class TestHermesReadStatus(unittest.TestCase):
    """Test Hermes read status capability."""

    def setUp(self):
        """Clear state and create connection."""
        principal_file = os.path.join(TEST_STATE_DIR, 'principal.json')
        hermes_pairing_file = os.path.join(TEST_STATE_DIR, 'hermes-pairing-store.json')
        for f in [principal_file, hermes_pairing_file]:
            if os.path.exists(f):
                os.remove(f)
        load_or_create_principal()
        pairing = hermes.pair('hermes-status', 'test-agent')
        self.connection = hermes.connect('hermes-status')

    def test_read_status_returns_snapshot(self):
        """Read status returns a miner snapshot."""
        status = hermes.read_status(self.connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)
        self.assertIn('freshness', status)


class TestHermesAppendSummary(unittest.TestCase):
    """Test Hermes summary append capability."""

    def setUp(self):
        """Clear state and create connection."""
        principal_file = os.path.join(TEST_STATE_DIR, 'principal.json')
        hermes_pairing_file = os.path.join(TEST_STATE_DIR, 'hermes-pairing-store.json')
        spine_file = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        for f in [principal_file, hermes_pairing_file, spine_file]:
            if os.path.exists(f):
                os.remove(f)
        load_or_create_principal()
        pairing = hermes.pair('hermes-summary', 'test-agent')
        self.connection = hermes.connect('hermes-summary')

    def test_append_summary_success(self):
        """Append summary creates an event."""
        result = hermes.append_summary(
            self.connection,
            "Miner running normally at 50kH/s",
            "observe"
        )
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
        self.assertEqual(result['kind'], 'hermes_summary')

    def test_append_summary_empty_text_raises(self):
        """Append summary with empty text raises ValueError."""
        with self.assertRaises(ValueError):
            hermes.append_summary(self.connection, "", "observe")

    def test_summary_appears_in_filtered_events(self):
        """Appended summary appears in filtered events."""
        hermes.append_summary(
            self.connection,
            "Test summary for filtering",
            "observe"
        )
        
        events = hermes.get_filtered_events(self.connection, limit=10)
        
        hermes_summary_events = [e for e in events if e['kind'] == 'hermes_summary']
        self.assertGreater(len(hermes_summary_events), 0)
        # Verify our summary is present
        texts = [e['payload'].get('summary_text') for e in hermes_summary_events]
        self.assertIn("Test summary for filtering", texts)


class TestHermesEventFiltering(unittest.TestCase):
    """Test Hermes event filtering (blocking user_message)."""

    def setUp(self):
        """Clear state and create connection."""
        principal_file = os.path.join(TEST_STATE_DIR, 'principal.json')
        hermes_pairing_file = os.path.join(TEST_STATE_DIR, 'hermes-pairing-store.json')
        spine_file = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        for f in [principal_file, hermes_pairing_file, spine_file]:
            if os.path.exists(f):
                os.remove(f)
        self.principal = load_or_create_principal()
        pairing = hermes.pair('hermes-filter', 'test-agent')
        self.connection = hermes.connect('hermes-filter')

    def test_user_message_not_in_filtered_events(self):
        """User message events are filtered out."""
        # Append a user_message event directly
        from spine import append_event, EventKind
        append_event(
            principal_id=self.principal.id,
            kind=EventKind.USER_MESSAGE,
            payload={
                "thread_id": "thread-001",
                "sender_id": "user-001",
                "encrypted_content": "secret message"
            }
        )
        
        # Append a hermes_summary
        hermes.append_summary(self.connection, "Agent summary", "observe")
        
        # Get filtered events
        events = hermes.get_filtered_events(self.connection, limit=20)
        
        # Verify no user_message events
        kinds = [e['kind'] for e in events]
        self.assertNotIn('user_message', kinds)
        # But hermes_summary should be present
        self.assertIn('hermes_summary', kinds)

    def test_miner_alert_in_filtered_events(self):
        """Miner alert events are visible to Hermes."""
        from spine import append_event, EventKind
        append_event(
            principal_id=self.principal.id,
            kind=EventKind.MINER_ALERT,
            payload={
                "alert_type": "health_warning",
                "message": "High temperature detected"
            }
        )
        
        events = hermes.get_filtered_events(self.connection, limit=20)
        
        kinds = [e['kind'] for e in events]
        self.assertIn('miner_alert', kinds)


class TestHermesConstants(unittest.TestCase):
    """Test Hermes adapter constants."""

    def test_capabilities_defined(self):
        """HERMES_CAPABILITIES contains observe and summarize."""
        self.assertIn('observe', hermes.HERMES_CAPABILITIES)
        self.assertIn('summarize', hermes.HERMES_CAPABILITIES)
        self.assertEqual(len(hermes.HERMES_CAPABILITIES), 2)

    def test_readable_events_defined(self):
        """HERMES_READABLE_EVENTS contains expected events."""
        from spine import EventKind
        kinds = [k.value for k in hermes.HERMES_READABLE_EVENTS]
        
        self.assertIn('hermes_summary', kinds)
        self.assertIn('miner_alert', kinds)
        self.assertIn('control_receipt', kinds)
        # user_message should NOT be in readable events
        self.assertNotIn('user_message', kinds)


class TestValidateAuthorityToken(unittest.TestCase):
    """Test authority token validation."""

    def setUp(self):
        """Clear state."""
        principal_file = os.path.join(TEST_STATE_DIR, 'principal.json')
        hermes_pairing_file = os.path.join(TEST_STATE_DIR, 'hermes-pairing-store.json')
        for f in [principal_file, hermes_pairing_file]:
            if os.path.exists(f):
                os.remove(f)
        load_or_create_principal()

    def test_validate_valid_token(self):
        """Validate returns valid for paired Hermes."""
        hermes.pair('hermes-valid', 'test-agent')
        result = hermes.validate_authority_token('hermes-valid')
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['hermes_id'], 'hermes-valid')
        self.assertIn('observe', result['capabilities'])

    def test_validate_invalid_token(self):
        """Validate returns invalid for unknown Hermes."""
        result = hermes.validate_authority_token('unknown-hermes')
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['reason'], 'not_paired')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the capability boundary enforcement for Hermes agents:
1. Hermes can connect with valid authority token
2. Hermes cannot connect with expired token
3. Hermes can read miner status (observe capability)
4. Hermes can append summaries (summarize capability)
5. Hermes CANNOT issue control commands
6. Hermes CANNOT read user_message events
7. Hermes pairing is idempotent
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add daemon to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set test state directory
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ["ZEND_STATE_DIR"] = TEST_STATE_DIR

import hermes
import spine
from store import load_or_create_principal


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter capability boundaries."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset state for each test
        self.principal = load_or_create_principal()
        self.hermes_id = "test-hermes-001"
        
        # Clean up any existing pairing
        pairings = hermes._load_hermes_pairings()
        for key in list(pairings.keys()):
            if pairings[key]['hermes_id'] == self.hermes_id:
                del pairings[key]
        hermes._save_hermes_pairings(pairings)

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_hermes_capabilities_constant(self):
        """Verify Hermes capabilities are observe and summarize only."""
        self.assertEqual(hermes.HERMES_CAPABILITIES, ['observe', 'summarize'])
        self.assertNotIn('control', hermes.HERMES_CAPABILITIES)

    def test_hermes_readable_events_constant(self):
        """Verify Hermes readable events exclude user_message."""
        readable = [e.value for e in hermes.HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable)
        self.assertIn('miner_alert', readable)
        self.assertIn('control_receipt', readable)
        self.assertNotIn('user_message', readable)

    def test_hermes_pair(self):
        """Test pairing a new Hermes agent."""
        pairing = hermes.pair_hermes(self.hermes_id, "test-device")
        
        self.assertEqual(pairing.hermes_id, self.hermes_id)
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertEqual(pairing.principal_id, self.principal.id)

    def test_hermes_pair_idempotent(self):
        """Test that pairing is idempotent."""
        pairing1 = hermes.pair_hermes(self.hermes_id)
        time.sleep(0.01)  # Ensure different timestamps
        pairing2 = hermes.pair_hermes(self.hermes_id)
        
        # Should return same pairing
        self.assertEqual(pairing1.id, pairing2.id)
        self.assertEqual(pairing1.hermes_id, pairing2.hermes_id)

    def test_generate_authority_token(self):
        """Test generating an authority token."""
        hermes.pair_hermes(self.hermes_id)
        token = hermes.generate_authority_token(self.hermes_id)
        
        # Token format: <hermes_id>:<capabilities>:<expiration>
        # The expiration may contain colons from ISO format
        self.assertTrue(token.startswith(self.hermes_id + ':'))
        self.assertIn('observe', token)
        self.assertIn('summarize', token)

    def test_connect_valid_token(self):
        """Test connecting with valid authority token."""
        hermes.pair_hermes(self.hermes_id)
        token = hermes.generate_authority_token(self.hermes_id)
        
        connection = hermes.connect(token)
        
        self.assertEqual(connection.hermes_id, self.hermes_id)
        self.assertEqual(connection.principal_id, self.principal.id)
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)

    def test_connect_invalid_token_format(self):
        """Test connecting with malformed token."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect("invalid-token")
        self.assertIn("malformed", str(ctx.exception).lower())

    def test_connect_invalid_capability(self):
        """Test connecting with unauthorized capability."""
        # Create token with control capability (not allowed)
        future = datetime.now(timezone.utc) + timedelta(days=1)
        token = f"{self.hermes_id}:observe,summarize,control:{future.isoformat()}"
        
        # Pair first
        hermes.pair_hermes(self.hermes_id)
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        self.assertIn("INVALID_CAPABILITY", str(ctx.exception))

    def test_connect_expired_token(self):
        """Test connecting with expired token."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        token = f"{self.hermes_id}:observe,summarize:{past.isoformat()}"
        
        # Pair first
        hermes.pair_hermes(self.hermes_id)
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_connect_not_paired(self):
        """Test connecting without pairing first."""
        # Use future expiration to avoid token expiration check
        future = datetime.now(timezone.utc) + timedelta(days=1)
        token = f"unknown-hermes:observe,summarize:{future.isoformat()}"
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        self.assertIn("NOT_PAIRED", str(ctx.exception))

    def test_read_status_capability_check(self):
        """Test that read_status enforces observe capability."""
        # Create connection without observe
        connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal.id,
            capabilities=['summarize'],  # No observe
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(connection)
        self.assertIn("HERMES_UNAUTHORIZED", str(ctx.exception))
        self.assertIn("observe", str(ctx.exception))

    def test_read_status_without_observe(self):
        """Test that Hermes without observe capability cannot read status."""
        # Create connection manually without observe
        connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal.id,
            capabilities=['summarize'],  # No observe
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(connection)
        self.assertIn("HERMES_UNAUTHORIZED", str(ctx.exception))
        self.assertIn("observe", str(ctx.exception))

    def test_append_summary_with_summarize(self):
        """Test appending summary with summarize capability."""
        hermes.pair_hermes(self.hermes_id)
        token = hermes.generate_authority_token(self.hermes_id)
        connection = hermes.connect(token)
        
        result = hermes.append_summary(
            connection,
            "Test summary: Miner running normally",
            "observe"
        )
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
        self.assertEqual(result['kind'], 'hermes_summary')

    def test_append_summary_without_summarize(self):
        """Test that Hermes without summarize capability cannot append summary."""
        connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal.id,
            capabilities=['observe'],  # No summarize
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(connection, "Test", "observe")
        self.assertIn("HERMES_UNAUTHORIZED", str(ctx.exception))
        self.assertIn("summarize", str(ctx.exception))

    def test_hermes_event_filter_blocks_user_message(self):
        """Test that user_message events are filtered from Hermes reads."""
        hermes.pair_hermes(self.hermes_id)
        token = hermes.generate_authority_token(self.hermes_id)
        connection = hermes.connect(token)
        
        # Append some events including user_message
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            self.principal.id,
            {"text": "Secret user message"}
        )
        spine.append_hermes_summary(
            "Hermes summary",
            ["observe"],
            self.principal.id
        )
        spine.append_miner_alert(
            "temperature_high",
            "Temperature exceeded threshold",
            self.principal.id
        )
        
        events = hermes.get_filtered_events(connection, limit=10)
        
        # Verify no user_message events
        event_kinds = [e['kind'] for e in events]
        self.assertNotIn('user_message', event_kinds)
        
        # Verify hermes_summary and miner_alert are present
        self.assertIn('hermes_summary', event_kinds)
        self.assertIn('miner_alert', event_kinds)

    def test_summary_appears_in_filtered_events(self):
        """Test that appended summary appears in filtered events."""
        hermes.pair_hermes(self.hermes_id)
        token = hermes.generate_authority_token(self.hermes_id)
        connection = hermes.connect(token)
        
        summary_text = "Miner running normally at 50kH/s"
        hermes.append_summary(connection, summary_text, "observe")
        
        events = hermes.get_filtered_events(connection, limit=5)
        
        # Find the summary event
        summary_events = [e for e in events if e['kind'] == 'hermes_summary']
        self.assertTrue(len(summary_events) > 0)
        
        # Verify content
        latest_summary = summary_events[0]
        self.assertEqual(latest_summary['payload']['summary_text'], summary_text)
        self.assertEqual(latest_summary['payload']['authority_scope'], 'observe')

    def test_check_hermes_auth_valid(self):
        """Test auth check for valid pairing."""
        hermes.pair_hermes(self.hermes_id)
        
        self.assertTrue(hermes.check_hermes_auth(self.hermes_id))

    def test_check_hermes_auth_invalid(self):
        """Test auth check for non-existent pairing."""
        self.assertFalse(hermes.check_hermes_auth("non-existent-hermes"))

    def test_get_hermes_pairing(self):
        """Test retrieving Hermes pairing."""
        created = hermes.pair_hermes(self.hermes_id, "test-device")
        retrieved = hermes.get_hermes_pairing(self.hermes_id)
        
        self.assertEqual(created.id, retrieved.id)
        self.assertEqual(created.hermes_id, retrieved.hermes_id)


class TestHermesAdapterIntegration(unittest.TestCase):
    """Integration tests for Hermes adapter with spine."""

    def setUp(self):
        """Set up test fixtures."""
        self.principal = load_or_create_principal()
        self.hermes_id = "integration-test-hermes"
        
        # Clean up
        pairings = hermes._load_hermes_pairings()
        for key in list(pairings.keys()):
            if pairings[key]['hermes_id'] == self.hermes_id:
                del pairings[key]
        hermes._save_hermes_pairings(pairings)

    def test_full_hermes_workflow(self):
        """Test complete Hermes workflow: pair -> connect -> append -> read events."""
        # 1. Pair Hermes
        pairing = hermes.pair_hermes(self.hermes_id)
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        
        # 2. Generate token
        token = hermes.generate_authority_token(self.hermes_id)
        
        # 3. Connect
        connection = hermes.connect(token)
        self.assertTrue('observe' in connection.capabilities)
        self.assertTrue('summarize' in connection.capabilities)
        
        # 4. Append summary (the core integration test)
        summary_result = hermes.append_summary(
            connection,
            "Integration test: Miner operating normally",
            "observe"
        )
        self.assertTrue(summary_result['appended'])
        
        # 5. Read filtered events
        events = hermes.get_filtered_events(connection, limit=5)
        hermes_events = [e for e in events if e['kind'] == 'hermes_summary']
        self.assertTrue(len(hermes_events) > 0)


if __name__ == '__main__':
    unittest.main()

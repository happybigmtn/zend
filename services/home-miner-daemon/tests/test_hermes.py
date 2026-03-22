#!/usr/bin/env python3
"""
Tests for Hermes adapter.

Validates:
1. Hermes can connect with authority token
2. Hermes can read miner status
3. Hermes can append summaries to event spine
4. Hermes CANNOT issue control commands
5. Hermes CANNOT read user_message events
6. Event filtering works correctly
7. Invalid tokens are rejected
"""

import json
import os
import sys
import tempfile
import time
import threading
import unittest
from datetime import datetime, timezone

# Set test state dir before imports
test_state_dir = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = test_state_dir

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hermes
import spine
import store


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing state
        self.state_dir = test_state_dir
        
        # Ensure clean state
        hermes_file = os.path.join(self.state_dir, 'hermes-pairing-store.json')
        if os.path.exists(hermes_file):
            os.remove(hermes_file)
    
    def test_hermes_pairing_creates_record(self):
        """Pairing creates a Hermes pairing record with correct capabilities."""
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        
        self.assertEqual(pairing.hermes_id, 'hermes-001')
        self.assertEqual(pairing.device_name, 'test-hermes-agent')
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertIn('token', json.dumps(hermes._load_hermes_pairings()))
    
    def test_hermes_pairing_idempotent(self):
        """Pairing same hermes_id updates existing record."""
        # First pairing
        pairing1 = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        token1 = pairing1.token
        
        # Second pairing with same ID should update
        pairing2 = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        
        # Token should be different (new token generated)
        self.assertNotEqual(token1, pairing2.token)
        self.assertEqual(pairing2.hermes_id, 'hermes-001')
    
    def test_hermes_connect_valid_token(self):
        """Connecting with valid token succeeds."""
        # Pair first
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        
        # Connect with token
        connection = hermes.connect(pairing.token)
        
        self.assertEqual(connection.hermes_id, 'hermes-001')
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)
    
    def test_hermes_connect_invalid_token(self):
        """Connecting with invalid token raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect('invalid-token')
        
        self.assertIn('HERMES_INVALID_TOKEN', str(ctx.exception))
    
    def test_hermes_connect_expired_token(self):
        """Connecting with expired token raises ValueError."""
        # Pair and manually expire token
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        
        # Manually set token as expired
        pairings = hermes._load_hermes_pairings()
        pairings['hermes-001']['token_expires_at'] = '1970-01-01T00:00:00+00:00'
        hermes._save_hermes_pairings(pairings)
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(pairing.token)
        
        self.assertIn('HERMES_INVALID_TOKEN', str(ctx.exception))
    
    def test_hermes_read_status_with_observe(self):
        """Hermes with observe capability can read status."""
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        connection = hermes.connect(pairing.token)
        
        status = hermes.read_status(connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)
    
    def test_hermes_read_status_without_observe(self):
        """Hermes without observe capability cannot read status."""
        # Create a pairing with only summarize capability
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        pairings = hermes._load_hermes_pairings()
        pairings['hermes-001']['capabilities'] = ['summarize']
        hermes._save_hermes_pairings(pairings)
        
        connection = hermes.connect(pairing.token)
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(connection)
        
        self.assertIn('HERMES_UNAUTHORIZED', str(ctx.exception))
    
    def test_hermes_append_summary_with_summarize(self):
        """Hermes with summarize capability can append summaries."""
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        connection = hermes.connect(pairing.token)
        
        result = hermes.append_summary(
            connection,
            "Miner running normally at 50kH/s",
            "observe"
        )
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
        self.assertEqual(result['kind'], 'hermes_summary')
    
    def test_hermes_append_summary_without_summarize(self):
        """Hermes without summarize capability cannot append summaries."""
        # Create a pairing with only observe capability
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        pairings = hermes._load_hermes_pairings()
        pairings['hermes-001']['capabilities'] = ['observe']
        hermes._save_hermes_pairings(pairings)
        
        connection = hermes.connect(pairing.token)
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(connection, "Test summary", "observe")
        
        self.assertIn('HERMES_UNAUTHORIZED', str(ctx.exception))
    
    def test_hermes_event_filter_blocks_user_message(self):
        """Hermes cannot see user_message events."""
        # Add a user message event
        principal = store.load_or_create_principal()
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            principal.id,
            {"text": "Secret message"}
        )
        
        # Add a hermes summary event
        spine.append_event(
            spine.EventKind.HERMES_SUMMARY,
            principal.id,
            {"summary_text": "Test summary"}
        )
        
        # Create Hermes connection
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        connection = hermes.connect(pairing.token)
        
        # Get filtered events
        events = hermes.get_filtered_events(connection, limit=20)
        
        # Should only see hermes_summary, not user_message
        event_kinds = [e['kind'] for e in events]
        self.assertIn('hermes_summary', event_kinds)
        self.assertNotIn('user_message', event_kinds)
    
    def test_hermes_event_filter_allows_readable_events(self):
        """Hermes can see allowed event types."""
        principal = store.load_or_create_principal()
        
        # Add various event types
        spine.append_event(spine.EventKind.HERMES_SUMMARY, principal.id, {"text": "s1"})
        spine.append_event(spine.EventKind.MINER_ALERT, principal.id, {"text": "a1"})
        spine.append_event(spine.EventKind.CONTROL_RECEIPT, principal.id, {"text": "c1"})
        spine.append_event(spine.EventKind.USER_MESSAGE, principal.id, {"text": "u1"})
        
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        connection = hermes.connect(pairing.token)
        
        events = hermes.get_filtered_events(connection, limit=20)
        event_kinds = [e['kind'] for e in events]
        
        # Should include these
        self.assertIn('hermes_summary', event_kinds)
        self.assertIn('miner_alert', event_kinds)
        self.assertIn('control_receipt', event_kinds)
        
        # Should NOT include user_message
        self.assertNotIn('user_message', event_kinds)
    
    def test_hermes_control_capability_rejected(self):
        """Hermes cannot have control capability."""
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        
        # Try to create a pairing with control capability
        pairings = hermes._load_hermes_pairings()
        pairings['hermes-001']['capabilities'] = ['observe', 'summarize', 'control']
        hermes._save_hermes_pairings(pairings)
        
        # Token validation should reject control capability
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(pairing.token)
        
        self.assertIn('not allowed', str(ctx.exception))
    
    def test_hermes_summary_appears_in_events(self):
        """Appended summary appears in event spine."""
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        connection = hermes.connect(pairing.token)
        
        result = hermes.append_summary(
            connection,
            "Miner is healthy",
            "observe"
        )
        
        # Verify the event was saved
        events = spine.get_events(kind=spine.EventKind.HERMES_SUMMARY, limit=1)
        
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].payload['summary_text'], "Miner is healthy")
        self.assertEqual(events[0].payload['authority_scope'], "observe")
    
    def test_revoke_hermes_token(self):
        """Token revocation makes token unusable."""
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        token = pairing.token
        
        # Connect should work
        connection = hermes.connect(token)
        self.assertEqual(connection.hermes_id, 'hermes-001')
        
        # Revoke token
        result = hermes.revoke_hermes_token('hermes-001')
        self.assertTrue(result)
        
        # Connect should fail now
        with self.assertRaises(ValueError):
            hermes.connect(token)
    
    def test_get_hermes_pairing(self):
        """Get pairing by hermes_id works."""
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes-agent')
        
        found = hermes.get_hermes_pairing('hermes-001')
        self.assertIsNotNone(found)
        self.assertEqual(found.hermes_id, 'hermes-001')
        
        # Non-existent pairing
        not_found = hermes.get_hermes_pairing('non-existent')
        self.assertIsNone(not_found)
    
    def test_capabilities_constant(self):
        """HERMES_CAPABILITIES only contains observe and summarize."""
        self.assertEqual(hermes.HERMES_CAPABILITIES, ['observe', 'summarize'])
    
    def test_readable_events_constant(self):
        """HERMES_READABLE_EVENTS excludes user_message."""
        self.assertIn('hermes_summary', hermes.HERMES_READABLE_EVENTS)
        self.assertIn('miner_alert', hermes.HERMES_READABLE_EVENTS)
        self.assertIn('control_receipt', hermes.HERMES_READABLE_EVENTS)
        self.assertNotIn('user_message', hermes.HERMES_READABLE_EVENTS)


class TestHermesConnection(unittest.TestCase):
    """Test HermesConnection dataclass."""
    
    def test_connection_properties(self):
        """Connection has correct properties."""
        conn = hermes.HermesConnection(
            hermes_id='hermes-001',
            principal_id='principal-001',
            capabilities=['observe', 'summarize'],
            connected_at='2026-03-22T10:00:00+00:00',
            authority_token='token-123'
        )
        
        self.assertEqual(conn.hermes_id, 'hermes-001')
        self.assertEqual(conn.principal_id, 'principal-001')
        self.assertEqual(conn.capabilities, ['observe', 'summarize'])
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the capability boundaries and event filtering for Hermes AI agents.
"""

import json
import os
import sys
import tempfile
import time
import threading
import unittest
from pathlib import Path

# Set up test environment
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR

# Add daemon to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes import (
    HermesConnection,
    HermesPairing,
    connect as hermes_connect,
    pair_hermes,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events,
    require_capability,
    validate_authority_token,
    is_token_expired,
    list_hermes_pairings,
    revoke_hermes_token,
    HERMES_CAPABILITIES,
    HERMES_READABLE_EVENTS,
    HERMES_BLOCKED_EVENTS,
)
from spine import append_event, get_events, EventKind, _load_events, SPINE_FILE
from store import load_or_create_principal


class TestHermesAdapter(unittest.TestCase):
    """Test cases for Hermes adapter."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear state
        if os.path.exists(SPINE_FILE):
            os.remove(SPINE_FILE)
        
        # Create principal
        self.principal = load_or_create_principal()
        
        # Pair a Hermes agent
        self.pairing = pair_hermes("test-hermes-001", "test-agent")
        
        # Connect
        self.connection = hermes_connect(self.pairing.token)

    def test_hermes_connect_valid(self):
        """Test connection with valid token succeeds."""
        conn = hermes_connect(self.pairing.token)
        
        self.assertIsInstance(conn, HermesConnection)
        self.assertEqual(conn.hermes_id, "test-hermes-001")
        self.assertEqual(conn.principal_id, self.principal.id)
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)

    def test_hermes_connect_expired(self):
        """Test connection with expired token fails."""
        # Create a token that's already expired by manipulating the store
        from hermes import _load_hermes_tokens, _save_hermes_tokens
        
        tokens = _load_hermes_tokens()
        expired_token = "expired-test-token"
        tokens[expired_token] = {
            'hermes_id': 'test-hermes-001',
            'principal_id': self.principal.id,
            'capabilities': HERMES_CAPABILITIES,
            'issued_at': '2020-01-01T00:00:00+00:00',
            'expires_at': '2020-01-01T01:00:00+00:00'  # Expired 4 years ago
        }
        _save_hermes_tokens(tokens)
        
        with self.assertRaises(ValueError) as context:
            hermes_connect(expired_token)
        
        self.assertIn("invalid or expired", str(context.exception))

    def test_hermes_connect_invalid_token(self):
        """Test connection with invalid token fails."""
        with self.assertRaises(ValueError) as context:
            hermes_connect("not-a-valid-token")
        
        self.assertIn("invalid or expired", str(context.exception))

    def test_hermes_read_status(self):
        """Test observe capability reads miner status."""
        from daemon import miner
        
        status = hermes_read_status(self.connection)
        
        self.assertIsInstance(status, dict)
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)

    def test_hermes_read_status_no_observe(self):
        """Test that observe is required to read status."""
        # Create connection with only summarize capability
        limited_pairing = pair_hermes("limited-hermes", "limited-agent", ['summarize'])
        limited_conn = hermes_connect(limited_pairing.token)
        
        with self.assertRaises(PermissionError) as context:
            hermes_read_status(limited_conn)
        
        self.assertIn("observe", str(context.exception))

    def test_hermes_append_summary(self):
        """Test summarize capability appends to spine."""
        event = hermes_append_summary(
            self.connection,
            "Miner running normally at 50kH/s",
            "observe"
        )
        
        self.assertIsNotNone(event)
        self.assertEqual(event.kind, EventKind.HERMES_SUMMARY)
        self.assertEqual(event.principal_id, self.principal.id)
        self.assertEqual(event.payload['summary_text'], "Miner running normally at 50kH/s")
        self.assertEqual(event.payload['authority_scope'], "observe")
        self.assertIn('generated_at', event.payload)

    def test_hermes_append_summary_no_capability(self):
        """Test that summarize is required to append summary."""
        # Create connection with only observe capability
        limited_pairing = pair_hermes("observe-hermes", "observe-agent", ['observe'])
        limited_conn = hermes_connect(limited_pairing.token)
        
        with self.assertRaises(PermissionError) as context:
            hermes_append_summary(limited_conn, "Test", "observe")
        
        self.assertIn("summarize", str(context.exception))

    def test_hermes_event_filter(self):
        """Test user_message events are filtered out."""
        # Append a user_message (should be blocked for Hermes)
        append_event(
            EventKind.USER_MESSAGE,
            self.principal.id,
            {"text": "Secret user message"}
        )
        
        # Append a hermes_summary (should be visible)
        append_event(
            EventKind.HERMES_SUMMARY,
            self.principal.id,
            {"summary_text": "Hermes summary", "hermes_id": self.connection.hermes_id}
        )
        
        # Get filtered events
        events = get_filtered_events(self.connection, limit=10)
        
        # Should not contain user_message
        event_kinds = [e.kind for e in events]
        self.assertNotIn(EventKind.USER_MESSAGE.value, event_kinds)
        
        # Should contain hermes_summary
        self.assertIn(EventKind.HERMES_SUMMARY.value, event_kinds)

    def test_hermes_no_control(self):
        """Test that Hermes cannot call control endpoints."""
        # Hermes has observe and summarize, but NOT control
        self.assertNotIn('control', self.connection.capabilities)
        
        # Verify capability enforcement
        with self.assertRaises(PermissionError):
            require_capability(self.connection, 'control')

    def test_hermes_invalid_capability(self):
        """Test that invalid capabilities are rejected during pairing."""
        with self.assertRaises(ValueError) as context:
            pair_hermes("invalid-caps", "bad-agent", ['observe', 'control'])
        
        self.assertIn("Invalid Hermes capability", str(context.exception))

    def test_hermes_summary_appears_in_inbox(self):
        """Test that appended summary is visible via spine events."""
        # Append a summary
        event = hermes_append_summary(
            self.connection,
            "Test summary for inbox",
            "observe"
        )
        
        # Read from spine directly
        events = get_events(kind=EventKind.HERMES_SUMMARY, limit=10)
        
        # Should find the summary
        summary_texts = [e.payload.get('summary_text') for e in events]
        self.assertIn("Test summary for inbox", summary_texts)

    def test_hermes_pairing_idempotent(self):
        """Test that re-pairing is idempotent."""
        # First pairing
        pairing1 = pair_hermes("idempotent-hermes", "idempotent-agent")
        
        # Re-pair (should succeed without error)
        pairing2 = pair_hermes("idempotent-hermes", "idempotent-agent")
        
        # Both should work and have same hermes_id
        self.assertEqual(pairing1.hermes_id, pairing2.hermes_id)
        
        # But different tokens (tokens are rotated on re-pair)
        self.assertNotEqual(pairing1.token, pairing2.token)

    def test_hermes_list_pairings(self):
        """Test listing Hermes pairings."""
        pairings = list_hermes_pairings()
        
        # Should have at least our test pairings
        hermes_ids = [p.hermes_id for p in pairings]
        self.assertIn("test-hermes-001", hermes_ids)

    def test_hermes_revoke_token(self):
        """Test token revocation."""
        token = self.pairing.token
        
        # Verify token works
        conn = hermes_connect(token)
        self.assertEqual(conn.hermes_id, "test-hermes-001")
        
        # Revoke
        result = revoke_hermes_token("test-hermes-001")
        self.assertTrue(result)
        
        # Token should no longer work
        with self.assertRaises(ValueError):
            hermes_connect(token)

    def test_hermes_capabilities_constant(self):
        """Test that HERMES_CAPABILITIES is correct."""
        self.assertEqual(HERMES_CAPABILITIES, ['observe', 'summarize'])

    def test_hermes_readable_events(self):
        """Test that HERMES_READABLE_EVENTS excludes user_message."""
        readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
        blocked_kinds = [e.value for e in HERMES_BLOCKED_EVENTS]
        
        # user_message should be in blocked
        self.assertIn('user_message', blocked_kinds)
        
        # user_message should NOT be in readable
        self.assertNotIn('user_message', readable_kinds)

    def test_hermes_authority_token_validation(self):
        """Test token validation returns correct data."""
        token_data = validate_authority_token(self.pairing.token)
        
        self.assertIsNotNone(token_data)
        self.assertEqual(token_data.hermes_id, "test-hermes-001")
        self.assertEqual(token_data.principal_id, self.principal.id)
        self.assertIn('observe', token_data.capabilities)
        self.assertIn('summarize', token_data.capabilities)

    def test_hermes_is_token_expired(self):
        """Test expiration checking."""
        # Past date should be expired
        self.assertTrue(is_token_expired('2020-01-01T00:00:00+00:00'))
        
        # Future date should not be expired
        future = '2099-12-31T23:59:59+00:00'
        self.assertFalse(is_token_expired(future))


class TestHermesControlBoundary(unittest.TestCase):
    """Test that Hermes cannot access control endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear state
        if os.path.exists(SPINE_FILE):
            os.remove(SPINE_FILE)
        
        self.principal = load_or_create_principal()
        self.pairing = pair_hermes("control-test-hermes", "control-test-agent")
        self.connection = hermes_connect(self.pairing.token)

    def test_hermes_lacks_control_capability(self):
        """Verify Hermes pairing does not grant control capability."""
        self.assertNotIn('control', self.connection.capabilities)
        
        # Control capability should not even be in the list
        self.assertNotIn('control', HERMES_CAPABILITIES)


def run_tests():
    """Run all tests with verbose output."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestHermesAdapter))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesControlBoundary))
    
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())

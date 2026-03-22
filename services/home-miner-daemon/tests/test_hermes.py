#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the capability boundaries for Hermes AI agent connections:
- Token validation and expiration
- Observe capability for status reads
- Summarize capability for summary appends
- Event filtering (no user_message)
- Control command rejection
"""

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Set up test state directory
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR

# Add daemon to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes import (
    HermesConnection,
    HERMES_CAPABILITIES,
    HERMES_READABLE_EVENTS,
    connect,
    pair_hermes,
    get_authority_token,
    generate_token,
    read_status,
    append_summary,
    get_filtered_events,
    _validate_authority_token,
)
from spine import append_event, get_events, EventKind
from store import load_or_create_principal, load_pairings, save_pairings


class TestHermesCapabilities(unittest.TestCase):
    """Test Hermes capability definitions."""

    def test_hermes_capabilities_defined(self):
        """Hermes has observe and summarize capabilities."""
        self.assertEqual(HERMES_CAPABILITIES, ['observe', 'summarize'])
        self.assertNotIn('control', HERMES_CAPABILITIES)

    def test_hermes_readable_events(self):
        """Hermes can read summary, alert, and receipt events."""
        readable = [e.value for e in HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable)
        self.assertIn('miner_alert', readable)
        self.assertIn('control_receipt', readable)
        self.assertNotIn('user_message', readable)


class TestTokenValidation(unittest.TestCase):
    """Test authority token validation."""

    def setUp(self):
        """Create a valid token for testing."""
        self.principal = load_or_create_principal()
        self.valid_token = generate_token("hermes-test", self.principal.id, days_valid=30)

    def test_valid_token_parses(self):
        """Valid token is accepted and claims extracted."""
        claims = _validate_authority_token(self.valid_token)
        self.assertEqual(claims['hermes_id'], 'hermes-test')
        self.assertEqual(claims['principal_id'], self.principal.id)
        self.assertIn('observe', claims['capabilities'])
        self.assertIn('summarize', claims['capabilities'])

    def test_empty_token_rejected(self):
        """Empty token raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_authority_token("")
        self.assertIn('Empty', str(ctx.exception))

    def test_malformed_token_rejected(self):
        """Malformed token raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_authority_token("invalid|token")
        self.assertIn('Malformed', str(ctx.exception))

    def test_expired_token_rejected(self):
        """Expired token raises ValueError."""
        expired_token = generate_token("hermes-test", self.principal.id, days_valid=-1)
        with self.assertRaises(ValueError) as ctx:
            _validate_authority_token(expired_token)
        self.assertIn('expired', str(ctx.exception).lower())


class TestHermesConnection(unittest.TestCase):
    """Test Hermes connection lifecycle."""

    def setUp(self):
        """Set up test state directory and principal."""
        self.principal = load_or_create_principal()
        self.token = generate_token("hermes-001", self.principal.id)

    def test_connect_with_valid_token(self):
        """Connect succeeds with valid token."""
        conn = connect(self.token)
        self.assertIsInstance(conn, HermesConnection)
        self.assertEqual(conn.hermes_id, 'hermes-001')
        self.assertEqual(conn.principal_id, self.principal.id)
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)
        self.assertIsNotNone(conn.connected_at)

    def test_connection_to_dict(self):
        """Connection serializes correctly."""
        conn = connect(self.token)
        d = conn.to_dict()
        self.assertEqual(d['hermes_id'], 'hermes-001')
        self.assertEqual(d['capabilities_label'], 'Hermes Adapter (observe + summarize)')

    def test_connect_with_invalid_token(self):
        """Connect fails with invalid token."""
        with self.assertRaises(ValueError):
            connect("invalid-token")


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing flow."""

    def setUp(self):
        """Set up fresh principal."""
        self.principal = load_or_create_principal()

    def test_pair_hermes_creates_record(self):
        """Pairing creates a Hermes pairing record."""
        conn = pair_hermes("hermes-pair-test", "test-agent")
        
        self.assertEqual(conn.hermes_id, 'hermes-pair-test')
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)
        self.assertNotIn('control', conn.capabilities)

    def test_pair_hermes_idempotent(self):
        """Re-pairing returns existing connection."""
        conn1 = pair_hermes("hermes-idempotent", "test-agent")
        conn2 = pair_hermes("hermes-idempotent", "test-agent")
        
        self.assertEqual(conn1.hermes_id, conn2.hermes_id)
        self.assertEqual(conn1.principal_id, conn2.principal_id)

    def test_get_authority_token(self):
        """Can retrieve stored authority token."""
        pair_hermes("hermes-token-test", "test-agent")
        token = get_authority_token("hermes-token-test")
        
        self.assertIsNotNone(token)
        self.assertIn("hermes-token-test", token)


class TestReadStatus(unittest.TestCase):
    """Test Hermes status read through adapter."""

    def setUp(self):
        """Set up paired Hermes connection."""
        self.principal = load_or_create_principal()
        self.conn = pair_hermes("hermes-status-test", "test-agent")

    def test_read_status_with_observe(self):
        """Observe capability allows status read."""
        # Use stored token
        token = get_authority_token(self.conn.hermes_id)
        conn = connect(token)
        
        status = read_status(conn)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)
        self.assertIn('temperature', status)
        self.assertIn('uptime_seconds', status)
        self.assertIn('freshness', status)

    def test_read_status_without_observe(self):
        """Connection without observe raises PermissionError."""
        # Create token without observe capability
        # Generate valid token, then create a token with only summarize
        from datetime import timedelta
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        bad_token = f"hermes-no-observe|{self.principal.id}|summarize|{expires.isoformat()}"
        
        conn = connect(bad_token)
        
        with self.assertRaises(PermissionError) as ctx:
            read_status(conn)
        self.assertIn('observe', str(ctx.exception))


class TestAppendSummary(unittest.TestCase):
    """Test Hermes summary append through adapter."""

    def setUp(self):
        """Set up paired Hermes connection."""
        self.principal = load_or_create_principal()
        self.conn = pair_hermes("hermes-summary-test", "test-agent")

    def test_append_summary_with_summarize(self):
        """Summarize capability allows summary append."""
        token = get_authority_token(self.conn.hermes_id)
        conn = connect(token)
        
        result = append_summary(conn, "Test summary text", ["observe"])
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
        self.assertIn('created_at', result)

    def test_summary_appears_in_spine(self):
        """Appended summary appears in event spine."""
        token = get_authority_token(self.conn.hermes_id)
        conn = connect(token)
        
        result = append_summary(conn, "Spine verification test")
        
        # Check spine
        events = get_events(kind=EventKind.HERMES_SUMMARY, limit=50)
        summary_events = [e for e in events if e.id == result['event_id']]
        
        self.assertEqual(len(summary_events), 1)
        self.assertEqual(summary_events[0].payload['summary_text'], "Spine verification test")
        self.assertEqual(summary_events[0].principal_id, conn.principal_id)

    def test_append_summary_without_summarize(self):
        """Connection without summarize raises PermissionError."""
        # Create token with only observe capability
        from datetime import timedelta
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        bad_token = f"hermes-no-summarize|{self.principal.id}|observe|{expires.isoformat()}"
        
        conn = connect(bad_token)
        
        with self.assertRaises(PermissionError) as ctx:
            append_summary(conn, "Should fail")
        self.assertIn('summarize', str(ctx.exception))


class TestEventFiltering(unittest.TestCase):
    """Test Hermes event filtering."""

    def setUp(self):
        """Set up with multiple event types."""
        self.principal = load_or_create_principal()
        self.conn = pair_hermes("hermes-filter-test", "test-agent")
        
        # Append various event types
        append_event(EventKind.HERMES_SUMMARY, self.principal.id, {"text": "summary"})
        append_event(EventKind.MINER_ALERT, self.principal.id, {"alert": "test"})
        append_event(EventKind.CONTROL_RECEIPT, self.principal.id, {"cmd": "start"})
        append_event(EventKind.USER_MESSAGE, self.principal.id, {"msg": "private"})

    def test_hermes_filtered_events_excludes_user_message(self):
        """Hermes cannot read user_message events."""
        token = get_authority_token(self.conn.hermes_id)
        conn = connect(token)
        
        events = get_filtered_events(conn, limit=100)
        event_kinds = [e['kind'] for e in events]
        
        self.assertIn('hermes_summary', event_kinds)
        self.assertIn('miner_alert', event_kinds)
        self.assertIn('control_receipt', event_kinds)
        self.assertNotIn('user_message', event_kinds)


class TestEventFilteringRequiresObserve(unittest.TestCase):
    """Test that get_filtered_events enforces observe capability."""

    def setUp(self):
        self.principal = load_or_create_principal()

    def test_filtered_events_without_observe_raises(self):
        """Connection with only summarize cannot read events."""
        from datetime import timedelta
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        token = f"hermes-summarize-only|{self.principal.id}|summarize|{expires.isoformat()}"
        conn = connect(token)

        with self.assertRaises(PermissionError) as ctx:
            get_filtered_events(conn)
        self.assertIn('observe', str(ctx.exception))


class TestHermesIdValidation(unittest.TestCase):
    """Test hermes_id input validation."""

    def test_pipe_in_hermes_id_rejected(self):
        """hermes_id containing pipe delimiter is rejected."""
        with self.assertRaises(ValueError) as ctx:
            pair_hermes("bad|id", "test-agent")
        self.assertIn('|', str(ctx.exception))


class TestExpiredRepair(unittest.TestCase):
    """Test that re-pairing regenerates expired tokens."""

    def setUp(self):
        self.principal = load_or_create_principal()

    def test_repairing_expired_regenerates_token(self):
        """Re-pairing with expired token generates a new valid token."""
        conn = pair_hermes("hermes-expire-test", "test-agent")

        # Manually expire the stored token
        pairings = load_pairings()
        for pid, p in pairings.items():
            if p.get('hermes_id') == 'hermes-expire-test':
                p['token_expires_at'] = '2020-01-01T00:00:00+00:00'
                p['authority_token'] = p['authority_token'].rsplit('|', 1)[0] + '|2020-01-01T00:00:00+00:00'
                pairings[pid] = p
                break
        save_pairings(pairings)

        # Re-pair should regenerate
        pair_hermes("hermes-expire-test", "test-agent")

        # Token should now be valid
        token = get_authority_token("hermes-expire-test")
        new_conn = connect(token)
        self.assertEqual(new_conn.hermes_id, 'hermes-expire-test')


class TestNoControlCapability(unittest.TestCase):
    """Test that Hermes cannot have control capability."""

    def test_control_not_in_hermes_capabilities(self):
        """Control is not a Hermes capability."""
        self.assertNotIn('control', HERMES_CAPABILITIES)

    def test_cannot_generate_control_token(self):
        """Cannot generate token with control capability."""
        token = generate_token("hermes-no-control", "dummy-principal")
        claims = _validate_authority_token(token)

        self.assertNotIn('control', claims['capabilities'])


class TestObservability(unittest.TestCase):
    """Test observability integration."""

    def setUp(self):
        """Set up test principal."""
        self.principal = load_or_create_principal()
        self.conn = pair_hermes("hermes-obs-test", "test-agent")

    def test_hermes_summary_event_format(self):
        """Hermes summary events have correct format."""
        token = get_authority_token(self.conn.hermes_id)
        conn = connect(token)
        
        result = append_summary(conn, "Observability test")
        
        events = get_events(kind=EventKind.HERMES_SUMMARY, limit=10)
        event = next((e for e in events if e.id == result['event_id']), None)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.kind, 'hermes_summary')
        self.assertIn('summary_text', event.payload)
        self.assertIn('authority_scope', event.payload)
        self.assertIn('generated_at', event.payload)
        self.assertIn('hermes_id', event.payload)


if __name__ == '__main__':
    unittest.main()

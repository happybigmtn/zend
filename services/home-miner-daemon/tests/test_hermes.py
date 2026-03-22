#!/usr/bin/env python3
"""
Tests for Hermes adapter boundary enforcement.

Tests the adapter's capability checking, event filtering, and 
authority token validation.
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import TestCase, main

# Setup test environment
test_dir = tempfile.mkdtemp()
os.environ["ZEND_STATE_DIR"] = test_dir

# Add service to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hermes
from spine import EventKind, append_event, get_events


class TestHermesAdapter(TestCase):
    """Test Hermes adapter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing state
        self.test_dir = tempfile.mkdtemp()
        os.environ["ZEND_STATE_DIR"] = self.test_dir
        
        # Import after setting env to ensure correct state dir
        import importlib
        importlib.reload(hermes)
        importlib.reload(sys.modules['spine'])
        
        # Create test principal
        from store import load_or_create_principal
        self.principal = load_or_create_principal()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_token(self, hermes_id: str, capabilities: list, 
                      expires_delta: timedelta = timedelta(hours=1)) -> str:
        """Helper to create authority tokens."""
        # Create a timezone-aware datetime
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(now.isoformat()) + expires_delta
        
        token = {
            'hermes_id': hermes_id,
            'principal_id': self.principal.id,
            'capabilities': capabilities,
            'token_expires_at': expires.isoformat(),
            'token_id': 'test-token-001'
        }
        return json.dumps(token)

    def test_hermes_connect_valid(self):
        """Connect with valid token succeeds."""
        # Pair first
        pairing = hermes.pair_hermes('hermes-001', 'test-hermes')
        
        # Generate token
        token = hermes.generate_authority_token('hermes-001')
        
        # Connect
        conn = hermes.connect(token)
        
        self.assertEqual(conn.hermes_id, 'hermes-001')
        self.assertEqual(conn.principal_id, self.principal.id)
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)

    def test_hermes_connect_expired(self):
        """Connect with expired token fails."""
        # First pair the Hermes
        hermes.pair_hermes('hermes-001', 'test-hermes')
        
        # Create expired token
        token = self._create_token(
            'hermes-001', 
            ['observe', 'summarize'],
            expires_delta=timedelta(hours=-1)  # Expired 1 hour ago
        )
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        
        self.assertIn('EXPIRED', str(ctx.exception))

    def test_hermes_connect_invalid_json(self):
        """Connect with invalid JSON fails."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect('not valid json')
        
        self.assertIn('INVALID_TOKEN', str(ctx.exception))

    def test_hermes_connect_missing_fields(self):
        """Connect with missing required fields fails."""
        # Missing hermes_id
        token = json.dumps({
            'principal_id': self.principal.id,
            'capabilities': ['observe'],
            'token_expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        })
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        
        self.assertIn('hermes_id', str(ctx.exception))

    def test_hermes_read_status(self):
        """Observe capability reads status."""
        # Pair and connect
        hermes.pair_hermes('hermes-001', 'test-hermes')
        token = hermes.generate_authority_token('hermes-001')
        conn = hermes.connect(token)
        
        # Read status
        status = hermes.read_status(conn)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)

    def test_hermes_read_status_no_observe(self):
        """Read without observe capability fails."""
        # Create token without observe
        token = self._create_token('hermes-002', ['summarize'])
        
        # Pair first
        hermes.pair_hermes('hermes-002', 'test-hermes')
        
        conn = hermes.connect(token)
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(conn)
        
        self.assertIn('observe', str(ctx.exception))

    def test_hermes_append_summary(self):
        """Summarize capability appends to spine."""
        # Pair and connect
        hermes.pair_hermes('hermes-001', 'test-hermes')
        token = hermes.generate_authority_token('hermes-001')
        conn = hermes.connect(token)
        
        # Append summary
        result = hermes.append_summary(
            conn, 
            "Miner running normally at 50kH/s",
            "observe"
        )
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)

    def test_hermes_append_summary_no_capability(self):
        """Append without summarize capability fails."""
        # Create token without summarize
        token = self._create_token('hermes-002', ['observe'])
        
        # Pair first
        hermes.pair_hermes('hermes-002', 'test-hermes')
        
        conn = hermes.connect(token)
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(conn, "Test summary", "observe")
        
        self.assertIn('summarize', str(ctx.exception))

    def test_hermes_no_control(self):
        """Hermes cannot request control capability."""
        # Try to pair with control capability
        with self.assertRaises(ValueError) as ctx:
            hermes.pair_hermes('hermes-control', 'test', ['observe', 'summarize', 'control'])
        
        self.assertIn('control', str(ctx.exception))

    def test_hermes_event_filter(self):
        """User_message events are filtered out."""
        # Pair and connect
        hermes.pair_hermes('hermes-001', 'test-hermes')
        token = hermes.generate_authority_token('hermes-001')
        conn = hermes.connect(token)
        
        # Append some events
        append_event(EventKind.HERMES_SUMMARY, self.principal.id, {
            'summary_text': 'Test summary'
        })
        append_event(EventKind.MINER_ALERT, self.principal.id, {
            'alert_type': 'temperature',
            'message': 'High temp'
        })
        append_event(EventKind.USER_MESSAGE, self.principal.id, {
            'from': 'alice',
            'message': 'Secret message'
        })
        
        # Get filtered events
        events = hermes.get_filtered_events(conn, limit=10)
        
        # Should not contain user_message
        kinds = [e['kind'] for e in events]
        self.assertNotIn('user_message', kinds)
        
        # Should contain hermes_summary and miner_alert
        self.assertIn('hermes_summary', kinds)
        self.assertIn('miner_alert', kinds)

    def test_hermes_summary_appears_in_inbox(self):
        """Appended summary visible in filtered events."""
        # Pair and connect
        hermes.pair_hermes('hermes-001', 'test-hermes')
        token = hermes.generate_authority_token('hermes-001')
        conn = hermes.connect(token)
        
        # Append summary
        hermes.append_summary(
            conn,
            "Miner efficiency at 95%",
            "observe"
        )
        
        # Get events
        events = hermes.get_filtered_events(conn, limit=10)
        
        # Find the summary
        summaries = [e for e in events if e['kind'] == 'hermes_summary']
        self.assertTrue(len(summaries) > 0)
        
        # Check payload
        summary_texts = [s['payload']['summary_text'] for s in summaries]
        self.assertIn("Miner efficiency at 95%", summary_texts)

    def test_hermes_pairing_idempotent(self):
        """Hermes pairing is idempotent."""
        # Pair twice with same ID
        p1 = hermes.pair_hermes('hermes-001', 'test-hermes')
        p2 = hermes.pair_hermes('hermes-001', 'test-hermes')
        
        # Should return same pairing
        self.assertEqual(p1['hermes_id'], p2['hermes_id'])
        self.assertEqual(p1['paired_at'], p2['paired_at'])

    def test_hermes_invalid_capability(self):
        """Requesting invalid capability rejected."""
        # Try to create token with invalid capability
        token = json.dumps({
            'hermes_id': 'hermes-new',
            'principal_id': self.principal.id,
            'capabilities': ['observe', 'hack'],
            'token_expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        })
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.connect(token)
        
        self.assertIn('hack', str(ctx.exception))

    def test_hermes_verify_connection(self):
        """verify_connection checks capabilities correctly."""
        hermes.pair_hermes('hermes-001', 'test-hermes')
        token = hermes.generate_authority_token('hermes-001')
        conn = hermes.connect(token)
        
        # Should have observe and summarize
        self.assertTrue(hermes.verify_connection(conn, 'observe'))
        self.assertTrue(hermes.verify_connection(conn, 'summarize'))
        self.assertFalse(hermes.verify_connection(conn, 'control'))

    def test_hermes_list_pairings(self):
        """List all Hermes pairings."""
        hermes.pair_hermes('hermes-001', 'test-1')
        hermes.pair_hermes('hermes-002', 'test-2')
        
        pairings = hermes.get_hermes_pairings()
        
        self.assertEqual(len(pairings), 2)
        ids = [p['hermes_id'] for p in pairings]
        self.assertIn('hermes-001', ids)
        self.assertIn('hermes-002', ids)


class TestHermesEndpoints(TestCase):
    """Test Hermes HTTP endpoints via daemon."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        os.environ["ZEND_STATE_DIR"] = self.test_dir
        
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_hermes_capabilities_constant(self):
        """HERMES_CAPABILITIES is correct."""
        self.assertEqual(hermes.HERMES_CAPABILITIES, ['observe', 'summarize'])

    def test_hermes_readable_events_constant(self):
        """HERMES_READABLE_EVENTS is correct."""
        readable = [e.value for e in hermes.HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable)
        self.assertIn('miner_alert', readable)
        self.assertIn('control_receipt', readable)
        self.assertNotIn('user_message', readable)


if __name__ == '__main__':
    main()

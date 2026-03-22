#!/usr/bin/env python3
"""
Tests for Hermes adapter boundary enforcement.

These tests verify:
1. Hermes can connect with valid authority token
2. Hermes connect fails with expired/invalid tokens
3. Hermes can read miner status (with observe capability)
4. Hermes can append summaries (with summarize capability)
5. Hermes CANNOT control the miner
6. Hermes CANNOT read user_message events
7. Invalid capabilities are rejected
8. Appended summaries appear in the event spine
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Add daemon directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set a temp state dir for isolated tests
_temp_state_dir = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = _temp_state_dir


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter module."""
    
    @classmethod
    def setUpClass(cls):
        """Initialize state for tests."""
        from store import load_or_create_principal
        from hermes import pair_hermes, generate_authority_token
        from spine import EventKind, append_event, _load_events
        
        # Create principal and Hermes pairing
        cls.principal = load_or_create_principal()
        cls.pairing = pair_hermes("test-hermes-001", "test-hermes-agent")
        cls.token = generate_authority_token(
            cls.pairing.hermes_id,
            cls.pairing.capabilities,
            cls.pairing.token_expires_at,
        )
    
    def setUp(self):
        """Reset state before each test."""
        from hermes import _get_hermes_pairings, _save_hermes_pairings, HermesConnection
        
        self.HermesConnection = HermesConnection
    
    def test_hermes_capabilities_defined(self):
        """Verify Hermes capabilities are correctly defined."""
        from hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS
        
        self.assertIn('observe', HERMES_CAPABILITIES)
        self.assertIn('summarize', HERMES_CAPABILITIES)
        self.assertEqual(len(HERMES_CAPABILITIES), 2)
        
        # Verify readable events exclude user_message
        readable_kinds = [e.value for e in HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable_kinds)
        self.assertIn('miner_alert', readable_kinds)
        self.assertIn('control_receipt', readable_kinds)
        self.assertNotIn('user_message', readable_kinds)
    
    def test_hermes_connect_valid(self):
        """Test Hermes connection with valid token succeeds."""
        from hermes import connect
        
        conn = connect(self.token)
        
        self.assertEqual(conn.hermes_id, 'test-hermes-001')
        self.assertIn('observe', conn.capabilities)
        self.assertIn('summarize', conn.capabilities)
    
    def test_hermes_connect_expired(self):
        """Test Hermes connection fails with expired token."""
        from hermes import connect
        
        # Create expired token
        expired_token = json.dumps({
            "hermes_id": "test-hermes-001",
            "principal_id": self.principal.id,
            "capabilities": ["observe", "summarize"],
            "token_expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        })
        
        with self.assertRaises(ValueError) as ctx:
            connect(expired_token)
        
        self.assertIn('expired', str(ctx.exception).lower())
    
    def test_hermes_connect_invalid_json(self):
        """Test Hermes connection fails with invalid JSON token."""
        from hermes import connect
        
        with self.assertRaises(ValueError) as ctx:
            connect("not valid json")
        
        self.assertIn('invalid', str(ctx.exception).lower())
    
    def test_hermes_connect_missing_field(self):
        """Test Hermes connection fails with missing required fields."""
        from hermes import connect
        
        # Missing token_expires_at
        incomplete_token = json.dumps({
            "hermes_id": "test-hermes-001",
            "principal_id": self.principal.id,
            "capabilities": ["observe"],
        })
        
        with self.assertRaises(ValueError) as ctx:
            connect(incomplete_token)
        
        self.assertIn('missing', str(ctx.exception).lower())
    
    def test_hermes_read_status(self):
        """Test Hermes can read miner status with observe capability."""
        from hermes import connect, read_status
        from daemon import miner
        
        conn = connect(self.token)
        status = read_status(conn)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)
    
    def test_hermes_no_observe_capability(self):
        """Test Hermes read_status fails without observe capability."""
        from hermes import HermesConnection, read_status
        
        conn = HermesConnection(
            hermes_id="limited-hermes",
            principal_id=self.principal.id,
            capabilities=["summarize"],  # No observe
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        )
        
        with self.assertRaises(PermissionError) as ctx:
            read_status(conn)
        
        self.assertIn('observe', str(ctx.exception))
    
    def test_hermes_append_summary(self):
        """Test Hermes can append summary with summarize capability."""
        from hermes import connect, append_summary
        from spine import get_events, EventKind
        
        conn = connect(self.token)
        
        event = append_summary(
            conn,
            "Test summary: miner running normally",
            "observe"
        )
        
        self.assertEqual(event.kind, EventKind.HERMES_SUMMARY.value)
        self.assertEqual(event.principal_id, conn.principal_id)
        self.assertEqual(event.payload['summary_text'], "Test summary: miner running normally")
        self.assertIn('hermes_id', event.payload)
    
    def test_hermes_no_summarize_capability(self):
        """Test Hermes append_summary fails without summarize capability."""
        from hermes import HermesConnection, append_summary
        
        conn = HermesConnection(
            hermes_id="limited-hermes",
            principal_id=self.principal.id,
            capabilities=["observe"],  # No summarize
            connected_at=datetime.now(timezone.utc).isoformat(),
            token_expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        )
        
        with self.assertRaises(PermissionError) as ctx:
            append_summary(conn, "should fail", "observe")
        
        self.assertIn('summarize', str(ctx.exception))
    
    def test_hermes_invalid_capability_rejected(self):
        """Test Hermes cannot request control capability."""
        from hermes import connect
        
        # Try to connect with control capability (not allowed for Hermes)
        bad_token = json.dumps({
            "hermes_id": "test-hermes-001",
            "principal_id": self.principal.id,
            "capabilities": ["observe", "summarize", "control"],  # control not allowed
            "token_expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        
        with self.assertRaises(ValueError) as ctx:
            connect(bad_token)
        
        self.assertIn('control', str(ctx.exception))
        self.assertIn('not allowed', str(ctx.exception).lower())
    
    def test_hermes_event_filter(self):
        """Test Hermes event filtering excludes user_message."""
        from hermes import connect, get_filtered_events
        from spine import append_event, EventKind
        
        conn = connect(self.token)
        
        # Append different event types
        append_event(
            EventKind.HERMES_SUMMARY,
            conn.principal_id,
            {"summary_text": "hermes summary test", "authority_scope": "observe"}
        )
        append_event(
            EventKind.MINER_ALERT,
            conn.principal_id,
            {"alert_type": "health_warning", "message": "test alert"}
        )
        append_event(
            EventKind.USER_MESSAGE,
            conn.principal_id,
            {"thread_id": "thread-1", "sender_id": "alice", "encrypted_content": "secret"}
        )
        
        # Get filtered events
        events = get_filtered_events(conn, limit=50)
        
        kinds = [e['kind'] for e in events]
        
        self.assertIn('hermes_summary', kinds)
        self.assertIn('miner_alert', kinds)
        self.assertNotIn('user_message', kinds)
    
    def test_hermes_summary_appears_in_spine(self):
        """Test appended Hermes summary is visible in event spine."""
        from hermes import connect, append_summary
        from spine import get_events, EventKind
        
        conn = connect(self.token)
        
        # Append summary
        summary_text = "Miner efficiency report: 98%"
        event = append_summary(conn, summary_text, "observe")
        
        # Verify it appears in spine
        events = get_events(kind=EventKind.HERMES_SUMMARY, limit=100)
        
        summary_ids = [e.id for e in events]
        self.assertIn(event.id, summary_ids)
        
        # Verify payload
        matching = [e for e in events if e.id == event.id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].payload['summary_text'], summary_text)
    
    def test_hermes_pairing_idempotent(self):
        """Test Hermes pairing is idempotent."""
        from hermes import pair_hermes
        
        # Pair same hermes_id twice
        p1 = pair_hermes("test-hermes-002", "test-agent")
        time.sleep(0.01)  # Ensure different timestamp
        p2 = pair_hermes("test-hermes-002", "test-agent")
        
        # Same ID, updated timestamp
        self.assertEqual(p1.hermes_id, p2.hermes_id)
        self.assertGreaterEqual(p2.paired_at, p1.paired_at)
    
    def test_hermes_get_filtered_events_limit(self):
        """Test Hermes event filtering respects limit."""
        from hermes import connect, get_filtered_events
        from spine import append_event, EventKind
        
        conn = connect(self.token)
        
        # Append multiple events
        for i in range(10):
            append_event(
                EventKind.HERMES_SUMMARY,
                conn.principal_id,
                {"summary_text": f"summary {i}", "authority_scope": "observe"}
            )
        
        # Get limited events
        events = get_filtered_events(conn, limit=5)
        self.assertLessEqual(len(events), 5)


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing functionality."""
    
    def test_pair_hermes_creates_record(self):
        """Test pair_hermes creates a pairing record."""
        from hermes import pair_hermes, get_hermes_pairing
        
        hermes_id = f"test-pairing-{int(time.time() * 1000)}"
        pairing = pair_hermes(hermes_id, "test-device")
        
        self.assertEqual(pairing.hermes_id, hermes_id)
        self.assertIn('observe', pairing.capabilities)
        self.assertIn('summarize', pairing.capabilities)
        
        # Verify retrieval
        retrieved = get_hermes_pairing(hermes_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hermes_id, hermes_id)
    
    def test_pair_hermes_custom_capabilities(self):
        """Test pairing with custom capability set."""
        from hermes import pair_hermes, get_hermes_pairing
        
        hermes_id = f"test-custom-{int(time.time() * 1000)}"
        pairing = pair_hermes(hermes_id, "test-device", capabilities=['observe'])
        
        self.assertEqual(pairing.capabilities, ['observe'])
    
    def test_pair_hermes_invalid_capability(self):
        """Test pairing with invalid capability fails."""
        from hermes import pair_hermes
        
        with self.assertRaises(ValueError) as ctx:
            pair_hermes("test-invalid", "test-device", capabilities=['observe', 'control'])
        
        self.assertIn('control', str(ctx.exception))
    
    def test_generate_authority_token(self):
        """Test authority token generation."""
        from hermes import generate_authority_token, connect
        from datetime import timedelta
        
        token = generate_authority_token(
            "test-hermes",
            ["observe"],
            (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        )
        
        # Parse and verify
        data = json.loads(token)
        self.assertEqual(data['hermes_id'], "test-hermes")
        self.assertEqual(data['capabilities'], ["observe"])
        self.assertIn('principal_id', data)
        self.assertIn('issued_at', data)
        
        # Verify it can be used to connect
        conn = connect(token)
        self.assertEqual(conn.hermes_id, "test-hermes")


class TestHermesConnection(unittest.TestCase):
    """Test HermesConnection dataclass."""
    
    def test_connection_creation(self):
        """Test HermesConnection can be created."""
        from hermes import HermesConnection
        
        conn = HermesConnection(
            hermes_id="h1",
            principal_id="p1",
            capabilities=["observe"],
            connected_at="2026-01-01T00:00:00Z",
            token_expires_at="2027-01-01T00:00:00Z",
        )
        
        self.assertEqual(conn.hermes_id, "h1")
        self.assertEqual(conn.capabilities, ["observe"])


if __name__ == '__main__':
    unittest.main(verbosity=2)

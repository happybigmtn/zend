#!/usr/bin/env python3
"""
Tests for Hermes adapter boundary enforcement.

These tests verify that:
1. Hermes can connect with valid authority token
2. Hermes can read miner status (observe capability)
3. Hermes can append summaries to event spine (summarize capability)
4. Hermes CANNOT issue control commands (403)
5. Hermes CANNOT read user_message events (filtered)
6. Invalid/expired tokens are rejected
7. Hermes summaries appear in the event spine
"""

import base64
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer
from unittest.mock import MagicMock, patch

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hermes
from hermes import (
    HermesConnection,
    HermesUnauthorizedError,
    HermesTokenExpiredError,
    HermesInvalidTokenError,
    connect,
    pair_hermes,
    read_status,
    append_summary,
    get_filtered_events,
    HERMES_CAPABILITIES,
    HERMES_READABLE_EVENTS,
    is_hermes_auth_header,
    extract_hermes_id,
)
from spine import EventKind, get_events, _load_events


class TestHermesConstants(unittest.TestCase):
    """Test that Hermes constants are correctly defined."""
    
    def test_hermes_capabilities(self):
        """Hermes should only have observe and summarize."""
        self.assertEqual(sorted(HERMES_CAPABILITIES), ['observe', 'summarize'])
        self.assertNotIn('control', HERMES_CAPABILITIES)
    
    def test_hermes_readable_events(self):
        """Hermes should be able to read summary, alert, and receipt events."""
        readable = [e.value for e in HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable)
        self.assertIn('miner_alert', readable)
        self.assertIn('control_receipt', readable)
        # user_message should NOT be in readable events
        self.assertNotIn('user_message', readable)


class TestHermesAuthHeader(unittest.TestCase):
    """Test Hermes authorization header parsing."""
    
    def test_is_hermes_auth_valid(self):
        """Valid Hermes auth header should be detected."""
        self.assertTrue(is_hermes_auth_header('Hermes hermes-001'))
    
    def test_is_hermes_auth_invalid(self):
        """Non-Hermes auth should return False."""
        self.assertFalse(is_hermes_auth_header('Bearer token'))
        self.assertFalse(is_hermes_auth_header('Basic creds'))
        self.assertFalse(is_hermes_auth_header(''))
        self.assertFalse(is_hermes_auth_header(None))
    
    def test_extract_hermes_id(self):
        """Should extract hermes_id from auth header."""
        self.assertEqual(extract_hermes_id('Hermes hermes-001'), 'hermes-001')
        self.assertEqual(extract_hermes_id('Hermes agent-42'), 'agent-42')
    
    def test_extract_hermes_id_invalid(self):
        """Should return None for non-Hermes auth."""
        self.assertIsNone(extract_hermes_id('Bearer token'))
        self.assertIsNone(extract_hermes_id(''))


class TestHermesConnect(unittest.TestCase):
    """Test Hermes connection establishment."""
    
    def setUp(self):
        """Set up test fixtures."""
        import uuid
        self.state_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.state_dir
        # Use unique hermes_id to avoid state collisions
        self.hermes_id = f'hermes-test-{uuid.uuid4().hex[:8]}'
    
    def tearDown(self):
        """Clean up test fixtures."""
        if 'ZEND_STATE_DIR' in os.environ:
            del os.environ['ZEND_STATE_DIR']
        import shutil
        shutil.rmtree(self.state_dir, ignore_errors=True)
    
    def _make_token(self, hermes_id=None, principal_id='principal-001',
                    capabilities=None, expires_delta=timedelta(hours=1)):
        """Create a valid authority token."""
        if hermes_id is None:
            hermes_id = self.hermes_id
        if capabilities is None:
            capabilities = HERMES_CAPABILITIES
        token_data = {
            'hermes_id': hermes_id,
            'principal_id': principal_id,
            'capabilities': capabilities,
            'expires_at': (datetime.now(timezone.utc) + expires_delta).isoformat(),
        }
        return base64.b64encode(json.dumps(token_data).encode()).decode()
    
    def test_connect_valid_token(self):
        """Connecting with valid token should succeed."""
        token = self._make_token()
        connection = connect(token)
        
        self.assertIsInstance(connection, HermesConnection)
        self.assertEqual(connection.hermes_id, self.hermes_id)
        self.assertEqual(connection.principal_id, 'principal-001')
        self.assertEqual(sorted(connection.capabilities), ['observe', 'summarize'])
    
    def test_connect_expired_token(self):
        """Connecting with expired token should fail."""
        token = self._make_token(expires_delta=timedelta(hours=-1))
        
        with self.assertRaises(HermesTokenExpiredError) as ctx:
            connect(token)
        self.assertIn('expired', str(ctx.exception).lower())
    
    def test_connect_missing_field(self):
        """Token missing required field should fail."""
        token_data = {
            'hermes_id': self.hermes_id,
            'principal_id': 'principal-001',
            # Missing 'capabilities' and 'expires_at'
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        with self.assertRaises(HermesInvalidTokenError) as ctx:
            connect(token)
        self.assertIn('missing', str(ctx.exception).lower())
    
    def test_connect_with_control_capability_rejected(self):
        """Hermes should never be allowed control capability."""
        token = self._make_token(capabilities=['observe', 'summarize', 'control'])
        
        with self.assertRaises(HermesUnauthorizedError) as ctx:
            connect(token)
        self.assertIn('control', str(ctx.exception).lower())
    
    def test_connect_malformed_token(self):
        """Malformed token should fail."""
        with self.assertRaises(HermesInvalidTokenError):
            connect('not-valid-json')
        
        with self.assertRaises(HermesInvalidTokenError):
            connect('aW52YWxpZC1qc29u')  # "invalid-json" b64


class TestHermesReadStatus(unittest.TestCase):
    """Test Hermes status reading."""
    
    def test_read_status_requires_observe(self):
        """Reading status should require observe capability."""
        connection = HermesConnection(
            hermes_id='hermes-test-status',
            principal_id='principal-001',
            capabilities=[],  # No observe
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
        
        with self.assertRaises(HermesUnauthorizedError) as ctx:
            read_status(connection)
        self.assertIn('observe', str(ctx.exception).lower())
    
    def test_read_status_with_observe(self):
        """Reading status with observe capability should work."""
        connection = HermesConnection(
            hermes_id='hermes-test-status',
            principal_id='principal-001',
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
        
        # Mock the daemon.miner module
        with patch('daemon.miner') as mock_miner:
            mock_miner.get_snapshot.return_value = {
                'status': 'running',
                'mode': 'balanced',
                'hashrate_hs': 50000,
            }
            
            status = read_status(connection)
            
            self.assertEqual(status['status'], 'running')
            self.assertEqual(status['mode'], 'balanced')


class TestHermesAppendSummary(unittest.TestCase):
    """Test Hermes summary appending."""
    
    def setUp(self):
        """Set up test fixtures."""
        import uuid
        self.state_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.state_dir
        # Use unique hermes_id to avoid state collisions
        self.hermes_id = f'hermes-test-summary-{uuid.uuid4().hex[:8]}'
    
    def tearDown(self):
        """Clean up test fixtures."""
        if 'ZEND_STATE_DIR' in os.environ:
            del os.environ['ZEND_STATE_DIR']
        import shutil
        shutil.rmtree(self.state_dir, ignore_errors=True)
    
    def test_append_summary_requires_summarize(self):
        """Appending summary should require summarize capability."""
        connection = HermesConnection(
            hermes_id=self.hermes_id,
            principal_id='principal-001',
            capabilities=['observe'],  # No summarize
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
        
        with self.assertRaises(HermesUnauthorizedError) as ctx:
            append_summary(connection, "Test summary", "observe")
        self.assertIn('summarize', str(ctx.exception).lower())
    
    def test_append_summary_creates_event(self):
        """Appending summary should create a hermes_summary event."""
        connection = HermesConnection(
            hermes_id=self.hermes_id,
            principal_id='principal-001',
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
        
        event = append_summary(connection, "Miner running normally", "observe")
        
        self.assertEqual(event.kind, EventKind.HERMES_SUMMARY.value)
        self.assertEqual(event.principal_id, 'principal-001')
        self.assertEqual(event.payload['summary_text'], "Miner running normally")
        self.assertIn('generated_at', event.payload)
    
    def test_summary_appears_in_spine(self):
        """Appended summary should be visible in the event spine."""
        connection = HermesConnection(
            hermes_id=self.hermes_id,
            principal_id='principal-001',
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
        
        # Generate unique summary text to avoid collision with other tests
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        summary_text = f"Test summary for spine verification {unique_id}"
        append_summary(connection, summary_text, "observe")
        
        # Read from spine
        events = get_events(kind=EventKind.HERMES_SUMMARY, limit=10)
        hermes_events = [e for e in events if e.payload.get('summary_text') == summary_text]
        
        self.assertEqual(len(hermes_events), 1)
        self.assertEqual(hermes_events[0].payload['summary_text'], summary_text)


class TestHermesEventFiltering(unittest.TestCase):
    """Test Hermes event filtering."""
    
    def setUp(self):
        """Set up test fixtures."""
        import uuid
        self.state_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.state_dir
        
        # Use unique hermes_id to avoid state collisions
        self.hermes_id = f'hermes-test-filter-{uuid.uuid4().hex[:8]}'
        
        # Create connection
        self.connection = HermesConnection(
            hermes_id=self.hermes_id,
            principal_id='principal-001',
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if 'ZEND_STATE_DIR' in os.environ:
            del os.environ['ZEND_STATE_DIR']
        import shutil
        shutil.rmtree(self.state_dir, ignore_errors=True)
    
    def test_user_message_filtered(self):
        """user_message events should not appear in filtered events."""
        from spine import append_event
        
        # Create a user_message event (should be filtered)
        append_event(
            kind=EventKind.USER_MESSAGE,
            principal_id='principal-001',
            payload={'thread_id': 'thread-1', 'content': 'secret'}
        )
        
        # Create a hermes_summary event (should appear)
        append_event(
            kind=EventKind.HERMES_SUMMARY,
            principal_id='principal-001',
            payload={'summary_text': 'Hermes summary', 'authority_scope': ['observe']}
        )
        
        # Get filtered events
        filtered = get_filtered_events(self.connection, limit=20)
        
        # Should not contain user_message
        for event in filtered:
            self.assertNotEqual(event.kind, EventKind.USER_MESSAGE.value)
        
        # Should contain hermes_summary
        kinds = [e.kind for e in filtered]
        self.assertIn(EventKind.HERMES_SUMMARY.value, kinds)
    
    def test_miner_alert_allowed(self):
        """miner_alert events should appear in filtered events."""
        from spine import append_event
        
        append_event(
            kind=EventKind.MINER_ALERT,
            principal_id='principal-001',
            payload={'alert_type': 'health_warning', 'message': 'High temp'}
        )
        
        filtered = get_filtered_events(self.connection, limit=20)
        
        kinds = [e.kind for e in filtered]
        self.assertIn(EventKind.MINER_ALERT.value, kinds)
    
    def test_control_receipt_allowed(self):
        """control_receipt events should appear in filtered events."""
        from spine import append_event
        
        append_event(
            kind=EventKind.CONTROL_RECEIPT,
            principal_id='principal-001',
            payload={'command': 'start', 'status': 'accepted'}
        )
        
        filtered = get_filtered_events(self.connection, limit=20)
        
        kinds = [e.kind for e in filtered]
        self.assertIn(EventKind.CONTROL_RECEIPT.value, kinds)


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        import uuid
        self.state_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.state_dir
        # Use unique hermes_id to avoid state collisions
        self.hermes_id = f'hermes-test-{uuid.uuid4().hex[:8]}'
    
    def tearDown(self):
        """Clean up test fixtures."""
        if 'ZEND_STATE_DIR' in os.environ:
            del os.environ['ZEND_STATE_DIR']
        import shutil
        shutil.rmtree(self.state_dir, ignore_errors=True)
    
    def test_pair_hermes(self):
        """Pairing should create Hermes pairing with correct capabilities."""
        pairing = pair_hermes(self.hermes_id, 'my-hermes-agent')
        
        self.assertEqual(pairing.hermes_id, self.hermes_id)
        self.assertEqual(pairing.device_name, 'my-hermes-agent')
        self.assertEqual(pairing.capabilities, HERMES_CAPABILITIES)
    
    def test_pair_hermes_idempotent(self):
        """Re-pairing same hermes_id should return existing pairing."""
        pairing1 = pair_hermes(self.hermes_id, 'agent-1')
        pairing2 = pair_hermes(self.hermes_id, 'agent-2')  # Different name
        
        # Should return first pairing, not create new
        self.assertEqual(pairing1.id, pairing2.id)
        self.assertEqual(pairing2.device_name, 'agent-1')  # Original name kept


class TestHermesCapabilityBoundary(unittest.TestCase):
    """Test that Hermes capability boundaries are enforced."""
    
    def test_connection_has_capability_check(self):
        """HermesConnection should have has_capability method."""
        connection = HermesConnection(
            hermes_id='hermes-001',
            principal_id='principal-001',
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
        
        self.assertTrue(connection.has_capability('observe'))
        self.assertTrue(connection.has_capability('summarize'))
        self.assertFalse(connection.has_capability('control'))
        self.assertFalse(connection.has_capability('nonexistent'))


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""
Tests for Hermes Adapter.

These tests verify:
1. Hermes can connect with valid authority token
2. Hermes cannot connect with expired token
3. Hermes can read miner status (observe capability)
4. Hermes can append summaries (summarize capability)
5. Hermes CANNOT issue control commands (403)
6. Hermes CANNOT read user_message events (filtered)
7. Hermes with invalid capability rejected
8. Appended summary appears in inbox
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add service to path
SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

# Set up isolated state directory for tests
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ["ZEND_STATE_DIR"] = TEST_STATE_DIR

# Import hermes module directly
import hermes
import store


class TestHermesAdapter(unittest.TestCase):
    """Test cases for Hermes adapter boundary enforcement."""
    
    def setUp(self):
        """Set up each test with fresh state."""
        # Clear state files
        hermes_store = os.path.join(TEST_STATE_DIR, 'hermes-store.json')
        hermes_tokens = os.path.join(TEST_STATE_DIR, 'hermes-tokens.json')
        spine_file = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        
        for f in [hermes_store, hermes_tokens, spine_file]:
            if os.path.exists(f):
                os.remove(f)
        
        self.hermes_id = f"test-hermes-{int(time.time() * 1000)}"
        self.principal = store.load_or_create_principal()
    
    def test_hermes_capabilities_defined(self):
        """Verify Hermes capabilities are correctly defined."""
        self.assertEqual(hermes.HERMES_CAPABILITIES, ['observe', 'summarize'])
    
    def test_hermes_readable_events_defined(self):
        """Verify Hermes-readable events are correctly defined."""
        expected = ['hermes_summary', 'miner_alert', 'control_receipt']
        self.assertEqual(hermes.HERMES_READABLE_EVENTS, expected)
    
    def test_hermes_pair_valid(self):
        """Test pairing a Hermes with valid credentials."""
        pairing = hermes.pair_hermes(
            hermes_id=self.hermes_id,
            device_name="test-agent",
            principal_id=self.principal.id
        )
        
        self.assertEqual(pairing.hermes_id, self.hermes_id)
        self.assertEqual(pairing.device_name, "test-agent")
        self.assertEqual(pairing.principal_id, self.principal.id)
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertIsNotNone(pairing.token_expires_at)
    
    def test_hermes_pair_idempotent(self):
        """Test that pairing is idempotent."""
        pairing1 = hermes.pair_hermes(
            hermes_id=self.hermes_id,
            device_name="test-agent",
            principal_id=self.principal.id
        )
        
        # Pair again with same ID
        pairing2 = hermes.pair_hermes(
            hermes_id=self.hermes_id,
            device_name="test-agent-2",  # Different name
            principal_id=self.principal.id
        )
        
        # Should return same pairing
        self.assertEqual(pairing1.hermes_id, pairing2.hermes_id)
        self.assertEqual(pairing1.paired_at, pairing2.paired_at)
    
    def test_hermes_connect_valid_token(self):
        """Test connecting with valid authority token."""
        # First pair
        hermes.pair_hermes(
            hermes_id=self.hermes_id,
            device_name="test-agent",
            principal_id=self.principal.id
        )
        
        # Connect with token
        token_data = {
            'hermes_id': self.hermes_id,
            'principal_id': self.principal.id,
            'capabilities': ['observe', 'summarize'],
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        
        connection = hermes.connect(token_data)
        
        self.assertIsInstance(connection, hermes.HermesConnection)
        self.assertEqual(connection.hermes_id, self.hermes_id)
        self.assertEqual(connection.principal_id, self.principal.id)
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)
    
    def test_hermes_connect_expired_token(self):
        """Test connecting with expired token fails."""
        token_data = {
            'hermes_id': self.hermes_id,
            'principal_id': self.principal.id,
            'capabilities': ['observe', 'summarize'],
            'expires_at': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        }
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token_data)
        
        self.assertIn("EXPIRED", str(ctx.exception))
    
    def test_hermes_invalid_capability(self):
        """Test that Hermes cannot request control capability."""
        token_data = {
            'hermes_id': self.hermes_id,
            'principal_id': self.principal.id,
            'capabilities': ['observe', 'summarize', 'control'],  # Invalid!
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token_data)
        
        self.assertIn("control", str(ctx.exception))
    
    def test_hermes_reconnect(self):
        """Test reconnecting a paired Hermes."""
        # Pair Hermes
        hermes.pair_hermes(
            hermes_id=self.hermes_id,
            device_name="test-agent",
            principal_id=self.principal.id
        )
        
        # Reconnect
        connection = hermes.reconnect_with_token(self.hermes_id)
        
        self.assertEqual(connection.hermes_id, self.hermes_id)
        self.assertIn('observe', connection.capabilities)
    
    def test_hermes_read_status_requires_observe(self):
        """Test that reading status requires observe capability."""
        # Create connection without observe
        connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal.id,
            capabilities=['summarize'],  # No observe!
            connected_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(connection)
        
        self.assertIn("observe", str(ctx.exception))
    
    def test_hermes_read_status_with_observe(self):
        """Test reading status with observe capability."""
        connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal.id,
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Should not raise
        status = hermes.read_status(connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
    
    def test_hermes_append_summary_requires_summarize(self):
        """Test that appending summary requires summarize capability."""
        connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal.id,
            capabilities=['observe'],  # No summarize!
            connected_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(connection, "Test summary", "observe")
        
        self.assertIn("summarize", str(ctx.exception))
    
    def test_hermes_append_summary_appears_in_spine(self):
        """Test that appended summary appears in the event spine."""
        # Pair and connect
        hermes.pair_hermes(
            hermes_id=self.hermes_id,
            device_name="test-agent",
            principal_id=self.principal.id
        )
        
        connection = hermes.reconnect_with_token(self.hermes_id)
        
        # Append summary
        result = hermes.append_summary(
            connection,
            "Miner running normally at 50kH/s",
            "observe"
        )
        
        self.assertTrue(result.get('appended'))
        self.assertIsNotNone(result.get('event_id'))
        
        # Verify it appears in filtered events
        events = hermes.get_filtered_events(connection, limit=10)
        
        hermes_summaries = [e for e in events if e['kind'] == 'hermes_summary']
        self.assertGreater(len(hermes_summaries), 0)
        
        # Check the summary text is present
        summary_event = hermes_summaries[0]
        self.assertIn("50kH/s", summary_event['payload']['summary_text'])
    
    def test_hermes_event_filter_blocks_user_message(self):
        """Test that user_message events are filtered from Hermes view."""
        connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.principal.id,
            capabilities=['observe', 'summarize'],
            connected_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Get filtered events
        events = hermes.get_filtered_events(connection, limit=50)
        
        # Verify no user_message events
        for event in events:
            self.assertNotEqual(event['kind'], 'user_message')
    
    def test_hermes_cannot_have_control_capability(self):
        """Test that Hermes connection cannot have control capability."""
        token_data = {
            'hermes_id': self.hermes_id,
            'principal_id': self.principal.id,
            'capabilities': ['observe', 'control'],  # Hermes with control!
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token_data)
        
        self.assertIn("control", str(ctx.exception))


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestHermesAdapter)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful(), result.testsRun, len(result.failures), len(result.errors)


if __name__ == '__main__':
    success, tests_run, failures, errors = run_tests()
    sys.exit(0 if success else 1)

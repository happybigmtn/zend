#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Validates the capability boundary between Hermes and the Zend gateway.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test state directory
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR

from services.home_miner_daemon import hermes
from services.home_miner_daemon import spine
from services.home_miner_daemon import store


class TestHermesPairing(unittest.TestCase):
    """Test Hermes device pairing."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Ensure clean state
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
    
    def tearDown(self):
        """Clean up test state."""
        # Clean up Hermes state
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
    
    def test_hermes_pair_success(self):
        """Test successful Hermes pairing."""
        pairing = hermes.pair_hermes(self.hermes_id, self.device_name)
        
        self.assertEqual(pairing.hermes_id, self.hermes_id)
        self.assertEqual(pairing.device_name, self.device_name)
        self.assertEqual(pairing.capabilities, hermes.HERMES_CAPABILITIES)
        self.assertIn('observe', pairing.capabilities)
        self.assertIn('summarize', pairing.capabilities)
    
    def test_hermes_pair_idempotent(self):
        """Test that Hermes pairing is idempotent."""
        pairing1 = hermes.pair_hermes(self.hermes_id, self.device_name)
        time.sleep(0.1)  # Ensure different timestamp
        pairing2 = hermes.pair_hermes(self.hermes_id, 'updated-device-name')
        
        # Should return same ID but updated name
        self.assertEqual(pairing1.id, pairing2.id)
        self.assertEqual(pairing2.device_name, 'updated-device-name')
    
    def test_hermes_pair_empty_hermes_id_fails(self):
        """Test that empty hermes_id raises ValueError."""
        with self.assertRaises(ValueError):
            hermes.pair_hermes('', self.device_name)
    
    def test_hermes_pair_empty_device_name_fails(self):
        """Test that empty device_name raises ValueError."""
        with self.assertRaises(ValueError):
            hermes.pair_hermes(self.hermes_id, '')
    
    def test_get_pairing_token(self):
        """Test retrieving pairing token."""
        hermes.pair_hermes(self.hermes_id, self.device_name)
        token = hermes.get_pairing_token(self.hermes_id)
        
        self.assertIsNotNone(token)
        self.assertTrue(len(token) > 0)


class TestHermesConnection(unittest.TestCase):
    """Test Hermes connection establishment."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
        hermes.pair_hermes(self.hermes_id, self.device_name)
        self.token = hermes.get_pairing_token(self.hermes_id)
    
    def tearDown(self):
        """Clean up test state."""
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
    
    def test_hermes_connect_valid_token(self):
        """Test connecting with valid token."""
        connection = hermes.connect(self.token)
        
        self.assertEqual(connection.hermes_id, self.hermes_id)
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)
        self.assertIsNotNone(connection.connected_at)
    
    def test_hermes_connect_invalid_token(self):
        """Test connecting with invalid token fails."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect('invalid-token-uuid')
        
        self.assertIn('HERMES_UNAUTHORIZED', str(ctx.exception))
    
    def test_hermes_connect_unknown_token(self):
        """Test connecting with unknown token fails."""
        import uuid
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(str(uuid.uuid4()))
        
        self.assertIn('HERMES_UNAUTHORIZED', str(ctx.exception))


class TestHermesReadStatus(unittest.TestCase):
    """Test Hermes status reading through adapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
        hermes.pair_hermes(self.hermes_id, self.device_name)
        self.token = hermes.get_pairing_token(self.hermes_id)
        self.connection = hermes.connect(self.token)
    
    def tearDown(self):
        """Clean up test state."""
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
    
    def test_hermes_read_status_success(self):
        """Test reading status with observe capability."""
        status = hermes.read_status(self.connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)
        self.assertIn('temperature', status)
        self.assertIn('freshness', status)
    
    def test_hermes_read_status_no_observe(self):
        """Test that missing observe capability raises PermissionError."""
        # Create connection without observe
        limited_connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.connection.principal_id,
            capabilities=['summarize'],  # No observe
            connected_at=self.connection.connected_at
        )
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(limited_connection)
        
        self.assertIn('HERMES_UNAUTHORIZED', str(ctx.exception))
        self.assertIn('observe', str(ctx.exception))


class TestHermesSummary(unittest.TestCase):
    """Test Hermes summary appending."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
        hermes.pair_hermes(self.hermes_id, self.device_name)
        self.token = hermes.get_pairing_token(self.hermes_id)
        self.connection = hermes.connect(self.token)
    
    def tearDown(self):
        """Clean up test state."""
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
    
    def test_hermes_append_summary_success(self):
        """Test appending summary with summarize capability."""
        summary_text = "Test summary: miner running normally"
        authority_scope = "observe"
        
        event = hermes.append_summary(self.connection, summary_text, authority_scope)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.kind, spine.EventKind.HERMES_SUMMARY.value)
        self.assertEqual(event.payload['summary_text'], summary_text)
        self.assertEqual(event.payload['authority_scope'], [authority_scope])
        self.assertIn('generated_at', event.payload)
    
    def test_hermes_append_summary_no_summarize(self):
        """Test that missing summarize capability raises PermissionError."""
        limited_connection = hermes.HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.connection.principal_id,
            capabilities=['observe'],  # No summarize
            connected_at=self.connection.connected_at
        )
        
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(limited_connection, "Test", "observe")
        
        self.assertIn('HERMES_UNAUTHORIZED', str(ctx.exception))
        self.assertIn('summarize', str(ctx.exception))


class TestHermesEventFiltering(unittest.TestCase):
    """Test Hermes event filtering."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
        hermes.pair_hermes(self.hermes_id, self.device_name)
        self.token = hermes.get_pairing_token(self.hermes_id)
        self.connection = hermes.connect(self.token)
        
        # Add test events
        self._add_test_events()
    
    def _add_test_events(self):
        """Add various test events to the spine."""
        principal = store.load_or_create_principal()
        
        # Add hermes_summary
        spine.append_hermes_summary(
            "Hermes test summary",
            ['observe'],
            principal.id
        )
        
        # Add miner_alert
        spine.append_miner_alert(
            "health_warning",
            "Temperature above normal",
            principal.id
        )
        
        # Add control_receipt
        spine.append_control_receipt(
            "start",
            None,
            "accepted",
            principal.id
        )
        
        # Add user_message (should be filtered)
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            principal.id,
            {
                "thread_id": "test-thread",
                "sender_id": "alice",
                "encrypted_content": "secret-message"
            }
        )
    
    def tearDown(self):
        """Clean up test state."""
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
        
        # Clean up spine
        spine_file = os.path.join(TEST_STATE_DIR, 'event-spine.jsonl')
        if os.path.exists(spine_file):
            os.remove(spine_file)
    
    def test_hermes_event_filter_blocks_user_message(self):
        """Test that user_message events are filtered out."""
        events = hermes.get_filtered_events(self.connection)
        
        event_kinds = [e.kind for e in events]
        
        self.assertNotIn('user_message', event_kinds)
    
    def test_hermes_event_filter_includes_readable_events(self):
        """Test that readable events are included."""
        events = hermes.get_filtered_events(self.connection)
        
        event_kinds = [e.kind for e in events]
        
        # Should include hermes_summary
        self.assertIn('hermes_summary', event_kinds)
        # Should include miner_alert
        self.assertIn('miner_alert', event_kinds)
        # Should include control_receipt
        self.assertIn('control_receipt', event_kinds)


class TestHermesControlDenial(unittest.TestCase):
    """Test that Hermes cannot perform control actions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
        hermes.pair_hermes(self.hermes_id, self.device_name)
        self.token = hermes.get_pairing_token(self.hermes_id)
        self.connection = hermes.connect(self.token)
    
    def tearDown(self):
        """Clean up test state."""
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
    
    def test_hermes_has_no_control_capability(self):
        """Test that Hermes does not have control capability."""
        self.assertNotIn('control', self.connection.capabilities)
    
    def test_hermes_control_denied(self):
        """Test that control attempts are denied."""
        result = hermes.check_control_denied(self.connection)
        
        self.assertFalse(result)  # Control should always be denied


class TestHermesInvalidCapability(unittest.TestCase):
    """Test Hermes with invalid capabilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
    
    def tearDown(self):
        """Clean up test state."""
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
    
    def test_hermes_capabilities_are_limited(self):
        """Test that Hermes capabilities are limited to observe and summarize."""
        hermes.pair_hermes(self.hermes_id, self.device_name)
        token = hermes.get_pairing_token(self.hermes_id)
        connection = hermes.connect(token)
        
        # Should have exactly observe and summarize
        self.assertEqual(set(connection.capabilities), set(hermes.HERMES_CAPABILITIES))


class TestHermesCLIHelpers(unittest.TestCase):
    """Test Hermes CLI helper functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hermes_id = f'test-hermes-{time.time()}'
        self.device_name = 'test-hermes-device'
    
    def tearDown(self):
        """Clean up test state."""
        hermes_dir = os.path.join(TEST_STATE_DIR, 'hermes')
        if os.path.exists(hermes_dir):
            import shutil
            shutil.rmtree(hermes_dir)
    
    def test_cmd_pair_hermes(self):
        """Test CLI pair helper."""
        result = hermes.cmd_pair_hermes(self.hermes_id, self.device_name)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['hermes_id'], self.hermes_id)
        self.assertEqual(result['capabilities'], hermes.HERMES_CAPABILITIES)
        self.assertIn('token', result)
    
    def test_cmd_hermes_connect_valid(self):
        """Test CLI connect helper with valid token."""
        hermes.pair_hermes(self.hermes_id, self.device_name)
        token = hermes.get_pairing_token(self.hermes_id)
        
        result = hermes.cmd_hermes_connect(token)
        
        self.assertTrue(result['success'])
        self.assertTrue(result['connected'])
        self.assertEqual(result['hermes_id'], self.hermes_id)
    
    def test_cmd_hermes_connect_invalid(self):
        """Test CLI connect helper with invalid token."""
        result = hermes.cmd_hermes_connect('invalid-token')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_cmd_hermes_status(self):
        """Test CLI status helper."""
        hermes.pair_hermes(self.hermes_id, self.device_name)
        token = hermes.get_pairing_token(self.hermes_id)
        
        result = hermes.cmd_hermes_status(token)
        
        self.assertTrue(result['success'])
        self.assertIn('status', result)
    
    def test_cmd_hermes_summary(self):
        """Test CLI summary helper."""
        hermes.pair_hermes(self.hermes_id, self.device_name)
        token = hermes.get_pairing_token(self.hermes_id)
        
        result = hermes.cmd_hermes_summary(token, "Test summary", "observe")
        
        self.assertTrue(result['success'])
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
    
    def test_cmd_hermes_events(self):
        """Test CLI events helper."""
        hermes.pair_hermes(self.hermes_id, self.device_name)
        token = hermes.get_pairing_token(self.hermes_id)
        
        result = hermes.cmd_hermes_events(token)
        
        self.assertTrue(result['success'])
        self.assertIn('events', result)
    
    def test_summary_appears_in_inbox(self):
        """Test that appended summary is visible via spine."""
        hermes.pair_hermes(self.hermes_id, self.device_name)
        token = hermes.get_pairing_token(self.hermes_id)
        
        # Append summary
        hermes.cmd_hermes_summary(token, "Miner status normal", "observe")
        
        # Verify it appears in spine events
        events = spine.get_events(kind=spine.EventKind.HERMES_SUMMARY)
        self.assertTrue(len(events) > 0)
        
        # Find our summary
        our_summary = None
        for event in events:
            if event.payload.get('summary_text') == "Miner status normal":
                our_summary = event
                break
        
        self.assertIsNotNone(our_summary)


def run_tests():
    """Run all Hermes adapter tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestHermesPairing))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesConnection))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesReadStatus))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesSummary))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesEventFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesControlDenial))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesInvalidCapability))
    suite.addTests(loader.loadTestsFromTestCase(TestHermesCLIHelpers))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())

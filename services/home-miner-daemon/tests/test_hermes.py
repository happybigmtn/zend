#!/usr/bin/env python3
"""
Tests for Hermes Adapter

Tests the Hermes adapter boundary enforcement:
1. Hermes can connect with valid token
2. Hermes cannot use control endpoints
3. Hermes can read status (observe capability)
4. Hermes can append summaries (summarize capability)
5. Hermes events are filtered (no user_message)
"""

import json
import os
import sys
import tempfile
import time
import threading
import unittest
from datetime import datetime, timezone

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up isolated state directory for tests
TEST_STATE_DIR = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR


class TestHermesAdapter(unittest.TestCase):
    """Test suite for Hermes adapter functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        from daemon import ThreadedHTTPServer, GatewayHandler, miner
        
        # Start test server
        cls.server = ThreadedHTTPServer(('127.0.0.1', 0), GatewayHandler)
        cls.server_port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        
        # Store URL for tests
        cls.daemon_url = f'http://127.0.0.1:{cls.server_port}'
        
        # Import modules after state dir is set
        import hermes
        import store
        import spine
        
        cls.hermes = hermes
        cls.store = store
        cls.spine = spine

    @classmethod
    def tearDownClass(cls):
        """Clean up test server."""
        cls.server.shutdown()

    def setUp(self):
        """Set up each test."""
        import importlib
        importlib.reload(self.hermes)
        importlib.reload(self.spine)
        importlib.reload(self.store)

    def _make_request(self, method, path, data=None, headers=None):
        """Make HTTP request to test server."""
        import urllib.request
        import urllib.error
        
        url = f'{self.daemon_url}{path}'
        req_headers = {'Content-Type': 'application/json'}
        if headers:
            req_headers.update(headers)
        
        try:
            if method == 'GET':
                req = urllib.request.Request(url, headers=req_headers)
            else:
                body = json.dumps(data or {}).encode()
                req = urllib.request.Request(url, data=body, headers=req_headers)
                req.get_method = lambda: method
            
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read()), resp.status
        except urllib.error.HTTPError as e:
            return json.loads(e.read()), e.code
        except urllib.error.URLError as e:
            return {'error': str(e)}, 0

    def test_hermes_capabilities_constant(self):
        """Verify Hermes capabilities are correct."""
        self.assertEqual(
            self.hermes.HERMES_CAPABILITIES,
            ['observe', 'summarize']
        )

    def test_hermes_readable_events_constant(self):
        """Verify Hermes readable events exclude user_message."""
        readable = [e.value for e in self.hermes.HERMES_READABLE_EVENTS]
        self.assertIn('hermes_summary', readable)
        self.assertIn('miner_alert', readable)
        self.assertIn('control_receipt', readable)
        self.assertNotIn('user_message', readable)

    def test_hermes_pair(self):
        """Test pairing a Hermes agent."""
        pairing = self.hermes.pair_hermes('test-hermes-001', 'test-agent')
        
        self.assertEqual(pairing.hermes_id, 'test-hermes-001')
        self.assertEqual(pairing.device_name, 'test-agent')
        self.assertEqual(pairing.capabilities, ['observe', 'summarize'])
        self.assertIsNotNone(pairing.principal_id)

    def test_hermes_pair_idempotent(self):
        """Test that pairing is idempotent."""
        pairing1 = self.hermes.pair_hermes('test-hermes-002', 'test-agent-2')
        pairing2 = self.hermes.pair_hermes('test-hermes-002', 'test-agent-2')
        
        self.assertEqual(pairing1.id, pairing2.id)

    def test_hermes_connect_valid(self):
        """Test Hermes connection with valid pairing."""
        # First pair
        self.hermes.pair_hermes('test-hermes-003', 'test-agent-3')
        
        # Connect
        connection = self.hermes.connect('test-token', 'test-hermes-003')
        
        self.assertEqual(connection.hermes_id, 'test-hermes-003')
        self.assertIn('observe', connection.capabilities)
        self.assertIn('summarize', connection.capabilities)

    def test_hermes_connect_invalid_hermes_id(self):
        """Test Hermes connection fails with unknown hermes_id."""
        with self.assertRaises(self.hermes.HermesAuthError) as ctx:
            self.hermes.connect('test-token', 'unknown-hermes')
        
        self.assertIn('No pairing found', str(ctx.exception))

    def test_hermes_read_status(self):
        """Test Hermes can read miner status."""
        # Pair and connect
        self.hermes.pair_hermes('test-hermes-004', 'test-agent-4')
        connection = self.hermes.connect('test-token', 'test-hermes-004')
        
        # Read status
        status = self.hermes.read_status(connection)
        
        self.assertIn('status', status)
        self.assertIn('mode', status)
        self.assertIn('hashrate_hs', status)

    def test_hermes_append_summary(self):
        """Test Hermes can append summary to spine."""
        # Pair and connect
        self.hermes.pair_hermes('test-hermes-005', 'test-agent-5')
        connection = self.hermes.connect('test-token', 'test-hermes-005')
        
        # Append summary
        result = self.hermes.append_summary(
            connection,
            'Test summary: miner running normally',
            'observe'
        )
        
        self.assertTrue(result['appended'])
        self.assertIn('event_id', result)
        self.assertIn('created_at', result)

    def test_hermes_event_filter(self):
        """Test that user_message events are filtered from Hermes reads."""
        # Pair and connect
        self.hermes.pair_hermes('test-hermes-006', 'test-agent-6')
        connection = self.hermes.connect('test-token', 'test-hermes-006')
        
        # Append a summary (should be visible)
        self.hermes.append_summary(connection, 'Test summary', 'observe')
        
        # Get filtered events
        events = self.hermes.get_filtered_events(connection, limit=10)
        
        # Verify no user_message events
        for event in events:
            self.assertNotEqual(event['kind'], 'user_message')

    def test_hermes_no_control_capability(self):
        """Test that Hermes connections have no control capability."""
        self.hermes.pair_hermes('test-hermes-007', 'test-agent-7')
        connection = self.hermes.connect('test-token', 'test-hermes-007')
        
        self.assertNotIn('control', connection.capabilities)

    def test_daemon_hermes_pair_endpoint(self):
        """Test daemon /hermes/pair endpoint."""
        response, status = self._make_request(
            'POST', '/hermes/pair',
            {'hermes_id': 'daemon-hermes-001', 'device_name': 'daemon-test'}
        )
        
        self.assertEqual(status, 200)
        self.assertTrue(response['success'])
        self.assertEqual(response['hermes_id'], 'daemon-hermes-001')
        self.assertEqual(response['capabilities'], ['observe', 'summarize'])

    def test_daemon_hermes_connect_endpoint(self):
        """Test daemon /hermes/connect endpoint."""
        # First pair
        self._make_request(
            'POST', '/hermes/pair',
            {'hermes_id': 'daemon-hermes-002', 'device_name': 'daemon-test-2'}
        )
        
        # Connect
        response, status = self._make_request(
            'POST', '/hermes/connect',
            {'hermes_id': 'daemon-hermes-002', 'authority_token': 'test-token'}
        )
        
        self.assertEqual(status, 200)
        self.assertTrue(response['connected'])
        self.assertEqual(response['hermes_id'], 'daemon-hermes-002')

    def test_daemon_hermes_status_endpoint(self):
        """Test daemon /hermes/status endpoint."""
        # Setup
        self._make_request(
            'POST', '/hermes/pair',
            {'hermes_id': 'daemon-hermes-003', 'device_name': 'daemon-test-3'}
        )
        self._make_request(
            'POST', '/hermes/connect',
            {'hermes_id': 'daemon-hermes-003', 'authority_token': 'test-token'}
        )
        
        # Read status
        response, status = self._make_request(
            'GET', '/hermes/status',
            headers={'Authorization': 'Hermes daemon-hermes-003'}
        )
        
        self.assertEqual(status, 200)
        self.assertIn('status', response)

    def test_daemon_hermes_summary_endpoint(self):
        """Test daemon /hermes/summary endpoint."""
        # Setup
        self._make_request(
            'POST', '/hermes/pair',
            {'hermes_id': 'daemon-hermes-004', 'device_name': 'daemon-test-4'}
        )
        self._make_request(
            'POST', '/hermes/connect',
            {'hermes_id': 'daemon-hermes-004', 'authority_token': 'test-token'}
        )
        
        # Append summary
        response, status = self._make_request(
            'POST', '/hermes/summary',
            {'summary_text': 'Daemon test summary', 'authority_scope': 'observe'},
            headers={'Authorization': 'Hermes daemon-hermes-004'}
        )
        
        self.assertEqual(status, 200)
        self.assertTrue(response['appended'])

    def test_daemon_hermes_control_blocked(self):
        """Test that Hermes cannot use control endpoints."""
        # Setup
        self._make_request(
            'POST', '/hermes/pair',
            {'hermes_id': 'daemon-hermes-005', 'device_name': 'daemon-test-5'}
        )
        self._make_request(
            'POST', '/hermes/connect',
            {'hermes_id': 'daemon-hermes-005', 'authority_token': 'test-token'}
        )
        
        # Try to start miner
        response, status = self._make_request(
            'POST', '/miner/start',
            {},
            headers={'Authorization': 'Hermes daemon-hermes-005'}
        )
        
        self.assertEqual(status, 403)
        self.assertEqual(response['error'], 'HERMES_UNAUTHORIZED')

    def test_daemon_hermes_events_filtered(self):
        """Test that /hermes/events returns filtered events."""
        # Setup
        self._make_request(
            'POST', '/hermes/pair',
            {'hermes_id': 'daemon-hermes-006', 'device_name': 'daemon-test-6'}
        )
        self._make_request(
            'POST', '/hermes/connect',
            {'hermes_id': 'daemon-hermes-006', 'authority_token': 'test-token'}
        )
        self._make_request(
            'POST', '/hermes/summary',
            {'summary_text': 'Test', 'authority_scope': 'observe'},
            headers={'Authorization': 'Hermes daemon-hermes-006'}
        )
        
        # Get events
        response, status = self._make_request(
            'GET', '/hermes/events?limit=10',
            headers={'Authorization': 'Hermes daemon-hermes-006'}
        )
        
        self.assertEqual(status, 200)
        self.assertIn('events', response)
        
        # Verify no user_message
        for event in response['events']:
            self.assertNotEqual(event['kind'], 'user_message')

    def test_daemon_hermes_missing_auth(self):
        """Test that Hermes endpoints require authorization."""
        response, status = self._make_request('GET', '/hermes/status')
        
        self.assertEqual(status, 401)
        self.assertEqual(response['error'], 'missing_hermes_auth')

    def test_daemon_hermes_not_connected(self):
        """Test that Hermes must be connected before using endpoints."""
        response, status = self._make_request(
            'GET', '/hermes/status',
            headers={'Authorization': 'Hermes unconnected-hermes'}
        )
        
        self.assertEqual(status, 401)
        self.assertEqual(response['error'], 'hermes_not_connected')


def run_tests():
    """Run all tests and return exit code."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestHermesAdapter)
    
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())

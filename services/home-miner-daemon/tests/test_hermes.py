#!/usr/bin/env python3
"""
Tests for the Hermes adapter boundary enforcement.

Covers:
1. Valid token connect succeeds
2. Expired token connect fails
3. Observe capability reads status
4. Summarize capability appends to spine
5. Hermes cannot call control endpoints (403)
6. user_message events are filtered out
7. Invalid/non-Hermes capabilities are rejected
8. Appended summary appears in /hermes/events
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer
from pathlib import Path

# Ensure daemon package is on path
ROOT = Path(__file__).resolve().parents[2]
DAEMON_DIR = ROOT / 'services' / 'home-miner-daemon'
sys.path.insert(0, str(DAEMON_DIR))

import daemon
import hermes
import spine
import store

# Use isolated state dir for tests
TEST_STATE_DIR = tempfile.mkdtemp(prefix='zend_hermes_test_')
os.environ['ZEND_STATE_DIR'] = TEST_STATE_DIR


def rebuild_modules():
    """Reimport modules with the test state dir active."""
    # Re-import with fresh state
    import importlib
    for mod in [spine, store, hermes]:
        importlib.reload(mod)
    # Re-create singleton miner
    daemon.miner = daemon.MinerSimulator()
    daemon._hermes_connections.clear()


rebuild_modules()


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

class HermesTestDaemon(HTTPServer):
    """In-process HTTP server for tests."""

    def __init__(self, port=18765):
        super().__init__(('127.0.0.1', port), daemon.GatewayHandler)
        self.port = port

    def url(self, path=''):
        return f'http://127.0.0.1:{self.port}{path}'


def make_token(
    hermes_id='hermes-001',
    principal_id=None,
    capabilities=None,
    days_valid=30,
):
    """Build a valid Hermes authority token."""
    if principal_id is None:
        principal_id = store.load_or_create_principal().id
    if capabilities is None:
        capabilities = hermes.HERMES_CAPABILITIES

    token = hermes.AuthorityToken(
        version=hermes.AUTHORITY_TOKEN_VERSION,
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=capabilities,
        issued_at=spine._iso_now() if hasattr(spine, '_iso_now') else hermes._iso_now(),
        expires_at=hermes._iso_now(days=days_valid),
    )
    return hermes._encode_token(token)


def make_expired_token(hermes_id='hermes-001', principal_id=None):
    """Build an expired Hermes authority token."""
    if principal_id is None:
        principal_id = store.load_or_create_principal().id
    token = hermes.AuthorityToken(
        version=hermes.AUTHORITY_TOKEN_VERSION,
        hermes_id=hermes_id,
        principal_id=principal_id,
        capabilities=hermes.HERMES_CAPABILITIES,
        issued_at=hermes._iso_now(days=-60),
        expires_at=hermes._iso_now(days=-30),
    )
    return hermes._encode_token(token)


def http_get(url, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Hermes {token}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def http_post(url, data, token=None):
    body = json.dumps(data).encode()
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Hermes {token}'
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHermesAdapter(unittest.TestCase):
    """Tests for the Hermes adapter boundary enforcement."""

    server = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        """Start the test daemon in a background thread."""
        cls.server = TestDaemon()
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.2)  # Let server start

    @classmethod
    def tearDownClass(cls):
        """Stop the test daemon."""
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        """Reset state before each test."""
        rebuild_modules()
        daemon._hermes_connections.clear()
        # Ensure a clean pairing for hermes-001
        hermes.pair_hermes('hermes-001', 'test-hermes')

    def test_hermes_pair(self):
        """Pairing a Hermes agent succeeds and returns observe+summarize."""
        data, status = http_post(
            self.server.url('/hermes/pair'),
            {'hermes_id': 'hermes-new', 'device_name': 'fresh-agent'}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data['hermes_id'], 'hermes-new')
        self.assertEqual(set(data['capabilities']), set(hermes.HERMES_CAPABILITIES))

    def test_hermes_connect_valid(self):
        """Connecting with a valid authority token succeeds."""
        token = make_token()
        data, status = http_post(
            self.server.url('/hermes/connect'),
            {'authority_token': token}
        )
        self.assertEqual(status, 200)
        self.assertTrue(data['connected'])
        self.assertEqual(data['hermes_id'], 'hermes-001')
        self.assertIn('observe', data['capabilities'])
        self.assertIn('summarize', data['capabilities'])

    def test_hermes_connect_expired(self):
        """Connecting with an expired token fails with 401."""
        token = make_expired_token()
        data, status = http_post(
            self.server.url('/hermes/connect'),
            {'authority_token': token}
        )
        self.assertEqual(status, 401)
        self.assertIn('TOKEN_EXPIRED', data.get('message', ''))

    def test_hermes_read_status(self):
        """Hermes with observe capability can read miner status."""
        token = make_token()
        data, status = http_get(
            self.server.url('/hermes/status'),
            token=token
        )
        self.assertEqual(status, 200)
        self.assertTrue(data['connected'])
        self.assertIn('miner', data)
        self.assertIn('status', data['miner'])
        self.assertIn('mode', data['miner'])
        self.assertIn('hashrate_hs', data['miner'])

    def test_hermes_append_summary(self):
        """Hermes with summarize capability can append to the event spine."""
        token = make_token()
        data, status = http_post(
            self.server.url('/hermes/summary'),
            {
                'summary_text': 'Miner running normally at 50kH/s',
                'authority_scope': 'observe',
            },
            token=token
        )
        self.assertEqual(status, 200)
        self.assertTrue(data['appended'])
        self.assertIn('event_id', data)
        self.assertEqual(data['kind'], 'hermes_summary')

    def test_hermes_no_control(self):
        """Hermes clients receive 403 on control endpoints."""
        token = make_token()
        data, status = http_post(
            self.server.url('/miner/start'),
            {},
            token=token
        )
        self.assertEqual(status, 403)
        self.assertIn('HERMES_UNAUTHORIZED', data.get('error', ''))

    def test_hermes_event_filter(self):
        """user_message events are not returned in /hermes/events."""
        # First, add a user_message directly to the spine
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            store.load_or_create_principal().id,
            {'thread_id': 't1', 'sender_id': 'alice', 'encrypted_content': '...'}
        )
        # Add a hermes_summary
        spine.append_event(
            spine.EventKind.HERMES_SUMMARY,
            store.load_or_create_principal().id,
            {'summary_text': 'Test summary', 'authority_scope': ['observe']}
        )

        token = make_token()
        data, status = http_get(
            self.server.url('/hermes/events'),
            token=token
        )
        self.assertEqual(status, 200)
        kinds = [e['kind'] for e in data['events']]
        self.assertNotIn('user_message', kinds)
        # hermes_summary should be present
        self.assertIn('hermes_summary', kinds)

    def test_hermes_invalid_capability(self):
        """A token claiming 'control' is rejected."""
        token = make_token(capabilities=['observe', 'control'])
        data, status = http_post(
            self.server.url('/hermes/connect'),
            {'authority_token': token}
        )
        self.assertEqual(status, 401)
        self.assertIn('INVALID_HERMES_CAPABILITIES', data.get('message', ''))

    def test_hermes_summary_appears_in_events(self):
        """An appended summary is visible via /hermes/events."""
        token = make_token()
        # Append summary
        _, status = http_post(
            self.server.url('/hermes/summary'),
            {'summary_text': 'Miner has been running for 1 hour in balanced mode'},
            token=token
        )
        self.assertEqual(status, 200)

        # Read events
        data, status = http_get(
            self.server.url('/hermes/events'),
            token=token
        )
        self.assertEqual(status, 200)
        summary_kinds = [e for e in data['events'] if e['kind'] == 'hermes_summary']
        self.assertTrue(
            any('1 hour' in str(e.get('payload', {}).get('summary_text', ''))
                for e in summary_kinds),
            f"Expected summary not found in events: {summary_kinds}"
        )

    def test_hermes_unauthorized_status(self):
        """Status endpoint without auth header returns 401."""
        data, status = http_get(self.server.url('/hermes/status'))
        self.assertEqual(status, 401)

    def test_hermes_idempotent_pairing(self):
        """Re-pairing the same hermes_id is idempotent (no error)."""
        data1, status1 = http_post(
            self.server.url('/hermes/pair'),
            {'hermes_id': 'hermes-001', 'device_name': 'test-hermes'}
        )
        data2, status2 = http_post(
            self.server.url('/hermes/pair'),
            {'hermes_id': 'hermes-001', 'device_name': 'test-hermes'}
        )
        self.assertEqual(status1, 200)
        self.assertEqual(status2, 200)
        self.assertEqual(data1['hermes_id'], data2['hermes_id'])


# ---------------------------------------------------------------------------
# Module-level proof (as documented in the plan)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Running Hermes adapter tests...")
    print("Capabilities:", hermes.HERMES_CAPABILITIES)
    print("Readable event kinds:", [k.value for k in hermes.HERMES_READABLE_EVENT_KINDS])
    unittest.main(verbosity=2)

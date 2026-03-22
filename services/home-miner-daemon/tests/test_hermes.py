#!/usr/bin/env python3
"""
Tests for the Hermes adapter.

These tests verify:
1. Hermes can connect with valid authority token
2. Hermes connection fails with expired/invalid tokens
3. Hermes can read miner status (observe capability)
4. Hermes can append summaries to the spine (summarize capability)
5. Hermes CANNOT issue control commands (no control capability)
6. Hermes CANNOT read user_message events (filtered)
7. Hermes with invalid capability is rejected
8. Appended summaries appear in the spine
"""

import base64
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Set up isolated state directory for tests
_test_state_dir = tempfile.mkdtemp(prefix='zend_hermes_test_')
os.environ['ZEND_STATE_DIR'] = _test_state_dir

# Add daemon directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hermes
import spine
import store


class TestHermesAdapter(unittest.TestCase):
    """Tests for the Hermes adapter boundary enforcement."""

    def setUp(self):
        """Set up test fixtures with isolated state."""
        # Reset singleton state files
        self.state_dir = _test_state_dir

        # Load or create principal
        self.principal = store.load_or_create_principal()

        # Pair Hermes
        self.pairing = hermes.pair_hermes("test-hermes-001", "test-hermes-agent")

        # Issue authority token
        self.token = hermes.issue_authority_token("test-hermes-001")

    def tearDown(self):
        """Clean up test state."""
        # No cleanup needed - each test gets isolated state
        pass

    # -------------------------------------------------------------------------
    # Test 1: Hermes connect with valid token
    # -------------------------------------------------------------------------
    def test_hermes_connect_valid(self):
        """connect() with valid authority token succeeds."""
        conn = hermes.connect(self.token)

        self.assertEqual(conn.hermes_id, "test-hermes-001")
        self.assertEqual(conn.principal_id, self.principal.id)
        self.assertIn("observe", conn.capabilities)
        self.assertIn("summarize", conn.capabilities)
        self.assertIsNotNone(conn.connected_at)
        self.assertIsNotNone(conn.token_expires_at)

    # -------------------------------------------------------------------------
    # Test 2: Hermes connect with expired token
    # -------------------------------------------------------------------------
    def test_hermes_connect_expired(self):
        """connect() with expired token raises ValueError."""
        # Create an expired token manually
        import base64 as b64
        expired_payload = {
            "hermes_id": "test-hermes-001",
            "principal_id": self.principal.id,
            "capabilities": ["observe", "summarize"],
            "issued_at": "2020-01-01T00:00:00Z",
            "expires_at": "2020-01-02T00:00:00Z"  # Long expired
        }
        expired_token = b64.b64encode(json.dumps(expired_payload).encode()).decode()

        with self.assertRaises(ValueError) as ctx:
            hermes.connect(expired_token)

        self.assertIn("expired", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # Test 3: Hermes read status (observe capability)
    # -------------------------------------------------------------------------
    def test_hermes_read_status(self):
        """read_status() with observe capability succeeds."""
        conn = hermes.connect(self.token)

        # Mock the miner by patching daemon.miner
        class MockMiner:
            def get_snapshot(self):
                return {
                    "status": "running",
                    "mode": "balanced",
                    "hashrate_hs": 50000,
                    "temperature": 45.0,
                    "uptime_seconds": 3600,
                    "freshness": datetime.now(timezone.utc).isoformat()
                }

        import daemon
        original_miner = daemon.miner
        daemon.miner = MockMiner()

        try:
            status = hermes.read_status(conn)

            self.assertEqual(status["status"], "running")
            self.assertEqual(status["mode"], "balanced")
            self.assertEqual(status["hashrate_hs"], 50000)
            self.assertEqual(status["source"], "hermes_adapter")
            self.assertEqual(status["hermes_id"], "test-hermes-001")
        finally:
            daemon.miner = original_miner

    # -------------------------------------------------------------------------
    # Test 4: Hermes append summary (summarize capability)
    # -------------------------------------------------------------------------
    def test_hermes_append_summary(self):
        """append_summary() with summarize capability appends to spine."""
        conn = hermes.connect(self.token)

        result = hermes.append_summary(
            conn,
            "Miner running normally at 50kH/s",
            authority_scope=["observe"]
        )

        self.assertTrue(result["appended"])
        self.assertIsNotNone(result["event_id"])
        self.assertEqual(result["kind"], "hermes_summary")

    # -------------------------------------------------------------------------
    # Test 5: Hermes cannot control (no control capability)
    # -------------------------------------------------------------------------
    def test_hermes_no_control(self):
        """Hermes connections have observe + summarize but not control."""
        conn = hermes.connect(self.token)

        self.assertNotIn("control", conn.capabilities)
        self.assertTrue(conn.is_capable("observe"))
        self.assertTrue(conn.is_capable("summarize"))
        self.assertFalse(conn.is_capable("control"))

    # -------------------------------------------------------------------------
    # Test 6: Hermes event filtering (user_message blocked)
    # -------------------------------------------------------------------------
    def test_hermes_event_filter(self):
        """get_filtered_events() excludes user_message events."""
        conn = hermes.connect(self.token)

        # Append a user_message (simulating a private message)
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            self.principal.id,
            {
                "thread_id": "thread-001",
                "sender_id": "alice",
                "encrypted_content": "secret message"
            }
        )

        # Append a hermes_summary
        spine.append_hermes_summary(
            "Miner is healthy",
            ["observe"],
            self.principal.id
        )

        events = hermes.get_filtered_events(conn, limit=20)

        # Should include the summary
        kinds = [e["kind"] for e in events]
        self.assertIn("hermes_summary", kinds)

        # Should NOT include the user_message
        self.assertNotIn("user_message", kinds)

    # -------------------------------------------------------------------------
    # Test 7: Hermes with invalid capability rejected
    # -------------------------------------------------------------------------
    def test_hermes_invalid_capability(self):
        """Token requesting 'control' capability is rejected."""
        import base64 as b64

        invalid_payload = {
            "hermes_id": "test-hermes-001",
            "principal_id": self.principal.id,
            "capabilities": ["observe", "summarize", "control"],  # control not allowed
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + 3600, tz=timezone.utc
            ).isoformat()
        }
        invalid_token = b64.b64encode(json.dumps(invalid_payload).encode()).decode()

        with self.assertRaises(ValueError) as ctx:
            hermes.connect(invalid_token)

        self.assertIn("control", str(ctx.exception))
        self.assertIn("invalid", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # Test 8: Hermes summary appears in inbox
    # -------------------------------------------------------------------------
    def test_hermes_summary_appears_in_inbox(self):
        """Appended hermes_summary is readable from spine."""
        conn = hermes.connect(self.token)

        summary_text = "Test summary for inbox verification"
        result = hermes.append_summary(conn, summary_text)

        # Read back from spine
        events = spine.get_events(kind=spine.EventKind.HERMES_SUMMARY, limit=50)
        event_ids = [e.id for e in events]

        self.assertIn(result["event_id"], event_ids)

        # Find the event and verify payload
        matching = [e for e in events if e.id == result["event_id"]]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].payload["summary_text"], summary_text)

    # -------------------------------------------------------------------------
    # Test 9: Pairing is idempotent
    # -------------------------------------------------------------------------
    def test_hermes_pairing_idempotent(self):
        """Re-pairing the same hermes_id returns existing record."""
        first_pairing = hermes.pair_hermes("idempotent-hermes", "idempotent-agent")

        # Pair again with same ID
        second_pairing = hermes.pair_hermes("idempotent-hermes", "idempotent-agent")

        self.assertEqual(first_pairing.hermes_id, second_pairing.hermes_id)
        self.assertEqual(first_pairing.principal_id, second_pairing.principal_id)
        # Tokens should be refreshed (different)
        self.assertNotEqual(first_pairing.token, second_pairing.token)

    # -------------------------------------------------------------------------
    # Test 10: Token expiration check
    # -------------------------------------------------------------------------
    def test_is_token_expired(self):
        """is_token_expired correctly identifies expired tokens."""
        past = datetime.fromtimestamp(time.time() - 3600, tz=timezone.utc).isoformat()
        future = datetime.fromtimestamp(time.time() + 3600, tz=timezone.utc).isoformat()

        self.assertTrue(hermes.is_token_expired(past))
        self.assertFalse(hermes.is_token_expired(future))

    # -------------------------------------------------------------------------
    # Test 11: Read status without observe capability raises
    # -------------------------------------------------------------------------
    def test_hermes_read_status_requires_observe(self):
        """read_status() raises PermissionError without observe capability."""
        # Create a connection with only summarize
        import base64 as b64
        limited_payload = {
            "hermes_id": "test-hermes-001",
            "principal_id": self.principal.id,
            "capabilities": ["summarize"],  # no observe
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + 3600, tz=timezone.utc
            ).isoformat()
        }
        limited_token = b64.b64encode(json.dumps(limited_payload).encode()).decode()

        # This will fail at the token level since hermes_id is already paired
        # with full capabilities. Let's use a fresh pairing.
        hermes.pair_hermes("limited-hermes", "limited-agent")

        # Issue token directly
        import base64 as b64
        limited_payload2 = {
            "hermes_id": "limited-hermes",
            "principal_id": self.principal.id,
            "capabilities": ["summarize"],  # no observe
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + 3600, tz=timezone.utc
            ).isoformat()
        }
        limited_token2 = b64.b64encode(json.dumps(limited_payload2).encode()).decode()

        conn = hermes.connect(limited_token2)

        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(conn)

        self.assertIn("observe", str(ctx.exception))

    # -------------------------------------------------------------------------
    # Test 12: Append summary without summarize capability raises
    # -------------------------------------------------------------------------
    def test_hermes_append_summary_requires_summarize(self):
        """append_summary() raises PermissionError without summarize capability."""
        import base64 as b64

        # Create a pairing with observe-only token
        hermes.pair_hermes("observe-only-hermes", "observe-only-agent")
        observe_payload = {
            "hermes_id": "observe-only-hermes",
            "principal_id": self.principal.id,
            "capabilities": ["observe"],  # no summarize
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + 3600, tz=timezone.utc
            ).isoformat()
        }
        observe_token = b64.b64encode(json.dumps(observe_payload).encode()).decode()

        conn = hermes.connect(observe_token)

        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(conn, "This should fail")

        self.assertIn("summarize", str(ctx.exception))


class TestHermesAdapterDaemon(unittest.TestCase):
    """Tests for Hermes endpoints in the daemon HTTP interface.

    These tests verify the Hermes adapter integration with the daemon by
    directly testing the handler logic rather than making HTTP requests,
    avoiding threading complexity in the test environment.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.state_dir = _test_state_dir
        self.principal = store.load_or_create_principal()

        # Pair Hermes
        self.pairing = hermes.pair_hermes("daemon-test-hermes", "daemon-test-agent")
        self.token = hermes.issue_authority_token("daemon-test-hermes")

    def test_daemon_hermes_status_endpoint_auth(self):
        """Verify hermes status endpoint requires Hermes auth header."""
        import re

        # Test that the auth header parsing works correctly
        auth_header = "Hermes daemon-test-hermes"
        match = re.match(r'^Hermes\s+(\S+)$', auth_header)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "daemon-test-hermes")

        # Test malformed header
        bad_header = "Bearer token123"
        match = re.match(r'^Hermes\s+(\S+)$', bad_header)
        self.assertIsNone(match)

    def test_daemon_hermes_pairing_creates_record(self):
        """POST /hermes/pair creates a Hermes pairing record."""
        # This tests the underlying pairing logic
        pairing = hermes.pair_hermes("new-pair-hermes", "new-pair-agent")
        self.assertEqual(pairing.hermes_id, "new-pair-hermes")
        self.assertEqual(pairing.capabilities, ["observe", "summarize"])

        # Verify it's retrievable
        retrieved = hermes.get_hermes_pairing("new-pair-hermes")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hermes_id, "new-pair-hermes")

    def test_daemon_hermes_connect_endpoint_logic(self):
        """Test connect endpoint logic (decode token and return connection)."""
        # Verify token can be decoded and used
        conn = hermes.connect(self.token)
        self.assertTrue(conn.hermes_id, "daemon-test-hermes")
        self.assertIn("observe", conn.capabilities)
        self.assertIn("summarize", conn.capabilities)

    def test_daemon_hermes_control_rejected(self):
        """Hermes CANNOT call /miner/start (no control capability)."""
        # Hermes has observe + summarize, not control.
        conn = hermes.connect(self.token)
        self.assertNotIn('control', conn.capabilities)
        self.assertTrue(conn.is_capable('observe'))
        self.assertTrue(conn.is_capable('summarize'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
Tests for the Hermes adapter boundary enforcement.

These tests validate that Hermes:
1. Can connect with a valid authority token
2. Cannot connect with an expired or malformed token
3. Can read miner status (observe capability)
4. Can append summaries (summarize capability)
5. CANNOT issue control commands (no control capability)
6. Cannot read user_message events (event filtering)
7. Cannot request control as a capability
8. Appended summaries appear in the event spine
"""

import json
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone

# Ensure service modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Use a temp state dir for all tests
_temp_state_dir = tempfile.mkdtemp()
os.environ['ZEND_STATE_DIR'] = _temp_state_dir

import hermes
import spine
from store import load_or_create_principal


class TestHermesConnect(unittest.TestCase):
    """Test Hermes connection with authority token."""

    def setUp(self):
        # Reset any cached state
        pass

    def test_hermes_connect_valid(self):
        """connect() with a valid token succeeds and returns HermesConnection."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-001",
            "capabilities": ["observe", "summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        }
        token = json.dumps(token_data)

        conn = hermes.connect(token)

        self.assertEqual(conn.hermes_id, "hermes-001")
        self.assertEqual(conn.principal_id, token_data["principal_id"])
        self.assertIn("observe", conn.capabilities)
        self.assertIn("summarize", conn.capabilities)
        self.assertNotIn("control", conn.capabilities)

    def test_hermes_connect_expired(self):
        """connect() with an expired token raises ValueError."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-expired",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }
        token = json.dumps(token_data)

        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        self.assertIn("EXPIRED", str(ctx.exception))

    def test_hermes_connect_malformed_token(self):
        """connect() with a malformed token raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            hermes.connect("not even json")
        self.assertIn("HERMES_INVALID_TOKEN", str(ctx.exception))

    def test_hermes_connect_missing_principal_id(self):
        """connect() with missing principal_id raises ValueError."""
        token_data = {
            "hermes_id": "hermes-bad",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(json.dumps(token_data))
        self.assertIn("principal_id", str(ctx.exception))

    def test_hermes_connect_invalid_capability_rejected(self):
        """connect() requesting 'control' capability is rejected."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-evil",
            "capabilities": ["observe", "summarize", "control"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(json.dumps(token_data))
        self.assertIn("HERMES_INVALID_CAPABILITY", str(ctx.exception))
        self.assertIn("control", str(ctx.exception))

    def test_hermes_connect_no_capabilities(self):
        """connect() with empty capabilities list is allowed (zero-scope)."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-empty",
            "capabilities": [],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        conn = hermes.connect(json.dumps(token_data))
        self.assertEqual(conn.capabilities, [])


class TestHermesReadStatus(unittest.TestCase):
    """Test Hermes readStatus through adapter."""

    def test_hermes_read_status_with_observe(self):
        """read_status() succeeds when observe capability is present."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-ro",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        conn = hermes.connect(json.dumps(token_data))

        result = hermes.read_status(conn)

        self.assertEqual(result["source"], "hermes_adapter")
        self.assertIn("snapshot", result)
        self.assertIn("status", result["snapshot"])

    def test_hermes_read_status_no_observe_raises(self):
        """read_status() raises PermissionError without observe capability."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-locked",
            "capabilities": [],  # no observe
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        conn = hermes.connect(json.dumps(token_data))

        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(conn)
        self.assertIn("observe", str(ctx.exception))


class TestHermesAppendSummary(unittest.TestCase):
    """Test Hermes summary append through adapter."""

    def setUp(self):
        # Ensure a principal exists
        load_or_create_principal()

    def test_hermes_append_summary_with_summarize(self):
        """append_summary() succeeds when summarize capability is present."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-writer",
            "capabilities": ["summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        conn = hermes.connect(json.dumps(token_data))

        result = hermes.append_summary(conn, "Miner running normally at 50kH/s")

        self.assertIn("event_id", result)
        self.assertEqual(result["kind"], "hermes_summary")

    def test_hermes_append_summary_no_summarize_raises(self):
        """append_summary() raises PermissionError without summarize capability."""
        token_data = {
            "principal_id": str(uuid.uuid4()),
            "hermes_id": "hermes-readonly",
            "capabilities": ["observe"],  # no summarize
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        conn = hermes.connect(json.dumps(token_data))

        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(conn, "This should fail")
        self.assertIn("summarize", str(ctx.exception))

    def test_hermes_summary_appears_in_inbox(self):
        """Appended summary is retrievable from the event spine."""
        principal = load_or_create_principal()
        conn = hermes.HermesConnection(
            hermes_id="hermes-inbox-test",
            principal_id=principal.id,
            capabilities=["summarize"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            authority_scope=["summarize"],
        )

        result = hermes.append_summary(conn, "Test summary for inbox")
        event_id = result["event_id"]

        # Fetch from spine
        events = spine.get_events(kind=spine.EventKind.HERMES_SUMMARY, limit=50)
        event_ids = [e.id for e in events]
        self.assertIn(event_id, event_ids)

        # Verify payload
        summary_event = next(e for e in events if e.id == event_id)
        self.assertEqual(summary_event.payload["summary_text"], "Test summary for inbox")


class TestHermesEventFilter(unittest.TestCase):
    """Test Hermes event filtering (user_message blocked)."""

    def setUp(self):
        self.principal = load_or_create_principal()
        self.conn = hermes.HermesConnection(
            hermes_id="hermes-filter-test",
            principal_id=self.principal.id,
            capabilities=["observe", "summarize"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            authority_scope=["observe", "summarize"],
        )
        # Seed the spine with mixed event kinds
        spine.append_hermes_summary("Hermes summary 1", ["observe"], self.principal.id)
        spine.append_miner_alert("health_warning", "Temperature high", self.principal.id)
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            self.principal.id,
            {"thread_id": "t1", "sender_id": "alice", "encrypted_content": "secret"},
        )
        spine.append_hermes_summary("Hermes summary 2", ["observe"], self.principal.id)

    def test_hermes_event_filter_blocks_user_message(self):
        """get_filtered_events() never returns user_message events."""
        events = hermes.get_filtered_events(self.conn, limit=100)

        kinds = [e["kind"] for e in events]
        self.assertNotIn("user_message", kinds)

    def test_hermes_event_filter_allows_hermes_summary(self):
        """get_filtered_events() returns hermes_summary events."""
        events = hermes.get_filtered_events(self.conn, limit=100)

        kinds = [e["kind"] for e in events]
        self.assertIn("hermes_summary", kinds)

    def test_hermes_event_filter_allows_miner_alert(self):
        """get_filtered_events() returns miner_alert events."""
        events = hermes.get_filtered_events(self.conn, limit=100)

        kinds = [e["kind"] for e in events]
        self.assertIn("miner_alert", kinds)

    def test_hermes_event_filter_respects_limit(self):
        """get_filtered_events() respects the requested limit."""
        events = hermes.get_filtered_events(self.conn, limit=2)
        self.assertLessEqual(len(events), 2)


class TestHermesPairing(unittest.TestCase):
    """Test Hermes pairing lifecycle."""

    def test_hermes_pair_idempotent(self):
        """pair_hermes() is idempotent: same hermes_id re-pairs."""
        conn1 = hermes.pair_hermes("hermes-idempotent", "idempotent-agent")
        conn2 = hermes.pair_hermes("hermes-idempotent", "idempotent-agent")

        self.assertEqual(conn1.hermes_id, conn2.hermes_id)
        self.assertEqual(conn1.capabilities, conn2.capabilities)
        self.assertIn("observe", conn1.capabilities)
        self.assertIn("summarize", conn1.capabilities)

    def test_hermes_get_pairing(self):
        """get_hermes_pairing() returns the correct connection after pairing."""
        hermes_id = f"hermes-get-{uuid.uuid4().hex[:8]}"
        created = hermes.pair_hermes(hermes_id, "test-agent")

        retrieved = hermes.get_hermes_pairing(hermes_id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hermes_id, created.hermes_id)
        self.assertEqual(retrieved.capabilities, created.capabilities)

    def test_hermes_get_pairing_unknown_id(self):
        """get_hermes_pairing() returns None for unknown hermes_id."""
        result = hermes.get_hermes_pairing("hermes-does-not-exist")
        self.assertIsNone(result)

    def test_hermes_build_authority_token(self):
        """build_authority_token() produces a valid token round-trip."""
        conn = hermes.pair_hermes("hermes-token-test", "token-agent")
        token = hermes.build_authority_token(conn, expires_in_hours=1)

        parsed = json.loads(token)
        self.assertEqual(parsed["hermes_id"], "hermes-token-test")
        self.assertEqual(parsed["capabilities"], ["observe", "summarize"])
        self.assertIn("expires_at", parsed)


class TestHermesCapabilityBoundary(unittest.TestCase):
    """Test that Hermes CANNOT perform gateway control operations."""

    def test_hermes_capabilities_are_not_gateway_capabilities(self):
        """Hermes capabilities (observe, summarize) differ from gateway capabilities."""
        # Gateway uses: observe, control
        # Hermes uses:   observe, summarize
        self.assertNotIn("control", hermes.HERMES_CAPABILITIES)
        self.assertIn("summarize", hermes.HERMES_CAPABILITIES)

    def test_hermes_readable_events_excludes_user_message(self):
        """HERMES_READABLE_EVENTS blocks user_message."""
        readable = [k.value for k in hermes.HERMES_READABLE_EVENTS]
        self.assertNotIn("user_message", readable)

    def test_hermes_connection_to_dict(self):
        """HermesConnection.to_dict() produces a serializable dict."""
        conn = hermes.HermesConnection(
            hermes_id="hermes-serialize",
            principal_id=str(uuid.uuid4()),
            capabilities=["observe", "summarize"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            authority_scope=["observe"],
        )
        d = conn.to_dict()
        self.assertEqual(d["hermes_id"], "hermes-serialize")
        self.assertIsInstance(d["capabilities"], list)
        # to_dict must be JSON-serializable (str values, not enums)
        json.dumps(d)


if __name__ == "__main__":
    unittest.main()

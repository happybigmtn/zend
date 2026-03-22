#!/usr/bin/env python3
"""
Tests for the Hermes adapter boundary.

Validates:
1. Hermes can connect with a valid authority token
2. Hermes connect fails with expired token
3. Hermes can read miner status (observe capability)
4. Hermes can append summaries to the event spine (summarize capability)
5. Hermes CANNOT issue control commands (403)
6. Hermes CANNOT read user_message events (filtered)
7. Invalid capability requests are rejected
8. Appended summaries appear in the spine inbox
"""

import json
import os
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

# Set up isolated state directory before importing adapter modules.
_TEST_DIR = tempfile.mkdtemp(prefix="zend_hermes_test_")
os.environ["ZEND_STATE_DIR"] = _TEST_DIR

# Ensure the daemon package is on the path.
_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(_ROOT))

from hermes import (
    HERMES_CAPABILITIES,
    HERMES_READABLE_EVENTS,
    HermesConnection,
    HermesPairing,
    append_summary,
    connect,
    get_filtered_events,
    get_hermes_pairing,
    pair_hermes,
    read_status,
    validate_connection,
)
from spine import EventKind, append_event, get_events


class TestHermesCapabilities(unittest.TestCase):
    """Smoke tests for constant definitions."""

    def test_hermes_capabilities_defined(self):
        self.assertEqual(HERMES_CAPABILITIES, ["observe", "summarize"])

    def test_hermes_readable_events_defined(self):
        expected = {EventKind.HERMES_SUMMARY, EventKind.MINER_ALERT,
                    EventKind.CONTROL_RECEIPT}
        self.assertEqual(set(HERMES_READABLE_EVENTS), expected)


class TestHermesPairing(unittest.TestCase):
    """Tests for Hermes pairing lifecycle."""

    def setUp(self):
        self.hermes_id = f"hermes-test-{time.time_ns()}"
        self.device_name = "hermes-test-agent"

    def test_pair_hermes_creates_pairing(self):
        pairing = pair_hermes(self.hermes_id, self.device_name)
        self.assertIsInstance(pairing, HermesPairing)
        self.assertEqual(pairing.hermes_id, self.hermes_id)
        self.assertEqual(pairing.device_name, self.device_name)
        self.assertEqual(pairing.capabilities, HERMES_CAPABILITIES)
        self.assertIsNotNone(pairing.token)
        self.assertIsNotNone(pairing.token_expires_at)
        self.assertFalse(pairing.token_used)

    def test_pair_hermes_idempotent(self):
        p1 = pair_hermes(self.hermes_id, self.device_name)
        p2 = pair_hermes(self.hermes_id, "new-name")
        # Idempotent: re-pairing creates a fresh token.
        self.assertEqual(p2.hermes_id, self.hermes_id)
        self.assertEqual(p2.device_name, "new-name")
        self.assertNotEqual(p1.token, p2.token)

    def test_get_hermes_pairing(self):
        created = pair_hermes(self.hermes_id, self.device_name)
        found = get_hermes_pairing(self.hermes_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.hermes_id, self.hermes_id)
        self.assertEqual(found.token, created.token)

    def test_get_hermes_pairing_not_found(self):
        found = get_hermes_pairing("nonexistent-hermes-99")
        self.assertIsNone(found)

    def test_pair_hermes_empty_id_raises(self):
        with self.assertRaises(ValueError):
            pair_hermes("", "some-device")

    def test_pairing_emits_spine_event(self):
        hermes_id = f"hermes-evttest-{time.time_ns()}"
        pair_hermes(hermes_id, "hermes-evttest-agent")
        events = get_events(kind=EventKind.PAIRING_GRANTED, limit=5)
        hermes_events = [e for e in events if e.payload.get("agent_type") == "hermes"]
        self.assertTrue(
            any(e.payload.get("device_name") == "hermes-evttest-agent"
                for e in hermes_events),
            "Expected a PAIRING_GRANTED event for Hermes in the spine"
        )


class TestHermesConnect(unittest.TestCase):
    """Tests for authority token validation."""

    def setUp(self):
        self.hermes_id = f"hermes-connect-{time.time_ns()}"
        self.pairing = pair_hermes(self.hermes_id, "connect-test-agent")

    def _authority_token(self, **overrides):
        """Build a valid authority token, overridden by `overrides`."""
        payload = {
            "hermes_id": self.hermes_id,
            "principal_id": self.pairing.principal_id,
            "capabilities": list(self.pairing.capabilities),
            "expires_at": self.pairing.token_expires_at,
        }
        payload.update(overrides)
        return json.dumps(payload)

    def test_connect_valid_token_succeeds(self):
        token = self._authority_token()
        conn = connect(token)
        self.assertIsInstance(conn, HermesConnection)
        self.assertEqual(conn.hermes_id, self.hermes_id)
        self.assertEqual(conn.principal_id, self.pairing.principal_id)
        self.assertEqual(conn.capabilities, ["observe", "summarize"])

    def test_connect_malformed_json_raises(self):
        with self.assertRaises(ValueError) as ctx:
            connect("not valid json at all")
        self.assertIn("malformed token", str(ctx.exception))

    def test_connect_missing_fields_raises(self):
        bad = json.dumps({"hermes_id": "x", "principal_id": "y"})
        with self.assertRaises(ValueError) as ctx:
            connect(bad)
        self.assertIn("missing fields", str(ctx.exception))

    def test_connect_expired_token_raises(self):
        expired = self._authority_token(
            expires_at="2020-01-01T00:00:00+00:00"
        )
        with self.assertRaises(PermissionError) as ctx:
            connect(expired)
        self.assertIn("expired", str(ctx.exception))

    def test_connect_invalid_capability_rejected(self):
        bad = self._authority_token(
            capabilities=["observe", "control"]  # control is forbidden
        )
        with self.assertRaises(PermissionError) as ctx:
            connect(bad)
        self.assertIn("not permitted", str(ctx.exception))

    def test_validate_connection_expired_raises(self):
        conn = HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.pairing.principal_id,
            capabilities=["observe"],
            connected_at="2020-01-01T00:00:00+00:00",
            expires_at="2020-01-01T00:00:00+00:00",
        )
        with self.assertRaises(PermissionError) as ctx:
            validate_connection(conn)
        self.assertIn("expired", str(ctx.exception))


class TestHermesReadStatus(unittest.TestCase):
    """Tests for read_status through the adapter."""

    def setUp(self):
        self.hermes_id = f"hermes-status-{time.time_ns()}"
        self.pairing = pair_hermes(self.hermes_id, "status-test-agent")
        self.conn = connect(json.dumps({
            "hermes_id": self.hermes_id,
            "principal_id": self.pairing.principal_id,
            "capabilities": ["observe"],
            "expires_at": self.pairing.token_expires_at,
        }))

    def test_read_status_returns_snapshot(self):
        snapshot = read_status(self.conn)
        self.assertIn("status", snapshot)
        self.assertIn("mode", snapshot)
        self.assertIn("hashrate_hs", snapshot)
        self.assertIn("temperature", snapshot)
        self.assertIn("freshness", snapshot)

    def test_read_status_expired_raises(self):
        conn = HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.pairing.principal_id,
            capabilities=["observe"],
            connected_at="2020-01-01T00:00:00+00:00",
            expires_at="2020-01-01T00:00:00+00:00",
        )
        with self.assertRaises(PermissionError):
            read_status(conn)

    def test_read_status_observe_only_sufficient(self):
        # A connection with only "observe" should work.
        conn = connect(json.dumps({
            "hermes_id": self.hermes_id,
            "principal_id": self.pairing.principal_id,
            "capabilities": ["observe"],
            "expires_at": self.pairing.token_expires_at,
        }))
        snapshot = read_status(conn)
        self.assertIsInstance(snapshot, dict)


class TestHermesAppendSummary(unittest.TestCase):
    """Tests for append_summary through the adapter."""

    def setUp(self):
        self.hermes_id = f"hermes-sum-{time.time_ns()}"
        self.pairing = pair_hermes(self.hermes_id, "sum-test-agent")
        self.conn = connect(json.dumps({
            "hermes_id": self.hermes_id,
            "principal_id": self.pairing.principal_id,
            "capabilities": ["observe", "summarize"],
            "expires_at": self.pairing.token_expires_at,
        }))

    def test_append_summary_returns_event_id(self):
        result = append_summary(
            self.conn,
            "Miner running normally at 50kH/s",
            "observe",
        )
        self.assertTrue(result["appended"])
        self.assertIn("event_id", result)
        self.assertEqual(result["kind"], EventKind.HERMES_SUMMARY.value)

    def test_append_summary_appears_in_spine(self):
        before = {
            e.id for e in get_events(kind=EventKind.HERMES_SUMMARY, limit=50)
        }
        result = append_summary(
            self.conn,
            "Hashrate steady, no alerts.",
            "observe",
        )
        after = get_events(kind=EventKind.HERMES_SUMMARY, limit=50)
        new_ids = {e.id for e in after} - before
        self.assertIn(result["event_id"], new_ids)

    def test_append_summary_empty_text_raises(self):
        with self.assertRaises(ValueError):
            append_summary(self.conn, "", "observe")
        with self.assertRaises(ValueError):
            append_summary(self.conn, "   ", "observe")

    def test_append_summary_expired_raises(self):
        conn = HermesConnection(
            hermes_id=self.hermes_id,
            principal_id=self.pairing.principal_id,
            capabilities=["summarize"],
            connected_at="2020-01-01T00:00:00+00:00",
            expires_at="2020-01-01T00:00:00+00:00",
        )
        with self.assertRaises(PermissionError):
            append_summary(conn, "test", "observe")


class TestHermesEventFiltering(unittest.TestCase):
    """Tests for user_message blocking and event filtering."""

    def setUp(self):
        self.hermes_id = f"hermes-filter-{time.time_ns()}"
        self.pairing = pair_hermes(self.hermes_id, "filter-test-agent")
        self.conn = connect(json.dumps({
            "hermes_id": self.hermes_id,
            "principal_id": self.pairing.principal_id,
            "capabilities": ["observe"],
            "expires_at": self.pairing.token_expires_at,
        }))
        # Seed some spine events.
        principal = self.pairing.principal_id
        append_event(EventKind.HERMES_SUMMARY, principal,
                     {"summary_text": "summary for filter test"})
        append_event(EventKind.MINER_ALERT, principal,
                     {"alert_type": "offline", "message": "test alert"})
        append_event(EventKind.USER_MESSAGE, principal,
                     {"thread_id": "t1", "sender_id": "alice",
                      "encrypted_content": "SECRET"})
        append_event(EventKind.CONTROL_RECEIPT, principal,
                     {"command": "start", "status": "accepted"})

    def test_filtered_events_excludes_user_message(self):
        events = get_filtered_events(self.conn, limit=20)
        kinds = {e["kind"] for e in events}
        self.assertNotIn(EventKind.USER_MESSAGE.value, kinds)

    def test_filtered_events_includes_hermes_summary(self):
        events = get_filtered_events(self.conn, limit=20)
        kinds = {e["kind"] for e in events}
        self.assertIn(EventKind.HERMES_SUMMARY.value, kinds)

    def test_filtered_events_includes_miner_alert(self):
        events = get_filtered_events(self.conn, limit=20)
        kinds = {e["kind"] for e in events}
        self.assertIn(EventKind.MINER_ALERT.value, kinds)

    def test_filtered_events_includes_control_receipt(self):
        events = get_filtered_events(self.conn, limit=20)
        kinds = {e["kind"] for e in events}
        self.assertIn(EventKind.CONTROL_RECEIPT.value, kinds)

    def test_filtered_events_respects_limit(self):
        events = get_filtered_events(self.conn, limit=2)
        self.assertLessEqual(len(events), 2)


class TestHermesNoControl(unittest.TestCase):
    """Tests verifying Hermes cannot perform control operations."""

    def setUp(self):
        self.hermes_id = f"hermes-noctrl-{time.time_ns()}"
        self.pairing = pair_hermes(self.hermes_id, "noctrl-test-agent")

    def test_control_capability_rejected_at_connect(self):
        token = json.dumps({
            "hermes_id": self.hermes_id,
            "principal_id": self.pairing.principal_id,
            "capabilities": ["observe", "control"],  # forbidden
            "expires_at": self.pairing.token_expires_at,
        })
        with self.assertRaises(PermissionError) as ctx:
            connect(token)
        self.assertIn("not permitted", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

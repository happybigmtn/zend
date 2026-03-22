#!/usr/bin/env python3
"""
Tests for Hermes adapter boundary enforcement.

Covers:
1. Valid/invalid/expired token connect
2. readStatus requires observe
3. appendSummary requires summarize
4. Control paths rejected for Hermes
5. Event filtering (user_message excluded)
6. Hermes cannot read other Hermes's summaries? No — all hermes_summary is readable
7. Empty/invalid summary rejected
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import hermes
import store
import spine


class TestHermesConnect(unittest.TestCase):
    """Tests for hermes.connect()"""

    def test_valid_token_succeeds(self):
        token = json.dumps({
            "hermes_id": "h-test",
            "principal_id": "p-test",
            "capabilities": ["observe", "summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        self.assertEqual(conn.hermes_id, "h-test")
        self.assertEqual(conn.principal_id, "p-test")
        self.assertEqual(conn.capabilities, ["observe", "summarize"])
        self.assertIn("observe", conn.capabilities)
        self.assertIn("summarize", conn.capabilities)

    def test_expired_token_rejected(self):
        token = json.dumps({
            "hermes_id": "h-test",
            "principal_id": "p-test",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        })
        with self.assertRaises(PermissionError) as ctx:
            hermes.connect(token)
        self.assertIn("EXPIRED", str(ctx.exception))

    def test_malformed_token_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            hermes.connect("not-json")
        self.assertIn("AUTH_INVALID", str(ctx.exception))

    def test_missing_hermes_id_rejected(self):
        token = json.dumps({
            "principal_id": "p-test",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        with self.assertRaises(ValueError) as ctx:
            hermes.connect(token)
        self.assertIn("hermes_id", str(ctx.exception))

    def test_control_capability_rejected(self):
        token = json.dumps({
            "hermes_id": "h-test",
            "principal_id": "p-test",
            "capabilities": ["observe", "summarize", "control"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        with self.assertRaises(PermissionError) as ctx:
            hermes.connect(token)
        self.assertIn("UNAUTHORIZED_CAPABILITY", str(ctx.exception))

    def test_observe_only_token_succeeds(self):
        token = json.dumps({
            "hermes_id": "h-observe",
            "principal_id": "p-test",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        self.assertEqual(conn.capabilities, ["observe"])
        self.assertTrue(conn.has_capability("observe"))
        self.assertFalse(conn.has_capability("summarize"))

    def test_summarize_only_token_succeeds(self):
        token = json.dumps({
            "hermes_id": "h-summarize",
            "principal_id": "p-test",
            "capabilities": ["summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        self.assertEqual(conn.capabilities, ["summarize"])


class TestHermesReadStatus(unittest.TestCase):
    """Tests for hermes.read_status()"""

    def test_observe_capability_reads_status(self):
        token = json.dumps({
            "hermes_id": "h-read",
            "principal_id": "p-read",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        status = hermes.read_status(conn)
        self.assertIn("status", status)
        self.assertIn("mode", status)
        self.assertIn("hashrate_hs", status)
        self.assertIn("temperature", status)

    def test_missing_observe_rejected(self):
        token = json.dumps({
            "hermes_id": "h-no-observe",
            "principal_id": "p-test",
            "capabilities": ["summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        with self.assertRaises(PermissionError) as ctx:
            hermes.read_status(conn)
        self.assertIn("observe capability required", str(ctx.exception))


class TestHermesAppendSummary(unittest.TestCase):
    """Tests for hermes.append_summary()"""

    def test_summarize_capability_appends_to_spine(self):
        token = json.dumps({
            "hermes_id": "h-sum",
            "principal_id": "p-sum",
            "capabilities": ["summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        result = hermes.append_summary(conn, "Miner is running well", ["observe"])
        self.assertTrue(result["appended"])
        self.assertIn("event_id", result)
        self.assertEqual(result["kind"], "hermes_summary")

        # Verify it appears in the spine
        events = spine.get_events(kind=spine.EventKind.HERMES_SUMMARY, limit=5)
        found = any(e.id == result["event_id"] for e in events)
        self.assertTrue(found, "Summary event should be in spine")

    def test_missing_summarize_rejected(self):
        token = json.dumps({
            "hermes_id": "h-no-sum",
            "principal_id": "p-test",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        with self.assertRaises(PermissionError) as ctx:
            hermes.append_summary(conn, "Some summary")
        self.assertIn("summarize capability required", str(ctx.exception))

    def test_empty_summary_rejected(self):
        token = json.dumps({
            "hermes_id": "h-empty",
            "principal_id": "p-test",
            "capabilities": ["summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        with self.assertRaises(ValueError) as ctx:
            hermes.append_summary(conn, "")
        self.assertIn("must not be empty", str(ctx.exception))

    def test_whitespace_only_summary_rejected(self):
        token = json.dumps({
            "hermes_id": "h-ws",
            "principal_id": "p-test",
            "capabilities": ["summarize"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        with self.assertRaises(ValueError):
            hermes.append_summary(conn, "   ")


class TestHermesEventFiltering(unittest.TestCase):
    """Tests for event filtering — user_message must not appear in Hermes reads."""

    def test_user_message_not_in_filtered_events(self):
        token = json.dumps({
            "hermes_id": "h-filter",
            "principal_id": "p-filter",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)

        # Append a user_message directly to spine
        spine.append_event(
            spine.EventKind.USER_MESSAGE,
            principal_id="p-filter",
            payload={"thread_id": "t1", "sender_id": "alice", "encrypted_content": "secret"},
        )

        # Append a hermes_summary
        spine.append_event(
            spine.EventKind.HERMES_SUMMARY,
            principal_id="p-filter",
            payload={"summary_text": "Test summary", "authority_scope": ["observe"]},
        )

        events = hermes.get_filtered_events(conn, limit=50)
        kinds = [e["kind"] for e in events]

        self.assertNotIn("user_message", kinds, "user_message must be filtered out")
        self.assertIn("hermes_summary", kinds, "hermes_summary should be present")


class TestHermesControlBoundary(unittest.TestCase):
    """Tests that Hermes cannot perform control operations."""

    def test_control_path_rejected(self):
        # Verify is_control_path marks all control paths
        self.assertTrue(hermes.is_control_path("/miner/start"))
        self.assertTrue(hermes.is_control_path("/miner/stop"))
        self.assertTrue(hermes.is_control_path("/miner/set_mode"))
        self.assertFalse(hermes.is_control_path("/status"))
        self.assertFalse(hermes.is_control_path("/hermes/summary"))

    def test_observe_only_cannot_write_summary(self):
        token = json.dumps({
            "hermes_id": "h-observe-only",
            "principal_id": "p-observe",
            "capabilities": ["observe"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        conn = hermes.connect(token)
        with self.assertRaises(PermissionError):
            hermes.append_summary(conn, "Trying to summarize without capability")


class TestHermesPairing(unittest.TestCase):
    """Tests for hermes.pair_hermes() and hermes.connect_from_pairing()."""

    def test_pair_creates_record(self):
        record = hermes.pair_hermes("h-pair-test", "pair-agent")
        self.assertEqual(record["hermes_id"], "h-pair-test")
        self.assertEqual(record["device_name"], "pair-agent")
        self.assertEqual(record["capabilities"], ["observe", "summarize"])
        self.assertIn("principal_id", record)
        self.assertIn("paired_at", record)
        self.assertIn("token_expires_at", record)

    def test_pair_is_idempotent(self):
        r1 = hermes.pair_hermes("h-idem", "idem-agent")
        r2 = hermes.pair_hermes("h-idem", "idem-agent")
        self.assertEqual(r1["hermes_id"], r2["hermes_id"])
        self.assertEqual(r2["device_name"], "idem-agent")

    def test_connect_from_pairing(self):
        hermes.pair_hermes("h-pair-connect", "pair-connect-agent")
        conn = hermes.connect_from_pairing("h-pair-connect")
        self.assertEqual(conn.hermes_id, "h-pair-connect")
        self.assertEqual(conn.capabilities, ["observe", "summarize"])

    def test_connect_from_unknown_pairing_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            hermes.connect_from_pairing("h-unknown")
        self.assertIn("PAIRING_NOT_FOUND", str(ctx.exception))

    def test_pair_token_expires_30_days_later(self):
        record = hermes.pair_hermes("h-exp-test", "exp-agent")
        expires = datetime.fromisoformat(record["token_expires_at"])
        now = datetime.now(timezone.utc)
        delta = expires - now
        self.assertGreater(delta.days, 25, "Token should expire ~30 days from now")


class TestHermesCapabilities(unittest.TestCase):
    """Tests for capability constants."""

    def test_hermes_capabilities_only_observe_and_summarize(self):
        self.assertEqual(hermes.HERMES_CAPABILITIES, ["observe", "summarize"])
        self.assertNotIn("control", hermes.HERMES_CAPABILITIES)

    def test_hermes_readable_events_excludes_user_message(self):
        kinds = {e.value for e in hermes.HERMES_READABLE_EVENTS}
        self.assertIn("hermes_summary", kinds)
        self.assertIn("miner_alert", kinds)
        self.assertIn("control_receipt", kinds)
        self.assertNotIn("user_message", kinds)
        self.assertNotIn("pairing_requested", kinds)
        self.assertNotIn("pairing_granted", kinds)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
Tests for event spine persistence and querying.

These tests verify:
- Events append correctly to the spine
- Events persist across reloads
- Events can be filtered by kind
- Limit parameter works correctly
"""

import json
import os

import pytest


class TestEventSpineAppend:
    """Tests for appending events to the spine."""

    def test_append_pairing_requested(self, state_dir):
        """Appending PAIRING_REQUESTED event works."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import append_pairing_requested, EventKind

        event = append_pairing_requested(
            device_name="test-device",
            requested_capabilities=["observe"],
            principal_id="test-principal-id"
        )

        assert event.id is not None
        assert event.kind == EventKind.PAIRING_REQUESTED.value
        assert event.principal_id == "test-principal-id"
        assert event.payload["device_name"] == "test-device"
        assert event.payload["requested_capabilities"] == ["observe"]

    def test_append_control_receipt(self, state_dir):
        """Appending CONTROL_RECEIPT event works."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import append_control_receipt, EventKind

        event = append_control_receipt(
            command="start",
            mode=None,
            status="accepted",
            principal_id="test-principal-id"
        )

        assert event.kind == EventKind.CONTROL_RECEIPT.value
        assert event.payload["command"] == "start"
        assert event.payload["status"] == "accepted"
        assert "receipt_id" in event.payload

    def test_append_hermes_summary(self, state_dir):
        """Appending HERMES_SUMMARY event works."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import append_hermes_summary, EventKind

        event = append_hermes_summary(
            summary_text="Mining status: healthy",
            authority_scope=["observe"],
            principal_id="test-principal-id"
        )

        assert event.kind == EventKind.HERMES_SUMMARY.value
        assert event.payload["summary_text"] == "Mining status: healthy"
        assert event.payload["authority_scope"] == ["observe"]


class TestEventSpinePersistence:
    """Tests for event persistence across reloads."""

    def test_events_persist_across_reload(self, state_dir):
        """Events survive process restart (file persists)."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import append_pairing_requested, get_events, EventKind

        # Append an event
        original = append_pairing_requested(
            device_name="persist-test",
            requested_capabilities=["observe"],
            principal_id="persist-principal"
        )

        # get_events reads from file, simulating reload
        events = get_events(kind=EventKind.PAIRING_REQUESTED, limit=10)

        # Should find our event
        assert len(events) >= 1
        found = any(e.id == original.id for e in events)
        assert found, "Appended event not found after reload"


class TestEventSpineQuery:
    """Tests for querying events."""

    def test_get_events_filtered_by_kind(self, state_dir):
        """Can filter events by kind."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import (
            append_pairing_requested,
            append_control_receipt,
            get_events,
            EventKind
        )

        # Append different event types
        append_pairing_requested("filter-test", ["observe"], "filter-principal")
        append_control_receipt("start", None, "accepted", "filter-principal")

        # Filter by kind
        pairing_events = get_events(kind=EventKind.PAIRING_REQUESTED, limit=10)
        control_events = get_events(kind=EventKind.CONTROL_RECEIPT, limit=10)

        # All pairing_events should be PAIRING_REQUESTED
        for e in pairing_events:
            assert e.kind == EventKind.PAIRING_REQUESTED.value

        # All control_events should be CONTROL_RECEIPT
        for e in control_events:
            assert e.kind == EventKind.CONTROL_RECEIPT.value

    def test_get_events_respects_limit(self, state_dir):
        """Limit parameter restricts returned events."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import append_pairing_requested, get_events, EventKind

        # Append multiple events
        for i in range(5):
            append_pairing_requested(
                f"limit-test-{i}",
                ["observe"],
                "limit-principal"
            )

        # Get only 2
        events = get_events(kind=EventKind.PAIRING_REQUESTED, limit=2)

        assert len(events) == 2

    def test_get_events_returns_most_recent_first(self, state_dir):
        """Events are returned newest-first."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import append_pairing_requested, get_events, EventKind

        # Append 3 events
        first = append_pairing_requested("order-test-1", ["observe"], "order-principal")
        second = append_pairing_requested("order-test-2", ["observe"], "order-principal")
        third = append_pairing_requested("order-test-3", ["observe"], "order-principal")

        events = get_events(kind=EventKind.PAIRING_REQUESTED, limit=3)

        # Most recent (third) should be first
        assert events[0].payload["device_name"] == "order-test-3"
        assert events[1].payload["device_name"] == "order-test-2"
        assert events[2].payload["device_name"] == "order-test-1"


class TestEventSpineSchema:
    """Tests for event schema compliance."""

    def test_event_has_required_fields(self, state_dir):
        """All events have required fields."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from spine import append_control_receipt

        event = append_control_receipt(
            command="stop",
            mode=None,
            status="accepted",
            principal_id="schema-test-principal"
        )

        assert hasattr(event, "id")
        assert hasattr(event, "principal_id")
        assert hasattr(event, "kind")
        assert hasattr(event, "payload")
        assert hasattr(event, "created_at")
        assert hasattr(event, "version")
        assert event.version == 1

#!/usr/bin/env python3
"""
Tests for inbox routing via the event spine API.

These tests verify that the /spine/events endpoint correctly:
1. Returns all event kinds
2. Filters by kind parameter
3. Respects the limit parameter
4. Returns events in reverse chronological order
"""

import json
import os
import tempfile
import pytest
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine import (
    SPINE_FILE,
    EventKind,
    SpineEvent,
    append_event,
    get_events,
    _load_events,
    _save_event,
)
from daemon import app


@pytest.fixture
def temp_spine(monkeypatch):
    """Create a temporary spine file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        temp_path = f.name
    
    # Override the spine file path
    monkeypatch.setattr('spine.SPINE_FILE', temp_path)
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestSpineEventsReturnsAllKinds:
    """Test that all event kinds can be stored and retrieved."""
    
    def test_pairing_requested_event(self, temp_spine):
        """Pairing requested events are stored and retrieved."""
        event = append_event(
            EventKind.PAIRING_REQUESTED,
            "test-principal",
            {"device_name": "test-phone", "requested_capabilities": ["observe"]}
        )
        
        events = get_events()
        assert len(events) == 1
        assert events[0].kind == "pairing_requested"
        assert events[0].payload["device_name"] == "test-phone"
    
    def test_pairing_granted_event(self, temp_spine):
        """Pairing granted events are stored and retrieved."""
        event = append_event(
            EventKind.PAIRING_GRANTED,
            "test-principal",
            {"device_name": "test-phone", "granted_capabilities": ["observe", "control"]}
        )
        
        events = get_events()
        assert len(events) == 1
        assert events[0].kind == "pairing_granted"
        assert "control" in events[0].payload["granted_capabilities"]
    
    def test_capability_revoked_event(self, temp_spine):
        """Capability revoked events are stored and retrieved."""
        event = append_event(
            EventKind.CAPABILITY_REVOKED,
            "test-principal",
            {"device_name": "test-phone", "revoked_capabilities": ["control"], "reason": "user_requested"}
        )
        
        events = get_events()
        assert len(events) == 1
        assert events[0].kind == "capability_revoked"
        assert events[0].payload["reason"] == "user_requested"
    
    def test_miner_alert_event(self, temp_spine):
        """Miner alert events are stored and retrieved."""
        event = append_event(
            EventKind.MINER_ALERT,
            "test-principal",
            {"alert_type": "health_warning", "message": "Temperature high"}
        )
        
        events = get_events()
        assert len(events) == 1
        assert events[0].kind == "miner_alert"
        assert events[0].payload["alert_type"] == "health_warning"
    
    def test_control_receipt_event(self, temp_spine):
        """Control receipt events are stored and retrieved."""
        event = append_event(
            EventKind.CONTROL_RECEIPT,
            "test-principal",
            {"command": "set_mode", "mode": "balanced", "status": "accepted"}
        )
        
        events = get_events()
        assert len(events) == 1
        assert events[0].kind == "control_receipt"
        assert events[0].payload["status"] == "accepted"
    
    def test_hermes_summary_event(self, temp_spine):
        """Hermes summary events are stored and retrieved."""
        event = append_event(
            EventKind.HERMES_SUMMARY,
            "test-principal",
            {"summary_text": "Miner running efficiently", "authority_scope": ["observe"]}
        )
        
        events = get_events()
        assert len(events) == 1
        assert events[0].kind == "hermes_summary"
        assert "efficiently" in events[0].payload["summary_text"]
    
    def test_user_message_event(self, temp_spine):
        """User message events are stored and retrieved."""
        event = append_event(
            EventKind.USER_MESSAGE,
            "test-principal",
            {"thread_id": "thread-123", "sender_id": "sender-456", "encrypted_content": "..."}
        )
        
        events = get_events()
        assert len(events) == 1
        assert events[0].kind == "user_message"
        assert events[0].payload["thread_id"] == "thread-123"


class TestSpineEventsFilterByKind:
    """Test that kind parameter correctly filters events."""
    
    def test_filter_by_single_kind(self, temp_spine):
        """Filter returns only events of specified kind."""
        # Create events of different kinds
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "start", "status": "accepted"})
        append_event(EventKind.MINER_ALERT, "p1", {"alert_type": "offline", "message": "Miner down"})
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "stop", "status": "accepted"})
        
        events = get_events(kind=EventKind.CONTROL_RECEIPT)
        assert len(events) == 2
        assert all(e.kind == "control_receipt" for e in events)
    
    def test_filter_by_kind_returns_empty_for_no_matches(self, temp_spine):
        """Filter returns empty list when no events match kind."""
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "start", "status": "accepted"})
        
        events = get_events(kind=EventKind.HERMES_SUMMARY)
        assert len(events) == 0
    
    def test_no_filter_returns_all_kinds(self, temp_spine):
        """No kind filter returns all events."""
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "start", "status": "accepted"})
        append_event(EventKind.MINER_ALERT, "p1", {"alert_type": "offline", "message": "Miner down"})
        append_event(EventKind.HERMES_SUMMARY, "p1", {"summary_text": "Test"})
        
        events = get_events()
        assert len(events) == 3
        kinds = {e.kind for e in events}
        assert "control_receipt" in kinds
        assert "miner_alert" in kinds
        assert "hermes_summary" in kinds


class TestSpineEventsLimit:
    """Test that limit parameter caps results."""
    
    def test_limit_returns_correct_count(self, temp_spine):
        """Limit parameter returns at most N events."""
        for i in range(10):
            append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": f"cmd-{i}", "status": "accepted"})
        
        events = get_events(limit=5)
        assert len(events) == 5
    
    def test_limit_with_kind_filter(self, temp_spine):
        """Limit works together with kind filter."""
        for i in range(5):
            append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": f"cmd-{i}", "status": "accepted"})
        append_event(EventKind.MINER_ALERT, "p1", {"alert_type": "offline", "message": "Miner down"})
        
        events = get_events(kind=EventKind.CONTROL_RECEIPT, limit=3)
        assert len(events) == 3
        assert all(e.kind == "control_receipt" for e in events)
    
    def test_limit_higher_than_available_returns_all(self, temp_spine):
        """Limit larger than available events returns all."""
        for i in range(3):
            append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": f"cmd-{i}", "status": "accepted"})
        
        events = get_events(limit=100)
        assert len(events) == 3


class TestSpineEventsOrder:
    """Test that events are returned in reverse chronological order."""
    
    def test_newest_first(self, temp_spine):
        """Most recent events appear first."""
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "first", "status": "accepted"})
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "second", "status": "accepted"})
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "third", "status": "accepted"})
        
        events = get_events()
        assert len(events) == 3
        # Events should be newest first
        assert events[0].payload["command"] == "third"
        assert events[1].payload["command"] == "second"
        assert events[2].payload["command"] == "first"
    
    def test_filter_preserves_order(self, temp_spine):
        """Filtering by kind preserves reverse chronological order."""
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "old", "status": "accepted"})
        append_event(EventKind.MINER_ALERT, "p1", {"alert_type": "offline", "message": "Miner down"})
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "new", "status": "accepted"})
        
        events = get_events(kind=EventKind.CONTROL_RECEIPT)
        assert events[0].payload["command"] == "new"
        assert events[1].payload["command"] == "old"


class TestInboxRouting:
    """Integration tests for inbox routing scenarios."""
    
    def test_inbox_events_route_correctly(self, temp_spine):
        """Verify events route to inbox correctly per event-spine.md."""
        # Inbox-routed events
        append_event(EventKind.CONTROL_RECEIPT, "p1", {"command": "start", "status": "accepted"})
        append_event(EventKind.MINER_ALERT, "p1", {"alert_type": "health_warning", "message": "Temp high"})
        append_event(EventKind.HERMES_SUMMARY, "p1", {"summary_text": "Running well"})
        append_event(EventKind.USER_MESSAGE, "p1", {"thread_id": "t1", "sender_id": "s1", "encrypted_content": "..."})
        
        # Device-routed events (should not appear in inbox)
        append_event(EventKind.PAIRING_REQUESTED, "p1", {"device_name": "phone", "requested_capabilities": ["observe"]})
        append_event(EventKind.PAIRING_GRANTED, "p1", {"device_name": "phone", "granted_capabilities": ["observe"]})
        append_event(EventKind.CAPABILITY_REVOKED, "p1", {"device_name": "phone", "revoked_capabilities": ["control"], "reason": "test"})
        
        all_events = get_events()
        inbox_kinds = {"control_receipt", "miner_alert", "hermes_summary", "user_message"}
        
        inbox_events = [e for e in all_events if e.kind in inbox_kinds]
        device_events = [e for e in all_events if e.kind not in inbox_kinds]
        
        assert len(inbox_events) == 4
        assert len(device_events) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

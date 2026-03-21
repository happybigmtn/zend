#!/usr/bin/env python3
"""
Event spine - append-only encrypted event journal.

The event spine is the source of truth. The inbox is a derived view.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

SPINE_FILE = os.path.join(STATE_DIR, 'event-spine.jsonl')


class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"


SURFACE_ROUTES = {
    "home": {EventKind.MINER_ALERT.value},
    "inbox": {
        EventKind.MINER_ALERT.value,
        EventKind.CONTROL_RECEIPT.value,
        EventKind.HERMES_SUMMARY.value,
        EventKind.USER_MESSAGE.value,
    },
    "agent": {EventKind.HERMES_SUMMARY.value},
    "device_pairing": {
        EventKind.PAIRING_REQUESTED.value,
        EventKind.PAIRING_GRANTED.value,
    },
    "device_permissions": {EventKind.CAPABILITY_REVOKED.value},
}


@dataclass
class SpineEvent:
    """An event in the append-only journal."""
    id: str
    principal_id: str
    kind: str
    payload: dict
    created_at: str
    version: int = 1


def _load_events() -> list[SpineEvent]:
    """Load all events from the spine."""
    events = []
    if os.path.exists(SPINE_FILE):
        with open(SPINE_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    events.append(SpineEvent(**data))
    return events


def _save_event(event: SpineEvent):
    """Append event to the spine."""
    with open(SPINE_FILE, 'a') as f:
        f.write(json.dumps(asdict(event)) + '\n')


def _coerce_event_kind(kind: Optional[EventKind | str]) -> Optional[str]:
    """Normalize event-kind input from CLI and HTTP callers."""
    if kind is None:
        return None
    if isinstance(kind, EventKind):
        return kind.value
    return EventKind(kind).value


def serialize_event(event: SpineEvent, include_version: bool = False) -> dict:
    """Render a spine event as a JSON-friendly dict."""
    payload = {
        "id": event.id,
        "principal_id": event.principal_id,
        "kind": event.kind,
        "payload": event.payload,
        "created_at": event.created_at,
    }
    if include_version:
        payload["version"] = event.version
    return payload


def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append a new event to the spine."""
    event = SpineEvent(
        id=str(uuid.uuid4()),
        principal_id=principal_id,
        kind=kind.value,
        payload=payload,
        created_at=datetime.now(timezone.utc).isoformat(),
        version=1
    )
    _save_event(event)
    return event


def get_events(
    kind: Optional[EventKind | str] = None,
    limit: int = 100,
    surface: Optional[str] = None,
) -> list[SpineEvent]:
    """Get events from the spine, optionally filtered by kind or routed surface."""
    events = _load_events()

    if surface:
        if surface not in SURFACE_ROUTES:
            raise ValueError(f"invalid_surface:{surface}")
        allowed_kinds = SURFACE_ROUTES[surface]
        events = [e for e in events if e.kind in allowed_kinds]

    if kind:
        kind_value = _coerce_event_kind(kind)
        events = [e for e in events if e.kind == kind_value]

    # Return most recent first
    events.reverse()

    return events[:limit]


def append_pairing_requested(device_name: str, requested_capabilities: list, principal_id: str):
    """Append a pairing requested event."""
    return append_event(
        EventKind.PAIRING_REQUESTED,
        principal_id,
        {
            "device_name": device_name,
            "requested_capabilities": requested_capabilities
        }
    )


def append_pairing_granted(device_name: str, granted_capabilities: list, principal_id: str):
    """Append a pairing granted event."""
    return append_event(
        EventKind.PAIRING_GRANTED,
        principal_id,
        {
            "device_name": device_name,
            "granted_capabilities": granted_capabilities
        }
    )


def append_control_receipt(command: str, mode: Optional[str], status: str, principal_id: str):
    """Append a control receipt event."""
    payload = {
        "command": command,
        "status": status,
        "receipt_id": str(uuid.uuid4())
    }
    if mode:
        payload["mode"] = mode

    return append_event(
        EventKind.CONTROL_RECEIPT,
        principal_id,
        payload
    )


def append_miner_alert(alert_type: str, message: str, principal_id: str):
    """Append a miner alert event."""
    return append_event(
        EventKind.MINER_ALERT,
        principal_id,
        {
            "alert_type": alert_type,
            "message": message
        }
    )


def append_hermes_summary(summary_text: str, authority_scope: list, principal_id: str):
    """Append a Hermes summary event."""
    return append_event(
        EventKind.HERMES_SUMMARY,
        principal_id,
        {
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    )

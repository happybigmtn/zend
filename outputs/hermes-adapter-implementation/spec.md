# Hermes Adapter Implementation — Specification

**Status:** Implementation Spec
**Last Updated:** 2026-03-22
**Plan:** `genesis/plans/009-hermes-adapter-implementation.md`

## Purpose

This document specifies the implementation details for the Hermes adapter module, which enables an AI agent (Hermes) to connect to the Zend daemon with scoped capabilities. Hermes can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages.

## Architecture Context

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ← THIS IS WHAT WE BUILD
      |
      v
Zend Gateway Contract → Event Spine
```

The adapter is a Python module (`hermes.py`) in the daemon, not a separate service. It enforces capability boundaries by filtering requests before they reach the event spine.

## Capability Model

### Hermes Capabilities (Milestone 1)
```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

| Capability | Description |
|------------|-------------|
| `observe`  | Read miner status through adapter |
| `summarize`| Append summaries to the event spine |

### Forbidden Capabilities
- `control` — Hermes CANNOT issue miner control commands
- Gateway `observe` and `control` are distinct from Hermes `observe` and `summarize`

## Event Access Model

### Hermes-Readable Events
```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,   # Hermes's own summaries
    EventKind.MINER_ALERT,      # Alerts Hermes may have generated
    EventKind.CONTROL_RECEIPT,  # Recent control actions (audit trail)
]
```

### Blocked Events
- `user_message` — Hermes CANNOT read user messages (privacy boundary)

## Authority Token Schema

The authority token is issued during Hermes pairing. It encodes:

| Field | Type | Description |
|-------|------|-------------|
| `principal_id` | string | Zend principal identifier |
| `hermes_id` | string | Unique Hermes agent identifier |
| `capabilities` | list[str] | Granted capabilities (`observe`, `summarize`) |
| `expires_at` | string | ISO 8601 expiration timestamp |

## Module Interface

### `services/home-miner-daemon/hermes.py`

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str

HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

def connect(authority_token: str) -> HermesConnection:
    """Validate authority token and establish Hermes connection.
    Raises ValueError if token is invalid, expired, or has wrong capabilities."""

def read_status(connection: HermesConnection) -> dict:
    """Read miner status through adapter. Requires observe capability."""
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")

def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> None:
    """Append a Hermes summary to the event spine. Requires summarize capability."""
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")

def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """Return events Hermes is allowed to see. Filters out user_message."""

def pair_hermes(hermes_id: str, device_name: str) -> HermesConnection:
    """Create or update Hermes pairing record with observe+summarize capabilities."""
```

## Daemon Endpoints

### `POST /hermes/connect`
Accepts authority token, returns connection status.

**Request:**
```json
{
  "authority_token": "eyJ..."
}
```

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "principal_id": "...",
  "capabilities": ["observe", "summarize"],
  "connected_at": "2026-03-22T12:00:00Z"
}
```

**Errors:**
- `401` — Invalid or expired token
- `403` — Token lacks Hermes capabilities

### `POST /hermes/pair`
Creates Hermes pairing record in store with observe+summarize capabilities.

**Request:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent"
}
```

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "capabilities": ["observe", "summarize"],
  "principal_id": "...",
  "paired_at": "2026-03-22T12:00:00Z",
  "authority_token": "eyJ..."
}
```

### `GET /hermes/status`
Read miner status through adapter (requires Hermes auth).

**Headers:**
```
Authorization: Hermes <hermes_id>
```

**Response:**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00Z"
}
```

**Errors:**
- `403` — Hermes lacks observe capability

### `POST /hermes/summary`
Append a summary to the spine (requires Hermes auth).

**Headers:**
```
Authorization: Hermes <hermes_id>
Content-Type: application/json
```

**Request:**
```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": "observe"
}
```

**Response:**
```json
{
  "appended": true,
  "event_id": "uuid-here"
}
```

**Errors:**
- `403` — Hermes lacks summarize capability

### `GET /hermes/events`
Read filtered events (no user_message).

**Headers:**
```
Authorization: Hermes <hermes_id>
```

**Response:**
```json
{
  "events": [
    {
      "id": "...",
      "kind": "hermes_summary",
      "payload": {"summary_text": "...", "authority_scope": "observe", "generated_at": "..."},
      "created_at": "2026-03-22T12:00:00Z"
    }
  ]
}
```

## Capability Boundary Enforcement

### Control Commands (Forbidden)
```bash
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Expected: 403 HERMES_UNAUTHORIZED
```

### Event Filtering
```bash
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001"
# user_message events are NOT present in response
```

## Data Flow

1. **Pairing**: `POST /hermes/pair` creates pairing record with `observe` + `summarize` capabilities
2. **Token Generation**: Authority token issued encoding principal_id, hermes_id, capabilities, expiration
3. **Connection**: `POST /hermes/connect` validates token and returns HermesConnection
4. **Observation**: `GET /hermes/status` reads miner snapshot (observe capability)
5. **Summarization**: `POST /hermes/summary` appends hermes_summary event (summarize capability)
6. **Audit Trail**: `GET /hermes/events` returns filtered events (user_message blocked)

## Idempotence

- Hermes pairing is idempotent (same hermes_id re-pairs)
- Summary append is append-only
- All operations can be safely repeated

## Acceptance Criteria

1. Hermes can connect with valid authority token
2. Hermes can read miner status (observe capability)
3. Hermes can append summaries to event spine (summarize capability)
4. Hermes CANNOT issue control commands (403 rejection)
5. Hermes CANNOT read user_message events (filtered)
6. All daemon endpoints return appropriate HTTP status codes
7. Authority token validation enforces expiration

## File Locations

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Hermes adapter module |
| `services/home-miner-daemon/daemon.py` | Daemon endpoints (modified) |
| `services/home-miner-daemon/cli.py` | CLI with Hermes subcommands (modified) |
| `state/pairing-store.json` | Hermes pairing records |
| `state/event-spine.jsonl` | Event journal |

## Dependencies

- Python 3.10+
- Standard library: `json`, `uuid`, `datetime`, `socketserver`, `http.server`
- Internal: `spine.py`, `store.py`

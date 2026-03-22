# Hermes Adapter Implementation Specification

**Status:** ✅ Implemented  
**Created:** 2026-03-22  
**Plan Reference:** genesis/plans/009-hermes-adapter-implementation.md

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| hermes.py adapter module | ✅ Complete | `services/home-miner-daemon/hermes.py` |
| HermesConnection | ✅ Complete | `services/home-miner-daemon/hermes.py` |
| read_status() | ✅ Complete | `services/home-miner-daemon/hermes.py` |
| append_summary() | ✅ Complete | `services/home-miner-daemon/hermes.py` |
| Event filtering | ✅ Complete | `services/home-miner-daemon/hermes.py` |
| Daemon endpoints | ✅ Complete | `services/home-miner-daemon/daemon.py` |
| CLI subcommands | ✅ Complete | `services/home-miner-daemon/cli.py` |
| Tests | ✅ Complete (17 tests) | `services/home-miner-daemon/tests/test_hermes.py` |
| Smoke test | ✅ Complete | `scripts/hermes_summary_smoke.sh` |

## Purpose

This specification defines the implementation contract for the Hermes Adapter, which enables an AI agent (Hermes) to connect to the Zend daemon through a scoped adapter. The adapter enforces capability boundaries: Hermes can read miner status and append summaries, but cannot issue control commands or read user messages.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
```

The adapter sits between the external Hermes agent and the internal gateway contract, enforcing:

1. **Token validation** — Authority tokens with principal_id, hermes_id, capabilities, expiration
2. **Capability checking** — Only 'observe' and 'summarize', never 'control'
3. **Event filtering** — Blocks user_message events from Hermes reads
4. **Payload transformation** — Strips fields Hermes shouldn't see

## Module: `hermes.py`

**Location:** `services/home-miner-daemon/hermes.py`

### Data Structures

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
    authority_scope: str  # 'observe' or 'observe+summarize'
```

### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

### Functions

#### `connect(authority_token: str) -> HermesConnection`

Validates an authority token and establishes a Hermes connection.

**Token Format:** Base64-encoded JSON containing:
- `hermes_id`: Unique Hermes identifier
- `principal_id`: Owner's principal ID
- `capabilities`: List of granted capabilities
- `expires_at`: ISO 8601 expiration timestamp

**Raises:**
- `ValueError` — If token structure is invalid
- `PermissionError` — If token is expired or lacks Hermes capabilities

#### `read_status(connection: HermesConnection) -> dict`

Returns current miner status snapshot.

**Requires:** 'observe' capability in connection.capabilities

**Returns:** Same dict as `MinerSimulator.get_snapshot()`

#### `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent`

Appends a Hermes summary to the event spine.

**Requires:** 'summarize' capability in connection.capabilities

**Returns:** The created SpineEvent

#### `get_filtered_events(connection: HermesConnection, limit: int = 20) -> list`

Returns events Hermes is allowed to see, filtering out user_message.

**Returns:** List of SpineEvent objects, max `limit` items

## Endpoints

### `POST /hermes/connect`

Accepts authority token, returns HermesConnection.

**Request:**
```json
{
  "authority_token": "eyJoZXJtZXNfaWQiOiAiaGVybWVzLTAwMSJ9..."
}
```

**Response (200):**
```json
{
  "hermes_id": "hermes-001",
  "principal_id": "...",
  "capabilities": ["observe", "summarize"],
  "connected_at": "2026-03-22T10:00:00Z",
  "authority_scope": "observe+summarize"
}
```

**Error (401):**
```json
{
  "error": "HERMES_UNAUTHORIZED",
  "message": "Invalid or expired authority token"
}
```

### `POST /hermes/pair`

Creates a Hermes pairing record.

**Request:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent"
}
```

**Response (200):**
```json
{
  "hermes_id": "hermes-001",
  "capabilities": ["observe", "summarize"],
  "paired_at": "2026-03-22T10:00:00Z",
  "token": "uuid-for-initial-token"
}
```

### `GET /hermes/status`

Read miner status through adapter (requires Hermes auth).

**Headers:** `Authorization: Hermes <hermes_id>`

**Response (200):**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T10:00:00Z"
}
```

**Error (403):**
```json
{
  "error": "HERMES_UNAUTHORIZED",
  "message": "observe capability required"
}
```

### `POST /hermes/summary`

Append a Hermes summary to the spine.

**Headers:** `Authorization: Hermes <hermes_id>`

**Request:**
```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": "observe"
}
```

**Response (200):**
```json
{
  "appended": true,
  "event_id": "uuid"
}
```

### `GET /hermes/events`

Read filtered events (no user_message).

**Headers:** `Authorization: Hermes <hermes_id>`

**Response (200):**
```json
{
  "events": [
    {
      "id": "uuid",
      "kind": "hermes_summary",
      "payload": {...},
      "created_at": "..."
    }
  ]
}
```

## Auth Model

Hermes uses a separate auth header scheme to distinguish from gateway device auth:

```
Authorization: Hermes <hermes_id>
```

The daemon maintains a Hermes connection session after initial `connect` or `pair`.

## Capability Boundaries (Milestone 1)

**Hermes CAN:**
- Connect with authority token
- Read miner status (observe)
- Append summaries to event spine (summarize)
- Read filtered events (hermes_summary, miner_alert, control_receipt)

**Hermes CANNOT:**
- Issue control commands (/miner/start, /miner/stop)
- Read user_message events
- Modify miner configuration
- Access inbox messages

## Acceptance Criteria

1. `connect()` accepts valid tokens and raises for expired/invalid
2. `read_status()` returns miner snapshot for observe-capable Hermes
3. `append_summary()` creates hermes_summary events in spine
4. `get_filtered_events()` excludes user_message events
5. All daemon endpoints return correct HTTP status codes
6. Control attempts return 403 HERMES_UNAUTHORIZED
7. All tests pass: `python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v`

## Test Cases

1. `test_hermes_connect_valid` — connect with valid token succeeds
2. `test_hermes_connect_expired` — connect with expired token fails
3. `test_hermes_read_status` — observe capability reads status
4. `test_hermes_append_summary` — summarize capability appends to spine
5. `test_hermes_no_control` — Hermes cannot call /miner/start
6. `test_hermes_event_filter` — user_message events not returned
7. `test_hermes_invalid_capability` — requesting control capability rejected
8. `test_hermes_summary_appears_in_inbox` — appended summary visible via /spine/events

## Files to Create/Modify

### New Files
- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/tests/test_hermes.py` — Adapter tests

### Modified Files
- `services/home-miner-daemon/daemon.py` — Add Hermes endpoints
- `services/home-miner-daemon/cli.py` — Add Hermes subcommands
- `apps/zend-home-gateway/index.html` — Update Agent tab

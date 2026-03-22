# Hermes Adapter Implementation Specification

**Status:** Implemented
**Date:** 2026-03-22
**Plan Reference:** `genesis/plans/009-hermes-adapter-implementation.md`

## Purpose

This specification documents the implementation of the Hermes Adapter, which provides a capability boundary between the Hermes AI agent and the Zend gateway contract. The adapter enables Hermes to observe miner status and append summaries while enforcing strict boundaries that prevent control commands and user message access.

## Architecture

```
Hermes Gateway
      |
      v
Hermes Adapter (hermes.py)
      |
      +-- connect() - validates authority token
      +-- read_status() - observes miner status
      +-- append_summary() - appends to event spine
      +-- get_filtered_events() - reads filtered events
      |
      v
Zend Gateway Contract
      |
      v
Event Spine
```

## Implementation Details

### Module Structure

**File:** `services/home-miner-daemon/hermes.py`

#### Constants
```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
HERMES_BLOCKED_EVENTS = [
    EventKind.USER_MESSAGE,
]
```

#### Data Classes

**HermesConnection**
```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
```

**HermesPairing**
```python
@dataclass
class HermesPairing:
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
```

### Core Functions

#### `pair_hermes(hermes_id, device_name)`
Creates or updates a Hermes pairing with observe and summarize capabilities. Idempotent operation.

**Parameters:**
- `hermes_id`: Unique identifier for the Hermes agent
- `device_name`: Human-readable name for the Hermes device

**Returns:** `HermesPairing` record

**Raises:** `ValueError` if hermes_id or device_name is empty

#### `connect(authority_token)`
Validates authority token and establishes Hermes connection.

**Parameters:**
- `authority_token`: The authority token issued during pairing

**Returns:** `HermesConnection` with validated capabilities

**Raises:** `ValueError` if token is invalid, expired, or has wrong capabilities

#### `read_status(connection)`
Reads miner status through the adapter. Requires observe capability.

**Parameters:**
- `connection`: Active HermesConnection

**Returns:** Miner snapshot dict with status, mode, hashrate, etc.

**Raises:** `PermissionError` if connection lacks observe capability

#### `append_summary(connection, summary_text, authority_scope)`
Appends a Hermes summary to the event spine. Requires summarize capability.

**Parameters:**
- `connection`: Active HermesConnection
- `summary_text`: The summary content to append
- `authority_scope`: The scope of observation that generated this summary

**Returns:** The appended `SpineEvent`

**Raises:** `PermissionError` if connection lacks summarize capability

#### `get_filtered_events(connection, limit=20)`
Returns events Hermes is allowed to see. Filters out user_message events.

**Parameters:**
- `connection`: Active HermesConnection
- `limit`: Maximum number of events to return

**Returns:** List of filtered `SpineEvent` objects

### Daemon Endpoints

**File:** `services/home-miner-daemon/daemon.py`

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/hermes/pair` | POST | Create/update Hermes pairing | None |
| `/hermes/connect` | POST | Connect with authority token | Token |
| `/hermes/disconnect` | POST | Disconnect Hermes session | Hermes ID |
| `/hermes/status` | GET | Read miner status | Hermes ID |
| `/hermes/summary` | POST | Append summary | Hermes ID |
| `/hermes/events` | GET | Get filtered events | Hermes ID |
| `/hermes/connection` | GET | Get connection state | Hermes ID |

### CLI Commands

**File:** `services/home-miner-daemon/cli.py`

```bash
# Pair Hermes
python cli.py hermes pair --hermes-id <id> --device-name <name>

# Connect Hermes
python cli.py hermes connect --token <token>

# Read status as Hermes
python cli.py hermes status --token <token>

# Append summary
python cli.py hermes summary --token <token> --summary "Miner running normally"

# Get filtered events
python cli.py hermes events --token <token> --limit 20

# Run proof of implementation
python cli.py hermes test
```

### Capability Enforcement

#### Observe Capability
- Grants access to `read_status()` function
- Allows reading miner snapshots
- Required for `/hermes/status` endpoint

#### Summarize Capability
- Grants access to `append_summary()` function
- Allows appending Hermes summaries to event spine
- Required for `/hermes/summary` endpoint

#### Control Denial
- Hermes CANNOT have `control` capability
- Any control attempt is logged and denied
- Returns `HERMES_UNAUTHORIZED` error

### Event Filtering

Hermes is blocked from reading:
- `user_message` events (private messages)

Hermes can read:
- `hermes_summary` events (own summaries)
- `miner_alert` events (alerts)
- `control_receipt` events (recent actions)

### Gateway Client Integration

**File:** `apps/zend-home-gateway/index.html`

The Agent tab in the gateway client now includes:
- Hermes connection form with token input
- Real-time connection state display
- Capability pills showing observe and summarize
- Recent Hermes summaries from event spine
- Add summary form for connected Hermes
- Persistent connection state (saved to localStorage)

## Observability

The adapter emits structured log events per `references/observability.md`:

| Event | Fields | Trigger |
|-------|--------|---------|
| `gateway.hermes.paired` | hermes_id, device_name, capabilities | Pairing completes |
| `gateway.hermes.connected` | hermes_id, capabilities | Connection established |
| `gateway.hermes.unauthorized` | action, reason, hermes_id | Authorization failure |
| `gateway.hermes.summary_appended` | summary_id, hermes_id | Summary appended |
| `gateway.status.read` | client, hermes_id, freshness | Status read |

## Acceptance Criteria

1. ✅ Hermes can pair with the gateway and receive authority token
2. ✅ Hermes can connect using valid authority token
3. ✅ Hermes can read miner status with observe capability
4. ✅ Hermes can append summaries to event spine with summarize capability
5. ✅ Hermes CANNOT issue control commands (always denied)
6. ✅ Hermes CANNOT read user_message events (filtered)
7. ✅ Hermes connection state visible in gateway client Agent tab
8. ✅ All tests pass: 8 test cases validated

## Test Coverage

**File:** `services/home-miner-daemon/tests/test_hermes.py`

| Test | Description |
|------|-------------|
| `test_hermes_connect_valid` | Connect with valid token succeeds |
| `test_hermes_connect_invalid` | Connect with invalid token fails |
| `test_hermes_read_status` | Observe capability reads status |
| `test_hermes_read_status_no_observe` | Missing observe raises PermissionError |
| `test_hermes_append_summary` | Summarize capability appends to spine |
| `test_hermes_append_summary_no_summarize` | Missing summarize raises PermissionError |
| `test_hermes_event_filter_blocks_user_message` | user_message events not returned |
| `test_hermes_event_filter_includes_readable_events` | Readable events included |
| `test_hermes_has_no_control_capability` | Hermes capabilities are observe+summarize only |
| `test_hermes_control_denied` | Control attempts always denied |
| `test_summary_appears_in_inbox` | Appended summary visible via spine |

## Dependencies

- `services/home-miner-daemon/spine.py` - Event spine operations
- `services/home-miner-daemon/store.py` - Principal and pairing store
- `services/home-miner-daemon/daemon.py` - HTTP endpoints

## Non-Goals (Out of Scope)

- Direct miner control from Hermes (not in milestone 1)
- Inbox message composition by Hermes
- Payout target mutation
- Remote internet access (LAN-only milestone)

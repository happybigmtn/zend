# Architecture

This document describes Zend's system design, module structure, and data flow.
It enables an engineer to understand the codebase and predict how new features
would be implemented.

## System Overview

Zend is a LAN-only control system with three main components:

```
  Mobile Client (HTML + JS)
           |
           | HTTP API
           v
   Home Miner Daemon
           |
           +--> Event Spine (JSONL)
           +--> Pairing Store
           +--> Principal Store
           +--> Miner Simulator
           +--> Hermes Adapter
```

### Design Principles

1. **LAN-only by default**: No internet-facing control surfaces
2. **Stdlib-only Python**: No external dependencies
3. **Append-only events**: The event spine is the source of truth
4. **Capability-scoped authority**: Observe or control, never both by default
5. **Single HTML client**: No build step required

## Module Guide

### `daemon.py` — HTTP API Server

**Location:** `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP server that exposes miner control endpoints.

**Key Components:**

- `MinerSimulator`: Simulates a home miner with status, mode, and hash rate
- `GatewayHandler`: HTTP request handler for `/health`, `/status`, `/miner/*`
- `ThreadedHTTPServer`: Threaded HTTP server for concurrent requests

**Endpoints:**

| Path | Handler | Description |
|------|---------|-------------|
| `GET /health` | `do_GET` | Daemon health check |
| `GET /status` | `do_GET` | Miner status snapshot |
| `POST /miner/start` | `do_POST` | Start mining |
| `POST /miner/stop` | `do_POST` | Stop mining |
| `POST /miner/set_mode` | `do_POST` | Change mode |

**State:**

```python
miner = MinerSimulator()  # Global instance
```

**Adding a New Endpoint:**

1. Add method check in `do_GET` or `do_POST`
2. Implement handler logic
3. Return JSON response via `_send_json()`

Example:

```python
def do_GET(self):
    if self.path == '/health':
        self._send_json(200, miner.health)
    elif self.path == '/custom':
        # Your new endpoint
        self._send_json(200, {"custom": "data"})
    else:
        self._send_json(404, {"error": "not_found"})
```

### `cli.py` — Command-Line Interface

**Location:** `services/home-miner-daemon/cli.py`

**Purpose:** High-level CLI for pairing, status, and control commands.

**Key Commands:**

| Command | Description |
|---------|-------------|
| `health` | Check daemon health |
| `status` | Read miner status |
| `bootstrap` | Create principal and initial pairing |
| `pair` | Pair a new client |
| `control` | Issue control command |
| `events` | List events from spine |

**Key Functions:**

- `daemon_call()`: Make HTTP request to daemon
- `has_capability()`: Check if client has capability
- `cmd_*()`: Individual command handlers

**Authorization Flow:**

```
CLI command
    |
    v
has_capability(client, action)
    |
    +--> No capability --> Print error, exit 1
    |
    v
daemon_call() --> Daemon
    |
    v
spine.append_*() --> Event Spine
```

### `spine.py` — Event Spine

**Location:** `services/home-miner-daemon/spine.py`

**Purpose:** Append-only encrypted event journal.

**Event Kinds:**

| Kind | Trigger |
|------|---------|
| `pairing_requested` | Client requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Permissions removed |
| `miner_alert` | Miner warning/error |
| `control_receipt` | Control command result |
| `hermes_summary` | Hermes agent activity |
| `user_message` | Future inbox messages |

**Data Model:**

```python
@dataclass
class SpineEvent:
    id: str              # UUID v4
    principal_id: str     # Owner's identity
    kind: str            # EventKind enum value
    payload: dict        # Encrypted payload
    created_at: str      # ISO 8601
    version: int         # Schema version (1)
```

**Storage:** `state/event-spine.jsonl`

Each event is one JSON line. New events append to the end.

**Key Functions:**

- `append_event()`: Append event to spine
- `get_events()`: Query events with optional filter
- `append_pairing_*()`: Convenience for pairing events
- `append_control_receipt()`: Record command outcome

**Adding a New Event Kind:**

1. Add to `EventKind` enum:

```python
class EventKind(str, Enum):
    # ... existing kinds ...
    NEW_EVENT = "new_event"
```

2. Add append helper:

```python
def append_new_event(data: dict, principal_id: str):
    return append_event(
        EventKind.NEW_EVENT,
        principal_id,
        data
    )
```

### `store.py` — Principal and Pairing

**Location:** `services/home-miner-daemon/store.py`

**Purpose:** Persistent storage for identity and device pairings.

**Data Models:**

```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str   # ISO 8601
    name: str         # Human-readable name

@dataclass
class GatewayPairing:
    id: str               # UUID v4
    principal_id: str      # References Principal
    device_name: str       # Client identifier
    capabilities: list      # ['observe', 'control']
    paired_at: str         # ISO 8601
    token_expires_at: str  # ISO 8601
    token_used: bool       # Replay prevention
```

**Storage:**

- `state/principal.json`: Single principal record
- `state/pairing-store.json`: Dictionary of pairings

**Key Functions:**

- `load_or_create_principal()`: Get or create identity
- `pair_client()`: Create new pairing record
- `get_pairing_by_device()`: Look up device
- `has_capability()`: Check permissions

**Authorization Check:**

```python
def has_capability(device_name: str, capability: str) -> bool:
    pairing = get_pairing_by_device(device_name)
    if not pairing:
        return False
    return capability in pairing.capabilities
```

## Data Flow

### Control Command Flow

```
User clicks "Start Mining"
           |
           v
CLI: cmd_control('start')
           |
           v
has_capability('alice-phone', 'control')
           |
           +--> False: Print error, exit
           |
           v
daemon_call('POST', '/miner/start')
           |
           v
Daemon: miner.start()
           |
           v
Return {"success": true, "status": "running"}
           |
           v
spine.append_control_receipt('start', None, 'accepted', principal.id)
           |
           v
Print confirmation
```

### Status Read Flow

```
CLI: cmd_status('alice-phone')
           |
           v
has_capability('alice-phone', 'observe')
           |
           +--> False: Print error, exit
           |
           v
daemon_call('GET', '/status')
           |
           v
Daemon: miner.get_snapshot()
           |
           v
Return snapshot with freshness timestamp
```

## Auth Model

### Principal Identity

Every deployment has one `Principal` with a stable UUID. This identity:
- Owns all pairing records
- Tags all event spine entries
- Will span future inbox access

### Capability Scopes

| Capability | Permissions |
|------------|-------------|
| `observe` | Read status, list events |
| `control` | Issue commands (implies observe) |

### Pairing Flow

```
Pairing Request
    |
    v
CLI: pair_client('my-phone', ['observe', 'control'])
    |
    v
store.pair_client()
    |
    v
Create pairing record with token
    |
    v
spine.append_pairing_requested()
spine.append_pairing_granted()
    |
    v
Return pairing confirmation
```

### Token Replay Prevention

Each pairing has a `token_used` flag. Reusing a consumed token fails:

```python
if pairing.token_used:
    raise ValueError("Pairing token already consumed")
```

## Event Spine Design

### Append-Only Guarantee

The spine is append-only. Events are never modified or deleted. This ensures:

1. Complete audit trail
2. Replay capability
3. Inbox projection correctness

### Inbox as Projection

The inbox is a derived view of the spine:

```
Event Spine (source of truth)
    |
    +--> Filter by kind
    |
    +--> Sort by timestamp
    |
    v
Inbox View (projection)
```

### Payload Encryption

Payloads are stored as dictionaries in milestone 1. Future versions will
encrypt using the principal's identity key.

## Hermes Adapter

The Hermes adapter connects Hermes Gateway to the Zend gateway contract.

### Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter
      |
      +--> readStatus()     (if observe granted)
      +--> appendSummary()  (if summarize granted)
      |
      v
Event Spine
```

### Milestone 1 Boundaries

- **Can do:** Read miner status, append summaries
- **Cannot do:** Control miner, change payout targets

## Design Decisions

### Why Stdlib-Only?

- No dependency hell
- Works on bare Python installations
- Easier to audit and verify
- Portable across all Python platforms

### Why LAN-Only?

- Lower blast radius for milestone 1
- Simpler security model
- No cloud infrastructure needed
- Trust boundary stays on local network

### Why JSONL?

- Append-only friendly
- Human-readable for debugging
- No database dependency
- Easy to backup and inspect

### Why Single HTML File?

- No build step required
- Works from `file://` protocol
- Easy to distribute and share
- Portable across devices

### Why No Auth at HTTP Layer?

- LAN-only assumption (trusted network)
- Simplicity for milestone 1
- Auth at CLI layer is sufficient
- Future: token-based auth at HTTP layer

## Failure Handling

### Daemon Unavailable

CLI detects and reports:

```json
{"error": "daemon_unavailable", "details": "Connection refused"}
```

### Unauthorized Action

CLI checks capability before calling daemon:

```json
{"success": false, "error": "unauthorized", "message": "This device lacks 'control' capability"}
```

### Stale Status

Daemon returns freshness timestamp:

```json
{"freshness": "2026-03-22T11:00:00Z"}  // Old timestamp signals stale data
```

### Control Conflict

Miner simulator rejects conflicting commands:

```json
{"success": false, "error": "already_running"}
```

## Observability

### Structured Log Events

The system emits these events (see `references/observability.md`):

| Event | Trigger |
|-------|---------|
| `gateway.bootstrap.started` | Bootstrap script runs |
| `gateway.pairing.succeeded` | Client pairs |
| `gateway.status.read` | Status endpoint called |
| `gateway.control.accepted` | Command succeeds |
| `gateway.inbox.appended` | Event written to spine |

### Metrics

| Metric | Labels |
|--------|--------|
| `gateway_pairing_attempts_total` | outcome |
| `gateway_status_reads_total` | freshness |
| `gateway_control_commands_total` | outcome |

## Extension Points

### Adding a New Endpoint

1. Add route in `daemon.py` `do_GET` or `do_POST`
2. Add CLI command in `cli.py`
3. Add event append if needed in `spine.py`
4. Add documentation

### Adding a New Event Kind

1. Add to `EventKind` enum in `spine.py`
2. Add payload schema in `references/event-spine.md`
3. Add append helper function
4. Add to inbox routing

### Adding a New Capability

1. Add to `GatewayCapability` type in `references/inbox-contract.md`
2. Update `has_capability()` checks
3. Update CLI authorization
4. Document in API reference

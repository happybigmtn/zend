# Architecture

This document describes the Zend system architecture, module relationships, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Zend System                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐                                                        │
│  │   Phone     │◄───────── Browser (HTML/JS)                            │
│  │             │         /apps/zend-home-gateway/                        │
│  └──────┬──────┘                                                        │
│         │                                                                │
│         │ fetch() / POST()                                               │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Home Miner Daemon                             │   │
│  │                   (services/home-miner-daemon/)                   │   │
│  │                                                                   │   │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │   │
│  │   │  daemon.py  │    │   cli.py    │    │   spine.py      │    │   │
│  │   │  HTTP API   │    │  Commands   │    │  Event Journal  │    │   │
│  │   │  :8080      │───►│             │───►│                 │    │   │
│  │   └─────────────┘    └─────────────┘    └────────┬────────┘    │   │
│  │          │                                      │              │   │
│  │          │                                      │              │   │
│  │          ▼                                      ▼              │   │
│  │   ┌─────────────┐                       ┌───────────────┐      │   │
│  │   │   Miner     │                       │   JSONL       │      │   │
│  │   │  Simulator  │                       │   File        │      │   │
│  │   │  (in-memory)│                       │ state/        │      │   │
│  │   └─────────────┘                       └───────────────┘      │   │
│  │                                                                   │   │
│  │   ┌─────────────┐    ┌─────────────────────────────────────┐   │   │
│  │   │  store.py   │◄───│  state/principal.json               │   │   │
│  │   │  Pairing &  │    │  state/pairing-store.json           │   │   │
│  │   │  Principal  │    └─────────────────────────────────────┘   │   │
│  │   └─────────────┘                                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### daemon.py — HTTP API Server

**File:** `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP server that exposes the miner control API.

**Key Components:**

| Component | Type | Description |
|-----------|------|-------------|
| `MinerSimulator` | Class | In-memory miner state machine |
| `GatewayHandler` | Class | HTTP request handler |
| `ThreadedHTTPServer` | Class | Concurrent request handler |
| `MinerMode` | Enum | `PAUSED`, `BALANCED`, `PERFORMANCE` |
| `MinerStatus` | Enum | `RUNNING`, `STOPPED`, `OFFLINE`, `ERROR` |

**Key Functions:**

```python
def run_server(host: str = BIND_HOST, port: int = BIND_PORT)
    """Start the daemon. Blocks until KeyboardInterrupt."""

def default_state_dir() -> str
    """Resolve state directory relative to repo root."""
```

**State:**

- Miner status (status, mode, hashrate, temperature, uptime)
- All state is in-memory (no persistence for miner state)

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `../state` | State directory path |
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind address |
| `ZEND_BIND_PORT` | `8080` | Bind port |

---

### cli.py — Command-Line Interface

**File:** `services/home-miner-daemon/cli.py`

**Purpose:** CLI tool for interacting with the daemon.

**Commands:**

| Command | Description |
|---------|-------------|
| `health` | Get daemon health |
| `status` | Get miner status |
| `events` | Query event spine |
| `control` | Control miner (start/stop/set_mode) |
| `bootstrap` | Create principal and initial pairing |
| `pair` | Pair a new device |

**Key Functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict
    """Make HTTP call to daemon."""

def cmd_status(args) -> int
def cmd_control(args) -> int
def cmd_events(args) -> int
# etc.
```

**State:**

- No persistent state (stateless CLI)
- Reads/writes via daemon HTTP API

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon base URL |

---

### spine.py — Event Spine

**File:** `services/home-miner-daemon/spine.py`

**Purpose:** Append-only event journal for receipts and operational history.

**Key Components:**

| Component | Type | Description |
|-----------|------|-------------|
| `SpineEvent` | Dataclass | Event record |
| `EventKind` | Enum | Event type identifiers |
| `SPINE_FILE` | Path | JSONL file path |

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
    """Append event to spine. Returns the created event."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]
    """Query events. Most recent first."""

def append_pairing_granted(device_name: str, capabilities: list, principal_id: str)
def append_control_receipt(command: str, mode: Optional[str], status: str, principal_id: str)
# etc.
```

**Event Kinds:**

| Kind | Trigger |
|------|---------|
| `pairing_requested` | Device requests pairing |
| `pairing_granted` | Pairing created |
| `capability_revoked` | Permission removed |
| `miner_alert` | Miner generates alert |
| `control_receipt` | Control command executed |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message received |

**Storage Format:**

Each event is one JSON object per line (JSONL):
```
{"id": "...", "principal_id": "...", "kind": "...", "payload": {...}, "created_at": "...", "version": 1}
{"id": "...", "principal_id": "...", "kind": "...", "payload": {...}, "created_at": "...", "version": 1}
```

**State:** `state/event-spine.jsonl`

**Access:** The event spine is queried via CLI only (`cli.py events` command). HTTP access to the spine is planned for milestone 2.

---

### store.py — Principal and Pairing Store

**File:** `services/home-miner-daemon/store.py`

**Purpose:** Manages principal identity and device pairings.

**Key Components:**

| Component | Type | Description |
|-----------|------|-------------|
| `Principal` | Dataclass | Home principal identity |
| `GatewayPairing` | Dataclass | Paired device record |

**Key Functions:**

```python
def load_or_create_principal() -> Principal
    """Get existing principal or create new one."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing
    """Create new pairing. Raises ValueError if device already paired."""

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
    """Get pairing record by device name."""

def has_capability(device_name: str, capability: str) -> bool
    """Check if device has specific capability."""

def list_devices() -> list[GatewayPairing]
    """List all paired devices."""
```

**State Files:**

| File | Content |
|------|---------|
| `state/principal.json` | Single principal identity |
| `state/pairing-store.json` | All pairing records |

---

## Data Flow

### Control Command Flow

```
1. Phone Browser
   └── User clicks "Start" in index.html

2. Command Center (JavaScript)
   └── fetch('http://daemon:8080/miner/start', {method: 'POST'})

3. Home Miner Daemon (daemon.py)
   └── GatewayHandler.do_POST() receives request
   └── MinerSimulator.start() called
   └── Miner state updated (status = RUNNING)
   └── Response: {"success": true, "status": "running"}

4. Command Center (JavaScript)
   └── Response received
   └── UI updated (status indicator turns green)
   └── CLI also logs receipt (via spine.append_control_receipt)

5. Event Spine (spine.py)
   └── control_receipt event appended to JSONL
   └── Contains: command, mode, status, receipt_id
```

### Status Query Flow

```
1. Phone Browser
   └── index.html loads, calls fetchStatus()

2. Command Center (JavaScript)
   └── fetch('http://daemon:8080/status')

3. Home Miner Daemon (daemon.py)
   └── GatewayHandler.do_GET() receives request
   └── MinerSimulator.get_snapshot() called
   └── Current state returned as JSON

4. Command Center (JavaScript)
   └── Response parsed
   └── UI elements updated (status, mode, hashrate)
```

### Bootstrap Flow

```
1. Operator runs bootstrap script
   └── ./scripts/bootstrap_home_miner.sh

2. Bootstrap Script
   └── Starts daemon.py in background
   └── Waits for /health to respond
   └── Calls cli.py bootstrap command

3. CLI (cli.py)
   └── load_or_create_principal() creates identity
   └── pair_client() creates initial pairing
   └── append_pairing_granted() logs to spine

4. State Files Created
   └── state/principal.json
   └── state/pairing-store.json
   └── state/event-spine.jsonl
```

## Auth Model

### Principal

The principal is the home identity. Currently, there is one principal per deployment. Future versions may support multiple principals (e.g., multiple adults in a household).

**Principal fields:**
- `id`: UUID, unique identifier
- `created_at`: ISO 8601 timestamp
- `name`: Human-readable name ("Zend Home")

### Pairing

Pairing links a device to a principal with specific capabilities.

**Pairing fields:**
- `id`: UUID, unique identifier
- `principal_id`: Links to principal
- `device_name`: Human-readable device identifier
- `capabilities`: List of granted capabilities
- `paired_at`: ISO 8601 timestamp
- `token_expires_at`: Token expiration (future use)
- `token_used`: Token usage flag (future use)

### Capabilities

| Capability | Grants Access To |
|------------|-----------------|
| `observe` | View status, query events |
| `control` | Start/stop miner, change mode |

### Capability Flow

```
Device requests pairing with capabilities: [observe, control]
    ↓
Principal approves (or system auto-approves in milestone 1)
    ↓
Pairing created with granted capabilities
    ↓
Device makes request with device_name in header/param
    ↓
has_capability() checks pairing record
    ↓
Request allowed or rejected
```

## Design Decisions

### Why Standard Library Only?

**Decision:** No external Python dependencies.

**Rationale:**
- Zero install friction
- Compatible with any Python 3.10+ environment
- No dependency conflicts
- Auditable code (no hidden implementations)
- Easier deployment on constrained hardware

**Trade-offs:**
- More code to write (no Flask, no Pydantic)
- Less validation framework
- Manual JSON handling

### Why LAN-Only?

**Decision:** Daemon binds to local network, not public internet.

**Rationale:**
- Attack surface minimized
- No authentication required for local devices
- Phone and miner are on same trust boundary
- Privacy preserved locally

**Trade-offs:**
- Remote access requires VPN or tunneling
- No cloud management in milestone 1

### Why JSONL for Event Spine?

**Decision:** Append-only JSON lines file, not SQLite or PostgreSQL.

**Rationale:**
- Simple (file + jq)
- Crash-safe (append only)
- No database server needed
- Easy backup (just copy the file)
- Human-readable

**Trade-offs:**
- No indexing (slow for large datasets)
- No transactions
- No concurrent write safety

**Note:** For milestone 1, this is sufficient. Future versions may migrate to a proper database if needed.

### Why Single HTML File?

**Decision:** Command center is one static HTML file, no build step.

**Rationale:**
- No compilation or bundling
- Can be served from anywhere (file://, http.server, CDN)
- Easy to inspect and debug
- Simple deployment

**Trade-offs:**
- No code splitting
- No module system
- Limited offline capability (future work)

### Why Separate CLI from Daemon?

**Decision:** CLI is a separate tool that calls the HTTP API.

**Rationale:**
- Consistent API (CLI and web use same endpoints)
- Easier testing (can curl anything CLI can do)
- Network transparency (CLI can run remotely)

**Trade-offs:**
- CLI adds HTTP overhead
- More complex than direct function calls

## Future Architecture

Planned changes for milestone 2+:

1. **Spine HTTP Endpoint**: Expose event spine queries via `GET /spine/events`
2. **Hermes Integration**: Agent adapter that routes commands through encrypted channels
3. **Token Authentication**: Signed tokens for device verification
4. **Metrics Endpoint**: Prometheus-compatible metrics
5. **Inbox Service**: Derived view of event spine for UI
6. **Database Migration**: SQLite or PostgreSQL for event spine at scale

## Reading the Code

When implementing a new feature, follow this checklist:

1. **Which module owns the data?**
   - Miner state → `daemon.py`
   - Events → `spine.py`
   - Identity → `store.py`

2. **Which layer handles the request?**
   - HTTP → `daemon.py` (add to `GatewayHandler`)
   - CLI → `cli.py` (add command)
   - Both → implement in appropriate module, expose in both

3. **Does it need persistence?**
   - Yes → add to `spine.py` or `store.py`
   - No → in-memory in `daemon.py`

4. **Does it need an event?**
   - Yes → use `spine.py` append function
   - No → skip

5. **Is it user-visible?**
   - Yes → add to `index.html`
   - No → backend only

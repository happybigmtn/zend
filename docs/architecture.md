# Architecture

Deep-dive into how Zend's home miner daemon works. Read this document to understand where code changes go, how data flows, and why the system is structured this way.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Client Layer                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Zend Home Gateway (index.html)                           │  │
│  │  Mobile-first HTML5 app. No build step. Fetches /status,  │  │
│  │  POSTs to /miner/* endpoints. Renders miner state and    │  │
│  │  mode switcher. Updates via polling every 5 seconds.      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ HTTP (LAN)                        │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Home Hardware (Raspberry Pi, NAS, Server)                │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  Zend Home Miner Daemon                             │  │  │
│  │  │  Python stdlib, ThreadedHTTPServer                  │  │  │
│  │  │                                                     │  │  │
│  │  │  ┌───────────────┐  ┌────────────┐  ┌───────────┐  │  │  │
│  │  │  │ GatewayHandler│──│ MinerSim   │  │  Store    │  │  │  │
│  │  │  │ (HTTP)        │  │ (Simulator)│  │(Principal)│  │  │  │
│  │  │  └───────┬───────┘  └────────────┘  └───────────┘  │  │  │
│  │  │          │                                        │  │  │
│  │  │          ▼                                        │  │  │
│  │  │  ┌─────────────────────────────────────────────┐  │  │  │
│  │  │  │  Event Spine (append-only JSONL)            │  │  │  │
│  │  │  │  spine.append_*() called after every action │  │  │  │
│  │  │  └─────────────────────────────────────────────┘  │  │  │
│  │  │                                                     │  │  │
│  │  │  ┌───────────────┐                                │  │  │
│  │  │  │ CLI (cli.py)  │                                │  │  │
│  │  │  │ Pair, control │                                │  │  │
│  │  │  │ events, status│                                │  │  │
│  │  │  └───────────────┘                                │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Modules

### `daemon.py` — HTTP Server

**File**: `services/home-miner-daemon/daemon.py`

The daemon is a `ThreadedHTTPServer` with a `BaseHTTPRequestHandler` subclass (`GatewayHandler`).

**Key Classes**:

- `MinerSimulator`: Wraps miner state (status, mode, hashrate, temperature). Thread-safe via `threading.Lock`.
- `MinerMode` (enum): `PAUSED`, `BALANCED`, `PERFORMANCE`
- `MinerStatus` (enum): `RUNNING`, `STOPPED`, `OFFLINE`, `ERROR`

**Endpoints**:

| Method | Path | Handler |
|---|---|---|
| GET | `/health` | Returns daemon health dict |
| GET | `/status` | Returns `miner.get_snapshot()` |
| POST | `/miner/start` | Calls `miner.start()` |
| POST | `/miner/stop` | Calls `miner.stop()` |
| POST | `/miner/set_mode` | Calls `miner.set_mode(mode)` |

**Design Decisions**:

- `ThreadedHTTPServer` (not `ForkingMixIn`) for lightweight concurrency
- Stdlib only: `socketserver.ThreadingMixIn` + `http.server`
- Binds to `ZEND_BIND_HOST:ZEND_BIND_PORT` (env vars)
- All state lives in `MinerSimulator` instance (`miner` global)

### `spine.py` — Event Spine

**File**: `services/home-miner-daemon/spine.py`

The event spine is an **append-only log** backed by a JSONL file (`state/event-spine.jsonl`). Each line is one JSON object.

**Core Functions**:

```python
append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
get_events(kind: EventKind = None, limit: int = 100) -> list[SpineEvent]
```

**Specialized Appenders**:

- `append_pairing_requested(device_name, capabilities, principal_id)`
- `append_pairing_granted(device_name, capabilities, principal_id)`
- `append_control_receipt(command, mode, status, principal_id)`
- `append_miner_alert(alert_type, message, principal_id)`
- `append_hermes_summary(summary_text, authority_scope, principal_id)`

**Event Structure**:

```python
@dataclass
class SpineEvent:
    id: str           # UUID
    principal_id: str  # Principal who owns this event
    kind: str          # EventKind.value
    payload: dict      # Event-specific data
    created_at: str    # ISO 8601 UTC
    version: int       # Always 1 in milestone 1
```

**Design Decisions**:

- JSONL (not SQLite) for simplicity and portability
- Append-only: events are never deleted or modified
- Most-recent-first ordering on read
- Thread-safe via file-level locking (Python's default JSONL write is not thread-safe; for milestone 1 this is acceptable)

### `store.py` — Identity and Pairing

**File**: `services/home-miner-daemon/store.py`

Manages principal identity and device pairing records.

**Principal**: The root identity. Created once, stored in `state/principal.json`.

```python
@dataclass
class Principal:
    id: str        # UUID
    created_at: str # ISO 8601 UTC
    name: str      # "Zend Home"
```

**GatewayPairing**: A paired device with capabilities.

```python
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str           # Human-readable name
    capabilities: list          # ["observe"] or ["observe", "control"]
    paired_at: str
    token_expires_at: str
    token_used: bool
```

**Key Functions**:

```python
load_or_create_principal() -> Principal
pair_client(device_name: str, capabilities: list) -> GatewayPairing
get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
has_capability(device_name: str, capability: str) -> bool
list_devices() -> list[GatewayPairing]
```

**Design Decisions**:

- Principal is singular: one home miner has one principal
- Pairing is per-device: each phone pairs separately
- No token validation in milestone 1 (tokens are created but not checked)
- Capabilities are the security boundary

### `cli.py` — Command-Line Interface

**File**: `services/home-miner-daemon/cli.py`

The CLI wraps HTTP calls to the daemon (via `urllib.request`) and local file access (via `store` and `spine`).

**Commands**:

| Command | Action |
|---|---|
| `bootstrap` | Create principal + first pairing |
| `pair` | Pair a new device |
| `status` | Show miner status |
| `health` | Show daemon health |
| `control` | Start, stop, or set mode |
| `events` | Query the event spine |

**Authorization**: The CLI checks `has_capability()` before allowing control commands. The daemon HTTP endpoints do not enforce authorization.

**Design Decision**: Split between CLI (capability check + event spine write) and daemon (miner state mutation) reflects the intended architecture: the CLI is the "trusted client," the daemon is the "untrusted network."

## Data Flow

### Control Command Flow

```
User clicks "Start" in the browser
    │
    ▼
Browser: POST /miner/start
    │
    ▼
Daemon: GatewayHandler.do_POST()
    │
    ▼
Daemon: miner.start()
    │
    ▼
Daemon: returns {"success": true, "status": "running"}
    │
    ▼
Browser: updates status display
    │
    ▼
User runs CLI: control --client alice-phone --action start
    │
    ▼
CLI: daemon_call('POST', '/miner/start')
    │
    ▼
CLI: spine.append_control_receipt("start", None, "accepted", principal.id)
    │
    ▼
CLI: prints receipt JSON
```

### Pairing Flow

```
Operator runs: cli.py bootstrap --device alice-phone
    │
    ▼
CLI: store.load_or_create_principal()
    │
    ▼
CLI: store.pair_client("alice-phone", ["observe"])
    │
    ▼
CLI: spine.append_pairing_granted("alice-phone", ["observe"], principal.id)
    │
    ▼
CLI: prints pairing JSON
```

## Auth Model

### Capability Scopes

| Capability | What It Allows |
|---|---|
| `observe` | Read `/status` and `/health` |
| `control` | Start, stop, set miner mode |

In milestone 1, capability enforcement is in the CLI only. The daemon HTTP endpoints are unprotected.

### Pairing Lifecycle

1. **Pairing Request**: `cli.py pair --device <name> --capabilities observe,control`
2. **Pairing Granted**: Stored in `state/pairing-store.json`
3. **Capability Check**: `cli.py control --client <name>` calls `has_capability(name, 'control')`
4. **Capability Revocation**: Not implemented in milestone 1 (future: `capability_revoked` event)

## Design Decisions Explained

### Why Stdlib Only?

No external dependencies means:
- No `pip install` step
- No dependency conflicts
- Easier auditing
- Faster cold starts

The tradeoff is more boilerplate (JSON handling, HTTP server) but this is acceptable for a daemon that won't grow large.

### Why LAN-Only?

The daemon binds to `127.0.0.1` by default. On a LAN deployment, bind to `0.0.0.0` for phone access. Exposing this port to the internet is explicitly out of scope for milestone 1.

Rationale: A home mining control surface should not be internet-facing without TLS, authentication, and careful firewall rules. Milestone 1 stays conservative.

### Why JSONL Not SQLite?

JSONL is:
- Human-readable and inspectable
- Append-only by nature
- Portable (copy the file anywhere)
- No schema migrations

SQLite would add complexity and is overkill for a log that milestone 1 only reads sequentially.

### Why Single HTML File?

The command center is a single `index.html` with inline CSS and JavaScript. No build step, no framework, no bundle.

Rationale: The product should feel like a native app. For milestone 1, a standalone HTML file proves the UI contract without framework lock-in.

### Why Split CLI from Daemon?

The CLI is the "smart client." It knows about pairing, capabilities, and the event spine. The daemon only knows about miner state.

This split:
- Allows future clients (mobile app, web app) without duplicating business logic
- Keeps the daemon simple (stateless HTTP)
- Makes the event spine the source of truth for audit trails

## Module Dependency Graph

```
cli.py
 ├── daemon_call() → daemon.py (HTTP)
 ├── store.py
 │    ├── load_or_create_principal()
 │    ├── pair_client()
 │    └── has_capability()
 └── spine.py
      ├── append_pairing_granted()
      ├── append_control_receipt()
      └── get_events()

daemon.py
 ├── MinerSimulator (in-process)
 └── GatewayHandler
      └── miner.get_snapshot() / miner.start() / miner.stop() / miner.set_mode()

spine.py
 └── (standalone, reads/writes state/event-spine.jsonl)

store.py
 └── (standalone, reads/writes state/principal.json, state/pairing-store.json)
```

## State Files

All state files live in `state/` (controlled by `ZEND_STATE_DIR`):

| File | Format | Created By |
|---|---|---|
| `principal.json` | JSON | `store.load_or_create_principal()` |
| `pairing-store.json` | JSON | `store.pair_client()` |
| `event-spine.jsonl` | JSONL | `spine.append_*()` functions |
| `daemon.pid` | Plain text | `bootstrap_home_miner.sh` |

## Adding a New Endpoint

To add a new daemon endpoint (e.g., `GET /metrics`):

1. **Define the response shape** in `daemon.py`
2. **Add the handler method** to `GatewayHandler` (`do_GET` or `do_POST`)
3. **Add the CLI wrapper** in `cli.py` (if CLI access is needed)
4. **Document the endpoint** in `docs/api-reference.md`
5. **Add an event** in `spine.py` if the endpoint should be auditable

Example:

```python
# daemon.py
def do_GET(self):
    if self.path == '/metrics':
        self._send_json(200, {
            "total_events": len(spine._load_events()),
            "uptime_seconds": miner.health["uptime_seconds"]
        })
```

## Performance Notes

- Daemon uses `ThreadedHTTPServer`: one thread per request
- Miner state access is protected by `threading.Lock`
- JSONL writes are synchronous (no async I/O in milestone 1)
- Event spine reads load the entire file into memory (acceptable for <10k events)

For production scale, consider:
- Async I/O (asyncio or trio)
- Event spine compaction
- Cached status responses with invalidation

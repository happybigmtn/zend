# Architecture

This document explains how the Zend system is structured, how data flows through it, and why key design decisions were made.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                    │
│                                                                              │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────┐  │
│  │  Mobile Browser             │    │  CLI                                │  │
│  │  apps/zend-home-gateway/    │    │  services/home-miner-daemon/cli.py   │  │
│  │  index.html                 │    │                                     │  │
│  │                             │    │  python3 cli.py status              │  │
│  │  Single HTML file           │    │  python3 cli.py control              │  │
│  │  fetches /status            │    │  python3 cli.py events               │  │
│  │  POSTs /miner/set_mode      │    │                                     │  │
│  └──────────────┬──────────────┘    └──────────────────┬──────────────────┘  │
│                 │                                        │                   │
│                 │  HTTP (LAN)                            │  HTTP             │
│                 │  http://127.0.0.1:8080                 │  http://127.0.0.1:8080
│                 ▼                                        ▼                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Daemon Layer                                       │
│                                                                              │
│  services/home-miner-daemon/                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        daemon.py                                        ││
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  ││
│  │  │ ThreadedHTTPServer│    │ MinerSimulator   │    │ GatewayHandler   │  ││
│  │  │                   │    │                  │    │                  │  ││
│  │  │ Serves HTTP      │───▶│ Simulates miner  │◀───│ Routes requests  │  ││
│  │  │ requests         │    │ state: status,   │    │ do_GET, do_POST  │  ││
│  │  │                  │    │ mode, hashrate   │    │                  │  ││
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────────────┐  │
│         │                            │                                    │  │
│         ▼                            ▼                                    ▼  │
│  ┌──────────────┐           ┌──────────────────┐            ┌─────────────┐  │
│  │ store.py     │           │ spine.py         │            │ __init__.py │  │
│  │              │           │                  │            │             │  │
│  │ PrincipalId  │           │ Event Spine      │            │ Package     │  │
│  │ Pairing      │           │ (JSONL journal)  │            │ marker      │  │
│  │ Capabilities │           │ Append-only      │            │             │  │
│  └──────────────┘           └──────────────────┘            └─────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           State Layer                                        │
│                                                                              │
│  state/                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ principal.json   │  │ pairing-store.json│  │ event-spine.jsonl        │  │
│  │                  │  │                  │  │                          │  │
│  │ {                │  │ {                │  │ {"id":"...","kind":"..."}│  │
│  │   "id": "...",   │  │   "pairing-id-1":│  │ {"id":"...","kind":"..."}│  │
│  │   "created_at":  │  │   {              │  │ {"id":"...","kind":"..."}│  │
│  │   "...",         │  │     "device_name"│  │ ...                      │  │
│  │   "name": "..."  │  │     "capabiliti..│  │                          │  │
│  │ }                │  │   }              │  │                          │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### `daemon.py` — HTTP Server and Miner Simulator

**Purpose**: HTTP server that handles requests and simulates miner behavior.

**Key classes**:

- `MinerSimulator` — Simulates miner state (status, mode, hashrate, temperature)
- `GatewayHandler` — HTTP request handler for `/health`, `/status`, `/miner/*`
- `ThreadedHTTPServer` — Threaded HTTP server for concurrent requests

**Key functions**:

```python
def run_server(host: str, port: int)
    """Start the HTTP server. Blocks until interrupted."""

class MinerSimulator:
    def start() -> dict
        """Start mining. Returns {"success": bool, "status": str}."""

    def stop() -> dict
        """Stop mining. Returns {"success": bool, "status": str}."""

    def set_mode(mode: str) -> dict
        """Set mining mode. Returns {"success": bool, "mode": str}."""

    def get_snapshot() -> dict
        """Return current miner state for clients."""
```

**State managed**: MinerSimulator holds in-memory state (status, mode, hashrate). This resets on daemon restart.

### `cli.py` — Command-Line Interface

**Purpose**: CLI for status checks, miner control, device pairing, and event queries.

**Key commands**:

- `health` — Check daemon health
- `status` — Get miner status
- `bootstrap` — Create principal identity and initial pairing
- `pair` — Pair a new device
- `control` — Start/stop/set_mode with capability checks
- `events` — Query the event spine

**Key functions**:

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict
    """Make an HTTP request to the daemon."""
```

**State managed**: CLI reads and writes state files but doesn't hold in-memory state.

### `store.py` — Principal and Pairing Store

**Purpose**: Manages principal identity and device pairings.

**Key classes**:

- `Principal` — Zend identity (`id`, `created_at`, `name`)
- `GatewayPairing` — Paired device record (`id`, `device_name`, `capabilities`)

**Key functions**:

```python
def load_or_create_principal() -> Principal
    """Load existing principal or create new one."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing
    """Create a new device pairing."""

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
    """Look up pairing by device name."""

def has_capability(device_name: str, capability: str) -> bool
    """Check if device has a specific capability."""
```

**State managed**: `state/principal.json`, `state/pairing-store.json`

### `spine.py` — Event Spine

**Purpose**: Append-only journal of all operations.

**Key classes**:

- `SpineEvent` — An event record (`id`, `principal_id`, `kind`, `payload`, `created_at`)
- `EventKind` — Enum of event types

**Key functions**:

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
    """Append a new event to the spine."""

def get_events(kind: EventKind = None, limit: int = 100) -> list[SpineEvent]
    """Get events, optionally filtered by kind."""

def append_pairing_requested(device_name, capabilities, principal_id)
def append_pairing_granted(device_name, capabilities, principal_id)
def append_control_receipt(command, mode, status, principal_id)
```

**State managed**: `state/event-spine.jsonl` (JSONL format, one event per line)

**Event kinds**:

| Kind | Triggered by |
|------|--------------|
| `pairing_requested` | New device requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Device capability removed |
| `miner_alert` | Miner warning or error |
| `control_receipt` | Miner control action |
| `hermes_summary` | Hermes gateway summary |
| `user_message` | User message received |

## Data Flow

### Control Command Flow

```
User clicks "Start" in browser
        │
        ▼
HTML calls fetch('/miner/start', {method: 'POST'})
        │
        ▼
GatewayHandler.do_POST() receives request
        │
        ▼
daemon_call() sends POST to /miner/start
        │
        ▼
MinerSimulator.start() updates internal state
        │
        ▼
Response {"success": true, "status": "running"}
        │
        ▼
CLI command control --action start
        │
        ▼
daemon_call() sends POST /miner/start
        │
        ▼
spine.append_control_receipt() logs to event-spine.jsonl
        │
        ▼
Receipt {"kind": "control_receipt", "payload": {...}}
```

### Device Pairing Flow

```
./scripts/pair_gateway_client.sh --client alice-phone
        │
        ▼
cli.py pair --device alice-phone
        │
        ▼
store.pair_client() creates pairing record
        │
        ▼
spine.append_pairing_requested() logs request
        │
        ▼
spine.append_pairing_granted() logs approval
        │
        ▼
state/pairing-store.json updated
```

## Auth Model

### Capability Scopes

Phase one supports two capabilities:

| Capability | Permissions |
|------------|------------|
| `observe` | Read `/status`, `/health`, `/spine/events` |
| `control` | All `observe` + POST `/miner/start`, `/miner/stop`, `/miner/set_mode` |

### Authorization Flow

```
CLI: control --client alice-phone --action start
        │
        ▼
store.has_capability("alice-phone", "control")
        │
        ├─── True ──▶ proceed with action
        │
        └─── False ──▶ return {"error": "unauthorized"}
```

### Design Decision: No HTTP Auth in Phase One

The daemon doesn't implement OAuth, JWT, or session cookies. Authorization relies on:

1. **LAN isolation** — daemon binds to 127.0.0.1 by default
2. **Capability checks** — CLI validates device capabilities before actions
3. **Event audit** — all actions logged to spine

This keeps phase one simple and auditable. More sophisticated auth (TLS, tokens) can be added in later phases.

## Event Spine Design

### Why JSONL?

- **Append-only**: JSONL naturally supports append-only writes (no locking needed)
- **Readable**: Each line is a complete JSON object, human-readable
- **Streaming**: Tools like `tail -f` can follow new events in real-time
- **Simple**: No SQLite or database dependencies

### Trade-offs

| Pros | Cons |
|------|------|
| Simple, no dependencies | No indexing (full scan for queries) |
| Human-readable | Grows indefinitely (needs rotation) |
| Works with standard tools | Not ideal for millions of events |

### Future: Event Rotation

When `event-spine.jsonl` grows large, implement rotation:

1. Rename current file with timestamp
2. Start new empty spine
3. Keep last N rotated files
4. Index by kind for common queries

## Design Decisions

### Why stdlib-only?

- **No dependency hell**: pip install fails on some systems
- **Reproducible**: Code works anywhere Python 3.10+ is available
- **Auditable**: All code is visible, no hidden library behavior
- **Portable**: Works on Raspberry Pi, VMs, containers without modification

### Why LAN-only by default?

- **Minimizes attack surface**: No internet-facing control surfaces
- **Phase one scope**: Focus on proving the product before remote access
- **User-controlled**: Operators can enable LAN access explicitly

### Why single HTML file for the gateway?

- **No build step**: Open the file and it works
- **Portable**: Copy to any device, works offline
- **Auditable**: One file, easy to review
- **No framework**: Pure HTML/CSS/JS, maximum compatibility

### Why not SQLite?

- **Dependency**: SQLite requires a C library and Python bindings
- **Complexity**: Schema migrations, connection management
- **Overkill**: For append-only JSONL, simpler is better

## Directory Conventions

```
services/
  home-miner-daemon/
    daemon.py          # HTTP server, miner simulator
    cli.py             # CLI interface
    store.py           # Principal and pairing store
    spine.py           # Event spine
    __init__.py        # Package marker

apps/
  zend-home-gateway/
    index.html         # Single-file mobile interface

scripts/
  bootstrap_home_miner.sh   # Start daemon, bootstrap identity
  pair_gateway_client.sh    # Pair a new device
  read_miner_status.sh      # Quick status check
  set_mining_mode.sh        # Change miner mode

state/                      # Created at runtime
  principal.json             # Principal identity
  pairing-store.json        # Device pairings
  event-spine.jsonl          # Event journal
  daemon.pid                 # Daemon process ID
```

## Adding a New Endpoint

To add a new daemon endpoint:

1. **Define the handler** in `daemon.py`:

```python
def do_GET(self):
    if self.path == '/health':
        self._send_json(200, miner.health)
    elif self.path == '/new-endpoint':  # Add here
        self._send_json(200, {"data": "value"})
```

2. **Update CLI** in `cli.py` if needed:

```python
def cmd_new_command(args):
    result = daemon_call('GET', '/new-endpoint')
    print(json.dumps(result, indent=2))
    return 0
```

3. **Add test** in `services/home-miner-daemon/test_daemon.py` (when test infrastructure exists):

```python
def test_new_endpoint():
    resp = requests.get(f'{BASE_URL}/new-endpoint')
    assert resp.status_code == 200
    assert resp.json()['data'] == 'value'
```

> **Note**: Test infrastructure is not yet implemented. The above is a placeholder for when tests are added.

4. **Document** in `docs/api-reference.md`

## Environment Variables

| Variable | Default | Used by | Purpose |
|----------|---------|---------|---------|
| `ZEND_BIND_HOST` | `127.0.0.1` | daemon.py | HTTP server bind address |
| `ZEND_BIND_PORT` | `8080` | daemon.py | HTTP server port |
| `ZEND_STATE_DIR` | `./state` | daemon.py, store.py, spine.py | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | cli.py | Daemon URL for CLI |

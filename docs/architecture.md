# Architecture

System architecture for Zend Home Mining Control System.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Mobile Device                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Zend Home Gateway                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │   │
│  │  │ Status Hero  │  │Mode Switcher │  │   Quick Actions       │    │   │
│  │  │              │  │              │  │   [Start] [Stop]      │    │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘    │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │                    Receipt Cards                          │    │   │
│  │  │  ┌────────────────────────────────────────────────────┐  │    │   │
│  │  │  │ Control Receipt: miner.start → accepted            │  │    │   │
│  │  │  │ 12:00:05 PM                                       │  │    │   │
│  │  │  └────────────────────────────────────────────────────┘  │    │   │
│  │  └──────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP API
┌────────────────────────────────────▼────────────────────────────────────┐
│                        Home Miner Daemon                                 │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      HTTP Server (ThreadedHTTPServer)               │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │                    GatewayHandler                             │   │  │
│  │  │  GET  /health    → miner.health                             │   │  │
│  │  │  GET  /status    → miner.get_snapshot()                       │   │  │
│  │  │  POST /miner/start → miner.start()                            │   │  │
│  │  │  POST /miner/stop  → miner.stop()                            │   │  │
│  │  │  POST /miner/set_mode → miner.set_mode()                      │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                     │                                     │
│  ┌───────────────────┐  ┌───────────▼───────────┐  ┌────────────────┐  │
│  │   MinerSimulator  │  │        Spine          │  │     Store      │  │
│  │                   │  │                       │  │                │  │
│  │  status: str      │  │  event-spine.jsonl    │  │  principal.json│  │
│  │  mode: str        │  │  (append-only log)     │  │  pairing-      │  │
│  │  hashrate_hs: int │  │                       │  │  store.json    │  │
│  │  temperature: float│ │  Events:             │  │                │  │
│  │  uptime_seconds: int│ │  - pairing_requested  │  │  Principal:    │  │
│  │                   │  │  - pairing_granted    │  │  - id          │  │
│  │  start()          │  │  - control_receipt     │  │  - created_at  │  │
│  │  stop()          │  │  - miner_alert        │  │  - name        │  │
│  │  set_mode()      │  │  - hermes_summary      │  │                │  │
│  │                   │  │                       │  │  Pairing:      │  │
│  │                   │  │                       │  │  - device_name │  │
│  │                   │  │                       │  │  - capabilities│  │
│  └───────────────────┘  └───────────────────────┘  └────────────────┘  │
│                                    │                                      │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                              ┌──────▼──────┐
                              │    state/   │
                              │             │
                              │ principal.json
                              │ pairing-    │
                              │ store.json  │
                              │ event-      │
                              │ spine.jsonl │
                              └─────────────┘
```

## Module Guide

### daemon.py

**Location**: `services/home-miner-daemon/daemon.py`

**Purpose**: HTTP server and miner simulation.

**Key Classes**:

#### `MinerSimulator`

The mining simulator that exposes the same contract a real miner backend will use.

```python
class MinerSimulator:
    def __init__(self):
        self._status = MinerStatus.STOPPED
        self._mode = MinerMode.PAUSED
        self._hashrate_hs = 0
        self._temperature = 45.0
        self._uptime_seconds = 0
        self._started_at: Optional[float] = None
        self._lock = threading.Lock()
```

**Properties**:
- `status`: Current miner status (`MinerStatus.RUNNING`, `MinerStatus.STOPPED`, `MinerStatus.OFFLINE`, `MinerStatus.ERROR`)
- `mode`: Current mining mode (`MinerMode.PAUSED`, `MinerMode.BALANCED`, `MinerMode.PERFORMANCE`)
- `health`: Health check dict

**Methods**:
- `start()`: Start mining, returns `{"success": bool, "status": str}`
- `stop()`: Stop mining, returns `{"success": bool, "status": str}`
- `set_mode(mode)`: Set mining mode, returns `{"success": bool, "mode": str}`
- `get_snapshot()`: Get complete status snapshot

#### `GatewayHandler`

HTTP request handler for the daemon API.

```python
class GatewayHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health': ...
        elif self.path == '/status': ...
    
    def do_POST(self):
        if self.path == '/miner/start': ...
        elif self.path == '/miner/stop': ...
        elif self.path == '/miner/set_mode': ...
```

#### `ThreadedHTTPServer`

Threaded HTTP server using Python's socketserver module.

```python
class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
```

---

### cli.py

**Location**: `services/home-miner-daemon/cli.py`

**Purpose**: Command-line interface for daemon control.

**Key Functions**:

```python
def cmd_status(args): ...      # Get miner status
def cmd_health(args): ...     # Get daemon health
def cmd_bootstrap(args): ...  # Bootstrap principal and first pairing
def cmd_pair(args): ...        # Pair a new device
def cmd_control(args): ...     # Control miner (start/stop/set_mode)
def cmd_events(args): ...      # List events from spine
```

**Usage Examples**:

```bash
# Bootstrap
python3 cli.py bootstrap --device my-phone

# Status
python3 cli.py status

# Control
python3 cli.py control --client my-phone --action start
python3 cli.py control --client my-phone --action set_mode --mode balanced

# Events
python3 cli.py events --kind control_receipt --limit 20
```

---

### spine.py

**Location**: `services/home-miner-daemon/spine.py`

**Purpose**: Append-only encrypted event journal. Source of truth for all operational events.

**Key Concepts**:

- The spine is **append-only**: events cannot be modified or deleted
- The inbox is a **derived view**: projections from the spine
- All events flow through the spine first

**Event Kinds**:

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"
```

**Key Functions**:

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]
def append_pairing_requested(device_name: str, capabilities: list, principal_id: str)
def append_pairing_granted(device_name: str, capabilities: list, principal_id: str)
def append_control_receipt(command: str, mode: Optional[str], status: str, principal_id: str)
```

**Storage Format**:

Events are stored in `state/event-spine.jsonl` (JSON Lines format):

```jsonl
{"id": "uuid", "principal_id": "uuid", "kind": "control_receipt", "payload": {...}, "created_at": "ISO8601", "version": 1}
{"id": "uuid", "principal_id": "uuid", "kind": "pairing_granted", "payload": {...}, "created_at": "ISO8601", "version": 1}
```

---

### store.py

**Location**: `services/home-miner-daemon/store.py`

**Purpose**: Principal identity and gateway pairing management.

**Key Classes**:

```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str   # ISO 8601
    name: str         # Human-readable name

@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list  # ['observe', 'control']
    paired_at: str
    token_expires_at: str
```

**Key Functions**:

```python
def load_or_create_principal() -> Principal
def pair_client(device_name: str, capabilities: list) -> GatewayPairing
def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
def has_capability(device_name: str, capability: str) -> bool
def list_devices() -> list[GatewayPairing]
```

**Storage Format**:

- `state/principal.json`: Single principal record
- `state/pairing-store.json`: Dictionary of pairing records keyed by ID

---

## Data Flow

### Control Command Flow

```
1. User taps "Start" in Gateway UI
          ↓
2. Browser sends: POST /miner/start
          ↓
3. GatewayHandler.do_POST() receives request
          ↓
4. miner.start() called on MinerSimulator
          ↓
5. MinerSimulator updates internal state
          ↓
6. Returns: {"success": true, "status": "running"}
          ↓
7. GatewayHandler sends HTTP 200 response
          ↓
8. Browser updates UI with new state
          ↓
9. CLI appends control_receipt to spine (via spine.py)
          ↓
10. Event stored in event-spine.jsonl
```

### Pairing Flow

```
1. Operator runs: python3 cli.py pair --device my-phone --capabilities observe,control
          ↓
2. cli.py calls store.pair_client()
          ↓
3. pair_client() creates GatewayPairing record
          ↓
4. Principal loaded or created
          ↓
5. Pairing saved to pairing-store.json
          ↓
6. cli.py calls spine.append_pairing_requested()
          ↓
7. cli.py calls spine.append_pairing_granted()
          ↓
8. Both events appended to event-spine.jsonl
          ↓
9. CLI outputs pairing details
```

## Auth Model

### Capabilities

Two capability levels:

| Capability | Description |
|------------|-------------|
| `observe` | View miner status and events |
| `control` | Start/stop mining, change mode |

### Pairing Flow

1. **Request**: Device requests pairing with specific capabilities
2. **Grant**: Operator grants capabilities via CLI
3. **Record**: Pairing stored with capabilities
4. **Check**: CLI checks `has_capability()` before control actions

### CLI Authorization

```python
def cmd_control(args):
    if not has_capability(args.client, 'control'):
        return {"error": "unauthorized", "message": "..."}
    # ... execute command
```

## Event Spine

### Design Rationale

**Why JSONL instead of SQLite?**

- Simpler: no database engine required
- Portable: single file, easy backup
- Append-only: naturally suitable for JSONL
- Stdlib: no external dependencies

**Why append-only?**

- Audit trail: complete history of all operations
- Recoverability: replay events to rebuild state
- Simplicity: no updates or deletes to implement

### Event Routing

| Event Kind | Routes To |
|------------|-----------|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home, Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox, Agent |
| `user_message` | Inbox |

## Design Decisions

### Why stdlib-only?

- **No dependency hell**: pip install never breaks
- **Portable**: runs anywhere Python 3.10+ exists
- ** auditable**: no hidden dependencies
- **Minimal attack surface**: fewer packages = fewer vulnerabilities

### Why LAN-only binding?

- **Security**: home network is trusted perimeter
- **Simplicity**: no TLS/certificates needed for local use
- **Low latency**: direct connection, no cloud round-trips
- **Privacy**: all data stays on local network

### Why JSONL for event spine?

- **Append-optimized**: writes never block
- **Human-readable**: inspect with cat/grep
- **Portable**: single file, no database
- **Recoverable**: easy to parse and replay

### Why single HTML file for gateway?

- **No build step**: edit and refresh
- **No framework**: just vanilla JS
- **Portable**: works anywhere, no server
- **Simple hosting**: serve static or open directly

## State Files

| File | Format | Purpose |
|------|--------|---------|
| `principal.json` | JSON | Principal identity |
| `pairing-store.json` | JSON | Device pairings |
| `event-spine.jsonl` | JSONL | Event journal |
| `daemon.pid` | Text | Daemon process ID |

All files are in `state/` directory (configurable via `ZEND_STATE_DIR`).

## Threading Model

```
Main Thread
    └── ThreadedHTTPServer
            ├── Thread 1: Handle request A
            ├── Thread 2: Handle request B
            └── Thread N: Handle request N
```

Each request runs in its own thread. The `MinerSimulator` uses a `threading.Lock` to protect shared state.

## Future Considerations

### Milestone 2+

- HTTPS/TLS for secure remote access
- Encrypted event payloads
- Rich conversation UI
- Contact policies
- Thread management

### Potential Changes

- SQLite for event spine (when compaction is needed)
- WebSocket for real-time updates
- Mobile native app
- Cloud sync for remote access

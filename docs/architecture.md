# Architecture

This document explains the Zend system design, module responsibilities, and data flows.

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                     Thin Mobile Client                              │
│                  apps/zend-home-gateway/                            │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                      index.html                               │   │
│   │                                                                  │   │
│   │   [Status Hero]  [Mode Switcher]  [Quick Actions]           │   │
│   │   [Receipt Card]  [Bottom Nav]                                │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              │ HTTP :8080 (LAN)
                              │ JSON-RPC style
                              v
┌────────────────────────────────────────────────────────────────────┐
│                   Home Miner Daemon                                 │
│              services/home-miner-daemon/                           │
│                                                                       │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│   │    daemon    │  │    spine     │  │        store          │   │
│   │              │  │              │  │                       │   │
│   │ - HTTP API   │  │ - Event log  │  │ - Principal          │   │
│   │ - Router     │  │ - Append-only│  │ - Pairing records    │   │
│   │ - MinerSim   │  │ - JSONL file │  │ - Capabilities       │   │
│   └──────────────┘  └──────────────┘  └───────────────────────┘   │
│          │                  │                      │                │
│          └──────────────────┼──────────────────────┘                │
│                             │                                       │
│                             v                                       │
│                    ┌─────────────────┐                              │
│                    │   state/        │                              │
│                    │   principal.json│                              │
│                    │   pairing-store │                              │
│                    │   event-spine   │                              │
│                    └─────────────────┘                              │
└────────────────────────────────────────────────────────────────────┘
```

## Modules

### daemon.py

The HTTP API server and miner simulator.

**Location**: `services/home-miner-daemon/daemon.py`

**Responsibilities**:
- HTTP server using Python's `http.server`
- Route requests to handlers
- Manage the `MinerSimulator` instance
- Return JSON responses

**Key Classes**:

```python
class MinerSimulator:
    """Simulates miner behavior for milestone 1."""
    
    def start() -> dict:
        """Start mining. Returns success status."""
    
    def stop() -> dict:
        """Stop mining. Returns success status."""
    
    def set_mode(mode: str) -> dict:
        """Set mining mode. Validates mode value."""
    
    def get_snapshot() -> dict:
        """Return current miner state."""
```

```python
class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler."""
    
    def do_GET(self):
        # Routes: /health, /status
    
    def do_POST(self):
        # Routes: /miner/start, /miner/stop, /miner/set_mode
```

**State**: In-memory only. Miner state resets on daemon restart.

### cli.py

Command-line interface for scripting and automation.

**Location**: `services/home-miner-daemon/cli.py`

**Responsibilities**:
- Parse command-line arguments
- Make HTTP calls to daemon
- Format and print output
- Coordinate with `store` and `spine` modules

**Commands**:

| Command | Description |
|---------|-------------|
| `status` | Get miner status |
| `health` | Get daemon health |
| `bootstrap` | Create principal and default pairing |
| `pair` | Pair a new device |
| `control` | Issue control action |
| `events` | Query event spine |

**Example**:

```bash
python3 cli.py control --client my-phone --action set_mode --mode balanced
```

### spine.py

Append-only encrypted event journal.

**Location**: `services/home-miner-daemon/spine.py`

**Responsibilities**:
- Append events to JSONL file
- Query events by kind
- Define event kinds and payloads

**Event Kinds**:

| Kind | When Appended |
|------|---------------|
| `pairing_requested` | Client requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Capability removed |
| `miner_alert` | Miner warning/alert |
| `control_receipt` | Control action completed |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message received |

**Data Flow**:

```
Control Action
     │
     v
daemon.py handles request
     │
     ├─► MinerSimulator updates state
     │
     └─► spine.append_control_receipt()
              │
              v
         Append to state/event-spine.jsonl
```

**File Format**: JSONL (JSON Lines), one event per line.

**Example Event**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "kind": "control_receipt",
  "payload": {
    "command": "start",
    "status": "accepted",
    "receipt_id": "660e8400-e29b-41d4-a716-446655440001"
  },
  "created_at": "2026-03-22T12:00:00+00:00",
  "version": 1
}
```

### store.py

Principal and pairing data store.

**Location**: `services/home-miner-daemon/store.py`

**Responsibilities**:
- Create and load principal identity
- Manage pairing records
- Store capabilities per device

**Data Model**:

```python
@dataclass
class Principal:
    id: str              # UUID
    created_at: str      # ISO 8601
    name: str            # Human-readable name

@dataclass
class GatewayPairing:
    id: str              # UUID
    principal_id: str    # Links to Principal
    device_name: str     # Human-readable name
    capabilities: list   # ["observe", "control"]
    paired_at: str       # ISO 8601
    token_expires_at: str
    token_used: bool
```

**Files**:

| File | Content |
|------|---------|
| `state/principal.json` | Single principal record |
| `state/pairing-store.json` | All pairing records |

## Data Flow

### Control Command Flow

```
1. User clicks "Start" in UI
          │
          v
2. Browser POSTs to /miner/start
          │
          v
3. daemon.py receives request
          │
          ├─► MinerSimulator.start()
          │         │
          │         └─► Updates in-memory state
          │
          └─► Returns {success: true}
          │
          v
4. UI updates status display
          │
          v
5. CLI/spine appends control_receipt event
          │
          v
6. Event appears in inbox
```

### Pairing Flow

```
1. Operator runs bootstrap or pair script
          │
          v
2. store.py creates Principal (if needed)
          │
          v
3. store.py creates GatewayPairing record
          │
          v
4. spine.py appends pairing_granted event
          │
          v
5. Pairing data stored in state/
```

## Auth Model

Milestone 1 has no authentication. Device authorization is based on pairing records.

**Capability Scoping**:

| Capability | Permissions |
|------------|-------------|
| `observe` | Read status, view events |
| `control` | Start, stop, change mode, plus observe |

**Authorization Flow**:

```
CLI: python3 cli.py control --client my-phone --action start
          │
          v
store.py.has_capability("my-phone", "control")
          │
          ├─► Yes: Execute action
          │
          └─► No:  Return {error: "unauthorized"}
```

## Design Decisions

### Why Stdlib-Only?

Python standard library has everything needed:
- `socketserver` + `http.server` for HTTP API
- `json` for data handling
- `pathlib` for file operations
- `threading` for concurrent requests

No pip install means:
- Faster setup
- Fewer security vulnerabilities
- Works in restricted environments

### Why JSONL Not SQLite?

JSONL (JSON Lines) is simpler for milestone 1:
- Append-only is correct by construction
- No schema migrations needed
- Easy to inspect with `cat` and `grep`
- Human-readable

SQLite would add complexity without clear benefit for the current scale.

### Why LAN-Only by Default?

Security first. Mining control on the internet is dangerous.

The daemon binds to `127.0.0.1` by default. Operators can configure LAN access when they understand the risks.

### Why Single HTML File?

The gateway client is intentionally simple:
- No build step
- No framework to learn
- Works from file:// or any static host
- Easy to inspect and modify

### Why Event Spine?

One source of truth for all events:
- Pairing approvals
- Control receipts
- Alerts
- Hermes summaries
- Messages

The inbox is a view of the spine, not a separate store.

## Module Dependencies

```
cli.py
  ├─► store.py (principal, pairing)
  ├─► spine.py (events)
  └─► daemon.py (via HTTP)

daemon.py
  ├─► store.py (optional, for future capability checks)
  └─► spine.py (optional, for event logging)

index.html (browser)
  └─► daemon.py (via fetch API)
```

## State Files

All state lives in the `state/` directory (gitignored).

| File | Format | Purpose |
|------|--------|---------|
| `principal.json` | JSON | Principal identity |
| `pairing-store.json` | JSON | Device pairings |
| `event-spine.jsonl` | JSONL | All events |
| `daemon.pid` | Text | Daemon process ID |

## Extensibility

### Adding New Endpoints

1. Add handler in `daemon.py`:

```python
def do_GET(self):
    if self.path == '/new-endpoint':
        self._send_json(200, {"result": "data"})
```

2. Add CLI command in `cli.py`:

```python
def cmd_new(self, args):
    result = daemon_call('GET', '/new-endpoint')
    print(json.dumps(result, indent=2))
```

### Adding New Event Kinds

1. Add to `spine.py`:

```python
class EventKind(str, Enum):
    # ... existing kinds ...
    NEW_KIND = "new_kind"

def append_new_event(payload: dict, principal_id: str):
    return append_event(EventKind.NEW_KIND, principal_id, payload)
```

### Adding New Capabilities

1. Define in `store.py`:

```python
# No code change needed, capabilities are arbitrary strings
pairing.capabilities = ["observe", "control", "new_capability"]
```

## Future Considerations

### Authentication

Future milestone may add token-based auth:
- Pairing generates a token
- Token included in request headers
- Token validated before action

### Remote Access

Future milestone may add secure tunneling:
- mTLS for mutual authentication
- WireGuard or Cloudflare Tunnel for access
- Rotate credentials on schedule

### Real Miner Backend

Current miner is a simulator. Future milestone may:
- Connect to real miner APIs
- Handle miner-specific error codes
- Support miner configuration

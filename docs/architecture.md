# Architecture

System design and module documentation for Zend Home Miner.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Diagram](#component-diagram)
3. [Module Guide](#module-guide)
4. [Data Flow](#data-flow)
5. [Auth Model](#auth-model)
6. [Event Spine](#event-spine)
7. [Design Decisions](#design-decisions)

---

## System Overview

Zend is a private command center for home mining hardware. The system has three
main components:

1. **Home Miner Daemon** — A Python HTTP server that runs on your mining
   hardware. Exposes a REST API for monitoring and controlling the miner.

2. **Mobile Gateway** — A single HTML file that runs in any browser. Provides
   a mobile-optimized interface for the daemon API.

3. **Event Spine** — An append-only log of all operations (pairing, control,
   alerts). Serves as the source of truth for the operations inbox.

```
┌─────────────────────────────────────────────────────────────────┐
│                          Zend System                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌──────────────┐                                               │
│   │   Mobile     │◄──────────────────────────────────────────┐  │
│   │   Gateway    │   Browser (any device on LAN)            │  │
│   │  (HTML/JS)   │   apps/zend-home-gateway/index.html       │  │
│   └──────────────┘                                            │  │
│        │                                                      │  │
│        │ HTTP/REST                                            │  │
│        │                                                      │  │
│        ▼                                                      │  │
│   ┌──────────────────────────────────────────────────────────┐│
│   │                   Home Miner Daemon                       ││
│   │                                                          ││
│   │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ ││
│   │  │  Daemon    │  │    CLI     │  │    Miner           │ ││
│   │  │  (HTTP)    │  │  (tools)   │  │    Simulator       │ ││
│   │  └─────┬──────┘  └─────┬──────┘  └────────┬───────────┘ ││
│   │        │               │                   │             ││
│   │        └───────────────┼───────────────────┘             ││
│   │                        │                                 ││
│   │                        ▼                                 ││
│   │              ┌──────────────────┐                        ││
│   │              │  Pairing Store   │                        ││
│   │              │  (principal.json)│                        ││
│   │              └────────┬─────────┘                        ││
│   │                       │                                  ││
│   └───────────────────────┼──────────────────────────────────┘│
│                           │                                    │
│                           ▼                                    │
│                   ┌────────────────┐                          │
│                   │  Event Spine   │                          │
│                   │(event-spine.   │                          │
│                   │ jsonl)         │                          │
│                   └────────────────┘                          │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Component Diagram

### Mobile Gateway

**Location:** `apps/zend-home-gateway/index.html`

A single-file HTML application that runs in any modern browser. No build step,
no server-side rendering, no framework.

**Features:**
- Status display with real-time updates (5-second polling)
- Mode switcher (Paused / Balanced / Performance)
- Start/Stop mining buttons
- Event receipt display
- Four-tab navigation (Home, Inbox, Agent, Device)

**Architecture:**
- Vanilla JavaScript (no dependencies)
- Fetch API for daemon communication
- CSS custom properties for theming
- Mobile-first responsive design

### Home Miner Daemon

**Location:** `services/home-miner-daemon/`

A Python HTTP server using only stdlib (`socketserver`, `http.server`,
`json`, `threading`).

**Features:**
- REST API for miner control
- Threaded request handling
- JSON request/response format
- Simulated miner for milestone 1

### Event Spine

**Location:** `services/home-miner-daemon/spine.py`

An append-only journal stored as JSONL (JSON Lines).

**Features:**
- Immutable event log
- Event kind filtering
- Most-recent-first ordering
- Principal-scoped queries

---

## Module Guide

### daemon.py

**Purpose:** HTTP server and miner simulator

**Key Classes:**

```python
class MinerSimulator:
    """Simulates miner hardware for milestone 1."""
    
    @property
    def status(self) -> MinerStatus:
        """Current miner state."""
    
    @property
    def mode(self) -> MinerMode:
        """Operating mode."""
    
    def start(self) -> dict:
        """Start mining. Returns success/error."""
    
    def stop(self) -> dict:
        """Stop mining. Returns success/error."""
    
    def set_mode(self, mode: str) -> dict:
        """Set operating mode. Returns success/error."""
    
    def get_snapshot(self) -> dict:
        """Get full status snapshot."""
```

```python
class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler for REST API."""
    
    def do_GET(self):
        """Handle GET /health, /status"""
    
    def do_POST(self):
        """Handle POST /miner/start, /miner/stop, /miner/set_mode"""
```

**State Management:**
- Global `miner` instance (thread-safe with locks)
- State stored in `state/` directory
- Environment variable `ZEND_STATE_DIR` for customization

**Configuration:**
```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
BIND_PORT = int(os.environ.get('ZEND_BIND_PORT', 8080))
STATE_DIR = os.environ.get('ZEND_STATE_DIR', default_state_dir())
```

### cli.py

**Purpose:** Command-line tools for daemon interaction

**Commands:**

| Command | Description |
|---------|-------------|
| `health` | Check daemon health |
| `status` | Get miner status |
| `bootstrap` | Create principal and default pairing |
| `pair` | Pair a new device |
| `control` | Control miner (start/stop/set_mode) |
| `events` | Query event spine |

**Key Functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make HTTP request to daemon."""
```

**Usage Examples:**
```bash
# Health check
python3 cli.py health

# Bootstrap
python3 cli.py bootstrap --device my-phone

# Control
python3 cli.py control --client my-phone --action start
python3 cli.py control --client my-phone --action set_mode --mode balanced
```

### spine.py

**Purpose:** Append-only event journal

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append a new event to the spine."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    """Query events, optionally filtered by kind."""

def append_pairing_requested(device_name: str, capabilities: list, principal_id: str):
    """Append pairing requested event."""

def append_pairing_granted(device_name: str, capabilities: list, principal_id: str):
    """Append pairing granted event."""

def append_control_receipt(command: str, mode: Optional[str], status: str, principal_id: str):
    """Append control receipt event."""
```

**Event Kinds:**
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

**Storage:**
- File: `state/event-spine.jsonl`
- Format: One JSON object per line (JSONL)
- Immutable: Events are never modified or deleted

### store.py

**Purpose:** Principal identity and pairing management

**Key Classes:**

```python
@dataclass
class Principal:
    id: str              # UUID
    created_at: str      # ISO 8601
    name: str            # Display name

@dataclass
class GatewayPairing:
    id: str              # UUID
    principal_id: str    # Owner's principal
    device_name: str     # Device identifier
    capabilities: list   # ['observe', 'control']
    paired_at: str       # ISO 8601
    token_expires_at: str
    token_used: bool
```

**Key Functions:**

```python
def load_or_create_principal() -> Principal:
    """Load existing principal or create new."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create new pairing for device."""

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Look up pairing by device name."""

def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""

def list_devices() -> list:
    """List all paired devices."""
```

**Storage:**
- Principal: `state/principal.json`
- Pairings: `state/pairing-store.json`

---

## Data Flow

### Control Command Flow

```
User clicks "Start Mining" in browser
         │
         ▼
HTML Gateway sends POST /miner/start
         │
         ▼
CLI checks device has 'control' capability
         │
         ├─── No control ──► Return error
         │
         ▼ Yes control
CLI sends POST /miner/start to daemon
         │
         ▼
GatewayHandler receives request
         │
         ▼
MinerSimulator.start() is called
         │
         ├─── Already running ──► Return error
         │
         ▼ Not running
Update miner state (locked)
         │
         ▼
Return success response
         │
         ▼
CLI appends control_receipt to event spine
         │
         ▼
CLI prints result to user
```

### Status Query Flow

```
User opens HTML Gateway
         │
         ▼
fetchStatus() called every 5 seconds
         │
         ▼
GET /status request sent
         │
         ▼
GatewayHandler receives request
         │
         ▼
MinerSimulator.get_snapshot() called
         │
         ▼
Return current miner state
         │
         ▼
HTML updates UI with status
```

---

## Auth Model

### Principal Identity

Every Zend installation has one principal identity:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-22T10:30:00+00:00",
  "name": "Zend Home"
}
```

The principal owns all pairings and event spine entries.

### Pairing

Pairing links a device to a principal with specific capabilities:

```json
{
  "id": "...",
  "principal_id": "550e8400-...",
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:30:00+00:00",
  "token_expires_at": "...",
  "token_used": false
}
```

### Capability Scopes

| Capability | Description |
|------------|-------------|
| `observe` | Read miner status, view events |
| `control` | Start/stop mining, change modes |

### Authorization Flow

```
CLI receives command with --client flag
         │
         ▼
store.has_capability(device_name, 'control')
         │
         ├─── False ──► Print error, exit 1
         │
         ▼ True
Proceed with command
```

---

## Event Spine

### Design Principles

1. **Append-only** — Events are never modified or deleted
2. **Source of truth** — The inbox is a derived view
3. **Principal-scoped** — Events belong to a principal
4. **Kind-filtered** — Events can be queried by type

### Event Structure

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "principal_id": "...",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "created_at": "2026-03-22T10:30:00+00:00",
  "version": 1
}
```

### Storage Format

JSONL (JSON Lines) — one event per line:

```
{"id":"...","principal_id":"...","kind":"pairing_granted",...}
{"id":"...","principal_id":"...","kind":"control_receipt",...}
{"id":"...","principal_id":"...","kind":"miner_alert",...}
```

### Why JSONL?

- **Append-only friendly** — New lines only
- **Crash-safe** — Partial writes don't corrupt
- **Streaming** — Read events as they arrive
- **Simple** — No database required

---

## Design Decisions

### Why stdlib Only?

**Decision:** No external Python dependencies

**Rationale:**
- Zero installation complexity (no pip, no requirements.txt)
- Maximum portability (works everywhere Python works)
- Minimal attack surface (no third-party code)
- Reproducible builds (same stdlib on every system)

**Trade-offs:**
- Less ergonomic than `requests` for HTTP
- No type hints in standard library
- Manual JSON handling

### Why LAN-Only by Default?

**Decision:** Daemon binds to 127.0.0.1 by default

**Rationale:**
- Security by default (no accidental exposure)
- Home network assumption (typical user is behind NAT)
- Trust boundary (only physical LAN access)
- Phase 1 simplicity (no TLS, no auth tokens)

**Trade-offs:**
- Requires VPN or tunneling for remote access
- Not suitable for shared networks
- Users must explicitly opt into LAN exposure

### Why JSONL Not SQLite?

**Decision:** Event spine stored as JSON Lines file

**Rationale:**
- Append-only semantics are natural
- No database dependency
- Easy to inspect, backup, migrate
- Sufficient for home-scale usage

**Trade-offs:**
- Slower than database for large queries
- No indexes or efficient filtering
- Single-writer constraint

### Why Single HTML File?

**Decision:** Mobile gateway is one HTML file, no build step

**Rationale:**
- Zero deployment (just open the file)
- No server required for UI
- Works offline after first load
- Trivially portable

**Trade-offs:**
- No SSR for initial load performance
- No code splitting
- All assets inline (increased file size)

---

## Security Considerations

### Current Protections

- LAN-only binding by default
- Capability-scoped permissions
- No plaintext secrets stored

### Current Limitations

- No TLS/HTTPS
- No token-based authentication
- Pairing store is file-based (no encryption)
- No rate limiting

### Recommendations for Production

1. **Network isolation** — Use VLAN or firewall to isolate mining hardware
2. **VPN access** — For remote control, use WireGuard or similar
3. **Encrypted storage** — Encrypt `state/` directory at rest
4. **Audit logging** — Forward event spine to centralized log system
5. **TLS** — Add HTTPS when daemon supports TLS certificates

---

## Future Architecture

### Phase 2 Enhancements

- Real miner backend integration
- Remote access via secure tunnel
- Encrypted pairing store
- TLS support

### Phase 3 Enhancements

- Hermes agent integration
- Multi-device sync
- Encrypted messaging via Zcash memo
- Advanced authorization model

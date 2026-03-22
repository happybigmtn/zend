# Architecture

This document describes the Zend system architecture, module responsibilities, data flows, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Zend System                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐                           ┌────────────────────────────┐  │
│   │   Browser    │                           │   Home Miner Daemon        │  │
│   │   (Phone)    │                           │                            │  │
│   │              │   HTTP/WebSocket          │   ┌──────────────────┐   │  │
│   │  index.html  │◄─────────────────────────►│   │  GatewayHandler  │   │  │
│   │              │                           │   └────────┬─────────┘   │  │
│   │  - Home tab  │                           │            │             │  │
│   │  - Inbox tab │                           │   ┌────────▼─────────┐   │  │
│   │  - Agent tab │                           │   │  MinerSimulator  │   │  │
│   │  - Device tab │                          │   └────────┬─────────┘   │  │
│   └──────────────┘                           │            │             │  │
│                                              │   ┌────────▼─────────┐   │  │
│                                              │   │  CLI (optional)  │   │  │
│                                              │   └──────────────────┘   │  │
│                                              └────────────┬─────────────┘  │
│                                                          │                 │
│                                    ┌─────────────────────┼─────────────┐    │
│                                    │                     │             │    │
│                           ┌────────▼────────┐   ┌────────▼──────┐    │    │
│                           │   Event Spine   │   │ Pairing Store │    │    │
│                           │   (JSONL file)  │   │   (JSON)      │    │    │
│                           └─────────────────┘   └───────────────┘    │    │
│                                   │                                   │    │
│                           ┌───────▼───────┐                           │    │
│                           │  Principal    │                           │    │
│                           │   (JSON)      │                           │    │
│                           └───────────────┘                           │    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. LAN-Only by Default

The daemon binds to `127.0.0.1` in development and `0.0.0.0` (LAN) in production. Internet-facing control surfaces are explicitly out of scope for phase one.

### 2. Stdlib-Only Python

No external Python dependencies. Uses `http.server`, `json`, `threading`, `socketserver` from the standard library. Simplifies deployment and security.

### 3. Append-Only Event Spine

The event spine (`state/event-spine.jsonl`) is the source of truth. The inbox is a derived view. Events are never modified or deleted.

### 4. Capability-Based Access

Devices are paired with specific capabilities (`observe`, `control`). The CLI enforces these; the daemon currently trusts the CLI.

## Module Guide

### `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP server and miner simulator.

**Key Classes:**

```python
class MinerMode(str, Enum):
    PAUSED = "paused"
    BALANCED = "balanced"
    PERFORMANCE = "performance"

class MinerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    OFFLINE = "offline"
    ERROR = "error"

class MinerSimulator:
    """Simulates a miner for milestone 1."""
    
    def start(self) -> dict:
        """Start mining. Returns success/failure."""
        
    def stop(self) -> dict:
        """Stop mining. Returns success/failure."""
        
    def set_mode(self, mode: str) -> dict:
        """Change mining mode. Returns success/failure."""
        
    def get_snapshot(self) -> dict:
        """Get current miner state."""
        
    @property
    def health(self) -> dict:
        """Get health status."""

class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the gateway API."""
    
    def do_GET(self):
        """Handle GET requests: /health, /status"""
        
    def do_POST(self):
        """Handle POST requests: /miner/*"""
```

**State:** Manages the `MinerSimulator` instance. Thread-safe via `threading.Lock`.

**Configuration:**
- `ZEND_BIND_HOST`: Interface to bind (default: `127.0.0.1`)
- `ZEND_BIND_PORT`: HTTP port (default: `8080`)
- `ZEND_STATE_DIR`: State directory (default: `./state`)

---

### `services/home-miner-daemon/cli.py`

**Purpose:** Command-line interface for daemon control.

**Commands:**

| Command | Description |
|---------|-------------|
| `health` | Get daemon health |
| `status` | Get miner status |
| `bootstrap` | Create principal identity and initial pairing |
| `pair` | Pair a new device |
| `control` | Send control command (start/stop/set_mode) |
| `events` | List events from spine |

**Key Functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make HTTP request to daemon."""
    
def cmd_status(args):
    """Get and display miner status."""
    
def cmd_bootstrap(args):
    """Bootstrap principal and create initial pairing."""
    
def cmd_control(args):
    """Send control command with capability check."""
```

**Capability Checks:**

```python
# Before control operations
if not has_capability(args.client, 'control'):
    return {"error": "unauthorized"}
```

---

### `services/home-miner-daemon/spine.py`

**Purpose:** Append-only event journal.

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append a new event to the spine."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    """Get events, optionally filtered by kind."""

def append_pairing_requested(device_name, capabilities, principal_id):
    """Log device requested pairing."""
    
def append_pairing_granted(device_name, capabilities, principal_id):
    """Log pairing was approved."""
    
def append_control_receipt(command, mode, status, principal_id):
    """Log control command result."""
```

**Event Kinds:**

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

**Data Format:** JSON Lines (one JSON object per line).

---

### `services/home-miner-daemon/store.py`

**Purpose:** Principal identity and pairing records.

**Key Classes:**

```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str   # ISO 8601
    name: str         # Display name
    
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list  # ['observe', 'control']
    paired_at: str      # ISO 8601
    token_expires_at: str
    token_used: bool
```

**Key Functions:**

```python
def load_or_create_principal() -> Principal:
    """Get existing principal or create new one."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create new pairing record."""

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Look up pairing by device name."""

def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""

def list_devices() -> list:
    """List all paired devices."""
```

**State Files:**
- `state/principal.json` — PrincipalId and metadata
- `state/pairing-store.json` — All pairing records

---

### `apps/zend-home-gateway/index.html`

**Purpose:** Mobile-shaped command center UI.

**Screens:**
- **Home:** Status hero, mode switcher, start/stop buttons
- **Inbox:** Event receipts and alerts
- **Agent:** Hermes connection status
- **Device:** Pairing info and permissions

**JavaScript State:**

```javascript
const state = {
    status: 'unknown',           // running, stopped, offline, error
    mode: 'paused',              // paused, balanced, performance
    hashrate: 0,                // hashes per second
    freshness: null,             // ISO timestamp
    capabilities: ['observe', 'control'],
    principalId: null,
    deviceName: 'alice-phone'
};
```

**API Integration:**

```javascript
async function fetchStatus() {
    const resp = await fetch(`${API_BASE}/status`);
    const data = await resp.json();
    // Update state...
}

async function setMode(mode) {
    const resp = await fetch(`${API_BASE}/miner/set_mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
    });
    // Handle response...
}
```

---

### `scripts/bootstrap_home_miner.sh`

**Purpose:** Start daemon and create initial state.

**Actions:**
1. Stop any existing daemon
2. Start daemon in background
3. Wait for health check
4. Run `bootstrap` CLI command to create principal

**Usage:**

```bash
./scripts/bootstrap_home_miner.sh        # Start + bootstrap
./scripts/bootstrap_home_miner.sh --daemon  # Start only
./scripts/bootstrap_home_miner.sh --stop    # Stop daemon
./scripts/bootstrap_home_miner.sh --status  # Show status
```

## Data Flow

### Control Command Flow

```
User taps "Start" in browser
         │
         ▼
JavaScript calls POST /miner/start
         │
         ▼
GatewayHandler.do_POST() receives request
         │
         ▼
MinerSimulator.start() called
         │
         ├──► Miner state updated (thread-safe lock)
         │
         ▼
Response sent to browser
         │
         ▼
CLI records control_receipt in event spine
```

### Pairing Flow

```
User runs: cli.py bootstrap --device alice-phone
         │
         ▼
load_or_create_principal() creates PrincipalId
         │
         ▼
pair_client() creates GatewayPairing
         │
         ▼
spine.append_pairing_granted() writes event
         │
         ▼
Pairing info printed to console
```

### Event Routing

| Event Kind | Source | Destination |
|------------|--------|-------------|
| `pairing_requested` | CLI `pair` command | Event spine |
| `pairing_granted` | CLI `pair`/`bootstrap` | Event spine |
| `control_receipt` | CLI `control` command | Event spine |
| `miner_alert` | Future: daemon monitoring | Event spine |
| `hermes_summary` | Future: Hermes gateway | Event spine |

## Auth Model

### Principal Identity

```
Principal
├── id: UUID v4           # Stable identity across sessions
├── created_at: timestamp  # When identity was created
└── name: string           # Display name ("Zend Home")
```

The same `PrincipalId` is used for:
- Gateway pairing records
- Event spine entries
- Future inbox metadata

### Capability Scopes

| Capability | Read | Control | Notes |
|------------|------|---------|-------|
| `observe` | Status, health, events | — | Default for bootstrap |
| `control` | Status, health, events | Start, stop, set_mode | Requires explicit grant |

### Capability Enforcement

CLI checks before control commands:

```python
def cmd_control(args):
    if not has_capability(args.client, 'control'):
        print(json.dumps({"error": "unauthorized"}))
        return 1
    # Proceed with command...
```

## Design Decisions

### Why Stdlib-Only?

**Decision:** No external Python dependencies.

**Rationale:**
- Simplifies deployment on home hardware
- No dependency conflicts or pip issues
- Smaller attack surface
- Easier to audit code

**Trade-off:** More boilerplate for HTTP handling, but acceptable for a simple daemon.

### Why LAN-Only?

**Decision:** Daemon binds to local network by default.

**Rationale:**
- Security: no internet-exposed control surfaces in phase one
- Simplicity: no TLS, auth tokens, or VPN needed
- Privacy: all traffic stays on local network

**Trade-off:** Cannot control miner remotely. Future: optional secure tunneling.

### Why JSONL for Event Spine?

**Decision:** Append-only JSON Lines file, not SQLite or database.

**Rationale:**
- Simple: one file, no server
- Auditable: can `grep` and `cat` directly
- Crash-safe: append is atomic at line boundaries
- Portable: works on any system

**Trade-off:** Not efficient for large datasets. Acceptable for milestone 1 usage.

### Why Single HTML File?

**Decision:** Command center is a single `index.html` with no build step.

**Rationale:**
- No compilation or bundling
- Works from filesystem or simple HTTP server
- Easy to inspect and debug
- No framework dependencies

**Trade-off:** No code sharing between pages. Acceptable for small UI.

### Why No Real Miner Integration?

**Decision:** Milestone 1 uses a simulator.

**Rationale:**
- Decouples UI/control development from miner software
- Faster iteration
- Easier to test and demo

**Trade-off:** Simulator doesn't reflect real hashrate/temperature. Noted in acceptance criteria.

## Future Enhancements

### Planned

- **Real miner backend:** Replace simulator with actual mining software
- **Secure remote access:** Optional TLS and authentication for LAN+ access
- **Hermes integration:** Full Hermes gateway adapter
- **Historical data:** Time-series storage for hashrate charts
- **Multi-device sync:** Encrypted state synchronization

### Not Planned

- **Internet-exposed control** in phase one
- **Payout-target mutation** in phase one
- **Public feeds or social features**
- **On-device mining**

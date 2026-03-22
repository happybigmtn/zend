# Architecture

This document describes the Zend Home system architecture, module responsibilities, data flow, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Zend Home System                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────┐      ┌──────────────────────────────────────────────┐ │
│   │   Phone     │      │              Home Miner (Linux)              │ │
│   │  Browser    │      │                                               │ │
│   │             │      │   ┌────────────────────────────────────────┐  │ │
│   │  index.html │◄────►│   │       Home Miner Daemon              │  │ │
│   │  (Command   │HTTP  │   │         ThreadedHTTPServer             │  │ │
│   │   Center)   │      │   │            GatewayHandler               │  │ │
│   │             │      │   │                                       │  │ │
│   │ Fetches     │      │   │  GET  /health      → miner.health     │  │ │
│   │ /status     │      │   │  GET  /status      → miner.snapshot   │  │ │
│   │ every 5s    │      │   │  POST /miner/start → miner.start      │  │ │
│   │             │      │   │  POST /miner/stop  → miner.stop       │  │ │
│   └─────────────┘      │   │  POST /miner/mode  → miner.set_mode   │  │ │
│                        │   └─────────────────┬────────────────────┘  │ │
│   ┌─────────────┐      │                      │                        │ │
│   │   CLI       │      │                      │                        │ │
│   │  (Python)   │      │                      ▼                        │ │
│   │             │      │   ┌────────────────────────────────────────┐  │ │
│   │ Commands:   │      │   │          MinerSimulator                │  │ │
│   │ - bootstrap│◄────►│   │                                        │  │ │
│   │ - pair     │HTTP  │   │  status: running|stopped|offline|error  │  │ │
│   │ - status   │      │   │  mode:   paused|balanced|performance   │  │ │
│   │ - control  │      │   │  hashrate_hs: 0|50000|150000           │  │ │
│   │ - events   │      │   │  temperature: float                    │  │ │
│   │             │      │   │  uptime_seconds: int                   │  │ │
│   └─────────────┘      │   └────────────────────────────────────────┘  │ │
│                        │                                               │ │
│                        │   ┌──────────────────┐  ┌─────────────────┐   │ │
│                        │   │   Event Spine    │  │  Pairing Store  │   │ │
│                        │   │ (event-spine.jsonl) │(pairing-store.json)│ │
│                        │   │   Append-only     │  │  Key-value     │   │ │
│                        │   │   JSONL journal   │  │  documents     │   │ │
│                        │   └──────────────────┘  └─────────────────┘   │ │
│                        │                                               │ │
│                        │   ┌──────────────────┐                         │ │
│                        │   │    Principal     │                         │ │
│                        │   │(principal.json)  │                         │ │
│                        │   │  Stable identity │                         │ │
│                        │   └──────────────────┘                         │ │
│                        └───────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### daemon.py — HTTP Server and Miner Simulator

**Location:** `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP server exposing the daemon API and simulating miner state for milestone 1.

**Key Classes:**

```python
class MinerSimulator:
    """Simulates miner state for milestone 1."""
    
    @property
    def status(self) -> MinerStatus:
        """Current miner status."""
    
    @property
    def mode(self) -> MinerMode:
        """Current operating mode."""
    
    def start(self) -> dict:
        """Start mining. Returns success/error."""
    
    def stop(self) -> dict:
        """Stop mining. Returns success/error."""
    
    def set_mode(self, mode: str) -> dict:
        """Change mode. Returns success/error."""
    
    def get_snapshot(self) -> dict:
        """Return complete status snapshot."""
    
    def health(self) -> dict:
        """Return health status."""
```

```python
class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler for all endpoints."""
    
    def do_GET(self):
        # /health → miner.health
        # /status → miner.snapshot
    
    def do_POST(self):
        # /miner/start → miner.start
        # /miner/stop → miner.stop
        # /miner/set_mode → miner.set_mode
```

```python
class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded server for concurrent requests."""
```

**State Managed:**
- Miner status (running/stopped/offline/error)
- Operating mode (paused/balanced/performance)
- Simulated hashrate and temperature
- Uptime counter

**Key Constants:**
```python
STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
BIND_PORT = int(os.environ.get('ZEND_BIND_PORT', 8080))
```

---

### cli.py — Command-Line Interface

**Location:** `services/home-miner-daemon/cli.py`

**Purpose:** User-facing CLI for pairing, status, control, and event queries.

**Commands:**

| Command | Purpose | Auth Required |
|---------|---------|----------------|
| `bootstrap` | Create principal, emit pairing | None |
| `pair` | Pair new client device | None |
| `status` | Read miner status | `observe` |
| `health` | Check daemon health | None |
| `control` | Control miner (start/stop/mode) | `control` |
| `events` | Query event spine | `observe` |

**Key Functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make HTTP call to daemon."""
    # Constructs URL from ZEND_DAEMON_URL
    # Returns parsed JSON response
    # Returns {"error": "daemon_unavailable"} on connection failure
```

**Authorization Flow:**
1. Check pairing exists for device name
2. Verify device has required capability
3. Return error if unauthorized

---

### spine.py — Event Spine

**Location:** `services/home-miner-daemon/spine.py`

**Purpose:** Append-only encrypted event journal. Source of truth for all operational events.

**Key Classes:**

```python
class SpineEvent:
    """An event in the append-only journal."""
    id: str              # UUID v4
    principal_id: str    # References PrincipalId
    kind: str            # EventKind value
    payload: dict        # Encrypted payload
    created_at: str      # ISO 8601 timestamp
    version: int         # Schema version (1)
```

**Event Kinds:**

| Kind | Trigger | Payload |
|------|---------|---------|
| `pairing_requested` | `pair_client()` | device_name, requested_capabilities |
| `pairing_granted` | `pair_client()` | device_name, granted_capabilities |
| `capability_revoked` | Future | device_name, revoked_capabilities, reason |
| `miner_alert` | Future | alert_type, message |
| `control_receipt` | `cmd_control()` | command, mode, status, receipt_id |
| `hermes_summary` | Future | summary_text, authority_scope, generated_at |
| `user_message` | Future | thread_id, sender_id, encrypted_content |

**Storage:** `state/event-spine.jsonl` (newline-delimited JSON)

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append new event to spine. Returns created event."""
    # Creates SpineEvent with UUID
    # Appends JSON to spine file
    # Returns event for confirmation

def get_events(kind: EventKind = None, limit: int = 100) -> list[SpineEvent]:
    """Query events, optionally filtered by kind."""
    # Loads all events from file
    # Filters by kind if specified
    # Returns most recent first, limited
```

**Design Decision:** JSONL format chosen over SQLite for:
- Simplicity (no external dependencies)
- Easy inspection (human-readable lines)
- Append-only semantics match JSONL naturally
- No schema migrations needed

---

### store.py — Principal and Pairing Storage

**Location:** `services/home-miner-daemon/store.py`

**Purpose:** Manages principal identity and device pairing records.

**Key Classes:**

```python
@dataclass
class Principal:
    """Zend principal identity."""
    id: str          # UUID v4
    created_at: str  # ISO 8601
    name: str        # Display name

@dataclass
class GatewayPairing:
    """Paired gateway client record."""
    id: str                    # UUID v4
    principal_id: str          # References Principal
    device_name: str           # Client identifier
    capabilities: list        # ['observe', 'control']
    paired_at: str             # ISO 8601
    token_expires_at: str      # ISO 8601
    token_used: bool           # Token consumed
```

**Storage Files:**
- `state/principal.json` — Single principal identity
- `state/pairing-store.json` — Dictionary of pairing records

**Key Functions:**

```python
def load_or_create_principal() -> Principal:
    """Load existing or create new principal."""
    # If principal.json exists, load it
    # Otherwise, create new with UUID
    # Returns Principal

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create new pairing record."""
    # Checks for duplicate device_name
    # Creates pairing with token
    # Saves to pairing-store.json
    # Returns GatewayPairing

def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""
    # Looks up pairing by device_name
    # Returns True if capability in list

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Get pairing record by device name."""

def list_devices() -> list[GatewayPairing]:
    """List all paired devices."""
```

---

### index.html — Mobile Command Center

**Location:** `apps/zend-home-gateway/index.html`

**Purpose:** Single-file mobile interface for miner control and monitoring.

**Screens:**

| Screen | Purpose | Key Elements |
|--------|---------|---------------|
| Home | Status overview | Status hero, mode switcher, start/stop, latest receipt |
| Inbox | Operations log | Receipt cards, alerts |
| Agent | Hermes status | Connection status (future) |
| Device | Device info | Paired device, permissions |

**API Integration:**
```javascript
const API_BASE = 'http://127.0.0.1:8080';

async function fetchStatus() {
    const resp = await fetch(`${API_BASE}/status`);
    const data = await resp.json();
    // Update state...
}
```

**Refresh Strategy:** Fetches `/status` every 5 seconds.

**Local Storage:**
- `zend_principal_id` — Principal ID
- `zend_device_name` — Device name

**Design:** See `DESIGN.md` for typography, colors, and component specs.

---

## Data Flow

### Control Command Flow

```
User clicks "Start Mining" in command center
         │
         ▼
POST /miner/start
         │
         ▼
GatewayHandler.do_POST()
         │
         ▼
miner.start()
         │
         ├─ Lock acquired
         ├─ Set status = RUNNING
         ├─ Set hashrate based on mode
         ├─ Return success
         │
         ▼
spine.append_control_receipt('start', None, 'accepted', principal_id)
         │
         ├─ Create SpineEvent
         └─ Append to event-spine.jsonl
         │
         ▼
Response: {"success": true, "status": "running"}
         │
         ▼
Command center receives response
         │
         ▼
Update UI: indicator green, status "Running", hashrate display
         │
         ▼
Next fetch (5s): GET /status returns updated snapshot
```

### Pairing Flow

```
python3 cli.py pair --device my-phone --capabilities observe,control
         │
         ▼
load_or_create_principal()
         │
         ├─ Check principal.json exists
         ├─ If not, create new with UUID
         └─ Return Principal
         │
         ▼
pair_client('my-phone', ['observe', 'control'])
         │
         ├─ Check for duplicate device_name
         ├─ Create pairing with token
         └─ Save to pairing-store.json
         │
         ▼
spine.append_pairing_requested(...)
spine.append_pairing_granted(...)
         │
         ▼
Output: {"success": true, "device_name": "my-phone", ...}
```

---

## Auth Model

### Principal Identity

The `Principal` is the stable identity for a Zend installation:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-22T12:00:00+00:00",
  "name": "Zend Home"
}
```

A single principal can have multiple paired devices. All devices share the same principal identity.

### Gateway Pairing

Each paired device has a `GatewayPairing` record:

```json
{
  "id": "...",
  "principal_id": "550e8400-...",
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00+00:00",
  "token_expires_at": "...",
  "token_used": false
}
```

### Capabilities

| Capability | Grants Access To |
|------------|------------------|
| `observe` | GET /health, GET /status, events list |
| `control` | All observe + POST /miner/* |

Capabilities are assigned during pairing and checked by the CLI before executing control commands.

### Token Model

- Each pairing has a token with expiration
- Token is generated during `pair_client()`
- Future: tokens will be required in API requests
- Future: tokens can be revoked to remove device access

---

## Event Spine Design

### Append-Only Semantics

The event spine is append-only. Events cannot be modified or deleted. This ensures:

1. **Audit trail:** Complete history of all operations
2. **Replay:** Inbox can be rebuilt from spine at any time
3. **Consistency:** No partial updates or race conditions

### Event Structure

```jsonl
{"id": "uuid", "principal_id": "...", "kind": "pairing_granted", "payload": {...}, "created_at": "...", "version": 1}
{"id": "uuid", "principal_id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "...", "version": 1}
...
```

### Routing Rules

| Event Kind | Destination |
|------------|-------------|
| `pairing_requested` / `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home and Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox and Agent |
| `user_message` | Inbox |

### Future: Encryption

Planned: All payloads encrypted using principal's identity key before writing to spine.

---

## Design Decisions

### Why Standard Library Only

**Decision:** Use Python standard library, no external dependencies.

**Rationale:**
- No dependency hell or version conflicts
- Works in restricted environments (no pip)
- Easier to audit and review
- Milestone 1 doesn't need external libraries
- Reduces attack surface

**Trade-off:** More verbose code for HTTP handling, JSON parsing.

### Why LAN-Only Binding

**Decision:** Daemon binds to localhost by default, optionally LAN.

**Rationale:**
- Security through isolation
- Home miners don't need public internet exposure
- Simpler threat model
- No need for TLS in milestone 1

**Trade-off:** Requires separate access method for remote management.

### Why JSONL Not SQLite

**Decision:** Use JSONL (newline-delimited JSON) for event spine.

**Rationale:**
- No external dependencies
- Human-readable for debugging
- Append-only semantics match JSONL naturally
- Easy to backup (copy file)
- No schema migrations needed
- Can use standard tools (grep, jq) for inspection

**Trade-off:** Slower for large queries (must scan all events).

### Why Single HTML File

**Decision:** Command center is a single HTML file, no build step.

**Rationale:**
- Works from filesystem without server
- No frontend toolchain required
- Easy to audit (all code visible)
- Can be hosted anywhere
- Simple deployment

**Trade-off:** No bundling, larger initial payload, no hot reload during development.

### Why Mobile-First

**Decision:** Design primarily for phone browser, expand to desktop later.

**Rationale:**
- Primary use case is on-the-go control
- Mobile design forces simplicity
- Desktop is progressive enhancement

**Trade-off:** Some desktop workflows less optimized.

---

## Future Architecture

### Phase 2: Real Mining Integration

- Replace `MinerSimulator` with real mining daemon integration
- Add WebSocket for real-time updates
- Add TLS and authentication

### Phase 3: Hermes Integration

- Connect Hermes agent for automated decisions
- Add `hermes_summary` events
- Add authority scope management

### Phase 4: Multi-Device Support

- Add device management UI
- Implement token revocation
- Add device permission granular control

### Phase 5: Encrypted Spine

- Encrypt payloads using principal identity key
- Add key derivation from seed phrase
- Support encrypted memo transport

---

## Glossary

| Term | Definition |
|------|------------|
| **Principal** | Stable identity for a Zend installation |
| **Pairing** | Association of a device name with capabilities |
| **Capability** | Permission to access specific endpoints |
| **Event Spine** | Append-only journal of all operational events |
| **Inbox** | Derived view of event spine for display |
| **Gateway** | The HTTP server exposing the daemon API |
| **Simulator** | Milestone 1 replacement for real mining hardware |

---

## Related Documents

- [Event Spine Contract](../references/event-spine.md) — Detailed event schema
- [Inbox Contract](../references/inbox-contract.md) — Inbox architecture
- [Design System](../DESIGN.md) — Visual and interaction design
- [API Reference](./api-reference.md) — Endpoint documentation

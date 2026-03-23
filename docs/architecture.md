# Architecture

This document describes the Zend system architecture, module design, and design decisions. Use this to understand how components fit together and where to make changes.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Module Guide](#module-guide)
4. [Data Flow](#data-flow)
5. [Auth Model](#auth-model)
6. [Event Spine](#event-spine)
7. [Design Decisions](#design-decisions)

---

## System Overview

Zend is a private command center for home mining. The system has three main components:

1. **Home Miner Daemon** (`services/home-miner-daemon/`)
   - HTTP API server that exposes miner control
   - Manages principal identity and device pairings
   - Records all operations to the event spine

2. **Command Center** (`apps/zend-home-gateway/`)
   - Single HTML file with CSS and JavaScript
   - Mobile-first web interface for monitoring and control
   - Connects to daemon via HTTP API

3. **Scripts** (`scripts/`)
   - Shell scripts for bootstrap, pairing, and control
   - Wrapper scripts for CLI operations
   - Audit and integration scripts

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Zend Architecture                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────────┐                                                   │
│   │  Command Center  │                                                   │
│   │  (index.html)   │                                                   │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            │ HTTP API                                                    │
│            │ (health, status, miner/*)                                  │
│            ▼                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                    Home Miner Daemon                              │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│   │  │ daemon.py  │  │   cli.py    │  │  spine.py   │  │  store.py  │  │  │
│   │  │            │  │             │  │            │  │            │  │  │
│   │  │ HTTP Server│  │ CLI Wrapper │  │ Event Spine │  │ Pairing &  │  │  │
│   │  │ MinerSim   │  │             │  │  Journal    │  │ Principal  │  │  │
│   │  └─────┬───────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘  │  │
│   │        │                 │                 │               │        │  │
│   │        └─────────────────┼─────────────────┘               │        │  │
│   │                          │                                  │        │  │
│   │                          ▼                                  │        │  │
│   │              ┌──────────────────┐                          │        │  │
│   │              │   state/         │                          │        │  │
│   │              │  principal.json  │◄─────────────────────────┘        │  │
│   │              │  pairing.json   │                                  │  │
│   │              │  event-spine.jsonl                                 │  │
│   │              └──────────────────┘                                  │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│   ┌──────────────────┐        ┌──────────────────┐                        │
│   │ Hermes Adapter   │───────►│ Hermes Gateway  │                        │
│   │ (observe only)  │        │ / Agent         │                        │
│   └──────────────────┘        └──────────────────┘                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Module Guide

### daemon.py

**Location:** `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP API server and miner simulator.

**Key Classes:**

```python
class MinerSimulator:
    """Simulates mining hardware for milestone 1."""
    
    @property
    def status(self) -> MinerStatus:
        """Current miner state: running, stopped, offline, error."""
    
    @property
    def mode(self) -> MinerMode:
        """Operating mode: paused, balanced, performance."""
    
    def start(self) -> dict:
        """Start mining. Returns {"success": bool, "status": str}."""
    
    def stop(self) -> dict:
        """Stop mining. Returns {"success": bool, "status": str}."""
    
    def set_mode(self, mode: str) -> dict:
        """Change mode. Returns {"success": bool, "mode": str}."""
    
    def get_snapshot(self) -> dict:
        """Returns current status for API response."""
```

```python
class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler for daemon API."""
    
    def do_GET(self):
        # /health - Daemon health check
        # /status - Miner status snapshot
    
    def do_POST(self):
        # /miner/start - Start mining
        # /miner/stop - Stop mining
        # /miner/set_mode - Change mode
```

**State:** In-memory `MinerSimulator` instance. No persistence (simulated state).

---

### cli.py

**Location:** `services/home-miner-daemon/cli.py`

**Purpose:** Command-line interface for daemon interaction.

**Commands:**

```bash
# Health check
python3 cli.py health

# Status
python3 cli.py status
python3 cli.py status --client my-phone

# Bootstrap
python3 cli.py bootstrap --device my-phone

# Pairing
python3 cli.py pair --device my-phone --capabilities observe,control

# Control
python3 cli.py control --client my-phone --action start
python3 cli.py control --client my-phone --action stop
python3 cli.py control --client my-phone --action set_mode --mode balanced

# Events
python3 cli.py events --limit 10
python3 cli.py events --kind control_receipt --limit 5
```

**Key Functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make HTTP call to daemon."""
```

---

### spine.py

**Location:** `services/home-miner-daemon/spine.py`

**Purpose:** Append-only event journal for audit trail and inbox.

**Event Kinds:**

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Device paired successfully |
| `capability_revoked` | Capability removed from device |
| `miner_alert` | Miner warning or error |
| `control_receipt` | Control action accepted/rejected |
| `hermes_summary` | Hermes adapter summary |
| `user_message` | User message (future) |

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append event to spine. Returns created event."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    """Get events, optionally filtered by kind. Returns newest first."""

def append_pairing_granted(device_name: str, capabilities: list, principal_id: str):
    """Convenience: append pairing_granted event."""

def append_control_receipt(command: str, mode: Optional[str], status: str, principal_id: str):
    """Convenience: append control_receipt event."""
```

**Storage:** `state/event-spine.jsonl` (JSON Lines format)

**Format:**
```jsonl
{"id": "...", "principal_id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "...", "version": 1}
{"id": "...", "principal_id": "...", "kind": "pairing_granted", "payload": {...}, "created_at": "...", "version": 1}
```

---

### store.py

**Location:** `services/home-miner-daemon/store.py`

**Purpose:** Principal identity and device pairing management.

**Key Classes:**

```python
@dataclass
class Principal:
    """Zend principal identity."""
    id: str              # UUID
    created_at: str      # ISO 8601
    name: str            # Human-readable name

@dataclass
class GatewayPairing:
    """Paired gateway client."""
    id: str              # UUID
    principal_id: str    # Links to Principal
    device_name: str     # Human-readable device name
    capabilities: list  # ["observe"], ["observe", "control"]
    paired_at: str      # ISO 8601
    token_expires_at: str
    token_used: bool
```

**Key Functions:**

```python
def load_or_create_principal() -> Principal:
    """Load existing principal or create new one."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create pairing record. Raises ValueError if device already paired."""

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Get pairing record by device name."""

def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""

def list_devices() -> list[GatewayPairing]:
    """List all paired devices."""
```

**Storage:** 
- `state/principal.json`
- `state/pairing-store.json`

---

## Data Flow

### Control Command Flow

```
Client                    Daemon                    State
  │                         │                         │
  │ POST /miner/set_mode    │                         │
  │ ───────────────────────►│                         │
  │                         │                         │
  │                         │ Validate request        │
  │                         │                         │
  │                         │ Update MinerSimulator   │
  │                         │ ───────────────────────►│
  │                         │                         │
  │                         │ Append to spine         │
  │                         │ ───────────────────────►│
  │                         │                         │
  │ {"success": true}       │                         │
  │ ◄───────────────────────│                         │
  │                         │                         │
```

### Pairing Flow

```
Operator                  CLI                       Daemon                    State
  │                        │                          │                         │
  │ pair --device X        │                          │                         │
  │ ─────────────────────►│                          │                         │
  │                        │                          │                         │
  │                        │ pair_client(X, caps)     │                         │
  │                        │ ────────────────────────►│                         │
  │                        │                          │                         │
  │                        │                          │ Create pairing          │
  │                        │                          │ ───────────────────────►│
  │                        │                          │                         │
  │                        │                          │ Append pairing events   │
  │                        │                          │ ───────────────────────►│
  │                        │                          │                         │
  │                        │ {"success": true, ...}  │                         │
  │                        │ ◄───────────────────────│                         │
  │ {"success": true, ...}│                          │                         │
  │ ◄─────────────────────│                          │                         │
  │                        │                          │                         │
```

---

## Auth Model

### Capabilities

Every paired device has a set of capabilities:

| Capability | Description | Operations Allowed |
|------------|-------------|-------------------|
| `observe` | Read-only access | `/health`, `/status`, events |
| `control` | Write access | `/miner/start`, `/miner/stop`, `/miner/set_mode` |

### Authorization Flow

```
Request ──► Check pairing exists ──► Check capability ──► Execute
              │                        │
              ▼                        ▼
         404 error              403 unauthorized
```

**Note:** The milestone 1 HTTP API does not enforce authorization. Authorization is enforced by the CLI via `has_capability()`.

---

## Event Spine

### Design Principles

1. **Append-only**: Events are never deleted or modified
2. **Ordered**: Events have timestamps and are queryable by kind
3. **Structured**: Each event has a type, payload, and metadata
4. **Projected**: The inbox is a view of filtered spine events

### Event Schema

```python
@dataclass
class SpineEvent:
    id: str           # UUID, unique identifier
    principal_id: str # Owner's principal
    kind: str         # EventKind value
    payload: dict     # Event-specific data
    created_at: str   # ISO 8601 timestamp
    version: int      # Schema version (currently 1)
```

### Querying Events

```bash
# All events (newest first)
python3 cli.py events --limit 10

# Control receipts only
python3 cli.py events --kind control_receipt --limit 10

# Pairing events
python3 cli.py events --kind pairing_granted --limit 5
```

### Future Inbox Integration

The event spine is designed to support the future inbox product:

- Same `principal_id` for gateway and inbox
- Same `SpineEvent` schema for all event kinds
- Inbox will be a projection with filtering by `kind`

---

## Design Decisions

### Why Python Standard Library Only?

**Decision:** No external Python dependencies.

**Rationale:**
- Zero dependency management overhead
- Works out of the box on any Python 3.10+ installation
- No pip, no virtual environment required
- Easier deployment on constrained hardware (Raspberry Pi)

**Trade-offs:**
- Less expressiveness than a web framework (Flask, FastAPI)
- Manual HTTP handling
- No type validation framework

### Why LAN-Only by Default?

**Decision:** Daemon binds to `127.0.0.1` by default.

**Rationale:**
- Reduces attack surface for milestone 1
- No TLS/certificate management needed
- Works within trusted home network
- Simpler for users to understand

**Trade-offs:**
- Requires VPN or SSH tunnel for remote access
- Not suitable for internet-exposed deployment yet

### Why JSONL for Event Spine?

**Decision:** Use JSON Lines (one JSON object per line) format.

**Rationale:**
- Append-only by design (no file locking for writes)
- Easy to tail with `tail -f`
- Simple to parse line-by-line
- Human-readable for debugging
- Can be processed with standard Unix tools

**Trade-offs:**
- No transactions across multiple events
- No indexing (full scan for queries)
- Not suitable for high-frequency writes (future concern)

### Why Single HTML File?

**Decision:** Command center is a single `index.html` file.

**Rationale:**
- No build step required
- Can be served statically or opened directly
- Easy to transfer to phone via AirDrop, email, USB
- No framework or bundler dependencies

**Trade-offs:**
- No code splitting or lazy loading
- All CSS/JS in one file
- No module system

### Why Mobile-First Design?

**Decision:** Command center targets mobile browser as primary client.

**Rationale:**
- Home mining is a mobile control scenario
- Easier to expand to desktop than vice versa
- Forces simplicity in UI design
- Aligns with "phone as control plane" product thesis

### Why Simulated Miner?

**Decision:** Milestone 1 uses a miner simulator, not real mining software.

**Rationale:**
- Proves the control contract without mining hardware
- Faster iteration on UI/UX
- Deterministic testing
- Separates gateway implementation from miner integration

**Trade-offs:**
- Doesn't test real mining integration
- Simulated hashrate doesn't reflect actual performance

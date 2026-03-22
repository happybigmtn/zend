# Architecture

Deep dive into Zend's system architecture, modules, and data flows.

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

Zend has four main components:

1. **Home Miner Daemon** — HTTP server that exposes miner control and status
2. **Miner Simulator** — Simulates miner behavior for milestone 1
3. **Pairing Store** — Manages device identities and capabilities
4. **Event Spine** — Append-only journal of all operations

```
┌─────────────────────────────────────────────────────────────────┐
│                         Zend System                              │
│                                                                 │
│   ┌──────────────┐         ┌─────────────────────────────┐   │
│   │   Browser    │         │   Home Miner Daemon          │   │
│   │   Client     │◄───────►│   (ThreadedHTTPServer)       │   │
│   │  (HTML/JS)   │  HTTP   │                             │   │
│   └──────────────┘         │  ┌───────────────────────┐  │   │
│                            │  │   GatewayHandler     │  │   │
│                            │  │   (HTTP endpoints)    │  │   │
│                            │  └───────────┬───────────┘  │   │
│                            │              │              │   │
│                            │  ┌───────────▼───────────┐  │   │
│                            │  │   MinerSimulator      │  │   │
│                            │  │   (Status + Control)  │  │   │
│                            │  └───────────────────────┘  │   │
│                            │                             │   │
│                            │  ┌───────────────────────┐  │   │
│                            │  │   Store               │  │   │
│                            │  │   (Principal, Pairing)│  │   │
│                            │  └───────────┬───────────┘  │   │
│                            │              │              │   │
│                            │  ┌───────────▼───────────┐  │   │
│                            │  │   Spine                │  │   │
│                            │  │   (Event Journal)     │  │   │
│                            │  └───────────────────────┘  │   │
│                            └─────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Diagram

```
  User's Phone                          Home Hardware
  ┌────────────┐                        ┌────────────────────────┐
  │            │                        │                        │
  │  Browser   │                        │   Zend Daemon          │
  │            │                        │   ┌──────────────────┐  │
  │            │──── HTTP ──────────────►│   │ GatewayHandler   │  │
  │            │◄─── JSON ──────────────│   │                  │  │
  │            │                        │   │ GET  /health     │  │
  │            │                        │   │ GET  /status      │  │
  │            │                        │   │ POST /miner/start │  │
  │            │                        │   │ POST /miner/stop  │  │
  │            │                        │   │ POST /miner/set   │  │
  │            │                        │   └────────┬─────────┘  │
  │            │                        │            │            │
  │            │                        │   ┌────────▼─────────┐  │
  │            │                        │   │ MinerSimulator   │  │
  │            │                        │   │                  │  │
  │            │                        │   │ status: running  │  │
  │            │                        │   │ mode: balanced   │  │
  │            │                        │   │ hashrate: 50k    │  │
  │            │                        │   └──────────────────┘  │
  └────────────┘                        │                        │
                                         │   ┌──────────────────┐  │
                                         │   │ Store            │  │
                                         │   │                  │  │
                                         │   │ principal.json   │  │
                                         │   │ pairing.json     │  │
                                         │   └──────────────────┘  │
                                         │                        │
                                         │   ┌──────────────────┐  │
                                         │   │ Spine            │  │
                                         │   │                  │  │
                                         │   │ event-spine.jsonl│  │
                                         │   └──────────────────┘  │
                                         └────────────────────────┘
```

---

## Module Guide

### daemon.py

**Purpose:** HTTP server and miner simulator.

**Key Classes:**

```python
class MinerSimulator:
    """Simulates miner for milestone 1."""

    def start(self) -> dict:
        """Start mining. Returns success/error."""

    def stop(self) -> dict:
        """Stop mining. Returns success/error."""

    def set_mode(self, mode: str) -> dict:
        """Set mode: paused, balanced, performance."""

    def get_snapshot(self) -> dict:
        """Return cached status for clients."""

class GatewayHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests to /health, /status, /miner/*."""
```

**State:** None persistent. Resets on restart.

**Endpoints:** `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`

---

### cli.py

**Purpose:** Command-line interface for operators.

**Commands:**

```bash
# Daemon health
python3 cli.py health

# Miner status
python3 cli.py status [--client <name>]

# Bootstrap principal
python3 cli.py bootstrap [--device <name>]

# Pair a client
python3 cli.py pair --device <name> --capabilities <list>

# Control miner
python3 cli.py control --client <name> --action <start|stop|set_mode> [--mode <mode>]

# Query events
python3 cli.py events [--client <name>] [--kind <kind>] [--limit <n>]
```

**Auth Checks:** CLI checks capabilities before allowing operations.
- `status` requires `observe` or `control`
- `control` requires `control`

---

### store.py

**Purpose:** Principal identity and pairing records.

**Key Functions:**

```python
def load_or_create_principal() -> Principal:
    """Load existing principal or create new one."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create pairing record. Fails if device already paired."""

def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Get pairing by device name."""
```

**Data Model:**

```python
@dataclass
class Principal:
    id: str          # UUID v4
    created_at: str  # ISO 8601
    name: str        # "Zend Home"

@dataclass
class GatewayPairing:
    id: str              # UUID v4
    principal_id: str    # References Principal
    device_name: str     # Human-readable name
    capabilities: list    # ["observe", "control"]
    paired_at: str       # ISO 8601
    token_expires_at: str
    token_used: bool
```

**Storage:** JSON files in `state/`
- `state/principal.json`
- `state/pairing-store.json`

---

### spine.py

**Purpose:** Append-only event journal.

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

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append new event to spine."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    """Query events, optionally filtered by kind."""

def append_pairing_requested(device_name, capabilities, principal_id):
    """Append pairing requested event."""

def append_pairing_granted(device_name, capabilities, principal_id):
    """Append pairing granted event."""

def append_control_receipt(command, mode, status, principal_id):
    """Append control receipt event."""
```

**Storage:** JSONL file `state/event-spine.jsonl`
- One JSON object per line
- Append-only (never modify or delete)

**Event Schema:**

```json
{
  "id": "uuid-v4",
  "principal_id": "uuid-v4",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "uuid-v4"
  },
  "created_at": "2026-03-22T12:00:00Z",
  "version": 1
}
```

---

## Data Flow

### Control Command Flow

```
User clicks "Set Mode: Balanced"
         │
         ▼
Browser sends POST /miner/set_mode
         │
         ▼
GatewayHandler.do_POST()
         │
         ▼
MinerSimulator.set_mode("balanced")
         │
         ├──► Update internal state
         │
         ▼
Return {"success": true, "mode": "balanced"}
         │
         ▼
Browser updates UI
```

### Pairing Flow

```
Operator runs: pair --device my-phone --capabilities observe,control
         │
         ▼
CLI calls store.pair_client()
         │
         ├──► Create GatewayPairing record
         ├──► Save to state/pairing-store.json
         │
         ▼
CLI calls spine.append_pairing_requested()
         │
         ▼
CLI calls spine.append_pairing_granted()
         │
         ▼
Print success JSON
```

### Event Query Flow

```
User opens Inbox tab
         │
         ▼
Browser calls: python3 cli.py events --limit 20
         │
         ▼
CLI calls spine.get_events(limit=20)
         │
         ├──► Read state/event-spine.jsonl
         ├──► Parse each line as JSON
         ├──► Return as list of SpineEvent
         │
         ▼
Format and display events
```

---

## Auth Model

### Capability Scopes

| Capability | Operations Allowed |
|------------|-------------------|
| `observe` | Read status, query events |
| `control` | Start/stop mining, change modes |

### Capability Check Flow

```python
def cmd_control(args):
    # 1. Check if device has 'control'
    if not has_capability(args.client, 'control'):
        print({"error": "unauthorized", "message": "..."})
        return 1

    # 2. Proceed with control action
    result = daemon_call('POST', '/miner/set_mode', ...)
```

### Token Expiry

Pairing tokens have an expiration time stored in the pairing record.
Token expiry validation is not yet implemented in milestone 1.

---

## Event Spine

### Append-Only Guarantee

The spine is append-only. Events are never modified or deleted.

```
Line 1: {"id": "...", "kind": "pairing_granted", ...}
Line 2: {"id": "...", "kind": "control_receipt", ...}
Line 3: {"id": "...", "kind": "control_receipt", ...}
Line 4: {"id": "...", "kind": "miner_alert", ...}
```

### Query Patterns

```python
# All events
events = get_events()

# Control receipts only
events = get_events(kind=EventKind.CONTROL_RECEIPT)

# Last 10 events
events = get_events(limit=10)
```

### Inbox Projection

The inbox is a derived view of the spine. It filters and formats events
for display:

```python
def get_inbox_events():
    """Get events for inbox display."""
    events = get_events(limit=50)
    return [format_for_inbox(e) for e in events]
```

---

## Design Decisions

### Why Stdlib Only?

**Decision:** No external Python dependencies.

**Rationale:**
- Zero install requirements
- Portable across Python versions
- No dependency conflicts
- Simpler security surface

**Trade-off:** More code to write (e.g., custom HTTP server instead of Flask).

### Why LAN-Only by Default?

**Decision:** Daemon binds to `127.0.0.1` in milestone 1.

**Rationale:**
- Lowest blast radius
- No exposure to internet
- Trust local network only
- Can add remote access later with proper auth

**Trade-off:** Can't control from outside the home network.

### Why JSONL for Spine?

**Decision:** Store events as newline-delimited JSON.

**Rationale:**
- Append-only friendly (no locking)
- Human-readable for debugging
- Streaming-friendly
- Simple implementation

**Trade-off:** Not as fast as SQLite for complex queries.

### Why Single HTML File?

**Decision:** Gateway UI is one `index.html` with inline CSS/JS.

**Rationale:**
- No build step
- Serve from anywhere
- Easy to audit
- Offline-capable

**Trade-off:** No bundling or optimization.

### Why Simulator for Miner?

**Decision:** Milestone 1 uses a simulator, not a real miner.

**Rationale:**
- No mining hardware required
- Faster iteration
- Same API contract
- Proves the product shape

**Trade-off:** Doesn't test real mining behavior.

### Why Explicit Control Receipts?

**Decision:** Every control action produces a receipt event.

**Rationale:**
- Complete audit trail
- User can see what happened
- Hermes can summarize
- Recovery possible

**Trade-off:** More storage over time.

---

## File Locations

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/daemon.py` | HTTP server + miner |
| `services/home-miner-daemon/cli.py` | CLI interface |
| `services/home-miner-daemon/store.py` | Principal + pairing |
| `services/home-miner-daemon/spine.py` | Event spine |
| `state/principal.json` | Principal identity |
| `state/pairing-store.json` | Device pairings |
| `state/event-spine.jsonl` | Event journal |
| `apps/zend-home-gateway/index.html` | Browser UI |

---

## Future Changes

| Area | Plan |
|------|------|
| Real miner backend | Replace MinerSimulator with actual miner API |
| Remote access | Add authentication and TLS for internet access |
| Payout control | Add payout-target mutation with stronger auth |
| Event compaction | Add spine archival for long-running deployments |
| Metrics | Add Prometheus-compatible metrics endpoint |

---

*Last updated: 2026-03-22*

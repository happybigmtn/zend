# Architecture

This document describes Zend's system architecture, module responsibilities, data flows, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Mobile Client                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Zend Home Gateway (HTML + JavaScript)                 │    │
│  │  - Status Hero     - Mode Switcher     - Quick Actions │    │
│  │  - Inbox View      - Agent Panel       - Device Info   │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/JSON
                            │ LAN Only
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Home Miner Daemon                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ GatewayHandler│  │MinerSimulator│  │ MinerSnapshot Cache  │  │
│  │  (HTTP API)   │  │  (Simulator) │  │  (Freshness TTL)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   store.py   │  │  spine.py    │  │   Hermes Adapter     │  │
│  │ (PrincipalId)│  │(Event Spine) │  │  (Observe-Only)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐  ┌───────────┐  ┌─────────────────┐
│ state/principal │  │ state/    │  │ state/event-    │
│     .json       │  │ pairing   │  │ spine.jsonl     │
│                 │  │ -store.json│ │                 │
└─────────────────┘  └───────────┘  └─────────────────┘
```

## Module Guide

### daemon.py — HTTP Server & Miner Simulator

**Purpose:** HTTP API server that exposes miner control endpoints and a simulator for development.

**Key Classes:**

```python
class MinerSimulator:
    """Simulates miner hardware for milestone 1."""
    
    def start() -> dict
    def stop() -> dict
    def set_mode(mode: str) -> dict
    def get_snapshot() -> MinerSnapshot
    @property health() -> dict
```

```python
class GatewayHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests to the gateway API."""
    
    def do_GET()   # /health, /status
    def do_POST()  # /miner/start, /miner/stop, /miner/set_mode
```

**State:** None (stateless request handlers; miner state in memory)

**Thread Safety:** Uses `threading.Lock` for miner state mutations.

---

### store.py — Principal & Pairing Store

**Purpose:** Manages stable identity and device pairing records.

**Key Types:**

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
    capabilities: list  # ['observe'] or ['observe', 'control']
    paired_at: str
    token_expires_at: str
```

**Key Functions:**

```python
def load_or_create_principal() -> Principal
def pair_client(device_name: str, capabilities: list) -> GatewayPairing
def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
def has_capability(device_name: str, capability: str) -> bool
def list_devices() -> list[GatewayPairing]
```

**State:** Persistent in `state/principal.json` and `state/pairing-store.json`

---

### spine.py — Event Spine Journal

**Purpose:** Append-only encrypted event journal serving as the single source of truth.

**Key Types:**

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"

@dataclass
class SpineEvent:
    id: str
    principal_id: str
    kind: str
    payload: dict
    created_at: str
    version: int = 1
```

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]
```

**Payload Schemas:**

| Event Kind | Key Fields |
|------------|------------|
| `pairing_requested` | `device_name`, `requested_capabilities` |
| `pairing_granted` | `device_name`, `granted_capabilities` |
| `capability_revoked` | `device_name`, `revoked_capabilities`, `reason` |
| `miner_alert` | `alert_type`, `message` |
| `control_receipt` | `command`, `mode?`, `status`, `receipt_id` |
| `hermes_summary` | `summary_text`, `authority_scope`, `generated_at` |
| `user_message` | `thread_id`, `sender_id`, `encrypted_content` |

**State:** Append-only file at `state/event-spine.jsonl` (one JSON object per line)

---

### cli.py — Command-Line Interface

**Purpose:** Human-friendly CLI for testing, scripting, and operator use.

**Commands:**

```bash
# Health check
python3 cli.py health

# Status (with capability check)
python3 cli.py status --client alice-phone

# Control (requires control capability)
python3 cli.py control --client alice-phone --action start
python3 cli.py control --client alice-phone --action set_mode --mode balanced

# Bootstrap principal
python3 cli.py bootstrap --device alice-phone

# Pair new device
python3 cli.py pair --device my-phone --capabilities observe,control

# View events
python3 cli.py events --client alice-phone
python3 cli.py events --kind control_receipt --limit 10
```

---

## Data Flow

### Control Command Flow

```
Client Script/UI
       │
       │ 1. Check capability
       ▼
   store.py: has_capability(client, 'control')
       │
       │ (if no control → return unauthorized error)
       │
       ▼
   daemon_call(POST /miner/set_mode)
       │
       │ 2. Validate request
       ▼
   daemon.py: GatewayHandler.do_POST()
       │
       │ 3. Acquire lock, update state
       ▼
   MinerSimulator.set_mode()
       │
       │ 4. Append receipt to spine
       ▼
   spine.py: append_control_receipt()
       │
       │ 5. Return result
       ▼
   JSON response to client
```

### Status Read Flow

```
Client Script/UI
       │
       │ GET /status
       ▼
   daemon.py: GatewayHandler.do_GET()
       │
       │ Acquire lock, read state
       ▼
   MinerSimulator.get_snapshot()
       │
       │ Add freshness timestamp
       ▼
   Return MinerSnapshot
```

### Pairing Flow

```
Operator runs: bootstrap_home_miner.sh
       │
       │ 1. Create principal
       ▼
   store.py: load_or_create_principal()
       │
       │ 2. Create pairing
       ▼
   store.py: pair_client(device, capabilities)
       │
       │ 3. Append pairing events
       ▼
   spine.py: append_pairing_requested()
   spine.py: append_pairing_granted()
       │
       │ 4. Return pairing record
       ▼
   JSON with principal_id, device_name, capabilities
```

## Auth Model

### Principal Identity

A `PrincipalId` is a UUID v4 that represents the home operator. It is:
- Created once during bootstrap
- Shared across all systems (gateway, inbox, future features)
- Never changes

### Gateway Pairing

Each device that connects to the daemon has a pairing record:
- Unique device name
- Capability set
- Pairing timestamp
- Token expiration (for future token-based auth)

### Capability Scopes

| Capability | Permissions |
|------------|-------------|
| `observe` | Read status, view events |
| `control` | Start/stop/miner mode, also includes observe |

### Capability Enforcement

The daemon does not enforce capabilities directly. Instead:
1. CLI scripts check capabilities via `store.has_capability()`
2. Scripts only call daemon endpoints if capability check passes
3. HTML client relies on capability metadata for UI state

This design allows the daemon to remain simple while capability enforcement is tested in the CLI layer.

## Event Spine

### Design Principles

1. **Append-only:** Events cannot be modified or deleted
2. **Source of truth:** The inbox is a derived view, not a separate store
3. **Ordered:** Events are ordered by append time
4. **Principal-scoped:** All events reference a PrincipalId

### Query Patterns

```python
# Get all events (newest first)
events = get_events(limit=100)

# Get only control receipts
events = get_events(kind=EventKind.CONTROL_RECEIPT, limit=50)

# Get pairing events
events = get_events(kind=EventKind.PAIRING_GRANTED)
```

### Routing to Inbox

| Event Kind | Inbox Location |
|------------|----------------|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home (banner), Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox, Agent |
| `user_message` | Inbox |

## Design Decisions

### Why Stdlib Only?

**Decision:** The daemon uses only Python standard library.

**Rationale:**
- Minimal attack surface
- No dependency conflicts
- Easy deployment on constrained hardware (Raspberry Pi)
- Deterministic builds

**Consequence:** No external HTTP libraries, no JSON parsing libraries, no asyncio. All implementations use `http.server`, `json`, and `urllib`.

---

### Why LAN-Only by Default?

**Decision:** Daemon binds to `127.0.0.1` in milestone 1.

**Rationale:**
- Lowest blast radius for first deployment
- No authentication layer needed yet
- Easy local testing

**Consequence:** Phone must be on same machine or network. Remote access requires VPN or explicit LAN binding.

---

### Why JSONL for Event Spine?

**Decision:** Event spine is a JSON Lines file (`event-spine.jsonl`), not SQLite.

**Rationale:**
- Append-only is naturally represented
- Easy to tail with standard tools
- No database dependency
- Crash-safe (append is atomic at line boundaries)
- Human-readable for debugging

**Consequence:** No complex queries. Filtering requires reading and parsing lines.

---

### Why Single HTML File?

**Decision:** Gateway client is a single `index.html` with no build step.

**Rationale:**
- No bundler, no dependencies
- Opens directly in browser
- Easy to serve from any static host
- Works offline

**Consequence:** No component system, no routing, no state management library. Pure vanilla JS.

---

### Why Capability Scoping?

**Decision:** Gateway permissions are limited to `observe` and `control`.

**Rationale:**
- Simple mental model
- Clear blast radius for each capability
- Gradual trust building

**Deferred:** Payout-target mutation requires stronger capability model and audit trail.

---

### Why Simulator for Milestone 1?

**Decision:** Daemon ships with a miner simulator, not a real miner.

**Rationale:**
- Proof-of-concept without hardware dependency
- Faster development and testing
- Same API contract a real miner would use

**Consequence:** Real miner integration requires implementing the same interface.

---

## Security Notes

### Threat Model

- **Local network access:** Anyone on LAN can reach daemon
- **No authentication:** Device pairing is the only access control
- **No encryption:** Local HTTP only (LAN assumption)

### Mitigations

1. **LAN-only binding:** Default prevents internet exposure
2. **Capability scoping:** Observe-only devices cannot control
3. **Single command path:** All control goes through daemon
4. **No local hashing:** Audit scripts verify client is not mining

### Future Security

- TLS for LAN encryption
- Token-based authentication
- Capability delegation with expiration
- Audit log export

## File Structure

```
services/home-miner-daemon/
├── daemon.py          # HTTP server, miner simulator
├── store.py          # PrincipalId, pairing records
├── spine.py          # Event spine append/query
├── cli.py            # CLI commands
└── __init__.py

state/                 # Runtime state (git-ignored)
├── principal.json     # PrincipalId
├── pairing-store.json # Device pairings
├── event-spine.jsonl  # Event journal
└── daemon.pid         # Daemon process ID

apps/zend-home-gateway/
└── index.html        # Mobile-first command center UI
```

## Metrics & Observability

### Structured Log Events

| Event | When |
|-------|------|
| `gateway.bootstrap.started` | Bootstrap begins |
| `gateway.bootstrap.complete` | Bootstrap succeeds |
| `gateway.pairing.succeeded` | Device paired |
| `gateway.pairing.rejected` | Pairing failed |
| `gateway.status.read` | Status queried |
| `gateway.status.stale` | Stale snapshot returned |
| `gateway.control.accepted` | Control command accepted |
| `gateway.control.rejected` | Control command rejected |
| `gateway.audit.local_hashing_detected` | Hashing found on client |

### Metrics

| Metric | Description |
|--------|-------------|
| `pairing_attempts_total` | Pairing attempts by outcome |
| `status_reads_total` | Status reads by freshness |
| `control_commands_total` | Control commands by outcome |
| `inbox_append_total` | Event spine appends by kind |

Milestone 1 logs to stdout. See `references/observability.md` for full contract.

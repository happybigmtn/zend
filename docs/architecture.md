# Architecture

This document describes the Zend system architecture, module responsibilities, data flow, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Zend Home                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Home Miner Daemon                              │    │
│  │                                                                      │    │
│  │  ┌─────────────────┐     ┌─────────────────┐     ┌────────────────┐ │    │
│  │  │ GatewayHandler  │────▶│ MinerSimulator  │────▶│    Health      │ │    │
│  │  │ (HTTP Server)   │     │ (State Machine) │     │   Monitor      │ │    │
│  │  └────────┬────────┘     └─────────────────┘     └────────────────┘ │    │
│  │           │                                                         │    │
│  │  ┌────────▼────────┐                                               │    │
│  │  │    CLI Tool     │◀────── Authorization Check ──────────────────│ │    │
│  │  │   (cli.py)     │         (capability scopes)                     │    │
│  │  └────────┬────────┘                                                 │    │
│  │           │                                                           │    │
│  │  ┌────────▼────────────────────────────────────────────────────┐     │    │
│  │  │                    Event Spine                              │     │    │
│  │  │              (Append-only JSONL journal)                     │     │    │
│  │  └────────────────────────────────────────────────────────────┘     │    │
│  │                                                                       │    │
│  │  ┌────────────────────────────────────────────────────────────┐     │    │
│  │  │                    Store (Pairing + Principal)              │     │    │
│  │  │              (principal.json, pairing-store.json)           │     │    │
│  │  └────────────────────────────────────────────────────────────┘     │    │
│  │                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Command Center (Browser)                          │    │
│  │                                                                       │    │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │    │
│  │   │    Home    │    │   Inbox     │    │   Device    │              │    │
│  │   │  (Status)  │    │  (Events)   │    │ (Trust/Pair)│              │    │
│  │   └─────────────┘    └─────────────┘    └─────────────┘              │    │
│  │                                                                       │    │
│  │                          JavaScript                                  │    │
│  │                     (fetch to daemon API)                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### daemon.py — HTTP Server and Miner Simulator

**File:** `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP server that exposes the gateway API and simulates miner behavior for milestone 1.

**Key Components:**

| Component | Type | Description |
|-----------|------|-------------|
| `MinerSimulator` | Class | Simulates miner state machine |
| `MinerMode` | Enum | `PAUSED`, `BALANCED`, `PERFORMANCE` |
| `MinerStatus` | Enum | `RUNNING`, `STOPPED`, `OFFLINE`, `ERROR` |
| `GatewayHandler` | Class | HTTP request handler |
| `ThreadedHTTPServer` | Class | Threaded HTTP server |

**State Managed:**

```python
class MinerSimulator:
    _status: MinerStatus          # Current miner state
    _mode: MinerMode              # Operating mode
    _hashrate_hs: int             # Hash rate in H/s
    _temperature: float            # Simulated temperature
    _uptime_seconds: int           # Seconds since start
    _started_at: Optional[float]   # Start timestamp
    _lock: threading.Lock          # Thread safety
```

**Key Functions:**

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `start()` | None | `dict` | Start mining |
| `stop()` | None | `dict` | Stop mining |
| `set_mode()` | `mode: str` | `dict` | Change operating mode |
| `get_snapshot()` | None | `dict` | Get full status snapshot |
| `health()` | None | `dict` | Get health metrics |

**API Endpoints:** All endpoints in `GatewayHandler.do_GET()` and `do_POST()`

**Thread Safety:** All state mutations use `threading.Lock`

---

### cli.py — Command-Line Interface

**File:** `services/home-miner-daemon/cli.py`

**Purpose:** Human-facing CLI tool for status checks, control, and pairing.

**Commands:**

| Command | Description |
|---------|-------------|
| `status` | Get miner status |
| `health` | Get daemon health |
| `bootstrap` | Create principal and default pairing |
| `pair` | Pair a new device |
| `control` | Start/stop/set_mode |
| `events` | List events from spine |

**Authorization Flow:**

```
Command → Check capability → Daemon call → Append event → Output
```

The CLI enforces capability checking before allowing control actions.

**Key Functions:**

| Function | Description |
|----------|-------------|
| `daemon_call()` | Make HTTP request to daemon |
| `cmd_status()` | Handle `status` command |
| `cmd_control()` | Handle control commands with capability check |
| `cmd_events()` | Query event spine |

---

### spine.py — Event Spine

**File:** `services/home-miner-daemon/spine.py`

**Purpose:** Append-only encrypted event journal. The event spine is the source of truth; all other views are projections.

**Event Types:**

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

**Event Structure:**

```python
@dataclass
class SpineEvent:
    id: str              # UUID
    principal_id: str    # Owner's principal
    kind: str            # EventKind value
    payload: dict        # Event-specific data
    created_at: str      # ISO 8601 timestamp
    version: int         # Schema version (1)
```

**Storage:** `state/event-spine.jsonl` (newline-delimited JSON)

**Key Functions:**

| Function | Description |
|----------|-------------|
| `append_event()` | Add event to spine |
| `get_events()` | Query events with filtering |
| `append_pairing_granted()` | Record pairing approval |
| `append_control_receipt()` | Record control action |
| `append_miner_alert()` | Record miner alert |

---

### store.py — Pairing and Principal Store

**File:** `services/home-miner-daemon/store.py`

**Purpose:** Manages principal identity and device pairings.

**Principal:**

```python
@dataclass
class Principal:
    id: str          # UUID
    created_at: str  # ISO 8601 timestamp
    name: str        # Display name ("Zend Home")
```

**GatewayPairing:**

```python
@dataclass
class GatewayPairing:
    id: str               # UUID
    principal_id: str     # Owner's principal
    device_name: str      # Human-readable name
    capabilities: list    # ["observe", "control"]
    paired_at: str        # ISO 8601 timestamp
    token_expires_at: str # Token expiration
    token_used: bool      # Whether token was consumed
```

**Storage:**
- `state/principal.json` — Principal identity
- `state/pairing-store.json` — All pairings as dict

**Key Functions:**

| Function | Description |
|----------|-------------|
| `load_or_create_principal()` | Get or create principal |
| `pair_client()` | Create new pairing |
| `get_pairing_by_device()` | Look up pairing by name |
| `has_capability()` | Check device capability |
| `list_devices()` | List all paired devices |

---

## Data Flow

### Control Command Flow

```
User → CLI → has_capability() → daemon_call() → GatewayHandler → MinerSimulator
                                              ↓
                                         spine.append_control_receipt()
                                              ↓
                                         store.save_pairings()
                                              ↓
                                         Response JSON
```

1. User invokes CLI command with `--client` and `--action`
2. CLI checks device capability via `has_capability()`
3. If unauthorized, return error
4. If authorized, make HTTP request to daemon
5. Daemon handler routes to appropriate method
6. MinerSimulator updates state
7. CLI appends event to spine
8. CLI prints JSON response

### Status Query Flow

```
Browser → fetch() → GatewayHandler.do_GET() → MinerSimulator.get_snapshot()
                                   ↓
                              Response JSON
                                   ↓
                         Browser updates UI
```

1. Browser polls daemon every 5 seconds
2. `fetch()` calls `GET /status`
3. Handler calls `MinerSimulator.get_snapshot()`
4. Snapshot returned as JSON
5. Browser updates DOM with new values

### Bootstrap Flow

```
./scripts/bootstrap_home_miner.sh
       ↓
   store.load_or_create_principal()
       ↓
   store.pair_client("alice-phone", ["observe"])
       ↓
   spine.append_pairing_granted()
       ↓
   Daemon starts, ready to serve
```

---

## Auth Model

### Capability Scopes

| Capability | Grants Access To |
|------------|------------------|
| `observe` | `GET /status`, `GET /health`, `GET /spine/events` |
| `control` | `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode` |

`control` implies `observe`. A device with `control` can perform all `observe` actions.

### Authorization Flow

```
Client Request
      ↓
CLI checks: has_capability(device, required_capability)
      ↓
┌─────┴─────┐
│ Authorized │ Not Authorized
│     ↓     │     ↓
│ Daemon    │ Error: "unauthorized"
│ Request   │
└───────────┘
```

### Pairing Process

1. Operator runs `./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control`
2. CLI creates new `GatewayPairing` record
3. Device is added to `pairing-store.json`
4. `pairing_granted` event appended to spine

---

## Event Spine Design

### Why JSONL?

- **Simplicity**: No database required
- **Durability**: Append-only, easy to back up
- **Debugging**: Human-readable, one event per line
- **Performance**: Fast appends, no locking needed

### Event Immutability

Events are never modified or deleted. To revoke a pairing, append a `capability_revoked` event rather than modifying the pairing record.

### Query Patterns

```python
# All events
events = spine.get_events()

# Filter by kind
events = spine.get_events(kind=EventKind.CONTROL_RECEIPT)

# Limit results
events = spine.get_events(limit=10)

# Combined
events = spine.get_events(kind=EventKind.PAIRING_GRANTED, limit=5)
```

---

## Design Decisions

### Why Stdlib Only?

**Decision:** Use Python's standard library, no external dependencies.

**Rationale:**
- Zero install footprint on target hardware
- No dependency conflicts
- Easier security auditing
- Faster cold starts
- Simpler deployment (copy files, run)

**Trade-off:** More boilerplate for HTTP handling, JSON parsing, etc.

### Why LAN-Only Phase One?

**Decision:** Daemon binds to private network interface by default.

**Rationale:**
- Security: No internet-facing control surfaces
- Simplicity: No TLS, authentication, or network hardening required
- Trust: User controls their own network boundary

**Trade-off:** No remote access out of the box. Remote access requires VPN or secure tunneling.

### Why Single HTML File?

**Decision:** Command center is a single `index.html` with embedded CSS and JavaScript.

**Rationale:**
- No build step required
- Easy to deploy: copy one file
- No framework dependencies
- Works from `file://` or `http://`
- Trivial to audit (all code visible)

**Trade-off:** No code splitting, no advanced JS features, no offline-first PWA.

### Why JSONL Not SQLite?

**Decision:** Use JSONL files for persistence instead of SQLite.

**Rationale:**
- Simpler: No SQLite dependency
- Debug-friendly: Open files in any text editor
- Backup-friendly: `cp` works, no `sqlite3` CLI needed
- Sufficient: Event volume is low, append-heavy workload

**Trade-off:** No query language, no transactions, no concurrent access without file locking.

### Why Miner Simulator?

**Decision:** Phase one uses a software simulator instead of real mining hardware.

**Rationale:**
- Accessibility: Anyone can run without specialized hardware
- Speed: Faster development and testing
- Safety: No risk of damaging real hardware
- Stability: Consistent behavior for CI/CD

**Trade-off:** Not representative of real mining performance or hardware integration.

### Why ThreadedHTTPServer?

**Decision:** Use `socketserver.ThreadingMixIn` for concurrent request handling.

**Rationale:**
- Stdlib: No additional dependencies
- Sufficient: Low request volume expected
- Simple: Works with existing `BaseHTTPRequestHandler`

**Trade-off:** Not as performant as async frameworks (asyncio, Twisted) but adequate for phase one.

---

## State Files

### state/principal.json

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-22T12:00:00+00:00",
  "name": "Zend Home"
}
```

### state/pairing-store.json

```json
{
  "<pairing-uuid>": {
    "id": "<pairing-uuid>",
    "principal_id": "<principal-uuid>",
    "device_name": "alice-phone",
    "capabilities": ["observe", "control"],
    "paired_at": "2026-03-22T12:00:00+00:00",
    "token_expires_at": "2026-03-23T12:00:00+00:00",
    "token_used": false
  }
}
```

### state/event-spine.jsonl

```
{"id": "...", "principal_id": "...", "kind": "pairing_granted", "payload": {...}, "created_at": "...", "version": 1}
{"id": "...", "principal_id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "...", "version": 1}
...
```

---

## Extending the System

### Adding a New Endpoint

1. Add route to `do_GET()` or `do_POST()` in `GatewayHandler` in `daemon.py`
2. Call appropriate service function
3. Return JSON response via `self._send_json()`
4. Document in `docs/api-reference.md`

Example:
```python
def do_GET(self):
    if self.path == '/new/endpoint':
        result = my_service.function()
        self._send_json(200, result)
    else:
        self._send_json(404, {"error": "not_found"})
```

Note: The daemon currently only implements 5 endpoints:
- `GET /health`, `GET /status`
- `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`

Additional functionality (events, pairing) is available via the CLI tool, which calls `spine.py` and `store.py` directly.

### Adding a New Event Type

1. Add to `EventKind` enum in `spine.py`
2. Create `append_<event_name>()` function
3. Call from appropriate CLI commands
4. Document event structure

### Adding a New Capability

1. Add to CLI capability check in `cli.py`
2. Add to pairing UI in `index.html`
3. Document in `docs/operator-quickstart.md`

---

## Performance Characteristics

| Operation | Expected Latency |
|-----------|-----------------|
| Health check | < 1ms |
| Status query | < 2ms |
| Miner control | < 5ms |
| Event append | < 10ms |
| Event query (1000 events) | < 50ms |

Memory footprint: ~10 MB idle, ~50 MB under load

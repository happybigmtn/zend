# Architecture

This document describes the Zend system architecture, module design, and data flows.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Thin Mobile Client                              │
│                         (apps/zend-home-gateway/)                           │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │    Home     │  │   Inbox     │  │   Agent     │  │   Device    │      │
│  │  - Status   │  │ - Receipts  │  │ - Hermes    │  │ - Trust     │      │
│  │  - Mode     │  │ - Alerts    │  │ - Actions   │  │ - Pairing   │      │
│  │  - Actions  │  │ - Messages  │  │ - Authority │  │ - Recovery  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      │ HTTP JSON
                                      │ observe + control + inbox
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Zend Home Miner Daemon                                 │
│                   (services/home-miner-daemon/)                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          Gateway Handler                             │   │
│  │                      HTTP Request Processing                         │   │
│  │                                                                     │   │
│  │  GET /health ───────────────────────────────────────────────────┐  │   │
│  │  GET /status ──┐                                               │  │   │
│  │  GET /spine/events ────► Spine Query                           │  │   │
│  │  GET /metrics ──┤                                               │  │   │
│  │  POST /miner/start ──► Miner Simulator ──► Status Snapshots     │  │   │
│  │  POST /miner/stop ───┤                                           │  │   │
│  │  POST /miner/set_mode ┘                                           │  │   │
│  │  POST /pairing/refresh                                          │  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐   │
│  │   Spine         │  │   Store         │  │    Hermes Adapter       │   │
│  │                 │  │                 │  │                         │   │
│  │ Append-only     │  │ PrincipalId     │  │ (Future)                │   │
│  │ event journal   │  │ Pairing records │  │ Delegated authority     │   │
│  │                 │  │                 │  │ Observe + summary       │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        State Files                                  │   │
│  │  state/principal.json ── PrincipalId and creation timestamp         │   │
│  │  state/pairing-store.json ─ All paired devices and capabilities     │   │
│  │  state/event-spine.jsonl ─ Append-only event journal                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      │ Future: Real miner backend
                                      ▼
                            ┌─────────────────┐
                            │  Zcash Network  │
                            └─────────────────┘
```

## Module Guide

### daemon.py

The main daemon process.

**Classes:**

- `MinerSimulator`: Simulates miner behavior
  - `status`: Current status (running, stopped, offline, error)
  - `mode`: Operating mode (paused, balanced, performance)
  - `health`: Health check dict
  - `start()`: Start mining
  - `stop()`: Stop mining
  - `set_mode(mode)`: Change mode
  - `get_snapshot()`: Get status snapshot for clients

- `GatewayHandler`: HTTP request handler
  - `do_GET()`: Handle GET requests
  - `do_POST()`: Handle POST requests
  - `_send_json()`: Helper to send JSON responses

- `ThreadedHTTPServer`: Threaded HTTP server
  - Uses `socketserver.ThreadingMixIn` for concurrent requests
  - `allow_reuse_address = True` for quick restarts

**State:** Module-level `miner` singleton

**Entry Point:** `run_server(host, port)`

### cli.py

Command-line interface for operators.

**Commands:**

- `status`: Get miner status
- `health`: Get daemon health
- `bootstrap`: Create principal and default pairing
- `pair`: Pair a new client device
- `control`: Send control commands
- `events`: List events from spine

**Key Functions:**

- `daemon_call(method, path, data)`: Make HTTP call to daemon
- `cmd_*`: Command handlers

**State:** Reads from daemon via HTTP, writes to event spine

### spine.py

Append-only event journal.

**Classes:**

- `SpineEvent`: Event record
  - `id`: UUID
  - `principal_id`: Owner's identity
  - `kind`: Event type
  - `payload`: Encrypted event data
  - `created_at`: ISO timestamp
  - `version`: Schema version

- `EventKind`: Enum of event types
  - `PAIRING_REQUESTED`
  - `PAIRING_GRANTED`
  - `CAPABILITY_REVOKED`
  - `MINER_ALERT`
  - `CONTROL_RECEIPT`
  - `HERMES_SUMMARY`
  - `USER_MESSAGE`

**Key Functions:**

- `append_event(kind, principal_id, payload)`: Append new event
- `get_events(kind, limit)`: Query events
- `append_pairing_requested()`: Append pairing event
- `append_pairing_granted()`: Append pairing event
- `append_control_receipt()`: Append control receipt
- `append_miner_alert()`: Append alert
- `append_hermes_summary()`: Append Hermes summary

**State:** Appends to `state/event-spine.jsonl`

### store.py

Principal and pairing store.

**Classes:**

- `Principal`: User/agent identity
  - `id`: UUID
  - `created_at`: ISO timestamp
  - `name`: Display name

- `GatewayPairing`: Paired device record
  - `id`: UUID
  - `principal_id`: Owner's identity
  - `device_name`: Human-readable name
  - `capabilities`: List of granted capabilities
  - `paired_at`: ISO timestamp
  - `token_expires_at`: ISO timestamp

**Key Functions:**

- `load_or_create_principal()`: Get or create PrincipalId
- `pair_client(device_name, capabilities)`: Create pairing
- `get_pairing_by_device(device_name)`: Lookup pairing
- `has_capability(device_name, capability)`: Check permission
- `list_devices()`: List all paired devices

**State:** Reads/writes `state/principal.json` and `state/pairing-store.json`

## Data Flow

### Control Command Flow

```
Client Request
      │
      ▼
┌─────────────────┐
│  CLI Command    │  (cli.py: cmd_control)
│  --action start │
└────────┬────────┘
         │
         │ Check capability
         ▼
┌─────────────────┐
│ has_capability │  store.py
│ (control?)     │
└────────┬────────┘
         │
         │ Denied ──► Return error
         │ Allowed
         ▼
┌─────────────────┐
│ daemon_call     │  cli.py
│ POST /miner/*   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GatewayHandler  │  daemon.py
│ do_POST()      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MinerSimulator │  daemon.py
│ start/stop/    │
│ set_mode()     │
└────────┬────────┘
         │
         │ Result
         ▼
┌─────────────────┐
│ _send_json()   │  daemon.py
│ HTTP 200/400   │
└────────┬────────┘
         │
         │ JSON response
         ▼
┌─────────────────┐
│ CLI Output     │  cli.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ spine.append   │  spine.py
│ _control_receipt│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ event-spine.jsonl│
│ Append-only     │
└─────────────────┘
```

### Status Read Flow

```
Client Request
      │
      ▼
┌─────────────────┐
│ CLI Command     │  (cli.py: cmd_status)
│ status --client │
└────────┬────────┘
         │
         │ Check capability
         ▼
┌─────────────────┐
│ has_capability │  store.py
│ (observe?)     │
└────────┬────────┘
         │
         │ Denied ──► Return error
         │ Allowed
         ▼
┌─────────────────┐
│ daemon_call     │  cli.py
│ GET /status    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GatewayHandler  │  daemon.py
│ do_GET()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MinerSimulator │  daemon.py
│ get_snapshot() │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ JSON Response   │  daemon.py
│ with freshness │
└─────────────────┘
```

## Auth Model

### PrincipalId

A `PrincipalId` is the stable identity assigned to a user or agent:

```python
@dataclass
class Principal:
    id: str          # UUID v4
    created_at: str  # ISO 8601
    name: str        # "Zend Home"
```

The same `PrincipalId` is used by:
- Gateway pairing records
- Event-spine items
- Future inbox metadata

### Capabilities

Two capability scopes:

- `observe`: Read miner status and events
- `control`: Change mining mode, start/stop mining

Pairing creates a record with granted capabilities:

```python
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list
    paired_at: str
    token_expires_at: str
```

### Authorization Flow

```
Request arrives
      │
      ▼
┌─────────────────┐
│ Check pairing   │  store.py
│ exists?        │
└────────┬────────┘
         │
         │ Not found ──► Return error
         │ Found
         ▼
┌─────────────────┐
│ has_capability  │  store.py
│ (device, cap)  │
└────────┬────────┘
         │
         │ Denied ──► Return error
         │ Allowed
         ▼
    Execute action
```

## Event Spine

The event spine is an append-only journal that serves as the source of truth.

### Event Flow

```
Operation
   │
   ▼
┌─────────────────┐
│ append_event() │  spine.py
│ Create event   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ event-spine.jsonl│
│ Append line     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ get_events()   │  spine.py
│ Query journal   │
└─────────────────┘
```

### Query Patterns

```python
# All events, recent first
events = get_events(limit=100)

# Filter by kind
events = get_events(kind=EventKind.CONTROL_RECEIPT, limit=10)

# All pairing events
events = get_events(kind=EventKind.PAIRING_REQUESTED, limit=50)
```

## Design Decisions

### Why Stdlib Only?

No external dependencies means:
- No dependency conflicts
- No version management
- Works in restricted environments
- Easier to audit

### Why LAN-Only?

Phase 1 is LAN-only to minimize blast radius. The control surface is powerful; exposing it to the internet requires additional security measures.

### Why JSONL for Event Spine?

- Append-only by design
- Easy to tail with standard tools
- Human-readable
- No database dependency
- Works with standard file tools

### Why Single HTML File?

The command center is a single HTML file that:
- Works offline after first load
- No build step required
- Easy to deploy anywhere
- Can be served from the daemon itself

### Why Capability Scoping?

Separating `observe` from `control` allows:
- Read-only access for monitoring devices
- Full control for trusted devices
- Future granular permissions

## State Files

```
state/
  principal.json        # PrincipalId
  pairing-store.json    # Paired devices
  event-spine.jsonl    # Event journal
  daemon.pid           # Daemon process ID (runtime)
```

All state files are in `state/` which is gitignored.

## Future Extensions

### Real Miner Backend

Replace `MinerSimulator` with a real miner control client:

```python
class MinerClient:
    def start(self): ...
    def stop(self): ...
    def set_mode(self, mode): ...
    def get_status(self): ...
```

### Hermes Adapter

Connect Hermes Gateway through a Zend adapter:

```
Hermes Gateway ──► Zend Adapter ──► Gateway Handler
                  (authority        (observe + control)
                   mapping)
```

### Remote Access

Secure remote access would require:
- TLS termination
- Token-based authentication
- Optional: Tailscale or similar VPN

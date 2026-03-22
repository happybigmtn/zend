# Architecture

This document describes the Zend system architecture, module structure, data
flow, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Zend System                                   │
│                                                                          │
│  ┌─────────────────┐                    ┌─────────────────────────┐   │
│  │  Mobile Client   │                    │   Home Miner Hardware    │   │
│  │  (HTML/SPA)     │◄──────HTTP───────►│   (Raspberry Pi, etc.)   │   │
│  └─────────────────┘                    │                          │   │
│         │                                │  ┌──────────────────┐   │   │
│         │                                │  │ Zend Daemon      │   │   │
│         │                                │  │ (Python stdlib)  │   │   │
│         │                                │  └────────┬─────────┘   │   │
│         │                                │           │             │   │
│         │                                │           ▼             │   │
│         │                                │  ┌──────────────────┐   │   │
│         │                                │  │ Miner Simulator  │   │   │
│         │                                │  │ (or real miner) │   │   │
│         │                                │  └──────────────────┘   │   │
│         │                                └─────────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────┐                                                │
│  │   Event Spine   │◄── Append-only journal                         │
│  │   (JSONL file) │     - pairing_requested                         │
│  └─────────────────┘     - pairing_granted                          │
│                          - control_receipt                           │
│                          - hermes_summary                            │
│                          - miner_alert                              │
│                          - user_message                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### `services/home-miner-daemon/daemon.py`

The HTTP API server and miner simulator.

**Purpose**: Expose the control plane API and simulate miner behavior.

**Key Classes**:

- `MinerSimulator`: Simulates miner state (status, mode, hashrate, temperature)
- `GatewayHandler`: HTTP request handler for the API endpoints
- `ThreadedHTTPServer`: Threaded HTTP server for concurrent requests

**Key Functions**:

- `run_server(host, port)`: Start the daemon

**State Managed**:
- Miner status (running/stopped/error/offline)
- Mining mode (paused/balanced/performance)
- Hash rate and temperature (simulated)

**API Endpoints**:
- `GET /health`: Health check
- `GET /status`: Miner status snapshot
- `POST /miner/start`: Start mining
- `POST /miner/stop`: Stop mining
- `POST /miner/set_mode`: Change mode

---

### `services/home-miner-daemon/spine.py`

The append-only event journal.

**Purpose**: Maintain an immutable audit trail of all operations.

**Key Functions**:

- `append_event(kind, principal_id, payload)`: Append an event to the spine
- `get_events(kind=None, limit=100)`: Retrieve events, optionally filtered
- `append_pairing_requested(device_name, capabilities, principal_id)`
- `append_pairing_granted(device_name, capabilities, principal_id)`
- `append_control_receipt(command, mode, status, principal_id)`
- `append_miner_alert(alert_type, message, principal_id)`
- `append_hermes_summary(summary_text, authority_scope, principal_id)`

**State Managed**:
- `state/event-spine.jsonl`: Append-only JSONL file

**Design**: Events are never modified or deleted. Each event has:
- `id`: UUID v4
- `principal_id`: References the principal contract
- `kind`: Event type
- `payload`: Encrypted event data
- `created_at`: ISO 8601 timestamp
- `version`: Schema version (always 1)

---

### `services/home-miner-daemon/store.py`

Principal and pairing storage.

**Purpose**: Manage identity and device pairing records.

**Key Functions**:

- `load_or_create_principal()`: Get or create the PrincipalId
- `pair_client(device_name, capabilities)`: Create a pairing record
- `get_pairing_by_device(device_name)`: Look up pairing by device name
- `has_capability(device_name, capability)`: Check if device has a capability
- `list_devices()`: List all paired devices

**State Managed**:
- `state/principal.json`: The PrincipalId record
- `state/pairing-store.json`: All pairing records

**Principal Schema**:
```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str   # ISO 8601
    name: str         # "Zend Home"
```

**Pairing Schema**:
```python
@dataclass
class GatewayPairing:
    id: str           # UUID v4
    principal_id: str
    device_name: str
    capabilities: list  # ["observe", "control"]
    paired_at: str      # ISO 8601
    token_expires_at: str
    token_used: bool
```

---

### `services/home-miner-daemon/cli.py`

Command-line interface for operator tasks.

**Purpose**: Provide scriptable access to the daemon API and local state.

**Commands**:

- `health`: Check daemon health
- `status`: Get miner status
- `bootstrap`: Create principal and initial pairing
- `pair`: Pair a new device
- `control`: Issue control commands
- `events`: List events from the spine

**Key Function**:

- `daemon_call(method, path, data=None)`: Make HTTP request to daemon

---

### `apps/zend-home-gateway/index.html`

The mobile-shaped command center UI.

**Purpose**: Provide a human-usable interface to the daemon.

**Features**:

- Status Hero: Current miner state, mode, hash rate, freshness
- Mode Switcher: Change mining mode (paused/balanced/performance)
- Quick Actions: Start/Stop buttons
- Receipt Card: Latest control receipt
- Bottom Navigation: Home, Inbox, Agent, Device tabs

**Design System**: Follows `DESIGN.md`
- Fonts: Space Grotesk, IBM Plex Sans, IBM Plex Mono
- Colors: Basalt, Slate, Moss (healthy), Amber (caution), Signal Red (error)
- Mobile-first, minimum 44x44 touch targets

---

## Data Flow

### Control Command Flow

```
┌──────────┐    HTTP POST     ┌──────────┐    Validate     ┌──────────┐
│  Client  │ ───────────────► │  Daemon  │ ──────────────► │  Miner   │
│          │                  │          │                  │          │
│ cli.py   │                  │daemon.py │                  │Simulator │
│ or HTML  │                  │          │                  │          │
└──────────┘                  └────┬─────┘                  └──────────┘
                                   │
                                   │ Record
                                   ▼
                            ┌──────────────┐
                            │ Event Spine  │
                            │              │
                            │control_receipt│
                            └──────────────┘
                                   │
                                   │ Derive
                                   ▼
                            ┌──────────────┐
                            │    Inbox     │
                            │   (View)     │
                            └──────────────┘
```

1. Client sends HTTP POST to `/miner/set_mode`
2. Daemon validates the request (capability check)
3. Daemon calls `miner.set_mode()` on the simulator
4. Daemon appends `control_receipt` to the event spine
5. Inbox view queries the event spine for display

### Pairing Flow

```
┌──────────┐    CLI call      ┌──────────┐    Store        ┌──────────┐
│ Operator │ ───────────────► │   CLI    │ ──────────────► │  Store   │
│          │                  │          │                  │          │
│bootstrap │                  │cli.py    │                  │store.py  │
│.sh       │                  │          │                  │          │
└──────────┘                  └────┬─────┘                  └──────────┘
                                   │
                                   │ Append
                                   ▼
                            ┌──────────────┐
                            │ Event Spine  │
                            │              │
                            │pairing_granted│
                            └──────────────┘
```

1. Operator runs `./scripts/bootstrap_home_miner.sh`
2. CLI calls `store.load_or_create_principal()`
3. CLI calls `store.pair_client()` with default capabilities
4. CLI calls `spine.append_pairing_granted()`
5. Pairing record is persisted; event is appended

---

## Auth Model

### PrincipalId

A `PrincipalId` is the stable identity for a Zend installation. It is:
- Created once during bootstrap
- Stored in `state/principal.json`
- Referenced by all pairing records and event spine entries

### Gateway Capabilities

| Capability | Description |
|------------|-------------|
| `observe` | Can read miner status, view events |
| `control` | Can start/stop mining, change mode |

Capability checks are enforced by the CLI before making daemon calls.

### Pairing Token

Each pairing has:
- A creation timestamp
- An expiration timestamp (default: 24 hours)
- A `token_used` flag (for replay prevention)

---

## Event Spine Design

### Why Append-Only?

The event spine is append-only to ensure:
- Complete audit trail
- No data loss
- Simple consistency model
- Easy replication

### Why JSONL?

- Human-readable
- Easy to append (no locking needed for writes)
- Can be processed line-by-line
- No schema migration needed (version field)

### Event Kinds and Routing

| Kind | Source | Inbox Display |
|------|--------|---------------|
| `pairing_requested` | CLI | Device > Pairing |
| `pairing_granted` | CLI | Device > Pairing |
| `capability_revoked` | CLI | Device > Permissions |
| `miner_alert` | Daemon | Home + Inbox |
| `control_receipt` | Daemon | Inbox |
| `hermes_summary` | Hermes | Inbox + Agent |
| `user_message` | Client | Inbox |

---

## Design Decisions

### Why Stdlib Only?

- Zero dependency installation
- Works on any Python 3.10+ installation
- Reduces attack surface
- Simplifies deployment

### Why LAN-Only by Default?

- Reduces blast radius for milestone 1
- No TLS/certificates needed
- Works behind NAT
- Internet exposure deferred to future

### Why JSONL Not SQLite?

- Simpler deployment (no database server)
- Human-readable for debugging
- Append-only matches our use case
- No ORM complexity

### Why Single HTML File?

- No build step
- Easy to serve or open directly
- Self-contained
- Easy to customize

### Why Separate CLI from Daemon?

- Operators can script with shell
- Daemon can be restarted independently
- Clear separation of concerns
- Easy to add new commands

### Why Event Spine as Source of Truth?

- Single source of truth prevents drift
- Inbox is just a view (filter/render)
- Future features can reprocess events
- Audit is built-in

---

## Future Considerations

### Remote Access

Future versions may add:
- TLS with self-signed certs
- Token-based authentication
- Optional cloud relay

### Real Miner Backend

The simulator exposes the same contract as a real miner. Future work may:
- Connect to `cpuminer` or similar
- Add GPU monitoring
- Expose pool configuration

### WebSocket Support

Real-time status updates could be added via WebSocket:
- Reduces polling
- Enables instant alerts
- Requires more infrastructure

---

## File Locations

| File | Purpose |
|------|---------|
| `state/principal.json` | PrincipalId |
| `state/pairing-store.json` | All pairings |
| `state/event-spine.jsonl` | Append-only event log |
| `state/daemon.pid` | Daemon PID for management |
| `apps/zend-home-gateway/index.html` | Command center UI |
| `services/home-miner-daemon/daemon.py` | API server |
| `services/home-miner-daemon/cli.py` | CLI tool |
| `services/home-miner-daemon/spine.py` | Event spine |
| `services/home-miner-daemon/store.py` | Storage |

# Architecture

This document explains the Zend system architecture — how components fit
together, how data flows, and why key design decisions were made.

## System Overview

```
  ┌────────────────────────────────────────────────────────────┐
  │  apps/zend-home-gateway/index.html                        │
  │  Mobile command center (single HTML file, no build step)  │
  │                                                            │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
  │  │  Home    │  │  Inbox   │  │  Agent   │  │  Device  │ │
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
  └──────────────────────────┬───────────────────────────────┘
                             │ HTTP JSON
                             ▼
  ┌────────────────────────────────────────────────────────────┐
  │  services/home-miner-daemon/daemon.py                      │
  │  LAN-only HTTP server (Python stdlib, no external deps)    │
  │                                                            │
  │  ThreadedHTTPServer on 127.0.0.1:8080                     │
  │  └── GatewayHandler (GET /health, GET /status)             │
  │  └── GatewayHandler (POST /miner/start, /stop, /set_mode)  │
  │  └── MinerSimulator (in-memory state machine)              │
  └────────────────┬─────────────────┬────────────────────────┘
                   │                 │
                   ▼                 ▼
  ┌────────────────────────┐  ┌─────────────────────────────────┐
  │  services/             │  │  services/                      │
  │  home-miner-daemon/    │  │  home-miner-daemon/             │
  │  spine.py              │  │  store.py                       │
  │                        │  │                                 │
  │  Append-only JSONL     │  │  PrincipalId                    │
  │  event journal          │  │  └── GatewayPairing records     │
  │                        │  │                                 │
  │  state/event-spine.jsonl│ │  state/principal.json           │
  │                        │  │  state/pairing-store.json       │
  └────────────────────────┘  └─────────────────────────────────┘

  Shell scripts wrap the CLI:
  ├── scripts/bootstrap_home_miner.sh
  ├── scripts/pair_gateway_client.sh
  ├── scripts/read_miner_status.sh
  └── scripts/set_mining_mode.sh
```

## Module Guide

### `daemon.py` — HTTP API Server

**Purpose**: Expose the gateway contract over HTTP. Handle concurrent requests
with a threaded server. Run a miner simulator that exposes the same contract a
real miner backend would use.

**Key classes**:

- `MinerSimulator` — In-memory miner state machine. Manages `status` (running/
  stopped/offline/error), `mode` (paused/balanced/performance), and derived
  values (hashrate, temperature, uptime).
- `GatewayHandler` — HTTP request handler. Maps paths to miner operations.
- `ThreadedHTTPServer` — Threaded HTTP server using Python's socketserver.

**Key functions**:

- `run_server(host, port)` — Entry point. Binds and starts the server.
- `MinerSimulator.start()` — Transition from stopped to running.
- `MinerSimulator.stop()` — Transition from running to stopped.
- `MinerSimulator.set_mode(mode)` — Change operating mode.
- `MinerSimulator.get_snapshot()` — Return current miner state as a dict.

**State managed**: In-memory only. State is reset when the daemon restarts.
Miner state is not persisted — it is always fresh from the simulator.

**Thread safety**: A `threading.Lock` protects all state mutations in
`MinerSimulator`.

### `cli.py` — Command-Line Interface

**Purpose**: Provide a human- and script-friendly interface to the daemon.
Each CLI command checks capabilities before forwarding requests, and appends
events to the spine after operations.

**Key functions**:

- `daemon_call(method, path, data)` — Make an HTTP request to the daemon.
- `cmd_status(args)` — Fetch miner snapshot, check observe capability.
- `cmd_control(args)` — Issue control command, check control capability,
  append control receipt to spine.
- `cmd_bootstrap(args)` — Create principal and pair first device.
- `cmd_pair(args)` — Pair a new device with specified capabilities.
- `cmd_events(args)` — Query the event spine.

**State managed**: None (stateless CLI). All state is in the daemon and the
JSON files.

### `spine.py` — Event Spine

**Purpose**: Append-only encrypted event journal. The single source of truth
for all operational events.

**Key classes**:

- `SpineEvent` — Dataclass with `id`, `principal_id`, `kind`, `payload`,
  `created_at`, `version`.
- `EventKind` — Enum of valid event kinds.

**Key functions**:

- `append_event(kind, principal_id, payload)` — Append a new event.
- `get_events(kind, limit)` — Query events, most recent first.
- `append_pairing_requested(...)` — Append pairing request event.
- `append_pairing_granted(...)` — Append pairing approval event.
- `append_control_receipt(...)` — Append control command receipt.
- `append_miner_alert(...)` — Append miner alert.
- `append_hermes_summary(...)` — Append Hermes summary.

**State managed**: `state/event-spine.jsonl` (one JSON object per line).
The file grows append-only. Events cannot be modified or deleted.

**Design note**: The spine is the source of truth. The inbox is a derived
view. Never write events only to a separate "inbox" store.

### `store.py` — Principal and Pairing Store

**Purpose**: Manage the stable `PrincipalId` and all paired device records
with their capabilities.

**Key classes**:

- `Principal` — Dataclass with `id` (UUID), `created_at`, `name`.
- `GatewayPairing` — Dataclass with `id`, `principal_id`, `device_name`,
  `capabilities`, `paired_at`, `token_expires_at`.

**Key functions**:

- `load_or_create_principal()` — Return existing principal or create new.
- `pair_client(device_name, capabilities)` — Create new pairing record.
- `get_pairing_by_device(device_name)` — Look up pairing by device name.
- `has_capability(device_name, capability)` — Check if device has capability.
- `list_devices()` — List all paired devices.

**State managed**:
- `state/principal.json` — One principal identity (stable across restarts).
- `state/pairing-store.json` — All pairing records.

**Design note**: The `principal_id` is shared across gateway pairing and future
inbox access. This ensures one stable identity for the whole system.

## Data Flow

### Control Command Flow

```
User/Agent
    │
    │ python3 cli.py control --client alice-phone --action set_mode --mode balanced
    │
    ▼
cli.py (cmd_control)
    │
    ├── has_capability("alice-phone", "control") → True?
    │       │
    │       └── No → print error, exit 1
    │
    ├── daemon_call("POST", "/miner/set_mode", {"mode": "balanced"})
    │       │
    │       ▼
    │   daemon.py (do_POST /miner/set_mode)
    │       │
    │       ├── miner.set_mode("balanced")
    │       │       │
    │       │       └── Updates in-memory state, returns {"success": true}
    │       │
    │       └── _send_json(200, result)
    │
    ├── spine.append_control_receipt("set_mode", "balanced", "accepted", principal.id)
    │       │
    │       └── Appends JSON line to state/event-spine.jsonl
    │
    └── print JSON response
```

### Status Read Flow

```
User opens index.html
    │
    │ fetch("/status")
    │
    ▼
daemon.py (do_GET /status)
    │
    ├── miner.get_snapshot()
    │       │
    │       └── Returns in-memory state + current uptime
    │
    └── _send_json(200, snapshot)
        │
        ▼
HTML updates status hero with:
    - Status indicator (green = running, gray = stopped, red = error)
    - Status value text
    - Hashrate display
    - Freshness timestamp
```

### Pairing Flow

```
bootstrap_home_miner.sh
    │
    ├── python3 cli.py bootstrap --device alice-phone
    │       │
    │       ├── store.load_or_create_principal() → creates state/principal.json
    │       ├── store.pair_client("alice-phone", ["observe"]) → creates pairing record
    │       ├── spine.append_pairing_granted("alice-phone", ["observe"], principal.id)
    │       └── print pairing bundle
    │
    └── Daemon running on 127.0.0.1:8080
```

## Auth Model

### Capability Scoping

Every paired device has one or both capabilities:

| Capability | Grants | Denied |
|------------|--------|--------|
| `observe` | Read status, list events | Control commands |
| `control` | All observe + start/stop/set_mode | Nothing additional in milestone 1 |

Capability checking is done in the CLI layer (`has_capability()`), not in the
HTTP daemon. The daemon trusts that the CLI has already checked.

### Pairing Records

```json
{
  "id": "uuid",
  "principal_id": "uuid",
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T...",
  "token_expires_at": "2026-04-21T...",
  "token_used": false
}
```

### Principal Identity

```
PrincipalId (stable, created once)
    │
    ├── Owns gateway pairing records
    ├── Owns all event spine entries
    └── Future: owns inbox metadata
```

## Event Spine

### Purpose

The event spine is an append-only journal. It provides:
- Complete audit trail of all operations
- Source of truth for the operations inbox
- Decoupling between daemon operations and UI presentation

### Event Kinds

| Kind | When appended |
|------|--------------|
| `pairing_requested` | Client requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Capability revoked |
| `miner_alert` | Miner alert generated |
| `control_receipt` | Control command processed |
| `hermes_summary` | Hermes summary appended |
| `user_message` | User message received |

### Routing to Inbox

| Event Kind | Inbox Destination |
|------------|------------------|
| `pairing_granted` | Device > Pairing |
| `control_receipt` | Inbox |
| `miner_alert` | Home + Inbox |
| `hermes_summary` | Inbox + Agent |
| `user_message` | Inbox |

### Why JSONL?

JSONL (one JSON object per line) is chosen for these properties:
- **Append-only friendly**: You can `echo '{"id":"..."}' >> spine.jsonl` to append
- **Streaming-friendly**: Read events one at a time without loading the whole file
- **No locking needed for appends**: Multiple processes can append safely
- **Simple recovery**: Corrupted line doesn't destroy the whole file
- **No schema migration needed**: Each line is self-contained

SQLite would add a dependency and complicate the "no external deps" constraint.
A SQL database is appropriate when you need queries, transactions, and
relationships. The event spine needs none of that.

## Design Decisions

### Why stdlib-only?

- **No dependency hell**: `pip install` breaks on Python version changes, network
  issues, or deprecated packages
- **Reproducible**: Standard library is always available with Python
- **Audit-friendly**: Zero supply chain risk
- **Simplicity**: A daemon that starts in one command is easier to operate

### Why LAN-only by default?

- **Security**: A home miner control surface exposed to the internet is a target
- **Simplicity**: No TLS, no authentication server, no certificate management
- **Trust**: The device is on your network, you control the hardware
- **Future-proof**: Remote access can be added later with explicit tunneling

### Why the HTML gateway is a single file?

- **No build step**: Open `index.html` and it works
- **Portable**: Runs on any device with a browser
- **Inspectable**: View source, modify, understand
- **No framework**: Pure HTML + CSS + vanilla JavaScript
- **Future-proof**: No framework to deprecate

### Why capability-scoped pairing?

- **Least privilege**: Observe-only clients can't change miner state
- **Upgradeable**: Start with observe, grant control later
- **Revocable**: Remove capability by editing the pairing store
- **Auditable**: Every control command is logged with the device identity

### Why shared PrincipalId?

- **Identity stability**: One identity for gateway + future inbox
- **Audit continuity**: All events trace to the same principal
- **Future-proof**: Inbox inherits identity without migration

### Why miner simulator instead of real miner?

- **Speed**: No mining hardware required
- **Deterministic**: Same inputs → same outputs
- **Isolated**: Doesn't affect real mining operations
- **Complete contract**: The simulator exposes exactly what a real miner would

The daemon's `MinerSimulator` class exposes the same interface a real miner
backend would use. When a real miner is integrated, only the simulator
replacement is needed.

## Future Architecture

### Remote Access

```
Phone (outside LAN)
    │
    │ HTTPS + auth token
    │
    ▼
Reverse proxy (nginx, Cloudflare Tunnel, etc.)
    │
    ▼
Zend daemon (still LAN-only)
```

Remote access requires a TLS-terminating proxy and a bearer token.
The daemon itself remains LAN-only.

### Hermes Integration

```
Hermes Gateway
    │
    │ Observe-only + summary append
    │
    ▼
Hermes Adapter
    │
    │ Delegates only granted capabilities
    │
    ▼
Zend Gateway Contract
```

Hermes connects through a Zend adapter. It receives only the capabilities Zend
explicitly grants. Direct miner control through Hermes is deferred to a later
capability model.

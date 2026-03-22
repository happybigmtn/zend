# Architecture

This document describes the Zend system architecture: components, data flow,
and design decisions.

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          Zend Home                                   │
│                    Mobile Command Center                              │
│               (apps/zend-home-gateway/index.html)                    │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   Home   │  │  Inbox   │  │  Agent   │  │  Device  │            │
│  │  Status  │  │ Receipts │  │  Hermes  │  │  Trust   │            │
│  │   Hero   │  │  + Msgs  │  │ Summary  │  │  + Perms │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │              │              │              │                │
│       └──────────────┴──────────────┴──────────────┘                │
│                           │                                          │
│                    Bottom Tab Bar                                    │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            │ HTTP (LAN)
                            │ observe + control
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Home Miner Daemon                               │
│                  (services/home-miner-daemon/)                       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        daemon.py                              │  │
│  │  ThreadedHTTPServer + GatewayHandler                           │  │
│  │                                                               │  │
│  │   Endpoints:                                                  │  │
│  │   • GET  /health     → daemon health                          │  │
│  │   • GET  /status     → miner snapshot                        │  │
│  │   • POST /miner/start → start mining                         │  │
│  │   • POST /miner/stop  → stop mining                          │  │
│  │   • POST /miner/set_mode → change mode                       │  │
│  │                                                               │  │
│  │   ┌─────────────────────────────────────────────────────┐    │  │
│  │   │              MinerSimulator                          │    │  │
│  │   │  status · mode · hashrate · temperature · uptime    │    │  │
│  │   └─────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │    cli.py    │  │   spine.py   │  │       store.py          │   │
│  │  Pairing +   │  │  Event       │  │  Principal + Pairing    │   │
│  │  Control +   │  │  Journal     │  │  Records               │   │
│  │  Events CLI  │  │  (JSONL)     │  │                        │   │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                 │                      │                 │
└─────────┼─────────────────┼──────────────────────┼─────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Local State                                  │
│                     (state/ — gitignored)                            │
│                                                                      │
│  ┌────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│  │ principal.json │ │pairing-store.json│ │   event-spine.jsonl    │ │
│  │                │ │                  │ │                         │ │
│  │ • id           │ │ • device_name   │ │ PairingRequested       │ │
│  │ • created_at   │ │ • capabilities  │ │ PairingGranted         │ │
│  │ • name         │ │ • paired_at     │ │ CapabilityRevoked       │ │
│  │                │ │ • token_expires │ │ MinerAlert             │ │
│  │                │ │                  │ │ ControlReceipt         │ │
│  │                │ │                  │ │ HermesSummary          │ │
│  │                │ │                  │ │ UserMessage            │ │
│  └────────────────┘ └─────────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### daemon.py

**Purpose**: HTTP server exposing the gateway API and miner simulator.

**Key Classes**:

- `MinerSimulator` — Simulates miner hardware. Exposes status, start, stop, set_mode.
- `GatewayHandler` — HTTP request handler. Maps URLs to miner operations.
- `ThreadedHTTPServer` — Threaded HTTP server for concurrent requests.

**Key Functions**:

- `default_state_dir()` — Resolves state directory relative to repo root.
- `run_server(host, port)` — Starts the daemon.

**State Managed**:
- `_status` — Current miner status (running/stopped/offline/error)
- `_mode` — Current mode (paused/balanced/performance)
- `_hashrate_hs` — Current hashrate in hashes per second
- `_temperature` — Current temperature
- `_uptime_seconds` — Seconds since miner started

**Example**:

```python
from daemon import miner

# Check miner status
snapshot = miner.get_snapshot()
print(snapshot)
# {'status': 'stopped', 'mode': 'paused', 'hashrate_hs': 0, ...}

# Start mining
result = miner.start()
print(result)
# {'success': True, 'status': 'running'}

# Change mode
result = miner.set_mode('balanced')
print(result)
# {'success': True, 'mode': 'balanced'}
```

### cli.py

**Purpose**: Command-line interface for pairing, status, control, and event queries.

**Key Functions**:

- `daemon_call(method, path, data)` — Make HTTP call to daemon.
- `cmd_status(args)` — Get miner status.
- `cmd_bootstrap(args)` — Bootstrap principal and first pairing.
- `cmd_pair(args)` — Pair a new device.
- `cmd_control(args)` — Control the miner.
- `cmd_events(args)` — List events from spine.

**State Managed**:
- Reads from `state/principal.json`, `state/pairing-store.json`
- Writes events to `state/event-spine.jsonl`

**Example**:

```bash
# Bootstrap
python3 cli.py bootstrap --device my-phone

# Check status
python3 cli.py status --client my-phone

# Control miner
python3 cli.py control --client my-phone --action set_mode --mode balanced

# View events
python3 cli.py events --limit 20
```

### spine.py

**Purpose**: Append-only JSONL event journal. Source of truth for all events.

**Key Functions**:

- `append_event(kind, principal_id, payload)` — Append a new event.
- `get_events(kind, limit)` — Retrieve events, optionally filtered.
- `append_pairing_requested(...)` — Append pairing requested event.
- `append_pairing_granted(...)` — Append pairing granted event.
- `append_control_receipt(...)` — Append control receipt event.

**State Managed**:
- `state/event-spine.jsonl` — Append-only log file

**Event Kinds**:

| Kind | Description |
|---|---|
| `pairing_requested` | New device requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Permission removed |
| `miner_alert` | Miner alert condition |
| `control_receipt` | Control action result |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message |

**Example**:

```python
from spine import append_control_receipt, get_events

# Append a control receipt
append_control_receipt(
    command='set_mode',
    mode='balanced',
    status='accepted',
    principal_id='...'
)

# Retrieve events
events = get_events(kind='control_receipt', limit=10)
for event in events:
    print(event.payload)
```

### store.py

**Purpose**: Principal identity and pairing record management.

**Key Functions**:

- `load_or_create_principal()` — Get or create principal identity.
- `pair_client(device_name, capabilities)` — Create new pairing record.
- `get_pairing_by_device(device_name)` — Get pairing by device name.
- `has_capability(device_name, capability)` — Check device capability.
- `list_devices()` — List all paired devices.

**State Managed**:
- `state/principal.json` — Principal identity
- `state/pairing-store.json` — Pairing records

**Example**:

```python
from store import load_or_create_principal, pair_client, has_capability

# Get or create principal
principal = load_or_create_principal()
print(principal.id)  # UUID

# Pair a new device
pairing = pair_client('my-phone', ['observe', 'control'])
print(pairing.capabilities)  # ['observe', 'control']

# Check capability
can_control = has_capability('my-phone', 'control')  # True
can_mine = has_capability('my-phone', 'mine')  # False
```

## Data Flow

### Control Command Flow

```text
  User Action (CLI or HTML)
          │
          ▼
    cli.py / HTML JS
          │
          │ Check capability (has_capability)
          │
          ▼
    HTTP POST /miner/set_mode
          │
          ▼
    daemon.py GatewayHandler
          │
          │ Validate mode parameter
          │
          ▼
    MinerSimulator.set_mode()
          │
          │ Update internal state
          │
          ▼
    Return success/failure
          │
          ▼
    cli.py / HTML JS
          │
          │ On success, append event
          │
          ▼
    spine.append_control_receipt()
          │
          ▼
    Append to event-spine.jsonl
          │
          ▼
    User sees acknowledgement
```

### Status Query Flow

```text
  User Action (CLI or HTML)
          │
          ▼
    cli.py / HTML JS
          │
          │ Check observe/control capability
          │
          ▼
    HTTP GET /status
          │
          ▼
    daemon.py GatewayHandler
          │
          ▼
    MinerSimulator.get_snapshot()
          │
          │ Collect status, mode, hashrate
          │ Add freshness timestamp
          │
          ▼
    Return snapshot JSON
          │
          ▼
    cli.py / HTML JS
          │
          ▼
    Display to user
```

## Auth Model

### Pairing Flow

```text
  Unpaired Device
        │
        │ pair_client(device_name, capabilities)
        │
        ▼
  Generate pairing record
        │
        ├── Validate no duplicate device_name
        ├── Create token with expiration
        └── Store in pairing-store.json
        │
        ▼
  Return GatewayPairing
        │
        ▼
  Append pairing_requested event
  Append pairing_granted event
        │
        ▼
  Device can now access gateway
```

### Capability Scopes

| Capability | Permissions |
|---|---|
| `observe` | Read status, view events |
| `control` | Start/stop miner, change mode |

### Capability Check Flow

```text
  CLI command with --client
        │
        ▼
  has_capability(device_name, required_capability)
        │
        ├── Load pairing-store.json
        ├── Find device by name
        └── Check capability in list
        │
        ├── If found: proceed with command
        │
        └── If not found or lacks capability:
              print authorization error
              exit 1
```

## Event Spine Mechanics

### Append-Only Guarantee

The spine is append-only JSONL. Events are never modified or deleted.

**Format**: One JSON object per line, terminated by newline.

```jsonl
{"id": "uuid-1", "principal_id": "...", "kind": "pairing_granted", "payload": {...}, "created_at": "...", "version": 1}
{"id": "uuid-2", "principal_id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "...", "version": 1}
```

### Querying

`get_events()` loads all events, filters by kind if specified, returns most
recent first.

```python
events = get_events(kind='control_receipt', limit=10)
# Returns last 10 control receipts, newest first
```

### Projection

The inbox is a derived view of the event spine. Different query patterns
project different subsets:

| View | Filter |
|---|---|
| Operations Inbox | pairing_requested, pairing_granted, control_receipt |
| Alerts | miner_alert |
| Hermes Feed | hermes_summary |
| Messages | user_message |

## Design Decisions

### Why Stdlib Only?

- **No dependency risk**: No external packages to maintain, update, or trust
- **Reproducible**: Same behavior across Python versions and platforms
- **Portable**: Works on Raspberry Pi OS, Ubuntu, macOS, Windows
- **Simple**: No virtual environment, no pip, no lock files

### Why LAN-Only by Default?

- **Security**: No internet-exposed control surface in milestone 1
- **Simplicity**: No TLS, no certificates, no authentication server
- **Privacy**: All traffic stays on local network
- **Blast radius**: Bugs can't affect the internet

### Why JSONL Not SQLite?

- **Simplicity**: No database server, no schema migrations
- **Transparency**: Events are plain text, human-readable
- **Reliability**: Append-only is simpler than ACID transactions
- **Auditability**: Can `grep` the event log directly

### Why Single HTML File?

- **Zero build**: No npm, no webpack, no transpilation
- **Portable**: Works from `file://` or any static server
- **Debuggable**: View source, inspect network, no source maps needed
- **Simple deployment**: Copy one file anywhere

### Why No Real Miner Backend?

- **Focus**: Milestone 1 proves the command-center shape, not mining efficiency
- **Simplicity**: A simulator has deterministic behavior
- **Speed**: No hardware dependencies, no blockchain sync
- **Contract**: The same API works for a real miner later

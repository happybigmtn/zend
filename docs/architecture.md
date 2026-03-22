# Architecture

This document describes the Zend system architecture, module responsibilities, data flows, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Zend Home System                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Client Layer                                      │   │
│  │                                                                       │   │
│  │   ┌───────────────────────┐    ┌─────────────────────────────────┐   │   │
│  │   │  Zend Home Gateway    │    │       CLI (cli.py)              │   │   │
│  │   │  (apps/zend-home-     │    │                                 │   │   │
│  │   │   gateway/index.html)  │    │   status | health | bootstrap  │   │   │
│  │   │                       │    │   pair   | control | events    │   │   │
│  │   │  Single-file mobile  │    │                                 │   │   │
│  │   │  command center UI   │    │   Human & agent interface      │   │   │
│  │   └───────────┬───────────┘    └──────────────┬──────────────────┘   │   │
│  │               │                                  │                    │   │
│  │               │         HTTP / fetch             │                    │   │
│  └───────────────┼────────────────────────────────┼────────────────────┘   │
│                  │                                │                         │
│                  ▼                                ▼                         │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     Service Layer                                      │ │
│  │                                                                       │ │
│  │                    ┌─────────────────────┐                           │ │
│  │                    │    daemon.py         │                           │ │
│  │                    │                     │                           │ │
│  │                    │  ThreadedHTTPServer │                           │ │
│  │                    │  GatewayHandler     │                           │ │
│  │                    │                     │                           │ │
│  │                    │  Routes:            │                           │ │
│  │                    │  GET  /health       │                           │ │
│  │                    │  GET  /status       │                           │ │
│  │                    │  POST /miner/start  │                           │ │
│  │                    │  POST /miner/stop   │                           │ │
│  │                    │  POST /miner/set_mode│                           │ │
│  │                    └──────────┬──────────┘                           │ │
│  │                               │                                      │ │
│  │                    ┌──────────▼──────────┐                           │ │
│  │                    │  MinerSimulator     │                           │ │
│  │                    │                     │                           │ │
│  │                    │  Simulates miner    │                           │ │
│  │                    │  status, mode,      │                           │ │
│  │                    │  health             │                           │ │
│  │                    └─────────────────────┘                           │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                     │                                      │
└─────────────────────────────────────┼──────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│     store.py        │  │      spine.py       │  │   Bootstrap Script │
│                     │  │                     │  │                     │
│  Principal Identity│  │  Event Spine        │  │  daemon.py --daemon│
│  Pairing Records    │  │  Append-only JSONL  │  │  cli.py bootstrap  │
│                     │  │                     │  │                     │
│  state/principal.json│  │  state/event-     │  │  Orchestrates       │
│  state/pairing-    │  │  spine.jsonl       │  │  first-run setup    │
│  store.json        │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

## Module Guide

### daemon.py

**Purpose**: HTTP server that exposes the miner control API and simulates miner behavior.

**Key Classes**:

| Class | Responsibility |
|-------|----------------|
| `MinerMode` | Enum: `PAUSED`, `BALANCED`, `PERFORMANCE` |
| `MinerStatus` | Enum: `RUNNING`, `STOPPED`, `OFFLINE`, `ERROR` |
| `MinerSimulator` | Simulates miner state, handles start/stop/mode changes |
| `GatewayHandler` | HTTP request handler for `/health`, `/status`, `/miner/*` |
| `ThreadedHTTPServer` | Threaded HTTP server for concurrent requests |

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `default_state_dir()` | Resolves state directory relative to repo root |
| `run_server(host, port)` | Starts the HTTP server |

**State Managed**:
- Current miner status (running/stopped)
- Current mining mode (paused/balanced/performance)
- Simulated hashrate and temperature

**Environment Variables**:
- `ZEND_STATE_DIR`: State directory path (default: `<repo>/state`)
- `ZEND_BIND_HOST`: Bind address (default: `127.0.0.1`)
- `ZEND_BIND_PORT`: Listen port (default: `8080`)

---

### cli.py

**Purpose**: Command-line interface for human and agent interaction with the daemon.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `daemon_call(method, path, data)` | Makes HTTP call to daemon |
| `cmd_status(args)` | Get miner status |
| `cmd_health(args)` | Get daemon health |
| `cmd_bootstrap(args)` | Create principal and initial pairing |
| `cmd_pair(args)` | Pair a new device |
| `cmd_control(args)` | Issue control command (start/stop/set_mode) |
| `cmd_events(args)` | List events from spine |

**Capability Checks**:
- `observe`: Required for `/status` endpoint
- `control`: Required for `/miner/*` endpoints

---

### store.py

**Purpose**: Manages principal identity and device pairing records.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `load_or_create_principal()` | Get or create the principal identity |
| `load_pairings()` | Load all pairing records |
| `pair_client(device_name, capabilities)` | Create a new pairing |
| `get_pairing_by_device(device_name)` | Get pairing by device name |
| `has_capability(device_name, capability)` | Check if device has capability |
| `list_devices()` | List all paired devices |

**Data Files**:

| File | Format | Contents |
|------|--------|----------|
| `state/principal.json` | JSON | Principal identity (id, name, created_at) |
| `state/pairing-store.json` | JSON | Device pairings (id, device_name, capabilities) |

**Principal Identity**:
```json
{
  "id": "uuid-v4",
  "name": "Zend Home",
  "created_at": "ISO-8601 timestamp"
}
```

**Pairing Record**:
```json
{
  "id": "uuid-v4",
  "principal_id": "uuid-v4",
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "ISO-8601 timestamp",
  "token_expires_at": "ISO-8601 timestamp",
  "token_used": false
}
```

---

### spine.py

**Purpose**: Append-only event journal for audit trail and inbox.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `append_event(kind, principal_id, payload)` | Append event to spine |
| `get_events(kind, limit)` | Query events (filtered by kind) |
| `append_pairing_requested(...)` | Record pairing request |
| `append_pairing_granted(...)` | Record pairing grant |
| `append_control_receipt(...)` | Record control command |
| `append_miner_alert(...)` | Record miner alert |
| `append_hermes_summary(...)` | Record Hermes summary |

**Data File**: `state/event-spine.jsonl` (JSON Lines format)

**Event Schema**:
```
{"id": "uuid", "principal_id": "uuid", "kind": "event_kind",
 "payload": {...}, "created_at": "ISO-8601", "version": 1}
```

**Event Kinds**:

| Kind | Triggered By |
|------|--------------|
| `pairing_requested` | `cli.py pair` command |
| `pairing_granted` | `cli.py pair` or `bootstrap` command |
| `capability_revoked` | Future: capability revocation |
| `miner_alert` | Future: miner health warnings |
| `control_receipt` | Any `cli.py control` command |

---

### Bootstrap Script

**File**: `scripts/bootstrap_home_miner.sh`

**Operations**:
1. Stop existing daemon (if running)
2. Start daemon in background
3. Wait for daemon to respond on `/health`
4. Run `cli.py bootstrap` to create principal and initial pairing
5. Save daemon PID to `state/daemon.pid`

**Options**:
- `--stop`: Stop the daemon
- `--daemon`: Start daemon only (no bootstrap)
- `--status`: Show daemon status

---

## Data Flow

### Control Command Flow

```
User/Agent
    │
    │ cli.py control --action set_mode --mode balanced
    │
    ▼
cli.py
    │
    │ 1. Check capability via store.py
    │ 2. POST /miner/set_mode to daemon.py
    │ 3. On success, append event via spine.py
    │
    ▼
daemon.py (GatewayHandler)
    │
    │ 1. Validate request (JSON, mode field)
    │ 2. Call miner.set_mode("balanced")
    │
    ▼
MinerSimulator
    │
    │ 1. Acquire lock
    │ 2. Update mode
    │ 3. Update hashrate based on mode
    │ 4. Return success
    │
    ▼
CLI prints receipt
spine.py appends control_receipt
```

### Status Query Flow

```
User (browser or CLI)
    │
    │ GET /status or fetch /status
    │
    ▼
daemon.py (GatewayHandler)
    │
    │ 1. Call miner.get_snapshot()
    │
    ▼
MinerSimulator.get_snapshot()
    │
    │ 1. Acquire lock
    │ 2. Calculate uptime
    │ 3. Return status dict with freshness timestamp
    │
    ▼
JSON response
    │
    │ Browser: update UI
    │ CLI: print JSON
    │
    ▼
User sees current miner state
```

---

## Auth Model

### Capability Scopes

| Capability | Allows |
|------------|--------|
| `observe` | GET /health, GET /status |
| `control` | POST /miner/start, POST /miner/stop, POST /miner/set_mode |

### Capability Check Flow

```
1. Client sends request with --client flag
2. CLI calls store.py.has_capability(device_name, required_capability)
3. If capability missing, return unauthorized error
4. If capability present, proceed with request
```

### Pairing Flow

```
1. Bootstrap creates initial pairing for alice-phone
2. alice-phone gets "observe" capability by default
3. To add "control", pair again with --capabilities observe,control
4. Or manually edit state/pairing-store.json
```

---

## Event Spine Design

### Why Append-Only?

The event spine is append-only to ensure:
- Complete audit trail
- No accidental data loss
- Simple recovery (replay events)
- No corruption from concurrent writes

### Why JSONL?

- No database dependency
- Easy to inspect with `cat` and `grep`
- Append-only by design
- Human-readable

### Future Considerations

Milestone 2+ may add:
- Encryption layer (via principal's identity key)
- Compaction/archival of old events
- Event subscription/polling

---

## Design Decisions

### Why Stdlib Only?

**Decision**: No external Python dependencies.

**Rationale**:
- Faster deployment (no pip install)
- Smaller attack surface
- Easier to audit
- Compatible with restricted environments (read-only filesystems)

### Why LAN-Only by Default?

**Decision**: Daemon binds to `127.0.0.1` by default.

**Rationale**:
- Minimizes blast radius in milestone 1
- No need for TLS/certificates
- No exposure to internet threats
- Explicit opt-in for LAN access

### Why Single HTML File?

**Decision**: Command center is a single `index.html` with no build step.

**Rationale**:
- Opens directly in browser
- No framework to learn
- Easy to customize
- Mobile-first by design

### Why Simulator, Not Real Miner?

**Decision**: Milestone 1 uses a simulator, not real mining hardware.

**Rationale**:
- Proves the control contract first
- No hardware dependency
- Easier to test and demo
- Real miner integration is milestone 2+

### Why Capability-Based Auth?

**Decision**: Devices get specific capabilities, not full access.

**Rationale**:
- Principle of least privilege
- Easier to audit (can observe without controlling)
- Graduated trust (start with observe, upgrade to control)
- Supports future revocation

---

## File Locations

```
zend/
├── services/home-miner-daemon/
│   ├── daemon.py           # HTTP server + miner simulator
│   ├── cli.py              # CLI interface
│   ├── store.py            # Principal and pairing store
│   └── spine.py            # Event spine
├── apps/zend-home-gateway/
│   └── index.html          # Command center UI
├── scripts/
│   └── bootstrap_home_miner.sh
├── state/                  # Runtime state (gitignored)
│   ├── principal.json
│   ├── pairing-store.json
│   ├── event-spine.jsonl
│   └── daemon.pid
└── docs/
    └── architecture.md     # This file
```

---

## Threading Model

The daemon uses `ThreadedHTTPServer` for concurrent request handling:

- Each request runs in a separate thread
- `MinerSimulator` uses a lock (`threading.Lock`) to protect shared state
- CLI makes sequential HTTP requests (no threading needed)

This is sufficient for milestone 1. Future versions may add:
- Connection pooling
- Async I/O (asyncio)
- Worker thread pools

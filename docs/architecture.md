# Architecture

This document describes the Zend system architecture, module responsibilities,
data flows, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Thin Mobile Client                        │
│                    (apps/zend-home-gateway/)                    │
│                      HTML + JavaScript                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP (fetch API)
                                │ LAN (127.0.0.1 or 0.0.0.0)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Home Miner Daemon                             │
│              (services/home-miner-daemon/)                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  daemon.py   │  │    cli.py    │  │   spine.py   │         │
│  │  HTTP Server │  │  CLI Tools   │  │ Event Spine │         │
│  │  + Simulator │  │  + Store     │  │  (JSONL)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐                                               │
│  │   store.py   │                                               │
│  │ Principal +  │                                               │
│  │  Pairing     │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ Simulated
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Miner Simulator                               │
│              (embedded in daemon.py)                              │
│                                                                  │
│  Status: running | stopped | offline | error                   │
│  Mode: paused | balanced | performance                          │
│  Hashrate: 0 | 50k | 150k H/s                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Module Guide

### daemon.py — HTTP Server and Miner Simulator

**Location:** `services/home-miner-daemon/daemon.py`

**Purpose:** Handles HTTP requests and simulates a miner backend.

**Key Components:**

| Component | Type | Description |
|-----------|------|-------------|
| `MinerSimulator` | Class | Simulates miner behavior (status, mode, hashrate) |
| `MinerMode` | Enum | `PAUSED`, `BALANCED`, `PERFORMANCE` |
| `MinerStatus` | Enum | `RUNNING`, `STOPPED`, `OFFLINE`, `ERROR` |
| `GatewayHandler` | Class | HTTP request handler (BaseHTTPRequestHandler) |
| `ThreadedHTTPServer` | Class | Threaded server for concurrent requests |

**Key Functions:**

| Function | Description |
|----------|-------------|
| `default_state_dir()` | Resolves state directory path |
| `run_server(host, port)` | Starts the HTTP server |

**HTTP Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Daemon health check |
| `GET` | `/status` | Miner status snapshot |
| `POST` | `/miner/start` | Start mining |
| `POST` | `/miner/stop` | Stop mining |
| `POST` | `/miner/set_mode` | Change mining mode |

**State:** The simulator maintains in-memory state for miner status, mode,
hashrate, temperature, and uptime.

**Thread Safety:** The simulator uses a `threading.Lock` to serialize state
changes. Multiple concurrent requests are handled by the threaded server.

### cli.py — Command-Line Interface

**Location:** `services/home-miner-daemon/cli.py`

**Purpose:** CLI tools for daemon interaction, pairing management, and control.

**Key Functions:**

| Function | Description |
|----------|-------------|
| `daemon_call(method, path, data)` | Makes HTTP call to daemon |
| `cmd_status(args)` | Get miner status |
| `cmd_health(args)` | Get daemon health |
| `cmd_bootstrap(args)` | Create principal and initial pairing |
| `cmd_pair(args)` | Pair a new gateway client |
| `cmd_control(args)` | Send control command to miner |
| `cmd_events(args)` | List events from spine |

**Authorization:** The CLI checks capabilities before issuing commands:

- `observe` capability required for: status, events
- `control` capability required for: start, stop, set_mode

**State:** Reads from pairing store to verify capabilities.

### spine.py — Event Spine (Append-Only Journal)

**Location:** `services/home-miner-daemon/spine.py`

**Purpose:** Append-only encrypted event journal. Source of truth for all
operational events.

**Key Components:**

| Component | Type | Description |
|-----------|------|-------------|
| `EventKind` | Enum | Event type identifiers |
| `SpineEvent` | Dataclass | Event record schema |
| `append_event()` | Function | Append new event to spine |
| `get_events()` | Function | Query events with optional filter |

**Event Kinds:**

| Kind | Description |
|------|-------------|
| `pairing_requested` | Client requested pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Permission removed |
| `miner_alert` | Miner warning or error |
| `control_receipt` | Control action result |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-to-user message |

**Storage:** Events are appended to `state/event-spine.jsonl` (JSON Lines format).
Each line is a valid JSON object representing one event.

**Schema:**

```json
{
  "id": "uuid-v4",
  "principal_id": "uuid-v4",
  "kind": "event_kind",
  "payload": {},
  "created_at": "2026-03-22T10:00:00Z",
  "version": 1
}
```

**Constraints:**

- Events are immutable once written
- No deletion or modification
- Most recent events returned first
- Optional kind filter for queries

### store.py — Principal and Pairing Storage

**Location:** `services/home-miner-daemon/store.py`

**Purpose:** Manages principal identity and device pairing records.

**Key Components:**

| Component | Type | Description |
|-----------|------|-------------|
| `Principal` | Dataclass | User identity (id, created_at, name) |
| `GatewayPairing` | Dataclass | Device pairing record |
| `load_or_create_principal()` | Function | Get or create principal |
| `pair_client()` | Function | Create new pairing |
| `get_pairing_by_device()` | Function | Get pairing by device name |
| `has_capability()` | Function | Check device capability |
| `list_devices()` | Function | List all paired devices |

**Storage:** JSON files in `ZEND_STATE_DIR/`:

| File | Content |
|------|---------|
| `principal.json` | Single principal record |
| `pairing-store.json` | Dictionary of pairing records |

**PrincipalId Contract:**

The same `PrincipalId` is used for:
1. Gateway pairing records
2. Event-spine items
3. Future inbox metadata

This ensures identity stability across miner control and future features.

**Capability Scopes:**

| Capability | Allows |
|------------|--------|
| `observe` | Read status, health, events |
| `control` | Send start, stop, set_mode commands |

## Data Flow

### Control Command Flow

```
1. Client sends command
   └─> ./scripts/set_mining_mode.sh --client my-phone --mode balanced

2. CLI checks authorization
   └─> store.has_capability('my-phone', 'control') → True

3. CLI sends HTTP request to daemon
   └─> POST /miner/set_mode {"mode": "balanced"}

4. Daemon validates request
   └─> MinerSimulator.set_mode('balanced') → success

5. Daemon returns response
   └─> {"success": true, "mode": "balanced"}

6. CLI appends control receipt to spine
   └─> spine.append_control_receipt('set_mode', 'balanced', 'accepted', principal_id)

7. CLI prints acknowledgment
   └─> "acknowledged=true"
```

### Status Query Flow

```
1. Client requests status
   └─> ./scripts/read_miner_status.sh --client my-phone

2. CLI checks authorization
   └─> store.has_capability('my-phone', 'observe') → True

3. CLI sends HTTP request to daemon
   └─> GET /status

4. Daemon returns snapshot
   └─> MinerSimulator.get_snapshot() → {...}

5. CLI prints formatted output
   └─> status=running, mode=balanced, freshness=2026-03-22T10:00:00Z
```

### Bootstrap Flow

```
1. Operator runs bootstrap
   └─> ./scripts/bootstrap_home_miner.sh

2. Script starts daemon
   └─> python3 daemon.py &

3. Script runs CLI bootstrap
   └─> python3 cli.py bootstrap --device alice-phone

4. CLI creates principal (if not exists)
   └─> store.load_or_create_principal()

5. CLI creates pairing
   └─> store.pair_client('alice-phone', ['observe'])

6. CLI appends event to spine
   └─> spine.append_pairing_granted(...)

7. Script reports success
   └─> {"principal_id": "...", "device_name": "alice-phone", ...}
```

## Auth Model

### Capability Scoping

Every paired device has a set of capabilities:

- **observe**: Can read status, health, and events
- **control**: Can send control commands (start, stop, set_mode)

Capabilities are checked at the CLI layer before calling the daemon. The daemon
itself does no auth checking (milestone 1 assumption: local access only).

### Pairing Flow

```
UNPAIRED → PAIRED_OBSERVER → PAIRED_CONTROLLER
              │                    │
              │ (explicit grant)    │ (revoke)
              ▼                    ▼
         PAIRED_CONTROLLER ←── CONTROL_ACTION
              │
              │ (expire / reset)
              ▼
         UNPAIRED
```

### Token Model

Pairing tokens are UUIDs generated at pairing time. They include an expiration
timestamp. Token replay prevention is checked during pairing.

## Design Decisions

### Why Standard Library Only?

**Decision:** No external Python dependencies.

**Rationale:**
- Reduces attack surface
- Simplifies deployment
- No dependency conflicts
- Faster startup

**Consequence:** More verbose code for HTTP serving, JSON handling, and threading.
The trade-off is acceptable for a daemon that serves a simple contract.

### Why LAN-Only for Milestone 1?

**Decision:** Daemon binds to private network interface only.

**Rationale:**
- Lowest blast radius for security
- Proves the control-plane thesis without internet exposure
- Avoids building auth infrastructure before the product is validated

**Consequence:** Remote access requires additional work (tunnel, VPN, or explicit
remote auth) in a future milestone.

### Why JSONL for Event Spine?

**Decision:** Events stored as JSON Lines (one JSON object per line).

**Rationale:**
- Simple append-only storage
- No database dependency
- Easy to inspect with standard tools
- Crash-safe (append operation)

**Consequence:** Query performance degrades with large histories. Compaction
needed for production scale.

### Why Single HTML File?

**Decision:** Gateway client is a single HTML file with inline CSS and JS.

**Rationale:**
- Zero build step
- No framework dependencies
- Opens directly in browser
- Easy to inspect and modify

**Consequence:** No code splitting, no module system, no external CSS/JS
dependencies. Appropriate for milestone 1 simplicity.

### Why Simulated Miner?

**Decision:** Milestone 1 uses a simulator, not real miner hardware.

**Rationale:**
- Faster development iteration
- No hardware dependency for contributors
- Same contract works with real backend

**Consequence:** Real miner behavior (power consumption, heat, failure modes)
not validated until later milestone.

## File Locations

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html           Gateway HTML client
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py          Package marker
│       ├── daemon.py            HTTP server + simulator
│       ├── cli.py               CLI tools
│       ├── spine.py             Event spine
│       ├── store.py             Principal + pairing store
│       └── index.html           (symlink to gateway HTML)
├── scripts/
│   ├── bootstrap_home_miner.sh  Start daemon + bootstrap
│   ├── pair_gateway_client.sh   Pair new device
│   ├── read_miner_status.sh     Read status
│   ├── set_mining_mode.sh       Control miner
│   ├── no_local_hashing_audit.sh Audit for mining
│   └── hermes_summary_smoke.sh  Hermes test
├── state/                       (created at runtime)
│   ├── principal.json           Principal identity
│   ├── pairing-store.json       Device pairings
│   ├── event-spine.jsonl        Event journal
│   └── daemon.pid               Daemon PID
└── references/
    ├── inbox-contract.md        Inbox architecture
    ├── event-spine.md           Spine contract
    ├── hermes-adapter.md        Hermes integration
    ├── error-taxonomy.md        Named errors
    └── observability.md         Log events + metrics
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Network interface |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_STATE_DIR` | `./state/` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## Observability

### Structured Log Events

| Event | When |
|-------|------|
| `gateway.bootstrap.started` | Bootstrap begins |
| `gateway.bootstrap.failed` | Bootstrap fails |
| `gateway.pairing.succeeded` | Device paired |
| `gateway.pairing.rejected` | Pairing denied |
| `gateway.status.read` | Status queried |
| `gateway.status.stale` | Stale snapshot returned |
| `gateway.control.accepted` | Control command accepted |
| `gateway.control.rejected` | Control command denied |
| `gateway.inbox.appended` | Event appended |
| `gateway.hermes.summary_appended` | Hermes summary added |

### Metrics

| Metric | Description |
|--------|-------------|
| `pairing_attempts` | Count by outcome |
| `status_reads` | Count by freshness |
| `control_commands` | Count by outcome |
| `inbox_appends` | Count by outcome |
| `hermes_actions` | Count by outcome |

## Future Architecture

### Phase 2: Real Miner Backend

Replace `MinerSimulator` with real miner driver while preserving the same API
contract. No changes to CLI, spine, or store needed.

### Phase 3: Remote Access

Add secure tunnel or relay for remote control. Preserve LAN-only as the safe
default. Add authentication layer.

### Phase 4: Hermes Integration

Connect Hermes agent through adapter. Hermes reads from event spine, appends
summaries. Capability model remains the same.

### Phase 5: Rich Inbox

Build conversation UX on top of existing event spine. Same `PrincipalId` ensures
identity continuity.

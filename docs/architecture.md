# Architecture

This document describes the Zend system architecture, module responsibilities, data flows, and design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Phone / Browser                          │
│                    (Mobile Command Center UI)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ REST API (HTTP/JSON)
                                │ LAN only by default
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Zend Home Miner Daemon                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  HTTP Server │  │   CLI Layer  │  │  MinerSimulator      │   │
│  │  (daemon.py) │  │   (cli.py)   │  │  (daemon.py)         │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                     │               │
│         └─────────────────┼─────────────────────┘               │
│                           │                                     │
│  ┌────────────────────────┼─────────────────────────────────┐  │
│  │                        ▼                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │  Event Spine │  │ Pairing Store│  │  Principal   │  │  │
│  │  │  (spine.py)  │  │  (store.py)  │  │  (store.py)  │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                  │
│  State directory: state/                                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ Control commands
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Home Miner Hardware                          │
│                   (Actual mining happens here)                   │
│                 (Simulator in milestone 1)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Module Guide

### daemon.py

**Purpose**: HTTP server and miner simulator.

**Key components**:

- `MinerSimulator`: Simulates miner behavior for milestone 1.
  - Properties: `status`, `mode`, `health`
  - Methods: `start()`, `stop()`, `set_mode(mode)`, `get_snapshot()`
  - Thread-safe with `_lock`

- `GatewayHandler`: HTTP request handler.
  - `GET /health`: Returns daemon health
  - `GET /status`: Returns miner snapshot
  - `POST /miner/start`: Start mining
  - `POST /miner/stop`: Stop mining
  - `POST /miner/set_mode`: Change mode

- `ThreadedHTTPServer`: Threaded HTTP server for concurrent requests.

**State managed**: Miner state (status, mode, hashrate, temperature, uptime).

**Key design decision**: Thread-safe simulator uses a lock to serialize state mutations. This prevents race conditions when multiple clients make concurrent requests.

### cli.py

**Purpose**: Command-line interface wrapping the daemon API and local store.

**Key functions**:

- `daemon_call(method, path, data)`: Makes HTTP requests to the daemon.
- `cmd_status(args)`: Gets miner status with capability check.
- `cmd_health(args)`: Gets daemon health.
- `cmd_bootstrap(args)`: Creates principal and initial pairing.
- `cmd_pair(args)`: Pairs a new device.
- `cmd_control(args)`: Issues control commands with capability check.
- `cmd_events(args)`: Queries the event spine.

**State managed**: None. Reads from daemon and local store, writes to store.

**Key design decision**: CLI acts as a capability gate. The HTTP layer has no auth; the CLI enforces it.

### spine.py

**Purpose**: Append-only event journal. Source of truth for the operations inbox.

**Key types**:

- `EventKind`: Enum of event types.
  - `PAIRING_REQUESTED`
  - `PAIRING_GRANTED`
  - `CAPABILITY_REVOKED`
  - `MINER_ALERT`
  - `CONTROL_RECEIPT`
  - `HERMES_SUMMARY`
  - `USER_MESSAGE`

- `SpineEvent`: Dataclass for events.
  - `id`: UUID
  - `principal_id`: Owner's principal
  - `kind`: Event type
  - `payload`: Event-specific data
  - `created_at`: ISO 8601 timestamp
  - `version`: Schema version (1)

**Key functions**:

- `append_event(kind, principal_id, payload)`: Appends an event to the JSONL file.
- `get_events(kind, limit)`: Queries events, most recent first.
- Helper functions for each event type: `append_pairing_requested()`, `append_pairing_granted()`, etc.

**State managed**: `state/event-spine.jsonl` (append-only lines).

**Key design decision**: JSONL format (one JSON object per line) enables:
- Atomic appends (no file locking needed for writes)
- Easy streaming (read line by line)
- Simple recovery (skip corrupted lines)
- No database dependency

### store.py

**Purpose**: Principal identity and device pairing records.

**Key types**:

- `Principal`: Zend principal identity.
  - `id`: UUID
  - `created_at`: ISO 8601 timestamp
  - `name`: Human-readable name

- `GatewayPairing`: Paired device record.
  - `id`: UUID
  - `principal_id`: Owner's principal
  - `device_name`: Human-readable device name
  - `capabilities`: List of capabilities
  - `paired_at`: ISO 8601 timestamp
  - `token_expires_at`: Token expiration
  - `token_used`: Whether token was used

**Key functions**:

- `load_or_create_principal()`: Gets existing or creates new principal.
- `pair_client(device_name, capabilities)`: Creates a pairing record.
- `get_pairing_by_device(device_name)`: Looks up pairing by name.
- `has_capability(device_name, capability)`: Checks if device has capability.
- `list_devices()`: Lists all paired devices.

**State managed**: `state/principal.json`, `state/pairing-store.json`.

**Key design decision**: The same `PrincipalId` is used for both gateway and future inbox. This keeps identity stable across features.

## Data Flow

### Control Command Flow

```
1. User clicks "Start Mining" in UI
           │
           ▼
2. Browser sends POST /miner/start
           │
           ▼
3. GatewayHandler.do_POST() receives request
           │
           ▼
4. MinerSimulator.start() updates state (thread-safe)
           │
           ▼
5. Response returned: {"success": true, "status": "running"}
           │
           ▼
6. CLI receives response, calls spine.append_control_receipt()
           │
           ▼
7. Event appended to state/event-spine.jsonl
           │
           ▼
8. Control receipt visible in inbox view
```

### Status Read Flow

```
1. Browser polls GET /status every 5 seconds
           │
           ▼
2. GatewayHandler.do_GET() receives request
           │
           ▼
3. MinerSimulator.get_snapshot() returns cached state
           │
           ▼
4. Response includes freshness timestamp
           │
           ▼
5. UI displays status, marks stale if timestamp is old
```

### Pairing Flow

```
1. Operator runs ./scripts/pair_gateway_client.sh
           │
           ▼
2. CLI calls store.pair_client() → creates pairing record
           │
           ▼
3. CLI calls spine.append_pairing_requested()
           │
           ▼
4. CLI calls spine.append_pairing_granted()
           │
           ▼
5. Both events appended to event spine
           │
           ▼
6. Device can now access daemon with its capabilities
```

## Auth Model

### Capability Scopes

| Capability | Permissions |
|------------|-------------|
| `observe` | Read status, view events |
| `control` | All of observe, plus start/stop/set_mode |

### How It Works

1. **Pairing**: Device pairs with a specific set of capabilities.
2. **Storage**: Pairing record stored in `state/pairing-store.json`.
3. **Enforcement**: CLI checks `has_capability()` before issuing control commands.
4. **HTTP Layer**: No auth at HTTP layer (LAN-only assumption in milestone 1).

### Future Extension

In future milestones:
- Token-based authentication with expiration
- Revocation of capabilities
- Audit trail of all auth decisions

## Event Spine

### Why JSONL?

- **Atomic appends**: Each line is a complete JSON object. No partial writes.
- **No database**: Uses filesystem only. Recovery is `rm -rf state/*`.
- **Streamable**: Process events line by line without loading all into memory.
- **Audit-friendly**: Human-readable text file. Easy to grep and inspect.

### Event Ordering

Events are ordered by append time. The most recent events are at the end of the file.

`get_events()` reads the file, reverses the list, and returns the most recent first.

### Inbox as Projection

The inbox is a derived view of the event spine, not a separate store. All events flow through the spine. Different clients filter and display events differently.

## Design Decisions

### Why stdlib only?

- **Auditable**: No hidden dependencies or supply chain risks.
- **Portable**: Works on any Python 3.10+ environment.
- **Simple**: No dependency management or version conflicts.

### Why LAN-only in milestone 1?

- **Lower blast radius**: No internet-facing attack surface.
- **Simpler**: No TLS, no certificates, no port forwarding.
- **Proof of concept**: Validates the product thesis before adding complexity.

### Why JSONL not SQLite?

- **Simplicity**: JSONL needs no database server.
- **Recovery**: Delete and recreate state is a valid recovery path.
- **Immutability**: Append-only design matches event sourcing.
- **Future migration**: Easy to migrate to a database later if needed.

### Why single HTML file?

- **No build step**: Open and it works.
- **Portable**: Copy the file anywhere.
- **Simple deployment**: Serve statically from any web server.
- **Debuggable**: View source, inspect network, no bundler magic.

### Why MinerSimulator?

- **Fast iteration**: No hardware dependency.
- **Contract validation**: Proves the API works before integrating with real miner.
- **Deterministic testing**: Simulator has predictable behavior.

## File Layout

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html              # Mobile command center UI
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py             # Package marker
│       ├── daemon.py               # HTTP server + simulator
│       ├── cli.py                  # CLI interface
│       ├── spine.py                # Event spine
│       └── store.py                # Principal + pairing store
├── scripts/
│   ├── bootstrap_home_miner.sh     # Start daemon + bootstrap
│   ├── pair_gateway_client.sh      # Pair a device
│   ├── read_miner_status.sh        # Read status
│   ├── set_mining_mode.sh          # Change mode
│   ├── hermes_summary_smoke.sh     # Test Hermes adapter
│   └── no_local_hashing_audit.sh   # Prove no on-device mining
├── state/                          # Runtime data (gitignored)
│   ├── daemon.pid                  # Daemon process ID
│   ├── event-spine.jsonl          # Event journal
│   ├── pairing-store.json         # Device pairings
│   └── principal.json            # Principal identity
├── specs/                          # Durable specs
├── plans/                          # Executable plans
├── references/                     # Architecture contracts
├── docs/                           # Documentation
└── README.md                      # This file
```

## Deployment Topology

### Single Machine (Development)

```
localhost:8080
    └── Daemon
         ├── status endpoint
         ├── control endpoints
         └── event spine
```

### Home Network (Operator)

```
Phone ──LAN──► Raspberry Pi
                    │
                    └── Daemon on 192.168.1.x:8080
                              │
                              └── index.html served or opened directly
```

### Future: Remote Access

Remote access will be added in a later milestone. Design considerations:
- TLS required
- Token-based auth with expiration
- Optional VPN instead of direct internet exposure

## Performance

### Expected Performance

| Operation | Latency |
|-----------|---------|
| Health check | < 5ms |
| Status read | < 10ms |
| Control command | < 50ms |
| Event append | < 10ms |

### Bottlenecks

- **JSONL file I/O**: Appends are fast, but reading all events is O(n).
- **Threading**: ThreadedHTTPServer handles concurrent requests.
- **Simulator**: The simulator has no I/O wait; real miners will be slower.

### Scaling Considerations

For milestone 1, single-machine deployment is expected. Future scaling paths:
- Event spine → database (PostgreSQL, SQLite)
- Status → caching layer (Redis)
- Multiple miners → load balancing

## Security

### Current Security Model

- **LAN-only**: Daemon binds to private interface by default.
- **No TLS**: HTTP only.
- **Capability-scoped pairing**: Devices have limited permissions.
- **No token expiration**: Milestone 1 limitation.

### Hardening Path

1. TLS termination
2. Token-based authentication with expiration
3. Rate limiting
4. Audit logging to separate secure store
5. Encryption at rest for state files

## Testing Strategy

### Unit Tests

Test individual modules in isolation.

```bash
python3 -m pytest services/home-miner-daemon/
```

### Integration Tests

Test the full stack via the CLI.

```bash
# Bootstrap
./scripts/bootstrap_home_miner.sh

# Verify health
curl http://127.0.0.1:8080/health

# Pair and control
./scripts/pair_gateway_client.sh --client test-device --capabilities observe,control
./scripts/set_mining_mode.sh --client test-device --mode balanced
```

### Smoke Tests

```bash
./scripts/hermes_summary_smoke.sh --client my-phone
./scripts/no_local_hashing_audit.sh --client my-phone
```

## Glossary

| Term | Definition |
|------|------------|
| **PrincipalId** | Stable identity shared by gateway and future inbox |
| **GatewayCapability** | Named permission (observe, control) |
| **MinerSnapshot** | Cached status with freshness timestamp |
| **Event Spine** | Append-only journal; source of truth |
| **Control Receipt** | Event confirming a control action |
| **Pairing** | Relationship between device and daemon |

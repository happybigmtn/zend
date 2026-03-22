# Architecture

This document explains how Zend's components fit together, the data flow through the system, and the design decisions that shape the implementation.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Thin Mobile Client                        │
│  (apps/zend-home-gateway/index.html)                            │
│  - Status Hero, Mode Switcher, Receipt Cards                    │
│  - Single HTML file, no build step                              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP JSON
                             │ pair + observe + control + inbox
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Zend Gateway Contract                         │
│  (services/home-miner-daemon/)                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │  daemon.py  │  │   cli.py    │  │      spine.py       │   │
│  │  HTTP API   │  │  CLI tools  │  │  Event Spine Store  │   │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘   │
│         │                │                    │                │
│         ▼                ▼                    ▼                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    store.py                              │   │
│  │  PrincipalId  │  GatewayPairing  │  Capabilities        │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────────┐
│ Miner Backend   │ │ Hermes      │ │ Event Spine         │
│ (simulator.py)  │ │ Adapter     │ │ (event-spine.jsonl) │
│                 │ │ (future)    │ │                     │
│ - status        │ │             │ │ - pairing_requested │
│ - start/stop    │ │             │ │ - pairing_granted   │
│ - set_mode      │ │             │ │ - control_receipt   │
│ - health        │ │             │ │ - miner_alert       │
└─────────────────┘ └─────────────┘ └─────────────────────┘
```

## Module Guide

### daemon.py

**Purpose**: HTTP server and miner simulator for milestone 1.

**Key Classes**:

- `MinerSimulator`: Simulates miner behavior (status, start, stop, set_mode, health)
- `GatewayHandler`: HTTP request handler for the gateway API
- `ThreadedHTTPServer`: Concurrent HTTP server using `socketserver.ThreadingMixIn`

**State Managed**:
- Current miner status (`running`, `stopped`, `offline`, `error`)
- Current mining mode (`paused`, `balanced`, `performance`)
- Simulated hashrate and temperature
- Uptime counter

**Key Functions**:
- `run_server(host, port)`: Start the HTTP server
- `MinerSimulator.get_snapshot()`: Return cached status object for clients

**API Endpoints**:
- `GET /health`: Health check
- `GET /status`: Miner snapshot
- `POST /miner/start`: Start mining
- `POST /miner/stop`: Stop mining
- `POST /miner/set_mode`: Change mode

### cli.py

**Purpose**: Command-line interface for controlling the daemon.

**Key Functions**:
- `daemon_call(method, path, data)`: Make HTTP request to daemon
- `cmd_status(args)`: Fetch and display miner status
- `cmd_health(args)`: Fetch and display daemon health
- `cmd_bootstrap(args)`: Create principal and initial pairing
- `cmd_pair(args)`: Pair a new device
- `cmd_control(args)`: Issue control command
- `cmd_events(args)`: Fetch events from spine

**Capability Checks**:
- `observe`: Required for `status`, `events`
- `control`: Required for `control` command

**Usage Pattern**:
```bash
python3 services/home-miner-daemon/cli.py <command> [options]
```

### store.py

**Purpose**: Persistent storage for principals, pairings, and capabilities.

**Key Classes**:
- `Principal`: User/agent identity (id, created_at, name)
- `GatewayPairing`: Paired device record (id, principal_id, device_name, capabilities, paired_at)

**Key Functions**:
- `load_or_create_principal()`: Get or create the principal identity
- `pair_client(device_name, capabilities)`: Create new pairing record
- `get_pairing_by_device(device_name)`: Lookup pairing by device name
- `has_capability(device_name, capability)`: Check device capability
- `list_devices()`: List all paired devices

**Storage Files**:
- `state/principal.json`: Principal identity
- `state/pairing-store.json`: All pairing records

**Data Model**:
```
Principal (1) ──────< GatewayPairing (many)
                         │
                         └── capabilities: ["observe", "control"]
```

### spine.py

**Purpose**: Append-only encrypted event journal. The event spine is the source of truth; the inbox is a derived view.

**Key Classes**:
- `EventKind`: Enum of event types (see below)
- `SpineEvent`: Event record (id, principal_id, kind, payload, created_at, version)

**Event Kinds**:
| Kind | Trigger |
|------|---------|
| `pairing_requested` | Device requests pairing |
| `pairing_granted` | Device paired successfully |
| `capability_revoked` | Device capability removed |
| `miner_alert` | Alert from miner backend |
| `control_receipt` | Control command acknowledged |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-to-user message |

**Key Functions**:
- `append_event(kind, principal_id, payload)`: Append new event
- `get_events(kind, limit)`: Query events with optional filter
- `append_pairing_requested(...)`: Append pairing request event
- `append_pairing_granted(...)`: Append pairing success event
- `append_control_receipt(...)`: Append control acknowledgment
- `append_miner_alert(...)`: Append alert event
- `append_hermes_summary(...)`: Append Hermes summary

**Storage Format**:
- `state/event-spine.jsonl`: One JSON object per line
- Append-only for durability
- Newest events first when queried

**Design Rationale**:
- JSONL over SQLite: Simpler, version-control-friendly, stdlib-only
- Append-only: Eventual consistency without transactions
- PrincipalId on every event: Enables inbox filtering without separate store

## Data Flow

### Control Command Flow

```
Client                    Daemon                    Miner
  │                          │                        │
  │  POST /miner/set_mode     │                        │
  │  {"mode": "balanced"}    │                        │
  │─────────────────────────>│                        │
  │                          │                        │
  │                          │  set_mode("balanced")  │
  │                          │───────────────────────>│
  │                          │                        │
  │                          │  {"success": true}     │
  │                          │<──────────────────────│
  │                          │                        │
  │                          │  spine.append_control_receipt() │
  │                          │                        │
  │  200 {"success": true}  │                        │
  │<─────────────────────────│                        │
  │                          │                        │
```

### Pairing Flow

```
Client                    CLI                       Store                    Spine
  │                         │                         │                        │
  │  cli.py pair --device   │                         │                        │
  │  --capabilities control │                         │                        │
  │────────────────────────>│                         │                        │
  │                         │                         │                        │
  │                         │  pair_client()          │                        │
  │                         │────────────────────────>│                        │
  │                         │                         │                        │
  │                         │  GatewayPairing created │                        │
  │                         │<────────────────────────│                        │
  │                         │                         │                        │
  │                         │  append_pairing_requested()                     │
  │                         │───────────────────────────────────────────────> │
  │                         │                         │                        │
  │                         │  append_pairing_granted()                      │
  │                         │───────────────────────────────────────────────> │
  │                         │                         │                        │
  │  {"success": true, ...}│                         │                        │
  │<────────────────────────│                         │                        │
```

### Status Read Flow

```
Client                    Daemon
  │                          │
  │  GET /status             │
  │─────────────────────────>│
  │                          │
  │                          │  MinerSimulator.get_snapshot()
  │                          │  - current status
  │                          │  - current mode
  │                          │  - hashrate
  │                          │  - freshness timestamp
  │                          │
  │  200 {"status": "...",   │
  │       "freshness": "..."} │
  │<─────────────────────────│
```

## Auth Model

### PrincipalId

Every user or agent has one `PrincipalId`. This identity:
- Owns all pairing records
- Appears on every event in the spine
- Will be used for future inbox access

Created once on first bootstrap and persisted to `state/principal.json`.

### Capabilities

Phase 1 supports two capabilities:

| Capability | Grants |
|------------|--------|
| `observe` | Read miner status, view events |
| `control` | Change modes, start/stop mining |

Devices can have both (`observe,control`) or just one (`observe`).

### Pairing Records

Each paired device stores:
- `id`: Unique pairing identifier
- `principal_id`: Owner's principal
- `device_name`: Human-readable name
- `capabilities`: List of granted capabilities
- `paired_at`: When pairing occurred
- `token_expires_at`: Token expiration (for future token-based auth)

## Design Decisions

### Why stdlib-only?

- No dependency management
- No pip install step
- Easier to audit
- Faster cold starts
- Works in restricted environments

### Why LAN-only for milestone 1?

- Minimizes blast radius
- No need for TLS/certificates
- No port forwarding complexity
- Trust boundary is the home network

### Why JSONL not SQLite?

- Simpler implementation
- Human-readable for debugging
- Version-control friendly
- Easier backup/restore
- No C extension dependencies

### Why single HTML file?

- No build step
- No npm/webpack complexity
- Can be served by any static file server
- Easy to inspect and modify
- Works offline once loaded

### Why simulator not real miner?

- Faster iteration
- No specialized hardware required
- Deterministic behavior for testing
- Same API contract as real miner

### Why event spine as source of truth?

- Single canonical store
- Audit trail for all operations
- Enables inbox projection
- Supports future analytics

## Future Extensions

### Real Miner Backend

Replace `MinerSimulator` with a real miner client that:
- Connects to hardware (USB, network)
- Uses manufacturer SDK
- Exposes same status/control contract

### Hermes Integration

Add Hermes adapter that:
- Connects to Hermes Gateway
- Translates between Zend and Hermes protocols
- Routes Hermes events through the spine

### Remote Access

Add secure tunneling for remote control:
- WireGuard or Tailscale integration
- Token-based authentication
- Encrypted transport

### Rich Inbox

Project inbox from spine:
- Conversation threading
- Contact policies
- Read state
- Search index

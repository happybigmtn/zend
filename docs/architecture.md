# Zend Architecture

This document describes the system design of Zend Home Miner. It explains how components connect, what each module does, and why key decisions were made.

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                         Phone Browser                               │
│               apps/zend-home-gateway/index.html                      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Home  │  Inbox  │  Agent  │  Device                        │   │
│  └────┬───────────────────────────────────────────────────────┘   │
│       │                                                               │
│       │  fetch() calls                                               │
│       ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   Daemon HTTP API                               │ │
│  │                   (services/home-miner-daemon/daemon.py)       │ │
│  │                                                                    │ │
│  │  GatewayHandler                                                  │ │
│  │    ├─ GET  /health                                               │ │
│  │    ├─ GET  /status                                               │ │
│  │    ├─ POST /miner/start                                          │ │
│  │    ├─ POST /miner/stop                                           │ │
│  │    └─ POST /miner/set_mode                                       │ │
│  └────┬───────────────────────────────────────────────────────────┘ │
│       │                                                               │
│       ├──────────────────────┬───────────────────────────────────────┤
│       │                      │                                       │
│       ▼                      ▼                                       │
│  ┌────────────┐       ┌─────────────┐                                │
│  │   Miner    │       │   Spine     │                                │
│  │ Simulator  │       │   Events    │                                │
│  │(daemon.py) │       │ (spine.py)  │                                │
│  └────────────┘       └──────┬──────┘                                │
│       │                      │                                       │
│       │                      ▼                                       │
│       │              ┌─────────────┐                                 │
│       │              │   Store     │                                 │
│       │              │ (store.py)  │                                 │
│       │              └──────┬──────┘                                 │
│       │                     │                                        │
│       ▼                     ▼                                        │
│  ┌─────────────────────────────────────┐                             │
│  │            state/                    │                             │
│  │  ├── principal.json                 │                             │
│  │  ├── pairing-store.json            │                             │
│  │  └── event-spine.jsonl             │                             │
│  └─────────────────────────────────────┘                             │
└────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### daemon.py — HTTP API Server

The daemon exposes a REST API for controlling the home miner. It uses Python's built-in `http.server` (no external dependencies).

**Key components:**

- `MinerSimulator`: A class that models miner state (status, mode, hashrate, temperature, uptime)
- `GatewayHandler`: HTTP request handler routing paths to miner operations
- `ThreadedHTTPServer`: Concurrent request handler using `socketserver.ThreadingMixIn`

**Miner modes:**
- `paused`: Mining disabled, 0 H/s
- `balanced`: Moderate hashrate (~50 kH/s)
- `performance`: Maximum hashrate (~150 kH/s)

**Miner states:**
- `running`: Actively mining (or simulating)
- `stopped`: Mining paused
- `offline`: Not connected
- `error`: Fault condition

### cli.py — Command-Line Interface

The CLI provides human-readable commands for daemon interaction. It handles authentication checks against the pairing store.

**Commands:**
- `status [--client NAME]`: Get miner status snapshot
- `health`: Get daemon health check
- `bootstrap [--device NAME]`: Create principal and first pairing
- `pair --device NAME --capabilities OBSERVE,CONTROL`: Pair a new device
- `control --client NAME --action ACTION [--mode MODE]`: Control miner
- `events [--client NAME] [--kind KIND] [--limit N]`: Query event spine

### spine.py — Event Spine

The event spine is an append-only journal. Every significant operation appends a JSON line to `state/event-spine.jsonl`.

**Event kinds:**
- `pairing_requested`: Device requested pairing with capabilities
- `pairing_granted`: Pairing was approved
- `capability_revoked`: Permission was revoked
- `miner_alert`: System alert (temperature, error, etc.)
- `control_receipt`: Control command acknowledgment
- `hermes_summary`: Agent activity summary
- `user_message`: User-initiated message

**Why append-only?**
- Auditability: Every operation is recorded
- Recoverability: State can be reconstructed from events
- Immutability: No accidental modifications

### store.py — Principal and Pairing Store

The store manages identity and authorization.

**Principal:**
- Unique identifier for the home miner installation
- Created once at bootstrap
- Persisted to `state/principal.json`

**Pairing:**
- Associates a device name with capabilities
- Capabilities: `observe` (read status), `control` (send commands)
- Persisted to `state/pairing-store.json`

## Data Flow

### Control Command Flow

```
Phone UI           CLI              Daemon            Miner
   │                │                 │                 │
   │  set_mode      │                 │                 │
   │────────────────>                 │                 │
   │                │  POST /miner/   │                 │
   │                │  set_mode       │                 │
   │                │────────────────>                 │
   │                │                 │  set_mode()     │
   │                │                 │────────────────>│
   │                │                 │                 │
   │                │  {success: true}                 │
   │                │<────────────────│                 │
   │                │  control_receipt│                 │
   │                │  (spine)        │                 │
   │                │                 │                 │
   │  {acknowledged}│                 │                 │
   │<────────────────│                 │                 │
```

### Status Query Flow

```
Phone UI           Daemon            Miner
   │                │                 │
   │  GET /status   │                 │
   │────────────────>                 │
   │                │  get_snapshot() │
   │                │────────────────>│
   │                │  {status, mode} │
   │                │<────────────────│
   │  {status, mode}│                 │
   │<────────────────│                 │
```

## Auth Model

Zend uses a capability-based model for the **CLI path**:

1. **Principal**: The home miner has a unique identity
2. **Pairing**: Devices are paired with specific capabilities
3. **Capability check**: CLI commands verify the device has the required capability before acting

```
observe capability → Can read status, health, events (CLI path)
control capability → Can send start/stop/mode commands (CLI path)
```

### HTTP API — No Authentication in Milestone 1

The HTTP API (`/miner/start`, `/miner/stop`, `/miner/set_mode`) has **no authentication**. Any process on the network can call these endpoints directly, bypassing CLI capability checks entirely. This is a known limitation of milestone 1.

The CLI path enforces capabilities; the HTTP API does not. See [api-reference.md](api-reference.md) for details.

The assumption for milestone 1 is LAN-only access — do not expose the daemon on untrusted networks.

## Design Decisions

### Why stdlib only?

No external dependencies means:
- Minimal attack surface
- No dependency conflicts
- Portable (works everywhere Python runs)
- Easier to audit

### Why LAN-only binding?

The daemon binds to `127.0.0.1` by default. Exposing it beyond the local network requires explicit configuration. This is intentional—Zend is designed for home deployments where the operator has physical control of the network.

### Why JSONL not SQLite?

The event spine uses append-only JSON Lines format:
- Simple: no database setup
- Auditable: human-readable lines
- Resilient: corrupted lines don't break the whole file
- Portable: works with standard shell tools

### Why single HTML file?

The command center is `apps/zend-home-gateway/index.html`—a self-contained file that:
- Requires no build step
- Works from `file://` or a simple HTTP server
- Can be bookmarked or added to home screen
- Loads instantly

## State Management

All state lives in `state/` (configurable via `ZEND_STATE_DIR`):

| File | Purpose |
|------|---------|
| `principal.json` | Home miner identity |
| `pairing-store.json` | Device pairings and capabilities |
| `event-spine.jsonl` | Append-only operation journal |
| `daemon.pid` | Daemon process ID (runtime) |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon HTTP port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI daemon URL |

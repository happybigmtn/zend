# Zend Architecture

This document describes the Zend system architecture with system diagrams, module explanations, and data flow descriptions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Thin Mobile Command Center                       │
│                  apps/zend-home-gateway/index.html                   │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │   Home   │  │  Inbox   │  │  Agent   │  │  Device  │           │
│  │  Screen  │  │  Screen  │  │  Screen  │  │  Screen  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP REST
                             │ observe + control
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Home Miner Daemon                             │
│                   services/home-miner-daemon/                        │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    GatewayHandler                            │   │
│  │              (HTTP server, routes requests)                  │   │
│  │                                                              │   │
│  │  GET /health    GET /status    POST /miner/*                │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                      │
│  ┌────────────────────────────▼────────────────────────────────┐   │
│  │                   MinerSimulator                             │   │
│  │              (status, modes, health)                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │    spine.py      │  │    store.py      │  │   cli.py        │   │
│  │  Event Journal   │  │  Principal +      │  │  CLI Interface  │   │
│  │                  │  │  Pairing Store   │  │                 │   │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Hermes Adapter                                │
│                   (references/hermes-adapter.md)                    │
│                                                                      │
│  - Observe-only for milestone 1                                     │
│  - Summary append to event spine                                    │
│  - Delegated authority via adapter                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### services/home-miner-daemon/daemon.py

The core HTTP server and miner simulator.

**Purpose:** Exposes a LAN-only REST API for miner control.

**Key Components:**
- `MinerSimulator` — Simulates miner behavior for milestone 1
- `GatewayHandler` — HTTP request router
- `ThreadedHTTPServer` — Concurrent request handling

**Key Functions:**
```python
miner.health                  # Property: returns healthy status and uptime
miner.start() -> dict           # Start mining, returns success/error
miner.stop() -> dict            # Stop mining, returns success/error
miner.set_mode(mode) -> dict    # Set mode (paused/balanced/performance)
miner.get_snapshot() -> dict    # Current status snapshot
```

**State Managed:**
- Current miner status (running/stopped/offline/error)
- Current operating mode (paused/balanced/performance)
- Simulated hashrate based on mode
- Temperature and uptime counters

### services/home-miner-daemon/cli.py

Command-line interface for daemon interaction.

**Purpose:** Human and agent-facing tool for controlling the daemon.

**Commands:**
```bash
python3 cli.py health                        # Get daemon health
python3 cli.py status --client <name>        # Get miner status
python3 cli.py bootstrap --device <name>     # Create principal + pair device
python3 cli.py pair --device <name> --capabilities <list>
python3 cli.py control --client <name> --action <start|stop|set_mode> --mode <mode>
python3 cli.py events --client <name> --kind <type> --limit <n>
```

**Key Functions:**
```python
daemon_call(method, path, data) -> dict   # HTTP call to daemon
cmd_status(args) -> int                   # Handle status command
cmd_control(args) -> int                  # Handle control command
cmd_events(args) -> int                   # Handle events command
```

### services/home-miner-daemon/spine.py

Append-only encrypted event journal.

**Purpose:** Single source of truth for all operational events.

**Event Kinds:**
- `pairing_requested` — Device requested pairing
- `pairing_granted` — Pairing approved
- `capability_revoked` — Permission revoked
- `miner_alert` — Miner warning or error
- `control_receipt` — Control action result
- `hermes_summary` — Hermes agent summary
- `user_message` — Encrypted user message

**Key Functions:**
```python
append_event(kind, principal_id, payload) -> SpineEvent
get_events(kind=None, limit=100) -> list[SpineEvent]
append_pairing_requested(device, capabilities, principal_id)
append_pairing_granted(device, capabilities, principal_id)
append_control_receipt(command, mode, status, principal_id)
```

**Storage:** JSONL file at `state/event-spine.jsonl`

### services/home-miner-daemon/store.py

Principal identity and pairing records.

**Purpose:** Manages stable identity and device permissions.

**Key Types:**
```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str    # ISO 8601
    name: str          # Human name

@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list  # ['observe', 'control']
    paired_at: str
    token_expires_at: str
```

**Key Functions:**
```python
load_or_create_principal() -> Principal
pair_client(device_name, capabilities) -> GatewayPairing
get_pairing_by_device(device_name) -> GatewayPairing
has_capability(device_name, capability) -> bool
list_devices() -> list[GatewayPairing]
```

**Storage:** JSON files at `state/principal.json` and `state/pairing-store.json`

### apps/zend-home-gateway/index.html

Single-file command center UI.

**Purpose:** Mobile-first miner control surface.

**Screens:**
1. **Home** — Status hero, mode switcher, quick actions, latest receipt
2. **Inbox** — Operational events (receipts, alerts, summaries)
3. **Agent** — Hermes connection status and authority
4. **Device** — Device name, permissions, pairing info

**Key Functions:**
```javascript
fetchStatus()         // Poll daemon for miner status
updateUI()            // Sync DOM with state
formatHashrate(hs)    // Format hashrate display
showAlert(message)    // Show temporary notification
```

**API Calls:**
- `GET /health` — Daemon health check
- `GET /status` — Miner status snapshot
- `POST /miner/start` — Start mining
- `POST /miner/stop` — Stop mining
- `POST /miner/set_mode` — Change mode

## Data Flow

### Control Command Flow

```
User taps "Start Mining"
         │
         ▼
HTML Button Click Handler
         │
         ▼
fetch('/miner/start', { method: 'POST' })
         │
         ▼
GatewayHandler.do_POST()
         │
         ▼
miner.start()
         │
         ├──► Update internal state
         │
         └──► Return { success: true/false }
                   │
                   ▼
HTML Response Handler
         │
         ▼
Update Status Hero
         │
         ▼
CLI command also triggers:
         │
         ▼
spine.append_control_receipt()
         │
         ▼
Append to event-spine.jsonl
```

### Pairing Flow

```
./scripts/bootstrap_home_miner.sh
         │
         ▼
Create/load Principal
         │
         ▼
pair_client('alice-phone', ['observe', 'control'])
         │
         ├──► Create GatewayPairing record
         │
         ├──► Append pairing_requested event
         │
         └──► Append pairing_granted event
                   │
                   ▼
         Return pairing bundle to user
```

## Auth Model

### Capability Scopes

| Capability | Permissions |
|------------|-------------|
| `observe` | Read miner status, health, events |
| `control` | Start/stop mining, change modes |

### Authorization Flow

```
Request arrives at GatewayHandler
         │
         ▼
Parse request body (if POST)
         │
         ▼
Route to appropriate handler
         │
         ▼
For /miner/* endpoints:
         │
         ▼
CLI checks has_capability(client, 'control')
         │
         ├─── No control ──► Return 401 unauthorized
         │
         └─── Has control ─► Proceed to daemon_call()
```

## Design Decisions

### Why stdlib Only

The daemon uses only Python standard library:
- No pip dependencies to manage
- Easier deployment on restricted systems
- Smaller attack surface
- Milestone 1 focuses on contract, not features

### Why LAN-Only for Milestone 1

- Lowest blast radius for first deployment
- Proves the control-plane thesis without internet exposure
- Operators can add tunneling later if needed

### Why JSONL for Event Spine

- Append-only semantics are natural for JSONL
- No database dependency
- Easy to inspect and debug
- Can be replayed for recovery

### Why Single HTML File

- Zero build step
- Opens directly in browser
- No server-side rendering
- Easy to audit and verify

### Why Capability Scoping

- `observe` without `control` is safe for read-only access
- `control` enables full miner management
- Future capabilities can be added (e.g., `tunnel`, `message`)

## Future Expansion

The architecture supports future capabilities:

1. **Remote Access** — Add secure tunneling (WireGuard, tailscale)
2. **Richer Inbox** — Full conversation UX on same event spine
3. **Multiple Miners** — Extend daemon to manage multiple miners
4. **Hermes Control** — Add control capability to Hermes adapter
5. **Metrics Dashboard** — Historical visualization of miner stats

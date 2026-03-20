# Private Control Plane Contract

**Status:** Implemented
**Lane:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Overview

This document describes the implemented private control plane for Zend Home Miner milestone 1. The control plane enables capability-scoped pairing between mobile clients and a home miner daemon, with all operations recorded to an encrypted event spine.

## Implemented Components

### 1. Principal Identity (`store.py`)

```python
@dataclass
class Principal:
    id: str          # UUID v4
    created_at: str  # ISO 8601
    name: str        # Human-readable name
```

The `PrincipalId` is the stable identity assigned to a Zend Home. It is referenced by:
- Gateway pairing records
- Event-spine items
- Future inbox metadata (deferred)

### 2. Gateway Pairing Records (`store.py`)

```python
@dataclass
class GatewayPairing:
    id: str                    # UUID v4
    principal_id: str           # References PrincipalId
    device_name: str           # Human-readable device name
    capabilities: list          # ['observe'] or ['observe', 'control']
    paired_at: str             # ISO 8601
    token_expires_at: str      # ISO 8601
    token_used: bool           # Anti-replay flag
```

**Capability Scopes:**
- `observe`: Read miner status, health, and snapshots
- `control`: Issue start/stop/set_mode commands

### 3. Event Spine (`spine.py`)

Append-only encrypted event journal. All events flow through here first; the inbox is a derived view.

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"

@dataclass
class SpineEvent:
    id: str
    principal_id: str
    kind: str
    payload: dict
    created_at: str
    version: int = 1
```

### 4. Home Miner Daemon (`daemon.py`)

LAN-only HTTP server exposing the gateway contract:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Daemon health check |
| `/status` | GET | `observe` | Cached miner snapshot with freshness timestamp |
| `/miner/start` | POST | `control` | Start mining |
| `/miner/stop` | POST | `control` | Stop mining |
| `/miner/set_mode` | POST | `control` | Set mode (paused/balanced/performance) |

### 5. CLI Commands (`cli.py`)

| Command | Auth | Description |
|---------|------|-------------|
| `bootstrap --device <name>` | None | Create principal and initial pairing with `observe` |
| `pair --device <name> --capabilities <list>` | None | Pair new client |
| `status --client <name>` | `observe` | Read miner status |
| `control --client <name> --action <act> --mode <mode>` | `control` | Issue control command |
| `events --client <name> --kind <kind> --limit <n>` | `observe` | Query event spine |

## Data Flow

```
CLI Command
    |
    v
cli.py (auth check via store.has_capability)
    |
    v
daemon.py (HTTP API - MinerSimulator)
    |
    v
spine.py (append_event -> event-spine.jsonl)
    |
    v
Event Spine (source of truth)
    |
    v
Inbox (derived view via spine.get_events)
```

## Implementation Locations

| Component | File | Key Functions |
|-----------|------|---------------|
| Principal Store | `services/home-miner-daemon/store.py` | `load_or_create_principal()` |
| Pairing Store | `services/home-miner-daemon/store.py` | `pair_client()`, `get_pairing_by_device()`, `has_capability()` |
| Event Spine | `services/home-miner-daemon/spine.py` | `append_event()`, `get_events()`, `append_pairing_granted()`, `append_control_receipt()` |
| Miner Simulator | `services/home-miner-daemon/daemon.py` | `MinerSimulator` class |
| Gateway Handler | `services/home-miner-daemon/daemon.py` | `GatewayHandler.do_GET()`, `do_POST()` |
| CLI | `services/home-miner-daemon/cli.py` | `cmd_bootstrap()`, `cmd_pair()`, `cmd_status()`, `cmd_control()`, `cmd_events()` |

## State Files

| File | Location | Description |
|------|----------|-------------|
| `principal.json` | `state/` | Single principal identity |
| `pairing-store.json` | `state/` | All paired devices |
| `event-spine.jsonl` | `state/` | Append-only event journal |

## Milestone 1 Boundaries

**In Scope:**
- LAN-only daemon binding (127.0.0.1)
- `observe` and `control` capability scopes
- PrincipalId shared across gateway and future inbox
- Event spine as source of truth
- Control receipt events for all commands

**Out of Scope:**
- Payout-target mutation
- Rich conversation UX
- Remote/internet-facing gateway
- Hermes direct miner control

## Next Steps

1. Add encrypted memo transport integration for user messages
2. Implement trust ceremony UI flow
3. Add Hermes adapter for delegated summaries
4. Implement capability revocation

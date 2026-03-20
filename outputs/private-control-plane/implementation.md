# Private Control Plane — Implementation

**Status:** Milestone 1 Implementation Complete
**Generated:** 2026-03-20

## Overview

This document describes the implementation of the private control plane slice for Zend, covering the services and scripts that implement the control-plane contract.

## Implementation Structure

```
services/home-miner-daemon/
├── daemon.py      # HTTP server + miner simulator
├── store.py       # Principal and pairing management
├── spine.py       # Event spine append and query
├── cli.py         # Command-line interface
└── __init__.py

scripts/
├── bootstrap_home_miner.sh
├── pair_gateway_client.sh
├── read_miner_status.sh
├── set_mining_mode.sh
├── hermes_summary_smoke.sh
└── no_local_hashing_audit.sh
```

## Principal Identity Implementation

### Data Model

```python
# store.py
@dataclass
class Principal:
    id: str          # UUID v4
    created_at: str  # ISO 8601
    name: str        # "Zend Home"
```

### Storage

- **File:** `state/principal.json`
- **Created by:** `store.py:load_or_create_principal()`
- **Loaded by:** All CLI commands that need principal_id

### Flow

1. On first bootstrap, `load_or_create_principal()` checks if `principal.json` exists
2. If not, creates new Principal with `uuid.uuid4()`
3. Principal is loaded on each CLI invocation to attach events to correct identity

## Capability-Scoped Pairing Implementation

### Data Model

```python
# store.py
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list  # ['observe'] or ['observe', 'control']
    paired_at: str
    token_expires_at: str
    token_used: bool = False
```

### Storage

- **File:** `state/pairing-store.json`
- **Schema:** Dict mapping pairing ID to pairing record

### Capability Checks

```python
# store.py:has_capability()
def has_capability(device_name: str, capability: str) -> bool:
    pairing = get_pairing_by_device(device_name)
    if not pairing:
        return False
    return capability in pairing.capabilities
```

### CLI Enforcement

| Command | Required Capability |
|---------|---------------------|
| `cli.py status` | `observe` OR `control` |
| `cli.py control --action start/stop` | `control` |
| `cli.py control --action set_mode` | `control` |
| `cli.py events` | `observe` OR `control` |

### Constraints Enforced

1. **Duplicate device names rejected** — `store.py:99-101`
2. **Capability boundary respected** — `cli.py:134-139` returns `unauthorized` error
3. **Token expiration tracked** — `token_expires_at` stored but not yet enforced

## Event Spine Implementation

### Data Model

```python
# spine.py
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

### Storage

- **File:** `state/event-spine.jsonl` (append-only JSON lines)
- **Append:** `spine.py:_save_event()` opens in append mode
- **Load:** `spine.py:_load_events()` reads all lines, parses JSON

### Source of Truth Enforcement

The spine is the **only** event store. All CLI commands that modify state append to the spine before returning success:

| CLI Command | Events Appended |
|-------------|-----------------|
| `cli.py bootstrap` | `pairing_granted` |
| `cli.py pair` | `pairing_requested`, `pairing_granted` |
| `cli.py control` | `control_receipt` |

### Event Flow

```
User Action → CLI → Daemon → Miner Simulator → Receipt
                ↓
           spine.append_*() → event-spine.jsonl
```

## Daemon HTTP API

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/status` | GET | None | Miner snapshot |
| `/miner/start` | POST | None* | Start mining |
| `/miner/stop` | POST | None* | Stop mining |
| `/miner/set_mode` | POST | None* | Set mode |
| `/spine/events` | GET | None* | List events |

*Note: Direct daemon endpoints have no auth. Auth is enforced at the CLI layer via `has_capability()`.

### Miner Simulator

```python
# daemon.py:MinerSimulator
class MinerSimulator:
    def start() -> dict
    def stop() -> dict
    def set_mode(mode: str) -> dict
    def get_snapshot() -> dict  # Includes freshness timestamp
```

### Thread Safety

The `MinerSimulator` uses a `threading.Lock()` to serialize access to miner state, preventing race conditions on concurrent control commands.

## Scripts

### bootstrap_home_miner.sh

1. Stops any existing daemon
2. Starts daemon on `127.0.0.1:8080` (LAN-only for milestone 1)
3. Runs `cli.py bootstrap` to create principal and initial pairing
4. Writes PID to `state/daemon.pid`

### pair_gateway_client.sh

1. Validates `--client` argument
2. Runs `cli.py pair --device <name> --capabilities <caps>`
3. Prints success with device name and capabilities

### read_miner_status.sh

1. Runs `cli.py status --client <name>`
2. Prints miner snapshot with freshness

### set_mining_mode.sh

1. Checks client has `control` capability via CLI
2. Runs `cli.py control --client <name> --action set_mode --mode <mode>`
3. Prints acknowledgement

### hermes_summary_smoke.sh

1. Runs `cli.py events` to verify spine access
2. Demonstrates Hermes summary would append to spine

## LAN-Only Constraint

**Milestone 1 binding:** `127.0.0.1:8080`

Set via environment:
- `ZEND_BIND_HOST` (default: `127.0.0.1`)
- `ZEND_BIND_PORT` (default: `8080`)

Production deployment on LAN would set `ZEND_BIND_HOST` to the local network interface IP.

## State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | PrincipalId and creation time |
| `state/pairing-store.json` | All paired devices and capabilities |
| `state/event-spine.jsonl` | Append-only event journal |
| `state/daemon.pid` | Running daemon PID |

All files are created in `state/` which is gitignored.

## Implementation Notes

### No Encryption in Milestone 1

Event payloads are plaintext JSON. Encryption is deferred to a later phase when real Zcash memo transport is integrated.

### Token Expiration Not Enforced

`token_expires_at` is stored in pairing records but the daemon does not yet check token validity on requests. This is acceptable for milestone 1 LAN-only deployment.

### Control Serialization

The `MinerSimulator` uses a lock to serialize control commands within a single daemon process. For distributed deployment, a proper distributed lock or consensus mechanism would be needed.

### Hermes Integration

Hermes adapter is contract-defined in `references/hermes-adapter.md` but not yet connected. Milestone 1 scope is observe-only plus summary append, which is sufficient for the contract.

# Hermes Adapter Implementation — Spec

**Status:** Implemented
**Date:** 2026-03-23
**Lane:** hermes-adapter-implementation

## Purpose

This document specifies the Hermes adapter implementation for the Zend Home Miner Daemon. The adapter enables an AI agent (Hermes) to connect to the daemon through a scoped interface that enforces capability boundaries: Hermes can observe miner status and append summaries, but cannot issue control commands or read user messages.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter (hermes.py)
      |
      +-- validate_hermes_auth() -- enforce capability scope
      +-- read_status() -- observe capability
      +-- append_summary() -- summarize capability  
      +-- get_filtered_events() -- filter user_message
      |
      v
Event Spine
```

## Capability Model

Hermes operates with a **reduced capability set** compared to human-controlled gateway clients:

| Capability | Gateway Client | Hermes Agent |
|------------|----------------|--------------|
| observe    | ✓              | ✓            |
| summarize  | ✗              | ✓            |
| control    | ✓              | ✗            |

**Key invariant:** Hermes must NEVER have `control` capability. This is enforced by the adapter before any request reaches the event spine.

## Module Interface

### hermes.py

```python
# Constants
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]

# Data classes
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    device_name: str
    connected_at: str
    token_expires_at: str

@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token: str
    token_expires_at: str

# Core functions
def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing
def connect(authority_token: str) -> HermesConnection
def validate_hermes_auth(hermes_id: str) -> HermesConnection
def read_status(connection: HermesConnection) -> dict
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]
def check_control_capability(connection: HermesConnection) -> bool
def get_hermes_status(connection: HermesConnection) -> dict
```

## Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing with observe+summarize |
| `/hermes/connect` | POST | None | Connect with authority token |
| `/hermes/status` | GET | `Authorization: Hermes <id>` | Read miner status (observe) |
| `/hermes/summary` | POST | `Authorization: Hermes <id>` | Append summary (summarize) |
| `/hermes/events` | GET | `Authorization: Hermes <id>` | Read filtered events |
| `/miner/start` | POST | — | BLOCKED for Hermes |
| `/miner/stop` | POST | — | BLOCKED for Hermes |
| `/miner/set_mode` | POST | — | BLOCKED for Hermes |

### Authorization Header

Hermes uses a distinct header scheme: `Authorization: Hermes <hermes_id>`

This distinguishes Hermes auth from device pairing auth.

## Event Filtering

Hermes can read events:

- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may have generated
- `control_receipt` — to understand recent actions

Hermes CANNOT read:

- `user_message` — private user communications (filtered out)

## Data Storage

Hermes pairings are stored in `state/hermes-pairing-store.json`:

```json
{
  "hermes-001": {
    "hermes_id": "hermes-001",
    "principal_id": "uuid",
    "device_name": "hermes-agent",
    "capabilities": ["observe", "summarize"],
    "paired_at": "2026-03-23T...",
    "token": "uuid",
    "token_expires_at": "2026-03-23T..."
  }
}
```

## CLI Commands

```bash
# Pair Hermes
python cli.py hermes pair --hermes-id hermes-001

# Get Hermes status
python cli.py hermes status --hermes-id hermes-001

# Append summary
python cli.py hermes summary --hermes-id hermes-001 --summary "Miner running normally"

# List filtered events
python cli.py hermes events --hermes-id hermes-001 --limit 20

# Test control boundary (should pass - Hermes cannot control)
python cli.py hermes test-control --hermes-id hermes-001
```

## Security Boundaries

1. **Control blocked:** Any request with `Authorization: Hermes <id>` to `/miner/*` endpoints returns 403 with `HERMES_UNAUTHORIZED`.

2. **Capability enforcement:** Before any operation, the adapter validates that the required capability exists in `connection.capabilities`.

3. **Event filtering:** `get_filtered_events()` removes `user_message` events before returning.

4. **Token validation:** `connect()` validates the authority token structure and checks for Hermes-appropriate capabilities.

## Dependencies

- `daemon.py` — miner simulator and HTTP server
- `spine.py` — event spine operations
- `store.py` — principal and pairing storage

## Acceptance Criteria

1. Hermes can connect with authority token
2. Hermes can read miner status via `/hermes/status`
3. Hermes can append summaries via `/hermes/summary`
4. Hermes CANNOT issue control commands (returns 403)
5. Hermes CANNOT read `user_message` events (filtered)
6. All CLI hermes subcommands work correctly
7. Idempotent pairing (same hermes_id re-pairs without error)

# Hermes Adapter Implementation — Specification

**Status:** Pre-Implementation (plan reviewed, no code produced)
**Generated:** 2026-03-22

## Overview

The Hermes adapter is a Python module (`services/home-miner-daemon/hermes.py`) that mediates between an external Hermes AI agent and the Zend gateway contract. It enforces a capability boundary: Hermes can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages.

The adapter sits in-process with the daemon, not as a separate service. It filters requests before they reach the gateway contract, ensuring Hermes operates within its delegated authority scope.

## Architecture

```
Hermes Agent (external)
      |
      v  HTTP: Authorization: Hermes <hermes_id>
Zend Hermes Adapter (hermes.py, in-process)
      |
      v  Internal function calls
Zend Gateway Contract (daemon.py, spine.py, store.py)
      |
      v
Event Spine (event-spine.jsonl)
```

## Capability Model

### Hermes Capabilities (M1)

| Capability | Read | Write | Scope |
|-----------|------|-------|-------|
| `observe` | Miner status, filtered events | None | Status snapshot only |
| `summarize` | None | `hermes_summary` events | Append-only to spine |

### Forbidden Actions

- `POST /miner/start`, `/miner/stop`, `/miner/set_mode` — rejected with 403
- Read `user_message` events — filtered at adapter layer
- Write any event kind other than `hermes_summary`
- Payout-target mutation
- Inbox message composition

## Data Models

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str           # Unique Hermes agent identifier
    principal_id: str        # Shared PrincipalId (UUID v4)
    capabilities: list[str]  # ['observe', 'summarize']
    connected_at: str        # ISO 8601
```

### Hermes-Readable Events

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,    # Its own summaries
    EventKind.MINER_ALERT,       # Alerts it may have generated
    EventKind.CONTROL_RECEIPT,   # Recent control actions for context
]
```

`EventKind.USER_MESSAGE` is explicitly excluded per the adapter contract.

### Authority Model (M1 Simplified)

M1 uses pairing-based auth. Hermes is paired via `POST /hermes/pair`, which creates a store record with `observe` and `summarize` capabilities. Subsequent requests authenticate via the `Authorization: Hermes <hermes_id>` header, looked up against the pairing store.

Full authority tokens with embedded claims (principal_id, capabilities, expiration) are deferred to M2 when internet-facing access requires signed tokens.

**M1 trust assumption:** LAN-only network. Any process on the local network can reach the daemon. The adapter boundary is a logical enforcement layer, not a cryptographic one.

## Interfaces

### New HTTP Endpoints (in daemon.py)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None (bootstrap) | Create Hermes pairing |
| `/hermes/status` | GET | Hermes | Read miner status |
| `/hermes/summary` | POST | Hermes | Append summary to spine |
| `/hermes/events` | GET | Hermes | Read filtered events |

### New Module: `services/home-miner-daemon/hermes.py`

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

def connect(hermes_id: str) -> HermesConnection
def read_status(connection: HermesConnection) -> dict
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: list) -> None
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list
```

Note: `authority_scope` is `list` (not `str`) to match `spine.append_hermes_summary()` signature.

### New Test File: `services/home-miner-daemon/tests/test_hermes.py`

8 tests covering: valid connect, expired token, read status, append summary, no control, event filter, invalid capability, summary-in-inbox visibility.

## Event Spine Integration

Hermes writes use `spine.append_hermes_summary()` which produces:
```json
{
  "id": "<uuid>",
  "principal_id": "<principal_uuid>",
  "kind": "hermes_summary",
  "payload": {
    "summary_text": "...",
    "authority_scope": ["observe"],
    "generated_at": "2026-03-22T..."
  },
  "created_at": "2026-03-22T...",
  "version": 1
}
```

Hermes reads use `spine.get_events()` filtered to `HERMES_READABLE_EVENTS`.

## Security Boundaries (M1)

| Boundary | Enforcement | Bypass Risk |
|----------|------------|-------------|
| No control commands | Adapter capability check | HIGH: daemon endpoints have no auth; direct HTTP bypasses adapter |
| No user_message reads | Adapter event filter | LOW: only bypassed by direct spine file access |
| Hermes identity | Header-based lookup | MEDIUM: any LAN client can spoof the header |
| Token expiration | Store-based TTL check | LOW: pairing token now has 24h TTL |

**Critical M1 limitation:** The daemon HTTP layer has no authentication middleware. Hermes capability restrictions are enforced only by the adapter module's Python code, not at the HTTP routing level. A Hermes agent (or any LAN client) can call `/miner/start` directly without going through the adapter. This is acceptable for M1 LAN-only but must be addressed before any network-facing deployment.

## Dependencies

- `spine.py` — EventKind enum, append_event, get_events, append_hermes_summary
- `store.py` — load_or_create_principal, pair_client, get_pairing_by_device, has_capability
- `daemon.py` — MinerSimulator.get_snapshot(), route registration

No external dependencies.

## Acceptance Criteria

1. `hermes.py` module importable with `HERMES_CAPABILITIES` and `HERMES_READABLE_EVENTS`
2. Hermes can pair via `POST /hermes/pair`
3. Hermes can read status via `GET /hermes/status` with observe capability
4. Hermes can append summary via `POST /hermes/summary` with summarize capability
5. `GET /hermes/events` returns only `hermes_summary`, `miner_alert`, `control_receipt`
6. `POST /miner/start` with Hermes auth returns 403
7. All 8 tests pass
8. `scripts/hermes_summary_smoke.sh` passes against live daemon

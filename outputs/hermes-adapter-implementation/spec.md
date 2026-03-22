# Hermes Adapter Implementation — Specification

**Status:** Pre-implementation (infrastructure ready, adapter not yet built)
**Generated:** 2026-03-22

## Overview

The Hermes adapter is a capability boundary module that sits between an external AI agent (Hermes) and the Zend gateway contract. It enforces a narrower authority scope than human clients: observe-only status reads and summary-only spine writes. No control commands, no user message access.

## Scope

- `hermes.py` adapter module in `services/home-miner-daemon/`
- Hermes-specific HTTP endpoints in `daemon.py`
- Event filtering (Hermes cannot read `user_message` events)
- Authority token validation with expiration enforcement
- Hermes pairing endpoint (idempotent, observe+summarize only)

## Architecture

```
Hermes Gateway (external agent)
      |
      v  HTTP with Authorization: Hermes <hermes_id>
[hermes.py adapter]  ← THIS MODULE
      |
      v  in-process calls
daemon.py + spine.py + store.py (existing infrastructure)
      |
      v
Event spine (append-only JSONL at state/event-spine.jsonl)
```

The adapter is in-process, not a separate service. It enforces scope by filtering requests before they reach the gateway contract internals.

## Capability Model

```
Gateway capabilities: observe | control
Hermes capabilities:  observe | summarize
```

These are independent namespaces stored in the same pairing store but with different trust models. A Hermes principal with `observe` cannot inherit gateway `control`. The adapter enforces this separation.

### Hermes-Readable Event Kinds

| Event Kind | Readable | Writable |
|------------|----------|----------|
| `hermes_summary` | yes | yes |
| `miner_alert` | yes | no |
| `control_receipt` | yes | no |
| `user_message` | **no** | no |
| `pairing_requested` | no | no |
| `pairing_granted` | no | no |
| `capability_revoked` | no | no |

## Data Models

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]  # ['observe', 'summarize']
    connected_at: str         # ISO 8601
```

### Authority Token

The authority token is the pairing record's UUID token, issued during `POST /hermes/pair`. It encodes no claims directly — claims are resolved by looking up the pairing record in the store. Token expiration is enforced via `is_token_expired()`.

## Interfaces

### New Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | none (LAN-only) | Create Hermes pairing with observe+summarize |
| `/hermes/connect` | POST | authority token | Validate token, return connection status |
| `/hermes/status` | GET | `Authorization: Hermes <id>` | Read miner snapshot via adapter |
| `/hermes/summary` | POST | `Authorization: Hermes <id>` | Append summary to event spine |
| `/hermes/events` | GET | `Authorization: Hermes <id>` | Read filtered events (no user_message) |

### Adapter Module Functions

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

def connect(authority_token: str) -> HermesConnection
def read_status(connection: HermesConnection) -> dict
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> None
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list
```

## Security Boundaries

### Enforced by Adapter

1. **Capability check on every operation** — `observe` required for reads, `summarize` required for writes
2. **Event filtering** — `user_message` events stripped from all Hermes reads
3. **Token expiration** — expired tokens rejected at `connect()`
4. **No control passthrough** — Hermes requests to `/miner/start`, `/miner/stop`, `/miner/set_mode` return 403

### LAN-Only Assumption (M1)

The `Authorization: Hermes <hermes_id>` scheme uses the hermes_id as the sole credential. This is acceptable for milestone 1 where the daemon binds to `127.0.0.1` (or LAN interface). For internet-facing deployments, this must be upgraded to a signed token scheme.

## Dependencies

### Existing Infrastructure (Ready)

| Module | Status | What it provides |
|--------|--------|-----------------|
| `spine.py` | Ready | `EventKind.HERMES_SUMMARY`, `append_hermes_summary()`, `get_events()` |
| `store.py` | Ready (fixed) | `pair_client()` (idempotent), `is_token_expired()`, `get_pairing_by_device()` |
| `daemon.py` | Ready | HTTP server, `MinerSimulator.get_snapshot()` |

### Source Fixes Applied

1. `store.py:create_pairing_token()` — token expiration changed from `datetime.now()` (instant expiry) to `now + 24h`
2. `store.py:is_token_expired()` — new function, referenced by plan but was missing
3. `store.py:pair_client()` — made idempotent for re-pairing (refreshes token/capabilities instead of raising)

## Out of Scope (Milestone 1)

- Direct miner control from Hermes
- Payout-target mutation
- Inbox message composition
- Cryptographic token signing
- Internet-facing auth
- Hermes disconnect/heartbeat lifecycle

# Hermes Adapter Implementation — Specification

**Status:** Pre-implementation review complete
**Generated:** 2026-03-22
**Lane:** hermes-adapter-implementation
**Depends on:** Home Command Center (complete), Token Auth (plan 006), Observability (plan 007)

## Overview

The Hermes adapter is a Python module inside the home-miner daemon that enforces a capability boundary between an external AI agent (Hermes) and the Zend gateway contract. It is not a separate service. It validates authority tokens, checks capabilities, filters events, and delegates to existing spine and daemon primitives.

After this slice lands, a contributor can: pair a Hermes agent, read miner status through the adapter, append a summary to the event spine, observe that user_message events are filtered from Hermes reads, and verify that control commands are rejected with 403.

## Architecture

```
Hermes Gateway (external agent)
      |
      | Authorization: Hermes <hermes_id>
      v
Zend Hermes Adapter (services/home-miner-daemon/hermes.py)
      |
      | capability check + event filter
      v
Zend Gateway Contract (daemon.py, spine.py, store.py)
      |
      v
Event Spine (state/event-spine.jsonl)
```

The adapter runs in-process with the daemon. Boundary enforcement is code-level, not process-level. This is acceptable for milestone 1 (LAN-only) but must be revisited before any remote access is enabled.

## Capability Model

Hermes capabilities are independent from gateway capabilities:

| Capability | Hermes | Gateway |
|------------|--------|---------|
| `observe` | Read miner status | Read miner status |
| `summarize` | Append to event spine | N/A |
| `control` | **DENIED** | Start/stop/set_mode |

Hermes capabilities are `['observe', 'summarize']`. These must be validated at pairing time — `pair_client()` must reject capability lists that include `control` when the pairing is for a Hermes agent.

## Data Model

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

The authority token is the pairing record's token field, looked up by `hermes_id` (which maps to `device_name` in the store). The token encodes:
- Principal ID (from store)
- Granted capabilities (from pairing record)
- Expiration time (from `token_expires_at`)

Token validation requires: record exists, token not expired (`is_token_expired()`), capabilities match Hermes-allowed set.

### Event Filtering

Hermes can read these event kinds (allowlist):
- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may act on
- `control_receipt` — recent control actions for context

Hermes cannot read:
- `user_message` — private user communications
- `pairing_requested` / `pairing_granted` — trust ceremony details
- `capability_revoked` — device trust state

## Interfaces

### New File: `services/home-miner-daemon/hermes.py`

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [EventKind.HERMES_SUMMARY, EventKind.MINER_ALERT, EventKind.CONTROL_RECEIPT]

def connect(authority_token: str) -> HermesConnection
def read_status(connection: HermesConnection) -> dict
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> None
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list
```

### New Daemon Endpoints (in `daemon.py`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None (local) | Create Hermes pairing with observe+summarize |
| `/hermes/connect` | POST | Hermes token | Validate token, return connection state |
| `/hermes/status` | GET | Hermes header | Read miner status through adapter |
| `/hermes/summary` | POST | Hermes header | Append summary to spine |
| `/hermes/events` | GET | Hermes header | Read filtered events |

Auth scheme: `Authorization: Hermes <hermes_id>` header. The hermes_id maps to device_name in the pairing store.

### Store Dependencies

From `store.py` (existing + fixed):
- `pair_client(device_name, capabilities)` — create pairing
- `get_pairing_by_device(device_name)` — lookup by hermes_id
- `is_token_expired(pairing)` — check expiration (added by this review)
- `has_capability(device_name, capability)` — check capability

## Boundaries (Non-Negotiable)

1. Hermes CANNOT call `/miner/start`, `/miner/stop`, `/miner/set_mode` — 403 HERMES_UNAUTHORIZED
2. Hermes CANNOT read `user_message` events — filtered from all read paths
3. Hermes CANNOT be paired with `control` capability — rejected at pairing time
4. Hermes CANNOT mutate payout targets — no endpoint exists, but must be explicitly blocked if added
5. Hermes CANNOT compose inbox messages — no write path except `hermes_summary`

## Acceptance Criteria

1. `hermes.py` importable with `HERMES_CAPABILITIES` and `HERMES_READABLE_EVENTS` constants
2. `connect()` validates token, rejects expired/invalid tokens with `ValueError`
3. `read_status()` returns miner snapshot when `observe` capability present
4. `append_summary()` writes `HERMES_SUMMARY` event to spine
5. `get_filtered_events()` returns only allowlisted event kinds
6. `POST /hermes/pair` creates pairing with `['observe', 'summarize']`
7. `POST /hermes/summary` appends summary through adapter
8. `GET /hermes/events` returns filtered events (no `user_message`)
9. Control endpoints return 403 for Hermes auth headers
10. All 8+ tests pass in `test_hermes.py`

## Known Limitations (Milestone 1)

- Token is opaque UUID lookup, not a signed JWT — no cryptographic binding between token and claims
- Boundary enforcement is code-level in same process — no process isolation
- `get_filtered_events()` over-fetch strategy may return fewer than `limit` results if most events are filtered
- No token rotation or refresh mechanism
- Pairing idempotence requires handling duplicate device_name (current `pair_client` rejects duplicates)

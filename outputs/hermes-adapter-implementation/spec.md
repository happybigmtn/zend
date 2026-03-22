# Hermes Adapter Implementation — Specification

**Lane:** `hermes-adapter-implementation`
**Status:** ✅ Milestone 1 Complete
**Generated:** 2026-03-22

## Purpose

Enables an AI agent (Hermes) to connect to the Zend daemon through a scoped adapter with restricted capabilities. The adapter enforces a hard boundary: Hermes agents can observe miner state and write summaries, but cannot issue control commands or read user messages.

## Architecture

```
Hermes Gateway → hermes.py adapter → daemon HTTP layer → event spine
                 ↑
                 capability boundary enforced here
```

The adapter is a Python module embedded in `services/home-miner-daemon/`. It is not a separate service or deployment boundary — it is a code-level capability filter applied before any request reaches the gateway contract or miner backend.

## Scope

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module: token validation, capability checks, event filtering |
| `services/home-miner-daemon/tests/test_hermes.py` | 17 tests covering all boundary enforcement cases |
| `services/home-miner-daemon/daemon.py` | Hermes HTTP endpoints: `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`; control command blocking |
| `services/home-miner-daemon/cli.py` | Hermes CLI subcommands: `hermes pair`, `hermes connect`, `hermes status`, `hermes summary`, `hermes events` |

## Data Models

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]   # ['observe', 'summarize']
    connected_at: str       # ISO-8601 UTC
    authority_token: str      # raw JSON token

@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
```

## Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

`user_message` events are **not** in `HERMES_READABLE_EVENTS` and are filtered out.

## Adapter API

| Function | Description | Raises |
|----------|-------------|--------|
| `pair_hermes(hermes_id, device_name)` | Create or update a pairing record; writes `hermes-store.json` | — |
| `generate_authority_token(hermes_id, capabilities)` | Produce a self-contained JSON token with 24h expiry | — |
| `connect(authority_token)` | Validate token (expiry, hermes_id, capabilities) and return `HermesConnection` | `ValueError` |
| `read_status(connection)` | Return filtered miner snapshot | `PermissionError` if no `observe` |
| `append_summary(connection, text, scope)` | Append `hermes_summary` event to spine | `PermissionError` if no `summarize` |
| `get_filtered_events(connection, limit)` | Return events from `HERMES_READABLE_EVENTS` only | `PermissionError` if no `observe` |
| `check_control_denied(connection)` | Return whether control is blocked | — |

## HTTP Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create/update pairing; returns token |
| `/hermes/connect` | POST | Token | Validate token; return connection info |
| `/hermes/status` | GET | Hermes | `read_status` |
| `/hermes/summary` | POST | Hermes | `append_summary` |
| `/hermes/events` | GET | Hermes | `get_filtered_events` |

Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) return `403 HERMES_UNAUTHORIZED` when the `Authorization` header starts with `Hermes `.

## Token Format

Authority tokens are self-contained JSON (no session DB required):

```json
{
  "hermes_id": "agent-001",
  "capabilities": ["observe", "summarize"],
  "issued_at": "2026-03-22T10:00:00+00:00",
  "expires_at": "2026-03-23T10:00:00+00:00"
}
```

## Error Codes

| Code | Condition |
|------|-----------|
| `unauthorized` (401) | Missing or invalid token |
| `missing_hermes_id` (400) | Pairing request without `hermes_id` |
| `missing_authority_token` (400) | Connect request without token |
| `missing_summary_text` (400) | Summary request without text |
| `HERMES_UNAUTHORIZED` (403) | Missing required capability or control attempt |

## Security Boundaries

**Hermes CAN:**
- Read miner status (requires `observe`)
- Append `hermes_summary` events to spine (requires `summarize`)
- Read filtered events: `hermes_summary`, `miner_alert`, `control_receipt`

**Hermes CANNOT:**
- Issue miner control commands (`start`, `stop`, `set_mode`)
- Read `user_message` events
- Hold `control` capability — rejected at token validation

## State Files

| File | Location | Purpose |
|------|----------|---------|
| `hermes-store.json` | `state/` | Hermes pairing records |
| `event-spine.jsonl` | `state/` | Event journal; Hermes summaries written here |

## Out of Scope (Deferred)

- Hermes control capability
- Hermes inbox / direct messaging
- Token refresh mechanism for long-running sessions
- Multi-Hermes multi-tenancy
- Gateway client Agent tab integration

## Acceptance Criteria

- [x] `hermes pair` creates a pairing record and returns an authority token
- [x] `hermes connect` validates token and returns `HermesConnection`
- [x] `hermes status` returns miner snapshot with `source: hermes_adapter`
- [x] `hermes summary` appends `hermes_summary` event to spine
- [x] `hermes events` excludes `user_message` events
- [x] `/miner/start`, `/miner/stop`, `/miner/set_mode` return `403 HERMES_UNAUTHORIZED` for Hermes auth
- [x] Invalid capabilities (e.g. `control`) rejected at `connect()`
- [x] Expired tokens rejected at `connect()`
- [x] All 17 tests pass (`pytest tests/test_hermes.py -v`)

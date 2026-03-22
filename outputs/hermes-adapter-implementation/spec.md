# Hermes Adapter Implementation — Specification

## Overview

**Lane:** `hermes-adapter-implementation`
**Status:** Implemented (milestone 1)
**Service:** `services/home-miner-daemon/`
**Entry points:** `hermes.py` (adapter module), `daemon.py` (HTTP endpoints), `cli.py` (CLI subcommands)

This document specifies the implementation of the Hermes adapter module for the Zend Home Miner Daemon. The adapter provides a capability-scoped interface for AI agents (Hermes) to interact with the daemon's event spine and status endpoints.

## Purpose

Enable AI agents to connect to the Zend daemon through a scoped adapter that:
- Allows reading miner status (observe capability)
- Allows appending summaries to the event spine (summarize capability)
- Blocks control commands entirely (no control capability)
- Filters out `user_message` events from event reads

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Home Miner Daemon → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WE BUILD
```

The adapter is a Python module (`hermes.py`) within the daemon service that:
1. Validates authority tokens issued to Hermes principals
2. Enforces capability boundaries (observe + summarize only)
3. Transforms payloads to strip fields Hermes shouldn't see
4. Filters events before returning them

## Module Interface

### `hermes.py`

#### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

#### `HermesConnection` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `hermes_id` | `str` | Unique Hermes instance identifier |
| `principal_id` | `str` | Zend principal this Hermes acts on behalf of |
| `capabilities` | `List[str]` | Granted capabilities (subset of HERMES_CAPABILITIES) |
| `connected_at` | `str` | ISO 8601 timestamp of connection establishment |

#### Public Functions

| Function | Returns | Required Capability | Description |
|----------|---------|---------------------|-------------|
| `connect(authority_token: str)` | `HermesConnection` | — | Validate token, establish connection |
| `get_connection(hermes_id: str)` | `Optional[HermesConnection]` | — | Look up active connection by ID |
| `disconnect(hermes_id: str)` | `bool` | — | Remove connection from in-memory store |
| `read_status(connection: HermesConnection)` | `dict` | `observe` | Get miner status snapshot |
| `append_summary(connection, summary_text, authority_scope)` | `SpineEvent` | `summarize` | Append summary to event spine |
| `get_filtered_events(connection, limit=20)` | `list[SpineEvent]` | `observe` | Read events, filtered to HERMES_READABLE_EVENTS |
| `pair_hermes(hermes_id, device_name)` | `dict` | — | Create/update Hermes pairing record in store |
| `get_hermes_pairing(hermes_id)` | `Optional[dict]` | — | Look up pairing by hermes_id |
| `list_hermes_pairings()` | `list[dict]` | — | List all Hermes pairings |

### Token Validation

Authority tokens are JWT-shaped (three dot-separated base64url segments) containing:

| Field | Type | Description |
|-------|------|-------------|
| `hermes_id` | `str` | Unique identifier for the Hermes instance (required, non-empty) |
| `principal_id` | `str` | Zend principal this Hermes acts on behalf of (required) |
| `capabilities` | `List[str]` | Granted capabilities (must be subset of HERMES_CAPABILITIES) |
| `exp` | `int` | Unix epoch seconds at which the token expires |

Tokens are validated by:
1. Splitting on `.` and verifying three parts exist
2. Base64url-decoding the payload segment
3. Checking `exp` against `time.time()`
4. Verifying every capability in `capabilities` is in `HERMES_CAPABILITIES`
5. Verifying `hermes_id` is non-empty

> **Security note:** JWT signatures are **not** verified in milestone 1. The daemon binds to `127.0.0.1` only. Signature verification is deferred to plan 006 (token auth).

### Error Codes

| Condition | Error Code | HTTP Status |
|-----------|-----------|-------------|
| Malformed token | `HERMES_INVALID_TOKEN` | 401 |
| Expired token | `HERMES_TOKEN_EXPIRED` | 401 |
| Missing capability | `HERMES_UNAUTHORIZED` | 403 |
| Internal error | `HERMES_INTERNAL_ERROR` | 500 |

## Daemon HTTP Endpoints

### `POST /hermes/connect`

Establish a Hermes connection from an authority token.

**Request:**
```json
{ "authority_token": "<jwt_token>" }
```

**Response 200:**
```json
{
  "hermes_id": "hermes-001",
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "capabilities": ["observe", "summarize"],
  "connected_at": "2026-03-22T12:00:00Z"
}
```

### `POST /hermes/pair`

Create or retrieve (idempotent) a Hermes pairing record. Capabilities are hardcoded to `["observe", "summarize"]`. No authentication required (localhost-only binding for milestone 1).

**Request:**
```json
{ "hermes_id": "hermes-001", "device_name": "hermes-agent" }
```

**Response 200:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent",
  "capabilities": ["observe", "summarize"],
  "paired_at": "2026-03-22T12:00:00Z",
  "principal_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### `GET /hermes/status`

Read miner status through adapter. Requires `Authorization: Hermes <hermes_id>` header.

**Response 200:**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00Z"
}
```

> **Known issue:** `MinerStatus` enum values serialize as `"MinerStatus.STOPPED"` (Python repr) rather than `"stopped"` on Python 3.15. Pre-existing in `MinerSimulator.get_snapshot()`; needs `.value` fix separately.

### `POST /hermes/summary`

Append a Hermes summary to the event spine. Requires `Authorization: Hermes <hermes_id>` header.

**Request:**
```json
{ "summary_text": "Miner running normally at 50kH/s", "authority_scope": "observe" }
```

**Response 200:**
```json
{ "appended": true, "event_id": "evt_abc123", "created_at": "2026-03-22T12:00:00Z" }
```

### `GET /hermes/events`

Read filtered events (user_message events excluded). Requires `Authorization: Hermes <hermes_id>` header.

**Query params:** `limit` (int, default 20)

**Response 200:**
```json
{
  "events": [
    {
      "id": "evt_abc123",
      "kind": "hermes_summary",
      "payload": {"summary_text": "...", "authority_scope": "observe"},
      "created_at": "2026-03-22T12:00:00Z"
    }
  ],
  "count": 1
}
```

### Control Endpoints (Hermes-blocked)

`POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode` return 403 when the `Authorization: Hermes <hermes_id>` header is present. This is defense-in-depth; Hermes connections cannot hold `control` capability so the adapter itself would reject any control-level call.

## CLI Subcommands

All subcommands live under `python -m cli hermes`.

| Subcommand | Description |
|------------|-------------|
| `connect --hermes-id <id> --token <jwt>` | Connect with authority token |
| `connect --hermes-id <id> --generate-token` | Generate a test token (dev/demo only) |
| `pair --hermes-id <id> --device-name <name>` | Pair a Hermes agent |
| `status --hermes-id <id>` | Read miner status via adapter |
| `summary --hermes-id <id> --text <text> --scope <scope>` | Append summary to spine |
| `events --hermes-id <id> [--limit <n>]` | Read filtered events |

## Data Flow

### Connect → Read Status

1. `POST /hermes/connect` with authority token
2. Adapter decodes JWT payload, checks expiry and capabilities
3. Adapter stores `HermesConnection` in `_hermes_connections` dict (in-memory)
4. `GET /hermes/status` with `Authorization: Hermes <hermes_id>` header
5. Adapter resolves connection, checks `observe` capability
6. Adapter delegates to `miner.get_snapshot()`
7. Returns status dict

### Connect → Append Summary

1. `GET /hermes/status` with `Authorization: Hermes <hermes_id>` header
2. Adapter resolves connection, checks `summarize` capability
3. Adapter calls `spine.append_event(EventKind.HERMES_SUMMARY, ...)`
4. Event includes `hermes_id` for attribution
5. Returns event info

### Connect → Read Filtered Events

1. `GET /hermes/events?limit=20` with `Authorization: Hermes <hermes_id>` header
2. Adapter fetches `limit * 2` events from spine (over-fetch strategy)
3. Filters to `HERMES_READABLE_EVENTS` (excludes `user_message`)
4. Returns first `limit` filtered events

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Hermes can connect with a valid authority token | ✅ |
| 2 | Hermes can read miner status via GET /hermes/status | ✅ |
| 3 | Hermes can append summaries via POST /hermes/summary | ✅ |
| 4 | Hermes CANNOT issue control commands (403 response) | ✅ |
| 5 | Hermes CANNOT read user_message events (filtered) | ✅ |
| 6 | All 5 daemon endpoints return appropriate status codes | ✅ |
| 7 | Token expiration is enforced | ✅ |
| 8 | Invalid tokens return 401 | ✅ |
| 9 | Missing capabilities return 403 | ✅ |
| 10 | CLI commands work against live daemon | ✅ (fixed during review) |

## Security Boundaries

The adapter enforces these hard boundaries:
- **No control capability** — never granted to Hermes, checked on every call
- **No user_message exposure** — filtered out of all event reads
- **Token expiration enforced** — no `exp` field or past `exp` causes rejection
- **Capability subset enforcement** — tokens with non-Hermes capabilities are rejected

**Not enforced in milestone 1 (deferred):**
- JWT signature verification (plan 006 — token auth)
- `/hermes/pair` authentication (localhost-only binding is the safeguard)
- `authority_scope` validation against granted capabilities
- Input bounds on `summary_text` (length limits)

## Dependencies

- `spine.py`: Event spine operations (EventKind enum, `append_event`, `get_events`)
- `store.py`: Pairing storage (`load_pairings`, `save_pairings`, `load_or_create_principal`)
- `daemon.py`: HTTP server (`miner.get_snapshot()`, endpoint routing)
- Python standard library: `json`, `base64`, `time`, `dataclasses`, `datetime`

No external dependencies required.

## File Inventory

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module (+337 lines) |
| `services/home-miner-daemon/daemon.py` | Daemon HTTP endpoints (+198/-16 lines) |
| `services/home-miner-daemon/cli.py` | CLI hermes subcommands (+136 lines) |
| `services/home-miner-daemon/spine.py` | Event spine (pre-existing) |
| `services/home-miner-daemon/store.py` | Pairing/principal store (pre-existing) |
| `outputs/hermes-adapter-implementation/spec.md` | This specification |
| `outputs/hermes-adapter-implementation/review.md` | Honest review |

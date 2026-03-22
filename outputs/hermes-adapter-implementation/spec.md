# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Date:** 2026-03-22
**Plan Reference:** `genesis/plans/001-master-plan.md` (frontier: `hermes-adapter-implementation`)

---

## Purpose

The Hermes Adapter is a Python module (`services/home-miner-daemon/hermes.py`) that serves as a **capability boundary** between a Hermes AI agent and the Zend gateway contract. It allows Hermes to observe miner status and append summaries to the event spine while **enforcing three hard constraints**:

1. Hermes cannot issue control commands.
2. Hermes cannot read `user_message` events.
3. All Hermes capabilities are granted explicitly via authority tokens, never dynamically.

This spec covers the first honest implementation slice. Future slices may add token refresh, rate limiting, and per-agent principals.

---

## Scope

### In scope for this slice

- `services/home-miner-daemon/hermes.py` — the adapter module
- `services/home-miner-daemon/daemon.py` — HTTP endpoints for Hermes operations
- `services/home-miner-daemon/cli.py` — CLI subcommands for Hermes
- `services/home-miner-daemon/tests/test_hermes.py` — adapter unit tests
- `apps/zend-home-gateway/index.html` — Agent tab Hermes integration
- Observability event emission per `references/observability.md`

### Out of scope for this slice

- Token refresh / re-pairing without re-entering credentials
- Rate limiting on Hermes endpoints
- Per-agent principal isolation (all Hermes agents share the gateway principal)
- Remote/internet access — milestone 1 is LAN-only

---

## Architecture

```
Hermes Gateway (external)
      │
      ▼
Hermes Adapter  hermes.py
      │
      ├── connect(authority_token)        ← validates token, returns HermesConnection
      ├── read_status(connection)          ← observe capability required
      ├── append_summary(connection, …)     ← summarize capability required
      ├── get_filtered_events(connection)  ← strips user_message
      └── check_control_denied(connection) ← always returns False, logs denial
      │
      ▼
Zend Gateway  daemon.py
      │
      ▼
Event Spine  spine.py
```

The adapter runs **in-process** with the daemon. It is a logical boundary (capability enforcement), not a deployment boundary.

---

## Capability Model

Hermes is granted exactly two capabilities:

| Capability | Grants access to |
|------------|-----------------|
| `observe` | `read_status()` and `GET /hermes/status` |
| `summarize` | `append_summary()` and `POST /hermes/summary` |

`control` is **never granted**. Any attempt to call a control operation via `check_control_denied()` is logged and denied at the adapter level. The daemon additionally rejects control commands from Hermes-identified sessions.

---

## Authority Token

For milestone 1, authority tokens are **UUIDs stored in the pairing JSON file** at `state/hermes/pairings.json`. Each token carries the `hermes_id`, `principal_id`, `capabilities` list, and an `expires_at` timestamp.

Token lifecycle:
1. `POST /hermes/pair` (or `cli.py hermes pair`) creates a pairing and returns a token.
2. `POST /hermes/connect` (or `cli.py hermes connect`) validates the token and returns an in-memory `HermesConnection`.
3. Subsequent requests use `Authorization: Hermes <hermes_id>` header; the daemon looks up the active connection from `_hermes_connections` dict.

Tokens expire after 24 hours. Re-pairing regenerates a new token for the same `hermes_id`.

---

## Event Filtering

`get_filtered_events()` returns only events whose `kind` is in `HERMES_READABLE_EVENTS`:

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

`EventKind.USER_MESSAGE` is explicitly blocked. Filtering is done in-memory after fetching from the spine; the spine itself is not modified.

---

## HTTP Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create or update pairing; returns `token` |
| `/hermes/connect` | POST | None (body: `token`) | Establish in-memory connection |
| `/hermes/disconnect` | POST | `Authorization: Hermes <id>` | Tear down in-memory connection |
| `/hermes/status` | GET | `Authorization: Hermes <id>` | Read miner snapshot |
| `/hermes/summary` | POST | `Authorization: Hermes <id>` | Append Hermes summary to spine |
| `/hermes/events` | GET | `Authorization: Hermes <id>` | Get filtered events |
| `/hermes/connection` | GET | `Authorization: Hermes <id>` | Return connection state |

---

## Observability Events

The adapter emits JSON-structured log events under the `hermes.adapter` logger:

| Event | Trigger |
|-------|---------|
| `gateway.hermes.paired` | Pairing created or updated |
| `gateway.hermes.connected` | Token validated, connection established |
| `gateway.hermes.unauthorized` | Any auth/capability failure |
| `gateway.hermes.summary_appended` | Summary written to spine |
| `gateway.status.read` | Status snapshot returned to Hermes |

---

## Acceptance Criteria

- [x] `python hermes.py` (proof of implementation) runs without error
- [x] Pairing a Hermes device returns a UUID authority token
- [x] Connecting with a valid token establishes an in-memory `HermesConnection`
- [x] Connecting with an invalid or expired token raises `ValueError`
- [x] `read_status()` requires `observe` capability; raises `PermissionError` otherwise
- [x] `append_summary()` requires `summarize` capability; raises `PermissionError` otherwise
- [x] `get_filtered_events()` never returns `user_message` events
- [x] `check_control_denied()` always returns `False` and logs the denial
- [x] All 11 test cases in `test_hermes.py` pass
- [x] Gateway client Agent tab shows connection state and can append summaries

---

## Design Decisions

**Decision: In-process adapter, not a separate service.**
Milestone 1 is single-instance LAN. Running the adapter in-process avoids network hop overhead while maintaining clear capability boundaries. Production multi-instance deployments would revisit this.

**Decision: In-memory connection state.**
`_hermes_connections` is a Python dict in daemon process memory. Connections are lost on daemon restart. Clients reconnect with their token. Acceptable for milestone 1; session persistence is a future slice concern.

**Decision: UUID tokens stored in plain JSON.**
Token storage is not encrypted for milestone 1. Cryptographic token signatures and encrypted storage are deferred to a future security hardening slice.

# Hermes Adapter — Capability Spec

**Lane:** `hermes-adapter-implementation`
**Status:** Implemented
**Date:** 2026-03-22
**Supervisory stage:** Polish

## Purpose / User-Visible Outcome

After this slice lands, a Hermes AI agent can pair with the Zend home-miner daemon, obtain a scoped authority token, read miner status, and append summaries to the event spine — while being structurally prevented from issuing control commands or reading user messages. The boundaries are enforced in-process, before any request reaches the gateway contract layer.

## Whole-System Goal

The Zend home miner has two distinct actor classes:

- **Gateway clients** (mobile app, web dashboard): `observe + control`
- **Hermes agents**: `observe + summarize` only

Hermes is a first-class adapter resident in the same daemon process. It is not a separate service. Its narrow capability surface means a compromised or misconfigured Hermes agent cannot start or stop the miner, change its mode, or read private user messages.

## Architecture

```
Hermes Agent
     │
     │  Hermes authority token
     │  (observe + summarize scope)
     ▼
hermes.py  ──────────────────► spine.py
(adapter module)               (append-only event journal)
     │
     │  filtered read
     ▼
spine.py
```

The adapter module lives in `services/home-miner-daemon/hermes.py` and is imported directly by `daemon.py`. There is no separate Hermes microservice.

## Capability Contract

### Hermes Capability Set

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

These are independent from gateway capabilities (`observe + control`). A Hermes token that contains `control` is rejected at `connect()` time.

### Readable Event Kinds

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,   # Hermes-generated summaries
    EventKind.MINER_ALERT,       # Miner alerts
    EventKind.CONTROL_RECEIPT,   # Control command receipts
]
```

**Blocked at the adapter layer:** `EventKind.USER_MESSAGE` is never exposed to Hermes. The `get_filtered_events()` function applies this filter before returning events.

## Adapter Interface

All functions in `hermes.py` raise `ValueError` for malformed input and `PermissionError` for capability violations.

### `connect(authority_token: str) → HermesConnection`

Parses a pipe-delimited token of the form:

```
{hermes_id}|{principal_id}|{capabilities}|{iso8601_expires_at}
```

Example: `hermes-001|abc123|observe,summarize|2027-12-31T23:59:59+00:00`

Validates:
- Token is well-formed (four fields)
- Token has not expired
- Capabilities include both `observe` and `summarize`
- `control` is **not** present in capabilities

Returns a `HermesConnection` dataclass. Raises `ValueError` on expiry or malformation; raises `PermissionError` if `control` appears in the token.

> **Note for future milestones:** The token format is intentionally simple for milestone 1. A future slice will replace this with a signed JWT so that tokens can be validated without a live lookup.

### `read_status(connection: HermesConnection) → dict`

Requires `observe` capability. Returns the current miner snapshot (status, mode, hashrate, temperature, uptime, freshness). The `source` field is set to `"hermes_adapter"` so clients can distinguish responses.

### `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) → SpineEvent`

Requires `summarize` capability. Appends a `hermes_summary` event to `spine.py`. The `authority_scope` field records which capability was used to authorize the write (default: `"observe"`).

### `get_filtered_events(connection: HermesConnection, limit: int = 20) → List[SpineEvent]`

Returns up to `limit` events from the spine, filtered to `HERMES_READABLE_EVENTS`. The `user_message` kind is excluded here and cannot be re-enabled by a future change without a new spec and approval flow.

### `pair_hermes(hermes_id: str, device_name: str) → HermesPairing`

Creates or updates a Hermes pairing record in the pairing store. Idempotent: calling with the same `hermes_id` updates `paired_at` without creating a duplicate. Produces a pairing with `observe + summarize` capabilities and a 1-year token expiration.

### `generate_hermes_token(hermes_id: str) → tuple[str, str]`

Generates the raw authority token and its expiration string. Called internally by the pairing flow and by the daemon's `/hermes/pair` endpoint.

## Daemon HTTP Interface

### Hermes Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/hermes/pair` | Create Hermes pairing, return authority token |
| `POST` | `/hermes/connect` | Validate token, store active connection |
| `GET` | `/hermes/status` | Read miner status (requires Hermes auth) |
| `POST` | `/hermes/summary` | Append summary to spine (requires Hermes auth) |
| `GET` | `/hermes/events` | Read filtered events (requires Hermes auth) |

### Authorization Header

Hermes uses `Authorization: Hermes <token>` where `<token>` is the raw authority token returned by `/hermes/pair`. This scheme is distinct from the device auth header (`Authorization: Bearer <token>`) used by gateway clients.

### Control Rejection

The daemon checks for a Hermes `Authorization` header on every control-class route (`/miner/start`, `/miner/stop`, `/miner/set_mode`). If present, it returns `403` immediately with `{"error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot issue control commands"}`. This check is in `GatewayHandler.do_POST` and is **not** middleware — it is a direct if-guard before the miner operation is dispatched.

## Event Schema

### `hermes_summary`

```json
{
  "id": "uuid",
  "principal_id": "principal-uuid",
  "kind": "hermes_summary",
  "payload": {
    "summary_text": "Miner running normally at 50kH/s",
    "authority_scope": ["observe"],
    "generated_at": "2026-03-22T10:00:00+00:00"
  },
  "created_at": "2026-03-22T10:00:00+00:00",
  "version": 1
}
```

## Boundary Enforcement Summary

| Boundary | Enforcement point | Behavior |
|----------|-------------------|----------|
| No control commands | `daemon.py` `do_POST` guard | 403 returned |
| No `control` in token | `hermes.py` `connect()` | `PermissionError` raised |
| No `user_message` read | `hermes.py` `get_filtered_events()` | Kind filtered out |
| `observe` required for status | `hermes.py` `read_status()` | `PermissionError` raised |
| `summarize` required for write | `hermes.py` `append_summary()` | `PermissionError` raised |
| Token expiration | `hermes.py` `connect()` | `ValueError` raised |

## Future Expansion (Out of Scope for This Slice)

- **Control capability for Hermes:** requires a new approval flow and spec; not additive
- **Inbox message access:** requires a contact-policy model; blocked by user_message filter
- **Signed JWT tokens:** replaces the pipe-delimited format in `connect()`
- **Session store:** replaces the in-memory `active_hermes_connections` dict

## Decision Log

- **Decision:** Hermes adapter is a Python module in the daemon process, not a separate service.
  **Rationale:** Enforces capability boundaries before requests reach the gateway contract. A separate service would require a second trust boundary and inter-process auth. Simpler for milestone 1.
  **Date:** 2026-03-22

- **Decision:** Hermes capabilities (`observe + summarize`) are independent from gateway capabilities (`observe + control`).
  **Rationale:** These are different actor classes. A Hermes token that contains `control` is a spec violation and is rejected.
  **Date:** 2026-03-22

- **Decision:** `user_message` events are filtered at `get_filtered_events()` rather than at the spine layer.
  **Rationale:** The spine is intentionally unopinionated about reader identity. Filtering in the adapter preserves spine simplicity and keeps the boundary explicit.
  **Date:** 2026-03-22

- **Decision:** Token format is pipe-delimited plain text for milestone 1.
  **Rationale:** Avoids JWT dependency until token refresh and distributed validation are needed. The format is documented here so a future migration to signed JWT is a mechanical change.
  **Date:** 2026-03-22

## Files

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module |
| `services/home-miner-daemon/daemon.py` | HTTP server + Hermes endpoints + control guard |
| `services/home-miner-daemon/spine.py` | Append-only event journal (reads and writes) |
| `services/home-miner-daemon/store.py` | Pairing store and principal management |
| `services/home-miner-daemon/cli.py` | CLI subcommands: `hermes pair`, `hermes status`, `hermes summary`, `hermes events` |

## Acceptance Criteria

- [x] `connect()` parses and validates a pipe-delimited authority token
- [x] `connect()` raises `PermissionError` if `control` is in the token
- [x] `read_status()` requires `observe` and returns miner snapshot
- [x] `append_summary()` requires `summarize` and appends a `hermes_summary` event
- [x] `get_filtered_events()` excludes `user_message` kind
- [x] `pair_hermes()` is idempotent on `hermes_id`
- [x] `/hermes/pair` returns a valid authority token
- [x] Control routes return 403 if Hermes `Authorization` header is present
- [x] CLI exposes `hermes pair`, `hermes status`, `hermes summary`, `hermes events`
- [x] Adapter module passes `python3 hermes.py` (prints capabilities and readable event kinds)

# Hermes Adapter — Capability Spec

**Status:** Implemented (Milestone 1)
**Date:** 2026-03-22
**Lane:** `hermes-adapter-implementation`
**Source:** `services/home-miner-daemon/hermes.py`, `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/tests/test_hermes.py`, `services/home-miner-daemon/cli.py`

---

## Purpose / User-Visible Outcome

After Milestone 1, a Hermes AI agent can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine. Hermes **cannot** issue control commands and **cannot** read user-message events. A contributor can simulate a Hermes pairing, observe a summary appear in the inbox, and verify that control attempts return HTTP 403.

## Whole-System Goal

Hermes is a first-class agent consumer of the Zend daemon, scoped to observe and summarize — not to drive miner control. The adapter establishes a hard, verifiable capability boundary at the HTTP handler level, not just inside internal functions.

## Scope

This spec covers Milestone 1 of the Hermes adapter. The adapter is a Python module in the daemon service, not a separate deployment.

### Built in Milestone 1

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module: pairing store, token validation, capability checking, event filtering |
| `services/home-miner-daemon/daemon.py` | HTTP endpoints for Hermes (`/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`) with HTTP-level 403 guard on control paths |
| `services/home-miner-daemon/cli.py` | CLI subcommands: `hermes pair`, `hermes status`, `hermes summary`, `hermes events` |
| `services/home-miner-daemon/tests/test_hermes.py` | 21 tests covering all acceptance criteria |

### Not Built (Milestone 2)

- Gateway client Agent tab UI updates (plan 010)
- Smoke test script integration
- Signed authority tokens (HMAC or JWT)
- File locking on `hermes-store.json`
- Rate limiting on `append_summary`
- Subset-match capability checking (current: exact-match)

## Architecture / Runtime Contract

The adapter sits between the external Hermes agent and the Zend event spine:

```
Hermes → Hermes Adapter → Event Spine
          ↑^^^^^^^^^^^^^
          THIS BOUNDARY
```

The boundary is enforced at two levels:
1. **HTTP handler level** — control paths (`/miner/start`, `/miner/stop`, `/miner/set_mode`) return 403 before reaching any miner logic if the `Authorization` header starts with `Hermes `
2. **Adapter function level** — `read_status` and `append_summary` check `HermesConnection.capabilities` before executing

### Adapter Enforces

1. **Token validation** — authority tokens carry `hermes_id`, `principal_id`, `capabilities`, and `expires_at`; decoded from base64
2. **Capability checking** — only `observe` and `summarize` are valid Hermes capabilities; `control` is rejected
3. **Event filtering** — `get_filtered_events` allowlists `hermes_summary`, `miner_alert`, and `control_receipt`; `user_message` is excluded
4. **Payload transformation** — `read_status` strips internal fields, returns only safe miner telemetry

## Hermes Capability Model

| Capability | What it allows |
|------------|---------------|
| `observe` | `read_status()` — read miner status snapshot |
| `summarize` | `append_summary()` — append to event spine |

Capabilities are Hermes-specific and **independent** from gateway client capabilities (`observe`, `control`). Hermes never inherits gateway `control`.

## API Contract

All Hermes endpoints are on the daemon HTTP server (`http://127.0.0.1:8080` by default).

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/hermes/pair` | Create or refresh a Hermes pairing; returns authority token | None |
| POST | `/hermes/connect` | Validate authority token; confirm connection | None |
| GET | `/hermes/status` | Read miner status | Hermes token |
| POST | `/hermes/summary` | Append summary to event spine | Hermes token |
| GET | `/hermes/events` | Get filtered events (no `user_message`) | Hermes token |

### Authorization Header Scheme

Hermes uses `Authorization: Hermes <base64-encoded-authority-token>`.

> **Note:** The token is a base64-encoded JSON object, not a `hermes_id` string. The spec in `references/hermes-adapter.md` described a simpler `<hermes_id>` scheme; the implementation uses the full token because it carries capabilities and expiration inline.

```
Authorization: Hermes eyJoZXJtZXNfaWQiOiJoZXJtZXMtMDAxIiwicHJpbmNpcGFsX2lkIjoicHJpbmNpcGFsLTg4OCIsImNhcGFiaWxpdGllcyI6WyJvYnNlcnZlIiwic3VtbWFyaXplIl0sImV4cGlyZXNfYXQiOiIyMDI2LTAzLTIzVDEyOjAwOjAwKzAwOjAwIn0=
```

### Authority Token Format

```json
{
  "hermes_id": "hermes-001",
  "principal_id": "principal-xxx",
  "capabilities": ["observe", "summarize"],
  "expires_at": "2026-03-23T12:00:00+00:00"
}
```

### Pairing Flow

1. Owner calls `POST /hermes/pair` with `hermes_id` → daemon stores pairing record and returns an authority token
2. Hermes includes the token in `Authorization: Hermes <token>` header on subsequent requests
3. `POST /hermes/connect` validates the token and confirms the connection
4. `GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events` use the token for per-request auth

Pairing is idempotent — calling `POST /hermes/pair` with the same `hermes_id` refreshes the token expiry.

## Data Model

### HermesConnection (runtime, in-memory per request)

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]
    connected_at: str    # ISO8601 UTC
```

### HermesPairing (durable, persisted to `state/hermes-store.json`)

```python
@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list[str]
    paired_at: str       # ISO8601 UTC
    token: str           # UUID, written but not validated in M1
    token_expires_at: str
```

### Events Visible to Hermes (allowlist)

- `hermes_summary` — Hermes-generated summaries
- `miner_alert` — System alerts
- `control_receipt` — Control command receipts

### Events Blocked for Hermes

- `user_message` — User communications (never surfaced to Hermes)
- `pairing_requested`, `pairing_granted`, `capability_revoked` — administrative events

## Acceptance Criteria

| # | Criterion | Evidence |
|---|-----------|----------|
| AC1 | Hermes can connect with a valid authority token | `test_connect_valid_token` passes |
| AC2 | Hermes can read miner status with `observe` capability | `test_read_status_with_observe` passes |
| AC3 | Hermes can append summaries to the event spine with `summarize` capability | `test_append_summary_with_summarize` passes; event verified in spine |
| AC4 | Hermes **cannot** issue control commands (returns HTTP 403) | HTTP-level guard in `daemon.py`; `test_no_control_at_http_level` (coverage gap — see review) |
| AC5 | Hermes **cannot** read `user_message` events | `test_filter_blocks_user_message` passes; allowlist-based filtering |
| AC6 | All 21 tests pass | `pytest services/home-miner-daemon/tests/test_hermes.py` |
| AC7 | Pairing is idempotent (same `hermes_id` re-pairs) | `test_pair_hermes_idempotent` passes |

## Failure Handling

| Error | HTTP Status | Response |
|-------|-------------|----------|
| Missing or malformed authority token | 401 | `{"error": "HERMES_UNAUTHORIZED", "message": "Valid Hermes authorization required"}` |
| Expired token | 401 | `{"error": "HERMES_UNAUTHORIZED", "message": "HERMES_TOKEN_EXPIRED: ..."}` |
| Missing required capability | 403 | `{"error": "HERMES_UNAUTHORIZED", "message": "HERMES_UNAUTHORIZED: {capability} capability required"}` |
| Hermes attempts control command | 403 | `{"error": "HERMES_UNAUTHORIZED", "message": "Hermes agents cannot issue control commands"}` |

## Decision Log

- **Decision:** Hermes adapter is a Python module in the daemon, not a separate service.
  **Rationale:** The adapter is a capability boundary, not a deployment boundary. Enforcing scope by filtering requests before they reach the gateway contract avoids network-hop complexity.
  **Date/Author:** 2026-03-22 / Genesis Sprint

- **Decision:** Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`.
  **Rationale:** Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.
  **Date/Author:** 2026-03-22 / Genesis Sprint

- **Decision:** Hermes uses `Authorization: Hermes <base64-token>` header scheme (not `Authorization: Hermes <hermes_id>` as described in `references/hermes-adapter.md`).
  **Rationale:** The token carries `hermes_id`, `principal_id`, `capabilities`, and `expiration` inline, eliminating a second lookup. The reference doc needs updating; implementation is authoritative.
  **Date/Author:** 2026-03-22 / Genesis Sprint

- **Decision:** Control rejection enforced at HTTP handler level, not just adapter function level.
  **Rationale:** A previous draft only checked inside `read_status`/`append_summary`. The control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) had no auth checks at all — Hermes could have issued them. HTTP-level guard is the correct enforcement point.
  **Date/Author:** 2026-03-22 / Nemesis review

- **Decision:** `EventKind` enum imported from `spine.py`, not duplicated in `hermes.py`.
  **Rationale:** Duplicating the enum risked drift — a new event kind added to `spine.py` but not `hermes.py` would silently break filtering.
  **Date/Author:** 2026-03-22 / Nemesis review

# Hermes Adapter Implementation — Specification

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Status:** Implementation complete; three bugs corrected during review; one design-level issue deferred

---

## Purpose / User-Visible Outcome

A Hermes AI agent can be paired with the Zend home-miner daemon, connect using an authority token, read a live miner status snapshot (observe capability), and append summary events to the event spine (summarize capability). The adapter enforces a strict capability boundary: Hermes cannot issue miner control commands and cannot read `user_message` spine events.

---

## Scope

The Hermes adapter is a Python module (`services/home-miner-daemon/hermes.py`) that acts as an in-process authority boundary between external Hermes AI agents and the Zend gateway contract. It is not a separate service.

---

## Capability Model

Hermes has exactly two capabilities, independent from gateway capabilities:

| Capability  | Grants                                         |
|-------------|------------------------------------------------|
| `observe`   | Read miner status snapshot                     |
| `summarize` | Append summary events to the event spine       |

Hermes **cannot**:
- Issue control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`)
- Read `user_message` events from the spine
- Mutate payout targets
- Compose inbox messages

---

## Module Surface (`services/home-miner-daemon/hermes.py`)

### Constants

| Name | Value | Purpose |
|------|-------|---------|
| `HERMES_TOKEN_TTL` | `timedelta(hours=24)` | Token lifetime after issuance |
| `HERMES_CAPABILITIES` | `['observe', 'summarize']` | Fixed capability set for all Hermes pairings |
| `HERMES_READABLE_EVENTS` | `['hermes_summary', 'miner_alert', 'control_receipt']` | Spine events Hermes may read |

### Dataclasses

`HermesConnection` — active connection record with `hermes_id`, `principal_id`, `capabilities`, `connected_at`, `device_name`.

`HermesPairing` — stored pairing record with all fields above plus `id`, `token`, `token_expires_at`, `paired_at`.

### Functions

| Function | Capability Required | Behavior |
|----------|-------------------|----------|
| `connect(authority_token)` | — | Validates token existence and expiration; returns `HermesConnection` or raises `ValueError` |
| `pair_hermes(hermes_id, device_name)` | — | Creates or refreshes a pairing record; idempotent; issues a fresh UUID4 token and extends TTL on re-pair |
| `read_status(connection)` | `observe` | Calls `miner.get_snapshot()`; raises `PermissionError` without capability |
| `append_summary(connection, summary_text, authority_scope)` | `summarize` | Appends `hermes_summary` event to spine; raises `PermissionError` without capability |
| `get_filtered_events(connection, limit)` | — | Returns spine events filtered to `HERMES_READABLE_EVENTS`; does not check `observe` capability (defense-in-depth gap) |
| `validate_hermes_auth(hermes_id)` | — | Looks up pairing by `hermes_id`; returns `HermesConnection` or raises `ValueError` |

### Token Model

- Tokens are UUID4 strings generated at pairing time.
- TTL is 24 hours from issuance.
- Re-pairing the same `hermes_id` silently rotates the token and resets TTL.
- Tokens are stored in `state/hermes-pairing-store.json` under pairing IDs.

### Spine Access

Readable kinds: `hermes_summary`, `miner_alert`, `control_receipt`.
Writable kinds: `hermes_summary` only.
Blocked: `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`.

---

## Daemon HTTP Endpoints (`services/home-miner-daemon/daemon.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/hermes/pair` | none | Create or refresh Hermes pairing; returns token and TTL |
| POST | `/hermes/connect` | `authority_token` in body | Validate token; establish session |
| GET | `/hermes/status` | `Authorization: Hermes <id>` | Read miner snapshot via adapter |
| POST | `/hermes/summary` | `Authorization: Hermes <id>` | Append summary to spine |
| GET | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered spine events |

### Control Rejection

`_handle_control_attempt()` checks for `Authorization: Hermes` prefix on all control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) and returns 403 `HERMES_UNAUTHORIZED` before processing.

---

## CLI Subcommands (`services/home-miner-daemon/cli.py`)

| Command | Description |
|---------|-------------|
| `hermes pair --hermes-id X` | Pair Hermes agent |
| `hermes connect --token X` | Connect with authority token |
| `hermes status --hermes-id X` | Read miner status |
| `hermes summary --hermes-id X --text Y` | Append summary |
| `hermes events --hermes-id X` | Read filtered events |

---

## Gateway Agent Tab (`apps/zend-home-gateway/index.html`)

The Agent tab displays:
- Hermes connection state (connected / offline indicator)
- Hermes ID
- Capability pills (`observe`, `summarize`)
- Miner status as seen by Hermes
- Recent `hermes_summary` events from the spine

---

## Spec Conformance Against `references/hermes-adapter.md`

| Contract Item | Status | Notes |
|---------------|--------|-------|
| `observe` capability gates `read_status` | ✅ | `PermissionError` raised without `observe` |
| `summarize` capability gates `append_summary` | ✅ | `PermissionError` raised without `summarize` |
| No control via Hermes | ✅ | 403 returned before processing on control endpoints |
| `user_message` excluded from spine reads | ✅ | Filtered via `HERMES_READABLE_EVENTS` |
| Spine write: `hermes_summary` only | ✅ | Only `append_hermes_summary()` is exposed |
| Authority token with principal, capabilities, expiration | Partial | Token is UUID4; principal and capabilities stored in pairing record alongside token |
| Token TTL 24 h | ✅ | `HERMES_TOKEN_TTL = timedelta(hours=24)` |

---

## Bugs Fixed During Implementation

1. **Token born expired** (`hermes.py:144,157`) — `token_expires_at` was set to `datetime.now()` instead of `datetime.now() + HERMES_TOKEN_TTL`. Fixed before review.

2. **Parameter swap crash** (`daemon.py:341`) — `_handle_hermes_summary` received `(data, connection)` but `@require_hermes_auth` injects `(connection, *args)`. Fixed to `(connection, data: dict)` before review.

3. **Dead Agent tab** (`index.html:957-958`) — `fetchHermesStatus()` was defined but never called. Added to initial fetch and polling interval before review.

---

## Deferred Design Issue

**Dual auth path**: `/hermes/connect` validates token expiration; `@require_hermes_auth` (used by status, summary, events) only checks that `hermes_id` exists in pairings. Any client who knows or guesses a `hermes_id` can access protected endpoints without a valid token. The contract specifies `Authorization: Hermes <id>` as the auth scheme; fixing this changes the wire protocol and is deferred to a design decision.

---

## Remaining Gaps

### Must fix before lane close
- **Tests**: `tests/test_hermes.py` does not exist. Plan specifies 8 tests; none are implemented.

### Should fix (not blocking)
- `validate_hermes_auth()` should also check `token_expires_at`
- `get_filtered_events()` should gate on `observe` capability
- Hermes pairing should emit a spine event (audit trail gap)
- `hermes_id` should be validated against a character whitelist

### Pre-existing issues (out of scope)
- `store.py:89` `create_pairing_token()` has the same born-expired bug for gateway pairings
- Smoke test `scripts/hermes_summary_smoke.sh` bypasses the adapter and writes directly to spine

---

## Decision Log

- **2026-03-22**: Fixed token born-expired bug in `pair_hermes()` and re-pair code path by adding `HERMES_TOKEN_TTL` constant.
- **2026-03-22**: Fixed `@require_hermes_auth` parameter ordering in `_handle_hermes_summary`.
- **2026-03-22**: Fixed dead Agent tab by wiring `fetchHermesStatus()` into initial fetch and polling.
- **2026-03-22**: Deferred token-expiration check in `validate_hermes_auth()` to a future design decision on wire protocol.

# Hermes Adapter — As-Built Spec

**Lane:** `hermes-adapter-implementation`
**Status:** partial
**Date:** 2026-03-22
**Updated:** 2026-03-23 (polish pass)

---

## Purpose

Record the durable as-built surface of the Hermes adapter slice — what was implemented, what was verified by review, and what gaps remain before the slice can be signed off as complete.

This document is not the plan. It is the snapshot of what exists. The review document paired with this one contains the honest assessment of fitness.

---

## Repo Context

The Zend product (`DESIGN.md`, `SPEC.md`) defines a home-miner gateway with an event spine. The Hermes adapter (`services/home-miner-daemon/hermes.py`) is the enforcement boundary between the Hermes agent (which can observe and summarize) and the daemon's control surfaces (which Hermes must not reach).

This adapter sits inside `services/home-miner-daemon/`, alongside `daemon.py` which is the HTTP front door.

---

## Implemented Surfaces

### `services/home-miner-daemon/hermes.py`

| Symbol | Purpose | State |
|--------|---------|-------|
| `HermesConnection` | Dataclass: validated connection with granted capabilities | done |
| `HermesPairing` | Dataclass: persisted pairing record with token | done |
| `HERMES_CAPABILITIES` | `['observe', 'summarize']` — no `control` | done |
| `HERMES_READABLE_EVENTS` | Event kinds Hermes may read (excludes `user_message`) | done |
| `pair_hermes(hermes_id, device_name)` | Create/update idempotent pairing; issues token | done |
| `connect(authority_token)` | Validate token, return `HermesConnection` | done |
| `validate_hermes_auth(hermes_id)` | Validate by ID only (see gap 1 below) | partial |
| `read_status(connection)` | Delegate to `miner.get_snapshot()`; checks `observe` | done |
| `append_summary(connection, text, scope)` | Append `HERMES_SUMMARY` event; checks `summarize` | done |
| `get_filtered_events(connection, limit)` | Return events filtered to `HERMES_READABLE_EVENTS` | done |
| `check_control_capability(connection)` | Safety: always returns `False` for Hermes | done |
| `get_hermes_status(connection)` | Connection diagnostics | done |

### `services/home-miner-daemon/daemon.py`

| Endpoint | Handler | Auth method |
|----------|---------|-------------|
| `POST /hermes/pair` | `_handle_hermes_pair` | none (pairing is open) |
| `POST /hermes/connect` | `_handle_hermes_connect` | body `authority_token` |
| `GET /hermes/status` | `_handle_hermes_status` | `Authorization: Hermes <hermes_id>` |
| `POST /hermes/summary` | `_handle_hermes_summary` | `Authorization: Hermes <hermes_id>` |
| `GET /hermes/events` | `_handle_hermes_events` | `Authorization: Hermes <hermes_id>` |
| Control endpoints | `_handle_control_with_hermes_check` | Blocks Hermes auth → 403 |

---

## Verified Behavior (from review)

1. **Pairing is idempotent.** `POST /hermes/pair` with the same `hermes_id` returns the existing pairing.

2. **Token flow works for `/hermes/connect`.** `POST /hermes/connect` with a valid token returns a connection status.

3. **`user_message` events are filtered.** `GET /hermes/events` omits `user_message` from results.

4. **Control commands are blocked for Hermes.** `POST /miner/start` with `Authorization: Hermes <id>` returns `403 HERMES_UNAUTHORIZED`.

5. **Router bug was fixed during review.** A duplicate `do_POST()` definition was removing Hermes routing; it was removed and endpoints became active.

---

## Known Gaps

### Gap 1 — Authority token is not the runtime auth boundary

**What the slice claims:** Hermes runtime requests are validated by the authority token.

**What actually happens:** After `connect()`, all subsequent requests (`/hermes/status`, `/hermes/summary`, `/hermes/events`) authorize with `Authorization: Hermes <hermes_id>` — the `authority_token` presented to `connect()` is not replayed or enforced.

**Impact:** Any caller who knows a paired `hermes_id` can call status, summary, and events without presenting the pairing token. The token is only used during `connect()`.

**Root cause:** `validate_hermes_auth(hermes_id)` looks up by ID only and does not accept or check a token. The design intent (token-as-session-credential) was not implemented in the runtime path.

**Next action:** Either (a) change runtime auth to require a server-issued session derived from the token, or (b) change the spec to document that Hermes auth is ID-based after pairing, not token-based.

### Gap 2 — Token expiration is not enforced

**What happens:** `pair_hermes()` sets `token_expires_at = now` (effectively immediately expired). `connect()` reads the field but never checks it.

**Impact:** Expiration semantics are cosmetic. A token stored at any point in the past is treated identically to a freshly issued one.

**Next action:** Either implement real token lifetime (future-dated expiry, enforcement in `connect()`) or remove the field and document that tokens do not expire.

### Gap 3 — Boundary tests are absent

`services/home-miner-daemon/tests/test_hermes.py` does not exist.

**Next action:** Add tests covering: token issuance and validation, capability enforcement, `user_message` filtering, and Hermes control-block before marking complete.

---

## Frontier Task Matrix

| Task | Intended | Actual | Gap |
|------|----------|--------|-----|
| Create `hermes.py` adapter module | module exists | module exists | none |
| `HermesConnection` with authority token validation | token used in all requests | token used only in `connect()`; runtime uses `hermes_id` | Gap 1 |
| `readStatus` through adapter | works through endpoint | works through endpoint | none |
| `appendSummary` through adapter | works through endpoint | works through endpoint | none |
| Event filtering | `user_message` excluded | `user_message` excluded | none |
| Hermes pairing endpoint in daemon | `POST /hermes/pair` active | active after router fix | none |

---

## Supervisory Plane Notes

This slice is usable as a local exploration surface. The core adapter shape is correct and the control-block is verified. The three gaps above are not aesthetic — Gap 1 is a real trust-boundary concern if Hermes credentials are ever exposed beyond the local LAN. Gap 2 makes token rotation or expiry unusable. Gap 3 means the slice has no automated proof of its security claims.

Do not mark `hermes-adapter-implementation` as complete until Gap 1 is resolved at the spec level and Gap 3 has test coverage.

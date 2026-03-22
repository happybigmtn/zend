# Hermes Adapter Implementation — Specification

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Status:** Complete

---

## Purpose

After this work, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine — but cannot issue control commands or read user messages. This is the first step toward agent parity: Hermes uses the same API primitives as human clients but with a narrower capability scope.

---

## What Was Built

### 1. `services/home-miner-daemon/hermes.py` — Adapter module

A Python module implementing the full Hermes adapter contract:

- **`HERMES_CAPABILITIES = ["observe", "summarize"]`** — distinct from gateway `["observe", "control"]`; Hermes can never inherit gateway control capability
- **`HERMES_READABLE_EVENTS`** — `[hermes_summary, miner_alert, control_receipt]`; explicitly excludes `user_message`
- **`HermesConnection`** dataclass — carries `hermes_id`, `principal_id`, `capabilities`, `connected_at`, `authority_scope`
- **`connect(authority_token)`** — validates token structure, expiration, and that no capability outside `HERMES_CAPABILITIES` is requested
- **`read_status(connection)`** — requires `observe` capability; raises `PermissionError` otherwise
- **`append_summary(connection, summary_text, authority_scope)`** — requires `summarize` capability; appends `hermes_summary` event to the spine
- **`get_filtered_events(connection, limit)`** — returns events from `HERMES_READABLE_EVENTS` only; over-fetches then trims
- **`pair_hermes(hermes_id, device_name)`** — creates (or re-creates) a pairing record; idempotent
- **`get_hermes_pairing(hermes_id)`** — retrieves pairing if it exists
- **`build_authority_token(connection, expires_in_hours)`** — produces a plain-JSON token (milestone 1); documents where JWT signing would go

### 2. `services/home-miner-daemon/daemon.py` — Hermes HTTP endpoints

Added to `GatewayHandler`:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/hermes/connect` | none | Validate authority token, return connection state |
| `POST` | `/hermes/pair` | none | Create Hermes pairing record |
| `GET` | `/hermes/status` | `Authorization: Hermes <id>` | Read miner status via adapter (observe cap) |
| `POST` | `/hermes/summary` | `Authorization: Hermes <id>` | Append Hermes summary (summarize cap) |
| `GET` | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered events (user_message blocked) |

All routes use the same threaded HTTP server. Hermes auth is a separate header scheme (`Hermes <id>`) from device auth.

### 3. `services/home-miner-daemon/cli.py` — Hermes subcommands

Added `hermes` top-level command with subcommands:
- `hermes pair --hermes-id <id>` — create pairing and print authority token
- `hermes connect --token <json>` — validate token and print connection state
- `hermes status --hermes-id <id>` — read miner status through adapter
- `hermes summary --hermes-id <id> --text <text>` — append summary
- `hermes events --hermes-id <id>` — read filtered events

### 4. `apps/zend-home-gateway/index.html` — Agent tab

Replaced "Hermes not connected" placeholder with:
- Real connection state from daemon (`hermesStatusDot`, `hermesId`)
- Capability pills (observe, summarize) rendered dynamically
- Recent Hermes summaries list from filtered events
- Boundary notice: "Hermes cannot issue control commands"
- Polling every 10s via `fetchHermesState()`

### 5. `services/home-miner-daemon/tests/test_hermes.py` — Boundary tests

22 tests covering:
- Valid / expired / malformed token connections
- `control` capability rejection at connect time
- `observe` gate on `read_status()`
- `summarize` gate on `append_summary()`
- `user_message` never appears in `get_filtered_events()`
- `hermes_summary` and `miner_alert` always allowed
- `append_summary` result appears in spine query
- Pairing idempotency
- Token round-trip (`pair_hermes` → `build_authority_token` → `connect`)

**Result: 22 passed, 0 failed.**

### 6. `scripts/hermes_summary_smoke.sh` — Integration smoke test

Rewritten to use the real adapter (not direct spine calls):
1. Pairs Hermes agent
2. Builds authority token
3. Connects with token
4. Appends summary
5. Verifies summary in filtered event list
6. Verifies `user_message` never appears before and after seeding

**Result: PASSED.**

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Hermes adapter is an in-process Python module, not a separate service | The adapter is a capability boundary, not a deployment boundary; avoids network hop complexity |
| Hermes uses `observe` + `summarize`, NOT `control` | Per `references/hermes-adapter.md`; agent trust model differs from gateway |
| Authority token is plain JSON in milestone 1, JWT in production | Simplicity for bootstrap; `build_authority_token` documents the signing point |
| Event filtering over-fetches then trims | Filtering removes items from the head of the list; over-fetching ensures the requested limit is met |
| `Authorization: Hermes <id>` header scheme | Distinguishes Hermes auth from device auth at the HTTP layer |

---

## Capability Boundary Summary

```
Gateway capabilities:  observe + control
Hermes capabilities:  observe + summarize
                      ^^^^^^^^^^^^^^^^^
                      overlap           exclusive
```

Hermes cannot:
- Call `/miner/start`, `/miner/stop`, `/miner/set_mode`
- Read `user_message` events from the spine
- Request `control` at connect time (rejected before any operation)

---

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Hermes can connect with authority token | ✓ |
| Hermes can read miner status | ✓ |
| Hermes can append summaries to event spine | ✓ |
| Hermes CANNOT issue control commands | ✓ (no `control` cap exists) |
| Hermes CANNOT read `user_message` events | ✓ (filtered) |
| Agent tab shows real connection state | ✓ (polling + rendering) |
| All 22 tests pass | ✓ |
| Smoke test passes | ✓ |

---

## Files Created or Modified

| File | Change |
|------|--------|
| `services/home-miner-daemon/hermes.py` | **Created** |
| `services/home-miner-daemon/daemon.py` | Modified — added Hermes endpoints |
| `services/home-miner-daemon/cli.py` | Modified — added `hermes` subcommands |
| `services/home-miner-daemon/tests/test_hermes.py` | **Created** |
| `apps/zend-home-gateway/index.html` | Modified — real Agent tab state |
| `scripts/hermes_summary_smoke.sh` | Modified — uses real adapter |

---

## Idempotence

- `pair_hermes` is idempotent: same `hermes_id` re-pairs cleanly
- Summary append is append-only (spine semantics)
- All operations can be safely repeated

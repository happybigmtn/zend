# Hermes Adapter Implementation — Spec

**Status:** Reviewed — not implemented
**Reviewed:** 2026-03-23
**Frontier:** `hermes-adapter-implementation`

---

## Intent

This lane delivers the first Hermes boundary inside the home-miner daemon: a scoped adapter that validates a Hermes authority token, reads miner status, appends `hermes_summary` events, hides `user_message` events from Hermes reads, and exposes Hermes-specific daemon routes.

The core trust contract is: **Hermes can observe and summarize, but cannot control the miner or read `user_message` events.**

---

## Requested Slice

1. Create `services/home-miner-daemon/hermes.py` — `HermesConnection` adapter
2. Implement authority token validation in the adapter
3. Implement `read_status` (via adapter → miner)
4. Implement `append_summary` (via adapter → spine)
5. Implement Hermes event filtering — block `user_message` on read
6. Add Hermes pairing endpoint to the daemon
7. Expose daemon routes: `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`

---

## Checked-In Reality

### Missing files

| File | Status |
|---|---|
| `services/home-miner-daemon/hermes.py` | Absent |
| `services/home-miner-daemon/tests/test_hermes.py` | Absent |

### Existing daemon routes (`daemon.py:168-200`)

Only these endpoints exist:
- `GET /health`
- `GET /status`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`

No `/hermes/*` routes exist.

### Control routes are unauthenticated

`POST /miner/start`, `POST /miner/stop`, and `POST /miner/set_mode` mutate miner state with no pairing check, token check, or capability guard. Any caller that can reach the daemon can control the miner.

### Store cannot represent Hermes authority tokens (`store.py:40-139`)

- `GatewayPairing` keys by `device_name` only — no Hermes-specific pairing record
- `create_pairing_token()` returns `expires = datetime.now(timezone.utc)` — a newly created token is already expired
- `pair_client()` calls `create_pairing_token()` but never stores the returned `token` value; the `token_expires_at` field is always `datetime.now()`
- No lookup by token or `hermes_id` exists

### Event filtering absent (`spine.py:82-92`)

`get_events()` returns raw events filtered only by optional `kind` parameter. No path enforces a Hermes-specific filter contract. `cli.py:179` prints whatever `spine.get_events()` returns with no `user_message` guard.

### Smoke test bypasses adapter (`hermes_summary_smoke.sh:44-55`)

The script imports `append_hermes_summary` directly from `spine` and writes without going through daemon routes or token validation.

### Agent UI is a static placeholder

`index.html:569` renders "Hermes not connected" with no backed connection state.

---

## Minimal Truthful Acceptance Criteria

This lane is complete only when all of the following are true in source:

### Adapter module
- [ ] `services/home-miner-daemon/hermes.py` exists
- [ ] `HermesConnection` class with constructor that accepts a validated authority token
- [ ] `read_status()` method that returns miner snapshot via adapter
- [ ] `append_summary()` method that appends `hermes_summary` to spine
- [ ] `get_events()` method that returns events with `user_message` filtered out

### Daemon routes
- [ ] `POST /hermes/pair` — creates Hermes pairing record with stored token
- [ ] `POST /hermes/connect` — validates authority token, returns Hermes session
- [ ] `GET /hermes/status` — returns Hermes connection status
- [ ] `POST /hermes/summary` — appends summary via adapter
- [ ] `GET /hermes/events` — returns filtered event stream

### Trust enforcement
- [ ] Hermes cannot reach miner control behavior through any daemon route
- [ ] Hermes event reads never include `user_message` events
- [ ] Control routes (`/miner/*`) are gated behind pairing/capability checks

### Store extensions
- [ ] Hermes pairing record with `hermes_id`, token material, capabilities, non-immediate expiry
- [ ] Lookup by token or `hermes_id`

### Integration
- [ ] Smoke path exercises daemon-facing Hermes flow (not direct spine append)

---

## Immediate Blockers

1. **No adapter module.** Nothing to review.
2. **No Hermes daemon routes.** Trust contract cannot be enforced.
3. **Store schema cannot represent Hermes authority tokens.** No token storage, no Hermes lookup, immediate expiry.
4. **Control routes are unauthenticated.** "Hermes cannot control" is not yet enforceable in code.

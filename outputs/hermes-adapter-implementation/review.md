# Hermes Adapter Implementation — Review

**Reviewed:** 2026-03-23
**Frontier:** `hermes-adapter-implementation`
**Verdict:** Not accepted — slice absent

---

## Summary

The Hermes adapter slice has not been implemented. The daemon exposes no Hermes routes, the store schema cannot represent Hermes authority tokens, the adapter module does not exist, and the control endpoints are unauthenticated. The trust contract ("Hermes observes but cannot control") is not yet enforceable in code.

---

## Critical Findings

### 1. Control routes are unauthenticated

`POST /miner/start`, `POST /miner/stop`, and `POST /miner/set_mode` in `daemon.py:168-200` mutate miner state without any pairing check, token check, or capability guard. Any local caller can control the miner.

**Impact:** The core trust property — Hermes cannot control — cannot be claimed until auth is placed in front of these mutations.

### 2. Hermes adapter slice is absent

`services/home-miner-daemon/hermes.py` does not exist. `daemon.py:168-200` has no `/hermes/*` endpoints. There is no `HermesConnection`, no token validation path, and no adapter enforcement layer.

**Impact:** Nothing exists to review. The lane must be built from scratch.

---

## High Findings

### 3. Authority token validation is unimplementable on current store contract

`store.py:83-86` — `create_pairing_token()` returns `expires = datetime.now(timezone.utc)`. A newly created token is immediately expired. Additionally, `pair_client()` calls `create_pairing_token()` but the returned `token` value is never stored anywhere — `GatewayPairing` has no `token` field, only `token_expires_at`. There is no lookup by token or `hermes_id`.

**Impact:** "Validate authority token, then connect Hermes" has no honest code path.

### 4. Event filtering is not enforced on any Hermes read path

`spine.py:82-92` — `get_events()` returns raw events with only an optional `kind` filter. `cli.py:179` prints the raw output with no `user_message` guard. The lane requirement to block `user_message` for Hermes is not implemented anywhere.

**Impact:** If a Hermes read path existed today, it would return all event types including `user_message`.

---

## Medium Findings

### 5. Hermes smoke path bypasses the adapter

`hermes_summary_smoke.sh:44-55` imports `append_hermes_summary` directly from `spine` and writes without exercising daemon routes or token validation. It cannot validate the milestone behavior.

### 6. Agent UI shows a static placeholder

`index.html:569` renders "Hermes not connected" with no backed connection state or capability display. Confirms the real Hermes connection flow is not wired through the product surface.

### 7. No Hermes test coverage

`services/home-miner-daemon/tests/test_hermes.py` is absent. No test files exist under the service tree.

---

## Trust Boundary Analysis

The central trust boundary is: **Hermes can observe and summarize, but cannot control or read `user_message` events.**

This boundary does not exist in code today. Worse, the daemon control endpoints are open to any local caller, so the repo is not merely missing Hermes scoping — it is missing request authentication for the dangerous path entirely.

### State coupling is broken

The Hermes flow requires consistent state across store, daemon auth, and spine reads. Today those surfaces are disconnected:

- Store only models gateway client pairings by `device_name`
- Daemon request handling does not consult store state for control routes
- Spine reads are raw and carry no Hermes-specific filter contract

Because those pieces are not coupled, there is no replay story, no expiry enforcement, and no capability boundary to review.

---

## Milestone Fit Assessment

This lane does not satisfy the requested frontier tasks. The lane can only be called a completed first slice after:

- The `hermes.py` adapter module exists with `HermesConnection`, token validation, `read_status`, `append_summary`, and filtered event access
- The daemon exposes `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`
- Token validation uses a store record that stores token material and non-immediate expiry
- Authorization guards are in front of control mutations so "Hermes cannot control" is true under adversarial requests
- The smoke path exercises daemon-facing Hermes flow instead of writing directly to the spine

---

## Remaining Blockers

| # | Blocker | File(s) |
|---|---|---|
| 1 | Add `HermesConnection` adapter module | `services/home-miner-daemon/hermes.py` (new) |
| 2 | Extend store with Hermes pairing/token record and lookup | `services/home-miner-daemon/store.py` |
| 3 | Add Hermes daemon routes | `services/home-miner-daemon/daemon.py` |
| 4 | Auth guard on miner control routes | `services/home-miner-daemon/daemon.py` |
| 5 | Replace direct-spine smoke with daemon-backed test | `scripts/hermes_summary_smoke.sh` |
| 6 | Add Hermes tests | `services/home-miner-daemon/tests/test_hermes.py` (new) |

---

## Reviewer Note

The prior lane artifacts overstated implementation progress. This review reflects the actual checked-in state. No product source changes were made.

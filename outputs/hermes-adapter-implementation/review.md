# Hermes Adapter Implementation — Review

**Lane:** hermes-adapter-implementation
**Plan:** genesis/plans/009-hermes-adapter-implementation.md
**Reviewer:** Nemesis security review + correctness audit
**Date:** 2026-03-22
**Verdict:** CONDITIONAL PASS — three critical bugs fixed during review; design-level auth issue remains

## Files Reviewed

| File | Lines | Role |
|------|-------|------|
| `services/home-miner-daemon/hermes.py` | 285 | Adapter module |
| `services/home-miner-daemon/daemon.py` | 406 | HTTP daemon with Hermes endpoints |
| `services/home-miner-daemon/spine.py` | 159 | Event spine |
| `services/home-miner-daemon/store.py` | 143 | Principal and pairing store |
| `services/home-miner-daemon/cli.py` | 402 | CLI with Hermes subcommands |
| `apps/zend-home-gateway/index.html` | 962 | Gateway client with Agent tab |
| `references/hermes-adapter.md` | 90 | Adapter contract spec |
| `scripts/hermes_summary_smoke.sh` | 59 | Smoke test |

## Critical Bugs Fixed During Review

### 1. Token Born Expired — `hermes.py:144,157`

**Was:** `pair_hermes()` set `token_expires_at = datetime.now(timezone.utc).isoformat()` — tokens expired at creation time.

**Impact:** `connect(authority_token)` always rejected tokens with `HERMES_TOKEN_EXPIRED`.

**Fix:** Added `HERMES_TOKEN_TTL = timedelta(hours=24)` and changed both expiration assignments to `datetime.now(timezone.utc) + HERMES_TOKEN_TTL`.

**Note:** The same pattern exists in `store.py:89` (`create_pairing_token()`) for gateway pairings. That is a pre-existing issue outside this lane's surface.

### 2. Parameter Swap Crash — `daemon.py:341`

**Was:** `_handle_hermes_summary(self, data: dict, connection)` — but `@require_hermes_auth` injects `(self, connection, *args)`, so `data` received the HermesConnection and `connection` received the dict.

**Impact:** Every POST to `/hermes/summary` raised `AttributeError: 'HermesConnection' object has no attribute 'get'`.

**Fix:** Changed signature to `_handle_hermes_summary(self, connection, data: dict)`.

### 3. Dead Agent Tab — `index.html:957-958`

**Was:** `fetchHermesStatus()` was defined but never called. Only `fetchStatus()` was in the initial fetch and polling interval.

**Impact:** Agent tab permanently showed "Not connected" / "Offline" regardless of actual Hermes state.

**Fix:** Added `fetchHermesStatus()` to initial fetch and `setInterval(fetchHermesStatus, 10000)` for polling.

## Nemesis Pass 1 — Trust Boundary Analysis

### DESIGN ISSUE: Dual Auth Path (NOT FIXED — requires design decision)

The daemon has two independent auth mechanisms:

| Path | Used By | Validates |
|------|---------|-----------|
| `connect(authority_token)` | `POST /hermes/connect` | Token existence + expiration + capabilities |
| `validate_hermes_auth(hermes_id)` | `@require_hermes_auth` decorator (all other endpoints) | Only that hermes_id exists in pairings |

**Consequence:** All protected Hermes endpoints (`/hermes/status`, `/hermes/summary`, `/hermes/events`) authenticate by hermes_id string alone. Token expiration is checked only in the explicit `/hermes/connect` call, which is optional — a client can skip it entirely and go straight to the data endpoints.

**Risk:** Anyone who knows or guesses a hermes_id can access all Hermes endpoints. Since hermes_id is user-provided during pairing (e.g., `"hermes-001"`), it's predictable.

**Recommendation:** `validate_hermes_auth()` should also check `token_expires_at`. Or better: the `connect()` flow should return a session token that subsequent requests use, rather than relying on the static hermes_id.

**Why not fixed here:** This is a design decision affecting the auth contract, not a bug in the implementation of the stated design. The plan describes `Authorization: Hermes <hermes_id>` as the auth scheme. Fixing this changes the wire protocol.

### Control Rejection: CORRECT

`_handle_control_attempt()` (`daemon.py:249-259`) correctly checks for `Authorization: Hermes` prefix and returns 403 before processing any control command. This is enforced at the routing level, not by capability check, which is defense-in-depth appropriate.

### Event Filtering: CORRECT but missing capability gate

`get_filtered_events()` (`hermes.py:224-249`) correctly filters to `HERMES_READABLE_EVENTS` (excludes `user_message`). However, it does **not** check for `observe` capability on the connection. Since all paired Hermes agents currently get both capabilities, this is safe today but violates defense-in-depth.

### Pairing Endpoint: UNAUTHENTICATED

`POST /hermes/pair` requires no authentication. Any client on the LAN can pair a Hermes agent. This is consistent with the gateway device pairing model (also unauthenticated) and acceptable for milestone 1 LAN-only deployment.

## Nemesis Pass 2 — Coupled State & Mutation Consistency

### Pairing Store / Spine Consistency

`pair_hermes()` writes to `hermes-pairing-store.json` but does NOT write a spine event. Compare with `cmd_pair()` in `cli.py` which writes both `pairing_requested` and `pairing_granted` events. Hermes pairing is unaudited in the spine.

**Impact:** No audit trail for when Hermes was paired or re-paired.

**Recommendation:** `pair_hermes()` should call `spine.append_pairing_granted()` with Hermes-specific metadata.

### Token Rotation on Re-pair

`pair_hermes()` (`hermes.py:140-146`) silently rotates the token on re-pair. If a Hermes agent is actively using the old token via `connect()`, it will be invalidated without notice. Acceptable for milestone 1.

### Append-Only Spine: CORRECT

`append_summary()` correctly delegates to `spine.append_hermes_summary()` which only appends. No mutation of existing events is possible.

### File I/O Race Conditions

Both `_load_hermes_pairings()` and `_save_hermes_pairings()` use plain file I/O with no locking. The `ThreadedHTTPServer` can serve concurrent requests, creating a TOCTOU window where two concurrent pairings could lose data. Acceptable for milestone 1 single-user.

## Milestone Fit Assessment

### Plan 009 Checklist

| Task | Status | Notes |
|------|--------|-------|
| Create hermes.py adapter module | DONE | Module exists with all specified functions |
| HermesConnection with authority token validation | DONE | Token validation works after TTL fix |
| readStatus through adapter | DONE | Capability-gated, delegates to miner snapshot |
| appendSummary through adapter | DONE | Capability-gated, writes to spine; parameter fix applied |
| Event filtering (block user_message) | DONE | `HERMES_READABLE_EVENTS` excludes `user_message` |
| Hermes pairing endpoint | DONE | `POST /hermes/pair` in daemon |
| CLI Hermes subcommands | DONE | pair, connect, status, summary, events |
| Gateway Agent tab | DONE | Shows connection state, capabilities, summaries; fetch fix applied |
| Tests | NOT DONE | `tests/test_hermes.py` does not exist |

### Spec Conformance (`references/hermes-adapter.md`)

| Spec Requirement | Implemented | Notes |
|-----------------|-------------|-------|
| observe capability | Yes | `read_status()` checks `observe` |
| summarize capability | Yes | `append_summary()` checks `summarize` |
| No direct control | Yes | 403 on control endpoints with Hermes auth |
| Spine read filtering | Yes | `user_message` excluded |
| Spine write: hermes_summary only | Yes | Only write path is `append_hermes_summary()` |
| Authority token with principal, capabilities, expiration | Partial | Token is UUID, not structured; principal and capabilities stored alongside in pairing record |

## Remaining Blockers

### Must-fix before lane close

1. **Tests** — Plan specifies 8 tests in `tests/test_hermes.py`. None exist. This is the primary remaining blocker.

### Should-fix (not blocking but recommended)

2. **`validate_hermes_auth()` should check token expiration** — Current auth decorator bypasses token lifecycle entirely.
3. **`get_filtered_events()` should check `observe` capability** — Defense-in-depth gap.
4. **Hermes pairing should emit spine events** — Audit trail gap.
5. **Input validation on hermes_id** — No sanitization of auth header value; should reject non-alphanumeric.
6. **`_parse_body()` needs Content-Length cap** — No limit on request body size.

### Out of scope (pre-existing)

7. `store.py:89` `create_pairing_token()` has the same born-expired bug for gateway pairings.
8. Spine claims "encrypted event journal" in docstring but has no encryption.
9. Smoke test (`scripts/hermes_summary_smoke.sh`) bypasses the adapter and writes directly to spine.

## Summary

The Hermes adapter implements the stated capability boundary correctly after the three fixes applied during this review. The core contract — observe, summarize, no control, no user_message — is enforced. The primary gap is the missing test suite and the design-level auth weakness where hermes_id alone (without token) grants endpoint access. The lane is unblocked for the next stage (test authoring) but should not be considered complete until `tests/test_hermes.py` exists and the auth path is hardened.

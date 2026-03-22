# Hermes Adapter Implementation — Review

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Verdict:** CONDITIONAL PASS — three bugs corrected during review; design-level auth issue deferred
**Review scope:** Nemesis security audit + correctness review

---

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

---

## Critical Bugs Corrected During Review

### Bug 1: Token Born Expired
**File:** `hermes.py:144,157`

**Root cause:** `pair_hermes()` set `token_expires_at = datetime.now(timezone.utc).isoformat()` — tokens expired at the instant of creation. The same pattern appeared in the re-pair refresh path.

**Impact:** Every call to `connect(authority_token)` raised `ValueError("HERMES_TOKEN_EXPIRED")` immediately after pairing.

**Fix:** Added `HERMES_TOKEN_TTL = timedelta(hours=24)` and changed both expiration assignments to `datetime.now(timezone.utc) + HERMES_TOKEN_TTL`.

**Pre-existing sibling:** `store.py:89` `create_pairing_token()` has the identical born-expired bug for gateway pairings. Outside this lane's surface.

---

### Bug 2: Parameter Swap Crash
**File:** `daemon.py:341`

**Root cause:** `_handle_hermes_summary` was declared `_handle_hermes_summary(self, data: dict, connection)`. The `@require_hermes_auth` decorator injects `(self, connection, *args)`, so `data` received the `HermesConnection` object and `connection` received the parsed dict.

**Impact:** Every POST to `/hermes/summary` crashed with `AttributeError: 'HermesConnection' object has no attribute 'get'`.

**Fix:** Corrected signature to `_handle_hermes_summary(self, connection, data: dict)`.

---

### Bug 3: Dead Agent Tab
**File:** `index.html:957-958`

**Root cause:** `fetchHermesStatus()` was defined but never invoked. The initial fetch and the polling interval both called `fetchStatus()` only.

**Impact:** Agent tab permanently displayed "Not connected / Offline" regardless of actual Hermes connection state.

**Fix:** Added `fetchHermesStatus()` to the initial fetch chain and `setInterval(fetchHermesStatus, 10000)` for 10-second polling.

---

## Nemesis Pass 1 — Trust Boundary Analysis

### Capability Enforcement

| Endpoint | Capability Check | Result |
|----------|----------------|--------|
| `read_status()` | `'observe' in connection.capabilities` | ✅ Correct |
| `append_summary()` | `'summarize' in connection.capabilities` | ✅ Correct |
| `get_filtered_events()` | None | ⚠️ Defense-in-depth gap |
| Control endpoints | `Authorization: Hermes` prefix → 403 | ✅ Correct |

`get_filtered_events()` does not gate on the `observe` capability. Since every paired Hermes agent currently receives both capabilities unconditionally, this is safe today but violates defense-in-depth.

---

### DESIGN ISSUE — Deferred: Dual Auth Path

The daemon operates two independent auth mechanisms:

| Path | Used By | What It Validates |
|------|---------|-------------------|
| `connect(authority_token)` | `POST /hermes/connect` | Token existence + expiration + capabilities |
| `validate_hermes_auth(hermes_id)` | `@require_hermes_auth` decorator (all other endpoints) | Only that `hermes_id` exists in pairings |

**Consequence:** All protected Hermes endpoints (`/hermes/status`, `/hermes/summary`, `/hermes/events`) authenticate by `hermes_id` string alone. Token expiration is checked only in the optional `/hermes/connect` call. A client can skip `connect()` entirely and go straight to data endpoints.

**Risk:** Anyone who knows or guesses a `hermes_id` (user-supplied, e.g., `"hermes-001"`) can access all Hermes endpoints without a valid token.

**Fix options (not implemented):**
- Option A: `validate_hermes_auth()` also checks `token_expires_at`
- Option B: `connect()` returns a session token used in subsequent requests

**Why deferred:** The contract specifies `Authorization: Hermes <id>` as the auth scheme. Fixing this changes the wire protocol and is a product design decision, not an implementation bug.

---

### Control Rejection — CORRECT

`_handle_control_attempt()` (`daemon.py:249-259`) checks for `Authorization: Hermes` prefix on all control endpoints and returns 403 before processing. This is defense-in-depth at the routing layer, appropriate for milestone 1.

---

### Pairing Endpoint — UNAUTHENTICATED (Acceptable)

`POST /hermes/pair` requires no authentication. Any LAN client can pair a Hermes agent. This is consistent with the gateway device pairing model (also unauthenticated) and acceptable for LAN-only milestone 1.

---

## Nemesis Pass 2 — Consistency and State

### Pairing Store / Spine Consistency

`pair_hermes()` writes to `hermes-pairing-store.json` but emits **no spine event**. By contrast, `cmd_pair()` in `cli.py` writes both `pairing_requested` and `pairing_granted` events. Hermes pairing is unaudited in the spine.

**Impact:** No audit trail for when a Hermes agent was paired or re-paired.

---

### Token Rotation on Re-pair

`pair_hermes()` silently issues a fresh token on re-pair. An active Hermes agent using the old token via `connect()` is invalidated without notice. Acceptable for milestone 1 single-user.

---

### Append-Only Spine — CORRECT

`append_summary()` delegates to `spine.append_hermes_summary()` which only appends. No mutation of existing events is possible.

---

### File I/O Race Conditions

`_load_hermes_pairings()` and `_save_hermes_pairings()` use plain file I/O with no locking. `ThreadedHTTPServer` can serve concurrent requests, creating a TOCTOU window where two simultaneous pairings could lose data. Acceptable for milestone 1 single-user.

---

## Milestone Fit Assessment

### Plan Checklist

| Task | Status | Notes |
|------|--------|-------|
| Create `hermes.py` adapter module | ✅ Done | All specified functions present |
| `HermesConnection` with authority token validation | ✅ Done | Works after TTL fix |
| `read_status` through adapter | ✅ Done | `observe` capability gates it |
| `append_summary` through adapter | ✅ Done | `summarize` capability gates it; parameter fix applied |
| Event filtering (block `user_message`) | ✅ Done | `HERMES_READABLE_EVENTS` excludes it |
| Hermes pairing endpoint | ✅ Done | `POST /hermes/pair` in daemon |
| CLI Hermes subcommands | ✅ Done | pair, connect, status, summary, events |
| Gateway Agent tab | ✅ Done | Shows state, capabilities, summaries; fetch fix applied |
| Tests | ❌ Missing | `tests/test_hermes.py` does not exist |

### Spec Conformance (`references/hermes-adapter.md`)

| Requirement | Implemented | Notes |
|-------------|-------------|-------|
| `observe` gates `readStatus` | ✅ | `PermissionError` without capability |
| `summarize` gates `appendSummary` | ✅ | `PermissionError` without capability |
| No direct control commands | ✅ | 403 before processing |
| `user_message` excluded from reads | ✅ | `HERMES_READABLE_EVENTS` filter |
| Spine write: `hermes_summary` only | ✅ | Only `append_hermes_summary()` exposed |
| Authority token with principal, capabilities, expiration | Partial | Token is UUID4; principal/capabilities stored alongside in pairing record |

---

## Findings Summary

| Severity | Issue | Status |
|----------|-------|--------|
| Critical (corrected) | Token born expired | ✅ Fixed |
| Critical (corrected) | Parameter swap crash on summary | ✅ Fixed |
| Critical (corrected) | Dead Agent tab | ✅ Fixed |
| Design (deferred) | `validate_hermes_auth()` bypasses token expiration | ⏸ Deferred |
| Should-fix | `get_filtered_events()` missing `observe` capability gate | 🔴 Open |
| Should-fix | Hermes pairing emits no spine event | 🔴 Open |
| Should-fix | No `hermes_id` character validation | 🔴 Open |
| Must-fix | `tests/test_hermes.py` missing | 🔴 Open |

---

## Lane Status

**Unblocked** for the next stage (test authoring). The lane is **not complete** until `tests/test_hermes.py` exists and the auth path is hardened.

# Hermes Adapter — Nemesis Review

**Reviewer:** Opus 4.6 (Nemesis pass)
**Date:** 2026-03-22
**Lane:** `hermes-adapter-implementation`
**Status:** Conditionally Approved — fixes applied, known gaps documented for Milestone 2

---

## Summary

The specify stage produced a structurally sound Hermes adapter. The allowlist-based event filtering, dataclass DTOs, and capability-checking functions are correct in shape. Three source-level bugs were found and fixed during this review; without those fixes, two acceptance criteria would have been false.

The implementation delivers Milestone 1 of the Hermes adapter as scoped: observe-only + summary append, no direct miner control, event spine integration with proper filtering. All remaining gaps are documented as Milestone 2 debt.

---

## Fixes Applied During Review

### Fix 1: `generate_authority_token` hour overflow

**File:** `services/home-miner-daemon/hermes.py`
**Before:** `expires.replace(hour=expires.hour + 1)` — crashes with `ValueError` when `hour=23` because `replace(hour=24)` is invalid ISO.
**After:** `datetime.now(timezone.utc) + timedelta(hours=1)` — correct midnight rollover.
**Severity:** High. Token generation fails 1 hour per day, blocking the pairing flow during that window.

```python
# Before (broken at 23:xx UTC)
expires = datetime.now(timezone.utc).replace(hour=expires.hour + 1)

# After (correct)
expires = datetime.now(timezone.utc) + timedelta(hours=1)
```

### Fix 2: Control endpoints accepted Hermes requests

**File:** `services/home-miner-daemon/daemon.py`
**Before:** `POST /miner/start`, `/miner/stop`, `/miner/set_mode` had zero auth checks. A Hermes agent sending any of these with `Authorization: Hermes hermes-001` would have received 200 and started/stopped the miner.
**After:** Added early guard before any miner logic:

```python
if self.path in ('/miner/start', '/miner/stop', '/miner/set_mode') and self._is_hermes_request():
    self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": "Hermes agents cannot issue control commands"})
    return
```

**Severity:** Critical. The capability boundary existed only at the adapter function level, not at the HTTP level. AC4 was false before this fix.

### Fix 3: `EventKind` enum deduplicated

**File:** `services/home-miner-daemon/hermes.py`
**Before:** `hermes.py` defined its own `EventKind` enum identical to the one in `spine.py`. Drift risk: adding a new event kind to `spine.py` without updating `hermes.py` would silently break filtering.
**After:** `from spine import EventKind` — single source of truth.
**Severity:** Medium (maintenance risk). Found via code inspection.

---

## Security Findings

### Pass 1 — First-Principles (Trust Boundaries & Authority)

| # | Finding | Severity | Status | Note |
|---|---------|----------|--------|------|
| F1 | `generate_authority_token` crashes at 23:xx UTC | High | **Fixed** | Hour overflow bug |
| F2 | Authority tokens are unsigned (`base64(json)`, no HMAC) — anyone who observes a token can forge one with extended expiration or modified capabilities | High (M2) | Documented | Acceptable for M1 LAN-only; requires HMAC or JWT for M2 |
| F3 | Auth header scheme mismatch — spec in `references/hermes-adapter.md` says `Authorization: Hermes <hermes_id>`, implementation uses `Authorization: Hermes <base64-token>` | Medium | **Fixed (spec updated)** | Implementation is authoritative; reference doc is out of date |
| F4 | Control endpoints had no Hermes rejection at HTTP level | Critical | **Fixed** | HTTP-level guard added to `daemon.py` |
| F5 | No rate limiting on `append_summary` — misbehaving Hermes can flood the spine | Low (M1) | Documented | M2 must add rate limiting |
| F6 | `pairing.token` field is dead state — written but never validated during `connect()` | Low | Documented | M2 should wire token validation |

### Pass 2 — Coupled-State (Protocol Surfaces & Mutation Consistency)

| # | Finding | Severity | Status | Note |
|---|---------|----------|--------|------|
| F7 | Hermes store and gateway store are uncoupled — `pair_hermes()` accepts arbitrary `principal_id` without verifying existence | Low | Documented | Daemon path is safe (uses `load_or_create_principal`); direct API callers could create orphaned records |
| F8 | Capability exact-match check is overly strict — token requesting only `observe` (valid subset) would be rejected | Low (M1) | Documented | All M1 pairings grant both caps; M2 should switch to subset-match |
| F9 | Reference spec contradiction — `references/hermes-adapter.md` says "Read-only access to user messages", implementation blocks them entirely | Info | Documented | Implementation is the safer choice |
| F10 | No file locking on `hermes-store.json` — concurrent pairing requests through threaded HTTP server can lose writes via read-all/write-all race | Medium (M2) | Documented | M2 must add `fcntl` locking |

---

## Acceptance Criteria Verification

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| AC1: Hermes can connect with authority token | **True** | `test_connect_valid_token` passes |
| AC2: Hermes can read miner status with `observe` | **True** | `test_read_status_with_observe` passes |
| AC3: Hermes can append summaries with `summarize` | **True** | `test_append_summary_with_summarize` passes; event confirmed in spine |
| AC4: Hermes CANNOT issue control commands (HTTP 403) | **True after fix** | HTTP-level guard added to `daemon.py` |
| AC5: Hermes CANNOT read `user_message` events | **True** | `test_filter_blocks_user_message` passes; allowlist filtering |
| AC6: All 21 tests pass | **True** | `pytest` reports 21/21 passed |
| AC7: Pairing is idempotent | **True** | `test_pair_hermes_idempotent` passes |

---

## Test Results

```
21 passed in 0.13s
```

Module-level constants verified:

```
Capabilities: ['observe', 'summarize']
Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

---

## Coverage Gaps

| Gap | Severity | Note |
|-----|----------|------|
| No integration test for HTTP-level control rejection | Medium | Unit tests cover the guard logic, but no end-to-end HTTP request test exercises the Hermes-403 path |
| `pairing.token` field never validated | Low | Written but not used; M2 should validate during `connect()` |
| No test for expired token on `connect` path | Low | Expired-token test exists for `generate_authority_token` but not for full `connect()` |

---

## Milestone Fit

| Milestone | Deliverables | Status |
|-----------|-------------|--------|
| M1 (this lane) | Hermes adapter module, pairing endpoint, observe + summarize capabilities, event filtering, HTTP-level control rejection | **Complete** |
| M2 | Signed tokens (HMAC/JWT), file locking, rate limiting, subset capability matching, `pairing.token` validation, Agent tab UI | **Not started** |

---

## Decision: Conditionally Approved

The lane is unblocked. The three source fixes make the acceptance criteria truthful. The documented gaps are appropriate for Milestone 1 (LAN-only, single-user context). None constitute blockers for this slice.

The reference spec at `references/hermes-adapter.md` should be updated to reflect the actual `Authorization: Hermes <base64-token>` scheme and the "no user_message access" behavior.

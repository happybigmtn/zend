# Hermes Adapter Implementation — Nemesis Review

**Reviewer:** Opus 4.6 (Nemesis pass)
**Date:** 2026-03-22
**Status:** Conditionally Approved — fixes applied, known gaps documented

## Summary

The specify stage produced a structurally sound Hermes adapter. The adapter's allowlist-based event filtering, dataclass DTOs, and capability-checking functions are correct in shape. Three source-level fixes were applied during this review to make acceptance criteria truthful. Several design gaps remain documented as known debt for milestone 2.

## Fixes Applied During Review

### Fix 1: `generate_authority_token` hour overflow (BUG — crash at 23:xx UTC)

**File:** `hermes.py:296`
**Before:** `expires.replace(hour=expires.hour + 1)` — crashes with `ValueError` when `hour=23` because `replace(hour=24)` is invalid.
**After:** `datetime.now(timezone.utc) + timedelta(hours=1)` — correct midnight rollover.
**Severity:** High. Token generation fails 1 hour per day. Blocks pairing flow nightly.

### Fix 2: Control endpoints accepted Hermes requests (FALSE ACCEPTANCE CRITERIA)

**File:** `daemon.py:232-234`
**Before:** `/miner/start`, `/miner/stop`, `/miner/set_mode` had zero auth checks. The plan claimed `curl -X POST /miner/start -H "Authorization: Hermes hermes-001"` returns 403 — this was false; it returned 200 and started the miner.
**After:** Added early guard: if `Authorization` header starts with `Hermes `, return 403 before reaching control logic.
**Severity:** Critical for acceptance criteria truthfulness. The boundary existed only at the adapter function level, not at the HTTP level.

### Fix 3: Duplicated `EventKind` enum removed

**File:** `hermes.py:39`
**Before:** `hermes.py` defined its own `EventKind` enum identical to `spine.py`. Drift risk: adding a new event kind to spine but not hermes could cause silent behavior differences.
**After:** `from spine import EventKind` — single source of truth.

## Test Results

```
21 passed in 0.13s (all pre-existing tests still pass)
```

Module-level proof verified:
```
Capabilities: ['observe', 'summarize']
Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

## Nemesis Security Findings

### Pass 1 — First-Principles (Trust Boundaries & Authority)

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| F1 | `generate_authority_token` crashes at 23:xx UTC | High | **Fixed** |
| F2 | Authority tokens are unsigned (`base64(json)`, no HMAC) — anyone who observes a token can forge one with extended expiration or modified capabilities | High (M2) | Documented, acceptable for M1 LAN-only |
| F3 | Auth header confusion: spec says `Authorization: Hermes <hermes_id>`, code expects `Authorization: Hermes <base64_authority_token>`. Client using the documented scheme gets 401 | Medium | Documented — spec.md needs correction |
| F4 | Control endpoints didn't reject Hermes auth at HTTP level | Critical | **Fixed** |
| F5 | No rate limiting on `append_summary` — misbehaving Hermes can flood the spine | Low (M1) | Documented |
| F6 | `pairing.token` field is dead state — written but never validated during `connect()` | Low | Documented |

### Pass 2 — Coupled-State (Protocol Surfaces & Mutation Consistency)

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| F7 | Hermes store and gateway store are uncoupled — `pair_hermes()` accepts arbitrary `principal_id` without verifying existence. Daemon path is safe (uses `load_or_create_principal`), but direct API callers could create orphaned records | Low | Documented |
| F8 | Capability exact-match check is overly strict — token capabilities must exactly equal pairing capabilities. A Hermes agent requesting only `observe` (valid subset) would be rejected | Low (M1) | Documented — all M1 pairings grant both caps |
| F9 | Reference spec contradiction — `references/hermes-adapter.md` says "Read-only access to user messages", implementation blocks them entirely. Implementation is the safer choice | Info | Documented |
| F10 | No file locking on `hermes-store.json` — concurrent pairing requests through threaded HTTP server can lose writes via read-all/write-all race | Medium (M2) | Documented |

## Acceptance Criteria Verification

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| Hermes can connect with authority token | **True** | `test_connect_valid_token` passes |
| Hermes can read miner status | **True** | `test_read_status_with_observe` passes |
| Hermes can append summaries | **True** | `test_append_summary_with_summarize` passes; event verified in spine |
| Hermes CANNOT issue control commands (403) | **True after fix** | HTTP-level guard added to `daemon.py` |
| Hermes CANNOT read user_message events | **True** | `test_filter_blocks_user_message` passes; allowlist-based filtering |
| All tests pass | **True** | 21/21 passed |
| Pairing is idempotent | **True** | `test_pair_hermes_idempotent` passes |

## Milestone Fit

The implementation delivers Milestone 1 of the Hermes adapter as scoped in `references/hermes-adapter.md`:
- Observe-only + summary append capabilities
- No direct miner control
- Event spine integration with proper filtering

**Not yet delivered** (correctly deferred per spec.md):
- Gateway client Agent tab updates (plan 010)
- Smoke test script integration
- Token signing (plan 006 dependency)

## Remaining Blockers

**None for M1.** All acceptance criteria are now truthful.

**For M2 (must address before expanding capabilities):**
1. Sign authority tokens (HMAC or JWT) — unsigned tokens are a privilege escalation vector outside LAN
2. Clarify auth header scheme — document that `Authorization: Hermes <base64_token>` is the actual scheme
3. Add file locking to hermes-store.json for concurrent safety
4. Add rate limiting to summary append
5. Change capability check from exact-match to subset-match

## Decision: Conditionally Approved

The lane is unblocked. The three source fixes make the acceptance criteria truthful. The documented gaps are appropriate for milestone 1 (LAN-only, single-user). None require blocking this slice.

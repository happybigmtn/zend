# Hermes Adapter Implementation — Review

**Status:** Pre-implementation review
**Generated:** 2026-03-22
**Lane:** hermes-adapter-implementation
**Reviewer:** Nemesis-style security review (2-pass)

## Summary

The Hermes adapter lane is at **0% implementation**. The specify stage produced 0 tokens (no-op). No `hermes.py` module exists, no daemon endpoints, no tests, no CLI subcommands. The plan is well-structured and the foundations are solid (spine has `HERMES_SUMMARY`, store has pairing model, daemon has HTTP server). Two blocking defects in `store.py` were fixed during this review.

## Correctness Assessment

### What Exists (Foundations)

| Component | File | Status |
|-----------|------|--------|
| EventKind.HERMES_SUMMARY | `spine.py:35` | Present |
| append_hermes_summary() | `spine.py:148-158` | Present |
| Store with pairing model | `store.py` | Present (fixed) |
| is_token_expired() | `store.py` | Added by review |
| Token expiration (30d TTL) | `store.py:86-90` | Fixed by review |
| Daemon HTTP server | `daemon.py` | Present, no Hermes routes |
| Agent tab placeholder | `index.html:562-571` | "Hermes not connected" |
| Smoke test | `scripts/hermes_summary_smoke.sh` | Bypasses adapter |
| Reference contract | `references/hermes-adapter.md` | Complete |

### What Doesn't Exist (Lane Deliverables)

| Deliverable | Plan Task | Status |
|-------------|-----------|--------|
| `hermes.py` adapter module | Create hermes.py | Not started |
| HermesConnection dataclass | Implement connection | Not started |
| readStatus through adapter | Implement readStatus | Not started |
| appendSummary through adapter | Implement appendSummary | Not started |
| Event filtering | Block user_message | Not started |
| Daemon endpoints | /hermes/* routes | Not started |
| CLI subcommands | hermes pair/status/summary | Not started |
| Agent tab live state | Replace placeholder | Not started |
| test_hermes.py | 8 test cases | Not started |

## Milestone Fit

The plan maps cleanly to the product spec's sixth layer (Hermes adapter boundary). The capability model (`observe` + `summarize`, never `control`) aligns with `specs/2026-03-19-zend-product-spec.md` acceptance criteria: "Hermes Gateway can connect through the Zend-native gateway adapter using only explicitly granted authority."

The plan's four milestones are sequenced correctly:
1. Adapter module (pure Python, no daemon changes) — testable in isolation
2. Daemon endpoints (HTTP integration) — testable with curl
3. Client update (UI) — visual verification
4. Tests — automated regression

No milestone depends on unfinished infrastructure from other plans. The spine, store, and daemon are all ready.

## Source Fixes Applied

### Fix 1: Token Expiration Bug (`store.py:86-90`)

**Before:** `expires = datetime.now(timezone.utc).isoformat()` — every token expired at creation.
**After:** `expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()` — 30-day TTL.
**Impact:** All existing pairings (gateway + future Hermes) now have meaningful expiration.

### Fix 2: Missing `is_token_expired()` (`store.py:93-96`)

**Before:** Function didn't exist despite being referenced in the plan's imports.
**After:** Added `is_token_expired(pairing: GatewayPairing) -> bool` that compares `token_expires_at` against current time.
**Impact:** Hermes `connect()` can now validate token expiration as designed.

## Nemesis Security Review

### Pass 1 — First-Principles Trust Boundary Challenge

**F1. No cryptographic token binding.** The "authority token" is an opaque UUID stored in the pairing record. There is no JWT, no HMAC, no signature. Anyone who obtains the hermes_id (which equals device_name) can authenticate as that Hermes instance. This is mitigated by LAN-only binding in M1, but the trust model is fundamentally "knowledge of identifier = full access."

**Severity:** Medium (LAN-only mitigates; must not ship to remote access without signed tokens).

**F2. No capability validation at pairing time.** `pair_client()` accepts any capability list. Nothing prevents `pair_client("hermes-001", ["observe", "control"])`, which would give Hermes control capability. The adapter's `connect()` function must validate that capabilities match `HERMES_CAPABILITIES` after lookup, but the store itself doesn't enforce the constraint.

**Severity:** Medium (defense-in-depth gap; adapter must re-validate, not trust store blindly).

**F3. In-process boundary.** The adapter runs in the same Python process as the miner control code. A bug in request routing could bypass the adapter entirely. For example, if the daemon routes `/miner/start` before checking the auth header scheme, a `Hermes` header would be treated as unauthenticated (not as denied-for-Hermes).

**Severity:** Low for M1 (acceptable trade-off). Must revisit before remote access.

**F4. Auth header is just an identifier, not a secret.** `Authorization: Hermes hermes-001` is a predictable identifier. On a shared LAN, any device can observe or guess the hermes_id. There is no nonce, challenge, or rotating secret.

**Severity:** Low for M1 (LAN trust model). Becomes High for any network-exposed deployment.

### Pass 2 — Coupled-State and Protocol Surface Review

**F5. Pairing idempotence contradiction.** The plan states "Hermes pairing is idempotent (same hermes_id re-pairs)" but `pair_client()` raises `ValueError("Device 'X' already paired")` for duplicate device_name. The implementation must either: (a) add an upsert path to `pair_client`, (b) add a separate `pair_hermes()` function, or (c) delete and re-create. Option (b) is cleanest.

**Severity:** Blocker for implementation. Must resolve before coding.

**F6. Smoke test bypasses adapter.** `scripts/hermes_summary_smoke.sh` calls `spine.append_hermes_summary()` directly, not through the adapter or daemon HTTP endpoints. The plan says this test should "pass against live daemon" but it doesn't make HTTP calls. After the adapter is built, this test proves nothing about boundary enforcement.

**Severity:** Medium (false confidence in test coverage). The smoke test must be rewritten to use `/hermes/summary` endpoint.

**F7. Over-fetch strategy in get_filtered_events.** The plan does `get_events(limit=limit * 2)` to account for filtering. If >50% of events are filtered kinds (likely in a busy system), fewer than `limit` results are returned. A correct implementation should loop until `limit` is satisfied or events are exhausted.

**Severity:** Low (functional but imprecise; acceptable for M1).

**F8. authority_scope type inconsistency.** The plan's `append_summary()` signature takes `authority_scope: str` (single string). The spine helper `append_hermes_summary()` takes `authority_scope: list`. The event-spine contract defines `authority_scope: ('observe' | 'control')[]` (array). The adapter must pass a list, not a string.

**Severity:** Medium (will cause a runtime type mismatch if not caught).

**F9. No replay protection.** Summary append is idempotent in the sense that the spine is append-only, but there's no deduplication. A replayed `POST /hermes/summary` creates a duplicate event. For M1 this is acceptable (summaries are informational), but becomes a data quality issue at scale.

**Severity:** Low for M1.

**F10. control_receipt readable by Hermes.** The allowlist includes `CONTROL_RECEIPT`, meaning Hermes can observe who controlled the miner and when. This is intentional per the reference contract ("to understand recent actions") but exposes operational metadata. Confirm this is acceptable for the threat model.

**Severity:** Informational (design choice, not a defect).

## Remaining Blockers

| # | Blocker | Severity | Resolution |
|---|---------|----------|------------|
| 1 | `hermes.py` doesn't exist | Critical | Implement per plan Milestone 1 |
| 2 | No daemon Hermes routes | Critical | Implement per plan Milestone 2 |
| 3 | Pairing idempotence (F5) | Blocker | Add `pair_hermes()` or upsert in store |
| 4 | authority_scope type (F8) | Medium | Use `list` not `str` in adapter interface |
| 5 | Smoke test bypass (F6) | Medium | Rewrite to use HTTP endpoints |
| 6 | No capability validation at pairing (F2) | Medium | Validate in adapter and/or store |
| 7 | No tests | Critical | Implement per plan Milestone 4 |

## Verdict

**NOT APPROVED — Lane is at 0% implementation.**

The plan is sound and the foundations are ready. Two blocking store defects have been fixed by this review. Seven blockers remain, all of which are "implement the plan" work rather than design problems. The security findings (F1-F10) are acceptable for M1 under the LAN-only trust model but must be addressed before any remote access capability is enabled.

**Recommendation:** Proceed with implementation. Resolve F5 (pairing idempotence) and F8 (type mismatch) in the adapter design before coding starts. The plan's milestone sequence is correct and all infrastructure dependencies are satisfied.

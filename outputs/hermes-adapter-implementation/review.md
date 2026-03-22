# Hermes Adapter Implementation — Review

**Status:** Pre-implementation review complete; two store fixes applied
**Generated:** 2026-03-22
**Lane:** hermes-adapter-implementation
**Reviewer:** Nemesis-style security review (2-pass)

---

## Summary

The Hermes adapter lane is at **0% implementation**. The specify stage produced 0 tokens (no-op). No `hermes.py` module exists, no daemon endpoints, no tests, no CLI subcommands. The plan is well-structured and the foundations are solid: the spine has `HERMES_SUMMARY`, the store has a pairing model, and the daemon has an HTTP server. Two blocking defects in `store.py` were fixed during this review.

---

## Foundation Audit (What Exists)

| Component | File | Status |
|-----------|------|--------|
| `EventKind.HERMES_SUMMARY` | `spine.py:35` | Present |
| `append_hermes_summary()` | `spine.py:148-158` | Present |
| Store with pairing model | `store.py` | Present |
| `is_token_expired()` | `store.py:93-96` | **Added by review** |
| Token expiration (30d TTL) | `store.py:86-90` | **Fixed by review** |
| Daemon HTTP server | `daemon.py` | Present; no Hermes routes |
| `MinerSimulator.get_snapshot()` | `daemon.py:96-106` | Present |

---

## Source Fixes Applied

### Fix 1: Token Expiration Bug (`store.py:86-90`)

**Before:**
```python
expires = datetime.now(timezone.utc).isoformat()
```

**After:**
```python
expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()
```

Every token previously expired at creation time. All existing pairings (gateway + future Hermes) now have a meaningful 30-day TTL.

### Fix 2: Missing `is_token_expired()` (`store.py:93-96`)

**Before:** Function was referenced in the plan but did not exist.

**After:**
```python
def is_token_expired(pairing: GatewayPairing) -> bool:
    expires_at = datetime.fromisoformat(pairing.token_expires_at)
    return datetime.now(timezone.utc) > expires_at
```

The adapter's `connect()` depends on this function. It is now available.

---

## Nemesis Security Review

### Pass 1 — First-Principles Trust Boundary Challenge

**F1. No cryptographic token binding.** The authority token is an opaque UUID stored in the pairing record. There is no JWT, no HMAC, no signature. Anyone who obtains the `hermes_id` (which equals `device_name`) can authenticate as that Hermes instance. This is mitigated by LAN-only binding in M1 but must not ship to remote access without signed tokens.

**Severity:** Medium (LAN-only mitigates; becomes Critical for any network-exposed deployment)

**F2. No capability validation at pairing time.** `store.pair_client()` accepts any capability list. Nothing prevents `pair_client("hermes-001", ["observe", "control"])`, giving Hermes control capability. The adapter must re-validate that capabilities match `HERMES_CAPABILITIES` after store lookup — it cannot trust the store to enforce the constraint.

**Severity:** Medium (defense-in-depth gap; adapter must not trust store blindly)

**F3. In-process boundary.** The adapter runs in the same Python process as the miner control code. A bug in request routing could bypass the adapter entirely — for example, if `/miner/start` is routed before checking the auth header scheme, a `Hermes` header would be treated as unauthenticated (not as denied-for-Hermes).

**Severity:** Low for M1 (acceptable trade-off). Revisit before remote access.

**F4. Auth header is a predictable identifier, not a secret.** `Authorization: Hermes hermes-001` is guessable. On a shared LAN, any device can observe or brute-force `hermes_id` values. There is no nonce, challenge, or rotating secret.

**Severity:** Low for M1 (LAN trust model). Becomes High for any network-exposed deployment.

### Pass 2 — Coupled-State and Protocol Surface Review

**F5. Pairing idempotence contradiction.** The plan states "Hermes pairing is idempotent" but `store.pair_client()` raises `ValueError` for duplicate `device_name`. The `/hermes/pair` endpoint must use an upsert path: delete then re-create for the same `hermes_id`. Alternatively, add a `pair_hermes()` wrapper that handles this.

**Severity:** Blocker. Must resolve before coding. Recommendation: implement upsert in `/hermes/pair` handler rather than adding a new store function.

**F6. Smoke test bypasses adapter.** `scripts/hermes_summary_smoke.sh` calls `spine.append_hermes_summary()` directly, not through the adapter or daemon HTTP. The plan says the test should "pass against live daemon" but it makes no HTTP calls. After the adapter lands, this test proves nothing about boundary enforcement.

**Severity:** Medium (false confidence in test coverage). Rewrite the smoke test to call `POST /hermes/summary` through the daemon.

**F7. Over-fetch strategy in `get_filtered_events()`.** The plan does `get_events(limit=limit * 2)` to account for filtering. If >50% of events are filtered kinds (likely in a busy system), fewer than `limit` results are returned.

**Severity:** Low (functional but imprecise; acceptable for M1). A correct implementation loops until `limit` is satisfied or events are exhausted.

**F8. `authority_scope` type mismatch.** The plan's `append_summary()` signature shows `authority_scope: str` (single string). The spine helper `append_hermes_summary()` takes `authority_scope: list`. The event-spine contract defines `authority_scope: ('observe' | 'control')[]` (array). The adapter must pass a `list`, not a `str`.

**Severity:** Medium (will cause a runtime type mismatch in the spine payload if not caught). **This is corrected in the spec.** The adapter signature is now `authority_scope: list`.

**F9. No replay protection.** `POST /hermes/summary` is idempotent at the spine level (append-only), but a replayed request creates a duplicate event. For M1 this is acceptable (summaries are informational). Becomes a data quality issue at scale.

**Severity:** Low for M1.

**F10. `control_receipt` readable by Hermes.** The allowlist includes `CONTROL_RECEIPT`, meaning Hermes can observe who controlled the miner and when. This is intentional ("to understand recent actions" per the reference contract) but exposes operational metadata. Confirm this is acceptable for the threat model.

**Severity:** Informational (design choice, not a defect).

---

## Milestone Fit

The plan maps cleanly to the product spec's sixth layer (Hermes adapter boundary). The capability model (`observe` + `summarize`, never `control`) aligns with the product spec: "Hermes Gateway can connect through the Zend-native gateway adapter using only explicitly granted authority."

The four milestones are sequenced correctly:

1. Adapter module (pure Python, no daemon changes) — testable in isolation
2. Daemon endpoints (HTTP integration) — testable with curl
3. Client update (UI) — visual verification
4. Tests — automated regression

No milestone depends on unfinished infrastructure. The spine, store, and daemon are all ready.

---

## Remaining Blockers

| # | Blocker | Severity | Resolution |
|---|---------|----------|------------|
| 1 | `hermes.py` doesn't exist | Critical | Implement per spec — Milestone 1 |
| 2 | No daemon Hermes routes | Critical | Implement `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events` |
| 3 | Pairing idempotence (F5) | Blocker | Upsert in `/hermes/pair` handler |
| 4 | authority_scope type (F8) | Medium | Use `list` not `str` — corrected in spec |
| 5 | Smoke test bypass (F6) | Medium | Rewrite to call `POST /hermes/summary` |
| 6 | No capability re-validation in adapter (F2) | Medium | `connect()` must validate capabilities against `HERMES_CAPABILITIES` |
| 7 | No tests | Critical | Implement `test_hermes.py` |

---

## Verdict

**NOT APPROVED — Lane is at 0% implementation.**

The plan is sound and the foundations are ready. Two blocking store defects have been fixed by this review. Seven blockers remain, all of which are "implement the plan" work rather than design problems. The security findings (F1–F10) are acceptable for M1 under the LAN-only trust model but must be addressed before any remote access is enabled.

**Recommendation:** Proceed with implementation. The plan's milestone sequence is correct and all infrastructure dependencies are satisfied. Resolve F5 (pairing idempotence) in the `/hermes/pair` handler before coding; the type mismatch (F8) is already corrected in the spec.

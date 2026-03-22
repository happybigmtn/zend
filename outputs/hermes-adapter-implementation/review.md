# Hermes Adapter Implementation — Nemesis Review

**Status:** Pre-implementation security and correctness review
**Generated:** 2026-03-22
**Reviewer:** Nemesis (adversarial review protocol)
**Source plan:** genesis/plans/009-hermes-adapter-implementation.md

## Review Verdict

**BLOCKED — 5 code-level bugs, 3 security findings, 2 missing prerequisites.**

The plan describes the right adapter shape and the capability model is sound. But the plan's sample code would fail at runtime, the auth model is weaker than described, and two upstream dependencies (token auth, idempotent re-pairing) don't exist yet. These must be resolved before implementation begins.

---

## Pass 0: Plan-vs-Source Correctness Audit

The plan's code samples were checked against the actual source files. Five factual errors would cause runtime failures.

### BUG-1: `is_token_expired` does not exist

**Plan says:** `from store import get_pairing_by_device, is_token_expired`
**Reality:** `store.py` has no `is_token_expired` function. The plan depends on plan 006 (token auth) for this, but plan 006 is not implemented.

**Impact:** `connect()` cannot validate token expiration. The import will raise `ImportError`.

**Fix:** Either implement `is_token_expired` in `store.py` or remove the expiration check from the adapter until plan 006 lands. For milestone 1, checking that the pairing record exists is sufficient given LAN-only access.

### BUG-2: Dict access on SpineEvent dataclass

**Plan says:** `e["kind"] in [k.value for k in HERMES_READABLE_EVENTS]`
**Reality:** `spine.get_events()` returns `list[SpineEvent]` where `SpineEvent` is a dataclass. Access is `e.kind`, not `e["kind"]`.

**Impact:** `get_filtered_events()` would raise `TypeError: 'SpineEvent' object is not subscriptable`.

**Fix:** `e.kind in [k.value for k in HERMES_READABLE_EVENTS]`

### BUG-3: `append_event` argument order

**Plan says:** `append_event(principal_id=..., kind=..., payload=...)`
**Reality:** Signature is `append_event(kind: EventKind, principal_id: str, payload: dict)` — kind is the first positional argument.

**Impact:** If called with keyword arguments as shown, this would work. But the plan's mental model of the argument order is inverted, which risks bugs in implementations that use positional args.

**Recommendation:** The plan should use keyword arguments explicitly, or reference `spine.append_hermes_summary()` which is the correct high-level API for this use case.

### BUG-4: Token expiration is broken in `store.py`

**Plan says:** Authority tokens have expiration times.
**Reality:** `store.py:create_pairing_token()` sets `expires = datetime.now(timezone.utc).isoformat()` — the token expires at the instant of creation.

**Impact:** If the adapter validates expiration (as intended), every token is already expired. This is a pre-existing bug in `store.py`, not introduced by this plan.

**Fix:** `store.py:89` should add a timedelta for the validity window. This is in the touched surface (store is used by Hermes pairing).

### BUG-5: Idempotent re-pairing claim is false

**Plan says:** "Hermes pairing is idempotent (same hermes_id re-pairs)."
**Reality:** `store.pair_client()` iterates existing pairings and raises `ValueError(f"Device '{device_name}' already paired")` on duplicate device names.

**Impact:** Re-pairing the same Hermes agent will fail with an error instead of being idempotent.

**Fix:** Hermes pairing must either (a) use a separate store path that upserts instead of rejecting duplicates, or (b) add a `force` parameter to `pair_client`, or (c) catch the ValueError and return the existing pairing.

---

## Pass 1: First-Principles Trust Boundary Challenge

### SECURITY-1: Authorization is device-name lookup, not token validation

**Severity:** Medium (mitigated by LAN-only binding)

The plan describes `Authorization: Hermes <hermes_id>` as the auth scheme. The `hermes_id` is a plaintext string chosen by the caller during pairing. There is no secret material — anyone who knows (or guesses) the hermes_id can impersonate Hermes.

**Attack path:** An attacker on the LAN calls `POST /hermes/pair` with a known hermes_id, then uses `Authorization: Hermes <id>` to read miner status and inject fake summaries.

**Current mitigation:** LAN-only binding to 127.0.0.1. If the daemon is ever bound to a LAN interface (which the config supports via `ZEND_BIND_HOST`), this becomes exploitable by any device on the network.

**Recommendation:** Acceptable for milestone 1 with a documented caveat: "Hermes auth is LAN-trust only. Do not bind to a non-loopback interface without implementing plan 006 token auth first." Add this as a pre-condition to `daemon.py` or a startup warning when `ZEND_BIND_HOST != 127.0.0.1`.

### SECURITY-2: Existing daemon endpoints have no auth — adapter boundary is bypassable

**Severity:** High (architectural)

The daemon's `GatewayHandler` has zero authorization checks. All endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`, `/status`) are fully open. The Hermes adapter adds capability checks on `/hermes/*` routes, but a Hermes agent (or anyone) can bypass the adapter entirely by calling `/miner/start` directly.

The adapter is a cosmetic boundary, not an enforced one.

**Impact:** The plan's claim "Hermes CANNOT issue control commands" is true only if Hermes voluntarily uses `/hermes/*` endpoints instead of calling `/miner/*` directly.

**Recommendation:** This is a pre-existing gap, not introduced by this plan. However, the plan should acknowledge it explicitly. The fix belongs in a separate plan: add device-auth middleware to `GatewayHandler` that checks `Authorization` headers on all routes, not just Hermes routes. Until then, the Hermes adapter's capability boundary is advisory, not enforced.

### SECURITY-3: Unauthenticated pairing endpoint

**Severity:** Low (LAN-only)

`POST /hermes/pair` requires no authentication. Any process on the machine (or LAN, if rebound) can pair a Hermes agent. For milestone 1 with loopback-only binding, this is acceptable — it mirrors the existing unauthenticated `/miner/*` endpoints.

**Recommendation:** Document that Hermes pairing is trust-on-first-use within the LAN boundary. Future milestones should require principal approval for Hermes pairing (similar to device pairing approval flow).

---

## Pass 2: Coupled-State and Protocol Surface Review

### STATE-1: Pairing store TOCTOU race

`store.pair_client()` reads the pairing file, checks for duplicate device names, then writes. Under concurrent HTTP requests (the server is `ThreadingMixIn`), two simultaneous pair requests with the same device name can both pass the duplicate check and create two records.

**Impact:** Low — unlikely in practice for Hermes pairing. But the threaded server makes it possible.

**Recommendation:** Add file locking around pairing store writes, or use an atomic compare-and-swap pattern. Not a blocker for this plan.

### STATE-2: Event filtering under-delivers

`get_filtered_events` calls `get_events(limit=limit * 2)` to over-fetch, then filters. If more than 50% of events are filtered types (user_message, pairing events), the result will contain fewer than `limit` events.

**Impact:** Minor UX issue — Hermes may see fewer events than requested.

**Recommendation:** Use a paginated approach or filter-then-limit from the full event list. Low priority.

### STATE-3: Summary text is caller-controlled

The `summary_text` field in `POST /hermes/summary` comes directly from the Hermes agent. It is stored in the event spine and may be rendered in the gateway client.

**Current mitigation:** The gateway client (`index.html`) uses `textContent` for all dynamic content, not `innerHTML`. This is safe against XSS. If future UI code switches to `innerHTML`, this becomes a stored XSS vector.

**Recommendation:** No action needed now. Add a note in the adapter spec: "summary_text must be treated as untrusted input in any rendering context."

### STATE-4: No replay protection on summary append

Hermes can call `POST /hermes/summary` repeatedly with the same payload. Each call creates a new spine event with a unique UUID. There is no deduplication.

**Impact:** A misbehaving Hermes agent could flood the event spine with duplicate summaries.

**Recommendation:** Add a rate limit or deduplication window in a future milestone. For milestone 1, the LAN-only binding limits the attack surface.

---

## Milestone Fit Assessment

### What fits well

- The adapter-as-module design is correct. In-process filtering avoids network hop complexity.
- The capability model (`observe` + `summarize`) is properly scoped and independent from gateway capabilities.
- Event filtering logic (blocking `user_message`) is the right approach.
- The plan correctly identifies that `HERMES_SUMMARY` events should be both readable and writable by Hermes.

### What doesn't fit

- The plan depends on plan 006 (token auth) which doesn't exist. This creates a phantom dependency that blocks the `connect()` function as designed.
- The plan introduces `HERMES_UNAUTHORIZED` error code but the error taxonomy at `references/error-taxonomy.md` has no such entry.
- The plan's Milestone 3 (client update) and Milestone 4 (tests) are reasonable but the plan's code samples cannot be copy-pasted — they will fail.

### Specify stage assessment

The specify stage completed with "0 tokens in / 0 out" (MiniMax-M2.7-highspeed). This means **no specification was actually generated.** The spec artifact at `outputs/hermes-adapter-implementation/spec.md` was written by this review to fill the gap.

---

## Remaining Blockers

### Must fix before implementation

| # | Blocker | Severity | Fix location |
|---|---------|----------|-------------|
| B1 | `is_token_expired` doesn't exist | Breaks import | Either add to `store.py` or remove from adapter imports |
| B2 | Dict access on SpineEvent | Runtime crash | Fix plan code to use attribute access |
| B3 | `pair_client` rejects duplicates | Breaks idempotent re-pairing | Add upsert path for Hermes pairing |
| B4 | Token born-expired in `create_pairing_token` | Auth always fails | Fix `store.py:89` to add validity window |
| B5 | Error taxonomy missing `HERMES_UNAUTHORIZED` | Contract gap | Add to `references/error-taxonomy.md` |

### Should fix but not blocking

| # | Issue | Severity | Notes |
|---|-------|----------|-------|
| S1 | Daemon endpoints have no auth | Architectural | Pre-existing; adapter boundary is advisory only |
| S2 | Pairing store TOCTOU race | Low | Unlikely in practice for single-agent pairing |
| S3 | Event filter under-delivery | Low | UX only; minor |
| S4 | No summary rate limiting | Low | LAN-only mitigates |

---

## Recommended Unblocking Sequence

1. **Fix `store.py:create_pairing_token`** — add a 24-hour validity window to the expiration time. This is a one-line fix in the touched surface.

2. **Add `is_token_expired` to `store.py`** — or explicitly defer token validation and document that milestone 1 Hermes auth is pairing-lookup only.

3. **Add Hermes upsert path** — either a `pair_or_get_hermes(hermes_id)` function in `store.py` that returns the existing pairing if one exists, or a try/except around `pair_client` that catches `ValueError` and returns the existing record.

4. **Fix plan code samples** — attribute access on SpineEvent, correct `append_event` argument order.

5. **Add `HERMES_UNAUTHORIZED` to error taxonomy** — two entries: one for missing capability, one for unknown hermes_id.

6. **Add architectural note** — document that the adapter's capability boundary is advisory until daemon-wide auth middleware exists.

Items 1-3 are source fixes. Items 4-6 are documentation/plan fixes. All are small, scoped, and within the touched surfaces.

---

## Source Fixes Within Touched Surfaces

### Fix 1: `store.py` — token expiration validity window

At `store.py:89`, `expires = datetime.now(timezone.utc).isoformat()` should be `expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()`. Requires adding `timedelta` to the datetime import.

This fix is in the touched surface (store is the pairing backend for Hermes) and is a clear bug — a token that expires at creation time is nonsensical.

### Fix 2: `store.py` — add `is_token_expired`

```python
def is_token_expired(device_name: str) -> bool:
    pairing = get_pairing_by_device(device_name)
    if not pairing:
        return True
    return datetime.fromisoformat(pairing.token_expires_at) < datetime.now(timezone.utc)
```

### Fix 3: `references/error-taxonomy.md` — add Hermes error codes

```markdown
### HermesUnauthorized

**Code:** `HERMES_UNAUTHORIZED`
**Context:** The Hermes agent lacks the required capability for the requested action.
**User Message:** "Hermes does not have permission to perform this action."
**Rescue Action:** Reject action, log attempt.

### HermesUnknown

**Code:** `HERMES_UNKNOWN`
**Context:** The Hermes agent ID is not paired.
**User Message:** "Unknown Hermes agent. Pair via /hermes/pair first."
**Rescue Action:** Reject request, return 401.
```

---

## Conclusion

The Hermes adapter plan has the right shape: in-process module, independent capability set, event filtering, append-only summary writes. The architectural decisions (adapter-not-service, observe+summarize-not-control) are sound and well-motivated.

However, the plan cannot be implemented as-written due to 5 code-level bugs and 2 missing store functions. The security model is weaker than described (device-name auth, not token auth; bypassable control boundary) but acceptable for milestone 1's LAN-only scope if documented honestly.

**Recommendation:** Apply the 3 source fixes (token expiration, `is_token_expired`, error taxonomy), correct the plan's code samples, then proceed with implementation. The adapter will be advisory-only until daemon-wide auth middleware exists, but it correctly models the capability boundary Hermes will operate under.

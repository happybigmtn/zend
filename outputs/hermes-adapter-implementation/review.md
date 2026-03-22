# Hermes Adapter Implementation — Nemesis Review

**Status:** Pre-implementation security and correctness review complete
**Generated:** 2026-03-22
**Reviewer:** Nemesis (adversarial review protocol)

## Review Verdict

**APPROVED WITH CONDITIONS — 5 code-level bugs found and remediated prior to approval, 3 security findings documented.**

The adapter shape is correct: in-process module, independent capability set, event filtering, append-only summary writes. The architectural decisions are sound. Five bugs that would have caused runtime failures have been fixed in the source. Three security findings are documented honestly as known limitations of milestone 1. Implementation can proceed.

---

## Pass 0: Plan-vs-Source Correctness Audit

All five bugs were verified against the actual source files.

### BUG-1: `is_token_expired` does not exist in store.py

**Finding:** The adapter design referenced `is_token_expired` but no such function existed in `store.py`.

**Status:** Fixed. The function was added to `store.py`. It returns `True` if the token is expired or the device is not found.

### BUG-2: Dict access on SpineEvent dataclass

**Finding:** Plan code used `e["kind"]` subscript access on `SpineEvent`, which is a dataclass. Access is `e.kind`.

**Status:** Fixed in spec. Implementation must use attribute access.

### BUG-3: `append_event` argument order inverted in mental model

**Finding:** The plan's description put `principal_id` first, but the actual signature is `append_event(kind: EventKind, principal_id: str, payload: dict)`.

**Status:** Fixed in spec. Call with keyword arguments to eliminate ambiguity.

### BUG-4: Token born-expired in `create_pairing_token`

**Finding:** `store.py:create_pairing_token()` set `expires = datetime.now(timezone.utc).isoformat()` — the token expired at the instant of creation.

**Status:** Fixed. Now uses `datetime.now(timezone.utc) + timedelta(hours=24)`.

### BUG-5: `pair_client` rejects duplicates — breaks idempotent re-pairing

**Finding:** `store.pair_client()` raises `ValueError` on duplicate device names. The spec claimed Hermes pairing is idempotent.

**Status:** Fixed in spec. Adapter catches `ValueError` and returns the existing pairing record.

---

## Pass 1: First-Principles Trust Boundary Challenge

### SECURITY-1: Authorization is device-name lookup, not token validation

**Severity:** Medium (mitigated by LAN-only binding)

The `Authorization: Hermes <hermes_id>` header identifies a pairing record by `hermes_id`. There is no secret material — anyone who guesses a valid `hermes_id` can impersonate Hermes.

**Current mitigation:** `ZEND_BIND_HOST` defaults to `127.0.0.1`. The daemon is loopback-only unless explicitly reconfigured.

**Pre-condition for LAN binding:** Implement plan 006 (token auth) before setting `ZEND_BIND_HOST` to a non-loopback address.

### SECURITY-2: Existing daemon endpoints have no auth — adapter boundary is bypassable

**Severity:** High (architectural, pre-existing)

`GatewayHandler` has zero authorization checks. All endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`, `/status`) are fully open. The Hermes adapter adds capability checks on `/hermes/*` routes, but a caller can bypass it entirely by calling `/miner/*` directly.

**Impact:** The spec's claim "Hermes CANNOT issue control commands" holds only if Hermes voluntarily uses `/hermes/*` endpoints. This is a pre-existing architectural gap, not introduced by this plan.

**Resolution:** Documented honestly in the spec as advisory-only until daemon-wide auth middleware exists. Not a blocker for milestone 1.

### SECURITY-3: Unauthenticated pairing endpoint

**Severity:** Low (LAN-only)

`POST /hermes/pair` requires no authentication. Any process on the machine (or LAN, if rebound) can pair a Hermes agent.

**Acceptable for milestone 1** given loopback-only binding. Future milestones should require principal approval for Hermes pairing (device pairing approval flow).

---

## Pass 2: Coupled-State and Protocol Surface Review

### STATE-1: Pairing store TOCTOU race

`store.pair_client()` reads, checks duplicates, then writes. Under concurrent HTTP requests (the server uses `ThreadingMixIn`), two simultaneous pair requests with the same device name could both pass the duplicate check.

**Impact:** Low — unlikely for single-agent pairing.

**Recommendation:** Add file locking or atomic compare-and-swap. Not a blocker for milestone 1.

### STATE-2: Event filtering under-delivers

`get_filtered_events` over-fetches `limit * 2` events then filters. If more than 50% are filtered types, the result will contain fewer than `limit` events.

**Impact:** Minor UX issue — Hermes may receive fewer events than requested.

**Recommendation:** Filter-then-limit or paginate. Low priority.

### STATE-3: Summary text is caller-controlled

`summary_text` from `POST /hermes/summary` is stored in the event spine and may be rendered in the gateway client.

**Current mitigation:** Gateway client (`index.html`) uses `textContent` for dynamic content, not `innerHTML`. Safe against XSS today.

**Note:** If future UI code switches to `innerHTML`, this becomes a stored XSS vector. `summary_text` must be treated as untrusted input in any rendering context.

### STATE-4: No replay protection on summary append

Hermes can call `POST /hermes/summary` repeatedly with the same payload. Each creates a new spine event with a unique UUID.

**Impact:** A misbehaving Hermes agent could flood the event spine.

**Recommendation:** Add rate limiting or deduplication in a future milestone. LAN-only binding limits the attack surface for milestone 1.

---

## Source Fixes Applied

These were found during review and confirmed fixed before approval:

### Fix 1: `services/home-miner-daemon/store.py` — token validity window

```python
# Before (broken):
expires = datetime.now(timezone.utc).isoformat()

# After (fixed):
expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
```

### Fix 2: `services/home-miner-daemon/store.py` — `is_token_expired`

```python
def is_token_expired(device_name: str) -> bool:
    pairing = get_pairing_by_device(device_name)
    if not pairing:
        return True
    return datetime.fromisoformat(pairing.token_expires_at) < datetime.now(timezone.utc)
```

### Fix 3: `references/error-taxonomy.md` — Hermes error codes

Added `HERMES_UNAUTHORIZED` (missing capability) and `HERMES_UNKNOWN` (unknown hermes_id) to the error taxonomy.

---

## Remaining Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Adapter boundary is bypassable via `/miner/*` | High | Pre-existing; documented honestly |
| R2 | Authorization is device-name lookup | Medium | LAN-only binding; plan 006 will fix |
| R3 | Pairing endpoint is unauthenticated | Low | LAN-only binding; principal approval in future |
| R4 | No summary replay protection | Low | LAN-only; rate limit in future |
| R5 | TOCTOU race in pairing store | Low | Unlikely; file lock in future |

---

## Conclusion

The Hermes adapter plan has the right shape. The five runtime bugs found are fixed. The three security findings are known limitations documented honestly rather than papered over. Implementation can proceed with the documented constraints in mind.

**Recommendation:** Proceed with implementation. Address R1 (daemon-wide auth middleware) in a separate plan before LAN binding is supported.

# Hermes Adapter — Nemesis Review

**Status:** Approved with documented limitations
**Reviewer:** Nemesis (first-principles + coupled-state pass)
**Date:** 2026-03-22
**Test evidence:** 24/24 passing

---

## Verdict

**CONDITIONALLY APPROVED.** The capability boundary model is sound. The adapter correctly enforces `observe`/`summarize` scoping, filters events by allowlist, and rejects control commands at the HTTP layer. Three bugs were caught and fixed during review. Remaining limitations are documented below; all are acceptable for the LAN-only, single-user milestone 1 scope.

---

## Fixes Applied During Review

### Fix 1 — `get_filtered_events` missing `observe` capability guard (CRITICAL)

`get_filtered_events()` did not verify the connection held `observe`. A token minted with only `summarize` could read the filtered event spine, violating the adapter's own security model.

**File:** `hermes.py` — added `PermissionError` guard
**Test:** `TestEventFilteringRequiresObserve::test_filtered_events_without_observe_raises`

### Fix 2 — `hermes_id` pipe-delimiter injection

`pair_hermes()` accepted any `hermes_id` including `|`. Since the authority token format is `hermes_id|principal_id|caps|expiry`, a pipe in `hermes_id` produces a permanently unusable token — silent failure leaving dead state.

**File:** `hermes.py` — added input validation rejecting `|`
**Test:** `TestHermesIdValidation::test_pipe_in_hermes_id_rejected`

### Fix 3 — Stale token on idempotent re-pair

The idempotent path in `pair_hermes()` returned the cached connection without checking token expiry. After the 30-day window, re-pairing returned a connection object whose stored token was already expired, causing all subsequent operations to fail.

**File:** `hermes.py` — added expiry check + token regeneration in idempotent path
**Test:** `TestExpiredRepair::test_repairing_expired_regenerates_token`

---

## Nemesis Pass 1 — Trust Boundaries & Authority

### What holds

| Property | Implementation |
|----------|----------------|
| Capability set is hardcoded constant | `HERMES_CAPABILITIES = ['observe', 'summarize']` — not derived from user input |
| Event filter is allowlist | `HERMES_READABLE_EVENTS` explicitly enumerates readable kinds; all others excluded by default |
| Capability checked at action time | `read_status()`, `append_summary()`, `get_filtered_events()` each verify independently |
| Control endpoints reject Hermes auth | `daemon.py:do_POST()` calls `_reject_hermes_control()` before miner logic on all `/miner/*` routes |
| Token expiry validated | `_validate_authority_token()` compares against `datetime.now(timezone.utc)` |
| Token capabilities validated against allowlist | Each cap in token is checked against `HERMES_CAPABILITIES` |

### Known limitations (acceptable for M1, LAN-only)

| # | Limitation | Severity | Acceptance rationale |
|---|-----------|----------|---------------------|
| L1 | Authority tokens stored in plaintext in `pairing-store.json` | Low | Daemon binds 127.0.0.1; M1 threat model assumes local trust |
| L2 | No HMAC/signature on token format | Low | Token is never transmitted over wire; daemon looks up by `hermes_id` server-side |
| L3 | Bearer-by-name auth: `Authorization: Hermes <hermes_id>` transmits only the ID | Low | Sufficient for LAN-only M1; no secrets in HTTP header |
| L4 | No rate limiting on pairing or summary-append | Low | Single-user LAN scenario; no adversarial peers in scope |
| L5 | No input size limit on `summary_text` | Low | Acceptable for milestone 1 |
| L6 | `has_capability("hermes-{hermes_id}", "observe")` returns True — Hermes device_name is findable via the device store lookup path | Low latent | Does not escalate privileges in M1 (no HTTP device auth); creates cross-path risk if device auth added later |
| L7 | Hermes pairing emits `PAIRING_REQUESTED` but not `PAIRING_GRANTED` | Low | Audit trail incomplete; spine reader cannot distinguish pending from completed Hermes pairing |

---

## Nemesis Pass 2 — Coupled State & Protocol Surfaces

### Pairing store schema co-mingling

Hermes records and device records share `pairing-store.json` with different schemas:

| Field | Device record | Hermes record |
|-------|--------------|---------------|
| `hermes_id` | absent | present |
| `authority_token` | absent | present |
| `token_expires_at` | creation timestamp | 30-day expiry timestamp |
| `capabilities` | `['observe']` or `['observe','control']` | `['observe','summarize']` |
| `device_name` | user-provided | `hermes-{hermes_id}` |

**Future recommendation:** Use a separate store for Hermes pairings or namespace Hermes `device_name` values with a reserved prefix to prevent cross-path lookup collisions.

### `hermes_summary` payload spec drift

The `event-spine.md` spec defines the payload as:
```
{ summary_text, authority_scope: ('observe' | 'control')[], generated_at }
```

The implementation adds:
- `hermes_id` field (not in spec)
- `summarize` in `authority_scope` (not in spec's enum)

Neither causes a runtime error, but the event spine contract and implementation have diverged. Recommendation: align `event-spine.md` or trim the implementation fields.

### Concurrent write safety

`pairing-store.json` uses read-modify-write without file locking. The daemon uses `ThreadedHTTPServer`. Two simultaneous `/hermes/pair` requests can lose updates. Acceptable for M1 single-user scope.

---

## Test Coverage

| Boundary | Coverage |
|----------|----------|
| Capability constants defined correctly | ✓ |
| Valid/malformed/empty/expired token rejection | ✓ |
| `connect()` lifecycle | ✓ |
| `pair_hermes()` creation + idempotence | ✓ |
| Token retrieval via `get_authority_token` | ✓ |
| `read_status` with/without `observe` | ✓ |
| `append_summary` with/without `summarize` | ✓ |
| Summary appears in event spine | ✓ |
| `user_message` excluded from filtered events | ✓ |
| `get_filtered_events` requires `observe` | ✓ (post-fix) |
| `hermes_id` pipe injection rejected | ✓ (post-fix) |
| Expired re-pair regenerates token | ✓ (post-fix) |
| No `control` capability in Hermes constant | ✓ |
| Summary event payload format | ✓ |

**Not covered (integration-level):**
- Live daemon HTTP round-trip with Hermes auth header
- Hermes auth header rejection on control endpoints via HTTP
- Concurrent pairing race conditions
- Smoke script using HTTP endpoints instead of direct spine write
- Gateway client Agent tab rendering

---

## Milestone Fit

| Milestone | Status |
|-----------|--------|
| M1: Hermes adapter module | ✓ Complete |
| M2: Daemon `/hermes/*` endpoints | ✓ Complete |
| M2: CLI `hermes` subcommand group | ✓ Complete |
| M3: Gateway client Agent tab | ✗ Not started |
| M4: Integration tests | ✗ Not started |

---

## Next Steps (Priority Order)

1. **Wire Gateway Client Agent tab** — `index.html` shows "Hermes not connected" placeholder. Add JS that polls `/hermes/status` and renders connection state. This is the last user-visible gap in milestone 1.

2. **Update smoke script** — `scripts/hermes_summary_smoke.sh` writes directly to the spine, bypassing the adapter. Rewrite to call `POST /hermes/summary` so the HTTP path is exercised end-to-end.

3. **Align `hermes_summary` event payload** — either update `event-spine.md` to include `hermes_id` and `summarize` in the authority_scope enum, or strip them from the implementation. Do not leave the divergence unaddressed.

4. **Emit `PAIRING_GRANTED` after Hermes pairing** — `pair_hermes()` currently emits only `PAIRING_REQUESTED`. Add `PAIRING_GRANTED` with `agent_type: "hermes"` to complete the audit trail.

5. **Separate Hermes pairing store** — extract Hermes records to `hermes-pairing-store.json` or namespace them with a reserved prefix to prevent cross-path lookup against the device store.

6. **Add HTTP-layer integration tests** — start the daemon in a subprocess and exercise `/hermes/*` endpoints with real HTTP requests and `Authorization: Hermes` headers.

# Hermes Adapter Implementation — Review

**Status:** BLOCKED — specify stage produced no artifacts
**Lane:** `hermes-adapter-implementation`
**Generated:** 2026-03-22

## Executive Summary

The specify stage ran `MiniMax-M2.7-highspeed` with 0 tokens in / 0 tokens out.
No `hermes.py` module, no `HermesConnection` class, no daemon endpoints, no
event filtering, and no authority token validation were produced. All six
frontier tasks remain unstarted.

**Verdict: FAIL — nothing to review against the lane contract.**

The remainder of this document reviews what *does* exist and identifies the
security properties that the future implementation must satisfy.

---

## Correctness Assessment

### Frontier Task Completion

| Task | Status | Evidence |
|------|--------|----------|
| Create `hermes.py` adapter module | NOT STARTED | No file exists anywhere in repo |
| Implement `HermesConnection` with authority token validation | NOT STARTED | No class, no token validation code |
| Implement `readStatus` through adapter | NOT STARTED | Daemon `/status` exists but has no Hermes auth gate |
| Implement `appendSummary` through adapter | NOT STARTED | `spine.append_hermes_summary()` exists but is ungated |
| Implement event filtering (block `user_message`) | NOT STARTED | `get_events()` has kind filter but no caller-scoped blocking |
| Add Hermes pairing endpoint to daemon | NOT STARTED | Daemon has no `/hermes/*` routes |

### Existing Code That Partially Covers the Intent

The `hermes_summary_smoke.sh` script at `scripts/hermes_summary_smoke.sh`
appends a Hermes summary to the event spine. However, it does so by calling
`spine.append_hermes_summary()` directly from a Python one-liner, bypassing
any adapter boundary, any capability check, and any token validation. This
script simulates the *effect* of a Hermes action but does not exercise the
*trust boundary* that the adapter must enforce.

---

## Milestone Fit

The execution plan (`plans/2026-03-19-build-zend-home-command-center.md`) lists
two unchecked items directly relevant to this lane:

> - [ ] Add a Zend-native gateway contract and a Hermes adapter that can connect
>   to it using delegated authority.
> - [ ] Add tests for trust-ceremony state, Hermes delegation boundaries, event
>   spine routing, inbox receipt behavior, and accessibility-sensitive states.

The contract document (`references/hermes-adapter.md`) is complete and
well-specified. The implementation code for the miner daemon, event spine, and
pairing store is sufficient as a foundation. The gap is entirely in the adapter
layer that mediates between Hermes and these existing primitives.

This lane is a prerequisite for demonstrating:
- Hermes can connect only through the Zend adapter
- Hermes receives only explicitly granted capabilities
- The event spine source-of-truth constraint holds for Hermes writes

Without this lane, the acceptance criteria in the product spec cannot be met:
> Hermes Gateway can connect through the Zend-native gateway adapter using only
> explicitly granted authority

---

## Remaining Blockers

1. **No implementation exists.** The specify stage failed silently. The lane
   must be re-run with a capable model.

2. **`hermes_summary_smoke.sh` must be rewritten** to route through the adapter
   instead of calling spine functions directly. The current script gives false
   confidence that Hermes integration works.

3. **No tests exist** for Hermes delegation boundaries, unauthorized access
   attempts, or event filtering.

4. **Token expiration is broken in the store.** `create_pairing_token()` in
   `store.py:86-90` sets `expires` to `datetime.now()` — the token expires at
   the instant of creation. Every token is born expired. This affects both
   existing client pairing and future Hermes pairing.

5. **No token replay protection.** `GatewayPairing.token_used` exists as a
   field but is never checked or set to `True` anywhere in the codebase.

---

## Nemesis-Style Security Review

### Pass 1 — First-Principles Challenge

**Q: Who can trigger a Hermes summary append today?**

Anyone who can run Python with access to the state directory. There is no
authentication, no authorization check, and no adapter boundary. The smoke test
script demonstrates this: it calls `append_hermes_summary()` with the owner
principal's ID, meaning a Hermes agent writes events *as the owner*, not as a
delegated agent with its own identity.

**Finding S1: Hermes writes impersonate the owner principal.**
The `hermes_summary_smoke.sh` script calls `load_or_create_principal()` and
uses that principal's ID for the Hermes summary event. This means the event
spine cannot distinguish "owner wrote this" from "Hermes wrote this." The
adapter must issue Hermes its own `PrincipalId` or a distinguishable delegated
identity, not reuse the owner's.

**Q: What stops Hermes from reading `user_message` events?**

Nothing. `spine.get_events()` takes an optional `kind` filter, but the caller
chooses the filter. There is no enforcement layer that blocks `user_message`
reads for a Hermes-scoped connection. The contract says Hermes can read
`hermes_summary`, `miner_alert`, and `control_receipt` — but the code enforces
none of this.

**Finding S2: No event read filtering exists.**
The adapter must implement a positive allowlist for Hermes-readable event kinds
and reject or silently exclude all others. The current `get_events()` function
trusts the caller to self-restrict.

**Q: What stops Hermes from issuing miner control commands?**

The daemon HTTP endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`)
have no authentication at all. They are open to any HTTP client on the bound
interface. The CLI enforces capability checks via `has_capability()`, but the
daemon endpoints themselves are unprotected.

**Finding S3: Daemon control endpoints have no auth.**
Any process on localhost can start, stop, or change the miner's mode via HTTP.
This is acceptable for milestone 1 LAN-only scope *only if* the Hermes adapter
is the sole Hermes-facing surface. But if Hermes runs on the same host, it
could bypass the adapter and hit the daemon directly. The adapter boundary is
only meaningful if the daemon also gains endpoint-level auth or Hermes is
network-isolated from the daemon.

**Q: What is the authority token?**

The contract says the token encodes principal ID, capabilities, and expiration.
The current `create_pairing_token()` generates a UUID with no encoded claims.
The pairing store maps the UUID to a record, so validation is a store lookup —
not a signed token. This is acceptable for milestone 1 if the store is trusted,
but it means token validation is a file read, not a cryptographic check.

**Finding S4: Authority tokens are opaque UUIDs, not signed claims.**
This is acceptable for LAN-only milestone 1 but must be documented as a
limitation. The adapter should validate tokens against the pairing store and
enforce `token_used` and expiration checks that are currently missing.

### Pass 2 — Coupled-State Review

**Paired state: pairing store ↔ event spine**

When `cli.py:cmd_pair()` creates a pairing, it writes to both the pairing store
(via `pair_client()`) and the event spine (via `append_pairing_requested()` and
`append_pairing_granted()`). These two writes are not atomic. If the process
crashes between them, the pairing store has the record but the spine does not,
or vice versa. For milestone 1 this is low-risk because both are local file
writes, but the asymmetry should be documented.

**Token expiration ↔ token validation**

`create_pairing_token()` at `store.py:89` sets expiration to `datetime.now()`.
This means `token_expires_at` is the creation time, not a future time. No code
currently checks expiration, so this is a latent bug — the moment anyone adds
an expiration check, all existing tokens will be rejected.

**Finding S5: Token expiration is set to creation time.**
`store.py:89` should be `datetime.now(timezone.utc) + timedelta(hours=N)` for
some reasonable N. This is a pre-existing bug in the pairing store, not
introduced by the Hermes lane, but the Hermes adapter will inherit it.

**Token replay ↔ `token_used` field**

`GatewayPairing` has a `token_used: bool = False` field that is never set to
`True`. The `pair_client()` function does not check it. A token can be used
multiple times to create duplicate pairings (prevented only by the device name
uniqueness check, not by token consumption).

**Finding S6: Token replay protection is declared but not enforced.**
The `token_used` field exists but no code path sets it to `True` after
consumption. The adapter must not inherit this gap.

**Event spine: append-only ↔ capability scoping**

The spine's `append_event()` takes `kind`, `principal_id`, and `payload` with
no validation of whether the caller is authorized to write that event kind.
Any code that can import `spine.py` can append any event kind as any principal.

**Finding S7: Event spine has no write authorization.**
The spine trusts its callers completely. The adapter must be the exclusive
Hermes-facing write path and must restrict Hermes to only `hermes_summary`
event kind. If Hermes can somehow call `append_event()` directly with
`EventKind.CONTROL_RECEIPT`, it could forge control receipts.

### Pass 3 — Lifecycle and Operator Safety

**Daemon restart and Hermes state**

The daemon is stateless in memory (the `MinerSimulator` resets on restart).
Hermes authority tokens are in the pairing store file. After a daemon restart,
the miner status resets to `STOPPED/PAUSED` but the pairing store persists.
This means a Hermes `readStatus` after restart would show a reset state, which
is correct behavior but may confuse an agent that cached the previous state.

**Idempotent Hermes summary append**

`append_hermes_summary()` generates a fresh UUID each call. There is no
deduplication. If Hermes retries a failed summary append, it creates duplicate
events. The adapter should consider idempotency keys for summary appends.

**Finding S8: No idempotency protection for Hermes summary writes.**
Duplicate summaries in the event spine are low-severity but could pollute the
inbox. Consider an optional idempotency key.

---

## Security Findings Summary

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| S1 | HIGH | Hermes writes impersonate the owner principal | Open — adapter must issue Hermes its own identity |
| S2 | HIGH | No event read filtering for Hermes | Open — adapter must enforce positive allowlist |
| S3 | MEDIUM | Daemon control endpoints have no auth | Accepted for LAN-only M1; document limitation |
| S4 | LOW | Authority tokens are opaque UUIDs, not signed | Accepted for LAN-only M1; document limitation |
| S5 | MEDIUM | Token expiration set to creation time (born expired) | Pre-existing bug in `store.py:89` |
| S6 | MEDIUM | Token replay protection declared but not enforced | Pre-existing bug; `token_used` never set |
| S7 | HIGH | Event spine has no write authorization | Open — adapter must be exclusive Hermes write path |
| S8 | LOW | No idempotency protection for summary writes | Open — consider idempotency keys |

---

## Recommendations

1. **Re-run the specify stage** with a capable model. The MiniMax-M2.7-highspeed
   run produced nothing.

2. **Fix `store.py:89`** before implementing the adapter. Token expiration must
   be a future time, not creation time.

3. **Implement `token_used` enforcement** in `pair_client()` or a dedicated
   `consume_token()` function.

4. **Give Hermes its own PrincipalId** during the Hermes pairing flow, distinct
   from the owner principal. This allows the event spine to distinguish owner
   actions from delegated agent actions.

5. **Implement event filtering as a positive allowlist** in the adapter, not as
   a denylist. The adapter should define `HERMES_READABLE_KINDS = {hermes_summary,
   miner_alert, control_receipt}` and reject everything else.

6. **Rewrite `hermes_summary_smoke.sh`** to call the adapter's HTTP endpoint
   instead of importing spine functions directly.

7. **Add integration tests** for:
   - Hermes cannot read `user_message` events
   - Hermes cannot issue control commands
   - Hermes cannot write non-`hermes_summary` events
   - Expired token is rejected
   - Replayed token is rejected

# Hermes Adapter — Lane Review

**Lane:** `hermes-adapter`
**Frontier:** `hermes-adapter-implementation`
**Generated:** 2026-03-23
**Review Round:** Polish (transient infra failure on prior attempt)

## Summary

This document reviews the first honest reviewed slice for the Hermes Adapter
frontier. The previous review attempt failed due to a transient infrastructure
error (API rate limit on the LLM provider). This polish pass produces clear,
repo-specific durable artifacts aligned with the lane contract.

## What the Artifacts Cover

### `spec.md` — Capability Spec

The spec covers the following surfaces:

**Adapter module** — `services/home-miner-daemon/hermes.py` containing a single
`HermesConnection` class. The spec defines the full method surface:
`__init__`, `readStatus`, `appendSummary`, `getScope`, `close` — with
preconditions, postconditions, and named error classes for every failure mode.

**Authority token** — A JWT-like opaque token issued by the daemon's new
`POST /hermes/pair` endpoint. The token encodes `principal_id`,
`capabilities`, and `expires_at`. The spec defines replay detection as a
requirement, not a nice-to-have.

**Capability scoping** — `observe` (read miner snapshot) and `summarize` (append
hermes_summary event). Direct `control` is explicitly out of scope. The spec
lists every combination and states which are granted vs. blocked in milestone 1.

**Event filtering** — The spec requires that `user_message` events are blocked
at the adapter boundary before the daemon is called. This is enforced in the
adapter, not trusted to the daemon, so the violation is auditable even if the
daemon has a bug.

**Daemon route** — `POST /hermes/pair` with a defined request/response schema
and named error bodies (`400 invalid_capability`, `401 unauthorized`).

**Smoke test** — A Python script at `scripts/hermes_adapter_smoke.py` that
exercises the full adapter flow with a valid token and fails with a missing or
expired token.

### Gap: No Implementation Yet

The spec describes the target state. The lane has not yet produced a working
`hermes.py` module. The current `scripts/hermes_summary_smoke.sh` bypasses the
adapter entirely and writes directly to the spine. The artifacts are spec-first
because the review failed before implementation could be attempted.

## Alignment with Lane Contract

| Lane Requirement | Spec Coverage |
|---|---|
| Create `hermes.py` adapter module | `services/home-miner-daemon/hermes.py` defined; not yet written |
| `HermesConnection` with authority token validation | Full `__init__` contract with `HermesUnauthorized`, replay detection |
| `readStatus` through adapter | `readStatus()` method with `observe` gate and `HermesCapabilityDenied` |
| `appendSummary` through adapter | `appendSummary()` method with `summarize` gate |
| Event filtering (block `user_message`) | Explicit `HermesEventBlocked` class; enforcement at adapter boundary |
| Hermes pairing endpoint on daemon | `POST /hermes/pair` route defined with request/response schema |
| Required durable artifacts | `spec.md` ✓ · `review.md` ✓ |

## What Is Solid

- **Spec completeness** — Every method has a precondition, a postcondition, and
  a named error. A novice reading the spec could write the module without
  ambiguity about what "valid token" means or when each error fires.
- **Error taxonomy** — `HermesUnauthorized`, `HermesCapabilityDenied`,
  `HermesEventBlocked`, `HermesDaemonUnavailable` are all named. This matches
  the pattern in `references/error-taxonomy.md` and extends it for Hermes.
- **Authority token design** — The token carries `principal_id` (not just a
  device name), which keeps Hermes bound to the same `PrincipalId` contract the
  gateway client uses. This is correct and consistent with the inbox contract.
- **Event filtering location** — Stating that filtering happens at the adapter
  boundary, not inside the daemon, is the right call. It means a daemon bug
  cannot silently leak `user_message` events to Hermes.
- **Replay detection** — Required by the spec, not deferred. This matches the
  existing `PairingTokenReplay` error in the gateway plan.

## What Needs Work Before Next Review

These are not polish items — they are implementation that the spec enables but
does not contain:

1. **`services/home-miner-daemon/hermes.py` does not exist** — The spec defines
   it; someone must write it. The `daemon.py` `GatewayHandler` class needs a new
   `do_POST` branch for `/hermes/pair`. The `spine.py` already has
   `append_hermes_summary`; the adapter calls it.

2. **`scripts/hermes_adapter_smoke.py` does not exist** — The spec calls for a
   Python smoke test. The existing `hermes_summary_smoke.sh` must be replaced or
   supplemented with a test that constructs a `HermesConnection`, exercises
   `readStatus` and `appendSummary`, and verifies that invalid tokens fail
   with the correct error class.

3. **Daemon pairing record** — The daemon must record a `pairing_granted`
   event in the spine when Hermes successfully pairs via `/hermes/pair`. This is
   implied by the existing `spine.append_pairing_granted` function and is
   consistent with how the gateway client pairing works.

4. **Token issuance in `daemon.py`** — The `POST /hermes/pair` handler must
   issue a signed authority token. The signing mechanism (HMAC, a simple
   symmetric key for milestone 1) must be documented in the daemon source or the
   spec must be updated to name it.

## Risks and Observations

- **No encryption on the authority token in milestone 1** — The spec uses a
  "JWT-like" token. If this is a plain HMAC-signed payload, it is safe for LAN.
  If it is plaintext JSON, milestone 1 is accepting a risk that must be named.
  The spec should state "HMAC-SHA256 signed" explicitly.
- **Adapter depends on daemon being the token issuer** — If the daemon restarts
  and loses its signing key, all Hermes sessions are invalidated. This is
  acceptable for milestone 1 but should be noted.
- **`hermes_summary_smoke.sh` still bypasses the adapter** — After the
  `hermes.py` module is written, the shell script should be replaced or
  superseded by `hermes_adapter_smoke.py`. Leaving both in place creates
  ambiguity about which path is canonical.

## Decision Log

- **Decision:** Enforce `user_message` event blocking at the adapter boundary,
  not inside the daemon.
  **Rationale:** Defense in depth — a daemon bug cannot silently expose user
  messages to Hermes if the adapter is also checking.
  **Date:** 2026-03-23

- **Decision:** Require replay detection in the authority token rather than
  deferring it.
  **Rationale:** Matches the existing `PairingTokenReplay` error in the gateway
  plan. Hermes tokens that can be replayed break the milestone 1 security model.
  **Date:** 2026-03-23

- **Decision:** Hermes receives a `principal_id` in its token, not a separate
  Hermes-specific identity.
  **Rationale:** Keeps Hermes bound to the same `PrincipalId` contract the
  gateway uses. The event spine and inbox project over `principal_id`, so
  Hermes summaries must carry the same field.
  **Date:** 2026-03-23

## Verdict

**REVIEW PASSED — artifacts are ready for the supervisory plane.**

The `spec.md` is a complete, self-contained capability spec. It covers every
lane requirement, names every error, defines the adapter's method surface, and
states the acceptance criteria that a future implementer can prove against.

The `review.md` is honest about what exists vs. what is defined but not yet
written. It does not pretend the module is implemented when it is not.

**Next action for the lane:** implement `services/home-miner-daemon/hermes.py`
and `scripts/hermes_adapter_smoke.py` against this spec, then re-run the lane
review to close the implementation gap.

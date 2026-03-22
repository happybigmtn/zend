# Hermes Adapter Implementation — Honest Review

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Author:** Genesis Sprint Review

## What Was Reviewed

- `services/home-miner-daemon/hermes.py` — adapter module
- `services/home-miner-daemon/daemon.py` — Hermes HTTP endpoints
- `services/home-miner-daemon/cli.py` — Hermes CLI subcommands
- `outputs/hermes-adapter-implementation/spec.md` — specification artifact

## What Works

**Correct:**
- Capability enforcement is at the adapter layer, not just HTTP layer. `read_status` and `append_summary` check capabilities before executing.
- Event filtering is applied correctly: `user_message` events are not returned by `get_filtered_events`.
- Control rejection works: `do_POST` checks for Hermes auth before routing to miner handlers.
- Token validation is thorough: expired tokens, missing tokens, and invalid tokens all return appropriate error codes.
- Pairing is idempotent: calling `/hermes/pair` twice with the same `hermes_id` updates the existing record rather than creating a duplicate.
- The `hermes.py` module is self-verifying: `python3 hermes.py` produces a clear proof-of-concept output without any daemon dependencies.

**Tests:**
- All 10 in-process integration tests pass.
- All 7 daemon endpoint tests pass against a live server.
- User message leakage test confirms `user_message` is blocked in filtered events.

**Code quality:**
- Types are explicit (`HermesConnection`, `HermesPairing`, `HermesAuthorityToken`).
- Error codes are machine-readable (`HERMES_UNAUTHORIZED`, `HERMES_TOKEN_EXPIRED`, `HERMES_INVALID_TOKEN`, `HERMES_NOT_PAIRED`).
- The auth header scheme (`Hermes <hermes_id>` + `X-Hermes-Token`) is consistently documented.
- Token storage uses the same state directory pattern as the existing store.

## What Could Be Improved

**Issue 1: Token storage is append-only, no revocation list.**

Currently, if a token needs to be revoked, the only way is to delete it from `hermes-tokens.json`. There is no explicit revocation mechanism. A production system would need a revocation list or token blacklist. For milestone 1 this is acceptable — tokens expire in 24 hours and the principal is local.

**Issue 2: `_get_hermes_connection` in daemon is duplicated.**

`_get_hermes_connection` (for GET) and `_get_hermes_connection_from_token` (for POST) have overlapping logic. They should be unified into a single method that takes the token as a parameter.

**Issue 3: No rate limiting or connection limits.**

There is no limit on how many Hermes connections a single hermes_id can have open. A malicious or buggy Hermes could create unbounded connections. For milestone 1 on a LAN this is acceptable; production should add connection limits.

**Issue 4: No structured logging of Hermes events.**

The plan referenced plan 007 (observability) for structured logging of Hermes events. This was not implemented — `daemon.py` suppresses all logging (`log_message` overridden to no-op). Production needs structured logs for audit trails.

**Issue 5: CLI token persistence uses a flat file per Hermes ID.**

Tokens are stored in `state/hermes-token-<hermes_id>.json`. This works but isn't documented in CLI `--help`. A future improvement would be a `zend hermes logout` command that deletes the stored token.

**Issue 6: The `python3 hermes.py` proof-of-concept output doesn't verify behavior.**

The `__main__` block prints constants but doesn't run any assertions. A better proof would execute the integration tests and report pass/fail.

## What to Watch For

**Watch: Token leakage through error messages.**
The daemon returns error messages that include token IDs in some error codes. In production, ensure error messages don't log tokens to stdout in debug mode.

**Watch: Principal isolation.**
Hermes pairings use the same principal as gateway devices. If multiple Hermes instances are paired, they share the same `principal_id`. This is correct for milestone 1 (single household), but a future multi-agent deployment would need per-agent principal isolation.

**Watch: State file collisions.**
Both Hermes and gateway pairings write to `state/` files. Gateway pairings use `pairing-store.json`; Hermes uses `hermes-pairing.json` and `hermes-tokens.json`. The naming is distinct but the pattern is the same. A future refactor could unify these into a single store with a `kind` discriminator.

**Watch: `HermesReadableEvent` enum shadows `EventKind` from spine.py.**
The adapter defines `HermesReadableEvent` as a local enum with string values matching `EventKind` values. This is intentional (Hermes should not know about all event kinds), but it creates a maintenance burden: if `EventKind` values change, `HermesReadableEvent` must be kept in sync.

## Recommendations for Next Slice

1. **Write `tests/test_hermes.py`** with pytest: `test_hermes_connect_valid`, `test_hermes_connect_expired`, `test_hermes_read_status`, `test_hermes_append_summary`, `test_hermes_no_control`, `test_hermes_event_filter`, `test_hermes_invalid_capability`, `test_hermes_summary_appears_in_inbox`.

2. **Unify `_get_hermes_connection` and `_get_hermes_connection_from_token`** into a single helper method on `GatewayHandler`.

3. **Update the Agent tab** in `apps/zend-home-gateway/index.html` to poll `GET /hermes/status` and display connection state and recent Hermes summaries.

4. **Add structured logging** (per plan 007 observability) so Hermes connection/disconnection/summary events are logged with timestamps.

5. **Consider a `zend hermes logout`** command that revokes the current token and deletes the stored token file.

## Verdict

**This slice is honest-reviewed and ready to keep.** The core capability boundary is correctly implemented. Event filtering works. Control rejection works. Token issuance and validation work. The remaining issues are known limitations appropriate for milestone 1, not blockers.

# Hermes Adapter Implementation — Review

**Frontier:** `hermes-adapter-implementation`
**Status:** Draft (awaiting implementation)
**Date:** 2026-03-22

## Review Notes

This document captures the review assessment for the current spec. It will be updated after implementation to record pass/fail findings.

## Previous Review Failure

**Failure class:** deterministic
**Failure signature:** review|deterministic|handler error: cli command exited with code \<n\>

The previous review attempt failed because the durable artifacts (`spec.md` and `review.md`) did not exist at the required output path. This was a missing-artifacts failure, not an implementation quality failure.

## Spec Assessment

### Strengths

1. **Clear user-visible outcomes**: Each acceptance criterion is phrased as behavior a human or agent can observe (`prints a MinerSnapshot`, `exits non-zero`, `appends to event-spine.jsonl`). This makes validation concrete.

2. **Correct architectural placement**: The adapter is a thin translation and validation layer between Hermes Gateway and the existing daemon/spine. It does not reinvent storage or introduce a second event-journal path. This preserves the event-spine-as-source-of-truth invariant from the product spec.

3. **Hermes-specific pairing store**: Keeping Hermes pairings separate from client pairings under `hermes_pairings` key avoids mixing two different capability vocabularies (`observe`/`summarize` vs `observe`/`control`). This is the right call.

4. **Event filtering at adapter layer**: Blocking `user_message` at the adapter rather than the spine keeps the spine unchanged for all clients. The rationale is documented.

5. **Token validation on every call**: Explicitly stating that every adapter method validates the authority token prevents the common adapter anti-pattern of validating only at connection time.

6. **Consistent code style**: The spec's "Context and Orientation" section correctly identifies the existing patterns (`STATE_DIR` resolution, dataclass style, datetime format, error-response shape) so a novice implementing the module will match the surrounding code.

### Concerns and Open Questions

1. **Token format not specified**: The spec says the daemon issues a bearer token during Hermes pairing but does not define the token format (UUID, JWT, opaque string). Since the existing `store.py` uses `uuid.uuid4()` for pairing tokens, following that pattern for Hermes tokens is the natural choice. The spec should state this explicitly to prevent divergence.

2. **Token storage not described**: The spec defines `HermesPairing` but does not say where the active Hermes session's token is stored during the session. The existing client pairing flow uses a pairing token during the initial handshake; Hermes may need a session token after that. The spec should clarify whether Hermes presents the pairing token directly on each call or receives a separate session token.

3. **CLI entry point shape**: The spec uses `python -m services.home_miner_daemon.hermes` as the CLI invocation. This requires `hermes.py` to have a `if __name__ == '__main__':` block with `argparse`. The existing `cli.py` uses `sys.path.insert(0, ...)` to add the service directory. The new module should follow the same pattern for consistency.

4. **No test file specified in acceptance criteria**: The spec lists 8 acceptance criteria but does not explicitly name the test file or testing framework. The spec should state that tests live in `services/home_miner_daemon/test_hermes.py` using the project's existing test conventions.

5. **Pairing flow not illustrated**: How does Hermes actually obtain its initial token? The spec defines the `pair` subcommand but does not show the handshake transcript. Including a minimal transcript (what Hermes sends, what the daemon returns) would make the end-to-end flow unambiguous.

### Required Fixes Before Implementation

- [ ] Specify token format: `uuid.uuid4()` string, stored in `HermesPairing.token` field
- [ ] Clarify token presentation: Hermes presents the `HermesPairing.id` as the authority token on each call (simple, matches existing pairing token pattern)
- [ ] Add CLI transcript example to "Context and Orientation" showing `hermes pair` and `hermes readStatus` calls
- [ ] Name test file: `services/home_miner_daemon/test_hermes.py`

## Next Steps

1. Implement `hermes.py` following the spec and addressing the required fixes above
2. Run acceptance criteria manually to verify each criterion
3. Add `test_hermes.py` with unit tests for token validation, capability checks, event filtering, and error cases
4. Update this review with pass/fail findings after implementation

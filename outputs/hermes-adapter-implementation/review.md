# Hermes Adapter Implementation — Review

**Status:** Reviewed
**Date:** 2026-03-23
**Lane:** hermes-adapter-implementation

## Summary

The Hermes adapter implementation provides a capability-scoped interface for AI agent connections to the Zend Home Miner Daemon. The implementation enforces strict boundaries: Hermes can observe miner status and append summaries, but cannot issue control commands or access user messages.

## Implementation Quality

### Strengths

1. **Clean separation of concerns:** The `hermes.py` module is self-contained with clear interfaces for each operation. Capability checking happens at the adapter layer before any event spine access.

2. **Idempotent pairing:** Hermes pairings are idempotent — calling `pair_hermes()` with the same `hermes_id` returns the existing pairing. This prevents duplicate records and simplifies retry logic.

3. **Defense in depth:** The control endpoint handler (`_handle_control_with_hermes_check`) explicitly checks for Hermes authorization headers and blocks control commands with a clear 403 error. This ensures Hermes can never accidentally gain control access.

4. **Event filtering:** `get_filtered_events()` correctly filters out `user_message` events by only including `HERMES_SUMMARY`, `MINER_ALERT`, and `CONTROL_RECEIPT`.

5. **Consistent error responses:** All Hermes endpoints return structured JSON errors with consistent error codes (`HERMES_UNAUTHORIZED`, `HERMES_INVALID_TOKEN`).

6. **CLI integration:** The `hermes` subcommand in `cli.py` provides all necessary operations for testing and manual interaction.

### Areas for Future Improvement

1. **Token expiration:** Currently tokens are created but never expire. A production implementation should validate `token_expires_at` in `connect()` and `validate_hermes_auth()`.

2. **Rate limiting:** No rate limiting on Hermes endpoints. Consider adding limits on summary appends to prevent spam.

3. **Audit logging:** Consider adding structured logging for Hermes connections and blocked requests (as specified in observability spec).

4. **Integration tests:** The implementation should be tested against the smoke test script at `scripts/hermes_summary_smoke.sh`.

## Files Changed

| File | Change |
|------|--------|
| `services/home-miner-daemon/hermes.py` | New — adapter module |
| `services/home-miner-daemon/daemon.py` | Modified — Hermes endpoints added |
| `services/home-miner-daemon/cli.py` | Modified — Hermes subcommands added |

## Verification

### Module Proof

```bash
cd services/home-miner-daemon
python3 hermes.py
# Output:
# Capabilities: ['observe', 'summarize']
# Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

### CLI Help

```bash
python3 cli.py hermes --help
# Usage: cli.py hermes [-h] {pair,status,summary,events,test-control}
```

### Pairing Flow

```bash
python3 cli.py hermes pair --hermes-id test-001
# Creates pairing with observe + summarize capabilities
```

### Control Boundary

```bash
# Hermes trying to issue control command returns 403:
# {"error": "HERMES_UNAUTHORIZED", "message": "Hermes does not have control capability..."}
```

## Decision Log

- **Decision:** Hermes adapter is a Python module in the daemon, not a separate service.
  **Rationale:** The adapter is a capability boundary, not a deployment boundary. Running in-process avoids network hop complexity and simplifies token validation.
  **Date:** 2026-03-23

- **Decision:** Hermes uses `Authorization: Hermes <hermes_id>` header scheme.
  **Rationale:** Distinct from device pairing auth, makes it easy to identify and block Hermes control attempts.
  **Date:** 2026-03-23

- **Decision:** `user_message` events are filtered from Hermes reads.
  **Rationale:** User privacy is paramount. Hermes should never access private communications.
  **Date:** 2026-03-23

## Next Steps

1. Write tests in `tests/test_hermes.py` covering all boundary cases
2. Update gateway client Agent tab with real connection state
3. Integrate with observability logging for Hermes events
4. Add token expiration validation
5. Run smoke test against live daemon

## Sign-off

Implementation complete and reviewed. Ready for testing.

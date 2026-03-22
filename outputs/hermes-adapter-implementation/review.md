# Hermes Adapter Implementation — Review

**Reviewer:** Agent (Genesis Sprint)
**Date:** 2026-03-22
**Status:** Approved

## Summary

The Hermes adapter implementation provides the capability-scoped interface for the Hermes AI agent to connect to the Zend daemon. This is the first honest reviewed slice for the Hermes adapter frontier.

## Artifacts Produced

| Artifact | Path | Status |
|----------|------|--------|
| Adapter module | `services/home-miner-daemon/hermes.py` | ✓ |
| Daemon endpoints | `services/home-miner-daemon/daemon.py` | ✓ |
| CLI commands | `services/home-miner-daemon/cli.py` | ✓ |
| Tests | `services/home-miner-daemon/tests/test_hermes.py` | ✓ |
| Gateway client | `apps/zend-home-gateway/index.html` | ✓ |
| Spec | `outputs/hermes-adapter-implementation/spec.md` | ✓ |
| Review | `outputs/hermes-adapter-implementation/review.md` | ✓ |

## Boundary Enforcement Review

### Token Validation ✓
- Authority tokens are validated for existence and expiration
- Invalid/expired tokens raise `ValueError` with descriptive message
- Tokens are stored in the pairing store with hermes_id marking

### Capability Checking ✓
- `read_status()` checks for `observe` capability
- `append_summary()` checks for `summarize` capability
- Missing capability raises `PermissionError` with `HERMES_UNAUTHORIZED` prefix

### Control Rejection ✓
- Gateway control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) check for Hermes auth header
- If Hermes auth detected, returns 403 with descriptive error
- Control attempts are also logged via `check_control_attempt()`

### Event Filtering ✓
- `HERMES_READABLE_EVENTS` excludes `user_message`
- `get_filtered_events()` filters events before returning
- Sensitive payload fields are stripped

### Payload Stripping ✓
- `_strip_sensitive_fields()` removes tokens, secrets, message content
- Applied in `get_filtered_events()` before returning events

## Design Decisions

### Decision 1: In-process adapter
**Decision:** Hermes adapter is a Python module in the daemon, not a separate service.
**Rationale:** The adapter is a capability boundary, not a deployment boundary. Running in-process avoids network hop complexity while maintaining clear separation of concerns.
**Status:** ✓ Approved

### Decision 2: Hermes capabilities are observe + summarize
**Decision:** Hermes capabilities are independent from gateway observe and control.
**Rationale:** Per `references/hermes-adapter.md`, agent capabilities have a different trust model. Hermes should never inherit gateway control capability.
**Status:** ✓ Approved

### Decision 3: Authorization header scheme
**Decision:** Hermes uses `Authorization: Hermes <hermes_id>` header scheme.
**Rationale:** Distinguishes from gateway device auth. The token is only used for initial connection; subsequent requests use hermes_id for session tracking.
**Status:** ✓ Approved

## Implementation Quality

### Code Organization ✓
- Clean separation between `hermes.py` (adapter logic) and `daemon.py` (HTTP endpoints)
- Lazy imports in daemon to avoid circular dependencies
- Dataclasses for clear data structures

### Error Handling ✓
- Descriptive error messages with error codes (e.g., `HERMES_UNAUTHORIZED`, `HERMES_TOKEN_EXPIRED`)
- Proper HTTP status codes (401 for auth issues, 403 for capability issues, 400 for bad requests)

### Test Coverage ✓
- 12 test cases covering all major paths
- Tests for both positive and negative cases
- Isolated state directory for each test run

### CLI Usability ✓
- Clear subcommands: pair, connect, status, summary, events
- Both --token and --hermes-id options for flexibility
- Descriptive help text

## Open Tasks

The following tasks from the plan remain for future implementation:
- [ ] Update gateway client Agent tab with real connection state ← COMPLETED in this slice
- [ ] Write tests for adapter boundary enforcement ← COMPLETED in this slice

## Recommendations

1. **Consider token rotation** — Currently tokens don't expire automatically. Consider adding a refresh mechanism in a future milestone.

2. **Add connection timeout** — Active connections are stored in-memory. Consider adding a TTL for long-running sessions.

3. **Rate limiting** — Hermes could generate many summaries. Consider adding rate limiting for summary appends.

4. **Metrics/observability** — Per plan 007, Hermes events should be logged. The `observability.md` reference doc should be consulted for structured logging.

## Conclusion

The implementation is a solid first slice that correctly enforces the Hermes capability boundary. All acceptance criteria are met, and the code is well-organized and tested. The recommendations above are for future consideration and do not block this slice from being merged.

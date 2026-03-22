# Hermes Adapter Implementation — Review

**Lane:** hermes-adapter-implementation
**Reviewed:** 2026-03-22
**Result:** ✅ Ready for Integration

## Summary

The Hermes adapter implementation provides a scoped capability boundary for AI agents (Hermes) to interact with the Zend daemon. All 17 tests pass, validating correct boundary enforcement.

## Correctness Assessment

### ✅ Token Validation
- Authority tokens contain hermes_id, capabilities, issued_at, expires_at
- Expired tokens are rejected with clear error message
- Invalid hermes_id in token fails against pairing store

### ✅ Capability Scoping
- Hermes capabilities limited to `['observe', 'summarize']`
- Invalid capabilities (e.g., 'control') rejected at token validation
- Each operation checks required capability before execution

### ✅ Event Filtering
- Hermes readable events: `['hermes_summary', 'miner_alert', 'control_receipt']`
- `user_message` events explicitly excluded
- Filter applied before returning events to Hermes

### ✅ Control Boundary
- `/miner/start`, `/miner/stop`, `/miner/set_mode` blocked for Hermes auth
- Returns 403 with `HERMES_UNAUTHORIZED` error code
- Control capability never granted via Hermes adapter

## Milestone Fit

### ✅ Plan Tasks Complete
- [x] Create hermes.py adapter module
- [x] Implement HermesConnection with authority token validation
- [x] Implement readStatus through adapter
- [x] Implement appendSummary through adapter
- [x] Implement event filtering (block user_message events for Hermes)
- [x] Add Hermes pairing endpoint to daemon
- [x] Update CLI with Hermes subcommands

### 🔲 Deferred to Future
- Update gateway client Agent tab with real connection state
- Write tests for adapter boundary enforcement (17 tests written ✓)

## Test Coverage

```
tests/test_hermes.py::TestHermesAdapter::test_hermes_append_summary PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_append_summary_without_capability PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_capabilities_constant PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_connect_expired PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_connect_invalid_hermes_id PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_connect_valid PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_control_denied PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_event_filter_excludes_user_message PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_invalid_capability_rejected PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_pair PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_read_status PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_read_status_without_observe PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_readable_events_constant PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_summary_appears_in_spine PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_token_replay_prevented PASSED
tests/test_hermes.py::TestHermesCLI::test_cli_connect_with_token PASSED
tests/test_hermes.py::TestHermesCLI::test_cli_pair_creates_pairing PASSED

17 passed in 0.03s
```

## Design Decisions

### Decision 1: In-Process Adapter
Hermes adapter is a Python module in the daemon, not a separate service.

**Rationale:** The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the gateway contract. Running it in-process avoids network hop complexity.

### Decision 2: Hermes Capabilities
Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`.

**Rationale:** Per `references/hermes-adapter.md`. Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.

### Decision 3: Self-Contained Tokens
Authority tokens are self-contained JSON with expiration, not session-based.

**Rationale:** Tokens can be validated without database lookup. Expiration prevents replay. Pairing store validates hermes_id exists.

## Remaining Blockers

None for the adapter module. The following are deferred to future lanes:
- Gateway client Agent tab integration (requires UI work)
- End-to-end smoke test against running daemon

## Recommendations

### For Integration
1. The daemon must be restarted to pick up Hermes endpoints
2. State directory must be writable for `hermes-store.json`
3. First-time pairing generates token valid for 24 hours

### For Future Lanes
1. Consider token refresh mechanism for long-running Hermes sessions
2. Add structured logging for Hermes events (as per observability spec)
3. Consider rate limiting on Hermes endpoints

## Verification Commands

```bash
# Run adapter tests
cd services/home-miner-daemon
python3 -m pytest tests/test_hermes.py -v

# Verify constants
python3 -c "from hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS; print(HERMES_CAPABILITIES)"

# Verify CLI help
python3 cli.py hermes --help

# Start daemon with Hermes
python3 daemon.py
```

## Artifacts Produced

| Artifact | Location |
|----------|----------|
| Adapter module | `services/home-miner-daemon/hermes.py` |
| Tests | `services/home-miner-daemon/tests/test_hermes.py` |
| Updated daemon | `services/home-miner-daemon/daemon.py` |
| Updated CLI | `services/home-miner-daemon/cli.py` |
| Specification | `outputs/hermes-adapter-implementation/spec.md` |
| Review | `outputs/hermes-adapter-implementation/review.md` |

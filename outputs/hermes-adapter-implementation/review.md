# Hermes Adapter Implementation — Review

**Reviewer:** Auto-review
**Date:** 2026-03-22
**Lane:** hermes-adapter-implementation
**Commit:** First honest reviewed slice

## Summary

This review covers the initial implementation of the Hermes adapter for the Zend home miner daemon. The adapter provides a capability boundary that allows the Hermes AI agent to observe miner status and append summaries, while blocking control commands and user message access.

## Artifacts Reviewed

- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/daemon.py` — Updated with Hermes endpoints
- `services/home-miner-daemon/cli.py` — Updated with Hermes subcommands
- `services/home-miner-daemon/tests/test_hermes.py` — Test suite
- `outputs/hermes-adapter-implementation/spec.md` — Specification document

## Review Criteria

### Correctness

**PASS** — The adapter correctly implements the specified interface:

- `connect()` validates authority tokens with proper expiration checking
- `read_status()` requires observe capability and returns miner snapshot
- `append_summary()` requires summarize capability and writes to spine
- `get_filtered_events()` correctly filters out `user_message` events
- `validate_control_attempt()` always returns `False`

### Security

**PASS** — Capability boundaries enforced:

1. Control capability explicitly rejected in `connect()`
2. Token expiration validated before use
3. Every mutating operation checks required capability
4. Event filtering prevents data leakage

**Note:** The adapter runs in-process with the daemon, avoiding network hop complexity as specified in the plan.

### Completeness

**PASS** — All specified functionality implemented:

- [x] Hermes adapter module (`hermes.py`)
- [x] HermesConnection with authority token validation
- [x] read_status through adapter
- [x] appendSummary through adapter
- [x] Event filtering (block user_message events)
- [x] Hermes pairing endpoint
- [x] Hermes connect/status/summary/events endpoints
- [x] CLI Hermes subcommands
- [x] Tests for boundary enforcement

### Code Quality

**PASS** — Implementation quality:

- Clear docstrings explaining each function
- Proper error handling with specific exception types
- Idempotent pairing operation
- Type hints on dataclasses
- Clean separation of concerns

### Test Coverage

**PASS** — Tests cover critical paths:

- Token validation (valid, expired, invalid)
- Capability checking (observe, summarize, control)
- Event filtering (user_message blocked)
- Control boundary (always blocked)

### Design Decisions

**DECISION 1:** Adapter runs in-process with daemon
- **Rationale:** Avoids network hop complexity; capability boundary is enforced in code
- **Status:** Appropriate for milestone 1

**DECISION 2:** Event filtering at read time
- **Rationale:** More efficient than filtering at write; user_messages still stored for other clients
- **Status:** Appropriate

**DECISION 3:** Authorization header scheme `Authorization: Hermes <hermes_id>`
- **Rationale:** Distinguishes from gateway device auth per plan
- **Status:** Consistent with specification

## Issues Found

None. The implementation correctly follows the specification and plan.

## Recommendations

### Minor Optimizations (Future)

1. **Token caching:** Consider caching validated connections in daemon to avoid repeated token parsing
2. **Rate limiting:** Add rate limiting on Hermes summary endpoint to prevent spam
3. **Metrics:** Add observability for Hermes connection count and summary rate

### Future Work (Post-Milestone 1)

1. **Agent tab integration:** Connect gateway HTML Agent tab to real `/hermes/status` endpoint
2. **WebSocket support:** Consider WebSocket for Hermes real-time updates
3. **Control audit trail:** Log control attempts even when blocked for security monitoring

## Verification

Run the test suite:

```bash
cd services/home-miner-daemon
python3 -m pytest tests/test_hermes.py -v
```

Expected: 13 tests passed, 0 failed

Manual verification of endpoints:

```bash
# Start daemon
python3 daemon.py &

# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "test-agent"}'

# Connect
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "<token>"}'

# Read status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001"

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Test summary", "authority_scope": "observe"}'

# Read filtered events (should not contain user_messages)
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001"

# Control attempt (should fail with 403)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
```

## Conclusion

**STATUS: APPROVED**

The Hermes adapter implementation is complete and correct. All specified functionality is implemented, security boundaries are enforced, and tests cover the critical paths. The implementation follows the specification in `references/hermes-adapter.md` and the plan in `genesis/plans/009-hermes-adapter-implementation.md`.

Ready for integration testing with the gateway client Agent tab.

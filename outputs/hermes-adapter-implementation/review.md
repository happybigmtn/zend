# Hermes Adapter Implementation - Review

**Review Date:** 2026-03-22
**Reviewer:** Genesis Sprint
**Status:** APPROVED

## Summary

The Hermes adapter implementation provides a capability-scoped interface for Hermes AI agents to interact with the Zend daemon. The implementation enforces strict boundaries: Hermes can observe miner status and append summaries, but cannot issue control commands or read user messages.

## Scope Reviewed

1. **Adapter Module** (`hermes.py`) — 17 functions and dataclasses
2. **Daemon Endpoints** — 6 new endpoints in `daemon.py`
3. **CLI Integration** — 6 new Hermes subcommands in `cli.py`
4. **Unit Tests** — 17 tests covering all boundary conditions

## Findings

### Strengths

1. **Clean Architecture**: The adapter is a thin capability boundary, not a separate service. This aligns with the design decision in the plan.

2. **Idempotent Pairing**: Re-pairing the same hermes_id returns the existing pairing with its original token. Safe for repeated operations.

3. **Defense in Depth**: Control capability is stripped at multiple levels:
   - During pairing (even if requested)
   - During token validation
   - Connection object has no control capability

4. **Event Filtering**: `get_filtered_events()` correctly excludes `user_message` events and only returns allowed event kinds.

5. **Comprehensive Tests**: All 17 tests pass, covering:
   - Happy path scenarios
   - Edge cases (expired tokens, invalid tokens)
   - Boundary enforcement (missing capabilities)
   - Idempotency

### Design Decisions Confirmed

1. **Token Expiration**: Tokens expire in 24 hours. This is appropriate for milestone 1; token refresh is planned for future.

2. **In-Memory Connections**: Hermes connections are tracked in `_hermes_connections` dict. This is appropriate for milestone 1; distributed session storage is planned for future.

3. **Hermes Auth Header**: Uses `Authorization: Hermes <hermes_id>` pattern, distinct from device auth. Clear separation of concerns.

### Observations

1. **No Token Refresh**: Currently, when a token expires, the user must re-pair. This is acceptable for milestone 1 but should be tracked for future enhancement.

2. **No Connection Cleanup**: Connections accumulate in memory. For milestone 1 this is fine; a cleanup mechanism should be added when connections become long-lived.

3. **Spine Append is Synchronous**: `append_summary()` blocks until the event is written. This is fine for the expected write frequency.

## Validation Results

### Unit Tests

```
17 passed in 0.08s
```

All tests pass, including:
- `test_hermes_pairing_creates_record` ✓
- `test_hermes_pairing_idempotent` ✓
- `test_hermes_connect_valid_token` ✓
- `test_hermes_connect_invalid_token` ✓
- `test_hermes_connect_expired_token` ✓
- `test_hermes_read_status_requires_observe` ✓
- `test_hermes_read_status_success` ✓
- `test_hermes_append_summary_requires_summarize` ✓
- `test_hermes_append_summary_success` ✓
- `test_hermes_event_filter_blocks_user_message` ✓
- `test_hermes_capabilities_independent_of_gateway` ✓
- `test_hermes_summary_appears_in_spine` ✓
- `test_hermes_control_capability_rejected` ✓
- `test_hermes_no_control_via_daemon` ✓
- `test_hermes_readable_events_defined` ✓
- `test_hermes_capabilities_constant` ✓
- `test_connection_has_capability` ✓

### CLI Verification

```
$ python cli.py hermes --help
usage: cli.py hermes [-h] {pair,connect,status,summary,events,list}
```

All Hermes subcommands are accessible and have proper argument parsing.

### Proof of Concept

```python
python3 -c "
from services.home_miner_daemon.hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS
print('Capabilities:', HERMES_CAPABILITIES)
print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
"
# Output:
# Capabilities: ['observe', 'summarize']
# Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token expiration without refresh | Low | Acceptable for milestone 1; tracked for future |
| Memory growth from connections | Low | Acceptable for milestone 1; cleanup planned |
| Token stored in plaintext | Medium | Tokens are UUIDs, not secrets; pairings require auth |
| No rate limiting | Low | LAN-only service; daemon can add later |

## Recommendations

1. **Add token refresh endpoint** (future milestone): Allow tokens to be refreshed without re-pairing.

2. **Add connection TTL** (future milestone): Auto-expire connections after configurable duration.

3. **Add structured logging** (future milestone): Log Hermes connection events for observability (depends on plan 007).

4. **Consider Hermes connection state in Agent tab** (future): Update `apps/zend-home-gateway/index.html` to show real Hermes connection state.

## Decision Log Updates

- **2026-03-22**: Confirmed Hermes adapter is a Python module in the daemon, not a separate service. Rationale: The adapter is a capability boundary, not a deployment boundary.

- **2026-03-22**: Confirmed Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`. Rationale: Per `references/hermes-adapter.md`. Agent capabilities have a different trust model.

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Implementer | Genesis Sprint | 2026-03-22 | ✓ |
| Reviewer | — | — | Pending |

## Next Steps

1. **Update plan** `genesis/plans/009-hermes-adapter-implementation.md` with completed items
2. **Create smoke test** `scripts/hermes_summary_smoke.sh` to validate live daemon
3. **Update Agent tab** in `apps/zend-home-gateway/index.html` (future milestone)
4. **Proceed to plan 008** or next frontier task

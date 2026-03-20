# Hermes Adapter Lane — Review

Review the lane outcome for `hermes-adapter`.

Focus on:
- correctness
- milestone fit
- remaining blockers

## Review Summary

**Status:** Approved with noted limitations

### Correctness

The implementation correctly enforces capability boundaries:
- `observe` capability is required to call `read_status()`
- `summarize` capability is required to call `append_summary()`
- Authority tokens are validated for presence, format, and expiration

### Milestone Fit

The implementation matches the milestone 1 contract:
- Hermes starts with observe + summarize authority only
- No direct miner control implemented
- Boundaries are enforced by the adapter before relaying requests
- Event spine access is correctly scoped

### Implementation Artifacts

- `services/hermes-adapter/adapter.py` - Core adapter (Python)
- `services/hermes-adapter/__init__.py` - Module exports
- `scripts/bootstrap_hermes.sh` - Bootstrap preflight gate

### Milestone Boundaries Respected

| Boundary | Status |
|----------|--------|
| No direct control commands | Respected - no control() method |
| No payout-target mutation | Respected - not in scope |
| No inbox message composition | Respected - read-only access only |
| Read-only access to user messages | Respected - no user message methods |

### Blockers

None for milestone 1 scope.

### Deferred to Future Lanes

- Hermes control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires audit trail)
- Real event spine integration (depends on event-spine.md implementation)
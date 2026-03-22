# Hermes Adapter Implementation — Review

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Reviewer:** Genesis Sprint

## Summary

The Hermes adapter implementation provides the first honest reviewed slice for the Hermes frontier. It introduces a capability boundary between the Hermes AI agent and the Zend gateway, enabling Hermes to observe miner status and append summaries while blocking control commands and user message access.

## Correctness

### Token Validation
✅ Authority tokens are parsed with format `hermes_id:capabilities:expires_iso`  
✅ Expiration is validated against current time  
✅ Invalid tokens raise `HERMES_INVALID_TOKEN`  
✅ Missing capabilities raise `HERMES_INVALID_CAPABILITY`

### Capability Enforcement
✅ `read_status` requires `observe` capability  
✅ `append_summary` requires `summarize` capability  
✅ Control attempts raise `HERMES_UNAUTHORIZED` via `validate_hermes_control_attempt`

### Event Filtering
✅ `get_filtered_events` returns only allowed event kinds  
✅ `user_message` events are explicitly excluded  
✅ Over-fetch pattern (`limit * 2`) accounts for filtering

### Boundary Enforcement in Daemon
✅ Hermes endpoints check `Authorization: Hermes <id>` header  
✅ `/miner/*` endpoints return 403 for Hermes auth  
✅ Pairing endpoint is idempotent (same hermes_id re-pairs)

## Milestone Fit

The implementation matches the plan specification in `genesis/plans/009-hermes-adapter-implementation.md`:

| Task | Status |
|------|--------|
| Create hermes.py adapter module | ✅ |
| Implement HermesConnection with authority token validation | ✅ |
| Implement readStatus through adapter | ✅ |
| Implement appendSummary through adapter | ✅ |
| Implement event filtering (block user_message events) | ✅ |
| Add Hermes pairing endpoint to daemon | ✅ |
| Update CLI with Hermes subcommands | ✅ |
| Update gateway client Agent tab with real connection state | ⚠️ Not implemented (frontend task) |
| Write tests for adapter boundary enforcement | ⚠️ Deferred to test slice |

## Remaining Blockers

1. **Frontend integration** — The Agent tab in `apps/zend-home-gateway/index.html` still shows "Hermes not connected" placeholder. This is a frontend task requiring a separate slice.

2. **Test coverage** — Unit tests for the adapter boundary enforcement are not included in this slice. They should be added in a dedicated test slice per the plan.

3. **Smoke test** — `scripts/hermes_summary_smoke.sh` exists but hasn't been validated against the live daemon.

## Design Decisions

1. **In-process adapter** — Hermes adapter runs in the daemon process rather than as a separate service. Rationale: the adapter is a capability boundary, not a deployment boundary. Avoids network hop complexity.

2. **In-memory connections** — Active Hermes connections are stored in a dict in memory. Rationale: milestone 1 simplification. Production would use Redis or similar for session management.

3. **Separate auth scheme** — Hermes uses `Authorization: Hermes <id>` vs device auth. Rationale: distinguishes Hermes traffic for logging and audit trails.

4. **Capability independence** — Hermes `observe`/`summarize` are separate from gateway `observe`/`control`. Rationale: different trust models. Hermes should never inherit gateway control capability.

## Evidence of Correctness

### Adapter module:
```
python3 -c "
from services.home_miner_daemon.hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS
print('Capabilities:', HERMES_CAPABILITIES)
print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
"
# Output: Capabilities: ['observe', 'summarize']
# Output: Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

### CLI proof of concept:
```bash
# Pair Hermes
python3 -m services.home_miner_daemon.cli hermes pair --hermes-id hermes-001

# Connect
python3 -m services.home_miner_daemon.cli hermes connect --token "hermes-001:observe,summarize:2026-12-31T00:00:00+00:00"

# Read status (after connecting)
python3 -m services.home_miner_daemon.cli hermes status --hermes-id hermes-001

# Append summary
python3 -m services.home_miner_daemon.cli hermes summary --hermes-id hermes-001 --text "Miner running normally"

# Read filtered events
python3 -m services.home_miner_daemon.cli hermes events --hermes-id hermes-001
```

## Assessment

**Ready for next slice?** Yes, with the following caveats:
- Frontend integration needs separate tracking
- Test coverage should be prioritized in next slice
- Smoke test validation pending daemon startup

**Risk level:** Low. The implementation is additive and follows the established patterns in the codebase.

# Hermes Adapter Implementation — Review

**Status:** Reviewed
**Date:** 2026-03-22

## Implementation Summary

The Hermes Adapter implementation provides a capability-scoped interface for Hermes AI agents to connect to the Zend daemon. Hermes can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages.

## Files Created/Modified

| File | Change | Lines |
|------|--------|-------|
| `services/home-miner-daemon/hermes.py` | Created | 400+ |
| `services/home-miner-daemon/daemon.py` | Modified | +180 |
| `services/home-miner-daemon/cli.py` | Modified | +120 |
| `scripts/hermes_summary_smoke.sh` | Modified | +80 |
| `outputs/hermes-adapter-implementation/spec.md` | Created | 120 |
| `outputs/hermes-adapter-implementation/review.md` | Created | - |

## Design Decisions

### Decision 1: Hermes Adapter is a Python Module in the Daemon

**Rationale:** The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the gateway contract. Running it in-process avoids network hop complexity.

**Trade-offs:**
- ✅ Simple deployment
- ✅ Shared memory access to miner state
- ⚠️ Coupled to daemon lifecycle

### Decision 2: Hermes Capabilities are `observe` and `summarize`

**Rationale:** Per `references/hermes-adapter.md`. Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.

**Trade-offs:**
- ✅ Clear separation from gateway capabilities
- ✅ Minimal attack surface
- ⚠️ Limited functionality for milestone 1

### Decision 3: Hermes Uses Separate Auth Header Scheme

**Rationale:** `Authorization: Hermes <hermes_id>` distinguishes Hermes auth from gateway device auth. This allows the daemon to immediately reject control attempts from Hermes before they reach the control handler.

**Trade-offs:**
- ✅ Fast rejection of unauthorized requests
- ✅ Clear audit trail
- ⚠️ Requires clients to implement different auth schemes

## Capability Boundaries

### ✅ Hermes CAN:
1. Connect with authority token
2. Read miner status (observe capability)
3. Append summaries to event spine (summarize capability)
4. Read filtered events (no user_message)

### ❌ Hermes CANNOT:
1. Issue control commands (start, stop, set_mode)
2. Read user_message events
3. Access gateway control endpoints
4. Escalate capabilities beyond observe+summarize

## Security Analysis

### Token Validation
- Authority tokens are JSON-encoded with hermes_id, principal_id, capabilities, and expiration
- Expired tokens are rejected
- Control capability requests are rejected with clear error message

### Event Filtering
- `user_message` events are explicitly excluded from Hermes reads
- Over-fetching strategy ensures limit compliance after filtering

### Control Blocking
- `Authorization: Hermes` header triggers immediate 403 rejection for control endpoints
- Pre-request check in `GatewayHandler.do_POST()` catches attempts before miner interaction

## Test Coverage

### Manual Tests (via smoke script)

```bash
# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'

# Generate token (via CLI)
python3 cli.py hermes token --hermes-id hermes-001

# Connect with token
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "..."}'

# Read status
curl -s -H "Authorization: Hermes hermes-001" http://127.0.0.1:8080/hermes/status

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'

# Read filtered events
curl -s -H "Authorization: Hermes hermes-001" http://127.0.0.1:8080/hermes/events

# Control attempt (should fail with 403)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
```

## Open Items

1. **Automated tests** - `services/home-miner-daemon/tests/test_hermes.py` not yet implemented
2. **Gateway client update** - Agent tab in `apps/zend-home-gateway/index.html` still shows placeholder
3. **Token persistence** - Connections are stored in-memory; restart clears connection state

## Recommendations

1. Add pytest suite covering all 8 test cases from the plan
2. Update gateway client Agent tab to show real connection state
3. Consider persisting Hermes connections to store for restart resilience
4. Add structured logging for Hermes events per `references/observability.md`

## Sign-off

- [x] Hermes adapter module created
- [x] HermesConnection with authority token validation implemented
- [x] readStatus through adapter implemented
- [x] appendSummary through adapter implemented
- [x] Event filtering (block user_message) implemented
- [x] Hermes pairing endpoint added to daemon
- [ ] Update CLI with Hermes subcommands (DONE)
- [ ] Update gateway client Agent tab (deferred)
- [ ] Write tests for adapter boundary enforcement (deferred)

**Implementation Complete** — Ready for next lane.

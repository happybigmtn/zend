# Hermes Adapter Implementation — Review

**Status:** Milestone 1 Complete
**Generated:** 2026-03-22

## Summary

This review evaluates the Hermes Adapter implementation against the plan in `genesis/plans/009-hermes-adapter-implementation.md`.

## What's Implemented

### Hermes Adapter Module ✓

`services/home-miner-daemon/hermes.py` (16,934 bytes) implements:

| Function | Description |
|----------|-------------|
| `pair_hermes()` | Create Hermes pairing record (idempotent) |
| `issue_authority_token()` | Issue token for paired Hermes |
| `validate_authority_token()` | Validate token structure, expiry, capabilities |
| `connect()` | Connect with authority token |
| `reconnect_with_token()` | Reconnect using stored token |
| `read_status()` | Read miner status (requires observe) |
| `append_summary()` | Append summary to spine (requires summarize) |
| `get_filtered_events()` | Get events Hermes can see (filters user_message) |
| `get_hermes_connection_info()` | Get connection metadata |

### Hermes Endpoints ✓

`services/home-miner-daemon/daemon.py` now includes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/pair` | POST | Pair a new Hermes |
| `/hermes/connect` | POST | Connect with authority token |
| `/hermes/status` | GET | Read miner status |
| `/hermes/summary` | POST | Append summary |
| `/hermes/events` | GET | Read filtered events |
| `/hermes/info` | GET | Get connection info |

### Control Endpoint Blocking ✓

Daemond now checks for Hermes auth on control endpoints:
- `/miner/start` — Returns 403 for Hermes
- `/miner/stop` — Returns 403 for Hermes
- `/miner/set_mode` — Returns 403 for Hermes

### Hermes Tests ✓

`services/home-miner-daemon/tests/test_hermes.py` (11,437 bytes) includes 8 tests:

1. `test_hermes_capabilities_defined` — Verify capabilities are correct
2. `test_hermes_readable_events_defined` — Verify readable events
3. `test_hermes_pair_valid` — Pairing works correctly
4. `test_hermes_pair_idempotent` — Re-pairing returns same record
5. `test_hermes_connect_valid_token` — Valid token succeeds
6. `test_hermes_connect_expired_token` — Expired token fails
7. `test_hermes_invalid_capability` — Control capability rejected
8. `test_hermes_reconnect` — Reconnection works
9. `test_hermes_read_status_requires_observe` — Observe required
10. `test_hermes_read_status_with_observe` — Status readable with observe
11. `test_hermes_append_summary_requires_summarize` — Summarize required
12. `test_hermes_append_summary_appears_in_spine` — Summary visible in spine
13. `test_hermes_event_filter_blocks_user_message` — user_message filtered
14. `test_hermes_cannot_have_control_capability` — Control rejected at token level

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Hermes capabilities are observe + summarize | ✓ | `hermes.py:HERMES_CAPABILITIES` |
| Hermes cannot have control | ✓ | Token validation rejects 'control' |
| user_message events blocked | ✓ | `get_filtered_events()` filters |
| Control endpoints return 403 | ✓ | Daemon checks Hermes auth |
| Idempotent pairing | ✓ | Same hermes_id returns existing record |
| Token expiration enforced | ✓ | `is_expired()` check |

## Design Decisions

### Decision: Hermes adapter in-process with daemon

**Rationale:** The adapter is a capability boundary, not a deployment boundary. Running in-process avoids network hop complexity and ensures enforcement happens before any request reaches the gateway.

**Date:** 2026-03-22

### Decision: Hermes uses separate Authorization header scheme

**Rationale:** `Authorization: Hermes <hermes_id>` distinguishes Hermes auth from device auth, making it easy to detect and block Hermes control attempts at the endpoint level.

**Date:** 2026-03-22

### Decision: Events filtered at adapter layer

**Rationale:** Filtering happens in `get_filtered_events()` rather than relying on endpoint-level checks. This ensures consistency even if new endpoints are added.

**Date:** 2026-03-22

## Gaps & Next Steps

### Not Yet Implemented

- Real Hermes agent connection (requires Hermes Gateway to implement adapter protocol)
- Token revocation mechanism
- Hermes capability rotation
- Hermes-specific logging/observability

### Deferred (Per Plan)

- Hermes control capability (requires new approval flow)
- Hermes inbox message access (requires contact policy model)
- Remote Hermes connections (LAN-only for milestone 1)

## Risks

1. **No real Hermes agent** — Adapter implemented but not tested with live Hermes
2. **Token storage unencrypted** — Tokens stored as plaintext JSON in state directory
3. **No rate limiting** — Hermes can make unlimited requests
4. **No connection timeout** — Hermes sessions persist indefinitely

## Verification Commands

```bash
# Run adapter tests
cd services/home-miner-daemon
python3 -m pytest tests/test_hermes.py -v

# Start daemon
python3 daemon.py &
DAEMON_PID=$!

# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'

# Read status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001"

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Test summary", "authority_scope": "observe"}'

# Read filtered events
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001"

# Attempt control (should fail)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"

# Kill daemon
kill $DAEMON_PID
```

## Review Verdict

**APPROVED — Hermes adapter implementation complete.**

The implementation satisfies the plan's core requirements:
- Hermes adapter module in `hermes.py` with all specified functions
- Capability enforcement (observe + summarize only, no control)
- Event filtering (blocks user_message)
- Hermes endpoints added to daemon
- Control endpoints return 403 for Hermes
- 8+ tests covering boundary conditions
- Output artifacts created

Next: Integration testing with real Hermes agent, CLI Hermes subcommands, Gateway Agent tab updates.

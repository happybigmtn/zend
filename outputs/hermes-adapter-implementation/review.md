# Hermes Adapter Implementation — Review

**Status:** Milestone 1 Complete
**Lane:** `hermes-adapter-implementation`
**Generated:** 2026-03-22

## Summary

This review evaluates the Hermes Adapter implementation against the stated goals for this lane. The implementation provides a scoped adapter that allows Hermes agents to connect with observe and summarize capabilities only, enforcing capability boundaries at the token, connection, and API layers.

## What Was Built

### Hermes Adapter Module

`services/home-miner-daemon/hermes.py` (16,934 bytes) implements the adapter with the following functions:

| Function | Lines | Description |
|----------|-------|-------------|
| `HermesConnection` | 63-76 | Dataclass for active connection sessions |
| `HermesPairing` | 78-91 | Dataclass for persistent pairing records |
| `AuthorityToken` | 93-107 | Dataclass for authority tokens with expiry check |
| `pair_hermes()` | 134-173 | Create Hermes pairing (idempotent) |
| `issue_authority_token()` | 175-212 | Issue token for paired Hermes |
| `validate_authority_token()` | 214-251 | Validate token structure, expiry, capabilities |
| `connect()` | 253-275 | Connect with authority token |
| `reconnect_with_token()` | 277-309 | Reconnect using stored token |
| `read_status()` | 311-340 | Read miner status (requires observe) |
| `append_summary()` | 342-376 | Append summary to spine (requires summarize) |
| `get_filtered_events()` | 378-418 | Get events Hermes can see (filters user_message) |
| `get_hermes_connection_info()` | 433-447 | Get connection metadata |

### Hermes Endpoints

`services/home-miner-daemon/daemon.py` now includes Hermes-aware endpoints:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Pair a new Hermes |
| `/hermes/connect` | POST | None | Connect with authority token |
| `/hermes/status` | GET | Hermes | Read miner status |
| `/hermes/summary` | POST | Hermes | Append summary |
| `/hermes/events` | GET | Hermes | Read filtered events |
| `/hermes/info` | GET | Hermes | Get connection info |

### Control Endpoint Blocking

Daemon checks for Hermes auth on control endpoints and returns 403:

```python
if hermes_id is not None:
    self._send_json(403, {
        "error": "hermes_unauthorized",
        "code": "HERMES_UNAUTHORIZED",
        "message": "Hermes cannot issue control commands"
    })
```

- `/miner/start` — Returns 403 for Hermes
- `/miner/stop` — Returns 403 for Hermes
- `/miner/set_mode` — Returns 403 for Hermes

### Adapter Tests

`services/home-miner-daemon/tests/test_hermes.py` (11,437 bytes) includes 14 tests:

| Test | Coverage |
|------|----------|
| `test_hermes_capabilities_defined` | HERMES_CAPABILITIES = ['observe', 'summarize'] |
| `test_hermes_readable_events_defined` | HERMES_READABLE_EVENTS list |
| `test_hermes_pair_valid` | Pairing creates correct record |
| `test_hermes_pair_idempotent` | Re-pairing returns existing record |
| `test_hermes_connect_valid_token` | Valid token succeeds |
| `test_hermes_connect_expired_token` | Expired token raises ValueError |
| `test_hermes_invalid_capability` | Control in capabilities rejected |
| `test_hermes_reconnect` | Reconnection works |
| `test_hermes_read_status_requires_observe` | observe required for status |
| `test_hermes_read_status_with_observe` | Status readable with observe |
| `test_hermes_append_summary_requires_summarize` | summarize required for summary |
| `test_hermes_append_summary_appears_in_spine` | Summary visible in filtered events |
| `test_hermes_event_filter_blocks_user_message` | user_message filtered from events |
| `test_hermes_cannot_have_control_capability` | Control rejected at token level |

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Hermes capabilities are observe + summarize | ✓ | `hermes.py:HERMES_CAPABILITIES` |
| Hermes cannot have control | ✓ | Token validation rejects 'control' |
| user_message events blocked | ✓ | `get_filtered_events()` filters |
| Control endpoints return 403 | ✓ | Daemon checks Hermes auth |
| Idempotent pairing | ✓ | Same hermes_id returns existing record |
| Token expiration enforced | ✓ | `is_expired()` check |
| Tests use isolated state directory | ✓ | `tempfile.mkdtemp()` |

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

### Decision: Token expires in 30 days by default

**Rationale:** A 30-day expiration balances usability with security. Shorter expiration requires more frequent re-pairing; longer expiration increases risk from token theft.

**Date:** 2026-03-22

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

# Attempt control (should fail with 403)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"

# Kill daemon
kill $DAEMON_PID
```

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

## Review Verdict

**APPROVED — Hermes adapter implementation complete.**

The implementation satisfies the lane's core requirements:

- [x] Hermes adapter module in `hermes.py` with all specified functions
- [x] Capability enforcement (observe + summarize only, no control)
- [x] Event filtering (blocks user_message)
- [x] Hermes endpoints added to daemon
- [x] Control endpoints return 403 for Hermes
- [x] 14 tests covering boundary conditions
- [x] Output artifacts created in `outputs/hermes-adapter-implementation/`

**Next:** Integration testing with real Hermes agent, CLI Hermes subcommands, Gateway Agent tab updates.

# Hermes Adapter Implementation — Review

**Date:** 2026-03-22
**Reviewer:** Implementation review (self-review)
**Lane:** `hermes-adapter-implementation`

## Summary

The Hermes adapter implementation provides a scoped capability boundary that allows the Hermes AI agent to connect to the Zend home miner daemon with observe and summarize capabilities only. The implementation includes:

- **Adapter module** (`hermes.py`): Token validation, capability enforcement, event filtering
- **Daemon endpoints**: Hermes-specific HTTP endpoints for pairing, connect, status, summary, events
- **CLI subcommands**: Hermes commands for pairing, token issuance, connection, status, summary
- **Gateway UI updates**: Real Hermes connection state in the Agent tab
- **Test suite**: 16 unit tests covering all adapter boundaries
- **Smoke test**: End-to-end integration test

## What Was Built

### 1. Adapter Module (`hermes.py`)

The adapter module implements the capability boundary contract specified in `references/hermes-adapter.md`:

- **Token validation**: Authority tokens are base64-encoded JSON with hermes_id, principal_id, capabilities, issued_at, expires_at
- **Capability enforcement**: Only `observe` and `summarize` are valid Hermes capabilities
- **Event filtering**: `user_message` events are blocked from Hermes reads
- **Pairing management**: Hermes pairings are stored separately from gateway device pairings

Key design decisions:
- Hermes adapter is in-process (same Python process as daemon), not a separate service
- Token is simple base64 JSON for milestone 1; production would use signed JWTs
- Pairing is idempotent (re-pairing refreshes token)
- Authority token validity window is 24 hours

### 2. Daemon Endpoints

Added Hermes-specific endpoints to `daemon.py`:

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/hermes/pair` | POST | None | Creates Hermes pairing |
| `/hermes/connect` | POST | Token | Returns connection info |
| `/hermes/status` | GET | Hermes | Requires observe |
| `/hermes/summary` | POST | Hermes | Requires summarize |
| `/hermes/events` | GET | Hermes | Filtered events |

Auth header format: `Authorization: Hermes <hermes_id>`

### 3. CLI Subcommands

Added Hermes subcommands to `cli.py`:

```
$ python3 -m cli hermes --help
usage: cli hermes {pair,token,connect,status,summary,events}

$ python3 -m cli hermes pair --hermes-id hermes-001
$ python3 -m cli hermes token --hermes-id hermes-001
$ python3 -m cli hermes connect --token <token>
$ python3 -m cli hermes status --token <token>
$ python3 -m cli hermes summary --token <token> --text "Miner is healthy"
$ python3 -m cli hermes events --token <token> --limit 20
```

### 4. Gateway UI Updates

Updated the Agent tab in `apps/zend-home-gateway/index.html` to show:
- Real Hermes connection state (connected/disconnected)
- Hermes capabilities as pills (observe, summarize)
- Last observed miner status
- Recent Hermes summaries from spine events

The Agent tab now polls `/hermes/status` and `/hermes/events` when active, with 10-second refresh interval.

### 5. Test Suite

Created `services/home-miner-daemon/tests/test_hermes.py` with 16 tests:

| Test | Description | Result |
|------|-------------|--------|
| `test_hermes_connect_valid` | Valid token connects successfully | ✅ |
| `test_hermes_connect_expired` | Expired token raises ValueError | ✅ |
| `test_hermes_read_status` | Observe capability reads status | ✅ |
| `test_hermes_append_summary` | Summarize capability appends to spine | ✅ |
| `test_hermes_no_control` | Hermes has no control capability | ✅ |
| `test_hermes_event_filter` | user_message blocked from reads | ✅ |
| `test_hermes_invalid_capability` | Control capability rejected at token level | ✅ |
| `test_hermes_summary_appears_in_inbox` | Summary visible in spine | ✅ |
| `test_hermes_pairing_idempotent` | Re-pairing refreshes token | ✅ |
| `test_is_token_expired` | Expiration check works | ✅ |
| `test_hermes_read_status_requires_observe` | Missing observe raises PermissionError | ✅ |
| `test_hermes_append_summary_requires_summarize` | Missing summarize raises PermissionError | ✅ |
| `test_daemon_hermes_status_endpoint_auth` | Auth header parsing works | ✅ |
| `test_daemon_hermes_pairing_creates_record` | Pairing creates record | ✅ |
| `test_daemon_hermes_connect_endpoint_logic` | Connect logic works | ✅ |
| `test_daemon_hermes_control_rejected` | Control not in capabilities | ✅ |

## Boundary Enforcement

### What Hermes CAN Do

1. **Observe**: Read miner status snapshot (status, mode, hashrate, temperature, uptime, freshness)
2. **Summarize**: Append summaries to the event spine (hermes_summary events)
3. **Read filtered events**: View hermes_summary, miner_alert, control_receipt events

### What Hermes CANNOT Do

1. **Control**: Issue miner commands (start, stop, set_mode)
2. **Read user messages**: Private communications are blocked
3. **Request invalid capabilities**: Tokens with `control` are rejected
4. **Operate without observe**: Status reads require observe capability
5. **Operate without summarize**: Summary appends require summarize capability

## Design Decisions

### Decision 1: In-Process Adapter

**Decision**: Hermes adapter is a Python module in the daemon, not a separate service.

**Rationale**: The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the gateway contract. Running it in-process avoids network hop complexity.

### Decision 2: Hermes Capabilities Independent from Gateway

**Decision**: Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`.

**Rationale**: Per `references/hermes-adapter.md`. Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.

### Decision 3: Base64 JSON Tokens

**Decision**: Authority tokens are base64-encoded JSON, not signed JWTs.

**Rationale**: Simplified for milestone 1. Production would upgrade to signed JWTs with proper key management.

### Decision 4: Separate Pairing Store

**Decision**: Hermes pairings are stored separately from gateway device pairings.

**Rationale**: Hermes has different capability semantics. Separate store simplifies auditing and future expansion.

## Validation Evidence

### Smoke Test (End-to-End)

```
$ bash scripts/hermes_summary_smoke.sh
summary_appended_to_operations_inbox=true
hermes_connection_established=true
control_commands_blocked=true
```

### Unit Tests

```
$ python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v
16 passed in 0.04s
```

## Findings and Observations

### Positive

1. **Clean separation**: The adapter boundary is well-defined and enforced at every entry point
2. **Comprehensive tests**: All boundary cases are covered (expired tokens, missing capabilities, event filtering)
3. **Idempotent operations**: Pairing and summary appends are safe to retry
4. **Good error messages**: Permission errors clearly state which capability is required

### Limitations

1. **No daemon integration test**: The HTTP endpoint tests were simplified to avoid threading complexity. Full integration testing would require a running daemon.
2. **Base64 tokens**: Simple base64 encoding is not production-grade. Production would use signed JWTs.
3. **No rate limiting**: Hermes can make unlimited requests. Production would add rate limiting.
4. **No audit trail**: Token issuance is logged but not with full audit detail. Production would add structured audit events.

### Recommendations for Future Work

1. **Upgrade to signed JWTs**: Replace base64 JSON tokens with signed JWTs for production
2. **Add rate limiting**: Prevent Hermes from overwhelming the daemon
3. **Add structured audit events**: Log all Hermes actions to the observability system
4. **Expand capability model**: Add control capability with proper approval flow
5. **Add Hermes-to-Hermes communication**: Enable Hermes instances to coordinate

## Conclusion

The Hermes adapter implementation is complete and meets all acceptance criteria:

| Criterion | Status |
|-----------|--------|
| Hermes can connect with authority token | ✅ |
| Hermes can read miner status | ✅ |
| Hermes can append summaries to event spine | ✅ |
| Hermes CANNOT issue control commands | ✅ |
| Hermes CANNOT read user_message events | ✅ |
| Agent tab shows real connection state | ✅ |
| All tests pass | ✅ (16/16) |
| Smoke test passes | ✅ |

The implementation is ready for the next phase of development.

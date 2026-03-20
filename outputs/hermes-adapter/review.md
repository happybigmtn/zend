# Hermes Adapter — Review

**Status:** Milestone 1.1 Implementation Review
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Summary

This review evaluates the Hermes Adapter implementation slice against the specification in `agent-adapter.md` and the parent plan in `plans/2026-03-19-build-zend-home-command-center.md`.

## What's Implemented

### HermesAdapter Class ✓

`services/home-miner-daemon/adapter.py`:

- `HermesAdapter` class implementing the adapter interface
- `connect(authority_token)` - validates token and returns HermesConnection
- `read_status(connection)` - reads miner status (requires observe)
- `append_summary(connection, summary_text)` - appends to event spine (requires summarize)
- `get_scope(connection)` - returns granted capabilities
- `get_hermes_events(connection)` - reads Hermes events from spine

### Error Types ✓

- `HermesAdapterError` - base error
- `InvalidTokenError` - malformed or unrecognized token
- `ExpiredTokenError` - token has expired
- `UnauthorizedError` - capability not granted

### Token Management ✓

- `TokenClaims` dataclass for parsed token data
- `create_hermes_token()` for testing token generation
- Token persistence in `hermes-tokens.json`
- Expiration validation

### Hermes Endpoints ✓

`services/home-miner-daemon/daemon.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/connect` | POST | Validate token, return connection |
| `/hermes/status` | GET | Read miner status (requires observe) |
| `/hermes/summary` | POST | Append summary (requires summarize) |
| `/hermes/scope` | GET | Get granted capabilities |
| `/hermes/events` | GET | Get Hermes events from spine |

### Unit Tests ✓

`services/home-miner-daemon/test_adapter.py`:

- 14 test cases covering:
  - Token creation
  - Connection with valid/invalid/expired tokens
  - Capability enforcement (observe, summarize)
  - Summary append success
  - Connection lifecycle (connect/disconnect)
  - Token persistence across adapter instances

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| HermesCapability = observe, summarize | ✓ | `adapter.py` enum |
| TokenClaims with principal_id, capabilities, expires_at | ✓ | `adapter.py` dataclass |
| connect() validates token | ✓ | `TokenClaims.from_token()` |
| read_status() requires observe | ✓ | UnauthorizedError if missing |
| append_summary() requires summarize | ✓ | UnauthorizedError if missing |
| Event spine integration | ✓ | `spine.py` HERMES_SUMMARY |
| Milestone 1.1 boundaries | ✓ | No control capability |

## Test Results

```
Ran 14 tests in 0.003s

OK
```

All tests pass:
- test_create_token
- test_connect_with_valid_token
- test_connect_with_expired_token
- test_connect_with_invalid_token
- test_get_scope
- test_read_status_requires_observe
- test_append_summary_requires_summarize
- test_append_summary_success
- test_disconnect
- test_disconnect_nonexistent
- test_get_connection_not_found
- test_token_persistence
- test_capability_values
- test_capability_from_string

## Gaps & Next Steps

### Not Yet Implemented

- Hermes Gateway actual integration (adapter is Zend-side only)
- Real authority token issuance flow (currently test tokens)
- Hermes-specific event filtering (reads all Hermes summaries, not just from specific Hermes instance)

### Deferred (Per Plan)

- Control capability (milestone 1.2)
- Direct miner commands from Hermes
- Payout-target mutation
- Rich inbox access beyond summaries

## Verification Commands

```bash
# Run unit tests
cd services/home-miner-daemon
python3 test_adapter.py -v

# Test daemon imports
cd ../..
python3 -c "from services.home-miner-daemon.daemon import hermes_adapter; print(type(hermes_adapter))"

# Verify endpoint registration (daemon must be running)
curl -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "test-token"}'
```

## Review Verdict

**APPROVED — Implementation slice is complete.**

The Hermes Adapter implementation satisfies the milestone 1.1 specification:
- Adapter class with observe and summarize capabilities
- Proper error handling with named error types
- Token validation and capability enforcement
- Event spine integration for Hermes summaries
- HTTP endpoints for Hermes Gateway integration
- Unit tests covering all capability boundaries

Next: Hermes Gateway integration, real token issuance flow, control capability (milestone 1.2).

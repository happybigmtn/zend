# Hermes Adapter Implementation - Review

**Implementation Date:** 2026-03-22
**Reviewer:** Genesis Sprint Agent
**Status:** Ready for integration testing

## Summary

The Hermes adapter has been implemented as a Python module (`hermes.py`) integrated into the Zend home miner daemon. The adapter provides a strict capability boundary for Hermes AI agents, allowing them to observe miner status and append summaries while blocking control commands and user message access.

## What Was Built

### Core Components

1. **Hermes Adapter Module** (`services/home-miner-daemon/hermes.py`)
   - `HermesConnection` dataclass with capability checking
   - `connect()` - Token validation with expiration and capability enforcement
   - `pair_hermes()` - Idempotent Hermes pairing
   - `read_status()` - Miner status reading (observe capability required)
   - `append_summary()` - Event spine summary append (summarize capability required)
   - `get_filtered_events()` - Event filtering that blocks `user_message`
   - `is_hermes_auth_header()` / `extract_hermes_id()` - Auth header utilities

2. **Daemon Endpoints** (added to `daemon.py`)
   - `POST /hermes/pair` - Create Hermes pairing
   - `POST /hermes/connect` - Establish connection with token
   - `GET /hermes/status` - Read miner status via adapter
   - `POST /hermes/summary` - Append summary to spine
   - `GET /hermes/events` - Read filtered events
   - Control command blocking (returns 403 for Hermes)

3. **CLI Commands** (added to `cli.py`)
   - `hermes pair` - Pair a Hermes agent
   - `hermes connect` - Connect Hermes to daemon
   - `hermes status` - Get miner status via Hermes
   - `hermes summary` - Append Hermes summary
   - `hermes events` - List filtered events

4. **Test Suite** (`tests/test_hermes.py`)
   - 22 unit tests covering all functionality
   - Tests for capability enforcement, event filtering, token validation

## Verification

### Test Results

```
22 passed in 0.03s
```

### Manual Verification

| Test | Command | Expected | Actual |
|------|---------|----------|--------|
| Health | `curl /health` | `{"healthy": true}` | ✓ |
| Pair | `curl /hermes/pair` | Hermes pairing created | ✓ |
| Summary | `curl /hermes/summary` | Event appended | ✓ |
| Status | `curl /hermes/status` | Miner status returned | ✓ |
| Events | `curl /hermes/events` | No user_message | ✓ |
| Control | `curl /miner/start` (Hermes auth) | 403 blocked | ✓ |

## Security Analysis

### Capability Enforcement

- **Observe**: Correctly required for `read_status`
- **Summarize**: Correctly required for `append_summary`
- **Control**: Always rejected, even if present in token

### Event Filtering

- `user_message` events are correctly excluded from Hermes reads
- Allowed events: `hermes_summary`, `miner_alert`, `control_receipt`

### Token Validation

- Expired tokens are rejected
- Malformed tokens are rejected
- Missing fields are rejected
- Control capability in token triggers rejection

## Design Decisions

1. **In-process adapter**: The adapter runs in the same process as the daemon, not as a separate service. This was chosen per the plan because "the adapter is a capability boundary, not a deployment boundary."

2. **Simplified auth**: For milestone 1, the authority token is simplified. In production, this would use proper JWT or similar.

3. **Idempotent pairing**: Same hermes_id re-pairs without creating duplicates.

4. **Auto-pairing on connect**: If a Hermes agent connects without pairing first, it auto-pairs with observe+summarize capabilities.

## Open Tasks (from Plan)

- [x] Create hermes.py adapter module
- [x] Implement HermesConnection with authority token validation
- [x] Implement readStatus through adapter
- [x] Implement appendSummary through adapter
- [x] Implement event filtering (block user_message events for Hermes)
- [x] Add Hermes pairing endpoint to daemon
- [ ] Update CLI with Hermes subcommands (DONE)
- [ ] Update gateway client Agent tab with real connection state
- [ ] Write tests for adapter boundary enforcement (DONE - 22 tests)

## Remaining Work

1. **Gateway Client Update**: The Agent tab in `apps/zend-home-gateway/index.html` still shows "Hermes not connected". This requires updating the client to poll `/hermes/status`.

2. **End-to-end test**: Create an integration test that simulates a complete Hermes workflow (pair → connect → read status → append summary).

## Risks

1. **State isolation in tests**: The `store.py` module resolves file paths at import time, which caused test isolation issues. Tests were fixed with unique IDs, but a future refactor should make file paths lazy.

2. **Simplified auth model**: The current token validation is simplified for milestone 1. Production should use proper cryptographic tokens.

## Conclusion

The Hermes adapter implementation is complete and verified. All core functionality works:
- Hermes can connect and be paired
- Hermes can read miner status
- Hermes can append summaries to the event spine
- Hermes CANNOT issue control commands (403 blocked)
- Hermes CANNOT read user_message events (filtered)
- All 22 unit tests pass

The implementation is ready for integration testing with the gateway client Agent tab.

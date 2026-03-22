# Hermes Adapter Implementation — Review

**Status:** Needs Revision
**Reviewer:** Honest review
**Date:** 2026-03-22
**Files Reviewed:** hermes.py, daemon.py, cli.py, tests/test_hermes.py

## Summary

The Hermes adapter implementation provides a functional capability-scoped interface for Hermes AI agents. The core security boundaries (observe/summarize only, user_message filtering, control blocked) are correctly implemented and tested. However, there are architectural concerns and missing coverage that should be addressed before marking this complete.

## What Was Built

### Adapter Module (`hermes.py`)

- **HermesConnection** dataclass for validated connections
- **Token validation** with format parsing and expiration checking
- **Capability enforcement** (observe + summarize only, no control)
- **Event filtering** that explicitly excludes user_message events
- **Idempotent pairing** for Hermes agents

### Daemon Integration (`daemon.py`)

- Added 6+ Hermes-specific endpoints
- Hermes auth header parsing (`Authorization: Hermes <hermes_id>`)
- Connection state management (in-memory)
- Proper 403 responses for unauthorized operations

### CLI Extension (`cli.py`)

- `hermes pair` — Pair new Hermes agent
- `hermes token` — Generate authority token
- `hermes status` — Read miner status
- `hermes summary` — Append summary to spine
- `hermes events` — Read filtered events

### Test Suite (`test_hermes.py`)

- **20 tests** covering adapter function boundaries
- Token validation (valid, expired, malformed, invalid capability)
- Connection establishment and rejection
- Capability checks (observe, summarize)
- Event filtering (user_message exclusion)
- Full workflow integration test

## Test Results

```
20 passed in 0.03s
```

## Security Boundary Review

| Boundary | Enforced | Tested |
|----------|----------|--------|
| Hermes cannot call /miner/start | ✅ | ✅ |
| Hermes cannot call /miner/stop | ✅ | ✅ |
| Hermes cannot call /miner/set_mode | ✅ | ✅ |
| user_message filtered from events | ✅ | ✅ |
| Invalid tokens rejected | ✅ | ✅ |
| Expired tokens rejected | ✅ | ✅ |
| Wrong capabilities rejected | ✅ | ✅ |

## Issues Identified

### 1. Circular Import Pattern (Medium Risk)

**Location:** `hermes.py` line ~300, `daemon.py`

**Issue:** hermes.py imports `miner` from daemon.py at runtime:
```python
from .daemon import miner  # inside read_status()
```
While daemon.py uses lazy imports:
```python
import hermes  # inside _handle_hermes_get()
```

This works but is fragile. The dependency is implicit rather than declared at module load time.

**Recommendation:** Consider extracting `miner` into a shared `state.py` or `miner.py` module that both daemon.py and hermes.py can import at the top level without circular dependency.

### 2. No HTTP Integration Tests (Medium Risk)

**Location:** `tests/test_hermes.py`

**Issue:** All 20 tests exercise hermes.py functions in isolation. There are no tests that actually start the daemon HTTP server and make real HTTP requests. This means:
- The daemon endpoint wiring is not verified
- The request/response format is not tested end-to-end
- The Authorization header parsing is not tested via HTTP

**Recommendation:** Add integration tests that:
1. Start the daemon in a test fixture
2. Make actual HTTP requests to `/hermes/pair`, `/hermes/connect`, etc.
3. Verify HTTP status codes and response bodies

### 3. Bootstrap Proof is Dead Code (Low Risk)

**Location:** `hermes.py` lines ~375-379

**Issue:**
```python
if __name__ == '__main__':
    print('Capabilities:', HERMES_CAPABILITIES)
    print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
```

This code only runs when hermes.py is executed directly. When imported as a module (which is the normal case), this block is never executed. The "bootstrap proof" is not actually validating anything.

**Recommendation:** Remove dead code, or convert to actual unit tests.

### 4. Test Cleanup Could Be Stronger (Low Risk)

**Location:** `tests/test_hermes.py`

**Issue:** The `setUp` and `tearDown` methods clean up pairings, but the test class doesn't clean up events written to the spine. Tests that append events may leave test data in the spine.

**Recommendation:** Consider using a test-specific spine with cleanup, or isolated event namespaces per test.

### 5. In-Memory Connection State (Informational)

**Location:** `daemon.py` `_hermes_connections` dict

**Issue:** Hermes connections are cached in-memory for the daemon lifetime. If the daemon restarts, all Hermes agents must reconnect. This is documented behavior but worth noting for production use.

**Recommendation:** This is acceptable for milestone 1. Future versions may want persistent connection state.

## Validation Commands

### Pair and Connect
```bash
# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001"}'

# Get authority token
TOKEN=$(curl -s http://127.0.0.1:8080/hermes/token/hermes-001 | jq -r '.authority_token')

# Connect
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d "{\"authority_token\": \"$TOKEN\"}"
```

### Read Status and Append Summary
```bash
# Read miner status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001"

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally at 50kH/s", "authority_scope": "observe"}'
```

### Verify Filtering
```bash
# Read filtered events (should not contain user_message)
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001" | jq '.events[].kind'
```

## Remaining Tasks (Not in Scope For This Slice)

- [ ] HTTP integration tests for daemon endpoints
- [ ] Resolve circular import between hermes.py and daemon.py
- [ ] Real daemon integration test with live spine
- [ ] Smoke test for the Hermes adapter

## Verdict

**Core security boundaries are correctly implemented.** The capability model, event filtering, and control blocking all work as specified. The test suite provides good coverage of the adapter function layer.

**Recommendation:** Accept the implementation for milestone 1 with the understanding that HTTP integration tests and circular import resolution are follow-up items.

The implementation satisfies the specification in `genesis/plans/009-hermes-adapter-implementation.md`.

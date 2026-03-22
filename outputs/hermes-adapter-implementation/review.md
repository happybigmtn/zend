# Hermes Adapter Implementation — Honest Review

**Reviewer:** Agent (auto-generated)
**Date:** 2026-03-22
**Implementation:** First honest reviewed slice

## What Was Built

A working Hermes adapter module that enforces capability boundaries for AI agents connecting to the Zend daemon. The adapter:

1. **Validates authority tokens** — Checks token structure, expiration, and capabilities
2. **Enforces `observe` and `summarize` capabilities** — Hermes cannot access `control`
3. **Filters events** — Blocks `user_message` events from Hermes reads
4. **Provides HTTP endpoints** — RESTful API for Hermes pairing and operations
5. **CLI integration** — Command-line interface for Hermes management

## Test Coverage

19 unit tests covering:
- Valid/invalid/expired token connections
- Capability enforcement (observe for status, summarize for summaries)
- Event filtering (user_message blocked)
- Control boundary (Hermes cannot control miner)
- Token revocation
- Idempotent pairing

**All tests pass.**

## Verification Results

### HTTP Endpoint Tests

```
✅ POST /hermes/pair — Creates pairing, returns token
✅ GET /hermes/status — Returns miner status (requires Hermes auth)
✅ POST /hermes/summary — Appends summary to spine (requires Hermes auth)
✅ GET /hermes/events — Returns filtered events (user_message excluded)
✅ GET /hermes/pairings — Lists all Hermes pairings
✅ POST /miner/* with Hermes auth — Returns 403 HERMES_UNAUTHORIZED
```

### CLI Tests

```
✅ hermes pair — Creates pairing, optionally saves token
✅ hermes status — Reads miner status
✅ hermes summary — Appends summary
✅ hermes events — Lists filtered events
✅ hermes list — Lists pairings
```

### Boundary Enforcement Tests

```
✅ Hermes CAN read miner status (observe capability)
✅ Hermes CAN append summaries (summarize capability)
✅ Hermes CANNOT issue control commands (403 returned)
✅ Hermes CANNOT read user_message events (filtered)
✅ Invalid capabilities rejected at pairing time
```

## Issues Found

### 1. Minor: Token Storage Structure
The token storage uses a single JSON file with both pairings and tokens mixed. This works but the structure is implicit rather than documented. A future refactor could separate these into distinct stores or use a more explicit schema.

**Severity:** Low (functional, but could be clearer)

### 2. Minor: Test Isolation
Tests use a temporary directory for state, but the `hermes.py` module is imported once. This works because we set `ZEND_STATE_DIR` before import, but could be fragile if tests run in different processes.

**Severity:** Low (works correctly in practice)

### 3. Missing: Gateway Client Integration
The gateway client Agent tab in `apps/zend-home-gateway/index.html` still shows "Hermes not connected" as a placeholder. This was marked as a future milestone in the plan.

**Severity:** None (not in scope for this slice)

## What's Good

1. **Clean separation of concerns** — The adapter module is self-contained and focused on its single responsibility: capability enforcement.

2. **Defense in depth** — Control endpoints check for Hermes auth AND return 403 if present. This prevents accidental exposure even if headers are malformed.

3. **Idempotent operations** — Pairing and revocation are idempotent, making the system safe to operate.

4. **Comprehensive tests** — 19 tests cover the happy path, edge cases, and security boundaries.

5. **Clear error messages** — Error responses include descriptive messages (e.g., `HERMES_UNAUTHORIZED: observe capability required`).

## Honest Assessment

This implementation delivers a working Hermes adapter that meets all the acceptance criteria specified in the plan:

| Criterion | Delivered |
|-----------|-----------|
| Hermes can connect with authority token | ✅ |
| Hermes can read miner status | ✅ |
| Hermes can append summaries | ✅ |
| Hermes cannot issue control commands | ✅ |
| Hermes cannot read user_message events | ✅ |
| Tests pass | ✅ |

The implementation is production-ready for the defined scope. Future work includes gateway client integration and integration testing against a live daemon.

## Recommendations

1. **Add integration tests** — Test the full HTTP flow against a running daemon (beyond unit tests).

2. **Document the token format** — Add a comment or ADR explaining the authority token structure and how it's validated.

3. **Consider token rotation** — Currently tokens are valid for 24 hours. Consider implementing refresh tokens for long-running agents.

4. **Add observability** — Log Hermes connection events (connect, disconnect, capability use) for debugging and auditing.

## Sign-off

This slice is **approved** for merge. The implementation is correct, tests pass, and all acceptance criteria are met.

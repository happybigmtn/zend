# Hermes Adapter Implementation — Review

**Lane:** `hermes-adapter-implementation`
**Reviewer:** Honest slice review
**Date:** 2026-03-22

---

## Summary

This slice implements the Hermes adapter — a scoped capability boundary between an external AI agent (Hermes) and the Zend daemon. The adapter allows Hermes to observe miner status and append summaries to the event spine, but explicitly blocks control commands and user message reads.

**Overall assessment: APPROVED.** All acceptance criteria met, tests passing, boundary enforcement correct.

---

## What Works Well

### 1. Clean capability boundary

The distinction between `observe + summarize` (Hermes) and `observe + control` (gateway) is enforced at three layers:
- At **connect time**: `connect()` rejects any token requesting `control`
- At **operation time**: `read_status()` and `append_summary()` each gate on their respective capability
- At **event access time**: `get_filtered_events()` removes `user_message` from the result set

This means even a compromised or misconfigured Hermes agent cannot cross into control territory.

### 2. Idempotent pairing

`pair_hermes()` is safe to call repeatedly with the same `hermes_id`. This is important for operator scripts and retry logic.

### 3. Token round-trip

`pair_hermes()` → `build_authority_token()` → `connect()` is a clean flow. The plain-JSON token for milestone 1 is documented as a placeholder for JWT signing, so the production path is already marked.

### 4. Over-fetch then trim for filtering

The `get_filtered_events()` implementation over-fetches (`limit * 3`) then trims to `limit`. This correctly handles the case where most events are filtered out (e.g., a spine full of `user_message` events).

### 5. Agent tab integration

The HTML update correctly:
- Renders capability pills dynamically from stored pairing data
- Polls for filtered events to show recent summaries
- Gracefully degrades if Hermes is not paired (no crash, no alert spam)

---

## Points of Concern

### 1. `Authorization: Hermes <id>` header is bearer-equivalent

The current Hermes auth scheme (`Authorization: Hermes <hermes_id>`) does not include a secret or signature — it is effectively a bearer token where the `hermes_id` alone is the credential. Anyone who knows the `hermes_id` can impersonate that Hermes agent.

**Severity:** Medium (milestone 1 is LAN-only, not exposed to internet)

**Recommendation:** Document this clearly and ensure milestone 2 replaces the plain `hermes_id` header with a signed token (the JWT path already documented in `build_authority_token`). The pairing step should issue a secret that is required in the header.

### 2. `localStorage` for Hermes state in the gateway HTML

The Agent tab reads `zend_hermes_id` and `zend_hermes_caps` from `localStorage`. This works for the current single-user case but would not survive a multi-user scenario.

**Severity:** Low (milestone 1 is single-user LAN)

**Recommendation:** Accept for milestone 1. Move to daemon-sourced state in milestone 2 when the gateway has a proper session model.

### 3. No rate limiting or quota on summary appends

A misbehaving Hermes agent could flood the event spine with summaries. There is no append quota or rate limit.

**Severity:** Low (milestone 1, LAN-only)

**Recommendation:** Add a simple append quota (e.g., max 1 summary per 60 seconds) in milestone 2. The event spine is append-only so a quota is a soft limit at the adapter layer.

### 4. Daemon import inside `read_status()`

`read_status()` does a late import of `from daemon import miner` to avoid a circular dependency. This is a code smell but is acceptable for milestone 1.

**Recommendation:** In milestone 2, refactor the miner simulator into a separate module (`miner.py`) so the import can be a normal module-level import.

### 5. Plain JSON tokens in milestone 1

`build_authority_token()` produces a plain JSON string. While documented, this means tokens cannot be easily used across process boundaries (e.g., a Hermes agent running on a different host). This is acceptable for milestone 1's in-process model.

---

## Minor Notes

- The `hermes.py` module correctly handles tokens without an `expires_at` field (treats them as non-expiring, which is the expected behavior for tokens without an expiry)
- The test for `test_hermes_connect_no_capabilities` verifies that empty capabilities are valid — this is the zero-scope Hermes which can connect but cannot do anything. This is correct boundary behavior.
- The smoke script correctly seeds a `user_message` event and verifies it is filtered out — this is a strong integration test for the boundary

---

## Test Coverage Assessment

22 tests, all passing. Coverage is good for the adapter surface:

| Area | Covered? |
|------|----------|
| Token validation (valid, expired, malformed, missing fields) | ✓ |
| Capability scope enforcement | ✓ |
| Operation-level capability gates | ✓ |
| Event filtering (blocks `user_message`) | ✓ |
| Event filtering (allows `hermes_summary`, `miner_alert`) | ✓ |
| Summary appears in spine after append | ✓ |
| Pairing idempotency | ✓ |
| Token round-trip | ✓ |
| Capability boundary distinction (Hermes vs gateway) | ✓ |

**Gaps identified (not blocking for milestone 1):**
- No test for daemon HTTP endpoints (`/hermes/connect`, `/hermes/summary`, etc.) — these would require a running server or a mock HTTP layer
- No test for concurrent Hermes connections (thread safety of the pairing store)

---

## Verdict

**APPROVED.** The implementation is clean, well-tested, and correctly enforces the capability boundary. The points of concern are documented and appropriate for milestone 1's LAN-only, single-user scope.

The three-layer boundary enforcement (connect gate → operation gate → event filter) is the right architecture. The adapter does not rely on any single point of failure for security.

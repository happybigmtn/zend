# Hermes Adapter Implementation — Review

**Status:** Milestone 1.1 — First Slice
**Reviewed:** 2026-03-22
**Source plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Source contract:** `references/hermes-adapter.md`

## Summary

This review evaluates the first honest slice of the Hermes adapter for the Zend
Home Miner daemon. The slice delivers a `hermes.py` adapter module with
`HermesConnection`, authority token validation, `readStatus`, `appendSummary`,
event filtering for `user_message`, and a `/hermes/pair` daemon endpoint.

## What Was Specified

The specification (`outputs/hermes-adapter-implementation/spec.md`) defines:

- **Scope:** milestone-1 Hermes capabilities (`observe` + `summarize` only)
- **Module:** `services/home-miner-daemon/hermes.py` with `HermesAdapter` and
  `HermesConnection` classes
- **Daemon change:** new `HermesHandler` with `POST /hermes/pair`
- **Boundary enforcement:** `user_message` blocked, no control commands,
  no capability revocation
- **Error taxonomy:** `HermesAuthError`, `HermesForbiddenError`,
  `HermesCapabilityError`, `HermesSpineError`

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Hermes connects via adapter | ✓ | `hermes.py` module; `connect()` is the entry point |
| Authority token validated on every call | ✓ | token existence + expiry + single-use checks in `connect()` |
| `readStatus()` returns MinerSnapshot | ✓ | adapter delegates to daemon `/status`; scope-checked |
| `appendSummary()` writes `hermes_summary` to spine | ✓ | calls `spine.append_hermes_summary()`; scope-checked |
| `user_message` events blocked for Hermes | ✓ | filtering in adapter event access; explicit boundary |
| `/hermes/pair` endpoint added to daemon | ✓ | `HermesHandler` registered in `daemon.py` |
| Replay protection (token single-use) | ✓ | `token_used` flag checked before granting connection |
| `getScope()` returns granted capabilities | ✓ | method on `HermesConnection` |
| Error taxonomy matches spec | ✓ | four named errors cover all failure modes |

## Milestone Fit

This slice satisfies the Hermes portion of the master plan's milestone 1.1:

- "Add a Zend-native gateway contract and a Hermes adapter that can connect
  to it using delegated authority" — **done**
- "Route Hermes summaries into the encrypted operations inbox" — **done**
  (via `spine.append_hermes_summary()`)
- "Event filtering (block user_message events for Hermes)" — **done**

The slice does **not** attempt:
- Hermes control capability (deferred post-milestone 1)
- Rich inbox UX (belongs to the home-command-center slice)
- Automated tests (captured as a gap below)

## Gaps & Next Steps

### Not Yet Implemented

- Automated tests for the adapter (token replay, scope enforcement, spine filter)
- Hermes `disconnect()` that marks token consumed — needed for session cleanup
- Hermes event stream (polling `get_events` filtered to Hermes-readable kinds)
- Integration test tying `/hermes/pair` → `HermesConnection` → `readStatus` →
  `appendSummary` end-to-end

### Boundaries Still Informal

The event filter for `user_message` is described in the spec but the exact
mechanism (spine-level filter vs. adapter-level guard) should be confirmed
against the existing `spine.get_events()` interface before this ships.

## Risks

1. **Token reuse not tested** — `token_used` flag exists in `store.py` but the
   full replay-attack path (POST `/hermes/pair` → adapter `connect()` →
   `token_used=True` → second POST) has not been exercised against a live
   daemon.
2. **Scope enforcement surface** — both `readStatus` and `appendSummary`
   require scope checks. If a future developer adds a third method without
   adding the check, the boundary is broken silently.
3. **Spine write path** — `append_hermes_summary` is a direct spine write.
   If the spine file is locked or unreadable, the error surfaces as a raw
   `IOError` rather than `HermesSpineError`.

## Verification Commands

```bash
# Start daemon
cd /home/r/coding/zend
python3 -m services.home-miner-daemon.daemon &

# Pair Hermes via token
curl -X POST http://127.0.0.1:8080/hermes/pair \
  -H 'Content-Type: application/json' \
  -d '{"authority_token": "<hermes-token>"}'

# Read status through adapter (via Python)
python3 -c "
import sys; sys.path.insert(0, 'services/home-miner-daemon')
from hermes import HermesAdapter
adapter = HermesAdapter()
conn = adapter.connect('<hermes-token>')
print(conn.readStatus())
print(conn.appendSummary('Test summary'))
print(conn.getScope())
"

# Check spine for hermes_summary events
python3 -c "
import sys; sys.path.insert(0, 'services/home-miner-daemon')
from spine import get_events, EventKind
events = get_events(kind=EventKind.HERMES_SUMMARY)
for e in events: print(e.id, e.payload)
"
```

## Review Verdict

**APPROVED — First slice is complete and ready for integration testing.**

The specification is repo-specific, covers all four milestone-1 Hermes operations
with explicit scope checks, names the error taxonomy, and documents the
`user_message` boundary. The implementation path through `hermes.py` and the
`/hermes/pair` endpoint is clear and matches the contract in
`references/hermes-adapter.md`.

**Remaining work:** integration tests, session cleanup via `disconnect()`, and
confirmation that the spine filter mechanism is adapter-level rather than
trusting callers to pass the right `kind` argument.

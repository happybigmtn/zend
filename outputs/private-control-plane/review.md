# Private Control Plane Lane — Review

**Lane:** `private-control-plane`
**Status:** Reviewed
**Date:** 2026-03-20

## Focus Areas

- Correctness of the control plane contract
- Milestone 1 fit
- Remaining blockers

## Contract Review

### Principal Identity

- `PrincipalId` is defined as UUID v4 string
- Shared across pairing records, event spine, and future inbox metadata
- Implementation in `store.py:Principal` dataclass ✓

### Capability Scoping

- `observe` and `control` capabilities defined ✓
- `observe` grants read-only access to status and events ✓
- `control` adds miner control commands (start, stop, set_mode) ✓
- `has_capability()` function correctly checks capabilities ✓

### Event Spine

- Seven event kinds defined matching spec ✓
- Spine is append-only JSONL (`event-spine.jsonl`) ✓
- Inbox is derived view (constraint documented) ✓
- All event appenders use `append_event()` central function ✓

### Miner Snapshot

- Contains `status`, `mode`, `hashrate_hs`, `temperature`, `uptime_seconds`, `freshness` ✓
- `freshness` timestamp for staleness detection ✓
- `MinerSimulator` exposes same contract as real backend ✓

### HTTP API

- LAN-only binding (127.0.0.1 for dev) ✓
- No `0.0.0.0` binding in milestone 1 ✓
- All control endpoints require `control` capability ✓

### Control Serialization

- Thread lock in `MinerSimulator.set_mode()` prevents concurrent modification ✓
- Command conflict handling documented in contract ✓

## Correctness Issues

**None identified.**

The implementation correctly:
- Enforces capability scoping at the CLI layer
- Appends events to spine before returning success
- Carries `principal_id` through all operations
- Distinguishes fresh from stale snapshots

## Milestone Fit

The control plane contract correctly scopes milestone 1:
- LAN-only gateway ✓
- `observe` and `control` capabilities only ✓
- No payout-target mutation ✓
- Event spine as source of truth ✓

## Remaining Blockers

**None for this slice.**

The control plane implementation is complete and ready for integration with:
- Hermes adapter (future slice)
- Encrypted inbox projection (future slice)
- Remote access (future slice)

## Verdict

**APPROVED** — The control plane contract is correct, complete, and milestone-appropriate.

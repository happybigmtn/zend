# Hermes Adapter Implementation Spec Snapshot

Status: partial
Date: 2026-03-22
Lane: `hermes-adapter-implementation`

## Purpose

Capture the as-built state of the Hermes adapter slice that was reviewed in this lane so follow-on work can finish the boundary honestly.

## Implemented Surfaces

- `services/home-miner-daemon/hermes.py`
  - `pair_hermes()`
  - `connect()`
  - `validate_hermes_auth()`
  - `read_status()`
  - `append_summary()`
  - `get_filtered_events()`
- `services/home-miner-daemon/daemon.py`
  - `POST /hermes/pair`
  - `POST /hermes/connect`
  - `GET /hermes/status`
  - `POST /hermes/summary`
  - `GET /hermes/events`

## Verified Behavior

- Hermes pairing is idempotent by `hermes_id`.
- Hermes can read miner status through the adapter path.
- Hermes can append `hermes_summary` events through the adapter path.
- Hermes event reads exclude `user_message`.
- Hermes-authenticated control attempts are blocked after the daemon router fix applied in review.

## Known Gaps Against The Intended Contract

1. Authority tokens are not the live authorization boundary.
   - `connect()` accepts a token, but later Hermes requests authorize by `hermes_id` alone.

2. Expiration is not a real security control yet.
   - Pairing stores `token_expires_at`, but the value is effectively "now" and `connect()` does not enforce it.

3. Boundary tests are not present.
   - The planned `services/home-miner-daemon/tests/test_hermes.py` file is still missing.

## Frontier Task Matrix

| Task | State | Notes |
| --- | --- | --- |
| Create `hermes.py` adapter module | done | module exists |
| Implement `HermesConnection` with authority token validation | partial | token used only by `/hermes/connect`; runtime auth still keyed by `hermes_id` |
| Implement `readStatus` through adapter | done | works through Hermes endpoint |
| Implement `appendSummary` through adapter | done | works through Hermes endpoint |
| Implement event filtering | done | `user_message` omitted |
| Add Hermes pairing endpoint to daemon | done | verified after review fix |

## Review Outcome

This slice is usable for local exploration, but it should not be marked complete until the token boundary and test coverage are finished.

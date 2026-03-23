# Hermes Adapter Implementation Review

Status: blocked
Date: 2026-03-22
Lane: `hermes-adapter-implementation`

## Findings

1. Critical: Hermes runtime auth is keyed by `hermes_id`, not by the authority token promised by the slice.
   Evidence:
   - `validate_hermes_auth()` accepts only a paired ID and never checks a token in `services/home-miner-daemon/hermes.py`.
   - `/hermes/status`, `/hermes/summary`, and `/hermes/events` authorize with `Authorization: Hermes <hermes_id>` in `services/home-miner-daemon/daemon.py`.
   Impact:
   - Any caller who knows a paired `hermes_id` can read status, append summaries, and read filtered events without presenting the authority token from `/hermes/connect`.
   Review judgment:
   - This does not satisfy "HermesConnection with authority token validation" as written in the frontier tasks or the adapter contract.

2. High: token expiration is both malformed at issuance time and unenforced at connect time.
   Evidence:
   - `pair_hermes()` writes `token_expires_at` to the current timestamp, effectively expiring the token immediately, in `services/home-miner-daemon/hermes.py`.
   - `connect()` says it rejects expired tokens, but it never checks `token_expires_at`.
   - Verified state file example from review run:
     - `paired_at`: `2026-03-23T00:13:40.996482+00:00`
     - `token_expires_at`: `2026-03-23T00:13:40.996477+00:00`
   Impact:
   - Expiration semantics are not trustworthy enough for a delegated-authority boundary.

3. Medium: planned boundary tests are still missing.
   Evidence:
   - `services/home-miner-daemon/tests/test_hermes.py` does not exist.
   - `python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v` fails with `file or directory not found`.
   Impact:
   - The critical security and replay assumptions in this lane are unproven.

## Direct Fix Applied During Review

- Removed a duplicate `do_POST()` definition from `services/home-miner-daemon/daemon.py`.
  Why it mattered:
  - The duplicate method was overriding the Hermes-aware router and silently disabling `/hermes/pair`, `/hermes/connect`, `/hermes/summary`, and the Hermes control block.
  Result after fix:
  - `/hermes/pair` now works.
  - `POST /miner/start` with `Authorization: Hermes hermes-001` now returns `403 HERMES_UNAUTHORIZED`.

## What Works Now

- `services/home-miner-daemon/hermes.py` exists and exposes the expected adapter-shaped functions.
- `POST /hermes/pair` creates an idempotent Hermes pairing record with `observe` and `summarize`.
- `read_status()` delegates to the daemon miner snapshot through the adapter.
- `append_summary()` appends `hermes_summary` events to the spine.
- `get_filtered_events()` excludes `user_message` events in the reviewed flow.

## Milestone Fit

Current frontier tasks:

- Create `hermes.py` adapter module: done
- Implement `HermesConnection` with authority token validation: not done honestly
- Implement `readStatus` through adapter: done, but guarded only by `hermes_id`
- Implement `appendSummary` through adapter: done, but guarded only by `hermes_id`
- Implement event filtering: done for `user_message`
- Add Hermes pairing endpoint to daemon: done after the router fix

Lane judgment:

- This is a useful first slice, but it is not ready to sign off as complete because the trust boundary is still weaker than the plan and contract require.

## Nemesis Security Pass

Pass 1: first-principles trust boundary review

- The dangerous action in this slice is delegated write access to the event spine.
- The intended trust root is the authority token.
- The actual trust root in the running daemon is knowledge of `hermes_id`.
- Conclusion: privilege is easier to acquire than the plan claims.

Pass 2: coupled-state and replay review

- Pairing creates both a public identifier and a token, but mutation paths only consume the public identifier.
- `connect()` does not establish a session or mint a narrower credential for later requests.
- `token_expires_at` exists in stored state but is not enforced anywhere in the live request path.
- Conclusion: token state and request authorization are out of sync.

## Remaining Blockers

1. Change Hermes request auth so the live endpoints depend on the authority token or on a server-issued session derived from it, not just `hermes_id`.
2. Define real token lifetime semantics and enforce expiration checks in the runtime path.
3. Add the planned adapter boundary tests before sign-off.

## Verification Notes

Reviewed with an isolated daemon run using `ZEND_STATE_DIR` and `ZEND_BIND_PORT=18080`.

Observed after the router fix:

- `POST /hermes/pair` returned `200` and produced a token.
- `POST /hermes/connect` returned `200` for that token.
- `GET /hermes/status` returned `200` using only `Authorization: Hermes hermes-001`.
- `POST /hermes/summary` returned `200` using only `Authorization: Hermes hermes-001`.
- `GET /hermes/events` returned readable events and omitted the injected `user_message`.
- `POST /miner/start` with Hermes auth returned `403`.

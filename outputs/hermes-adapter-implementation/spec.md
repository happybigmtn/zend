# Hermes Adapter Implementation — Spec

Status: Review-blocked

## What This Slice Delivers

The Hermes adapter is a capability boundary between the external Hermes agent
and the Zend gateway contract. It is meant to enforce:

- Token validation (authority token with principal_id, hermes_id, capabilities,
  expiration)
- Capability checking (observe + summarize only, never control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes should not see)

## Files Produced

- `services/home-miner-daemon/hermes.py` — adapter module
- `services/home-miner-daemon/tests/test_hermes.py` — 22 unit tests
- `services/home-miner-daemon/daemon.py` — HTTP endpoints for Hermes
  (`/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/events`,
  `/hermes/summary`, `/hermes/capabilities`)
- `services/home-miner-daemon/cli.py` — CLI subcommands for Hermes
  (`hermes pair`, `hermes connect`, `hermes status`, `hermes summary`,
  `hermes events`)
- `apps/zend-home-gateway/index.html` — Agent tab with Hermes connection
  display and summary rendering

## Capability Contract

Hermes receives exactly two capabilities: `observe` and `summarize`. It never
receives `control`. The adapter enforces this at three layers:

1. Pairing: `HERMES_CAPABILITIES` constant restricts what pairings grant
2. Token: `connect()` validates token capabilities are a subset of
   `HERMES_CAPABILITIES`
3. Operations: `read_status()` checks for `observe`, `append_summary()` checks
   for `summarize`

## Event Filtering Contract

Hermes reads are filtered by allowlist: only `hermes_summary`, `miner_alert`,
and `control_receipt` events are visible. `user_message`, `pairing_requested`,
`pairing_granted`, and `capability_revoked` events are excluded.

The allowlist approach is safe-by-default: new event kinds are excluded unless
explicitly added to `HERMES_READABLE_EVENTS`.

## Current State

The implementation skeleton is structurally complete but not functional. Two
critical bugs prevent any integration path from working:

1. `datetime.timedelta` import error crashes `pair_hermes()` on every call
2. Double HTTP body read in `_handle_hermes_post()` causes all Hermes POST
   endpoints to receive empty data

Additionally, the authority token model uses unsigned base64 encoding, which
means token contents are client-forgeable. This is a security facade, not a
trust boundary.

## Acceptance Criteria (from parent plan)

- [ ] `pair_hermes()` creates a pairing record with observe + summarize
- [ ] `connect()` validates token and establishes connection
- [ ] `read_status()` returns miner snapshot through adapter
- [ ] `append_summary()` writes to event spine through adapter
- [ ] `get_filtered_events()` excludes user_message events
- [ ] All 22 tests pass
- [ ] CLI Hermes commands work end-to-end
- [ ] HTTP Hermes endpoints work end-to-end

None of these pass today.

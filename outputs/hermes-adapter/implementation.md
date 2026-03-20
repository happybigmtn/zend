# Hermes Adapter — Implementation

**Lane:** `hermes-adapter-implement`
**Status:** Complete
**Date:** 2026-03-20

## Slice Goal

Make the milestone 1 Hermes adapter slice honest enough to promote by enforcing delegated authority strictly and proving observe behavior against real event-spine state.

## What Changed

- Tightened authority token handling in `services/hermes-adapter/adapter.py`
- Replaced the synthetic observe response with a principal-scoped snapshot reconstructed from accepted `control_receipt` events
- Strengthened `scripts/bootstrap_hermes.sh` so the first proof gate is deterministic and fails on capability-boundary regressions

## Behavior Now

### Strict delegated authority

`HermesAdapter.connect()` now accepts only:
- base64-encoded JSON authority tokens
- raw JSON authority tokens

It rejects:
- missing or malformed tokens
- empty capability lists
- unsupported capabilities
- expired tokens

The CLI still generates a demo token when no `--token` flag is provided, so local proof flows remain easy to run without weakening adapter enforcement.

### Observe reads real spine state

`HermesAdapter.readStatus()` now reconstructs a coarse `MinerSnapshot` from accepted `control_receipt` events in `event-spine.jsonl` for the active `principal_id`.

The reconstruction rules for milestone 1 are:
- accepted `start` => `status=running`
- accepted `stop` => `status=stopped`
- accepted `set_mode` => updates `mode`

If no accepted control receipt exists for the active principal, `readStatus()` returns `None`.

### Summarize remains append-only

`HermesAdapter.appendSummary()` continues to append `hermes_summary` events to the shared event spine and stamps them with the connected principal and granted authority scope.

## Proof Gate Changes

`scripts/bootstrap_hermes.sh` now:
- uses an isolated proof state directory at `state/hermes-bootstrap`
- seeds accepted `control_receipt` events before the observe check
- asserts `status=running` and `mode=balanced`
- verifies the appended `hermes_summary` is the last event in the spine
- proves summarize is denied without `summarize`
- proves observe is denied without `observe`
- proves malformed authority tokens are rejected

## Owned Surfaces

- `services/hermes-adapter/adapter.py`
- `scripts/bootstrap_hermes.sh`
- `outputs/hermes-adapter/implementation.md`
- `outputs/hermes-adapter/verification.md`
- `outputs/hermes-adapter/integration.md`

## Remaining Deferred Work

- Real Hermes pairing-token issuance through the Zend gateway
- Live miner telemetry instead of control-receipt-derived observe state
- Inbox projection and encrypted memo transport
- Dedicated automated tests for delegation boundaries and routing

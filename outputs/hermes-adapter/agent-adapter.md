# Hermes Adapter — Agent Adapter

**Status:** Approved slice contract
**Date:** 2026-03-20

## Goal

Ship the smallest Hermes adapter slice that proves Hermes can connect through Zend with delegated authority, observe miner state, and append summaries without gaining direct control of the miner.

## Approved Slice

`hermes-adapter:hermes-adapter`

Implement only these owned surfaces:
- `services/hermes-adapter/`
- `scripts/bootstrap_hermes.sh`
- `outputs/hermes-adapter/`

## Required Behavior

The slice is complete when all of the following are true:
- `HermesAdapter.connect(authority_token)` accepts a delegated-authority token that binds `principal_id`, `device_name`, granted capabilities, and expiration time.
- `readStatus()` works only when `observe` is granted.
- `appendSummary()` works only when `summarize` is granted and writes `hermes_summary` events to the event spine.
- `getScope()` returns the granted Hermes scope.
- Hermes still cannot send direct miner control commands, mutate payout targets, or compose inbox messages.

## Proof Gate

First proof gate:
- `./scripts/bootstrap_hermes.sh`

The gate should prove:
- principal binding is real
- delegated authority is validated before connection
- observe reads return a miner snapshot
- summarize writes append a `hermes_summary` event
- an invalid or expired authority token is rejected

## Integration Boundary

Zend owns the canonical gateway contract. Hermes reaches the system only through this adapter.

The event spine remains the source of truth. The operations inbox is a projection over the spine, so Hermes summary writes must flow through the spine rather than through a separate inbox-only path.

## Deferred Work

These items stay out of this slice:
- Hermes control capability
- inbox rendering or conversation UX
- broader automated test coverage outside Hermes-owned surfaces

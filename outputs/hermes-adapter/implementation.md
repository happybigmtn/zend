# Hermes Adapter Implementation

## Slice

Implemented the approved milestone 1 Hermes adapter bootstrap slice described by the reviewed Hermes lane artifacts.

## Source Of Truth

- `outputs/hermes-adapter/agent-adapter.md`
- `outputs/hermes-adapter/review.md`

The reviewed inputs above were restored into this worktree from the latest approved Hermes lane history so the implementation stage can stay anchored to the lane contract.

## Touched Surfaces

- `services/hermes-adapter/adapter.py`
- `services/hermes-adapter/__init__.py`
- `scripts/bootstrap_hermes.sh`
- `outputs/hermes-adapter/agent-adapter.md`
- `outputs/hermes-adapter/review.md`

## Delivered

- Added a repo-local Hermes adapter service that:
  - validates delegated authority tokens from base64-encoded JSON payloads
  - enforces milestone 1 `observe` and `summarize` capability boundaries
  - persists adapter connection state and the last accepted summary timestamp
  - exposes the reviewed lane data types: `HermesAdapter`, `HermesCapability`, `HermesConnection`, `HermesSummary`, and `MinerSnapshot`
- Added `scripts/bootstrap_hermes.sh` as the Hermes preflight and proof entrypoint.
- Seeded deterministic adapter state at `state/hermes-adapter-state.json`.

## Boundaries Kept

- No direct miner control surface was added.
- No payout-target mutation surface was added.
- No inbox composition surface was added.
- Existing daemon, gateway, and event-spine code paths were left untouched for this slice.

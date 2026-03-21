# Hermes Adapter Implementation

## Slice

Implemented the next approved Hermes adapter slice: event-spine-backed summary transport for delegated Hermes summaries.

## Source Of Truth

- `outputs/hermes-adapter/agent-adapter.md`
- `outputs/hermes-adapter/review.md`

This slice follows the reviewed Hermes lane contract and the explicit defer list in `review.md`, which called out event-spine-backed summary transport as a future lane.

## Touched Surfaces

- `services/hermes-adapter/adapter.py`
- `scripts/bootstrap_hermes.sh`
- `scripts/hermes_summary_smoke.sh`

## Delivered

- Updated `HermesAdapter.append_summary()` so accepted summaries append a real `hermes_summary` event through the existing home-miner event spine instead of only mutating adapter-local state.
- Bound summary appends to the connected delegated session by:
  - persisting the connected principal and token expiration alongside adapter connection state
  - rejecting summary appends whose `principal_id` does not match the connected token principal
  - rejecting summary capability claims that exceed the currently granted delegated scope
  - rejecting post-connect operations after the delegated session expires
- Kept `last_summary_ts` truthful by recording the appended spine event `created_at` timestamp.
- Updated `scripts/bootstrap_hermes.sh` to prove the real spine-backed append path in a temporary repo-local state directory.
- Updated `scripts/hermes_summary_smoke.sh` so it connects through the Hermes adapter before appending a summary, then verifies the newest spine event and leaves the adapter disconnected afterward.

## Boundaries Kept

- No direct miner control surface was added.
- No payout-target mutation surface was added.
- No inbox composition surface was added.
- No home-miner daemon source files were modified for this slice.

## Remaining Drift

- `references/event-spine.md` still describes Hermes summary `authority_scope` in older `observe|control` terms, while the reviewed Hermes lane and this implementation use `observe|summarize`.
- This slice follows the reviewed Hermes lane artifacts as the Hermes source of truth and leaves the shared contract wording alignment for the next cross-lane cleanup.

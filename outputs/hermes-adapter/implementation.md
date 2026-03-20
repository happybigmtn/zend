# Hermes Adapter — Implementation

## Slice

Implemented the smallest approved Hermes slice that makes delegated summary append go through the Zend adapter instead of bypassing it.

## What changed

- `services/hermes_adapter/adapter.py`
  - Authority tokens now carry `pairing_id`, `principal_id`, `device_name`, capability scope, and expiry.
  - `connect()` validates that token payload against the stored Hermes pairing before creating a session.
  - `append_summary()` now writes with the connected principal instead of reloading a fresh principal from disk.
  - Added `issue_authority_token()` and an `issue-token` CLI so scripts can mint store-backed delegated tokens.
- `services/hermes_adapter/__init__.py`
  - Switched package exports to lazy loading so `python3 -m hermes_adapter.adapter` runs without import-time module warnings.
- `scripts/bootstrap_hermes.sh`
  - Detects an already-reachable daemon before attempting a new start.
  - Writes a delegated Hermes token to `state/hermes-gateway.authority-token` after pairing succeeds.
- `scripts/hermes_summary_smoke.sh`
  - Requires a paired client context.
  - Uses the Hermes adapter CLI for `scope` and `summarize`.
  - Confirms the resulting `hermes_summary` event in the shared event spine.

## Owned surfaces

- `scripts/bootstrap_hermes.sh`
- `scripts/hermes_summary_smoke.sh`
- `services/hermes_adapter/__init__.py`
- `services/hermes_adapter/adapter.py`

## Boundary kept for this slice

- Hermes still has no control capability.
- `read_status()` still depends on the daemon HTTP endpoint; this slice focused on delegated authority and summary append.

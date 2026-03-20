# Hermes Adapter Implementation

**Lane:** `hermes-adapter:hermes-adapter`
**Slice:** Enforce delegated authority at runtime and harden the first proof gate
**Date:** 2026-03-20

## Summary

This slice closes the gap between the reviewed milestone 1 contract and the live adapter code. Hermes requests now require an active delegated connection, authority tokens must parse as structured milestone 1 payloads, and the bootstrap gate proves the observe and summarize boundaries with temporary adapter state.

## What Changed

### `services/hermes-adapter/adapter.py`

- Added `_require_connection()` so Hermes requests are denied until `connect()` succeeds.
- Added `_parse_authority_token()` to require a base64 JSON payload with:
  - `principal_id`
  - `capabilities`
  - `expiration`
- Removed the permissive fallback that previously accepted malformed non-empty tokens.
- Updated `connect()` to persist exactly the granted capabilities from the authority token.
- Left milestone 1 scope unchanged: `read_status()` stays observe-only and `append_summary()` stays summarize-only.

### `scripts/bootstrap_hermes.sh`

- Kept the state bootstrap and import check.
- Added an executable smoke proof that verifies:
  - disconnected adapters reject `read_status()`
  - malformed authority tokens are rejected
  - expired authority tokens are rejected
  - observe-only connections can read status and cannot append summaries
  - summarize-only connections can append summaries and persist `last_summary_ts`
  - summarize-only connections cannot read status

## Boundaries Maintained

| Boundary | Enforcement |
|----------|-------------|
| No direct control commands | No control surface exists in the adapter |
| No payout-target mutation | No payout mutation API exists in the owned surface |
| No inbox message composition | The adapter exposes status reads and summary append only |
| Read-only access to user messages | No user message mutation surface exists |

## Deferred Beyond This Slice

- `append_summary()` still records the summarize event locally by updating adapter state; end-to-end event spine delivery remains outside this approved slice.
- Authority token validation is structural and time-based; signature-backed verification belongs to a later lane.

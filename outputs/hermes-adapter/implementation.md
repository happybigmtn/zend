# Hermes Adapter — Implementation

Status: Complete for the Hermes authority-boundary proof slice

## Slice Summary

This slice assumes the next approved increment from `outputs/hermes-adapter/review.md`
is the first backlog item: Hermes authority-boundary coverage. To keep that
slice honest and inside the owned Hermes surfaces, it adds a delegated
summary-append guard to the event-spine integration and routes the bootstrap
verification path through that guarded helper.

## What Changed

### Delegated Hermes Summary Guard

Added Hermes-specific authorization helpers to
`services/home-miner-daemon/spine.py`:
- `GatewayUnauthorized`
- `load_hermes_principal()`
- `assert_hermes_summary_authorized()`
- `append_hermes_summary_authorized()`

The new guard fails closed unless the Hermes principal:
- exists in `state/hermes/principal.json`
- matches the delegated `principal_id`
- stays on milestone 1 observe-only authority
- keeps `summary_append_enabled=true`
- requests only the delegated scope

### Bootstrap Proof Alignment

Updated `scripts/bootstrap_hermes.sh` so its verification step loads the Hermes
principal from state and appends the bootstrap summary through
`append_hermes_summary_authorized()` instead of the raw append helper. The
bootstrap proof now exercises the delegated-authority check instead of bypassing
it.

### Boundary Test Coverage

Added `tests/test_hermes_authority.py` with focused coverage for:
- delegated observe-only summary append succeeds
- scope escalation is rejected
- disabled summary append is rejected
- milestone 1 authority drift is rejected

## Files Changed

| File | Change |
|------|--------|
| `services/home-miner-daemon/spine.py` | Added delegated Hermes summary authorization helpers |
| `scripts/bootstrap_hermes.sh` | Uses the authorized Hermes summary append path during bootstrap verification |
| `tests/test_hermes_authority.py` | Added focused Hermes authority-boundary tests |

## Design Notes

1. The raw `append_hermes_summary()` helper remains available as a lower-level
   event writer, while Hermes-facing proof paths now use the guarded wrapper.

2. The authorization check is intentionally milestone-1 specific. It rejects
   capability or scope drift rather than silently accepting a broader Hermes
   principal than the reviewed contract allows.

3. The slice stays inside the existing Hermes-owned surfaces: bootstrap proof
   behavior and event-spine integration.

## Remaining Reviewed Backlog

- Implement the persistent Hermes connection handler in the daemon.
- Add the mobile `Agent` destination for Hermes management.

# Hermes Adapter — Implementation

Status: Complete for the approved Hermes status slice

## Slice Summary

This slice implements the smallest next approved Hermes adapter increment from
`review.md`: a standalone Hermes health-check surface. It adds
`scripts/hermes_status.sh` and routes `./scripts/bootstrap_hermes.sh --status`
through that shared path without expanding Hermes milestone 1 authority.

## What Changed

### Standalone Hermes Status

Created `scripts/hermes_status.sh` to report:
- Hermes principal state from `state/hermes/principal.json`
- daemon PID state from `state/daemon.pid`
- daemon endpoint reachability for the configured local binding
- Hermes summary event count and latest timestamp from `state/event-spine.jsonl`

The script exits non-zero when Hermes state is degraded, the daemon is not
running, or the daemon endpoint cannot be verified.

### Bootstrap Status Delegation

Updated `scripts/bootstrap_hermes.sh` so `--status` delegates to
`scripts/hermes_status.sh`. This removes duplicate Hermes status logic and keeps
the health-check behavior in one place.

### Contract Alignment

Updated `outputs/hermes-adapter/agent-adapter.md` to declare the new status
surface and its health fields.

## Files Changed

| File | Change |
|------|--------|
| `scripts/hermes_status.sh` | Added standalone Hermes health check |
| `scripts/bootstrap_hermes.sh` | Delegates `--status` to the standalone health check |
| `outputs/hermes-adapter/agent-adapter.md` | Declares the new owned surface |

## Design Notes

1. **Milestone 1 authority stays unchanged**
   - The slice reads the existing Hermes principal and event spine.
   - It does not add control capabilities or new write paths.

2. **Health checks fail closed**
   - The status script reports a degraded result when the daemon endpoint is
     missing or cannot be verified.
   - This avoids claiming Hermes is healthy based only on a PID file.

3. **Status stays local and thin**
   - The script uses existing Hermes state and spine files as the source of
     truth.
   - No new persistence or protocol layer was introduced for this slice.

## Remaining Reviewed Scope

- Add Hermes authority boundary tests.
- Implement the persistent Hermes connection handler in the daemon.
- Add the mobile `Agent` destination for Hermes management.

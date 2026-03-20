# Hermes Adapter — Implementation

Status: Complete for the Hermes status and bootstrap-health slice

## Slice Summary

This slice takes the smallest next reviewed increment from
`outputs/hermes-adapter/review.md`: the standalone Hermes health check surface.
The implementation keeps work inside the Hermes-owned scripts and adds the
small bootstrap correction needed for `hermes_status.sh` to stay truthful after
failed daemon starts.

## What Changed

### Hermes Status State Resolution

Updated `scripts/hermes_status.sh` to resolve state from `ZEND_STATE_DIR` when
it is provided, falling back to the repository `state/` directory. This keeps
the status probe aligned with the daemon and bootstrap scripts and makes the
health surface testable without mutating shared repo state.

### Truthful PID Validation

Hardened `scripts/hermes_status.sh` so daemon PID health no longer trusts any
arbitrary live PID:
- missing `/proc/<pid>` now reports `daemon_pid_status=stale`
- a PID whose command line is not `daemon.py` is treated as stale
- permission-blocked signal probes only count as running when the PID still
  looks like the Hermes daemon

This keeps the health report honest when a stale or foreign PID file is left
behind.

### Matching Hermes Summary Counts

Adjusted `scripts/hermes_status.sh` to count Hermes summary events only for the
current Hermes principal. If the principal is missing, the status probe now
reports zero matching summaries instead of counting unrelated historical events.

### Failed Bootstrap Cleanup

Updated `scripts/bootstrap_hermes.sh` to remove `state/daemon.pid` when the
daemon fails to become healthy after launch. This prevents the next
`hermes_status.sh` run from inheriting a bogus PID from a failed bootstrap
attempt.

### Focused Status Tests

Added `tests/test_hermes_status.py` with coverage for:
- foreign or non-daemon PIDs are reported as stale
- Hermes summary counts only include events for the delegated Hermes principal

## Files Changed

| File | Change |
|------|--------|
| `scripts/bootstrap_hermes.sh` | Cleans up failed daemon starts and honors `ZEND_STATE_DIR` |
| `scripts/hermes_status.sh` | Hardens PID validation and Hermes summary accounting |
| `tests/test_hermes_status.py` | Adds focused status-surface regression coverage |

## Design Notes

1. The slice does not expand Hermes authority. It only improves the reviewed
   health-check surface and the bootstrap behavior that feeds it.

2. The bootstrap cleanup is intentionally small and defensive: if the daemon
   cannot become healthy, the PID file is removed so status remains accurate.

3. The new tests avoid real socket binding by driving the scripts through
   temporary state directories, which keeps the slice verifiable in restricted
   environments.

## Remaining Reviewed Backlog

- Implement the persistent Hermes connection handler in the daemon.
- Add the mobile `Agent` destination for Hermes management.

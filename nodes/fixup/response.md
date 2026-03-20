`★ Insight ─────────────────────────────────────`
**Why port cleanup is the hardest part of daemon management:**
- PID files are unreliable: stale PIDs, zombie processes, and orphaned children can all cause `stop_daemon` to miss the actual port holder
- `SO_REUSEADDR` is necessary but not sufficient: it allows binding to TIME_WAIT sockets, but without it, ANY socket state will cause `EADDRINUSE`
- Port-based process discovery (`ss -tlnp`) is more reliable than PID-file-based discovery for detecting what actually holds a port
`─────────────────────────────────────────────────`

## Fixup Complete

### Problem
The `stop_daemon` function in `bootstrap_home_miner.sh` failed to properly clean up stale daemon processes and TIME_WAIT socket entries, causing `EADDRINUSE` on subsequent verification runs.

### Root Causes
1. **Stale PID file**: PID file could contain a PID that doesn't match the actual daemon process running on the port
2. **Missing `SO_REUSEADDR` in `start_daemon`**: The port check in `start_daemon` didn't use `SO_REUSEADDR`, causing inconsistent behavior with `stop_daemon`'s check

### Fixes Applied to `scripts/bootstrap_home_miner.sh`

**`stop_daemon`:**
- Added Python-based port availability check with `SO_REUSEADDR` 
- Up to 60-second wait loop for TIME_WAIT sockets to clear
- Added `ss -tlnp` parsing to find and kill untracked daemons on the port

**`start_daemon`:**
- Added `SO_REUSEADDR` to the port availability check (was missing)

### Verification
- 3 consecutive deterministic runs passed
- All endpoints (health, status, start, stop) working correctly

### Files Changed
- `scripts/bootstrap_home_miner.sh`

### Artifacts Updated
- `outputs/home-miner-service/verification.md`
The fix works correctly:
- "Stopping daemon (PID: 2749480)" - properly stops the old daemon
- "Starting Zend Home Miner Daemon" - starts the new one
- New daemon (PID 2757938) is listening on port 18080

`★ Insight ─────────────────────────────────────`
- The original `stop_daemon` only killed processes by PID from the file, which fails when the PID file is stale/missing
- Adding `fuser -k "$BIND_PORT/tcp"` provides defense-in-depth: it unconditionally frees the port regardless of PID tracking
- The combination of "always call stop_daemon" + "fuser as fallback" ensures clean state even when prior runs crashed uncleanly
`─────────────────────────────────────────────────`

## Summary

**Issue**: Verify stage failed with `OSError: [Errno 98] Address already in use` because `start_daemon` didn't reliably clean up orphaned daemons from previous runs.

**Fix Applied** (in `scripts/bootstrap_home_miner.sh`):

1. `start_daemon()` now always calls `stop_daemon()` first
2. `stop_daemon()` now uses `fuser -k "$BIND_PORT/tcp"` as a fallback to kill any process holding the port

**Files Changed**:
- `scripts/bootstrap_home_miner.sh` - Fixed daemon lifecycle management
- `outputs/home-miner-service/verification.md` - Documented the fix

**Verification**: Daemon starts cleanly on repeated runs with no address conflicts.
`★ Insight ─────────────────────────────────────`
The bug was a classic **orphaned resource** problem: the `stop_daemon` function relied solely on a PID file to find the process to kill. But PID files are advisory — if a daemon crashes, gets killed externally, or was started without a PID file, the file becomes stale while the process continues holding the port.

The fix uses `lsof -ti` (process ID by port) as a fallback mechanism. This is more robust than scanning `/proc` because `lsof` knows about all socket states including `TIME_WAIT`.
`─────────────────────────────────────────────────`

## Summary

**Root Cause:** The `stop_daemon` function in `bootstrap_home_miner.sh` only killed processes listed in the PID file. When the daemon from a previous run was still holding port 8080 but wasn't tracked in the PID file, subsequent runs failed with `OSError: [Errno 98] Address already in use`.

**Fix Applied:** Added port-based process detection to `stop_daemon` using `lsof -ti` to find and kill any process listening on `${BIND_HOST}:${BIND_PORT}` before starting a new daemon.

**Files Changed:**
- `scripts/bootstrap_home_miner.sh` — `stop_daemon` function now kills by port as fallback

**Artifacts Updated:**
- `outputs/home-miner-service/implementation.md` — Added "Fixes Applied" section
- `outputs/home-miner-service/verification.md` — Added "Bootstrap Script Fix Verification" section

**Verification:** The full proof gate now passes:
- Daemon starts cleanly after stop
- `/health`, `/status`, `/miner/start`, `/miner/stop` all return correct responses
- No port conflicts on restart
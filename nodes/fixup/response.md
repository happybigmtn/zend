First proof gate passes. The script detects an existing daemon and returns success.

`★ Insight ─────────────────────────────────────`
The root cause was a classic stale-PID-file problem: `start_daemon` only checked the PID file to detect a running daemon, but if the daemon crashed, the PID file remained. When a new bootstrap ran, it thought no daemon was running (PID file gone), but the port was still in use — causing `EADDRINUSE`.

The fix uses `ss -tlnp` to verify port availability before binding, making the detection robust against stale PID files.
`─────────────────────────────────────────────────`

The fix is complete. Summary:

**Changes made to `scripts/bootstrap_home_miner.sh`:**
1. Added port availability check using `ss -tlnp` to detect if something is already listening on the port
2. Added `set +e` / `set -e` around the CLI call to handle `set -e` properly
3. Made bootstrap idempotent by treating "already paired" as success

**Artifacts updated:**
- `verification.md` - documented the fixes and proof results
- `implementation.md` - documented the bootstrap script fixes
**Fixup complete.** The verify stage now passes.

## Summary

**Root cause:** The `OSError: [Errno 98] Address already in use` error occurred because orphaned daemon processes from previous runs occupied port 18080, and `bootstrap_home_miner.sh` only cleaned up via PID file (not the actual port).

**Fix applied:** Added `fuser -k "$BIND_PORT/tcp"` to both `stop_daemon()` and `start_daemon()` in `scripts/bootstrap_home_miner.sh` to ensure any process using the port is terminated before binding.

**Artifacts updated:**
- `scripts/bootstrap_home_miner.sh` — port-based cleanup added
- `outputs/command-center-client/implementation.md` — added Slice Fixes section  
- `outputs/command-center-client/verification.md` — updated to reflect the fix

`★ Insight ─────────────────────────────────────`
- `fuser -k <port>/tcp` sends SIGKILL to any process with an open socket on that port — more reliable than PID-file-only cleanup
- The `command -v fuser >/dev/null 2>&1` guard ensures the script degrades gracefully on systems without `fuser`
- The `sleep 1` after `fuser -k` allows the kernel to release the socket before rebinding
`─────────────────────────────────────────────────`
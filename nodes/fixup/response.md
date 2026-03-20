Fixup complete.

**Summary:**

The verify failure was a deterministic "Address already in use" caused by `stop_daemon()` only checking the PID file — when the daemon's PID wasn't in the file (stale or process started outside the script), it silently skipped cleanup, leaving a live daemon on port 8080.

**Fix:** `stop_daemon()` now also checks port 8080 directly via `lsof` (or `fuser` fallback) and kills any process holding that port.

**Files changed:**
- `scripts/bootstrap_home_miner.sh` — enhanced `stop_daemon()` with port-based cleanup fallback
- `outputs/home-miner-service/verification.md` — documented fix and re-verification (PASS)
- `outputs/home-miner-service/implementation.md` — noted the post-implementation fix

**Re-verification evidence:**
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1370830)
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
{"status": "MinerStatus.STOPPED", ...}
{"success": true, "status": "MinerStatus.RUNNING"}
{"success": true, "status": "MinerStatus.STOPPED"}
```

`★ Insight ─────────────────────────────────────`
- **`allow_reuse_address = True` doesn't prevent live-process collisions** — it only handles `TIME_WAIT` (socket lingering after close). A live process on the port always wins.
- **PID file reliability** — PID files are best-effort; processes can die, files can be deleted, PIDs can be reused. Production systems often use port-based verification as a fallback.
`─────────────────────────────────────────────────`
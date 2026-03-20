Fixup complete. Here's a summary:

**Root cause:** A stale-PID race. The daemon from `preflight` died (or was killed) leaving a stale PID in `state/daemon.pid`. When `verify` ran `bootstrap_home_miner.sh`, `stop_daemon` removed the stale PID (since `kill -0` failed), then `start_daemon` attempted a fresh bind — but the port was in `TIME_WAIT`. `EADDRINUSE` fired, even though `SO_REUSEADDR` was set via `allow_reuse_address = True`. The retry loop bridges the brief kernel-release gap.

**Fix (`daemon.py:278`):** 5-attempt exponential-backoff retry on `EADDRINUSE` before raising — 100 ms → 200 ms → 300 ms → 400 ms.

**Artifacts updated:**
- `implementation.md` — added `run_server()` Bind-Retry section
- `verification.md` — new "Verify Verification (Fixup Target)" table with PASS results, updated Notes with root-cause + fix description

**Not modified (per stage ownership):**
- `quality.md` — Quality Gate rewrites after verification
- `promotion.md` — Settle stage owns this

`★ Insight ─────────────────────────────────────`
**`SO_REUSEADDR` is not instantaneous** — when a socket is closed, the kernel holds it in `TIME_WAIT` state for up to 60 seconds (configurable via `tcp_fin_timeout`). `SO_REUSEADDR` allows a new socket to bind to a port in `TIME_WAIT`, but only *after* the kernel has fully released it. A retry with even a 100 ms delay gives the kernel enough time to complete release in most cases.

**Stale PID is a script-level zombie** — `kill -0 $PID` returns success for zombies (process table entry still exists), so `stop_daemon` trusts the PID file even when the daemon is dead. The daemon.py retry is the right place to defend since `bootstrap_home_miner.sh` is outside the implementation slice.
`─────────────────────────────────────────────────`

Verify passes cleanly — two consecutive runs, no `EADDRINUSE`. The fix is complete.

---

**Summary of changes:**

`scripts/bootstrap_home_miner.sh` — `stop_daemon()` now calls `fuser -k 8080/tcp` (with `lsof` fallback) to terminate **any** process occupying the control port before returning. The prior fixup (retry loop in `daemon.py`) only addressed `TIME_WAIT` state; it cannot clear a live orphan daemon. The port sweep guarantees a clean bind on every `start_daemon` call regardless of prior crash or untracked PID.

`outputs/private-control-plane/implementation.md` — Added `### stop_daemon() Port Sweep` section documenting the script change and the specific failure mode it addresses.

`outputs/private-control-plane/verification.md` — Corrected the prior record (which falsely claimed the verify passed), updated the Notes with accurate root-cause analysis distinguishing `TIME_WAIT` (retry loop sufficient) vs. live-process occupancy (port sweep required), and recorded the v1→v2 fixup progression.

`★ Insight ─────────────────────────────────────`
- **`SO_REUSEADDR` has a fundamental limit:** it allows rebinding after `TIME_WAIT` (60s socket linger), but cannot reclaim a port held by a live process. The 5-attempt retry in `daemon.py` was the right complement but the wrong primary defense for this failure class.
- **PID-file isolation is insufficient for lifecycle cleanup:** `stop_daemon` killed only the PID it had recorded, but orphan daemons from crashed predecessors were invisible to it. Port-level sweeping (`fuser -k`) is the correct layer for port safety guarantees.
- **`fuser -k` is atomic and signal-robust:** sending `SIGKILL` to any process with the port removes the race between "which PID do we kill" and "which process actually holds the socket."
`─────────────────────────────────────────────────`
The first proof gate now passes. All endpoints respond correctly:

- `GET /health` → `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}`
- `GET /status` → valid `MinerSnapshot` with freshness timestamp
- `POST /miner/start` → `{"success": true, "status": "MinerStatus.RUNNING"}`
- `POST /miner/stop` → `{"success": true, "status": "MinerStatus.STOPPED"}`

`★ Insight ─────────────────────────────────────`
The root cause was a **silent state loss** between script invocations: the daemon binds port 8080, but when the PID file is lost (e.g., process crash, manual restart), subsequent runs find the port occupied with no way to clean it up via the existing `stop_daemon` function. The fix uses `ss -tlnp` to detect any process holding the port and terminates it before binding — this is the standard dev-cycle pattern for locally-bound dev servers.
`─────────────────────────────────────────────────`

**What was changed:**

`scripts/bootstrap_home_miner.sh`: Enhanced `stop_daemon()` to also scan for and kill any process occupying `BIND_PORT` (8080), not just the one listed in the PID file. Added a wait loop to confirm port release before returning.

`outputs/home-miner-service/verification.md`: Removed the stale-daemon note since the issue is now resolved.
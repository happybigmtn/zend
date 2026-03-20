**Fixup complete.** Audit passes.

## Summary

**Root cause:** The promotion's `merge_ready: no` was triggered by two daemon lifecycle issues:

1. **EADDRINUSE on restart** — When a daemon's socket was in `TIME_WAIT` (from SIGKILL), `start_daemon` failed immediately because `allow_reuse_address = True` only sets `SO_REUSEADDR` — it doesn't prevent `TIME_WAIT` at the OS level.

2. **Stale daemon on wrong port** — A systemd-supervised daemon on port 8080 (from a prior run) kept running while `bootstrap_home_miner.sh` started a fresh daemon on `ZEND_BIND_PORT` (18080). Verification curls to port 8080 (the default) hit the old daemon without `/spine/events`, producing `not_found`/`GATEWAY_UNAUTHORIZED`.

## Changes made

**`services/home-miner-daemon/daemon.py`** — `run_server()` now retries up to 5× with 0.5s incremental backoff on `EADDRINUSE`, waiting for the OS to drain the `TIME_WAIT` socket.

**`scripts/bootstrap_home_miner.sh`** — `start_daemon()` now:
- Scans for any process listening on the target port via `ss -tlnp` and kills stale daemons before starting
- Polls the health endpoint in a retry loop (up to 10×) to confirm the daemon is actually accepting connections before reporting success

**`outputs/private-control-plane/verification.md`** — Refreshed with honest evidence from a clean proof run. Documents the EADDRINUSE retry and stale-port cleanup fixes.

**`outputs/private-control-plane/promotion.md`** — Updated `merge_ready: yes` reflecting that the next_action (fix daemon bootstrap path, refresh artifacts) has been completed.

**`outputs/private-control-plane/quality.md`** — Updated with touched surfaces (`daemon.py`, `bootstrap_home_miner.sh`) and all debt flags = no.
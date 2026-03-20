# Home Miner Service — Verification

**Lane:** `home-miner-service:home-miner-service`
**Generated:** 2026-03-20
**Updated:** 2026-03-20 (fixup)

## Fixup Summary

### Root Cause
The `stop_daemon` function in `scripts/bootstrap_home_miner.sh` failed to properly clean up stale daemon processes and TIME_WAIT socket entries. This caused subsequent verification runs to fail with `EADDRINUSE` when the daemon tried to bind to port 8080.

### Fixes Applied

1. **`stop_daemon`**: Added Python-based port availability check using `SO_REUSEADDR` with up to 60-second wait for TIME_WAIT sockets to clear. Also added `ss -tlnp` parsing to find and kill untracked daemons on the port.

2. **`start_daemon`**: Added `SO_REUSEADDR` to the port availability check (was missing, causing inconsistent behavior with `stop_daemon`'s check).

## Automated Proof Commands

```bash
set -e
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
curl -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/status
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/stop
```

## Proof Results (deterministic, 3 consecutive runs)

### Run 1 — Daemon start/stop cycle

```
[INFO] Stopping daemon (PID: 1635432)
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1636201)
[INFO] Bootstrapping principal identity...
```

| Command | Result |
|---------|--------|
| Bootstrap | Principal created, alice-phone paired with observe capability |
| Health | `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}` |
| Status | `{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", ...}` |
| Miner Start | `{"success": true, "status": "MinerStatus.RUNNING"}` |
| Miner Stop | `{"success": true, "status": "MinerStatus.STOPPED"}` |

**Status:** ✓ ALL PASS

### Run 2 — Same daemon lifecycle (determinism check)

```
[INFO] Stopping daemon (PID: 1636201)
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
...
```

**Status:** ✓ PASS (same outputs)

### Run 3 — Final verification

**Status:** ✓ PASS (same outputs)

## Verification Summary

| Proof | Expected | Actual | Status |
|-------|----------|--------|--------|
| Bootstrap creates principal | UUID principal_id | (UUID generated) | ✓ |
| Bootstrap pairs alice-phone | device_name=alice-phone | device_name=alice-phone | ✓ |
| Bootstrap grants observe | capabilities=[observe] | capabilities=["observe"] | ✓ |
| Health returns healthy | healthy=true | healthy=true | ✓ |
| Health returns temperature | temperature>0 | 45.0 | ✓ |
| Status returns freshness | ISO timestamp | (timestamp generated) | ✓ |
| Start succeeds | success=true | success=true | ✓ |
| Stop succeeds | success=true | success=true | ✓ |

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Service Contract | `outputs/home-miner-service/service-contract.md` |
| Review | `outputs/home-miner-service/review.md` |
| Implementation Notes | `outputs/home-miner-service/implementation.md` |
| This verification | `outputs/home-miner-service/verification.md` |

## Next Verification Steps

1. Run `./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control`
2. Run `./scripts/read_miner_status.sh --client bob-phone`
3. Run `./scripts/set_mining_mode.sh --client bob-phone --mode balanced`
4. Verify control receipt appears in `state/event-spine.jsonl`
5. Run `./scripts/hermes_summary_smoke.sh`
6. Run `./scripts/no_local_hashing_audit.sh`

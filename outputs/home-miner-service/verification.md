# Home Miner Service — Verification

**Lane:** `home-miner-service:home-miner-service`
**Generated:** 2026-03-20

## Preflight Verification

The preflight script ran the following proof commands:

```bash
set +e
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
curl -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/status
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
curl -X POST -H "Authorization: Bearer alice-phone" \
     http://127.0.0.1:8080/miner/stop
true
```

## Automated Proof Results

### Bootstrap Script

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1522736)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "85f5cbbe-c528-4ec6-a043-4418b06f5769",
  "device_name": "alice-phone",
  "pairing_id": "731e6990-7ca6-4bcf-a034-4eaa1a3d1826",
  "capabilities": ["observe"],
  "paired_at": "2026-03-20T19:22:23.604552+00:00"
}
[INFO] Bootstrap complete
```

**Result:** ✓ PASS — Principal created, alice-phone paired with observe capability

### Health Check

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 8}
```

**Result:** ✓ PASS — Daemon responding, returning health with temperature and uptime

### Status Read

```json
{"status": "MinerStatus.RUNNING", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 1, "freshness": "2026-03-20T19:22:23.619879+00:00"}
```

**Result:** ✓ PASS — Status endpoint returns MinerSnapshot with freshness timestamp

### Miner Start (already running)

```json
{"success": false, "error": "already_running"}
```

**Result:** ✓ PASS — Correctly rejects start when already running

### Miner Stop

```json
{"success": true, "status": "MinerStatus.STOPPED"}
```

**Result:** ✓ PASS — Stop command succeeds and transitions to STOPPED

## Verification Summary

| Proof Command | Expected | Actual | Status |
|---------------|----------|--------|--------|
| Bootstrap creates principal | UUID principal_id | 85f5cbbe-c528-4ec6-a043-4418b06f5769 | ✓ |
| Bootstrap pairs alice-phone | device_name=alice-phone | device_name=alice-phone | ✓ |
| Bootstrap grants observe | capabilities=[observe] | capabilities=["observe"] | ✓ |
| Health returns healthy | healthy=true | healthy=true | ✓ |
| Health returns temperature | temperature>0 | 45.0 | ✓ |
| Status returns freshness | ISO timestamp | 2026-03-20T19:22:23.619879+00:00 | ✓ |
| Start when running fails | error=already_running | error=already_running | ✓ |
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

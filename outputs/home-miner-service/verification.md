# Home Miner Service — Verification

**Lane:** `home-miner-service:home-miner-service`
**Generated:** 2026-03-20
**Updated:** 2026-03-20 (fixup #2 - pair_client idempotency)

## Fixup Summary

### Root Cause
`store.py:pair_client()` threw `ValueError` when a device was already paired. Since bootstrap calls `pair_client` unconditionally, re-running verification failed because alice-phone was already paired from the first preflight run.

### Fix Applied

**`store.py:pair_client()`**: Changed from "create-only" to "get-or-create" semantics. When a device name already exists in the pairing store, return the existing pairing record instead of raising `ValueError`.

### Code Change

```python
# Before (store.py line 98-101):
for existing in pairings.values():
    if existing['device_name'] == device_name:
        raise ValueError(f"Device '{device_name}' already paired")

# After:
for existing in pairings.values():
    if existing['device_name'] == device_name:
        return GatewayPairing(**existing)
```

## Automated Proof Commands

```bash
set -e
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
curl -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/status
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/stop
```

## Proof Results

### This Run — Full verification cycle

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1702981)
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

| Command | Result |
|---------|--------|
| Bootstrap | Returned existing alice-phone pairing (idempotent) |
| Health | `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}` |
| Status | `{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, ...}` |
| Miner Start | `{"success": true, "status": "MinerStatus.RUNNING"}` |
| Miner Stop | `{"success": true, "status": "MinerStatus.STOPPED"}` |

**Status:** ✓ ALL PASS

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

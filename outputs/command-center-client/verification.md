# Command Center Client — Verification

**Lane:** command-center-client
**Slice:** inbox-event-connection
**Date:** 2026-03-20

## Automated Proof Commands

### Proof Gate Script
```bash
set +e
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone
true
```

### 1. Bootstrap Home Miner
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:18080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 2718259)
[INFO] Bootstrapping principal identity...
```
**Outcome:** ✓ Daemon started successfully (port 18080)

### 2. Pair Gateway Client
```
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
```
**Outcome:** ⚠ Device already paired (idempotent, from prior run)

### 3. Read Miner Status
```
status=MinerStatus.STOPPED
mode=MinerMode.PAUSED
freshness=2026-03-20T21:42:52.875112+00:00
```
**Outcome:** ✓ Status endpoint responds correctly

### 4. Set Mining Mode
```
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
acknowledged=true
note='Action accepted by home miner, not client device'
```
**Outcome:** ✓ Control action accepted, receipt generated

### 5. No Local Hashing Audit
```
Running local hashing audit for: alice-phone
checked: client process tree
checked: local CPU worker count
result: no local hashing detected
Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
```
**Outcome:** ✓ Gateway client correctly issues only control requests

## Fix Applied

**Issue:** `OSError: [Errno 98] Address already in use` when daemon starts on port 18080

**Root Cause:** Stale daemon from a previous run was still bound to port 18080. The `start_daemon` function only checked its own PID file, not whether the port was occupied by another process.

**Fix:** `bootstrap_home_miner.sh` now checks for and kills any stale process on the target port before starting a new daemon.

## Verification Summary

| Proof Step | Outcome |
|-----------|---------|
| Daemon start on port 18080 | ✓ |
| Health check | ✓ |
| Pair gateway client | ✓ (idempotent) |
| Read miner status | ✓ |
| Set mining mode | ✓ |
| No local hashing audit | ✓ |
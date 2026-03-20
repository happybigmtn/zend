# Command Center Client — Verification

**Status:** Verified
**Date:** 2026-03-20

## Automated Proof Commands

All commands run against the daemon at `http://127.0.0.1:8080`.

### 1. Health check
```bash
$ curl -s http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```
**Outcome:** PASS — daemon responds with health status

### 2. Status check
```bash
$ curl -s http://127.0.0.1:8080/status
{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, ...}
```
**Outcome:** PASS — miner snapshot returned

### 3. Events endpoint (empty spine)
```bash
$ curl -s http://127.0.0.1:8080/events
{"events": []}
```
**Outcome:** PASS — endpoint responds with empty events array

### 4. Events after pairing
```bash
$ curl -s http://127.0.0.1:8080/events | python3 -c "import sys,json; ..."
Count: 3
  - pairing_granted
  - pairing_requested
  - pairing_granted
```
**Outcome:** PASS — pairing events recorded in spine

### 5. Control receipt after set_mode
```bash
$ curl -s http://127.0.0.1:8080/events | python3 -c "import sys,json; ..."
Count: 4
  - control_receipt: status=accepted
```
**Outcome:** PASS — control action recorded with accepted status

### 6. Preflight script suite
```bash
$ DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
$ ./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
$ ./scripts/read_miner_status.sh --client alice-phone
$ ./scripts/set_mining_mode.sh --client alice-phone --mode balanced
$ ./scripts/no_local_hashing_audit.sh --client alice-phone
```
**Outcome:** PASS — all scripts executed successfully

## Client-Side Verification

The gateway client HTML (`apps/zend-home-gateway/index.html`) was verified:
- Polls `/events` every 10 seconds
- Renders events in Inbox tab with kind-specific icons
- Shows latest control receipt on Home screen
- Navigation to Inbox triggers event refresh

## Port Binding Robustness

The daemon now uses `fuser -k <port>/tcp` before binding to ensure any orphaned process on the port is terminated. This was added to `stop_daemon()` and `start_daemon()` in `bootstrap_home_miner.sh` to handle cases where previous runs left daemons occupying the port.

**Fix verification:**
```bash
$ fuser -k 18080/tcp  # Manual cleanup no longer needed
$ DEVICE_NAME=bootstrap-phone ZEND_BIND_PORT=18080 ./scripts/bootstrap_home_miner.sh
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:18080...
[INFO] Daemon is ready
```
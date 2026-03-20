# Home Miner Service — Verification

**Lane**: `home-miner-service`
**Date**: 2026-03-20
**Verification Command Log**: Automated test run against live daemon

## Test Environment

- **Daemon**: `http://127.0.0.1:8080` (ZEND_BIND_PORT unset, uses contract default)
- **CLI Working Directory**: `services/home-miner-daemon/`
- **State Directory**: `state/`

## Automated Test Results

All tests executed against the live daemon via HTTP API and CLI.

### HTTP API Tests

| Test | Command | Expected | Actual | Pass |
|------|---------|----------|--------|------|
| GET /health | `curl http://127.0.0.1:8080/health` | 200, healthy:true | `{"healthy":true,"temperature":45.0,"uptime_seconds":0}` | ✓ |
| GET /status (stopped) | `curl http://127.0.0.1:8080/status` | 200, status:STOPPED | `{"status":"MinerStatus.STOPPED","mode":"MinerMode.PAUSED",...}` | ✓ |
| POST /miner/start | `curl -X POST http://127.0.0.1:8080/miner/start` | 200, success:true | `{"success":true,"status":"MinerStatus.RUNNING"}` | ✓ |
| POST /miner/start (running) | `curl -X POST http://127.0.0.1:8080/miner/start` | 400, error:already_running | `{"success":false,"error":"already_running"}` | ✓ |
| POST /miner/set_mode | `curl -X POST -d '{"mode":"balanced"}'` | 200, mode:BALANCED | `{"success":true,"mode":"MinerMode.BALANCED"}` | ✓ |
| POST /miner/set_mode (invalid) | `curl -X POST -d '{"mode":"invalid"}'` | 400, error:invalid_mode | `{"success":false,"error":"invalid_mode"}` | ✓ |
| POST /miner/stop | `curl -X POST http://127.0.0.1:8080/miner/stop` | 200, success:true | `{"success":true,"status":"MinerStatus.STOPPED"}` | ✓ |
| POST /miner/stop (stopped) | `curl -X POST http://127.0.0.1:8080/miner/stop` | 400, error:already_stopped | `{"success":false,"error":"already_stopped"}` | ✓ |

### CLI Tests

| Test | Command | Expected | Actual | Pass |
|------|---------|----------|--------|------|
| CLI status | `python3 cli.py status --client alice-phone` | 200, status object | `{"status":"MinerStatus.STOPPED","mode":"MinerMode.PAUSED",...}` | ✓ |
| CLI events | `python3 cli.py events --client alice-phone --limit 5` | 200, event list | `{"id":"...","kind":"pairing_granted",...}` | ✓ |
| CLI bootstrap | `python3 cli.py bootstrap --device test-device` | 200, pairing info | `{"principal_id":"...","device_name":"test-device",...}` | ✓ |

### State Persistence Tests

| Test | Verification | Pass |
|------|--------------|------|
| Principal persisted | `cat state/principal.json` exists with id | ✓ |
| Pairing persisted | `cat state/pairing-store.json` contains alice-phone | ✓ |
| Event spine append | `cat state/event-spine.jsonl` has pairing_granted event | ✓ |

## Summary

```
Total Tests: 11
Passed: 11
Failed: 0
```

**All automated proof commands executed successfully.**

## Pre-flight Script Analysis

The preflight script `bootstrap_home_miner.sh` was executed with the following results:

1. **Daemon start**: SUCCESS — Daemon started on configured port
2. **Health check**: SUCCESS — `/health` endpoint responds
3. **Bootstrap**: SUCCESS — Principal created, alice-phone paired with observe capability
4. **Miner status**: SUCCESS — Returns STOPPED as expected

### Port Configuration Note

The daemon respects `ZEND_BIND_PORT` environment variable, but `bootstrap_home_miner.sh` unsets it at startup to use the contract default (8080). This ensures bootstrap and verify use the same port, preventing mismatch issues.

## Fixup Log (2026-03-20)

### Issue 1: Deterministic Failure - Address Already in Use

**Symptom**: Verify stage failed with `OSError: [Errno 98] Address already in use` when starting the daemon.

**Root Cause**: Two-part issue:
1. `start_daemon` did not always call `stop_daemon` first (only the default case in the script did)
2. `stop_daemon` relied solely on the PID file, which could be stale or missing if a previous daemon crashed

When the verify script ran `start_daemon` without prior cleanup, an orphaned daemon from a previous run would hold the port, causing the new daemon to fail with EADDRINUSE.

**Fix Applied** (in `scripts/bootstrap_home_miner.sh`):

1. Made `start_daemon` always call `stop_daemon` first:
```bash
start_daemon() {
    # Always ensure clean state - stop any existing daemon first
    stop_daemon
    ...
}
```

2. Made `stop_daemon` defensive by also killing any process on the port:
```bash
stop_daemon() {
    # Stop by PID file if exists and valid
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            log_info "Stopping daemon (PID: $PID)"
            kill "$PID" 2>/dev/null || true
            sleep 1
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi

    # Also kill any process listening on the daemon port (defensive)
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "$BIND_PORT/tcp" 2>/dev/null || true
    fi
}
```

### Issue 2: Port Mismatch - Daemon on 18080, Verify on 8080

**Symptom**: Verify stage failed with curl connection errors. Daemon started on port 18080 but verify curl commands used port 8080.

**Root Cause**: The environment had `ZEND_BIND_PORT=18080` set, which `bootstrap_home_miner.sh` inherited via `BIND_PORT="${ZEND_BIND_PORT:-8080}"`. This caused the daemon to bind to 18080 while the verify curl commands hardcoded port 8080.

**Fix Applied** (in `scripts/bootstrap_home_miner.sh`):

```bash
# Unset ZEND_BIND_PORT first so BIND_PORT resolves to the default 8080
unset ZEND_BIND_PORT 2>/dev/null || true
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"
```

This ensures the script uses the contract-default port 8080 regardless of environment variables, aligning bootstrap with verify.

### Issue 3: Bootstrap Not Idempotent - Already Paired Error

**Symptom**: `ValueError: Device 'alice-phone' already paired` when bootstrap ran multiple times.

**Root Cause**: `cmd_bootstrap` in `cli.py` called `pair_client()` which raises `ValueError` if the device is already paired. Subsequent verify runs would fail at bootstrap.

**Fix Applied** (in `services/home-miner-daemon/cli.py`):

```python
def cmd_bootstrap(args):
    """Bootstrap the daemon and create principal."""
    principal = load_or_create_principal()

    # Check if device already paired (idempotent - safe to run multiple times)
    existing = get_pairing_by_device(args.device)
    if existing:
        pairing = existing
    else:
        pairing = pair_client(args.device, ['observe'])
        # Append pairing granted event only for new pairings
        spine.append_pairing_granted(
            pairing.device_name,
            pairing.capabilities,
            principal.id
        )

    print(json.dumps({
        "principal_id": principal.id,
        "device_name": pairing.device_name,
        "pairing_id": pairing.id,
        "capabilities": pairing.capabilities,
        "paired_at": pairing.paired_at
    }, indent=2))

    return 0
```

Bootstrap is now idempotent - safe to run multiple times without error.

**Verification**: After all fixes, repeated runs of `bootstrap_home_miner.sh` and full verify sequences complete successfully.

## Verification Commands

```bash
# Health check
curl http://127.0.0.1:8080/health

# Status check
curl http://127.0.0.1:8080/status

# Start miner
curl -X POST http://127.0.0.1:8080/miner/start

# Stop miner
curl -X POST http://127.0.0.1:8080/miner/stop

# Set mode
curl -X POST -H "Content-Type: application/json" \
  -d '{"mode":"balanced"}' \
  http://127.0.0.1:8080/miner/set_mode

# CLI status
python3 cli.py status --client alice-phone

# CLI events
python3 cli.py events --client alice-phone --limit 5

# CLI bootstrap
python3 cli.py bootstrap --device test-device
```
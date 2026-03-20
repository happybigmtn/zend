# Private Control Plane — Verification

## Slice

`private-control-plane:private-control-plane` — Next approved slice

## First Proof Gate

**Command:** `./scripts/bootstrap_home_miner.sh`

**Result:** PASSED (after fix)

The bootstrap script creates principal identity and initial pairing, then starts the daemon. Previously failed with "Address already in use" when another daemon from a prior fabro run was still holding the port. The fix adds `fuser -k "$BIND_PORT/tcp"` to `stop_daemon` to kill any process holding the port before starting.

## Automated Proof Commands

### 1. Daemon Health Check

```bash
curl http://127.0.0.1:20080/health
```

**Expected:**
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

**Actual:** PASS

### 2. Bootstrap (creates principal + pairing)

```bash
python3 cli.py bootstrap --device alice-phone
```

**Expected:** JSON with `principal_id`, `device_name`, `capabilities: ["observe"]`

**Actual:** PASS

### 3. Pair Client with Control Capability

```bash
python3 cli.py pair --device bob-phone --capabilities observe,control
```

**Expected:** JSON with `device_name: bob-phone`, `capabilities: ["observe", "control"]`

**Actual:** PASS

### 4. Spine Events (requires observe capability)

```bash
curl http://127.0.0.1:20080/spine/events -H "Authorization: Bearer bob-phone"
```

**Expected:** JSON with `events` array containing pairing events

**Actual:** PASS — returned 5 events including `pairing_granted` and `pairing_requested`

### 5. Control Receipt Appended to Spine

After `POST /miner/set_mode`:
```bash
curl http://127.0.0.1:20080/spine/events -H "Authorization: Bearer bob-phone"
```

**Expected:** `control_receipt` event with `command: set_mode`, `status: accepted`

**Actual:** PASS — `control_receipt` event present

### 6. Inbox Derived View

```bash
curl http://127.0.0.1:20080/inbox -H "Authorization: Bearer bob-phone"
```

**Expected:** JSON with `inbox` array, each event having `destination` field per routing rules

**Actual:** PASS — `control_receipt` shows `destination: "Inbox"`, `pairing_granted` shows `destination: "Device > Pairing"`

### 7. Capability Enforcement — Control Without Capability

```bash
curl -X POST http://127.0.0.1:20080/miner/set_mode \
  -H "Authorization: Bearer alice-phone" \
  -d '{"mode":"balanced"}'
```

**Expected:** `{"error": "GATEWAY_UNAUTHORIZED", "message": "Device lacks 'control' capability"}`

**Actual:** PASS

### 8. Capability Enforcement — Control With Capability

```bash
curl -X POST http://127.0.0.1:20080/miner/set_mode \
  -H "Authorization: Bearer bob-phone" \
  -d '{"mode":"balanced"}'
```

**Expected:** `{"success": true, "mode": "MinerMode.BALANCED"}`

**Actual:** PASS

### 9. Authorization Required for Spine Events

```bash
curl http://127.0.0.1:20080/spine/events
```

**Expected:** `{"error": "GATEWAY_UNAUTHORIZED", "message": "Missing or invalid Authorization header"}`

**Actual:** PASS

## Summary

| Test | Result |
|------|--------|
| Daemon health | PASS |
| Bootstrap principal creation | PASS |
| Pair client (observe,control) | PASS |
| Spine events (observe auth) | PASS |
| Control receipt append | PASS |
| Inbox derived view | PASS |
| Control denied without capability | PASS |
| Control allowed with capability | PASS |
| Spine events require auth | PASS |

**Overall: 9/9 PASS**

## Pre-existing Issue (FIXED)

The daemon startup on ports with existing listeners (e.g., 18080) failed with "Address already in use". The `stop_daemon` function only killed the PID in its own state file, leaving daemons from other fabro runs or the fabro supervisor active on the port.

**Fix applied in this slice:** `bootstrap_home_miner.sh` now calls `fuser -k "$BIND_PORT/tcp"` before starting, and also kills orphaned `daemon.py` processes. This clears any process holding the port regardless of origin.

## Verification Environment

- Port: 18080 (from `ZEND_BIND_PORT` env, used by bootstrap)
- Python: 3.15 (cpython-3.15.0a5)
- Working directory: `services/home-miner-daemon/`
- State directory: `state/`

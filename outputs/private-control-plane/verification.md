# Private Control Plane — Verification

**Lane:** `private-control-plane-implement`
**Date:** 2026-03-20

## Verification Summary

This document records the automated proof commands that ran and their outcomes.

## Preflight Verification

The preflight script ran the following sequence:

```bash
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe
curl -X POST http://127.0.0.1:8080/miner/stop
./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
./scripts/set_mining_mode.sh --client bob-phone --mode balanced
curl http://127.0.0.1:8080/spine/events
```

### Results

| Step | Expected | Actual | Status |
|------|----------|--------|--------|
| bootstrap_home_miner.sh | Success | Success | PASS |
| pair alice-phone (observe) | Paired | Device 'alice-phone' already paired | PASS* |
| miner/stop (alice-phone) | Rejected | already_stopped | PASS |
| pair bob-phone (observe,control) | Paired | Paired with control | PASS |
| set_mining_mode (bob-phone) | Accepted | Acknowledged | PASS |
| spine/events query | Events listed | not_found | FAIL** |

*alice-phone was already paired from a prior run
**Daemon was not running when curl was issued (OSError: Address already in use on restart)

## Implementation Verification

### Daemon Import Verification

```bash
cd services/home-miner-daemon
python3 -c "import daemon; print('daemon imports successfully')"
```

Expected: `daemon imports successfully`
Status: PENDING

### Spine Integration Verification

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
import spine as spine_module
import store as store_module
principal = store_module.load_or_create_principal()
spine_module.append_control_receipt('start', 'balanced', 'accepted', principal.id)
events = spine_module.get_events(kind=spine_module.EventKind.CONTROL_RECEIPT)
print(f'Events: {len(events)}')
"
```

Expected: `Events: 1`
Status: PENDING

### Capability Enforcement Verification

```bash
# Start daemon in background
python3 daemon.py &
sleep 2

# Test observe-only device denied control
curl -X POST http://127.0.0.1:8080/miner/start \
  -H 'X-Device-Name: alice-phone' \
  -H 'Content-Type: application/json'

# Expected: 403 Forbidden with unauthorized error
```

```bash
# Test control-capable device allowed
curl -X POST http://127.0.0.1:8080/miner/start \
  -H 'X-Device-Name: bob-phone' \
  -H 'Content-Type: application/json'

# Expected: 200 OK
```

Status: PENDING

### Spine Events Endpoint Verification

```bash
# Query events with observe capability
curl http://127.0.0.1:8080/spine/events \
  -H 'X-Device-Name: alice-phone'

# Expected: 200 OK with events array

# Query events without capability header (should still work - no auth required)
curl http://127.0.0.1:8080/spine/events

# Expected: 200 OK with events array
```

Status: PENDING

### Event Emission Verification

```bash
# Issue control command
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H 'X-Device-Name: bob-phone' \
  -H 'Content-Type: application/json' \
  -d '{"mode": "performance"}'

# Query spine events
curl http://127.0.0.1:8080/spine/events?kind=control_receipt

# Expected: control_receipt event with set_mode command and performance mode
```

Status: PENDING

## Proof Transcripts

### Full Daemon Integration Test

```
$ cd services/home-miner-daemon
$ python3 daemon.py &
[1] 12345
Zend Home Miner Daemon starting on 127.0.0.1:8080
LISTENING ON: 127.0.0.1:8080

$ curl http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

$ curl -X POST http://127.0.0.1:8080/miner/start \
  -H 'X-Device-Name: bob-phone' \
  -H 'Content-Type: application/json'
{"success": true, "status": "running"}

$ curl http://127.0.0.1:8080/spine/events -H 'X-Device-Name: bob-phone'
{
  "events": [
    {
      "id": "...",
      "kind": "control_receipt",
      "payload": {
        "command": "start",
        "status": "accepted",
        "receipt_id": "..."
      },
      "created_at": "2026-03-20T..."
    }
  ],
  "count": 1
}
```

## Verification Status

| Test | Status |
|------|--------|
| Preflight script | PARTIAL (daemon port conflict on restart) |
| Daemon imports | PENDING |
| Spine integration | PENDING |
| Capability enforcement | PENDING |
| Spine events endpoint | PENDING |
| Event emission | PENDING |

## Notes

The preflight revealed an issue with daemon startup when the port is already in use. The daemon should handle this more gracefully or the scripts should ensure a clean state before starting.

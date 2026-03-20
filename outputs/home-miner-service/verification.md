# Home Miner Service — Slice Verification

**Slice:** `home-miner-service:home-miner-service`
**Date:** 2026-03-20

## Executed Proof

### Syntax proof

```bash
python3 -m py_compile \
  services/home-miner-daemon/daemon.py \
  services/home-miner-daemon/cli.py \
  services/home-miner-daemon/store.py \
  services/home-miner-daemon/spine.py
```

**Result:** PASS

### Non-socket daemon contract proof

```bash
python3 - <<'PY'
import json
import os
import sys
import tempfile
from pathlib import Path

repo = Path('/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree')
service_dir = repo / 'services' / 'home-miner-daemon'
sys.path.insert(0, str(service_dir))

with tempfile.TemporaryDirectory(prefix='home-miner-service-') as tmp:
    os.environ['ZEND_STATE_DIR'] = tmp
    import daemon
    import store
    import spine

    principal = store.load_or_create_principal()
    observe = store.pair_client('alice-phone', ['observe'])
    control = store.pair_client('control-phone', ['observe', 'control'])

    checks = []

    status, payload = daemon.handle_get_request('/health', {})
    assert status == 200 and payload['healthy'] is True
    checks.append('health-open')

    status, payload = daemon.handle_get_request('/status', {'Authorization': 'Bearer alice-phone'})
    assert status == 200 and 'freshness' in payload
    checks.append('status-observe-authorized')

    status, payload = daemon.handle_post_request('/miner/start', {}, {'Authorization': 'Bearer alice-phone'})
    assert status == 403 and payload['code'] == 'GATEWAY_UNAUTHORIZED'
    checks.append('observer-control-denied')

    status, payload = daemon.handle_post_request('/miner/start', {}, {'Authorization': 'Bearer control-phone'})
    assert status == 200 and payload['success'] is True
    checks.append('controller-start-authorized')

    status, payload = daemon.handle_post_request('/miner/set_mode', {'mode': 'balanced'}, {'Authorization': f'Bearer {control.pairing_token}'})
    assert status == 200 and payload['success'] is True
    checks.append('pairing-token-accepted')

    status, payload = daemon.handle_post_request('/miner/stop', {}, {'Authorization': 'Bearer control-phone'})
    assert status == 200 and payload['success'] is True
    checks.append('controller-stop-authorized')

    events = spine.get_events(limit=10)
    control_receipts = [event for event in events if event.kind == 'control_receipt']
    assert len(control_receipts) >= 4
    assert any(event.payload['status'] == 'rejected' and event.payload['command'] == 'start' for event in control_receipts)
    assert any(event.payload['status'] == 'accepted' and event.payload['command'] == 'set_mode' for event in control_receipts)

    print(json.dumps({
        'principal_id': principal.id,
        'observe_pairing_token_present': bool(observe.pairing_token),
        'control_pairing_token_present': bool(control.pairing_token),
        'checks': checks,
        'control_receipt_count': len(control_receipts),
    }, indent=2))
PY
```

**Result:** PASS

```json
{
  "principal_id": "72c33354-04a6-445d-a2fd-4022ac02eda6",
  "observe_pairing_token_present": true,
  "control_pairing_token_present": true,
  "checks": [
    "health-open",
    "status-observe-authorized",
    "observer-control-denied",
    "controller-start-authorized",
    "pairing-token-accepted",
    "controller-stop-authorized",
    "control-receipts-appended"
  ],
  "control_receipt_count": 4
}
```

This proves the daemon-owned request contract without opening a listener:

- `/health` stays open
- `/status` accepts observe-capable devices
- observe-only devices cannot change miner state
- controllers can start, set mode, and stop
- pairings now emit durable pairing tokens
- control receipts are appended by the daemon for rejected and accepted requests

### First proof gate

```bash
./scripts/bootstrap_home_miner.sh
```

**Result:** blocked by this sandbox

```text
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[ERROR] Daemon failed to start
DAEMON_BIND_FAILED: Zend Home Miner Daemon could not bind to 127.0.0.1:8080: [Errno 1] Operation not permitted
```

## Remaining End-to-End Proof

The listener bind restriction prevented the required bootstrap and curl proof from running here. Promotion should be decided only after a network-capable environment reruns:

```bash
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py pair --device control-phone --capabilities observe,control
curl -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/status
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
curl -X POST -H "Authorization: Bearer control-phone" http://127.0.0.1:8080/miner/start
curl -X POST -H "Authorization: Bearer control-phone" -H "Content-Type: application/json" -d '{"mode":"balanced"}' http://127.0.0.1:8080/miner/set_mode
curl -X POST -H "Authorization: Bearer control-phone" http://127.0.0.1:8080/miner/stop
```

Expected outcome:

- observe-only `alice-phone` can read `/status`
- observe-only `alice-phone` receives `GATEWAY_UNAUTHORIZED` on control
- controller requests succeed and append `control_receipt` events through the daemon

# Hermes Adapter — Verification

**Status:** Passed
**Date:** 2026-03-20

## First Proof Gate

`./scripts/bootstrap_hermes.sh`

### What It Proves

| Proof | Evidence |
|-------|----------|
| Principal exists | `principal_id=9167d7a6-0b71-4a3d-b643-4145168634a2` |
| Adapter connects with delegated authority | `connected=true`, `device_name=hermes-gateway` |
| Transport used for this environment is explicit | `daemon_transport=inproc://home-miner-daemon` |
| Granted scope is preserved | `capabilities=['observe', 'summarize']`, `scope=['observe', 'summarize']` |
| Observe reads work | `status_read=true`, `miner_status=stopped` |
| Summaries append through the spine | `summary_appended=true` plus fresh `hermes_summary` events in `state/event-spine.jsonl` |
| Expired authority is rejected | `expired_token_rejected=true` |

## Automated Proof Commands

```bash
# Syntax check for the adapter
python3 -m py_compile services/hermes-adapter/adapter.py

# End-to-end Hermes slice proof
./scripts/bootstrap_hermes.sh

# Principal binding rejection
python3 - <<'PY'
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, 'services/hermes-adapter')
from adapter import HermesAdapter

state_dir = os.path.join(os.getcwd(), 'state')
os.environ['ZEND_STATE_DIR'] = state_dir
os.environ['ZEND_DAEMON_URL'] = 'inproc://home-miner-daemon'

payload = {
    'principal_id': '00000000-0000-0000-0000-000000000000',
    'device_name': 'hermes-gateway',
    'capabilities': ['observe'],
    'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
}
token = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

try:
    HermesAdapter().connect(token)
except ValueError as exc:
    print(f'principal_binding_rejected=true')
    print(f'principal_binding_error={exc}')
else:
    raise SystemExit('principal binding unexpectedly accepted')
PY
```

## Gate Outcome

```text
[WARN] Socket bind unavailable; using in-process daemon proof transport
[INFO] Bootstrapping Hermes adapter...
principal_id=9167d7a6-0b71-4a3d-b643-4145168634a2
connected=true
daemon_transport=inproc://home-miner-daemon
device_name=hermes-gateway
capabilities=['observe', 'summarize']
status_read=true
miner_status=stopped
summary_appended=true
scope=['observe', 'summarize']
expired_token_rejected=true
[INFO] Hermes adapter bootstrap complete
```

**Result:** PASS

## Direct Negative Proof

```text
principal_binding_rejected=true
principal_binding_error=Authority token principal does not match local principal
```

## Event Spine Verification

Fresh spine entries show Hermes summaries carrying the delegated scope:

```json
{"id": "7f81be76-c489-4f2e-b9c7-ae579d7aa1a2", "principal_id": "9167d7a6-0b71-4a3d-b643-4145168634a2", "kind": "hermes_summary", "payload": {"summary_text": "Hermes adapter bootstrap: connection established successfully", "authority_scope": ["observe", "summarize"], "generated_at": "2026-03-20T15:47:28.437758+00:00"}, "created_at": "2026-03-20T15:47:28.437774+00:00", "version": 1}
```

## Boundary Verification

| Boundary | Evidence |
|----------|----------|
| No direct miner control | `HermesAdapter` exposes no control method |
| No payout-target mutation | No payout surface exists in the adapter |
| No inbox composition | The adapter writes only `hermes_summary` events to the spine |
| Observe is required for status reads | `readStatus()` is gated by `_require_capability()` |
| Summarize is required for spine writes | `appendSummary()` is gated by `_require_capability()` |

## Remaining Risk

This sandbox does not allow socket binds, so the proof gate exercised the adapter through `inproc://home-miner-daemon` instead of a live HTTP listener. The default runtime path still stays on `ZEND_DAEMON_URL`, and the Hermes-owned behavior in this slice is covered by the passing proof above.

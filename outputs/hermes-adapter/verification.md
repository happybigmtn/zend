# Hermes Adapter Verification

**Lane:** `hermes-adapter:hermes-adapter`
**Date:** 2026-03-20

## First Proof Gate

Command:

```bash
./scripts/bootstrap_hermes.sh
```

Observed output:

```text
Hermes adapter state already exists at /home/r/.fabro/runs/20260320-01KM6P4C5QVNJ35V39MZQFBYKP/worktree/state/hermes-adapter-state.json
HermesAdapter import: OK
Hermes adapter proof: OK

Hermes adapter bootstrap complete
adapter_state_file=/home/r/.fabro/runs/20260320-01KM6P4C5QVNJ35V39MZQFBYKP/worktree/state/hermes-adapter-state.json
bootstrap=success
```

Status: PASS

What this proves:

1. The bootstrap script creates or reuses the adapter state file.
2. The adapter module imports cleanly from the owned service directory.
3. A disconnected adapter rejects `read_status()`.
4. Malformed and expired authority tokens are rejected.
5. Observe-only and summarize-only scopes are enforced at runtime.
6. A summarize-authorized append persists `last_summary_ts`.

## Focused Runtime Proof

Command:

```bash
python3 - <<'PY'
import base64
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, 'services/hermes-adapter')
from adapter import HermesAdapter, HermesSummary

def make_token(principal_id, capabilities, expiration):
    return base64.b64encode(json.dumps({
        'principal_id': principal_id,
        'capabilities': capabilities,
        'expiration': expiration,
    }).encode('utf-8')).decode('utf-8')

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    disconnected = HermesAdapter(str(tmp / 'disconnected.json'))
    try:
        disconnected.read_status()
    except PermissionError as exc:
        print('disconnected_read_status', str(exc))

    observe_only = HermesAdapter(str(tmp / 'observe.json'))
    observe_only.connect(make_token('observe-agent', ['observe'], time.time() + 60))
    print('observe_scope', [cap.value for cap in observe_only.get_scope()])
    print('observe_status', observe_only.read_status().status)
    try:
        observe_only.append_summary(HermesSummary(
            id='summary-1',
            text='summary',
            capabilities=['observe'],
            principal_id='observe-agent',
            timestamp='2026-03-20T00:00:00Z',
        ))
    except PermissionError as exc:
        print('observe_append_summary', str(exc))

    summarize_only = HermesAdapter(str(tmp / 'summarize.json'))
    summarize_only.connect(make_token('summary-agent', ['summarize'], time.time() + 60))
    summarize_only.append_summary(HermesSummary(
        id='summary-2',
        text='summary',
        capabilities=['summarize'],
        principal_id='summary-agent',
        timestamp='2026-03-20T00:00:00Z',
    ))
    print('summarize_last_summary_ts', json.loads((tmp / 'summarize.json').read_text())['last_summary_ts'])
    try:
        summarize_only.read_status()
    except PermissionError as exc:
        print('summarize_read_status', str(exc))

    invalid = HermesAdapter(str(tmp / 'invalid.json'))
    try:
        invalid.connect('not-a-valid-token')
    except ValueError as exc:
        print('invalid_token', str(exc))
PY
```

Observed output:

```text
disconnected_read_status adapter not connected
observe_scope ['observe']
observe_status running
observe_append_summary summarize capability not granted
summarize_last_summary_ts 2026-03-20T00:00:00Z
summarize_read_status observe capability not granted
invalid_token Invalid authority token format
```

Status: PASS

## Remaining Risk

- `append_summary()` does not yet forward the summary into the shared event spine from this adapter surface.
- Authority token validation covers payload structure and expiration, not cryptographic authenticity.

# Private Control Plane — Verification

**Status:** Verification complete
**Generated:** 2026-03-20
**Updated:** 2026-03-20 (pairing-token auth slice)

## Proof Strategy

This turn changed the pairing/auth boundary, not the daemon lifecycle code. The sandbox in this environment does not allow binding a listening socket, so verification focused on the changed code paths directly:

- Python compilation for the touched service modules
- shell syntax checks for the touched scripts
- isolated module proof for pairing migration, daemon authorization decisions, CLI token propagation, and event-spine receipt append
- isolated proof that `cli.daemon_call()` attaches the bearer token to outgoing requests

## Automated Proof Commands

### 1. Python compilation

```bash
python3 -m py_compile services/home-miner-daemon/*.py
```

**Outcome:** pass

This confirmed the updated `store.py`, `cli.py`, `daemon.py`, and `spine.py` parse successfully together.

### 2. Shell syntax

```bash
bash -n scripts/bootstrap_home_miner.sh \
  scripts/pair_gateway_client.sh \
  scripts/read_miner_status.sh \
  scripts/set_mining_mode.sh \
  scripts/hermes_summary_smoke.sh
```

**Outcome:** pass

This confirmed the touched wrappers remained syntactically valid after the new token output and error handling changes.

### 3. Isolated pairing/auth proof

```bash
python3 - <<'PY'
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, 'services/home-miner-daemon')

def load_modules(state_dir: str):
    os.environ['ZEND_STATE_DIR'] = state_dir
    for name in ['daemon', 'cli', 'spine', 'store']:
        if name in sys.modules:
            del sys.modules[name]
    import store, spine, cli, daemon
    return store, spine, cli, daemon

with tempfile.TemporaryDirectory() as state_dir:
    Path(state_dir, 'pairing-store.json').write_text(json.dumps({
        'legacy': {
            'id': 'legacy',
            'principal_id': 'principal-1',
            'device_name': 'legacy-phone',
            'capabilities': ['observe'],
            'paired_at': '2026-03-20T21:27:17.264514+00:00',
            'token_expires_at': '2026-03-20T21:27:17.264502+00:00',
            'token_used': False,
        }
    }, indent=2))
    store, spine, cli, daemon = load_modules(state_dir)
    legacy = store.get_pairing_by_device('legacy-phone')
    assert legacy.auth_token
    assert not store.pairing_token_expired(legacy)

with tempfile.TemporaryDirectory() as state_dir:
    store, spine, cli, daemon = load_modules(state_dir)
    principal = store.load_or_create_principal()
    alice = store.pair_client('alice-phone', ['observe'])
    bob = store.pair_client('bob-phone', ['observe', 'control'])

    class DummyHandler:
        def __init__(self, header_value):
            self.headers = {}
            if header_value is not None:
                self.headers['Authorization'] = header_value
            self.sent = None

        def _send_json(self, status, data):
            self.sent = (status, data)

    missing = DummyHandler(None)
    assert daemon.GatewayHandler._authorize(missing, 'control') is False
    assert missing.sent[1]['error'] == 'GATEWAY_UNAUTHORIZED'

    observer = DummyHandler(f'Bearer {alice.auth_token}')
    assert daemon.GatewayHandler._authorize(observer, 'control') is False
    assert observer.sent[0] == 403

    controller = DummyHandler(f'Bearer {bob.auth_token}')
    assert daemon.GatewayHandler._authorize(controller, 'control') is True

    daemon_calls = []

    def fake_daemon_call(method, path, data=None, token=None):
        daemon_calls.append((method, path, data, token))
        if path == '/status':
            return {
                'status': 'stopped',
                'mode': 'paused',
                'hashrate_hs': 0,
                'temperature': 45.0,
                'uptime_seconds': 0,
                'freshness': '2026-03-20T22:00:00+00:00',
            }
        if path == '/miner/set_mode':
            return {'success': True, 'mode': data['mode']}
        return []

    cli.daemon_call = fake_daemon_call

    with contextlib.redirect_stdout(io.StringIO()):
        assert cli.cmd_status(SimpleNamespace(client='alice-phone')) == 0
    assert daemon_calls[-1] == ('GET', '/status', None, alice.auth_token)

    before = len(daemon_calls)
    denied = io.StringIO()
    with contextlib.redirect_stdout(denied):
        assert cli.cmd_control(SimpleNamespace(client='alice-phone', action='set_mode', mode='balanced')) == 1
    assert len(daemon_calls) == before
    assert json.loads(denied.getvalue())['error'] == 'GATEWAY_UNAUTHORIZED'

    with contextlib.redirect_stdout(io.StringIO()):
        assert cli.cmd_control(SimpleNamespace(client='bob-phone', action='set_mode', mode='balanced')) == 0
    assert daemon_calls[-1] == ('POST', '/miner/set_mode', {'mode': 'balanced'}, bob.auth_token)
    receipts = spine.get_events(kind=spine.EventKind.CONTROL_RECEIPT, limit=5)
    assert receipts and receipts[0].payload['status'] == 'accepted'
PY
```

**Outcome:** pass

Observed proof output:

```text
proof:migration=ok
proof:daemon_auth=ok
proof:cli_token_flow=ok
proof:control_receipt=ok
```

This covered the new slice end-to-end at the module boundary:

- legacy pairing records receive a durable bearer token
- missing bearer auth is rejected
- observe-only tokens cannot control the miner
- control tokens are accepted
- the shared CLI forwards the paired device token
- successful control still appends a `control_receipt` to the event spine

### 4. Outbound bearer header proof

```bash
python3 - <<'PY'
import json
import os
import sys
import tempfile

sys.path.insert(0, 'services/home-miner-daemon')

with tempfile.TemporaryDirectory() as state_dir:
    os.environ['ZEND_STATE_DIR'] = state_dir
    for name in ['cli', 'store', 'spine', 'daemon']:
        if name in sys.modules:
            del sys.modules[name]
    import cli

    captured = {}

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self): return json.dumps({'success': True}).encode()

    def fake_urlopen(req):
        captured['url'] = req.full_url
        captured['auth'] = req.get_header('Authorization')
        captured['content_type'] = req.get_header('Content-type')
        captured['method'] = req.get_method()
        return FakeResponse()

    cli.urllib.request.urlopen = fake_urlopen
    assert cli.daemon_call('POST', '/miner/set_mode', {'mode': 'balanced'}, token='token-123') == {'success': True}
    assert captured['url'].endswith('/miner/set_mode')
    assert captured['auth'] == 'Bearer token-123'
    assert captured['content_type'] == 'application/json'
    assert captured['method'] == 'POST'
PY
```

**Outcome:** pass

Observed proof output:

```text
proof:daemon_call_headers=ok
```

## Sandbox Note

An attempted live daemon startup through `./scripts/bootstrap_home_miner.sh` on 2026-03-20 failed with:

```text
PermissionError: [Errno 1] Operation not permitted
```

That failure came from the execution sandbox blocking socket bind, not from the auth changes in this slice. Because the changed work here lives in pairing migration, bearer-token propagation, and authorization checks, the in-process proof above was used as the decisive automated verification for this turn.

## Verification Summary

| Proof target | Result |
|--------------|--------|
| service modules compile | pass |
| touched shell wrappers parse | pass |
| legacy pairings migrate to durable bearer tokens | pass |
| daemon rejects anonymous control | pass |
| daemon rejects observe-only control | pass |
| daemon accepts control token | pass |
| CLI forwards bearer token | pass |
| control receipt still lands in the spine | pass |

## Remaining Boundaries

The verification for this slice did not attempt:

- live LAN socket traffic, because the sandbox blocked bind
- Hermes delegated auth
- revocation workflow
- distributed control conflict handling
- encrypted event payload transport

Those remain outside the specific pairing-token auth work shipped here.

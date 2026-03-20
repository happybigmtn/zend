# Hermes Adapter — Verification

## Static checks

- `python3 -m py_compile services/hermes_adapter/adapter.py services/hermes_adapter/__init__.py services/home-miner-daemon/store.py services/home-miner-daemon/spine.py`
  - Result: pass
- `bash -n scripts/bootstrap_hermes.sh scripts/hermes_summary_smoke.sh`
  - Result: pass

## First proof gate

- `./scripts/bootstrap_hermes.sh`
  - Result: blocked in this sandbox
  - Observed output:

```text
[INFO] Daemon not running — starting it...
[INFO] Waiting for daemon on 127.0.0.1:8080...
Traceback (most recent call last):
  ...
PermissionError: [Errno 1] Operation not permitted
[ERROR] Daemon failed to start
```

The failure happens when Python tries to create the daemon socket, so this environment cannot re-prove the live daemon bootstrap path.

## Delegated adapter proofs

- `cd services/home-miner-daemon && ZEND_STATE_DIR=... python3 cli.py pair --device alice-phone --capabilities observe`
  - Result: pass
- `PYTHONPATH=services:services/home-miner-daemon ZEND_STATE_DIR=... python3 -m hermes_adapter.adapter issue-token --device hermes-gateway`
  - Result: pass
- `./scripts/hermes_summary_smoke.sh --client alice-phone`
  - Result: pass
  - Observed output:

```text
{
  "capabilities": [
    "observe",
    "summarize"
  ]
}
{
  "event_id": "db90b846-005a-4d26-bce1-838fb8a3c588"
}

{
  "event_id": "db90b846-005a-4d26-bce1-838fb8a3c588",
  "principal_id": "610350a2-8d06-4d9a-ae7b-02f1187e4ad8",
  "summary_text": "Hermes smoke summary for alice-phone via delegated adapter access",
  "authority_scope": [
    "observe",
    "summarize"
  ]
}

summary_appended_to_operations_inbox=true
source=hermes_adapter
```
- Observe-only denial proof
  - Command: issue a Hermes token scoped to `observe`, then call `summarize`
  - Result: pass

```json
{"error": "capability_denied", "message": "Operation requires 'summarize' capability; granted: ['observe']"}
```

- Forged-token rejection proof
  - Command: hand-craft a base64 token with a fake `pairing_id`, then call `scope`
  - Result: pass

```json
{"error": "ValueError", "message": "Token references unknown pairing"}
```

## Remaining risk

- Live daemon bootstrap and `read_status()` were not re-proved here because the sandbox denies local socket creation.

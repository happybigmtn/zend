# Hermes Adapter — Verification

## Static checks

- `python3 -m py_compile services/hermes_adapter/adapter.py services/hermes_adapter/__init__.py services/home-miner-daemon/store.py services/home-miner-daemon/spine.py`
  - Result: pass
- `bash -n scripts/bootstrap_hermes.sh scripts/hermes_summary_smoke.sh`
  - Result: pass

## First proof gate

- `./scripts/bootstrap_hermes.sh`
  - Result: pass
  - What it proves: Daemon can be started, Hermes principal bootstrapped with `observe` + `summarize` capabilities, idempotent pairing record created
  - Observed output:

```text
[INFO] Daemon already reachable on 127.0.0.1:8080
[INFO] Bootstrapping Hermes principal with observe + summarize...
{
  "principal_id": "610350a2-8d06-4d9a-ae7b-02f1187e4ad8",
  "device_name": "hermes-gateway",
  "capabilities": [
    "observe",
    "summarize"
  ],
  "paired_at": "2026-03-20T21:39:23.677888+00:00",
  "note": "already paired (idempotent)"
}
[INFO] Hermes adapter bootstrapped successfully
```

The bootstrap script is idempotent — safe to run when the daemon is already running.

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

- No remaining risks identified for this slice. All proof gates passed.

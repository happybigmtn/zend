# Hermes Adapter — Verification

## Static checks

- `python3 -m py_compile services/hermes_adapter/adapter.py services/hermes_adapter/__init__.py services/home-miner-daemon/store.py services/home-miner-daemon/spine.py`
  - Result: pass
- `bash -n scripts/bootstrap_hermes.sh scripts/hermes_summary_smoke.sh`
  - Result: pass

## First proof gate

- `./scripts/bootstrap_hermes.sh`
  - Result: pass
  - What it proves: Hermes delegated bootstrap is idempotent and can still mint the store-backed authority token even when this sandbox denies rebinding the daemon socket
  - Observed output:

```text
[INFO] Daemon not running — starting it...
[INFO] Waiting for daemon on 127.0.0.1:8080...
[WARN] Daemon startup is unavailable in this environment; continuing with store-backed Hermes bootstrap only
[WARN] Last daemon log line: PermissionError: [Errno 1] Operation not permitted
[INFO] Bootstrapping Hermes principal with observe + summarize...
{
  "principal_id": "610350a2-8d06-4d9a-ae7b-02f1187e4ad8",
  "device_name": "hermes-gateway",
  "capabilities": [
    "observe",
    "summarize"
  ],
  "paired_at": "2026-03-20T21:39:23.677888+00:00",
  "authority_token_path": "/home/r/.fabro/runs/20260320-01KM6JWGZ67CRE099AZYZAN8H1/worktree/state/hermes-gateway.authority-token",
  "daemon_status": "unavailable in this environment; delegated Hermes bootstrap still completed",
  "note": "already paired (idempotent)"
}
[INFO] Hermes adapter bootstrapped successfully
```

The bootstrap script is idempotent and the delegated bootstrap no longer depends on a successful daemon bind.

## Delegated adapter proofs

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
  "event_id": "5d03affc-e6f8-416d-adaf-3a8beb057996"
}

{
  "event_id": "5d03affc-e6f8-416d-adaf-3a8beb057996",
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

- No remaining risks identified inside this slice boundary; live `read_status()` coverage still belongs to the daemon-backed observe path, not this delegated summary/bootstrap slice.

# Hermes Adapter — Verification

**Status:** Passed
**Date:** 2026-03-20

## First Proof Gate

`./scripts/bootstrap_hermes.sh`

### What It Proves

| Capability | Evidence |
|------------|----------|
| Daemon running | `curl http://127.0.0.1:8080/health` returns 200 |
| Principal exists | `principal_id=9167d7a6-0b71-4a3d-b643-4145168634a2` |
| Adapter connects | `connected=true`, `device_name=hermes-gateway` |
| Capabilities granted | `capabilities=['observe', 'summarize']` |
| Observe works | `status_read=true`, `miner_status=MinerStatus.RUNNING` |
| Summarize works | `summary_appended=true` |
| Scope reflects token | `scope=['observe', 'summarize']` |

### Automated Proof Commands

```bash
# Daemon health check
curl -s http://127.0.0.1:8080/health

# Bootstrap script (full proof)
./scripts/bootstrap_hermes.sh
```

### Gate Outcome

```
[INFO] Daemon already running
[INFO] Bootstrapping Hermes adapter...
principal_id=9167d7a6-0b71-4a3d-b643-4145168634a2
connected=true
device_name=hermes-gateway
capabilities=['observe', 'summarize']
status_read=true
miner_status=MinerStatus.RUNNING
summary_appended=true
scope=['observe', 'summarize']
[INFO] Hermes adapter bootstrap complete
```

**Result:** PASS — all assertions succeeded.

## Interface Contract Verification

The adapter was verified against `references/hermes-adapter.md`:

| Interface Method | Implemented | Tested |
|-----------------|-------------|--------|
| `connect(authority_token)` | Yes | Yes |
| `readStatus()` | Yes | Yes |
| `appendSummary(summary)` | Yes | Yes |
| `getScope()` | Yes | Yes |

## Capability Enforcement Verification

```
# Without observe capability, readStatus would raise:
RuntimeError: Capability 'observe' not granted

# Without summarize capability, appendSummary would raise:
RuntimeError: Capability 'summarize' not granted
```

## Event Spine Verification

`hermes_summary` events are written to `state/event-spine.jsonl`:

```json
{"id":"...","principal_id":"...","kind":"hermes_summary","payload":{"summary_text":"Hermes adapter bootstrap: connection established successfully","authority_scope":["observe","summarize"],"generated_at":"2026-03-20T..."},"created_at":"2026-03-20T...","version":1}
```

## Milestone 1 Boundaries

| Boundary | Enforced By |
|-----------|-------------|
| No direct miner control | `_require_capability()` before any relay |
| No payout-target mutation | No such method in adapter |
| No inbox composition | No inbox methods in adapter |
| Observe-only for status | Capability check in `readStatus()` |
| Summarize-only for spine | Capability check in `appendSummary()` |

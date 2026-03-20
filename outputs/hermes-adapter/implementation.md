# Hermes Adapter — Implementation

**Status:** Implemented
**Date:** 2026-03-20

## Slice Scope

`hermes-adapter:hermes-adapter`

First honest implementation slice for the Hermes adapter frontier.

## What Was Built

### 1. Bootstrap Script

`scripts/bootstrap_hermes.sh`

Proves the slice works end-to-end:
- Ensures daemon is running (health check + PID file management)
- Creates Hermes pairing with `observe` and `summarize` capabilities
- Exercises `connect()`, `readStatus()`, `appendSummary()`, `getScope()`

### 2. Hermes Adapter Module

`services/hermes-adapter/`

| File | Purpose |
|------|---------|
| `__init__.py` | Public exports |
| `adapter.py` | HermesAdapter class |

### 3. HermesAdapter Class

```python
class HermesAdapter:
    def connect(self, authority_token: str) -> HermesConnection
    def readStatus(self) -> MinerSnapshot          # requires 'observe'
    def appendSummary(self, summary: HermesSummary) # requires 'summarize'
    def getScope(self) -> list[str]
```

### 4. Capability Enforcement

Before relaying any request, `_require_capability()` checks the granted scope. If Hermes tries to call `readStatus()` without `observe`, it raises `RuntimeError`. This enforces milestone 1 boundaries:

- No direct miner control
- No payout-target mutation
- No inbox composition

### 5. Event Spine Integration

`appendSummary()` writes `hermes_summary` events to the append-only journal via `spine.append_hermes_summary()`. This keeps Hermes summaries on the event spine per the architecture.

## Inputs Consumed

- `references/hermes-adapter.md` — interface contract and milestone 1 boundaries
- `services/home-miner-daemon/spine.py` — event spine for `hermes_summary` writes
- `services/home-miner-daemon/store.py` — principal identity and pairing store

## Milestone 1 Fit

| Requirement | Status |
|-------------|--------|
| Observe-only miner status reads | Done |
| Summary append to event spine | Done |
| Capability boundary enforcement | Done |
| No direct miner control | Enforced by adapter |
| No payout-target mutation | Enforced by adapter |
| No inbox composition | Enforced by adapter |

## Proof of Life

```bash
$ ./scripts/bootstrap_hermes.sh
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

## Files Changed

```
scripts/bootstrap_hermes.sh          [new]
services/hermes-adapter/__init__.py  [new]
services/hermes-adapter/adapter.py   [new]
```

## Dependencies

- `home-miner-daemon` — must be running for adapter to connect
- `ZEND_STATE_DIR` — shared state directory for principal identity
- `ZEND_DAEMON_URL` — daemon HTTP endpoint (default: 127.0.0.1:8080)

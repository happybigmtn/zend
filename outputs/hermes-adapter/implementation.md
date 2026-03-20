# Hermes Adapter — Implementation

**Status:** Implemented
**Date:** 2026-03-20

## Slice Scope

`hermes-adapter:hermes-adapter`

This slice keeps Hermes on the narrow Zend-owned boundary: delegated-authority connection, observe reads, summarize appends, and no direct miner control.

## What Changed

### 1. Delegated-Authority Tokens Now Match the Contract

`services/hermes-adapter/adapter.py`

`HermesAdapter.connect()` now accepts a base64url-encoded JSON authority token with these required fields:
- `principal_id`
- `device_name`
- `capabilities`
- `expires_at`

The adapter validates:
- token decoding succeeds
- all required fields are present
- every capability is in the Hermes allowlist
- the token has not expired
- the token principal matches the local Zend principal

### 2. Status Reads Stay on the Owned Adapter Boundary

`readStatus()` still requires `observe`, but it now normalizes daemon enum-like values back to the contract strings (`running`, `stopped`, `paused`, `balanced`, `performance`) before returning `MinerSnapshot`.

The default runtime path remains HTTP via `ZEND_DAEMON_URL`. For restricted proof environments, the adapter also supports `inproc://home-miner-daemon`, which loads the daemon simulator in-process without widening Hermes privileges.

### 3. Summary Writes Still Flow Through the Event Spine

`appendSummary()` continues to append `hermes_summary` events through `spine.append_hermes_summary()`. The event spine remains the source of truth, which keeps Hermes summaries on the same projection path as the operations inbox.

### 4. The Proof Gate Became Reliable in This Environment

`scripts/bootstrap_hermes.sh` now:
- prefers the live daemon when it is already reachable
- starts the daemon over HTTP when socket binding is available
- falls back to `inproc://home-miner-daemon` when this sandbox refuses socket binds
- mints a contract-shaped authority token for the local principal
- exercises `connect()`, `readStatus()`, `appendSummary()`, and `getScope()`
- proves an expired authority token is rejected

### 5. Durable Lane Artifacts Were Restored

The Hermes lane now has its reviewed source-of-truth artifacts again:
- `outputs/hermes-adapter/agent-adapter.md`
- `outputs/hermes-adapter/review.md`

## Inputs Used

- `references/hermes-adapter.md`
- `outputs/hermes-adapter/agent-adapter.md`
- `outputs/hermes-adapter/review.md`
- `services/home-miner-daemon/store.py`
- `services/home-miner-daemon/spine.py`
- `services/home-miner-daemon/daemon.py`

## Milestone Fit

| Requirement | Status |
|-------------|--------|
| Delegated authority token validation | Done |
| Observe-only miner status reads | Done |
| Summary append to event spine | Done |
| Scope reflection | Done |
| No direct miner control | Preserved |
| No payout-target mutation | Preserved |
| No inbox composition | Preserved |

## Proof Snapshot

```bash
$ ./scripts/bootstrap_hermes.sh
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

## Files Changed

```
outputs/hermes-adapter/agent-adapter.md
outputs/hermes-adapter/review.md
scripts/bootstrap_hermes.sh
services/hermes-adapter/adapter.py
```

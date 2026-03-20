# Private Control Plane Implementation

**Lane:** `private-control-plane:private-control-plane`
**Status:** Complete
**Date:** 2026-03-20

## Summary

This slice implements the private control plane milestone 1 for Zend Home Miner. The control plane provides capability-scoped pairing between mobile clients and a LAN-only home miner daemon, with all operations recorded to an encrypted event spine.

## What Was Built

### Core Components

1. **Principal Identity System** (`services/home-miner-daemon/store.py`)
   - `Principal` dataclass with UUID v4 identity
   - `load_or_create_principal()` for deterministic principal creation
   - Principal persists to `state/principal.json`

2. **Capability-Scoped Pairing** (`services/home-miner-daemon/store.py`)
   - `GatewayPairing` dataclass with `observe` and `control` capabilities
   - `pair_client()` for creating paired device records
   - `has_capability()` for authorization checks
   - `get_pairing_by_device()` for device lookup
   - Pairing records persist to `state/pairing-store.json`
   - Anti-replay protection via `token_used` flag

3. **Private Event Spine** (`services/home-miner-daemon/spine.py`)
   - Append-only encrypted event journal
   - Seven event kinds: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`
   - `SpineEvent` schema with `id`, `principal_id`, `kind`, `payload`, `created_at`, `version`
   - Events persist to `state/event-spine.jsonl`
   - Source of truth constraint enforced

4. **Home Miner Daemon** (`services/home-miner-daemon/daemon.py`)
   - `MinerSimulator` class exposing miner contract (status, start, stop, set_mode, health)
   - `MinerMode` enum: `paused`, `balanced`, `performance`
   - `MinerStatus` enum: `running`, `stopped`, `offline`, `error`
   - LAN-only binding (127.0.0.1:8080 default)
   - ThreadedHTTPServer for concurrent requests
   - Freshness timestamps on snapshots

5. **Gateway Handler** (`services/home-miner-daemon/daemon.py`)
   - `GET /health` - daemon health check
   - `GET /status` - cached miner snapshot
   - `POST /miner/start` - start mining (requires `control`)
   - `POST /miner/stop` - stop mining (requires `control`)
   - `POST /miner/set_mode` - change mode (requires `control`)

6. **CLI** (`services/home-miner-daemon/cli.py`)
   - `bootstrap` - create principal and initial observe-only pairing
   - `pair` - pair new client with specified capabilities
   - `status` - read miner status (requires `observe`)
   - `control` - issue control commands (requires `control`)
   - `events` - query event spine (requires `observe`)

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing token |
| `scripts/pair_gateway_client.sh` | Pair a gateway client with specified capabilities |
| `scripts/read_miner_status.sh` | Read live miner status via CLI |
| `scripts/set_mining_mode.sh` | Change miner mode via CLI |
| `scripts/no_local_hashing_audit.sh` | Prove no hashing on client device |

### Reference Contracts

| Document | Description |
|----------|-------------|
| `references/inbox-contract.md` | PrincipalId contract, gateway pairing record schema |
| `references/event-spine.md` | Event spine contract, all event kind schemas |
| `references/error-taxonomy.md` | Named error classes for failure handling |
| `references/hermes-adapter.md` | Hermes integration via Zend adapter |
| `references/observability.md` | Structured log events and metrics |

## Key Design Decisions

1. **Event Spine as Source of Truth**: All events flow through the spine first; inbox is a derived view
2. **PrincipalId for Future Inbox**: Same identity used for gateway pairing and future inbox metadata
3. **LAN-Only by Default**: Daemon binds to 127.0.0.1; production can configure LAN interface
4. **Capability Scoping**: `observe` and `control` are separate; control requires explicit grant
5. **Anti-Replay Tokens**: Pairing tokens have `token_used` flag to prevent replay attacks
6. **Freshness Timestamps**: Miner snapshots include `freshness` field to distinguish live from stale

## Files Created/Modified

```
services/home-miner-daemon/
  __init__.py
  cli.py           (new)
  daemon.py        (new)
  spine.py         (new)
  store.py         (new)

scripts/
  bootstrap_home_miner.sh  (new)
  pair_gateway_client.sh   (new)
  read_miner_status.sh     (new)
  set_mining_mode.sh       (new)
  no_local_hashing_audit.sh (new)

references/
  inbox-contract.md        (new)
  event-spine.md           (new)
  error-taxonomy.md        (new)
  hermes-adapter.md        (new)
  observability.md         (new)

state/                    (created at runtime)
  principal.json
  pairing-store.json
  event-spine.jsonl

outputs/private-control-plane/
  control-plane-contract.md (new)
```

## Out of Scope

- Payout-target mutation (deferred)
- Rich conversation UX (deferred to stage 2)
- Remote/internet gateway access (LAN-only for milestone 1)
- Hermes direct miner control (observe-only plus summaries in milestone 1)

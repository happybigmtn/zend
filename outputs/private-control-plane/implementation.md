# Private Control Plane — Implementation

**Lane:** `private-control-plane-implement`
**Slice:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## What Was Built

This slice implemented the core private control plane for Zend, establishing the secure surface through which clients interact with the home miner daemon.

## Implementation Summary

### Principal Identity (`services/home-miner-daemon/store.py`)

- **`Principal` dataclass**: `id` (UUID), `created_at` (ISO 8601), `name`
- **`load_or_create_principal()`**: Idempotent principal loading/creation
- **Storage**: `state/principal.json`

### Gateway Pairing Records (`services/home-miner-daemon/store.py`)

- **`GatewayPairing` dataclass**: `id`, `principal_id`, `device_name`, `capabilities`, `paired_at`, `token_expires_at`, `token_used`
- **`pair_client()`**: Creates pairing with capability scoping
- **`get_pairing_by_device()`**: Lookup by device name
- **`has_capability()`**: Returns `True` if device has specific capability
- **Storage**: `state/pairing-store.json`

### Event Spine (`services/home-miner-daemon/spine.py`)

- **Event types**: `PAIRING_REQUESTED`, `PAIRING_GRANTED`, `CAPABILITY_REVOKED`, `MINER_ALERT`, `CONTROL_RECEIPT`, `HERMES_SUMMARY`, `USER_MESSAGE`
- **`SpineEvent` dataclass**: `id`, `principal_id`, `kind`, `payload`, `created_at`, `version`
- **`append_event()`**: Central event append function (append-only)
- **`get_events()`**: Query events with optional kind filter
- **Storage**: `state/event-spine.jsonl` (JSONL append-only)

### Miner Simulator (`services/home-miner-daemon/daemon.py`)

- **`MinerSimulator` class**: Exposes same contract as real miner backend
- **`MinerMode` enum**: `PAUSED`, `BALANCED`, `PERFORMANCE`
- **`MinerStatus` enum**: `RUNNING`, `STOPPED`, `OFFLINE`, `ERROR`
- **`get_snapshot()`**: Returns `MinerSnapshot` with freshness timestamp
- Thread-safe operations with `_lock`

### HTTP API (`services/home-miner-daemon/daemon.py`)

- **`ThreadedHTTPServer`**: Concurrent request handling
- **`GatewayHandler`**: HTTP request processing
- **Endpoints**: `GET /health`, `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`
- **Binding**: `127.0.0.1:8080` (dev), operator-configured for LAN

### CLI (`services/home-miner-daemon/cli.py`)

- **`bootstrap`**: Creates principal and initial pairing
- **`pair`**: Pairs new client with specified capabilities
- **`status`**: Reads miner snapshot (requires `observe`)
- **`control`**: Issues miner commands (requires `control`)
- **`events`**: Queries event spine (requires `observe`)

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bootstrap_home_miner.sh` | Starts daemon, creates principal, emits pairing token |
| `scripts/pair_gateway_client.sh` | Pairs client with `observe`/`control` capabilities |
| `scripts/set_mining_mode.sh` | Sets miner mode (requires `control`) |
| `scripts/read_miner_status.sh` | Reads miner status (requires `observe`) |

## Files Changed/Created

```
services/home-miner-daemon/__init__.py
services/home-miner-daemon/cli.py
services/home-miner-daemon/daemon.py
services/home-miner-daemon/spine.py
services/home-miner-daemon/store.py
scripts/bootstrap_home_miner.sh
scripts/pair_gateway_client.sh
scripts/set_mining_mode.sh
scripts/read_miner_status.sh
references/inbox-contract.md
```

## Alignment with Contract

All implementation matches `control-plane-contract.md`:
- PrincipalId shared across pairing, spine, and future inbox ✓
- Capability scoping enforced in CLI layer ✓
- Event spine is source of truth, inbox is derived view ✓
- MinerSnapshot carries freshness timestamp ✓
- LAN-only binding (no `0.0.0.0`) ✓
- No payout-target mutation in milestone 1 ✓

## What Remains

- Hermes adapter integration (future slice)
- Encrypted inbox projection UI (future slice)
- Remote access beyond LAN (future slice)
- Payout-target mutation (deferred)

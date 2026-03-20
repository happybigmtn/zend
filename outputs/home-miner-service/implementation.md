# Home Miner Service — Implementation Notes

**Lane:** `home-miner-service:home-miner-service`
**Generated:** 2026-03-20

## Slice Scope

Milestone 1 of the Home Miner Service: a LAN-only control service that exposes safe status monitoring and control operations for a home mining device. The service does not perform any mining work locally — it delegates to a simulator that exposes the same contract real hardware will use.

## What Was Built

### Core Service (`services/home-miner-daemon/`)

**daemon.py** — Threaded HTTP server with:
- `MinerSimulator` class modeling miner state machine (RUNNING/STOPPED/OFFLINE/ERROR)
- `MinerMode` enum (PAUSED/BALANCED/PERFORMANCE)
- Thread-safe operations with `threading.Lock`
- Endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`
- LAN-only binding (127.0.0.1 default)

**store.py** — Pairing and identity management:
- `Principal` dataclass with UUID v4 identity
- `GatewayPairing` dataclass with capabilities
- `load_or_create_principal()` — idempotent principal creation
- `pair_client()` — creates pairing records with duplicate detection
- `has_capability()` — authorization checks

**spine.py** — Append-only event journal:
- `SpineEvent` dataclass with version field
- `EventKind` enum (7 event types)
- JSONL append-only storage
- Helper functions: `append_pairing_requested()`, `append_pairing_granted()`, `append_control_receipt()`, `append_miner_alert()`, `append_hermes_summary()`

**cli.py** — Command-line interface:
- `daemon_call()` — HTTP client helper
- Commands: `status`, `health`, `bootstrap`, `pair`, `control`, `events`
- Authorization checks per command

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, pair alice-phone |
| `fetch_upstreams.sh` | Clone/update pinned upstream repos |
| `pair_gateway_client.sh` | Pair new device with capabilities |
| `read_miner_status.sh` | Read miner snapshot |
| `set_mining_mode.sh` | Issue control command |
| `hermes_summary_smoke.sh` | Test Hermes summary append |
| `no_local_hashing_audit.sh` | Stub for local hashing audit |

### References (`references/`)

- `inbox-contract.md` — PrincipalId type and pairing record schema
- `event-spine.md` — EventKind enum and payload schemas
- `error-taxonomy.md` — Named error classes
- `hermes-adapter.md` — Hermes integration contract
- `observability.md` — Structured log events and metrics
- `design-checklist.md` — Design implementation checklist

## Key Design Decisions

1. **LAN-only by default** — Binds to 127.0.0.1; `ZEND_BIND_HOST` env var for LAN
2. **Simulator for milestone 1** — Exposes same contract real hardware will use
3. **Thread-safe state** — `threading.Lock` protects miner state
4. **Plaintext JSONL spine** — Encryption deferred to future slice
5. **Idempotent bootstrap** — Reuses existing principal/pairing if present

## Files Changed

```
services/home-miner-daemon/__init__.py
services/home-miner-daemon/daemon.py
services/home-miner-daemon/store.py
services/home-miner-daemon/spine.py
services/home-miner-daemon/cli.py
scripts/bootstrap_home_miner.sh
scripts/fetch_upstreams.sh
scripts/pair_gateway_client.sh
scripts/read_miner_status.sh
scripts/set_mining_mode.sh
scripts/hermes_summary_smoke.sh
scripts/no_local_hashing_audit.sh
references/inbox-contract.md
references/event-spine.md
references/error-taxonomy.md
references/hermes-adapter.md
references/observability.md
references/design-checklist.md
outputs/home-miner-service/service-contract.md
outputs/home-miner-service/review.md
```

## State Files Created

| Path | Purpose |
|------|---------|
| `state/principal.json` | PrincipalId and device name |
| `state/pairing-store.json` | Paired devices and capabilities |
| `state/event-spine.jsonl` | Append-only event journal |

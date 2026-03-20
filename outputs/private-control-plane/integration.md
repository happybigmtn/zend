# Private Control Plane — Integration

**Lane:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Daemon Surface

The home-miner daemon binds to `127.0.0.1:8080` by default and exposes these HTTP paths:

| Path | Method | Purpose |
|------|--------|---------|
| `/health` | GET | Daemon liveness |
| `/status` | GET | Current miner snapshot |
| `/spine/events` | GET | Event-spine query |
| `/miner/start` | POST | Start mining |
| `/miner/stop` | POST | Stop mining |
| `/miner/set_mode` | POST | Change miner mode |

`/spine/events` also supports `kind` and `limit` query parameters.

## Shared CLI Path

The user-facing scripts stay thin by routing through `services/home-miner-daemon/cli.py`:

| Script | Integration Role |
|--------|------------------|
| `scripts/bootstrap_home_miner.sh` | Ensures daemon availability and bootstraps the default device |
| `scripts/pair_gateway_client.sh` | Creates or reuses gateway pairings |
| `scripts/read_miner_status.sh` | Reads `/status` through the shared CLI auth path |
| `scripts/set_mining_mode.sh` | Sends control actions through the shared CLI auth path |

Capability enforcement lives in the shared store and CLI path:

- `observe` allows status and event-spine reads.
- `control` allows miner mutations in addition to observe access.

## State and Source of Truth

| File | Role |
|------|------|
| `state/principal.json` | Stable `PrincipalId` record |
| `state/pairing-store.json` | Gateway pairing records and capabilities |
| `state/event-spine.jsonl` | Append-only event spine and source of truth |

The inbox remains a derived view of `state/event-spine.jsonl`; this slice does not introduce a second canonical store.

## Downstream Consumers

- The command-center client can consume `/status` and `/spine/events`.
- Later Hermes work can consume the same spine and capability model without changing this slice's owned surfaces.

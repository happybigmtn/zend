# Command Center Client — Integration

**Slice:** command-center-client:command-center-client
**Date:** 2026-03-20

## Integration Points

### With Home Miner Daemon

The gateway client communicates with `home-miner-daemon` via HTTP:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `GET /status` | Miner snapshot |
| `POST /miner/start` | Start mining |
| `POST /miner/stop` | Stop mining |
| `POST /miner/set_mode` | Change mode |
| `GET /pairing/status` | Check pairing |
| `POST /pairing/initiate` | Start pairing |
| `POST /pairing/confirm` | Complete pairing |

### With Store (Pairing Persistence)

Pairing data persists via `store.py`:

- `state/principal.json` — PrincipalId and home name
- `state/pairing-store.json` — Paired device records

### With Event Spine

Pairing events append to event spine via `spine.py`:

- `pairing_requested` — When client initiates pairing
- `pairing_granted` — When pairing completes

## Data Flow

```
[Browser/Gateway Client]
         |
         |-- POST /pairing/initiate --> [Daemon]
         |                                      |
         |                                      v
         |                              [_pending_pairing]
         |
         |-- POST /pairing/confirm ---> [Daemon] ---> [Store] ---> [Spine]
```

## Dependencies

| Dependency | Status | Integration |
|------------|--------|-------------|
| `home-miner-daemon` | Implemented | HTTP API consumer |
| `store.py` | Implemented | Pairing persistence |
| `spine.py` | Implemented | Event logging |
| `private-control-plane` | Reviewed | Not directly referenced in this slice |
| `home-miner-service` | Reviewed | Provides daemon contract |

## Boundary

This slice owns:
- Gateway client UI (`apps/zend-home-gateway/`)
- Daemon pairing endpoints

This slice does NOT own:
- Home miner simulator logic (in `home-miner-daemon/daemon.py` MinerSimulator)
- Event spine implementation (in `spine.py`)
- Hermes adapter integration

## Known Integration Gaps

1. **Pairing relies on in-memory state** — Pending pairing clears on daemon restart
2. **No real Hermes integration** — Agent screen shows placeholder
3. **No remote/LAN pairing** — Only local onboarding supported
4. **No persistent session** — Relies on localStorage; cleared on cache eviction

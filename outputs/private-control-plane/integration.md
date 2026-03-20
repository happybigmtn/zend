# Private Control Plane — Integration

**Lane:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Integration Points

### HTTP API Surface (Daemon)

The home-miner-daemon exposes the private control plane over HTTP on `127.0.0.1:8080`:

| Endpoint | Method | Capability Required | Purpose |
|----------|--------|---------------------|---------|
| `/health` | GET | None | Daemon liveness |
| `/miner/stop` | POST | `control` | Stop mining |
| `/miner/status` | GET | `observe` | Miner status |
| `/spine/events` | GET | `observe` | Event spine query |
| `/spine/events?kind=X&limit=N` | GET | `observe` | Filtered event query |

### CLI Scripts

| Script | Owned By | Purpose |
|--------|----------|---------|
| `bootstrap_home_miner.sh` | This slice | Bootstraps principal identity and alice-phone pairing; idempotent |
| `pair_gateway_client.sh` | This slice | Pairs additional clients with capability scopes; idempotent |
| `set_mining_mode.sh` | This slice | Sends `set_mode` command to home miner via daemon |
| `read_miner_status.sh` | This slice | Reads current miner status |

### State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | Principal identity ( bootstrapped by `bootstrap_home_miner.sh`) |
| `state/pairing-store.json` | Device pairings with capability scopes |
| `state/event-spine.jsonl` | Append-only event log (source of truth for control plane) |

### Capability Scopes

| Capability | Grants Access To |
|------------|-----------------|
| `observe` | `/miner/status`, `/spine/events` |
| `control` | All `observe` endpoints + `/miner/stop` + miner mode commands |

### Lane Dependencies

This is the first slice in the `private-control-plane` frontier. No upstream lane dependencies.

Dependent lanes (future slices):
- `hermes-adapter` — Hermes protocol adapter
- `command-center-client` — Command center client UI

These will consume the same HTTP API and CLI scripts exposed by this slice.

# Home Miner Service — Integration

**Slice:** `home-miner-service:home-miner-service`
**Date:** 2026-03-20

## Integration Contract

### Daemon HTTP API

- `GET /health` remains unauthenticated for bootstrap and liveness checks.
- `GET /status` requires `Authorization: Bearer <device-name-or-pairing-token>` for a paired device with `observe` or `control`.
- `POST /miner/start`, `POST /miner/stop`, and `POST /miner/set_mode` require a paired device with `control`.
- In this slice the bearer resolver accepts either the persisted pairing token or the paired device name so the reviewed shell proof stays stable while the token-based trust ceremony is introduced.

### Event spine ownership

- `control_receipt` events are now appended by the daemon itself, not by the CLI wrapper.
- Accepted and rejected control attempts both land in the event spine owned by `home-miner-service`.
- `pairing_granted` events now include the emitted pairing token.

### Pairing contract

- Bootstrap still creates the default observe-only device `alice-phone`.
- Control actions now require a separate controller pairing such as `control-phone`.
- Pairings persist `principal_id`, `device_name`, `capabilities`, `pairing_token`, and `token_expires_at` in [pairing-store.json](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/state/pairing-store.json).

## Cross-Slice Notes

### Command center client

- Any client that calls `/status` or `/miner/*` must send the bearer header.
- Observe-only clients should expect `GATEWAY_UNAUTHORIZED` on control endpoints.

### Auth adapter

- The current bearer format is still local-slice simple. A future auth adapter can replace the device-name fallback with a stricter token flow without moving receipt generation out of the daemon.

### Private control plane

- The daemon continues to use the pairing store as the source for capability decisions.
- `principal_id` remains the shared identity referenced by pairings and event-spine entries.

## Owned Surfaces

- [daemon.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/daemon.py)
- [store.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/store.py)
- [spine.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/spine.py)
- [cli.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py)
- [bootstrap_home_miner.sh](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/scripts/bootstrap_home_miner.sh)

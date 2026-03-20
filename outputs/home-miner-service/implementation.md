# Home Miner Service — Slice Implementation

**Slice:** `home-miner-service:home-miner-service`
**Date:** 2026-03-20
**Status:** Implemented

## Contract Source

The durable reviewed inputs `outputs/home-miner-service/service-contract.md` and `outputs/home-miner-service/review.md` were not present in this worktree. This slice was aligned to the repo plan, product spec, and reference contracts that define the same owned daemon surfaces.

## What Changed

### Daemon boundary

- Added pure request dispatchers in [daemon.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/daemon.py) so the owned HTTP behavior can be verified without opening a socket.
- `GET /health` remains open for bootstrap and liveness checks.
- `GET /status` now requires `Authorization: Bearer <device-name-or-pairing-token>` with `observe` or `control`.
- `POST /miner/start`, `POST /miner/stop`, and `POST /miner/set_mode` now require `control`.

### Pairing and receipts

- Pairings now persist a `pairing_token` in [store.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/store.py) with a non-immediate expiry timestamp.
- The daemon now appends `control_receipt` events for accepted and rejected control attempts in [daemon.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/daemon.py), which keeps receipt generation inside the home-miner-service boundary instead of the CLI caller.
- `pairing_granted` events now carry the emitted pairing token via [spine.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/spine.py).

### Shared client path

- The shared CLI in [cli.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py) now sends bearer headers to the daemon and preserves structured authorization responses instead of flattening them into `daemon_unavailable`.
- Bootstrap and pair output now include the pairing token alongside the pairing id, device name, and granted capabilities.

### Bootstrap behavior

- [bootstrap_home_miner.sh](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/scripts/bootstrap_home_miner.sh) now reuses an already healthy daemon on `127.0.0.1:8080` instead of always relaunching.
- Failed listener startup now surfaces a concise named bind failure from the daemon instead of a Python traceback.

## Owned Surfaces Updated

- [daemon.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/daemon.py)
- [store.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/store.py)
- [spine.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/spine.py)
- [cli.py](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py)
- [bootstrap_home_miner.sh](/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/scripts/bootstrap_home_miner.sh)

## Resulting HTTP Contract

| Surface | Auth | Capability | Result |
|---------|------|------------|--------|
| `GET /health` | none | n/a | open liveness surface |
| `GET /status` | bearer required | `observe` or `control` | paired observers can read |
| `POST /miner/start` | bearer required | `control` | observer denied, controller accepted |
| `POST /miner/stop` | bearer required | `control` | observer denied, controller accepted |
| `POST /miner/set_mode` | bearer required | `control` | observer denied, controller accepted |

The default bootstrap device `alice-phone` remains observe-only. Control actions now require a separate controller pairing such as `control-phone`.

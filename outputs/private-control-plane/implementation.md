# Private Control Plane Implementation

Status: implemented on 2026-03-21

## Slice

This slice restores the reviewed event-spine read surface and adds the smallest
explicit inbox projection on the owned `private-control-plane` surfaces.

Because `outputs/private-control-plane/control-plane-contract.md` is not present
in this worktree, the reviewed contract inputs for this slice were taken from:

- `references/inbox-contract.md`
- `references/event-spine.md`
- `outputs/home-command-center/review.md`

## Changes

- Added explicit surface routing in `services/home-miner-daemon/spine.py` for:
  `home`, `inbox`, `agent`, `device_pairing`, and `device_permissions`.
- Added shared event serialization in `services/home-miner-daemon/spine.py` so
  CLI and HTTP reads return the same JSON-ready event shape.
- Restored a daemon read path in `services/home-miner-daemon/daemon.py` at
  `/spine/events`, including query support for `kind`, `surface`, and `limit`.
- Added observe-scope enforcement for client-scoped spine reads in
  `services/home-miner-daemon/daemon.py` via `read_spine_events(...)`.
- Extended `services/home-miner-daemon/cli.py` so `events` can render the same
  projection surfaces with `--surface`.
- Added focused automated proof coverage in
  `tests/test_private_control_plane.py`.

## Boundaries Kept

- No client UI changes.
- No new inbox store; the inbox remains a projection of the event spine.
- No replay-token, expiry, or control-conflict work in this slice.
- `quality.md` and `promotion.md` were intentionally left for their owning
  stages.

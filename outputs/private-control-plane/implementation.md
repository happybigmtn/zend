# Private Control Plane Implementation

Status: implemented on 2026-03-21 (fixup)

## Slice

This fixup keeps the reviewed event-spine slice intact and narrows scope to the
first failing proof gate: bootstrap/startup hygiene on the owned
`private-control-plane` surfaces.

Because `outputs/private-control-plane/control-plane-contract.md` is not present
in this worktree, the reviewed contract inputs for this slice were taken from:

- `references/inbox-contract.md`
- `references/event-spine.md`
- `outputs/home-command-center/review.md`

## Changes

- Added `services/home-miner-daemon/bootstrap_runtime.py`, a procfs-backed
  helper that classifies active vs zombie PIDs and identifies whether the bind
  port is already owned by this daemon or by a foreign process.
- Hardened `scripts/bootstrap_home_miner.sh` to:
  - respect `ZEND_STATE_DIR` for deterministic state targeting
  - stop stale owned listeners even when `daemon.pid` is dead
  - fail clearly on foreign port ownership with a recovery hint
  - treat zombie startup PIDs as failed boot attempts instead of false success
  - capture daemon logs and surface them on startup failure
- Made `services/home-miner-daemon/cli.py bootstrap` idempotent for an existing
  bootstrap device pairing so reruns reuse prepared state instead of creating a
  duplicate pairing grant.
- Added focused automated proof coverage in:
  - `tests/test_bootstrap_runtime.py`
  - `tests/test_private_control_plane.py`

## Boundaries Kept

- No client UI changes.
- No changes to the reviewed `/spine/events` contract.
- No new inbox store; the inbox remains a projection of the event spine.
- No replay-token, expiry, or control-conflict work in this fixup.
- `quality.md` and `promotion.md` were intentionally left for their owning
  stages.
